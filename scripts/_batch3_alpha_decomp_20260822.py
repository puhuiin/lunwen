# -*- coding: utf-8 -*-
"""批次③（路径 C，2026-08-22）：alpha 分解——行为指标预测"哪种能力"？

分解（每个基金-年，与批次②同窗口：前1年+当年，≥200 交易日）：
  选股α   = TM 回归截距年化（TM_alpha_annual，批次②已产出）
  择时贡献 = TM_β₂ × E[(r_m−r_f)²] × 252（本脚本在同一窗口补算二阶矩）

三组回归（DV 不同，RHS 相同；CGM2011 双向聚类 + C(year) FE + 1%/99% 缩尾，
完全对齐 v4 权威口径；DV 已是风险调整量，故 RHS 不含 FF5 因子列；SDI 结构零剔除）：
  DV1 = TM_alpha_annual   （选股能力）
  DV2 = timing_contrib     （择时贡献）
  DV3 = ff5_adj_return     （总α 参照，M4 主口径 DV）
核心问题：RA / DE / LSV 的预测力来自选股α还是择时α？
"""
import os, json, warnings
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from scipy import stats as spstats
warnings.filterwarnings("ignore")

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NAVPATH = os.path.join(HERE, "归档", "旧版数据", "fund_nav_new200.csv")
FF5PATH = os.path.join(HERE, "指标计算流水线", "data", "FF因子", "FF5日度因子.csv")
PANEL = os.path.join(HERE, "指标计算流水线", "output", "主分析面板_重建_含TOwind.csv")
BATCH2 = os.path.join(HERE, "output", "batch2_daily_factors_2026-08-21.csv")
OUTJSON = os.path.join(HERE, "output", "batch3_alpha_decomposition_2026-08-22.json")
OUTM2 = os.path.join(HERE, "output", "batch3_mkt2_window_2026-08-22.csv")

# ---------- CGM2011 双向聚类（v4 权威口径） ----------
def _meat(groups, X, resid):
    k = X.shape[1]; meat = np.zeros((k, k))
    for gg in np.unique(groups):
        m = groups == gg
        s = X[m].T @ resid[m]
        meat += np.outer(s, s)
    return meat
def _oneway_V(X, resid, groups):
    XtX_inv = np.linalg.inv(X.T @ X)
    return XtX_inv @ _meat(groups, X, resid) @ XtX_inv
def two_way_V(X, resid, g1, g2):
    g12 = np.array([f"{a}|{b}" for a, b in zip(g1, g2)])
    return _oneway_V(X, resid, g1) + _oneway_V(X, resid, g2) - _oneway_V(X, resid, g12)
def winsor(s, lo=0.01, hi=0.99):
    s = s.astype(float); a, b = s.quantile(lo), s.quantile(hi)
    return s.clip(a, b)

# ---------- 1. 同窗口补算 E[(r_m−r_f)²] ----------
nav = pd.read_csv(NAVPATH, parse_dates=["date"])
ff5 = pd.read_csv(FF5PATH, parse_dates=["date"])
panel = pd.read_csv(PANEL, dtype={"fund_code": str})
panel["fund_code"] = panel["fund_code"].astype(str).str.strip()
panel["year"] = pd.to_datetime(panel["report_date"]).dt.year
panel_funds = set(panel["fund_code"].unique()); years = sorted(panel["year"].unique())

nav = nav[nav["fund_code"].isin([int(f) for f in panel_funds if str(f).isdigit()])].copy()
nav["fund_code"] = nav["fund_code"].astype(int).astype(str)
nav["daily_return"] = pd.to_numeric(nav["daily_return"], errors="coerce")
nav["daily_return"] = nav["daily_return"].where(nav["daily_return"].abs() <= 50, np.nan)
nav = nav.dropna(subset=["daily_return"]); nav["year"] = nav["date"].dt.year
nav["daily_return"] = nav["daily_return"] / 100.0
ff5 = ff5.sort_values("date").reset_index(drop=True)
ff5["MKT_excess"] = ff5["MKT"]
merged = nav.merge(ff5[["date", "MKT_excess", "RF"]], on="date", how="inner")
merged["excess"] = merged["daily_return"] - merged["RF"]
merged = merged.dropna(subset=["excess", "MKT_excess"]).copy()

rows = []
for fund, g in merged.groupby("fund_code"):
    g = g.sort_values("date")
    for yr in years:
        w = g[(g["date"] >= f"{yr-1}-01-01") & (g["date"] <= f"{yr}-12-31")]
        if len(w) < 200:
            continue
        rows.append(dict(fund_code=fund, year=yr,
                         mkt2_mean=float((w["MKT_excess"] ** 2).mean()), n_days=len(w)))
m2 = pd.DataFrame(rows)
m2.to_csv(OUTM2, index=False)
print(f"[1] 窗口二阶矩 {len(m2):,} 基金-年 / {m2['fund_code'].nunique()} 基金")

