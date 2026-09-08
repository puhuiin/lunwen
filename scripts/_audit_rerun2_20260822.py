# -*- coding: utf-8 -*-
"""
重跑核验第二轮（2026-08-22）
补充核验四件事：
  A. Table 4-5 全部系数的双向聚类 t 值（确认表内标准误口径是否统一）
  B. L5 三指标 VIF / 相关系数在"仅L5可用样本(3455)"与"M4样本(2264)"两口径下的差异
  C. 同样本逐层 ΔR² 的加入顺序敏感性（检验层级排序是否稳健）
  D. ff5_adj_return 基金内时不变性核查 + 基金层面折叠回归（真实独立样本）
只读，不改任何既有脚本/数据。
"""
import json
import warnings

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from scipy import stats as st
from statsmodels.stats.outliers_influence import variance_inflation_factor

warnings.filterwarnings("ignore")

PANEL = r"指标计算流水线/output/主分析面板_重建_含TOwind.csv"
OUT = r"_audit_rerun2_20260822.json"

df = pd.read_csv(PANEL)
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

W = [v + "_w" for v in ALLRHS]
d4 = df.dropna(subset=W + ["ff5_adj_return_w"]).copy()

form4 = "ff5_adj_return_w ~ " + " + ".join(W) + " + C(year)"
m4 = smf.ols(form4, data=d4).fit(cov_type="cluster",
                                 cov_kwds={"groups": d4["fund_code"]})

res = {}


# ---------- A. 全变量双向聚类 t ----------
def twoway_se(model, d, g1="fund_code", g2="year"):
    X = model.model.exog
    u = model.resid.values
    XtX_inv = np.linalg.pinv(X.T @ X)

    def meat(groups):
        M = np.zeros((X.shape[1], X.shape[1]))
        for _, idx in pd.Series(range(len(groups))).groupby(groups.values):
            ii = idx.values
            s = X[ii, :].T @ u[ii]
            M += np.outer(s, s)
        return M

    g1v = d[g1].astype(str).reset_index(drop=True)
    g2v = d[g2].astype(str).reset_index(drop=True)
    V = XtX_inv @ (meat(g1v) + meat(g2v) - meat(g1v + "_" + g2v)) @ XtX_inv
    return np.sqrt(np.abs(np.diag(V)))


def stars(p):
    return "***" if p < 0.01 else "**" if p < 0.05 else "*" if p < 0.1 else ""


se2w = twoway_se(m4, d4)
names = m4.model.exog_names
A = {}
for v in ALLRHS:
    k = v + "_w"
    j = names.index(k)
    b = m4.params[k]
    t_fund = m4.tvalues[k]
    t_2w = b / se2w[j]
    p_2w = 2 * (1 - st.norm.cdf(abs(t_2w)))
    A[v] = dict(beta=round(b, 5),
                t_fund=round(t_fund, 2), star_fund=stars(m4.pvalues[k]),
                t_2way=round(t_2w, 2), p_2way=round(p_2w, 4),
                star_2way=stars(p_2w))
res["A_table45_SE"] = A

# ---------- B. L5 VIF / corr 两口径 ----------
L5w = [v + "_w" for v in L5]
d5 = df.dropna(subset=L5w).copy()
B = {"N_L5only": len(d5), "N_M4": len(d4)}
for tag, dd in [("L5only_3455", d5), ("M4_2264", d4)]:
    X = dd[L5w].copy()
    X.insert(0, "const", 1.0)
    vif = {L5[i - 1]: round(variance_inflation_factor(X.values, i), 3)
           for i in range(1, 4)}
    c = dd[L5w].corr()
    offdiag = [abs(c.iloc[i, j]) for i in range(3) for j in range(3) if i != j]
    B[tag] = dict(N=len(dd), vif_L5only_spec=vif,
                  max_abs_r=round(max(offdiag), 4),
                  corr=c.round(3).values.tolist())
# M4 全 RHS 口径下 L5 的 full-conditional VIF
Xf = d4[W].copy()
Xf.insert(0, "const", 1.0)
B["vif_fullRHS_L5"] = {v: round(variance_inflation_factor(Xf.values,
                                                          Xf.columns.get_loc(v + "_w")), 3)
                       for v in L5}
res["B_L5_indep"] = B

# ---------- C. 同样本逐层 ΔR²，及顺序敏感性 ----------
def r2_on(rhs, dd):
    ww = [r + "_w" for r in rhs]
    f = "ff5_adj_return_w ~ " + " + ".join(ww) + " + C(year)"
    return smf.ols(f, data=dd).fit().rsquared


BASE = CONT + FF5
blocks = {"L1": L1, "L2": L2, "L3+L4": L3 + L4, "L5": L5}

seq = {}
cum = list(BASE)
prev = r2_on(cum, d4)
seq["M0"] = round(prev, 4)
for nm in ["L1", "L2", "L3+L4", "L5"]:
    cum = cum + blocks[nm]
    r = r2_on(cum, d4)
    seq[nm] = dict(R2=round(r, 4), dR2=round(r - prev, 4))
    prev = r
