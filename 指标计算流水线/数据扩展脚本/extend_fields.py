# -*- coding: utf-8 -*-
"""
extend_fields.py — 将六个目标字段扩展覆盖至全样本（400 只基金 / 全部时间段）
========================================================================
核心思想：以「面板骨架」(output/00_面板骨架.csv, 9974 观测) 为**观测索引基准**，
对每个目标字段做三件事：
  1. 重新索引(reindex) 到全骨架 —— 缺失的观测天然变成 NaN（即「覆盖缺口」）；
  2. 若对应的「扩展数据源」已就绪（CSMAR/Wind/iFinD/外部院校），则改用该源重算，
     从而提升覆盖率；否则保留现有口径，仅做全样本对齐与统计；
  3. 输出 (a) 全样本字段长表 + (b) 覆盖率统计，供 00_run_extension 汇总。

各字段扩展策略（与需求文件一一对应）：
  TO_two_sided / OCI_two_sided (L3)
      - 现状：18%（200 只 / 9 个半年点，2021–2025），缺因需基金买卖成交额（定期报告披露），自由源不可得。
      - 扩展：若 CSMAR/Wind 双边换手率就绪，覆盖拉至 400 只 / 2006–2026 半年频；
              否则仅把现有 200 只观测对齐到全骨架（缺口显式保留）。
  de / pgr / plr (L5)
      - 现状：46%（399 只基金有值，但因 only_612=True 仅用 6/12 月半年快照，约半数季度本无 de）。
      - 扩展：保持「半年频」定义不变（de 定义上仅半年可算）；若 CSMAR/Wind 全持仓就绪，
              302/400 → 提升持仓覆盖，从而让更多基金的半年度有 de 值；否则保留现有口径。
  ICI / industry_hhi (L2)
      - 现状：43%（357 只），受 302 只基金持仓覆盖限制。
      - 扩展：用与现有 lib_metrics 完全一致的口径（th指标计算流水线/data/L2_持仓偏离层/行业集中度HHI_申万31.csv
              的 industry_hhi / hhi_normalized / ICI / ICI_normalized），重新索引到全骨架；
              若 CSMAR/Wind 全持仓就绪，重算整个区间的 ICI/hhi（口径不变：权重占净值比，行业=申万31）。
              注：ICI/DE 的「半年度限制」是监管披露约束（仅半年报/年报有全持仓），非数据缺口，报告中需说明。
  SDI (L3)
      - 现状：64%（366 只），因滚动 8 期暖机，早期无值（结构性）。
      - 扩展：保持滚动 8 期口径不变（仍是结构性暖机），重新索引到全骨架；
              扩展数据源（更长净值历史）不改变其结构性特征，仅把现有值对齐全样本。
  school (L1 控制变量)
      - 现状：46%（253 只），因基金经理毕业院校信息缺失。
      - 扩展：若外部院校补全就绪，合并进现有 school；否则保留现有口径。school 属公开信息可得性限制。
  ARG (L4)
      - 现状：96.7%（已近乎全样本），2006–2017 早期用 AKShare 稀疏持仓 + 108 股子集。
      - 扩展：保持现有口径（已很高），重新索引到全骨架；若个股收益补全到位，ARG 在 2006–2017 的
              覆盖会进一步改善（但本模块不强制依赖 AKShare 在线抓取，离线回退现有文件）。

所有函数返回「全样本对齐后的 DataFrame」（fund_code, report_date, <字段>），
缺失处为 NaN —— 这正是「扩展覆盖至全样本」的精确含义：全观测索引 + 明确的缺失标记。
"""
import os
import warnings
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA = os.environ.get("LIB_DATA", os.path.join(BASE_DIR, "..", "data"))


def D(*p):
    return os.path.join(DATA, *p)


# 申万31 行业映射文件
SW31_FILE = D("L2_持仓偏离层", "股票行业映射.csv")
HHI_FILE = D("L2_持仓偏离层", "行业集中度HHI_申万31.csv")
HOLD_FILE = D("L2_持仓偏离层", "基金持仓明细_全量修正版_v2.csv")


