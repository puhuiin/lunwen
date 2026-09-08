"""L3 深化补充：RG 对替代因变量的预测力（KSZ 2008 思路）。
关键方法学点：alpha 对 RG 回归存在机械重叠（RG 含 quarter_return，alpha 由 quarter_return 算出），
故 RG 的真正检验应放在 未来收益 / 领先 alpha 上。
DV 候选：future_return（下季收益）、ff5_adj_return_lead（下季alpha）、excess_return_lead。
"""
import os, numpy as np, pandas as pd
import statsmodels.formula.api as smf
from scipy import stats as spstats

PANEL = "D:/Desktop/基金经理行为分析研究/指标计算流水线/output/主分析面板_重建_含TOwind.csv"
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
df = pd.read_csv(PANEL, dtype={"fund_code": str})
df["log_aum"] = np.log(df["avg_aum"].clip(lower=1e-9))
df["ff5_adj_return"] = pd.to_numeric(df["ff5_adj_return"], errors="coerce")
df["future_return"]  = pd.to_numeric(df["future_return"], errors="coerce")
df["excess_return"]  = pd.to_numeric(df["excess_return"], errors="coerce")
# 领先一期 alpha / excess
df = df.sort_values(["fund_code","year","quarter"])
for c in ["ff5_adj_return","excess_return"]:
    df[c+"_lead"] = df.groupby("fund_code")[c].shift(-1)

FF5  = ["ff5_MKT_excess","ff5_SMB","ff5_HML","ff5_RMW","ff5_CMA"]
CONT = ["log_aum"]
L1   = ["log_fund_age","mgr_total_tenure_v2"]
L2   = ["AS_improved","ICI","industry_hhi"]
L4   = ["ARG","return_volatility"]
L5   = ["de","lsv","risk_asym"]
CTRL = CONT + FF5 + L1 + L2 + L4 + L5   # 不含 L3

def winsor(s):
    s = s.astype(float); lo, hi = s.quantile(0.01), s.quantile(0.99)
    return s.clip(lo, hi)
for v in CTRL + ["RG","future_return","ff5_adj_return_lead","excess_return_lead","ff5_adj_return"]:
    if v in df.columns:
        df[v+"_w"] = winsor(pd.to_numeric(df[v], errors="coerce"))

def _meat(groups, X, resid):
    k = X.shape[1]; meat = np.zeros((k, k))
    for gg in np.unique(groups):
        m = groups == gg; s = X[m].T @ resid[m]; meat += np.outer(s, s)
    return meat
def _oneway_V(X, resid, groups):
    return np.linalg.inv(X.T @ X) @ _meat(groups, X, resid) @ np.linalg.inv(X.T @ X)
def two_way_V(X, resid, g1, g2):
    g12 = np.array([f"{a}|{b}" for a, b in zip(g1, g2)])
    return _oneway_V(X, resid, g1) + _oneway_V(X, resid, g2) - _oneway_V(X, resid, g12)

def fit(dv, rhs_list):
    rhs_w = [r+"_w" for r in rhs_list]
    d = df.dropna(subset=rhs_w + [dv+"_w"]).copy()
    form = f"{dv}_w ~ " + " + ".join(rhs_w) + " + C(year)"
    m = smf.ols(form, data=d).fit(cov_type="cluster", cov_kwds={"groups": d["fund_code"]})
    X = np.asarray(m.model.data.exog, float); resid = np.asarray(m.resid, float)
    g1 = d["fund_code"].values.astype(str); g2 = d["year"].values.astype(str)
    V2 = two_way_V(X, resid, g1, g2)
    se2 = np.sqrt(np.maximum(np.diag(V2), 0)); t2 = m.params.values / se2
    p2 = 2.0 * spstats.t.sf(np.abs(t2), df=len(resid)-X.shape[1])
    names = list(m.params.index); out = {}
    for i, nm in enumerate(names):
        if nm == "Intercept" or nm.startswith("C(year)"): continue
        base = nm[:-2] if nm.endswith("_w") else nm
        out[base] = dict(beta=float(m.params.values[i]), t2w=float(t2[i]), p2w=float(p2[i]))
    return m, d, out

def stars(p):
    return "***" if p<0.01 else "**" if p<0.05 else "*" if p<0.10 else "n.s."

print("="*78)
print("L3 深化补充 — RG 对替代因变量的预测力（双向聚类 CGM2011）")
print("="*78)
for dv in ["future_return","ff5_adj_return_lead","excess_return_lead"]:
    m, d, o = fit(dv, CTRL + ["RG"])
    r = o.get("RG")
    print(f"\nDV={dv:22s}  N={int(m.nobs)}  R²={m.rsquared:.4f}")
    if r:
        print(f"   RG  β={r['beta']:+.5f}  t2w={r['t2w']:+.2f}  p2w={r['p2w']:.3f}  {stars(r['p2w']):>4s}")
    else:
        print("   RG 未进入（缺失过多被drop）")

# 组内 FE：fund demeaning 后 RG → ff5_adj_return
print("\n--- 组内 FE（fund demeaning）：RG → ff5_adj_return ---")
fe_vars = CTRL + ["RG","ff5_adj_return"]
for v in fe_vars:
    df[v+"_dm"] = df.groupby("fund_code")[v+"_w"].transform(lambda x: x - x.mean())
d_fe = df.dropna(subset=[v+"_dm" for v in fe_vars])
form = "ff5_adj_return_dm ~ " + " + ".join([r+"_dm" for r in CTRL+["RG"]])
mfe = smf.ols(form, data=d_fe).fit(cov_type="cluster", cov_kwds={"groups": d_fe["fund_code"]})
rg_dm = [i for i,nm in enumerate(mfe.params.index) if nm=="RG_dm"][0]
print(f"   RG_dm β={mfe.params.values[rg_dm]:+.5f}  t={mfe.tvalues.values[rg_dm]:+.2f}  p={mfe.pvalues.values[rg_dm]:.3f}  N={int(mfe.nobs)}  {stars(mfe.pvalues.values[rg_dm])}")
