# -*- coding: utf-8 -*-
"""v4 基准回归表数据导出：全变量缩尾 + 18 RHS(含FF5) + C(year) + 双向聚类(CGM2011)。
导出全部 RHS 的 beta/se2w/t2w/p2w/se1w/t1w/p1w + 增量 R^2，供独立基准表 HTML 生成。
"""
import os, json, numpy as np, pandas as pd, warnings
import statsmodels.formula.api as smf
from scipy import stats as spstats
warnings.filterwarnings("ignore")

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PANEL = os.path.join(HERE, "指标计算流水线", "output", "主分析面板_重建_含TOwind.csv")
df = pd.read_csv(PANEL, dtype={"fund_code": str})
df["log_aum"] = np.log(df["avg_aum"].clip(lower=1e-9))
df["ff5_adj_return"] = pd.to_numeric(df["ff5_adj_return"], errors="coerce")

FF5  = ["ff5_MKT_excess","ff5_SMB","ff5_HML","ff5_RMW","ff5_CMA"]
CONT = ["log_aum"]
L1   = ["log_fund_age","mgr_total_tenure_v2"]
L2   = ["AS_improved","ICI","industry_hhi"]
L3   = ["SDI","TO_wind"]
L4   = ["ARG","return_volatility"]
L5   = ["de","lsv","risk_asym"]
ALLRHS = CONT + FF5 + L1 + L2 + L3 + L4 + L5

def winsor(s):
    s = s.astype(float); lo, hi = s.quantile(0.01), s.quantile(0.99)
    return s.clip(lo, hi)
for v in ALLRHS + ["ff5_adj_return"]:
    df[v+"_w"] = winsor(df[v])

# 双向聚类 (CGM 2011)
def _meat(groups, X, resid):
    k = X.shape[1]; meat = np.zeros((k, k))
    for gg in np.unique(groups):
        m = groups == gg; s = X[m].T @ resid[m]; meat += np.outer(s, s)
    return meat
def _oneway_V(X, resid, groups):
    XtX_inv = np.linalg.inv(X.T @ X)
    return XtX_inv @ _meat(groups, X, resid) @ XtX_inv
def two_way_V(X, resid, g1, g2):
    g12 = np.array([f"{a}|{b}" for a, b in zip(g1, g2)])
    return _oneway_V(X, resid, g1) + _oneway_V(X, resid, g2) - _oneway_V(X, resid, g12)

def fit(rhs_list):
    rhs_w = [r+"_w" for r in rhs_list]
    d = df.dropna(subset=rhs_w + ["ff5_adj_return_w"]).copy()
    form = "ff5_adj_return_w ~ " + " + ".join(rhs_w) + " + C(year)"
    m = smf.ols(form, data=d).fit(cov_type="cluster", cov_kwds={"groups": d["fund_code"]})
    return m, d

m, d = fit(ALLRHS)
X = np.asarray(m.model.data.exog, float)
resid = np.asarray(m.resid, float)
g1 = d["fund_code"].values.astype(str)
g2 = d["year"].values.astype(str)
V2 = two_way_V(X, resid, g1, g2)
se2 = np.sqrt(np.maximum(np.diag(V2), 0))
t2 = m.params.values / se2
p2 = 2.0 * spstats.t.sf(np.abs(t2), df=len(resid) - X.shape[1])
se1 = np.asarray(m.bse.values, float)        # statsmodels 单维基金聚类 SE
t1 = m.tvalues.values
p1 = m.pvalues.values

names = list(m.params.index)
out = {}
for i, nm in enumerate(names):
    if nm == "Intercept" or nm.startswith("C(year)"):
        continue
    base = nm[:-2] if nm.endswith("_w") else nm
    out[base] = {
        "beta": float(m.params.values[i]),
        "se2w": float(se2[i]),
        "t2w": float(t2[i]),
        "p2w": float(p2[i]),
        "se1w": float(se1[i]),
        "t1w": float(t1[i]),
        "p1w": float(p1[i]),
    }

# 增量 R^2：去掉 L5 三列后的 R^2 下降
m_wo, _ = fit([r for r in ALLRHS if r not in L5])
r2_full = float(m.rsquared)
r2_wo   = float(m_wo.rsquared)
delta_r2 = r2_full - r2_wo

# 读取置换 / WCB p（来自 _v4_robust.json）
robust_path = os.path.join(HERE, "_v4_robust.json")
robust_raw = {}
if os.path.exists(robust_path):
    robust_raw = json.load(open(robust_path, encoding="utf-8"))
perm_p = robust_raw.get("perm_p", {}) if isinstance(robust_raw, dict) else {}
wcb_p  = robust_raw.get("wcb_p", {}) if isinstance(robust_raw, dict) else {}
for v in L5:
    out[v]["perm_p"] = float(perm_p.get(v)) if v in perm_p else None
    out[v]["wcb_p"]  = float(wcb_p.get(v))  if v in wcb_p  else None

result = {
    "n_obs": int(m.nobs),
    "n_fund": int(d["fund_code"].nunique()),
    "r2": r2_full,
    "adj_r2": float(m.rsquared_adj),
    "r2_without_L5": r2_wo,
    "delta_r2_L5": delta_r2,
    "coefs": out,
    "perm_p": perm_p,
    "wcb_p": wcb_p,
    "rhs_order": ALLRHS,
    "ff5": FF5,
}
with open(os.path.join(HERE, "_v4_benchmark.json"), "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

print("N=%d  基金=%d  R2=%.4f  adjR2=%.4f  R2_wo_L5=%.4f  ΔR2_L5=%.4f"
      % (result["n_obs"], result["n_fund"], r2_full, result["adj_r2"], r2_wo, delta_r2))
print("%-20s %+10s %8s %8s %8s %8s %8s" % ("var","beta","t2w","p2w","t1w","p1w","stars"))
for nm in ALLRHS:
    c = out[nm]
    star = "" if c["p2w"]>0.10 else ("*" if c["p2w"]>0.05 else ("**" if c["p2w"]>0.01 else "***"))
    print("%-20s %+10.5f %+8.2f %8.3f %+8.2f %8.3f %8s" % (nm, c["beta"], c["t2w"], c["p2w"], c["t1w"], c["p1w"], star))
print("\nperm_p:", perm_p)
print("wcb_p :", wcb_p)