def _reindex(df, skeleton, value_cols):
    """把 df(fund_code, report_date, value_cols) 重新索引到全骨架，缺失→NaN。"""
    sk = skeleton[["fund_code", "report_date"]].copy()
    sk["report_date"] = pd.to_datetime(sk["report_date"], errors="coerce")
    d = df.copy()
    d["report_date"] = pd.to_datetime(d["report_date"], errors="coerce")
    d["fund_code"] = d["fund_code"].astype(str).str.zfill(6)
    sk["fund_code"] = sk["fund_code"].astype(str).str.zfill(6)
    out = sk.merge(d, on=["fund_code", "report_date"], how="left")
    return out[["fund_code", "report_date"] + value_cols]


def _reindex_yq(df, skeleton, value_cols):
    """按 (fund_code, year, quarter) 稳健连接骨架 —— 绕开 report_date ±1 天约定脆弱性。
    返回骨架的 report_date（+1 天面板口径），保证后续横向合并一致。"""
    key = skeleton[["fund_code", "year", "quarter", "report_date"]].drop_duplicates()
    key["fund_code"] = key["fund_code"].astype(str).str.zfill(6)
    key["report_date"] = pd.to_datetime(key["report_date"], errors="coerce")
    d = df.copy()
    d["fund_code"] = d["fund_code"].astype(str).str.zfill(6)
    out = key.merge(d, on=["fund_code", "year", "quarter"], how="left")
    return out[["fund_code", "report_date", "year", "quarter"] + value_cols]


def _panel_date(s):
    dt = pd.to_datetime(s, errors="coerce")
    return dt + pd.Timedelta(days=1)


# ============================================================
# TO_two_sided / OCI_two_sided
# ============================================================
def extend_turnover(skeleton, src=None):
    """扩展双边换手率至全样本。
    src: 来自 lib_data_sources.load_turnover_csmar_wind 的标准表；
         若为 None（CSMAR/Wind 未就绪），则回退到现有 基金换手率_双边_含卖出.csv（200 只口径）。"""
    if src is None:
        p = D("L3_交易行为层", "基金换手率_双边_含卖出.csv")
        if not os.path.exists(p):
            return None, "现有双边换手率文件缺失"
        df = pd.read_csv(p, encoding="utf-8-sig")
        df["report_date"] = df["report_date"].apply(_panel_date)
        if "TO_two_sided" not in df.columns:
            df["TO_two_sided"] = (df["total_buy"] + df["total_sell"]) / (2.0 * df["avg_aum"].replace(0, np.nan))
        g = df.groupby("fund_code")["TO_two_sided"]
        df["OCI_two_sided"] = (df["TO_two_sided"] - g.transform("mean")) / g.transform("std")
        val = ["TO_two_sided", "OCI_two_sided"]
        return _reindex(df[["fund_code", "report_date"] + val], skeleton, val), None
    # 使用 CSMAR/Wind 扩展源（覆盖 400 只 / 2006–2026）
    g = src.groupby("fund_code")["TO_two_sided"]
    src = src.copy()
    src["OCI_two_sided"] = (src["TO_two_sided"] - g.transform("mean")) / g.transform("std")
    val = ["TO_two_sided", "OCI_two_sided"]
    return _reindex(src[["fund_code", "report_date"] + val], skeleton, val), None


# ============================================================
# de / pgr / plr
# ============================================================
def extend_de(skeleton, full_holdings=None, only_612=True):
    """扩展处置效应 de=pgr-plr 至全样本（保持半年频定义）。

    直接复用现有 lib_metrics.calc_de(only_612=True) 成品（已验证 de 非空 5217 行 ≈46.3%），
    其 report_date 已是 +1 天面板口径，可直接对齐骨架。
    full_holdings: 若提供 CSMAR/Wind 全季度全持仓，应将其落盘覆盖 HOLD_FILE 后再跑
                  （calc_de 固定读取 HOLD_FILE），从而把持仓覆盖从 302 只提升至 400 只。"""
    import sys
    sys.path.insert(0, os.path.join(BASE_DIR, ".."))
    import lib_metrics as M
    if full_holdings is not None:
        # 用户将 CSMAR/Wind 全持仓落盘到 HOLD_FILE 路径后再调用本函数即可；
        # 此处不重复实现，保证与现有口径严格一致。
        full_holdings.to_csv(HOLD_FILE, encoding="utf-8-sig", index=False)
    df = M.calc_de(only_612=only_612)
    val = ["de", "pgr", "plr"]
    return _reindex(df[["fund_code", "report_date"] + val], skeleton, val), None


