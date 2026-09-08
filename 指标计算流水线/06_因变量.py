# -*- coding: utf-8 -*-
"""步骤 06 — 因变量层（基金绩效 / 风险），全部从原始数据**自算**，不依赖论文原始面板(元面板)。

数据来源（均为仓库内原始数据，离线自洽）：
  - 基金净值历史_全量.csv        → 季度收益 / 未来收益 / 超额收益 / 绝对收益
  - 基金持仓明细_全量修正版.csv + 个股月收益率_全量.csv → 收益差 RG(持仓隐含收益减基金收益)
  - data/FF因子/FF因子_合并完整版.csv（季度）→ FF3/MOM 因子 + rf
  - data/FF因子/FF5月度因子.csv（月度）→ 聚合为季度 FF5 因子(ff5_MKT_excess/SMB/HML/RMW/CMA/RF)

计算：
  quarter_return : 由净值日收益复利得到季度收益
  future_return  : 同基金下一季度 quarter_return
  excess_return  : quarter_return − rf(季度无风险)
  abs_return     : |quarter_return|
  RG             : quarter_return − Σ_i w_i·r_i (持仓快照权重 × 个股季度收益)，即收益差/选股贡献
  ff3_adj_return : 时序回归 excess_return ~ MKT_excess + SMB + HML 的截距(alpha)
  ff4_adj_return : 同上 + MOM
  ff5_adj_return : 时序回归 excess_return ~ MKT + SMB + HML + RMW + CMA(FF5季度因子) 的截距
  FF 因子列      : MKT_excess/SMB/HML/MOM/rf(FF3合并版) + MKT/SMB/HML/RMW/CMA/RF(FF5季度聚合)
输出：output/L6_因变量.csv
"""
import os
import re
import numpy as np
import pandas as pd

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, "output")
os.makedirs(OUT, exist_ok=True)

# 复用 lib_metrics 的路径与日期工具
import lib_metrics as M


def _quarterly_returns():
    """由净值历史算 (fund_code, report_date, year, quarter, quarter_return)。

    **残缺季度剔除（2026-08-13 修复）**：净值历史最大日期为 max_date，凡
    `季度末 > max_date` 的季度（如净值截至 2026-08-07 时的 2026Q3，仅含 7/1–8/7
    共 38 天）收益残缺、非完整季度，绝不能保留——否则 future_return=shift(-1)
    会把半个 Q3 收益当成 2026Q2 的『下季度收益』泄漏进面板（与样本骨架
    load_skeleton 的『未来季度剔除』同口径）。仅保留 `季度末 ≤ max_date` 的季度。"""
    nav = pd.read_csv(M.D("L4_风险应对层", "基金净值历史_全量.csv"), encoding="utf-8-sig")
    nav["date"] = pd.to_datetime(nav["date"], errors="coerce")
    nav = nav.dropna(subset=["date"]).sort_values(["fund_code", "date"])
    max_date = nav["date"].max()                       # 净值实际覆盖末尾
    nav["nav"] = pd.to_numeric(nav["nav"], errors="coerce")
    nav["daily_return"] = pd.to_numeric(nav["daily_return"], errors="coerce")
    # 口径统一(2026-08-13)：仅 200 只有 daily_return，另 200 只仅有 nav（全缺失）→
    # 由 nav 统一派生日收益补齐（与 load_skeleton 完全一致的逻辑），已有 daily_return 保留原值。
    nav["ret"] = nav.groupby("fund_code")["nav"].pct_change()
    has_dr = nav["daily_return"].notna()
    nav.loc[has_dr, "ret"] = nav.loc[has_dr, "daily_return"] / 100.0
    nav = nav.dropna(subset=["ret"])
    nav["q"] = nav["date"].dt.to_period("Q")
    fr = nav.groupby(["fund_code", "q"])["ret"].apply(lambda s: (1 + s).prod() - 1).reset_index()
    # 仅保留季度末（q_end）≤ 净值最大日期的季度，剔除残缺未来季
    fr["q_end"] = fr["q"].apply(lambda p: p.end_time.normalize())
    fr = fr[fr["q_end"] <= max_date].drop(columns=["q_end"])
    fr["report_date"] = fr["q"].apply(lambda p: M.to_panel_date(p.end_time.normalize()))
    fr["year"] = fr["q"].dt.year
    fr["quarter"] = fr["q"].dt.quarter
    fr = fr.rename(columns={"ret": "quarter_return"})
    return fr[["fund_code", "report_date", "year", "quarter", "q", "quarter_return"]]


