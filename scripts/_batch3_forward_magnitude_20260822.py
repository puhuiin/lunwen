# -*- coding: utf-8 -*-
"""前向能力分解 + 经济量级（2026-08-22）。
A) 前向：DV = t+1 年的选股α/择时贡献（TM/HM），RHS = t 年基金-年行为均值。
   回答"行为分解发现是同期关联还是前瞻预测"；C(year) FE + 基金聚类 SE。
B) 经济量级：能力分解决数 × 行为变量标准差 → 年化选股α 变化（百分点/年）。
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
M2 = os.path.join(HERE, "output", "batch3_mkt2_window_2026-08-22.csv")
OUT = os.path.join(HERE, "output", "batch3_forward_decomposition_2026-08-22.json")

def winsor(s, lo=0.01, hi=0.99):
    s = s.astype(float); a, b = s.quantile(lo), s.quantile(hi)
    return s.clip(a, b)

panel = pd.read_csv(PANEL, dtype={"fund_code": str})
panel["fund_code"] = panel["fund_code"].str.strip()
panel["year"] = pd.to_datetime(panel["report_date"]).dt.year
panel["log_aum"] = np.log(panel["avg_aum"].clip(lower=1e-9))
for v in ["log_aum","AS_improved","ICI","industry_hhi","TO_wind","ARG","return_volatility","de","lsv","risk_asym"]:
    panel[v+"_w"] = winsor(panel[v])
agg = panel.groupby(["fund_code","year"])[[c+"_w" for c in
    ["log_aum","AS_improved","ICI","industry_hhi","TO_wind","ARG","return_volatility","de","lsv","risk_asym"]]].mean().reset_index()

def load_b(path, cols):
    b = pd.read_csv(path)
    b["fund_code"] = b["fund_code"].astype(int).astype(str)
    b["year"] = b["year"].astype(int)
    return b[["fund_code","year"]+cols]

b2 = load_b(B2TM, ["TM_alpha_annual","TM_beta2"]).merge(load_b(B2HM, ["HM_alpha","timing_contrib_HM"]), on=["fund_code","year"])
m2 = pd.read_csv(M2); m2["fund_code"] = m2["fund_code"].astype(str).str.strip(); m2["year"] = m2["year"].astype(int)
b2 = b2.merge(m2[["fund_code","year","mkt2_mean"]], on=["fund_code","year"], how="left")
b2["timing_contrib_TM"] = b2["TM_beta2"] * b2["mkt2_mean"] * 252.0
b2["sel_TM_w"] = winsor(b2["TM_alpha_annual"]); b2["sel_HM_w"] = winsor(b2["HM_alpha"])
b2["tim_TM_w"] = winsor(b2["timing_contrib_TM"]); b2["tim_HM_w"] = winsor(b2["timing_contrib_HM"])

# ---- A) 前向：行为(t) → 能力(t+1) ----
fwd = agg.merge(b2[["fund_code","year","sel_TM_w","sel_HM_w","tim_TM_w","tim_HM_w"]],
                left_on=["fund_code", "year"], right_on=["fund_code", "year"], how="inner")
for c in ["sel_TM_w","sel_HM_w","tim_TM_w","tim_HM_w"]:
    fwd[c+"_lead"] = fwd.groupby("fund_code")[c].shift(-1)
fwd = fwd.dropna(subset=["sel_TM_w_lead"])
print(f"前向样本 {len(fwd)} 基金-年 / {fwd['fund_code'].nunique()} 基金（t → t+1）")

RHS = ["log_aum_w","AS_improved_w","ICI_w","industry_hhi_w","TO_wind_w","ARG_w",
       "return_volatility_w","de_w","lsv_w","risk_asym_w"]
def fit(d, dv):
    sub = d.dropna(subset=RHS + [dv]).copy()
    keep = [c for c in RHS if sub[c].std() > 1e-12]
    m = smf.ols(dv + " ~ " + " + ".join(keep) + " + C(year)", data=sub).fit()
    X = np.asarray(m.model.data.exog, float); resid = np.asarray(m.resid, float)
    groups = sub["fund_code"].values.astype(str); k = X.shape[1]
    XtX_inv = np.linalg.inv(X.T @ X); meat = np.zeros((k, k))
    for g in np.unique(groups):
        mm = groups == g
        s = X[mm].T @ resid[mm]; meat += np.outer(s, s)
    V = XtX_inv @ meat @ XtX_inv
    se = np.sqrt(np.maximum(np.diag(V), 0)); t2 = m.params.values / se
    p2 = 2.0 * spstats.t.sf(np.abs(t2), df=len(resid) - k)
    out = {}
    for i, nm in enumerate(m.params.index):
        if nm in keep:
            out[nm] = dict(beta=float(m.params.values[i]), t=float(t2[i]), p=float(p2[i]),
                           stars="" if p2[i] > .10 else "*" if p2[i] > .05 else "**" if p2[i] > .01 else "***")
    return out, dict(N=int(m.nobs), nfund=int(sub["fund_code"].nunique()), r2=float(m.rsquared))

results = {"design": "行为(t) → 能力(t+1)，C(year) FE + 基金聚类"}
for dv, label in [("sel_TM_w_lead","前向TM选股α"), ("sel_HM_w_lead","前向HM选股α"),
                  ("tim_TM_w_lead","前向TM择时"), ("tim_HM_w_lead","前向HM择时")]:
    coefs, meta = fit(fwd, dv)
    results[label] = dict(dv=dv, meta=meta, coefs=coefs)
    print(f"\n[{label}]  N={meta['N']}  funds={meta['nfund']}  R²={meta['r2']:.4f}")
    for v in ["de_w","lsv_w","risk_asym_w","ICI_w","TO_wind_w"]:
        c = coefs.get(v)
        if c: print(f"   {v:16s} β={c['beta']:+.5f}  t={c['t']:+.2f}  {c['stars']}")

# ---- B) 经济量级 ----
sd = {v: float(agg[v].std()) for v in ["de_w", "risk_asym_w", "lsv_w"]}
wjson = json.load(open(os.path.join(HERE, "output", "batch3_within_decomposition_2026-08-22.json"), encoding="utf-8"))
cjson = json.load(open(os.path.join(HERE, "output", "batch3_alpha_decomposition_2026-08-22.json"), encoding="utf-8"))
def beta_of(blob, label, var):
    return blob[label]["coefs"][var]["beta"]
mag = {}
for tag, blob, label, var in [
    ("截面TM", cjson, "DV1_选股α", "de"), ("截面HM", None, None, None),
    ("组内TM", wjson, "组内 DV1_TM选股α", "de_w"), ("组内HM", wjson, "组内 DV2_HM选股α", "de_w"),
]:
    if blob is None: continue
    b = beta_of(blob, label, var)
    mag[f"DE_{tag}"] = dict(beta=b, sd=sd["de_w"], effect_pp_per_year=float(b * sd["de_w"] * 100))
hmcs = cjson["DV1_选股α"]["coefs"]["risk_asym"]["beta"]
mag["RA_截面TM"] = dict(beta=hmcs, sd=sd["risk_asym_w"], effect_pp_per_year=float(hmcs * sd["risk_asym_w"] * 100))
mag["RA_组内TM"] = dict(beta=beta_of(wjson, "组内 DV1_TM选股α", "risk_asym_w"), sd=sd["risk_asym_w"],
                        effect_pp_per_year=float(beta_of(wjson, "组内 DV1_TM选股α", "risk_asym_w") * sd["risk_asym_w"] * 100))
sd_dv = float(b2["sel_TM_w"].std())
mag["DV_std"] = dict(sel_alpha_TM_w_std=sd_dv)
print("\n=== 经济量级（1 SD 行为 → 年化选股α 变化，百分点/年）===")
print(f"  de_w SD={sd['de_w']:.3f}  risk_asym_w SD={sd['risk_asym_w']:.3f}  选股α(TM) SD={sd_dv:.3f}")
for k, v in mag.items():
    if k != "DV_std": print(f"  {k}: β={v['beta']:+.3f} → {v['effect_pp_per_year']:+.2f} pp/年")
results["economic_magnitude"] = mag
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)
print(f"\n[out] {OUT}")
