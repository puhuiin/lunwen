# -*- coding: utf-8 -*-
"""
PS 五分位 / 单调性 / Logistic / 八画像 —— v4 权威面板全链路重算
严格复刻 _repro_all_OptionA_2026-08-15.py 的管线：
  面板 -> log_aum -> 1%/99% 缩尾 -> M4 完整观测集(N=2264) -> M4 簇稳健系数 -> PS 加权
内置复现校验：B.M4 必须 = N 2264 / 348 基金 / R2 0.129；权重须匹配已发表 |β|
输出: output/ps_v4_recalc_20260822.json
"""
import json, warnings, numpy as np, pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from scipy import stats as st

warnings.filterwarnings("ignore")

PANEL = r"指标计算流水线/output/主分析面板_重建_含TOwind.csv"
OUT = r"output/ps_v4_recalc_20260822.json"

df = pd.read_csv(PANEL)
df["log_aum"] = np.log(df["avg_aum"].clip(lower=1e-9))
df["ff5_adj_return"] = pd.to_numeric(df["ff5_adj_return"], errors="coerce")

CONT = ["log_aum"]
FF5  = ["ff5_MKT_excess","ff5_SMB","ff5_HML","ff5_RMW","ff5_CMA"]
L1   = ["log_fund_age","mgr_total_tenure_v2"]
L2   = ["AS_improved","ICI","industry_hhi"]
L3   = ["SDI","TO_wind"]
L4   = ["ARG","return_volatility"]
L5   = ["de","lsv","risk_asym"]
ALLRHS = CONT + FF5 + L1 + L2 + L3 + L4 + L5

def winsor(s):
    s = s.astype(float)
    lo, hi = s.quantile(0.01), s.quantile(0.99)
    return s.clip(lo, hi)

for v in ALLRHS + ["ff5_adj_return"]:
    df[v+"_w"] = winsor(df[v])

m4_rhs = CONT + FF5 + L1 + L2 + L3 + L4 + L5
m4d = df.dropna(subset=[r+"_w" for r in m4_rhs]+["ff5_adj_return_w"]).copy()
form = "ff5_adj_return_w ~ " + " + ".join(r+"_w" for r in m4_rhs) + " + C(year)"
m4 = smf.ols(form, data=m4d).fit(cov_type="cluster", cov_kwds={"groups": m4d["fund_code"]})

# ---------- 复现校验 ----------
chk = {
    "N": len(m4d), "funds": m4d["fund_code"].nunique(),
    "R2": round(m4.rsquared, 4),
}
print("=== 复现校验 ===")
print(f"M4: N={chk['N']} funds={chk['funds']} R2={chk['R2']}")
assert chk["N"] == 2264 and chk["funds"] == 348, "M4 样本与权威口径不符！"
assert abs(chk["R2"] - 0.129) < 0.0011, "M4 R² 与权威值 0.129 不符！"

W = {}
for v in L5:
    W[v] = dict(beta=round(m4.params[v+"_w"],5), t=round(m4.tvalues[v+"_w"],2))
print("L5 系数:", W)
assert abs(abs(W["risk_asym"]["beta"]) - 0.07311) < 5e-4
assert abs(abs(W["lsv"]["beta"]) - 0.01548) < 5e-4
assert abs(abs(W["de"]["beta"]) - 0.00606) < 5e-4
print("[OK] 三权重与已发表值一致")

# ---------- PS 得分（与 OptionA-H 完全一致：m4d 上原始列 Z 化）----------
zw = {v: (m4d[v]-m4d[v].mean())/m4d[v].std() for v in L5}
ps = (-abs(W["de"]["beta"])*zw["de"] + abs(W["lsv"]["beta"])*zw["lsv"]
      + abs(W["risk_asym"]["beta"])*zw["risk_asym"])
m4d["_ps"] = ps.values

H = dict(N=len(m4d), funds=int(chk["funds"]),
         ps_mean=round(float(ps.mean()),4), ps_std=round(float(ps.std()),4),
         ps_min=round(float(ps.min()),4), ps_max=round(float(ps.max()),4),
         weights={v: abs(W[v]["beta"]) for v in L5})
print("=== H PS 描述性统计(v4) ===")
print(H)

# ---------- 五分位 ----------
m4d["_psq"] = pd.qcut(m4d["_ps"], 5, labels=["Q1","Q2","Q3","Q4","Q5"])
g = m4d.groupby("_psq", observed=False)["ff5_adj_return_w"]
quint = {}
for qname, s in g:
    quint[qname] = dict(n=int(s.count()),
                        alpha_mean=round(float(s.mean()),4),
                        alpha_median=round(float(s.median()),4),
                        alpha_std=round(float(s.std()),4),
                        ps_mean=round(float(m4d.loc[s.index,"_ps"].mean()),4))
