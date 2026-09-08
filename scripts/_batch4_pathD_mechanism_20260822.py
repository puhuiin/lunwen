# -*- coding: utf-8 -*-
"""路径D探索 + 批次④机制检验（2026-08-22）：
A) 路径D（基金类型异质性）：类型字段仅 119/400 匹配（偏股97/灵活22），只做探索性检查：
   RA×灵活交互 + 分组系数，正式结论判为"数据不可行"。
B) TO_wind×log_aum 交互（IS 冲击成本启发）：换手的边际价值是否随规模递减（成本渠道）。
全部回归对齐 v4 权威口径：缩尾 + C(year) FE + CGM2011 双向聚类。
"""
import os, json, warnings
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from scipy import stats as spstats
warnings.filterwarnings("ignore")

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PANEL = os.path.join(HERE, "指标计算流水线", "output", "主分析面板_重建_含TOwind.csv")
FLIST = os.path.join(HERE, "数据", "基金基础信息", "全部基金列表_含清盘.csv")
OUTJSON = os.path.join(HERE, "output", "batch4_pathD_mechanism_2026-08-22.json")

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

panel = pd.read_csv(PANEL, dtype={"fund_code": str})
panel["fund_code"] = panel["fund_code"].str.strip()
panel["log_aum"] = np.log(panel["avg_aum"].clip(lower=1e-9))
panel["year"] = pd.to_datetime(panel["report_date"]).dt.year

V4 = ["log_aum","log_fund_age","mgr_total_tenure_v2","AS_improved","ICI","industry_hhi",
      "SDI","TO_wind","ARG","return_volatility","de","lsv","risk_asym",
      "ff5_MKT_excess","ff5_SMB","ff5_HML","ff5_RMW","ff5_CMA","ff5_adj_return"]
for v in V4:
    panel[v+"_w"] = winsor(panel[v])

def fit(d, rhs, dv="ff5_adj_return_w", keyvars=()):
    sub = d.dropna(subset=rhs + [dv]).copy()
    keep = [c for c in rhs if sub[c].std() > 1e-12]
    m = smf.ols(dv + " ~ " + " + ".join(keep) + " + C(year)", data=sub).fit()
    X = np.asarray(m.model.data.exog, float); resid = np.asarray(m.resid, float)
    V = two_way_V(X, resid, sub["fund_code"].values.astype(str), sub["year"].values.astype(str))
    se = np.sqrt(np.maximum(np.diag(V), 0))
    t2 = m.params.values / se
    p2 = 2.0 * spstats.t.sf(np.abs(t2), df=len(resid) - X.shape[1])
    names = list(m.params.index)
    coefs = {}
    for i, nm in enumerate(names):
        if nm == "Intercept" or nm.startswith("C(year)"):
            continue
        base = nm[:-2] if nm.endswith("_w") else nm
        coefs[base] = dict(beta=float(m.params.values[i]), t=float(t2[i]), p=float(p2[i]),
                           stars="" if p2[i] > .10 else "*" if p2[i] > .05 else "**" if p2[i] > .01 else "***")
    meta = dict(N=int(m.nobs), nfund=int(sub["fund_code"].nunique()), r2=float(m.rsquared))
    return coefs, meta

results = {}

# ===== A) 路径D：类型异质性（探索性） =====
fl = pd.read_csv(FLIST, dtype={"基金代码": str})
fl["基金代码"] = fl["基金代码"].str.strip()
fl = fl.dropna(subset=["基金类型"])
typ = fl[["基金代码", "基金类型"]].rename(columns={"基金代码": "fund_code"})
panel_t = panel.merge(typ, on="fund_code", how="left")
matched = panel_t["基金类型"].notna()
n_matched_funds = panel_t.loc[matched, "fund_code"].nunique()
panel_t["flex"] = (panel_t["基金类型"] == "混合型-灵活").astype(float)
results["pathD_data"] = dict(matched_funds=int(n_matched_funds), total_funds=400,
                             type_counts=panel_t.loc[matched].groupby("fund_code")["基金类型"].first().value_counts().to_dict())
print(f"[A] 类型匹配 {n_matched_funds}/400 基金：", results["pathD_data"]["type_counts"])

RHSD = [c+"_w" for c in ["log_aum","log_fund_age","mgr_total_tenure_v2","AS_improved","ICI","industry_hhi",
                          "SDI","TO_wind","ARG","return_volatility","de","lsv","risk_asym",
                          "ff5_MKT_excess","ff5_SMB","ff5_HML","ff5_RMW","ff5_CMA"]]
# 中心化交互，避免共线
for c in ["TO_wind_w", "log_aum_w", "risk_asym_w"]:
    panel_t[c] = panel_t[c] - panel_t[c].mean()
panel_t["RA_x_flex"] = panel_t["risk_asym_w"] * panel_t["flex"]

sub_m = panel_t[panel_t["基金类型"].notna()].copy()
coefs, meta = fit(sub_m, RHSD + ["flex", "RA_x_flex"], keyvars=("risk_asym", "RA_x_flex", "flex"))
results["pathD_RAxFlex"] = dict(meta=meta, coefs=coefs)
print(f"[A] RA×灵活交互（探索性） N={meta['N']} funds={meta['nfund']}")
for v in ["risk_asym", "RA_x_flex", "flex"]:
    c = coefs.get(v)
    if c: print(f"    {v:12s} β={c['beta']:+.5f}  t2w={c['t']:+.2f}  {c['stars']}")

# 分组
for tname, tmask in [("偏股", sub_m["flex"] == 0), ("灵活", sub_m["flex"] == 1)]:
    coefs_g, meta_g = fit(sub_m[tmask], RHSD)
    results[f"pathD_group_{tname}"] = dict(meta=meta_g, coefs=coefs_g)
    c = coefs_g.get("risk_asym")
    print(f"    分组[{tname}] N={meta_g['N']} funds={meta_g['nfund']}  RA β={c['beta']:+.4f} t={c['t']:+.2f} {c['stars']}")

# ===== B) TO×规模交互（成本渠道，全样本） =====
panel["TO_x_aum"] = panel["TO_wind_w"] * panel["log_aum_w"]   # 已各自中心化于上一步? panel_t 中心化不影响 panel
# 注意：中心化在 panel_t 上做的，panel 上重新中心化
panel["TO_wind_c"] = panel["TO_wind_w"] - panel["TO_wind_w"].mean()
panel["log_aum_c"] = panel["log_aum_w"] - panel["log_aum_w"].mean()
panel["TO_x_aum"] = panel["TO_wind_c"] * panel["log_aum_c"]
RHSM = [c+"_w" for c in ["log_aum","log_fund_age","mgr_total_tenure_v2","AS_improved","ICI","industry_hhi",
                          "SDI","TO_wind","ARG","return_volatility","de","lsv","risk_asym",
                          "ff5_MKT_excess","ff5_SMB","ff5_HML","ff5_RMW","ff5_CMA"]] + ["TO_x_aum"]
coefs, meta = fit(panel, RHSM)
results["mechanism_TOxAUM"] = dict(meta=meta, coefs=coefs)
print(f"\n[B] TO×log_aum 交互（v4 全样本） N={meta['N']} funds={meta['nfund']}")
for v in ["TO_wind", "TO_x_aum", "risk_asym", "de"]:
    c = coefs[v]
    print(f"    {v:12s} β={c['beta']:+.6f}  t2w={c['t']:+.2f}  {c['stars']}")

with open(OUTJSON, "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)
print(f"\n[out] {OUTJSON}")
