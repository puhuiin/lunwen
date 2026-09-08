# -*- coding: utf-8 -*-
"""权威 M4 重算（诚实收口 v4）：全变量缩尾 + 18 RHS(含FF5) + C(year) + 双向聚类(CGM2011)。
输出全部系数 + 双向(t2w)/单维(t1w) t 与 p，供稿件全表+叙事统一刷新。"""
import os, numpy as np, pandas as pd, warnings
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

# 双向聚类 (CGM 2011) —— 与 _verify_two_way_cluster.py 金标准交叉验证口径一致
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

rhs_w = [r+"_w" for r in ALLRHS]
d = df.dropna(subset=rhs_w + ["ff5_adj_return_w"]).copy()
form = "ff5_adj_return_w ~ " + " + ".join(rhs_w) + " + C(year)"
m = smf.ols(form, data=d).fit(cov_type="cluster", cov_kwds={"groups": d["fund_code"]})

X = np.asarray(m.model.data.exog, float)
resid = np.asarray(m.resid, float)
g1 = d["fund_code"].values.astype(str)
g2 = d["year"].values.astype(str)
V2 = two_way_V(X, resid, g1, g2)
se2 = np.sqrt(np.maximum(np.diag(V2), 0))
t2 = m.params.values / se2
p2 = 2.0 * spstats.t.sf(np.abs(t2), df=len(resid) - X.shape[1])

names = list(m.params.index)
print("N=%d  基金=%d  R2=%.4f  adjR2=%.4f" % (int(m.nobs), d["fund_code"].nunique(), m.rsquared, m.rsquared_adj))
print("%-22s %10s %8s %8s %8s %8s %8s" % ("var","beta","t2w","p2w","t1w","p1w","stars"))
rows = {}
for i, nm in enumerate(names):
    if nm == "Intercept" or nm.startswith("C(year)"):
        continue
    b = m.params.values[i]
    star = "" if p2[i] > 0.10 else ("*" if p2[i] > 0.05 else ("**" if p2[i] > 0.01 else "***"))
    rows[nm] = (b, t2[i], p2[i], m.tvalues.values[i], m.pvalues.values[i], star)
    print("%-22s %+10.5f %+8.2f %8.3f %+8.2f %8.3f %8s" % (nm, b, t2[i], p2[i], m.tvalues.values[i], m.pvalues.values[i], star))

print("\n=== L5 重点（双向聚类权威值）===")
for v in ["de","lsv","risk_asym"]:
    b, t, p, t1, p1, st = rows[v]
    print("%-12s beta=%+.5f  t2w=%+.2f p2w=%.3f  | t1w=%+.2f p1w=%.3f  %s"
          % (v, b, t, p, t1, p1, st))

# 同时打印 FF5 供全表重写
print("\n=== FF5 / 控制 系数（供全表）===")
for v in ["ff5_MKT_excess","ff5_SMB","ff5_HML","ff5_RMW","ff5_CMA",
          "log_aum","log_fund_age","mgr_total_tenure_v2","AS_improved","ICI",
          "industry_hhi","SDI","TO_wind","ARG","return_volatility"]:
    b, t, p, t1, p1, st = rows[v]
    print("%-18s %+10.5f t2w=%+7.2f p2w=%.3f %s" % (v, b, t, p, st))