def _stock_quarter_return():
    """个股月收益 → 个股季度收益字典 {(quarter_period, stock_code): q_ret}。"""
    sm = pd.read_csv(M.D("股价行情", "个股月收益率_全量.csv"), encoding="utf-8-sig")
    sm["date"] = pd.to_datetime(sm["date"], errors="coerce")
    sm = sm.dropna(subset=["date"])
    sm["month"] = sm["date"].dt.to_period("M")
    sm["stock_code"] = sm["stock_code"].astype(str).str.zfill(6)
    sm["q"] = sm["date"].dt.to_period("Q")   # 直接由 datetime 派生季度 Period[Q]，与基金/持仓口径一致
    # 个股季度收益 = (1+月收益)连乘 - 1（复利，与基金季度收益口径一致）
    g = sm.groupby(["stock_code", "q"])["monthly_return"].apply(
        lambda s: (1 + s.fillna(0)).prod() - 1).reset_index()
    out = {}
    for (stk, q), sub in g.groupby(["stock_code", "q"]):
        out[(q, stk)] = float(sub["monthly_return"].iloc[0])
    return out


def _compute_RG(fr):
    """RG = quarter_return − Σ_i w_i·r_i(个股季度收益)，持仓快照取 ≤ 该季度的一期内最近者。"""
    h = pd.read_csv(M.D("L2_持仓偏离层", "基金持仓明细_全量修正版.csv"), encoding="utf-8-sig")
    h["w"] = pd.to_numeric(h["hold_ratio"], errors="coerce").fillna(0) / 100.0
    h["rd"] = M.to_panel_date(h["report_date"])
    h["q"] = h["rd"].dt.to_period("Q")
    h["stock_code"] = h["stock_code"].astype(str).str.zfill(6)
    sq = _stock_quarter_return()
    rows = []
    for fund, fdf in h.groupby("fund_code"):
        fdf = fdf.sort_values("rd")
        snaps = list(zip(fdf["q"], fdf["rd"],
                         [dict(zip(g["stock_code"], g["w"])) for _, g in fdf.groupby("q")]))
        for _, r in fr[fr["fund_code"] == fund].iterrows():
            q = r["q"]
            # 取 ≤ q 的最近快照（保留权重映射 sw）
            cand = [(sqp, sd, sw) for (sqp, sd, sw) in snaps if sqp <= q]
            if not cand:
                rows.append((fund, r["report_date"], np.nan)); continue
            wmap = cand[-1][2]
            if not wmap:
                rows.append((fund, r["report_date"], np.nan)); continue
            port = sum(wmap.get(stk, 0) * sq.get((q, stk), np.nan)
                       for stk in wmap if not pd.isna(sq.get((q, stk), np.nan)))
            # 仅用有收益的个股权重归一
            wsum = sum(wmap.get(stk, 0) for stk in wmap if not pd.isna(sq.get((q, stk), np.nan)))
            if wsum and not pd.isna(port):
                port = port / wsum
                rg = r["quarter_return"] - port
            else:
                rg = np.nan
            rows.append((fund, r["report_date"], rg))
    return pd.DataFrame(rows, columns=["fund_code", "report_date", "RG"])


def _ff3_factors():
    """FF3+MOM 季度因子（来自 合并完整版），返回 (year, quarter) 索引的因子表。"""
    f = pd.read_csv(M.D("FF因子", "FF因子_合并完整版.csv"), encoding="utf-8-sig")
    return f[["year", "quarter", "MKT_excess", "SMB", "HML", "MOM", "rf"]]


def _ff5_factors_quarter():
    """FF5 月度因子 → 季度（月收益求和）因子，列统一加 ff5_ 前缀避免与 FF3 重名。"""
    f = pd.read_csv(M.D("FF因子", "FF5月度因子.csv"), encoding="utf-8-sig")
    f["date"] = pd.to_datetime(f["date"], errors="coerce")
    f = f.dropna(subset=["date"])
    f["q"] = f["date"].dt.to_period("Q")
    g = f.groupby("q")[["MKT", "SMB", "HML", "RMW", "CMA", "RF"]].sum().reset_index()
    g["year"] = g["q"].dt.year
    g["quarter"] = g["q"].dt.quarter
    # MKT 在 FF5 月度文件中已是超额收益(已减 RF)，命名 ff5_MKT_excess 表意更准确
    g = g.rename(columns={"MKT": "ff5_MKT_excess", "SMB": "ff5_SMB", "HML": "ff5_HML",
                          "RMW": "ff5_RMW", "CMA": "ff5_CMA", "RF": "ff5_RF"})
    return g[["year", "quarter", "ff5_MKT_excess", "ff5_SMB", "ff5_HML",
              "ff5_RMW", "ff5_CMA", "ff5_RF"]]


