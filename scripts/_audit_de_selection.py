# -*- coding: utf-8 -*-
"""de 选择性子样本审计（v4 深度优化 · 接续 lsv 诊断）。

问题：de（处置效应）在 M4 面板仅覆盖 46.6%（结构缺失：依赖半年报全持仓快照；
2006–2015 近零覆盖，2016+ 稳定 ~45%）。de 是 headline 显著指标(t=−2.99***)，
但其估计样本是被"是否有全持仓数据"选择的。本脚本审计该选择是否威胁 de 结论：

  (1) 选择性/可比性：de 有值 vs 缺失两组在结果变量与各 RHS 上的组间差异
      （Welch t + 标准化均值差 SMD，阈值 |SMD|>0.25 视为失衡）；
  (2) de_avail 指示本身是否预测 alpha（控制全 RHS + 年份 FE，双向聚类）；
  (3) 敏感性电池：
      A 基线(de-present only, t−2.99 对照)
      B 均值插补 de + de_avail 指示（全样本）
      C 最坏情形·低 de（缺失插补 mean−2sd）
      D 最坏情形·高 de（缺失插补 mean+2sd）
      E de_avail 指示仅（不放入 de）
      F 仅 2016+ 的 de-present 子样本（隔离时期选择）
  所有规格 DV=ff5_adj_return_w，全变量 1/99 缩尾，CGM2011 双向聚类。
复用 _diag_lsv_fragility 的聚类实现。
"""
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

def winsor(s, lo=0.01, hi=0.99):
    s = s.astype(float); a, b = s.quantile(lo), s.quantile(hi)
    return s.clip(a, b)

# ---------- 双向聚类 (CGM2011) ----------
def _meat(groups, X, resid):
    k = X.shape[1]; meat = np.zeros((k, k))
    for gg in np.unique(groups):
        m = groups == gg; v = X[m].T @ resid[m]; meat += np.outer(v, v)
    return meat
def _oneway_V(X, resid, groups):
    return np.linalg.inv(X.T @ X) @ _meat(groups, X, resid) @ np.linalg.inv(X.T @ X)
def two_way_V(X, resid, g1, g2):
    g12 = np.array([f"{a}|{b}" for a, b in zip(g1, g2)])
    return _oneway_V(X, resid, g1) + _oneway_V(X, resid, g2) - _oneway_V(X, resid, g12)

def est(d, rhs, target, dv="ff5_adj_return_w", fe=True, cluster="two-way"):
    """返回 (beta_target, t, p, N, nfund)。"""
    rhs = list(rhs)
    sub = d.dropna(subset=rhs + [dv]).copy()
    keep = []
    for r in rhs:
        sv = sub[r]
        if sv.notna().sum() > 1 and sv.std() > 1e-12:
            keep.append(r)
        else:
            print("  [est] 剔除零方差列:", r)
    rhs = keep
    if fe:
        form = dv + " ~ " + " + ".join(rhs) + " + C(year)"
    else:
        form = dv + " ~ " + " + ".join(rhs)
    m = smf.ols(form, data=sub).fit(cov_type="cluster", cov_kwds={"groups": sub["fund_code"]})
    X = np.asarray(m.model.data.exog, float); resid = np.asarray(m.resid, float)
    g1 = sub["fund_code"].values.astype(str)
    V2 = two_way_V(X, resid, g1, sub["year"].values.astype(str)) if cluster=="two-way" else _oneway_V(X, resid, g1)
    se2 = np.sqrt(np.maximum(np.diag(V2), 0))
    t2 = m.params.values / se2; p2 = 2.0*spstats.t.sf(np.abs(t2), df=len(resid)-X.shape[1])
    names = list(m.params.index)
    if target not in names:
        raise KeyError("target %s not in model: %s" % (target, names))
    i = names.index(target)
    return m.params.values[i], t2[i], p2[i], int(m.nobs), int(sub["fund_code"].nunique())

def stars(p):
    return "" if p > 0.10 else ("*" if p > 0.05 else ("**" if p > 0.01 else "***"))

# 缩尾准备
for v in ALLRHS:
    df[v+"_w"] = winsor(df[v])