# ============================================================
# ICI / industry_hhi  —— 口径严格对齐现有 lib_metrics（已反推验证）
# ============================================================
def _load_sw_map():
    m = pd.read_csv(SW31_FILE, encoding="utf-8-sig")
    m["stock_code"] = m["stock_code"].astype(str).str.zfill(6)
    return dict(zip(m["stock_code"], m["sw31_industry"]))


def _compute_ici_hhi_from_holdings(hold):
    """从股票级持仓重算 ICI / industry_hhi（口径与现有 HHI 文件一致）：
      w_raw = hold_ratio/100  （占净值比，未归一）
      industry_hhi  = Σ(w_raw)²                （原始 NAV 权重 HHI）
      hhi_normalized= industry_hhi / (Σw_raw)² （权重归一化 Σ=1）
      ICI  = Σ_i (w_i − 1/31)²                 （与 31 行业等权基准的偏离平方和）
      ICI_normalized = ICI / (Σw_raw)²         （同上，除以总权重平方 → 归一化）
    其中 i 遍历该基金-期持有的申万31行业；未持有的行业 w_i=0 仍参与偏离平方和（等权基准 1/31）。"""
    cod2sw = _load_sw_map()
    h = hold.copy()
    h["stock_code"] = h["stock_code"].astype(str).str.zfill(6)
    h["w_raw"] = pd.to_numeric(h["hold_ratio"], errors="coerce").fillna(0) / 100.0
    h["sw"] = h["stock_code"].map(cod2sw)
    h = h.dropna(subset=["sw"])
    h["rd"] = pd.to_datetime(h["report_date"], errors="coerce")
    h["year"] = h["rd"].dt.year
    h["quarter"] = h["rd"].dt.month.map({3: 1, 6: 2, 9: 3, 12: 4})
    N31 = 31
    rows = []
    for (fund, rd), g in h.groupby(["fund_code", "rd"]):
        Sw = g["w_raw"].sum()
        # 行业聚合（原始权重）
        ind = g.groupby("sw")["w_raw"].sum()
        # industry_hhi
        hhi_raw = (g["w_raw"] ** 2).sum()
        hhi_norm = hhi_raw / (Sw ** 2) if Sw else np.nan
        # ICI: 遍历全部31行业，未持有记 w=0（等权基准 Sw/31，与现有口径一致）
        ici = 0.0
        for s in set(cod2sw.values()):
            w = ind.get(s, 0.0)
            ici += (w - Sw / N31) ** 2
        ici_norm = ici / (Sw ** 2) if Sw else np.nan
        q = {3: 1, 6: 2, 9: 3, 12: 4}[rd.month]
        rows.append((fund, rd.year, q, hhi_raw, hhi_norm, ici, ici_norm))
    out = pd.DataFrame(rows, columns=["fund_code", "year", "quarter",
                                       "industry_hhi", "hhi_normalized", "ICI", "ICI_normalized"])
    return out


def extend_ici_hhi(skeleton, full_holdings=None):
    """扩展 ICI / industry_hhi 至全样本。

    严谨口径（与需求一致）：ICI / industry_hhi **仅能在半年报/年报全持仓快照上计算**
    （quarter∈{2,4}），Q1/Q3 仅有前十大持仓，算出的集中度会系统性低估，方法上不等价，
    必须排除——因此本函数**默认只保留半年频观测**，缺失处显式留空（非缺口，是定义性约束）。

    默认：复用现有 行业集中度HHI_申万31.csv 中**半年报/年报**行（ICI_normalized /
    hhi_normalized 已与原始口径反推校验一致），按 (fund_code, year, quarter) 稳健连接骨架。
    若提供 CSMAR/Wind 全持仓，则对**整个区间的半年频**重算（口径不变），扩展到 400 只。
    """
    if full_holdings is None:
        hhi = pd.read_csv(HHI_FILE, encoding="utf-8-sig")
        # 仅保留半年报/年报全持仓（quarter∈{2,4}），剔除 Q1/Q3 前十大持仓的失真值
        hhi = hhi[hhi["quarter"].isin([2, 4])].copy()
        sel = hhi[["fund_code", "year", "quarter", "ICI_normalized", "hhi_normalized"]].rename(
            columns={"ICI_normalized": "ICI", "hhi_normalized": "industry_hhi"})
    else:
        h = full_holdings.copy()
        h["report_date"] = pd.to_datetime(h["report_date"], errors="coerce")
        h = h[h["report_date"].dt.month.isin([6, 12])]   # 全持仓仅在半年报/年报
        comp = _compute_ici_hhi_from_holdings(h)
        sel = comp[["fund_code", "year", "quarter", "ICI", "industry_hhi"]]
    return _reindex_yq(sel, skeleton, ["ICI", "industry_hhi"]), None


