# -*- coding: utf-8 -*-
"""批次③稳健性复验（2026-08-22）：HM 口径的能力分解。
批次③发现（TM 口径）：RA/DE 的预测力全部来自选股α（t=+5.12***/−3.03***），
择时贡献维度不显著。审稿人必问：换 Henriksson-Merton（分段）设定是否成立？
本脚本以 HM 模型重做同一分解：
  HM: r_p − r_f = α + β·MKT + β₂·max(MKT,0) + ε
  选股α   = HM 截距年化（HM_alpha_w）
  择时贡献 = β₂ × E[max(rm,0)] × 252（timing_contrib_HM_w）
窗口/清洗/缩尾/聚类与批次③完全一致（前1年+当年，≥200交易日）。
判读：若 RA 在 HM 选股α上显著为正、在 HM 择时贡献上不显著 → 双分离稳健。
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
OUTCSV = os.path.join(HERE, "output", "batch3_hm_factors_2026-08-22.csv")
OUTJSON = os.path.join(HERE, "output", "batch3_hm_decomposition_2026-08-22.json")

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

# ---------- 1. HM 因子（同窗口） ----------
nav = pd.read_csv(NAVPATH, parse_dates=["date"])
ff5 = pd.read_csv(FF5PATH, parse_dates=["date"])
panel = pd.read_csv(PANEL, dtype={"fund_code": str})
panel["fund_code"] = panel["fund_code"].str.strip()
panel["year"] = pd.to_datetime(panel["report_date"]).dt.year
panel_funds = set(panel["fund_code"].unique()); years = sorted(panel["year"].unique())

nav = nav[nav["fund_code"].isin([int(f) for f in panel_funds if str(f).isdigit()])].copy()
nav["fund_code"] = nav["fund_code"].astype(int).astype(str)
nav["daily_return"] = pd.to_numeric(nav["daily_return"], errors="coerce")
nav["daily_return"] = nav["daily_return"].where(nav["daily_return"].abs() <= 50, np.nan)
nav = nav.dropna(subset=["daily_return"])
nav["daily_return"] = nav["daily_return"] / 100.0
ff5 = ff5.sort_values("date").reset_index(drop=True)
ff5["MKT_excess"] = ff5["MKT"]
ff5["MKT_up"] = np.maximum(ff5["MKT_excess"], 0.0)
merged = nav.merge(ff5[["date", "MKT_excess", "MKT_up", "RF"]], on="date", how="inner")
merged["excess"] = merged["daily_return"] - merged["RF"]
merged = merged.dropna(subset=["excess", "MKT_excess", "MKT_up"]).copy()

rows = []
for fund, g in merged.groupby("fund_code"):
    g = g.sort_values("date")
    for yr in years:
        w = g[(g["date"] >= f"{yr-1}-01-01") & (g["date"] <= f"{yr}-12-31")]
        n = len(w)
        if n < 200:
            continue
        yv = w["excess"].values
        X = np.column_stack([np.ones(n), w["MKT_excess"].values, w["MKT_up"].values])
        try:
            beta, *_ = np.linalg.lstsq(X, yv, rcond=None)
        except Exception:
            continue
        m_up = float(w["MKT_up"].mean())
        rows.append(dict(fund_code=fund, year=yr, HM_alpha=float(beta[0] * 252.0),
                         HM_beta2=float(beta[2]), mkt_up_mean=m_up,
                         timing_contrib_HM=float(beta[2] * m_up * 252.0), n_days=n))
hm = pd.DataFrame(rows)
for c in ["HM_alpha", "timing_contrib_HM"]:
    hm[c + "_w"] = winsor(hm[c])
hm.to_csv(OUTCSV, index=False)
print(f"[1] HM 因子 {len(hm):,} 基金-年 / {hm['fund_code'].nunique()} 基金")
print(f"    corr(HM选股α, HM择时贡献) = {hm[['HM_alpha_w','timing_contrib_HM_w']].dropna().corr().iloc[0,1]:+.4f}")

# ---------- 2. 合并面板并回归 ----------
panel["log_aum"] = np.log(panel["avg_aum"].clip(lower=1e-9))
PANELV = ["log_aum","log_fund_age","mgr_total_tenure_v2","AS_improved","ICI","industry_hhi",
          "TO_wind","ARG","return_volatility","de","lsv","risk_asym","ff5_adj_return"]
for v in PANELV:
    panel[v+"_w"] = winsor(panel[v])
df = panel.merge(hm[["fund_code","year","HM_alpha_w","timing_contrib_HM_w"]],
                 on=["fund_code","year"], how="inner")
RHS_W = [c+"_w" for c in ["log_aum","log_fund_age","mgr_total_tenure_v2","AS_improved","ICI","industry_hhi",
                          "TO_wind","ARG","return_volatility","de","lsv","risk_asym"]]
KEYVARS = ["risk_asym","de","lsv","ICI","ARG","TO_wind"]

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
            beta=float(m.params.values[i]), t=float(t2[i]), p=float(p2[i]),
            stars="" if p2[i] > .10 else "*" if p2[i] > .05 else "**" if p2[i] > .01 else "***")
    return out, dict(N=int(m.nobs), nfund=int(sub["fund_code"].nunique()), r2=float(m.rsquared))

results = {"model": "HM: rp-rf = α + β·MKT + β₂·max(MKT,0) + ε; 窗口/缩尾/聚类同批次③",
           "corr_alpha_timing": float(hm[["HM_alpha_w","timing_contrib_HM_w"]].dropna().corr().iloc[0,1])}
for dv, label in [("HM_alpha_w","DV1_HM选股α"), ("timing_contrib_HM_w","DV2_HM择时贡献"), ("ff5_adj_return_w","DV3_总α_参照")]:
    coefs, meta = fit_dv(df, dv)
    results[label] = dict(dv=dv, meta=meta, coefs=coefs)
    print(f"\n[{label}]  N={meta['N']}  funds={meta['nfund']}  R²={meta['r2']:.4f}")
    for v in KEYVARS:
        c = coefs.get(v)
        if c:
            print(f"   {v:12s} β={c['beta']:+.5f}  t2w={c['t']:+.2f}  p={c['p']:.4f}  {c['stars']}")

with open(OUTJSON, "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)
print(f"\n[out] {OUTCSV}\n[out] {OUTJSON}")
