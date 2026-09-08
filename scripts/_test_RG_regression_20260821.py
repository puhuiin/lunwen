# -*- coding: utf-8 -*-
"""用正确归一(port/wsum) 的 RG（非v2=面板原RG；v2仅6/12=候选）跑 M4 同规格回归，
双向聚类 CGM2011，检验 RG 是否显著。判定到底哪个源可落地。"""
import os, numpy as np, pandas as pd, statsmodels.formula.api as smf
from scipy import stats as spstats
ROOT = "D:/Desktop/基金经理行为分析研究"
PIPE = "D:/Desktop/基金经理行为分析研究/指标计算流水线"
PANEL = f"{PIPE}/output/主分析面板_重建_含TOwind.csv"
HOLD_NONV2 = f"{PIPE}/data/L2_持仓偏离层/基金持仓明细_全量修正版.csv"
HOLD_V2 = f"{PIPE}/data/L2_持仓偏离层/基金持仓明细_全量修正版_v2.csv"
STK = f"{PIPE}/data/股价行情/个股月收益率_全量.csv"

def to_panel_date(s):
    return pd.to_datetime(s, errors="coerce") + pd.Timedelta(days=1)

sm = pd.read_csv(STK, encoding="utf-8-sig")
sm["date"] = pd.to_datetime(sm["date"], errors="coerce"); sm = sm.dropna(subset=["date"])
sm["stock_code"] = sm["stock_code"].astype(str).str.zfill(6)
sm["q"] = sm["date"].dt.to_period("Q")
g = sm.groupby(["stock_code", "q"])["monthly_return"].apply(lambda s: (1 + s.fillna(0)).prod() - 1).reset_index()
sq = {}
for (stk, q), sub in g.groupby(["stock_code", "q"]):
    sq[(q, stk)] = float(sub["monthly_return"].iloc[0])

pan = pd.read_csv(PANEL, dtype={"fund_code": str}); pan["fund_code"] = pan["fund_code"].astype(int)
pan["rd"] = to_panel_date(pan["report_date"])
pan["q"] = (pd.to_datetime(pan["report_date"]) - pd.Timedelta(days=1)).dt.to_period("Q")
fr = pan[["fund_code", "report_date", "q", "quarter_return"]].copy()

def compute_RG(hold_path, restrict_months=None):
    h = pd.read_csv(hold_path, encoding="utf-8-sig", low_memory=False)
    h["fund_code"] = h["fund_code"].astype(int)
    h["w"] = pd.to_numeric(h["hold_ratio"], errors="coerce").fillna(0) / 100.0
    h["rd"] = to_panel_date(h["report_date"]); h["q"] = h["rd"].dt.to_period("Q")
    h["stock_code"] = h["stock_code"].astype(str).str.zfill(6)
    if restrict_months is not None:
        h = h[pd.to_datetime(h["report_date"]).dt.month.isin(restrict_months)]
    rows = []
    for fund, fdf in h.groupby("fund_code"):
        fdf = fdf.sort_values("rd")
        snaps = list(zip(fdf["q"], fdf["rd"], [dict(zip(gg["stock_code"], gg["w"])) for _, gg in fdf.groupby("q")]))
        sub = fr[fr["fund_code"] == fund]
        if sub.empty: continue
        for _, r in sub.iterrows():
            q = r["q"]
            cand = [(sqp, sd, sw) for (sqp, sd, sw) in snaps if sqp <= q]
            if not cand: rows.append((fund, r["report_date"], np.nan)); continue
            wmap = cand[-1][2]
            if not wmap: rows.append((fund, r["report_date"], np.nan)); continue
            port = sum(wmap.get(stk, 0) * sq.get((q, stk), np.nan) for stk in wmap if not pd.isna(sq.get((q, stk), np.nan)))
            wsum = sum(wmap.get(stk, 0) for stk in wmap if not pd.isna(sq.get((q, stk), np.nan)))
            rg = (r["quarter_return"] - port / wsum) if (wsum and not pd.isna(port)) else np.nan
            rows.append((fund, r["report_date"], rg))
    return pd.DataFrame(rows, columns=["fund_code", "report_date", "RG"])

rg_v2sa = compute_RG(HOLD_V2, restrict_months=[6, 12]).rename(columns={"RG": "RG_v2sa"})
pan = pan.merge(rg_v2sa, on=["fund_code", "report_date"], how="left")

# ---- M4 规格 ----
CTRL = ["log_aum", "ff5_MKT_excess", "ff5_SMB", "ff5_HML", "ff5_RMW", "ff5_CMA",
        "log_fund_age", "mgr_total_tenure_v2", "AS_improved", "ICI", "industry_hhi",
        "SDI", "TO_wind", "ARG", "return_volatility", "de", "lsv", "risk_asym"]
pan["avg_aum"] = pd.to_numeric(pan["avg_aum"], errors="coerce")
pan["log_aum"] = np.log(pan["avg_aum"].clip(lower=1e-9))
for c in CTRL + ["ff5_adj_return", "future_return", "RG", "RG_v2sa"]:
    pan[c] = pd.to_numeric(pan[c], errors="coerce")
def w(s): s = s.astype(float); lo, hi = s.quantile(.01), s.quantile(.99); return s.clip(lo, hi)
for v in CTRL + ["ff5_adj_return", "future_return", "RG", "RG_v2sa"]:
    pan[v + "_w"] = w(pan[v])

def tw(X, res, a, b):
    def ow(gr):
        k = X.shape[1]; m = np.zeros((k, k))
        for gg in np.unique(gr):
            mm = gr == gg; s = X[mm].T @ res[mm]; m += np.outer(s, s)
        return m
    ab = np.array([f"{x}|{y}" for x, y in zip(a, b)])
    return ow(a) + ow(b) - ow(ab)

def st(p): return "***" if p < .01 else "**" if p < .05 else "*" if p < .1 else "n.s."

print("=== RG 显著性检验（双向聚类 CGM2011，M4 同规格）===")
for rgcol in ["RG", "RG_v2sa"]:
    print(f"\n--- 指标: {rgcol} ---")
    for dv in ["ff5_adj_return", "future_return"]:
        rhs = [r + "_w" for r in CTRL] + [rgcol + "_w"]
        d = pan.dropna(subset=rhs + [dv + "_w"]).copy()
        m = smf.ols(f"{dv}_w ~ " + " + ".join(rhs) + " + C(year)", data=d).fit(cov_type="cluster", cov_kwds={"groups": d["fund_code"]})
        X = np.asarray(m.model.data.exog, float); res = np.asarray(m.resid, float)
        V2 = tw(X, res, d["fund_code"].values.astype(str), d["year"].values.astype(str))
        se2 = np.sqrt(np.maximum(np.diag(V2), 0))
        i = [j for j, nm in enumerate(m.params.index) if nm == rgcol + "_w"][0]
        t2 = m.params.values[i] / se2[i]; p2 = 2 * spstats.t.sf(abs(t2), df=len(res) - X.shape[1])
        # 同时给出单维基金聚类(t1w)对照
        se1 = np.sqrt(np.diag(m.cov_params()))[i]; t1 = m.params.values[i] / se1; p1 = 2 * spstats.t.sf(abs(t1), df=len(res) - X.shape[1])
        print(f"  DV={dv:16s} N={int(m.nobs):5d} R²={m.rsquared:.4f}  β={m.params.values[i]:+.5f}  t2w={t2:+.2f} p2w={p2:.3f} {st(p2)}  | t1w={t1:+.2f} p1w={p1:.3f}")