# ---------- 2. 合并面板与批次②变量 ----------
b2 = pd.read_csv(BATCH2)  # fund_code 为 int
b2["fund_code"] = b2["fund_code"].astype(int).astype(str)
b2["year"] = b2["year"].astype(int)
b2 = b2.merge(m2, on=["fund_code", "year"], how="left")
b2["timing_contrib"] = b2["TM_beta2"] * b2["mkt2_mean"] * 252.0   # 年化择时贡献
b2["timing_contrib_w"] = winsor(b2["timing_contrib"])
b2["TM_alpha_w"] = winsor(b2["TM_alpha_annual"])
print(f"[2] timing_contrib: n={b2['timing_contrib'].notna().sum()}  mean={b2['timing_contrib'].mean():+.5f}  std={b2['timing_contrib'].std():.5f}")
print(f"    corr(选股α, 择时贡献) = {b2[['TM_alpha_w','timing_contrib_w']].dropna().corr().iloc[0,1]:+.4f}")
print(f"    corr(择时贡献, TM_beta2) = {b2[['TM_beta2','timing_contrib_w']].dropna().corr().iloc[0,1]:+.4f}")

panel["log_aum"] = np.log(panel["avg_aum"].clip(lower=1e-9))
PANELV = ["log_aum","log_fund_age","mgr_total_tenure_v2","AS_improved","ICI","industry_hhi",
          "TO_wind","ARG","return_volatility","de","lsv","risk_asym","ff5_adj_return"]
for v in PANELV:
    panel[v+"_w"] = winsor(panel[v])
df = panel.merge(b2[["fund_code","year","TM_alpha_w","timing_contrib_w"]],
                 on=["fund_code","year"], how="inner")
print(f"[3] 合并后 {len(df):,} 基金-季度 / {df['fund_code'].nunique()} 基金")

# ---------- 3. 三组回归 ----------
RHS = ["log_aum","log_fund_age","mgr_total_tenure_v2","AS_improved","ICI","industry_hhi",
       "TO_wind","ARG","return_volatility","de","lsv","risk_asym"]
RHS_W = [c + "_w" for c in RHS]
KEYVARS = ["risk_asym","de","lsv","AS_improved","ICI","ARG","TO_wind","return_volatility"]

def fit_dv(d, dv):
    sub = d.dropna(subset=RHS_W + [dv]).copy()
    keep = [c for c in RHS_W if sub[c].std() > 1e-12]
    m = smf.ols(dv + " ~ " + " + ".join(keep) + " + C(year)", data=sub).fit()
    X = np.asarray(m.model.data.exog, float); resid = np.asarray(m.resid, float)
    V = two_way_V(X, resid, sub["fund_code"].values.astype(str), sub["year"].values.astype(str))
    se = np.sqrt(np.maximum(np.diag(V), 0))
    t2 = m.params.values / se
    p2 = 2.0 * spstats.t.sf(np.abs(t2), df=len(resid) - X.shape[1])
    names = list(m.params.index)
    out = {}
    for i, nm in enumerate(names):
        if nm == "Intercept" or nm.startswith("C(year)"):
            continue
        out[nm[:-2] if nm.endswith("_w") else nm] = dict(
            beta=float(m.params.values[i]), se=float(se[i]), t=float(t2[i]), p=float(p2[i]),
            stars="" if p2[i] > .10 else "*" if p2[i] > .05 else "**" if p2[i] > .01 else "***")
    meta = dict(N=int(m.nobs), nfund=int(sub["fund_code"].nunique()), r2=float(m.rsquared))
    return out, meta

results = {"dvs_describe": {
    "TM_alpha_w": dict(mean=float(b2["TM_alpha_w"].mean()), std=float(b2["TM_alpha_w"].std())),
    "timing_contrib_w": dict(mean=float(b2["timing_contrib_w"].mean()), std=float(b2["timing_contrib_w"].std())),
    "corr_alpha_timing": float(b2[["TM_alpha_w","timing_contrib_w"]].dropna().corr().iloc[0,1]),
    "corr_timing_beta2": float(b2[["TM_beta2","timing_contrib_w"]].dropna().corr().iloc[0,1])}}

for dv, label in [("TM_alpha_w","DV1_选股α"), ("timing_contrib_w","DV2_择时贡献"), ("ff5_adj_return_w","DV3_总α_参照")]:
    coefs, meta = fit_dv(df, dv)
    results[label] = dict(dv=dv, meta=meta, coefs=coefs)
    print(f"\n[{label}]  dv={dv}  N={meta['N']}  funds={meta['nfund']}  R²={meta['r2']:.4f}")
    for v in KEYVARS:
        c = coefs.get(v)
        if c:
            print(f"   {v:18s} β={c['beta']:+.5f}  se={c['se']:.5f}  t2w={c['t']:+.2f}  p={c['p']:.4f}  {c['stars']}")

with open(OUTJSON, "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)
print(f"\n[out] {OUTJSON}")