df["ff5_adj_return_w"] = winsor(df["ff5_adj_return"], 0.01, 0.99)
df["de_avail"] = df["de"].notna().astype(int)

# =====================================================================
# (1) 选择性 / 可比性诊断
# =====================================================================
print("="*72)
print("(1) de 选择性诊断：de 有值 vs 缺失 组间可比性")
print("     覆盖：有值 %d / 缺失 %d (覆盖率 %.1f%%)" % (df["de"].notna().sum(), df["de"].isna().sum(), 100*df["de"].notna().mean()))
present = df[df["de"].notna()]; missing = df[df["de"].isna()]
cmp_vars = ["ff5_adj_return","log_aum","log_fund_age","mgr_total_tenure_v2","TO_wind",
            "SDI","ICI","industry_hhi","AS_improved","ARG","return_volatility","lsv","risk_asym"]
print("\n%-18s %10s %10s %8s %8s %8s" % ("变量","有值均值","缺失均值","Welch_t","p","SMD"))
rows_sel = []
for v in cmp_vars:
    a = present[v].astype(float).dropna(); b = missing[v].astype(float).dropna()
    if len(a)<2 or len(b)<2:
        print("%-18s 数据不足" % v); continue
    t, p = spstats.ttest_ind(a, b, equal_var=False)
    pooled = np.sqrt(((len(a)-1)*a.var() + (len(b)-1)*b.var())/(len(a)+len(b)-2))
    smd = (a.mean()-b.mean())/pooled if pooled>0 else 0.0
    flag = "  <-- 失衡|SMD|>0.25" if abs(smd)>0.25 else ""
    print("%-18s %10.4f %10.4f %8.2f %8.3f %8.3f%s" % (v, a.mean(), b.mean(), t, p, smd, flag))
    rows_sel.append({"var":v,"mean_present":round(a.mean(),5),"mean_missing":round(b.mean(),5),
                     "welch_t":round(t,2),"p":round(p,3),"SMD":round(smd,3)})
sel = pd.DataFrame(rows_sel)
# 年分布失衡
print("\nde 有值样本年份分布 vs 全样本：")
yr = df.groupby("year").apply(lambda x: pd.Series({
    "n_total":len(x),"n_de":int(x["de"].notna().sum()),
    "cov":round(x["de"].notna().mean(),3),
    "alpha_present":round(x.loc[x["de"].notna(),"ff5_adj_return"].mean(),4) if x["de"].notna().any() else np.nan,
    "alpha_missing":round(x.loc[x["de"].isna(),"ff5_adj_return"].mean(),4) if x["de"].isna().any() else np.nan,
}))
print(yr.to_string())

# =====================================================================
# (2) de_avail 指示本身是否预测 alpha
# =====================================================================
print("\n" + "="*72)
print("(2) de_avail 指示对 alpha 的预测力（控制除 de 外全 RHS + 年份 FE，双向聚类）")
rhs_c = [r+"_w" for r in (CONT+FF5+L1+L2+L3+L4+["lsv","risk_asym"])] + ["de_avail"]
bd, td, pd_, Nd, nfd = est(df, rhs_c, "de_avail")
print("  de_avail β=%.4f t=%.2f p=%.3f %s  (N=%d, funds=%d)" % (bd, td, pd_, stars(pd_), Nd, nfd))
bd0, td0, pd0, Nd0, nfd0 = est(df, ["de_avail"], "de_avail")
print("  仅 de_avail + FE（无控制）：β=%.4f t=%.2f p=%.3f %s" % (bd0, td0, pd0, stars(pd0)))

# =====================================================================
# (3) 敏感性电池
# =====================================================================
print("\n" + "="*72)
print("(3) de 敏感性电池（DV=ff5_adj_return_w，全变量缩尾，双向聚类）")
rows = []
def add(name, beta, t, p, N, nf, extra=""):
    rows.append({"spec":name,"de_beta":round(beta,5),"t2w":round(t,2),"p2w":round(p,3),
                 "stars":stars(p),"N":N,"funds":nf,"note":extra})