# ============================================================
# SDI
# ============================================================
def extend_sdi(skeleton, window=8):
    """扩展 SDI 至全样本（保持滚动 8 期暖机口径 —— 早期缺失为结构性，非数据缺口）。"""
    # 复用 lib_metrics.calc_sdi 的结果（已算），重新索引到全骨架
    import sys
    sys.path.insert(0, os.path.join(BASE_DIR, ".."))
    import lib_metrics as M
    df = M.calc_sdi(window=window)
    return _reindex(df, skeleton, ["SDI"]), None


# ============================================================
# school
# ============================================================
def extend_school(skeleton, school_ext=None):
    """扩展 school（基金经理毕业院校）至全样本。
    school_ext: 来自 lib_data_sources.load_school_external 的外部补全表，按 manager_id 合并；
                若 None，则保留现有 lib_metrics.calc_control_vars 口径（253/400 只）。"""
    import sys
    sys.path.insert(0, os.path.join(BASE_DIR, ".."))
    import lib_metrics as M
    sk = skeleton[["fund_code", "report_date"]].copy()
    sk["report_date"] = pd.to_datetime(sk["report_date"], errors="coerce")
    cv = M.calc_control_vars(sk)            # 现有 school/education/gender/CFA
    if school_ext is not None:
        # 外部补全按 manager_id 合并（尽量补齐缺失院校）
        info_cols = [c for c in school_ext.columns if c in ("manager_id", "school")]
        ext_map = school_ext[info_cols].dropna(subset=["school"]).drop_duplicates("manager_id")
        cv = cv.merge(ext_map, on="manager_id", how="left", suffixes=("", "_ext"))
        cv["school"] = cv["school"].fillna(cv["school_ext"])
        cv = cv.drop(columns=["school_ext"], errors="ignore")
    val = ["school"]
    out = cv[["fund_code", "report_date"] + val]
    return _reindex(out, skeleton, val), None


# ============================================================
# ARG
# ============================================================
def extend_arg(skeleton):
    """扩展 ARG 至全样本（现状已 96.7%，近乎全样本）。

    直接复用现有流水线已算好的权威 ARG（output/L4_风险应对.csv），避免重复执行
    高内存占用的 calc_arg（其需构建 股票×月 全量 pivot）。若现有文件缺失再回退重算。
    """
    l4 = os.path.join(BASE_DIR, "..", "output", "L4_风险应对.csv")
    if os.path.exists(l4):
        df = pd.read_csv(l4, encoding="utf-8-sig", usecols=["fund_code", "report_date", "ARG"])
        # L4 的 report_date 已是 +1 天面板口径，直接对齐骨架（切勿再叠加 _panel_date）
        return _reindex(df, skeleton, ["ARG"]), None
    # 回退：重算（联网/高内存环境）
    import sys
    sys.path.insert(0, os.path.join(BASE_DIR, ".."))
    import lib_metrics as M
    df = M.calc_arg()
    return _reindex(df, skeleton, ["ARG"]), None


if __name__ == "__main__":
    import lib_data_sources as S
    sk = S.load_skeleton()
    print("骨架:", len(sk), "obs")
    for name, fn in [("TO", lambda: extend_turnover(sk)),
                     ("DE", lambda: extend_de(sk)),
                     ("ICI/HHI", lambda: extend_ici_hhi(sk)),
                     ("SDI", lambda: extend_sdi(sk)),
                     ("school", lambda: extend_school(sk)),
                     ("ARG", lambda: extend_arg(sk))]:
        df, r = fn()
        cov = df[["de", "pgr", "plr", "ICI", "industry_hhi", "SDI", "school", "ARG", "TO_two_sided"]
                 ].notna().any(axis=1).mean() if df is not None else 0
        print(f"[{name}] 全样本行={len(df) if df is not None else 0}, 就绪={r is None}")