means = [quint[q]["alpha_mean"] for q in ["Q1","Q2","Q3","Q4","Q5"]]
a_q1 = m4d.loc[m4d["_psq"]=="Q1","ff5_adj_return_w"]
a_q5 = m4d.loc[m4d["_psq"]=="Q5","ff5_adj_return_w"]
tt = st.ttest_ind(a_q5, a_q1, equal_var=False)
rho, rho_p = st.spearmanr([1,2,3,4,5], means)
tr = sm.OLS(means, sm.add_constant([1,2,3,4,5])).fit()
mono = dict(q5_q1_spread=round(float(a_q5.mean()-a_q1.mean()),4),
            spread_t=round(float(tt.statistic),2), spread_p=float(tt.pvalue),
            spearman_rho=round(float(rho),4), spearman_p=float(rho_p),
            trend_slope=round(float(tr.params[1]),4),
            trend_t=round(float(tr.tvalues[1]),2), trend_p=float(tr.pvalues[1]))
print("=== 五分位(v4) ===")
for k,v in quint.items(): print(" ",k,v)
print(" ", mono)

# ---------- PS 与 alpha 的相关/回归 ----------
pr, pp_ = st.pearsonr(m4d["_ps"], m4d["ff5_adj_return_w"])
reg = sm.OLS(m4d["ff5_adj_return_w"], sm.add_constant(m4d["_ps"])).fit()
corrblk = dict(pearson_r=round(float(pr),4), pearson_p=float(pp_),
               reg_beta=round(float(reg.params.iloc[1]),4),
               reg_t=round(float(reg.tvalues.iloc[1]),2),
               reg_r2=round(float(reg.rsquared),4))
print("=== 相关/回归 ===", corrblk)

# ---------- Logistic：alpha>中位数 ----------
y = (m4d["ff5_adj_return_w"] > m4d["ff5_adj_return_w"].median()).astype(int)
X = sm.add_constant(m4d[["de_w","lsv_w","risk_asym_w","log_aum_w"]])
lg = sm.Logit(y, X).fit(disp=0)
pred = lg.predict(X)
acc = float(((pred>0.5).astype(int)==y).mean())
# AUC via Mann-Whitney
r_ = st.rankdata(pred)
n1, n0 = int(y.sum()), int((1-y).sum())
u1 = float(r_[y==1].sum()) - n1*(n1+1)/2
auc = u1/(n1*n0)
lgt = {"pseudo_r2": round(float(lg.prsquared),4),
       "accuracy": round(acc,4), "auc": round(auc,4),
       "coef": {k: dict(coef=round(float(lg.params[k]),3), z=round(float(lg.tvalues[k]),2),
                         p=float(lg.pvalues[k]))
                for k in ["const","de_w","lsv_w","risk_asym_w","log_aum_w"]}}
print("=== Logistic(v4) ===")
print(json.dumps(lgt, ensure_ascii=False, indent=1))

# ---------- 八画像 ----------
meds = {v: m4d[v].median() for v in L5}
PROF = [("理性止损型",0,0,0),("自信止损型",0,0,1),("从众止损型",0,1,0),("自信从众型",0,1,1),
        ("固执独立型",1,0,0),("过度自信型",1,0,1),("固执从众型",1,1,0),("冲动型",1,1,1)]
prof = {}
al = m4d["ff5_adj_return_w"]
hi = {v: (m4d[v] > meds[v]) for v in L5}
for name, d_, l_, r_ in PROF:
    msk = pd.Series(True, index=m4d.index)
    if d_: msk &= hi["de"]
    else:  msk &= ~hi["de"]
    if l_: msk &= hi["lsv"]
    else:  msk &= ~hi["lsv"]
    if r_: msk &= hi["risk_asym"]
    else:  msk &= ~hi["risk_asym"]
    sub = al[msk]
    prof[name] = dict(n=int(sub.count()), pct=round(100*sub.count()/len(m4d),1),
                      alpha_mean=round(float(sub.mean()),4),
                      alpha_median=round(float(sub.median()),4),
                      ps_mean=round(float(m4d.loc[sub.index,"_ps"].mean()),4))
best = max(prof, key=lambda k: prof[k]["alpha_mean"])
worst = min(prof, key=lambda k: prof[k]["alpha_mean"])
# 直接按掩码取组内 alpha 做 Welch t
def mask_of(name):
    for nm,d_,l_,r_ in PROF:
        if nm==name:
            msk = pd.Series(True, index=m4d.index)
            msk &= (hi["de"] if d_ else ~hi["de"])
            msk &= (hi["lsv"] if l_ else ~hi["lsv"])
            msk &= (hi["risk_asym"] if r_ else ~hi["risk_asym"])
            return msk
mb, mw = mask_of(best), mask_of(worst)
tb = st.ttest_ind(al[mb], al[mw], equal_var=False)
prof_blk = dict(profiles=prof, best=best, worst=worst,
                spread=round(float(al[mb].mean()-al[mw].mean()),4),
                t=round(float(tb.statistic),2), p=float(tb.pvalue))
print("=== 八画像(v4) ===")
print(json.dumps(prof_blk, ensure_ascii=False, indent=1))

result = dict(checks=chk, coefs_L5=W, H_ps=H, quintiles=quint,
              monotonicity=mono, correlation=corrblk, logistic=lgt, profiles=prof_blk)
with open(OUT,"w",encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
print("\nDONE ->", OUT)
