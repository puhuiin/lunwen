# -*- coding: utf-8 -*-
"""
独立重跑核验（2026-08-22）
目的：以 _repro_all_OptionA_2026-08-15.py 的完全相同口径重跑 M0-M4 与 M4 系数，
      并与稿件 merged_manuscript.html 中已写入的数字逐项比对，找出不一致。
不修改任何既有脚本与数据，只读 + 输出 JSON。
"""
import json
import warnings

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from statsmodels.stats.outliers_influence import variance_inflation_factor

warnings.filterwarnings("ignore")

PANEL = r"指标计算流水线/output/主分析面板_重建_含TOwind.csv"
OUT = r"_audit_rerun_20260822.json"

df = pd.read_csv(PANEL)
TOTAL = len(df)

df["log_aum"] = np.log(df["avg_aum"].clip(lower=1e-9))
df["ff5_adj_return"] = pd.to_numeric(df["ff5_adj_return"], errors="coerce")

CONT = ["log_aum"]
FF5 = ["ff5_MKT_excess", "ff5_SMB", "ff5_HML", "ff5_RMW", "ff5_CMA"]
L1 = ["log_fund_age", "mgr_total_tenure_v2"]
L2 = ["AS_improved", "ICI", "industry_hhi"]
L3 = ["SDI", "TO_wind"]
L4 = ["ARG", "return_volatility"]
L5 = ["de", "lsv", "risk_asym"]
ALLRHS = CONT + FF5 + L1 + L2 + L3 + L4 + L5


def winsor(s):
    s = s.astype(float)
    lo, hi = s.quantile(0.01), s.quantile(0.99)
    return s.clip(lo, hi)


for v in ALLRHS + ["ff5_adj_return"]:
    df[v + "_w"] = winsor(df[v])


def run_model(rhs, data):
    rhs_w = [r + "_w" for r in rhs]
    d = data.dropna(subset=rhs_w + ["ff5_adj_return_w"]).copy()
    form = "ff5_adj_return_w ~ " + " + ".join(rhs_w) + " + C(year)"
    m = smf.ols(form, data=d).fit(cov_type="cluster",
                                  cov_kwds={"groups": d["fund_code"]})
    return m, len(d), d["fund_code"].nunique(), d


specs = {
    "M0": CONT + FF5,
    "M1": CONT + FF5 + L1,
    "M2": CONT + FF5 + L1 + L2,
    "M3": CONT + FF5 + L1 + L2 + L3 + L4,
    "M4": CONT + FF5 + L1 + L2 + L3 + L4 + L5,
}

B, models = {}, {}
for name, rhs in specs.items():
    m, n, nf, d = run_model(rhs, df)
    models[name] = (m, n, nf, rhs, d)
    B[name] = dict(N=n, funds=nf, R2=round(m.rsquared, 4),
                   adjR2=round(m.rsquared_adj, 4))


def dR2(a, b):
    return round(models[b][0].rsquared - models[a][0].rsquared, 4)


B["dR2"] = {
    "M0_M1": dR2("M0", "M1"), "M1_M2": dR2("M1", "M2"),
    "M2_M3": dR2("M2", "M3"), "M3_M4": dR2("M3", "M4"),
    "M0_M4": dR2("M0", "M4"),
}

# ---------- 同样本 ΔR²（在 M4 样本上重估 M0/M3）----------
d4 = models["M4"][4]
same = {}
for nm in ["M0", "M1", "M2", "M3"]:
    rhs_w = [r + "_w" for r in specs[nm]]
    form = "ff5_adj_return_w ~ " + " + ".join(rhs_w) + " + C(year)"
    mm = smf.ols(form, data=d4).fit(cov_type="cluster",
                                    cov_kwds={"groups": d4["fund_code"]})
    same[nm] = round(mm.rsquared, 4)
same["M4"] = round(models["M4"][0].rsquared, 4)
same["dR2_L1"] = round(same["M1"] - same["M0"], 4)
same["dR2_L2"] = round(same["M2"] - same["M1"], 4)
same["dR2_L3L4"] = round(same["M3"] - same["M2"], 4)
same["dR2_L5"] = round(same["M4"] - same["M3"], 4)

