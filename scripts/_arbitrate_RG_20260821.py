# -*- coding: utf-8 -*-
"""RG 数据源仲裁：精确复刻 06_因变量._compute_RG 逻辑（含 to_panel_date +1天、q<=r[q] 快照选择、
port/wsum 归一），对两个持仓文件分别计算，并与面板原 RG 交叉验证。

目标：
  (1) 用 non-v2 重算 RG，应≈面板 RG（sanity，验证复刻正确）；
  (2) 用 v2(仅6/12全持仓) 重算 RG，与原 RG / non-v2 重算 比较，定根因。
"""
import os, numpy as np, pandas as pd
ROOT = "D:/Desktop/基金经理行为分析研究"
PIPE = "D:/Desktop/基金经理行为分析研究/指标计算流水线"
PANEL = f"{PIPE}/output/主分析面板_重建_含TOwind.csv"
HOLD_NONV2 = f"{PIPE}/data/L2_持仓偏离层/基金持仓明细_全量修正版.csv"
HOLD_V2 = f"{PIPE}/data/L2_持仓偏离层/基金持仓明细_全量修正版_v2.csv"
STK = f"{PIPE}/data/股价行情/个股月收益率_全量.csv"

def to_panel_date(s):
    dt = pd.to_datetime(s, errors="coerce")
    return dt + pd.Timedelta(days=1)

# 个股季度收益，键 (q_period, stk)，完全照 06_因变量._stock_quarter_return
sm = pd.read_csv(STK, encoding="utf-8-sig")
sm["date"] = pd.to_datetime(sm["date"], errors="coerce")
sm = sm.dropna(subset=["date"])
sm["stock_code"] = sm["stock_code"].astype(str).str.zfill(6)
sm["q"] = sm["date"].dt.to_period("Q")
g = sm.groupby(["stock_code", "q"])["monthly_return"].apply(lambda s: (1 + s.fillna(0)).prod() - 1).reset_index()
sq = {}
for (stk, q), sub in g.groupby(["stock_code", "q"]):
    sq[(q, stk)] = float(sub["monthly_return"].iloc[0])

# fr：与面板一致（面板 quarter_return 即 06 的 fr 输出），统一 fund_code 为 int
pan = pd.read_csv(PANEL, dtype={"fund_code": str})
pan["fund_code"] = pan["fund_code"].astype(int)
pan["rd"] = to_panel_date(pan["report_date"])
# 真实基金季度 = 季度末(report_date - 1天) 所在季度；与 06 的 NAV 派生 q 一致
pan["q"] = (pd.to_datetime(pan["report_date"]) - pd.Timedelta(days=1)).dt.to_period("Q")
pan = pan.rename(columns={"fund_code": "fund_code_int"})
fr = pan[["fund_code_int", "report_date", "q", "quarter_return"]].copy()
fr["fund_code"] = fr["fund_code_int"]

def compute_RG(hold_path, restrict_months=None):
    """精确复刻 06_因变量._compute_RG。restrict_months: 仅保留这些月份快照（None=全部）。"""
    h = pd.read_csv(hold_path, encoding="utf-8-sig", low_memory=False)
    h["fund_code"] = h["fund_code"].astype(int)
    h["w"] = pd.to_numeric(h["hold_ratio"], errors="coerce").fillna(0) / 100.0
    h["rd"] = to_panel_date(h["report_date"])
    h["q"] = h["rd"].dt.to_period("Q")
    h["stock_code"] = h["stock_code"].astype(str).str.zfill(6)
    if restrict_months is not None:
        h = h[pd.to_datetime(h["report_date"]).dt.month.isin(restrict_months)]
    rows = []
    for fund, fdf in h.groupby("fund_code"):
        fdf = fdf.sort_values("rd")
        snaps = list(zip(fdf["q"], fdf["rd"],
                         [dict(zip(gg["stock_code"], gg["w"])) for _, gg in fdf.groupby("q")]))
        sub = fr[fr["fund_code"] == fund]
        if sub.empty:
            continue
        for _, r in sub.iterrows():
            q = r["q"]
            cand = [(sqp, sd, sw) for (sqp, sd, sw) in snaps if sqp <= q]
            if not cand:
                rows.append((fund, r["report_date"], np.nan)); continue
            wmap = cand[-1][2]
            if not wmap:
                rows.append((fund, r["report_date"], np.nan)); continue
            port = sum(wmap.get(stk, 0) * sq.get((q, stk), np.nan)
                       for stk in wmap if not pd.isna(sq.get((q, stk), np.nan)))
            wsum = sum(wmap.get(stk, 0) for stk in wmap if not pd.isna(sq.get((q, stk), np.nan)))
            if wsum and not pd.isna(port):
                port = port / wsum
                rg = r["quarter_return"] - port
            else:
                rg = np.nan
            rows.append((fund, r["report_date"], rg))
    return pd.DataFrame(rows, columns=["fund_code", "report_date", "RG"])

