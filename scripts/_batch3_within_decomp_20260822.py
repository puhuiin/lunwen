# -*- coding: utf-8 -*-
"""批次③组内维度（2026-08-22）：基金固定效应下的能力分解。
已有发现（截面）：RA/DE 预测选股α而非择时贡献（TM+HM 双口径复现）。
本检验：把行为变量聚合到基金-年，加基金+年份双固定效应——
  同一基金内部，DE/RA 更高的年份，其选股α/择时贡献是否更高？
意义：DE 的 A 级证据在组内维度（§4.2.4），若组内维度下 DE 仍预测选股α，
则"处置效应损害选股能力"从截面关联升级为组内（准因果方向）证据，两支最强发现闭环。
口径：1%/99% 缩尾（界取全样本）+ C(fund)+C(year) 双 FE + 基金聚类 SE（组内设计中年份维度被 FE 吸收）。
"""
import os, json, warnings
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from scipy import stats as spstats
warnings.filterwarnings("ignore")

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PANEL = os.path.join(HERE, "指标计算流水线", "output", "主分析面板_重建_含TOwind.csv")
B2TM = os.path.join(HERE, "output", "batch2_daily_factors_2026-08-21.csv")
B2HM = os.path.join(HERE, "output", "batch3_hm_factors_2026-08-22.csv")
OUTJSON = os.path.join(HERE, "output", "batch3_within_decomposition_2026-08-22.json")

def winsor(s, lo=0.01, hi=0.99):
    s = s.astype(float); a, b = s.quantile(lo), s.quantile(hi)
    return s.clip(a, b)

panel = pd.read_csv(PANEL, dtype={"fund_code": str})
panel["fund_code"] = panel["fund_code"].str.strip()
panel["year"] = pd.to_datetime(panel["report_date"]).dt.year
panel["log_aum"] = np.log(panel["avg_aum"].clip(lower=1e-9))
for v in ["log_aum","AS_improved","ICI","industry_hhi","TO_wind","ARG","return_volatility",
          "de","lsv","risk_asym"]:
    panel[v+"_w"] = winsor(panel[v])

# 基金-年聚合（均值）
agg = panel.groupby(["fund_code","year"])[[c+"_w" for c in
        ["log_aum","AS_improved","ICI","industry_hhi","TO_wind","ARG","return_volatility","de","lsv","risk_asym"]]].mean().reset_index()

def load_b(path, cols):
    b = pd.read_csv(path)
    b["fund_code"] = b["fund_code"].astype(int).astype(str)
    b["year"] = b["year"].astype(int)
    return b[["fund_code","year"]+cols]

b2 = load_b(B2TM, ["TM_alpha_annual","TM_beta2"]).merge(
     load_b(B2HM, ["HM_alpha","timing_contrib_HM"]), on=["fund_code","year"])
# 择时贡献(TM)：用批次③的窗口二阶矩重算口径
m2 = pd.read_csv(os.path.join(HERE, "output", "batch3_mkt2_window_2026-08-22.csv"))
m2["fund_code"] = m2["fund_code"].astype(str).str.strip()
m2["year"] = m2["year"].astype(int)
b2 = b2.merge(m2[["fund_code","year","mkt2_mean"]], on=["fund_code","year"], how="left")
b2["timing_contrib_TM"] = b2["TM_beta2"] * b2["mkt2_mean"] * 252.0
b2["TM_alpha_w"] = winsor(b2["TM_alpha_annual"])
b2["HM_alpha_w"] = winsor(b2["HM_alpha"])
b2["timing_TM_w"] = winsor(b2["timing_contrib_TM"])
b2["timing_HM_w"] = winsor(b2["timing_contrib_HM"])

df = agg.merge(b2[["fund_code","year","TM_alpha_w","HM_alpha_w","timing_TM_w","timing_HM_w"]],
               on=["fund_code","year"], how="inner")
print(f"基金-年样本 {len(df)} / {df['fund_code'].nunique()} 基金")

RHS = ["log_aum_w","AS_improved_w","ICI_w","industry_hhi_w","TO_wind_w","ARG_w",
       "return_volatility_w","de_w","lsv_w","risk_asym_w"]
KEY = ["de_w","lsv_w","risk_asym_w","ICI_w","TO_wind_w","ARG_w"]

def fit_within(d, dv):
    sub = d.dropna(subset=RHS + [dv]).copy()
    keep = [c for c in RHS if sub[c].std() > 1e-12]
    m = smf.ols(dv + " ~ " + " + ".join(keep) + " + C(fund_code) + C(year)", data=sub).fit()
    X = np.asarray(m.model.data.exog, float); resid = np.asarray(m.resid, float)
    groups = sub["fund_code"].values.astype(str)
    k = X.shape[1]
    XtX_inv = np.linalg.inv(X.T @ X)
    meat = np.zeros((k, k))
    for g in np.unique(groups):
        mm = groups == g
        s = X[mm].T @ resid[mm]
        meat += np.outer(s, s)
    V = XtX_inv @ meat @ XtX_inv
    se = np.sqrt(np.maximum(np.diag(V), 0))
    t2 = m.params.values / se
    p2 = 2.0 * spstats.t.sf(np.abs(t2), df=len(resid) - X.shape[1])
    names = list(m.params.index)
    out = {}
    for i, nm in enumerate(names):
        if nm in keep:
            out[nm] = dict(beta=float(m.params.values[i]), t=float(t2[i]), p=float(p2[i]),
                           stars="" if p2[i] > .10 else "*" if p2[i] > .05 else "**" if p2[i] > .01 else "***")
    return out, dict(N=int(m.nobs), nfund=int(sub["fund_code"].nunique()), r2=float(m.rsquared))

results = {"design": "基金-年聚合 + C(fund)+C(year) 双FE + 基金聚类；缩尾界取全样本"}
for dv, label in [("TM_alpha_w","组内 DV1_TM选股α"), ("HM_alpha_w","组内 DV2_HM选股α"),
                  ("timing_TM_w","组内 DV3_TM择时"), ("timing_HM_w","组内 DV4_HM择时")]:
    coefs, meta = fit_within(df, dv)
    results[label] = dict(dv=dv, meta=meta, coefs=coefs)
    print(f"\n[{label}]  N={meta['N']}  funds={meta['nfund']}  R²={meta['r2']:.4f}")
    for v in KEY:
        c = coefs.get(v)
        if c:
            print(f"   {v:20s} β={c['beta']:+.5f}  t={c['t']:+.2f}  p={c['p']:.4f}  {c['stars']}")

with open(OUTJSON, "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)
print(f"\n[out] {OUTJSON}")