# ---------- M4 系数 ----------
def stars(p):
    return "***" if p < 0.01 else "**" if p < 0.05 else "*" if p < 0.1 else "n.s."


m4 = models["M4"][0]
M4C = {}
for v in ALLRHS:
    k = v + "_w"
    M4C[v] = dict(beta=round(m4.params[k], 5), t=round(m4.tvalues[k], 2),
                  p=round(m4.pvalues[k], 4), stars=stars(m4.pvalues[k]))

# ---------- VIF（M4 RHS）----------
X = d4[[v + "_w" for v in ALLRHS]].copy()
X.insert(0, "const", 1.0)
VIF = {}
for i, c in enumerate(X.columns):
    if c == "const":
        continue
    VIF[c.replace("_w", "")] = round(variance_inflation_factor(X.values, i), 3)

# ---------- L5 相关矩阵 ----------
CORR = d4[[v + "_w" for v in L5]].corr().round(3).to_dict()

# ---------- 双向聚类 SE（CGM 2011）核验 L5 三指标 ----------
def twoway_cluster(model, d, g1="fund_code", g2="year"):
    """CGM2011: V = V_g1 + V_g2 - V_g1g2"""
    X = model.model.exog
    u = model.resid.values
    XtX_inv = np.linalg.pinv(X.T @ X)

    def meat(groups):
        M = np.zeros((X.shape[1], X.shape[1]))
        for _, idx in pd.Series(range(len(groups))).groupby(groups.values):
            ii = idx.values
            Xg = X[ii, :]
            ug = u[ii]
            s = Xg.T @ ug
            M += np.outer(s, s)
        return M

    g1v = d[g1].astype(str).reset_index(drop=True)
    g2v = d[g2].astype(str).reset_index(drop=True)
    g12 = (g1v + "_" + g2v)
    V = XtX_inv @ (meat(g1v) + meat(g2v) - meat(g12)) @ XtX_inv
    se = np.sqrt(np.abs(np.diag(V)))
    return se


se2w = twoway_cluster(m4, d4)
names = m4.model.exog_names
TW = {}
for v in L2 + L3 + L4 + L5:
    k = v + "_w"
    j = names.index(k)
    b = m4.params[k]
    t = b / se2w[j]
    from scipy import stats as st
    p = 2 * (1 - st.norm.cdf(abs(t)))
    TW[v] = dict(beta=round(b, 5), t2w=round(t, 2), p2w=round(p, 4),
                 stars=stars(p))

res = dict(TOTAL=TOTAL, panel_shape=list(df.shape), B=B,
           same_sample=same, M4C=M4C, VIF=VIF, CORR=CORR, TwoWay=TW)

with open(OUT, "w", encoding="utf-8") as f:
    json.dump(res, f, ensure_ascii=False, indent=2)

print("面板 =", df.shape, " 基金数 =", df["fund_code"].nunique())
print("\n=== M0-M4 （各自样本）===")
for k in ["M0", "M1", "M2", "M3", "M4"]:
    print(f"  {k}: N={B[k]['N']:>6}  funds={B[k]['funds']:>4}  "
          f"R2={B[k]['R2']:.4f}  adjR2={B[k]['adjR2']:.4f}")
print("  ΔR²:", B["dR2"])
print("\n=== 同样本（M4 样本 N=%d）ΔR² ===" % B["M4"]["N"])
print("  ", {k: v for k, v in same.items() if k.startswith("dR2")})
print("\n=== M4 系数（基金聚类 SE）===")
for v in L1 + L2 + L3 + L4 + L5:
    c = M4C[v]
    print(f"  {v:<22} b={c['beta']:>+10.5f}  t={c['t']:>+6.2f}  {c['stars']}")
print("\n=== 双向聚类 SE（CGM2011）===")
for v in L2 + L3 + L4 + L5:
    c = TW[v]
    print(f"  {v:<22} b={c['beta']:>+10.5f}  t2w={c['t2w']:>+6.2f}  {c['stars']}")
print("\n=== VIF ===")
print("  max =", max(VIF.values()), "@", max(VIF, key=VIF.get))
for k, v in sorted(VIF.items(), key=lambda x: -x[1])[:6]:
    print(f"  {k:<22} {v}")
print("\nsaved ->", OUT)
