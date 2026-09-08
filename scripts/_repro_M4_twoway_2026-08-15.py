# -*- coding: utf-8 -*-
"""M4 权威重算（2026-08-15 深度优化）：在诚实面板 + 稿件精确 RHS（5 FF5 + 13 行为/控制，
无 gender/cfa/edu）+ C(year) 下，计算 M4 系数、单维基金聚类 SE 与基金×年双向聚类 SE（CGM 2011），
并与 merged_manuscript.html §4.2.8 现载数值逐项对账。仅读面板，产出对比表，不改动任何交付物。"""
import json, warnings, numpy as np, pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from scipy import stats as _tstats
warnings.filterwarnings("ignore")

PANEL = r"指标计算流水线/output/主分析面板_重建_含TOwind.csv"
df = pd.read_csv(PANEL, dtype={"fund_code": str})
df["report_date"] = df["report_date"].astype(str)
df["year"] = df["report_date"].str[:4].astype(int)
df["log_aum"] = np.log(df["avg_aum"].clip(lower=1e-9))

# 与稿件一致：1%/99% 缩尾
def wins(s, lo=0.01, hi=0.99):
    s = s.astype(float); a, b = s.quantile(lo), s.quantile(hi); return s.clip(a, b)
RHS = ["ff5_MKT_excess","ff5_SMB","ff5_HML","ff5_RMW","ff5_CMA",
       "log_aum","log_fund_age","mgr_total_tenure_v2",
       "AS_improved","ICI","industry_hhi","SDI","TO_wind",
       "ARG","return_volatility","de","lsv","risk_asym"]
for c in RHS + ["ff5_adj_return"]:
    df[c] = wins(df[c])

form = "ff5_adj_return ~ " + " + ".join(RHS) + " + C(year)"
sub = df.dropna(subset=["ff5_adj_return"]+RHS).copy()
m = smf.ols(form, data=sub).fit(cov_type="cluster", cov_kwds={"groups": sub["fund_code"]})

# ---- CGM 双向聚类（fund × year）----
X = m.model.data.exog.astype(float)          # 设计矩阵（含截距 + 年份哑变量）
resid = m.resid.astype(float)
g1 = sub["fund_code"].values.astype(str)
g2 = sub["year"].values.astype(str)
def _meat(groups):
    k = X.shape[1]; meat = np.zeros((k, k))
    for gg in np.unique(groups):
        mm = groups == gg; s = X[mm].T @ resid[mm]; meat += np.outer(s, s)
    return meat
def _oneway(groups):
    XtX_inv = np.linalg.inv(X.T @ X); return XtX_inv @ _meat(groups) @ XtX_inv
g12 = np.array([f"{a}|{b}" for a, b in zip(g1, g2)])
V = _oneway(g1) + _oneway(g2) - _oneway(g12)
se2 = np.sqrt(np.maximum(np.diag(V), 0))
beta = m.params.values
t2 = beta / se2
p2 = 2.0 * _tstats.t.sf(np.abs(t2), df=len(resid) - X.shape[1])

# 单维基金聚类（statsmodels 自带）
se1 = m.bse.values; t1 = m.tvalues.values; p1 = m.pvalues.values

names = list(m.params.index)
# 现载稿件数值（手稿 §4.2.8，供对账）
ms = {
 "log_aum":(+0.00069,+1.21),"ff5_MKT_excess":(-0.03477,-2.67),"ff5_SMB":(+0.01152,+1.38),
 "ff5_HML":(+0.05353,+3.48),"ff5_RMW":(-0.05213,-2.64),"ff5_CMA":(-0.11291,-3.22),
 "log_fund_age":(-0.00429,-2.64),"mgr_total_tenure_v2":(0.00000,+0.99),
 "AS_improved":(-0.03217,-3.16),"ICI":(+0.01789,+3.63),"industry_hhi":(+0.01146,+0.26),
 "SDI":(+0.00003,+0.02),"TO_wind":(0.00000,+0.96),"ARG":(+0.01625,+2.65),
 "return_volatility":(+0.02379,+1.07),"de":(-0.00606,-2.50),"lsv":(+0.01548,+1.23),
 "risk_asym":(+0.07311,+4.53)}

print("="*100)
print(f"M4 精确 RHS | N={int(m.nobs)} 基金={sub.fund_code.nunique()} R2={m.rsquared:.4f} adjR2={m.rsquared_adj:.4f}")
print("="*100)
print(f"{'变量':18s}{'β(本跑)':>11s}{'t1w(单)':>10s}{'t2w(双向)':>11s}{'p2w':>9s}{'β(稿件)':>11s}{'t(稿件)':>9s}{'Δβ':>9s}{'Δt2w':>8s}")
print("-"*100)
for i, nm in enumerate(names):
    if nm == "Intercept" or nm.startswith("C(year)"):
        continue
    key = nm
    b = beta[i]; tt1 = t1[i]; tt2 = t2[i]; pp2 = p2[i]
    mb, mt = ms.get(key, (np.nan, np.nan))
    d_b = b - mb if not np.isnan(mb) else np.nan
    d_t = tt2 - mt if not np.isnan(mt) else np.nan
    star = "" if pp2>0.10 else ("*" if pp2>0.05 else ("**" if pp2>0.01 else "***"))
    print(f"{key:18s}{b:+11.5f}{tt1:+10.2f}{tt2:+11.2f}{pp2:9.4f}{mb:+11.5f}{mt:+9.2f}{d_b:+9.5f}{d_t:+8.2f}  {star}")
print("-"*100)
print(f"R2 本跑={m.rsquared:.4f}  稿件=0.129  Δ={m.rsquared-0.129:+.4f}")
print("[DONE]")