# A 基线 de-present only
bA,tA,pA,NA,nfA = est(df, [r+"_w" for r in ALLRHS], "de_w")
add("A 基线(de-present only)", bA,tA,pA,NA,nfA, "对照 t-2.99")

# de 在有值样本上的均值/标准差（用于最坏情形插补）
de_present_vals = df["de"].dropna()
de_m, de_s = de_present_vals.mean(), de_present_vals.std()
print("\n  de 有值样本：mean=%.4f sd=%.4f" % (de_m, de_s))

# B 均值插补 + de_avail
dfB = df.copy()
dfB["de_w_imp"] = dfB["de_w"].fillna(de_m)
rhsB = [r+"_w" for r in (CONT+FF5+L1+L2+L3+L4+["lsv","risk_asym"])] + ["de_w_imp","de_avail"]
bB,tB,pB,NB,nfB = est(dfB, rhsB, "de_w_imp")
bAv,tAv,pAv,_,_ = est(dfB, rhsB, "de_avail")
add("B 均值插补+de_avail", bB,tB,pB,NB,nfB, "de_avail beta=%.4f t=%.2f %s" % (bAv,tAv,stars(pAv)))

# C 最坏情形·低 de（缺失=mean-2sd，最自律）
dfC = df.copy()
dfC["de_w_imp"] = dfC["de_w"].fillna(de_m - 2*de_s)
bC,tC,pC,NC,nfC = est(dfC, rhsB, "de_w_imp")
bCv,_,_,_,_ = est(dfC, rhsB, "de_avail")
add("C 最坏·低de(mean-2sd)", bC,tC,pC,NC,nfC, "de_avail beta=%.4f" % bCv)

# D 最坏情形·高 de（缺失=mean+2sd，最差行为）
dfD = df.copy()
dfD["de_w_imp"] = dfD["de_w"].fillna(de_m + 2*de_s)
bD,tD,pD,ND,nfD = est(dfD, rhsB, "de_w_imp")
bDv,_,_,_,_ = est(dfD, rhsB, "de_avail")
add("D 最坏·高de(mean+2sd)", bD,tD,pD,ND,nfD, "de_avail beta=%.4f" % bDv)

# E de_avail 仅（不放 de）
rhsE = [r+"_w" for r in (CONT+FF5+L1+L2+L3+L4+["lsv","risk_asym"])] + ["de_avail"]
bE,tE,pE,NE,nfE = est(df, rhsE, "de_avail")
add("E de_avail仅(无de)", float("nan"), tE, pE, NE, nfE, "de_avail beta=%.4f t=%.2f %s" % (bE,tE,stars(pE)))

# F 仅 2016+ 的 de-present 子样本（隔离时期选择）
dfF = df[(df["year"]>=2016) & (df["de"].notna())].copy()
bF,tF,pF,NF,nfF = est(dfF, [r+"_w" for r in ALLRHS], "de_w")
add("F 仅2016+ de-present", bF,tF,pF,NF,nfF, "隔离 2006-2015 缺失主导")

res = pd.DataFrame(rows)
print("\n" + res.to_string(index=False))

# =====================================================================
# 威胁评估小结
# =====================================================================
print("\n" + "="*72)
print("(4) 威胁评估")
print("  - 基线 A：de beta=%.5f t=%.2f %s" % (bA,tA,stars(pA)))
print("  - 均值插补 B：de beta=%.5f t=%.2f %s" % (bB,tB,stars(pB)))
print("  - 最坏情形 C/D 边界：de beta in [%.5f, %.5f]" % (min(bC,bD), max(bC,bD)))
print("  - de_avail 在 B/C/D 中 |t| 最大值：%.2f" % (max(abs(bAv),abs(bCv),abs(bDv))))
print("  - 2016+ 子样本 F：de beta=%.5f t=%.2f %s" % (bF,tF,stars(pF)))

out = os.path.join(HERE, "output", "de_选择性审计_2026-08-16.csv")
os.makedirs(os.path.dirname(out), exist_ok=True)
res.to_csv(out, index=False)
sel.to_csv(os.path.join(HERE, "output", "de_组间可比性_2026-08-16.csv"), index=False)
print("\n保存:", out, "及 组间可比性表")
