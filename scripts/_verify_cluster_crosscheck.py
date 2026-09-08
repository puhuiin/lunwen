# -*- coding: utf-8 -*-
"""CGM2011 双向聚类实现权威校验：自实现 two_way_V  vs statsmodels 原生双向聚类(groups=2D)。
若两者 t 值一致，证明自实现正确。"""
import os, warnings, numpy as np, pandas as pd
import statsmodels.formula.api as smf
warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PANEL = os.path.join(HERE,"指标计算流水线","output","主分析面板_重建_含TOwind.csv")
panel = pd.read_csv(PANEL, dtype={"fund_code":str})
panel["report_date"]=panel["report_date"].astype(str)
panel["year"]=panel["report_date"].str[:4].astype(int)
FF5=["ff5_MKT_excess","ff5_SMB","ff5_HML","ff5_RMW","ff5_CMA"]
CONT=["log_aum"];L1=["log_fund_age","mgr_total_tenure_v2"];L2=["AS_improved","ICI","industry_hhi"]
L3=["SDI","TO_wind"];L4=["ARG","return_volatility"];L5=["de","lsv","risk_asym"]
ALLRHS=CONT+FF5+L1+L2+L3+L4+L5
panel["log_aum"]=np.log(panel["avg_aum"].clip(lower=1e-9))
panel["ff5_adj_return"]=pd.to_numeric(panel["ff5_adj_return"],errors="coerce")
def wins(s): s=s.astype(float);lo,hi=s.quantile(0.01),s.quantile(0.99);return s.clip(lo,hi)
for v in ALLRHS+["ff5_adj_return"]: panel[v+"_w"]=wins(panel[v])
d=panel.dropna(subset=[r+"_w" for r in ALLRHS]+["ff5_adj_return_w"]).copy()
form="ff5_adj_return_w ~ "+" + ".join(r+"_w" for r in ALLRHS)+" + C(year)"
m=smf.ols(form,data=d).fit(cov_type="cluster",cov_kwds={"groups":d["fund_code"]})  # 单维基金(旧口径)
# 自实现 CGM 双向
X=np.asarray(m.model.data.exog,float); resid=np.asarray(m.resid,float)
def _meat(groups,X,resid):
    k=X.shape[1];meat=np.zeros((k,k))
    for gg in np.unique(groups):
        mm=groups==gg;s=X[mm].T@resid[mm];meat+=np.outer(s,s)
    return meat
def _oneway(X,resid,g): return np.linalg.inv(X.T@X)@_meat(g,X,resid)@np.linalg.inv(X.T@X)
def twoway(X,resid,g1,g2):
    g12=np.array([f"{a}|{b}" for a,b in zip(g1,g2)])
    return _oneway(X,resid,g1)+_oneway(X,resid,g2)-_oneway(X,resid,g12)
g1=d["fund_code"].values.astype(str);g2=d["year"].values.astype(str)
V2=twoway(X,resid,g1,g2);se_m=np.sqrt(np.maximum(np.diag(V2),0));t_m=m.params.values/se_m

# statsmodels 原生双向聚类（簇标号需为数值，整数编码）
fcode_int, _ = pd.factorize(d["fund_code"])
yr_int = d["year"].values.astype(int)
grps=np.column_stack([fcode_int, yr_int]).astype(int)
m2=smf.ols(form,data=d).fit(cov_type="cluster",cov_kwds={"groups":grps,"use_correction":False})
se_s=m2.bse.values; t_s=m2.tvalues.values

names=list(m.params.index)
print("变量(非FE)            t_自实现CGM    t_statsmodels原生    |Δt|")
maxd=0
for i,nm in enumerate(names):
    if nm=="Intercept" or nm.startswith("C(year)"): continue
    base=nm[:-2] if nm.endswith("_w") else nm
    dd=abs(t_m[i]-t_s[i]); maxd=max(maxd,dd)
    print("%-18s %+12.4f %+18.4f %+12.5f"%(base,t_m[i],t_s[i],dd))
print("\nmax|Δt| = %.5f  → 自实现CGM 与 statsmodels 原生双向聚类一致？ %s"%(maxd, maxd<0.05))

# 同时报告 SDI / TO_wind / de / risk_asym 两种口径 t 值
for base in ["SDI","TO_wind","de","risk_asym"]:
    idx=[i for i,n in enumerate(names) if (n==base+"_w" or n==base)][0]
    print("  %-12s manual=%.3f  statsmodels=%.3f"%(base,t_m[idx],t_s[idx]))