print("计算非v2 RG(精确复刻)...")
rg_orig = compute_RG(HOLD_NONV2)
print("计算 v2 RG(仅6/12全持仓)...")
rg_v2sa = compute_RG(HOLD_V2, restrict_months=[6, 12])

# 合并到面板
m = pan[["fund_code_int", "report_date", "RG", "quarter_return"]].copy()
m = m.rename(columns={"fund_code_int": "fund_code"})
m = m.merge(rg_orig.rename(columns={"RG": "RG_recomp"}), on=["fund_code", "report_date"], how="left")
m = m.merge(rg_v2sa.rename(columns={"RG": "RG_v2sa"}), on=["fund_code", "report_date"], how="left")

def corr_report(a, b):
    s = m.dropna(subset=[a, b])
    if len(s) < 10:
        return f"N={len(s)} (样本过少)"
    c = s[[a, b]].corr().iloc[0, 1]
    return f"N={len(s)}  corr={c:+.3f}"

print("\n=== 仲裁结果 ===")
print(f"[Sanity] 面板RG  vs  非v2重算RG : {corr_report('RG', 'RG_recomp')}")
print(f"[仲裁A] 面板RG  vs  v2(6/12)RG  : {corr_report('RG', 'RG_v2sa')}")
print(f"[仲裁B] 非v2重算 vs  v2(6/12)   : {corr_report('RG_recomp', 'RG_v2sa')}")

# 覆盖统计
print("\n=== 覆盖统计 ===")
print(f"面板 RG 非空: {m['RG'].notna().sum()}")
print(f"非v2重算 非空: {m['RG_recomp'].notna().sum()}")
print(f"v2(6/12) 非空: {m['RG_v2sa'].notna().sum()}")
print(f"非v2重算 与 面板RG 同时非空: {m.dropna(subset=['RG','RG_recomp']).shape[0]}")
print(f"v2(6/12) 与 面板RG 同时非空: {m.dropna(subset=['RG','RG_v2sa']).shape[0]}")
print(f"v2(6/12) 与 非v2重算 同时非空: {m.dropna(subset=['RG_recomp','RG_v2sa']).shape[0]}")

# 基金覆盖
nf_orig = set(rg_orig["fund_code"].unique())
nf_v2 = set(rg_v2sa["fund_code"].unique())
print(f"\n非v2 基金数: {len(nf_orig)}    v2(6/12) 基金数: {len(nf_v2)}")
print(f"共同基金数: {len(nf_orig & nf_v2)}    仅v2新增: {len(nf_v2 - nf_orig)}    仅非v2: {len(nf_orig - nf_v2)}")

# 描述统计
print("\n=== 描述统计（同时非空的子集）===")
for a, lbl in [("RG", "面板RG"), ("RG_recomp", "非v2重算"), ("RG_v2sa", "v2(6/12)")]:
    s = m[a].dropna()
    print(f"  {lbl:12s} n={len(s):5d}  mean={s.mean():+.4f}  std={s.std():.4f}  min={s.min():.4f}  max={s.max():.4f}")