def _ts_alpha(y, X):
    """单基金时序回归 y = a + b·X 的截距(alpha)。y,X 已按行对齐、屏蔽 NaN。"""
    y = np.asarray(y, float); X = np.asarray(X, float)
    mask = ~(np.isnan(y) | np.isnan(X).any(axis=1))
    if mask.sum() < X.shape[1] + 5:
        return np.nan
    A = np.column_stack([np.ones(mask.sum()), X[mask]])
    beta, *_ = np.linalg.lstsq(A, y[mask], rcond=None)
    return beta[0]


def _alpha_by_fund(df, model):
    """对每只基金做时序回归求 alpha，广播回该基金所有季度。model: 'ff3'/'ff4'/'ff5'。
    注意：df(=fr) 已在 main() 中并入 FF3/FF5 因子列，故此处**不再二次 merge**
    （否则因子列会因重名被加 _x/_y 后缀而丢失）。"""
    if model == "ff3":
        Xcols = ["MKT_excess", "SMB", "HML"]
    elif model == "ff4":
        Xcols = ["MKT_excess", "SMB", "HML", "MOM"]
    else:  # ff5
        Xcols = ["ff5_MKT_excess", "ff5_SMB", "ff5_HML", "ff5_RMW", "ff5_CMA"]
    out = {}
    for fund, g in df.groupby("fund_code"):
        y = g["excess_return"].values
        X = g[Xcols].values
        a = _ts_alpha(y, X)
        out[fund] = a
    df = df.copy()
    df["alpha"] = df["fund_code"].map(out)
    return df[["fund_code", "report_date", "alpha"]]


def main():
    fr = _quarterly_returns()
    # 未来收益
    fr = fr.sort_values(["fund_code", "report_date"])
    fr["future_return"] = fr.groupby("fund_code")["quarter_return"].shift(-1)
    # FF3 因子 + rf → 超额收益
    ff3 = _ff3_factors()
    fr = fr.merge(ff3, on=["year", "quarter"], how="left")
    fr["excess_return"] = fr["quarter_return"] - fr["rf"]
    fr["abs_return"] = fr["quarter_return"].abs()
    # RG（持仓隐含收益差）
    rg = _compute_RG(fr)
    fr = fr.merge(rg, on=["fund_code", "report_date"], how="left")
    # FF5 季度因子
    ff5 = _ff5_factors_quarter()
    fr = fr.merge(ff5, on=["year", "quarter"], how="left")

    # alphas
    a3 = _alpha_by_fund(fr, "ff3").rename(columns={"alpha": "ff3_adj_return"})
    a4 = _alpha_by_fund(fr, "ff4").rename(columns={"alpha": "ff4_adj_return"})
    a5 = _alpha_by_fund(fr, "ff5").rename(columns={"alpha": "ff5_adj_return"})
    fr = (fr.merge(a3, on=["fund_code", "report_date"], how="left")
             .merge(a4, on=["fund_code", "report_date"], how="left")
             .merge(a5, on=["fund_code", "report_date"], how="left"))

    cols = ["fund_code", "report_date", "quarter_return", "future_return", "excess_return",
            "abs_return", "RG", "ff3_adj_return", "ff4_adj_return", "ff5_adj_return",
            "MKT_excess", "SMB", "HML", "MOM", "rf",
            "ff5_MKT_excess", "ff5_SMB", "ff5_HML", "ff5_RMW", "ff5_CMA", "ff5_RF"]
    out = fr[cols].copy()
    out.to_csv(os.path.join(OUT, "L6_因变量.csv"), index=False, encoding="utf-8-sig")
    print(f"   写出 output/L6_因变量.csv: {out.shape}")
    # 覆盖速览
    for c in ["quarter_return", "future_return", "excess_return", "RG",
              "ff3_adj_return", "ff4_adj_return", "ff5_adj_return"]:
        print(f"     {c:16s} 非空 {out[c].notna().sum():6d} ({out[c].notna().mean()*100:5.1f}%)  mean={out[c].mean():.4f}")


if __name__ == "__main__":
    main()