R2_FULL = prev

# 各层"最后加入"（LMG 式上界）与"单独加入"（下界）
lastin, firstin = {}, {}
for nm, vs in blocks.items():
    rest = BASE + [x for k, v in blocks.items() if k != nm for x in v]
    lastin[nm] = round(R2_FULL - r2_on(rest, d4), 4)
    firstin[nm] = round(r2_on(BASE + vs, d4) - seq["M0"], 4)
res["C_same_sample"] = dict(sequential=seq, R2_full=round(R2_FULL, 4),
                            dR2_last_in=lastin, dR2_alone=firstin)

# ---------- D. 因变量时不变性 + 基金层折叠回归 ----------
g = df.dropna(subset=["ff5_adj_return"]).groupby("fund_code")["ff5_adj_return"]
nun = g.nunique()
D = {"funds_with_alpha": int(len(nun)),
     "funds_alpha_time_varying": int((nun > 1).sum()),
     "max_within_fund_std": float(g.std().max())}

fl = d4.groupby("fund_code")[W + ["ff5_adj_return_w"]].mean()
mf = smf.ols("ff5_adj_return_w ~ " + " + ".join(W), data=fl).fit(cov_type="HC1")
D["fund_level"] = dict(N=int(mf.nobs), R2=round(mf.rsquared, 4),
                       adjR2=round(mf.rsquared_adj, 4))
D["fund_level_coef"] = {v: dict(beta=round(mf.params[v + "_w"], 5),
                                t=round(mf.tvalues[v + "_w"], 2),
                                star=stars(mf.pvalues[v + "_w"]))
                        for v in L1 + L2 + L3 + L4 + L5}
# 基金层同样本逐层 ΔR²
def r2f(rhs):
    return smf.ols("ff5_adj_return_w ~ " + " + ".join([r + "_w" for r in rhs]),
                   data=fl).fit().rsquared


cum, prev, fseq = list(BASE), r2f(BASE), {}
fseq["M0"] = round(prev, 4)
for nm in ["L1", "L2", "L3+L4", "L5"]:
    cum = cum + blocks[nm]
    r = r2f(cum)
    fseq[nm] = dict(R2=round(r, 4), dR2=round(r - prev, 4))
    prev = r
D["fund_level_seq"] = fseq
res["D_dv_structure"] = D

with open(OUT, "w", encoding="utf-8") as f:
    json.dump(res, f, ensure_ascii=False, indent=2)

print("=== A. 表4-5 标准误口径核验（beta / 基金聚类t / 双向聚类t）===")
for v in ALLRHS:
    a = A[v]
    print(f"  {v:<20} b={a['beta']:>+10.5f}  t_fund={a['t_fund']:>+6.2f}{a['star_fund']:<4}"
          f"  t_2way={a['t_2way']:>+6.2f}{a['star_2way']}")

print("\n=== B. L5 独立性两口径 ===")
print("  仅L5可用样本 N=%d  max|r|=%.4f  VIF=%s"
      % (B["L5only_3455"]["N"], B["L5only_3455"]["max_abs_r"],
         B["L5only_3455"]["vif_L5only_spec"]))
print("  M4样本      N=%d  max|r|=%.4f  VIF=%s"
      % (B["M4_2264"]["N"], B["M4_2264"]["max_abs_r"],
         B["M4_2264"]["vif_L5only_spec"]))
print("  M4全RHS口径 L5 full-conditional VIF =", B["vif_fullRHS_L5"])

print("\n=== C. 同样本（N=%d）逐层增量 ===" % len(d4))
print("  M0 R2 =", seq["M0"])
for nm in ["L1", "L2", "L3+L4", "L5"]:
    print(f"  +{nm:<6} R2={seq[nm]['R2']:.4f}  dR2={seq[nm]['dR2']:+.4f}")
print("  最后加入(last-in) :", lastin)
print("  单独加入(alone)   :", firstin)

print("\n=== D. 因变量结构 ===")
print("  有alpha基金数 =", D["funds_with_alpha"],
      " 其中alpha随时间变化的基金数 =", D["funds_alpha_time_varying"],
      " 组内最大std =", D["max_within_fund_std"])
print("  基金层折叠回归: N=%d  R2=%.4f  adjR2=%.4f"
      % (D["fund_level"]["N"], D["fund_level"]["R2"], D["fund_level"]["adjR2"]))
for v in L2 + L4 + L5:
    c = D["fund_level_coef"][v]
    print(f"    {v:<20} b={c['beta']:>+10.5f}  t={c['t']:>+6.2f} {c['star']}")
print("  基金层逐层 dR2:",
      {k: (v if k == "M0" else v["dR2"]) for k, v in fseq.items()})
print("\nsaved ->", OUT)
