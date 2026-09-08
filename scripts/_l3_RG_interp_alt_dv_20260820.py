"""RG_interp 对替代因变量的预测力（排除 alpha 机械重叠）。
载入 output/RG_interp_2026-08-20.csv，合并面板，跑 future_return / lead alpha / lead excess。
"""
import os, numpy as np, pandas as pd
import statsmodels.formula.api as smf
from scipy import stats as spstats
ROOT="D:/Desktop/基金经理行为分析研究"
PANEL=f"{ROOT}/指标计算流水线/output/主分析面板_重建_含TOwind.csv"
RG=f"{ROOT}/output/RG_interp_2026-08-20.csv"
pan=pd.read_csv(PANEL,dtype={"fund_code":str})
rg=pd.read_csv(RG,encoding="utf-8-sig")
def nf(s): return str(int(float(s)))
pan["fund_code"]=pan["fund_code"].apply(nf); rg["fund_code"]=rg["fund_code"].apply(nf)
pan=pan.merge(rg,on=["fund_code","report_date"],how="left")
pan["log_aum"]=np.log(pd.to_numeric(pan["avg_aum"],errors="coerce").clip(lower=1e-9))
for c in ["ff5_adj_return","future_return","excess_return"]:
    pan[c]=pd.to_numeric(pan[c],errors="coerce")
pan=pan.sort_values(["fund_code","year","quarter"])
for c in ["ff5_adj_return","excess_return"]:
    pan[c+"_lead"]=pan.groupby("fund_code")[c].shift(-1)
FF5=["ff5_MKT_excess","ff5_SMB","ff5_HML","ff5_RMW","ff5_CMA"];CONT=["log_aum"]
L1=["log_fund_age","mgr_total_tenure_v2"];L2=["AS_improved","ICI","industry_hhi"]
L4=["ARG","return_volatility"];L5=["de","lsv","risk_asym"]
CTRL=CONT+FF5+L1+L2+L4+L5
def winsor(s):
    s=s.astype(float);lo,hi=s.quantile(.01),s.quantile(.99);return s.clip(lo,hi)
for v in CTRL+["RG_interp","future_return","ff5_adj_return_lead","excess_return_lead","ff5_adj_return"]:
    pan[v+"_w"]=winsor(pd.to_numeric(pan[v],errors="coerce"))
def meat(gr,X,res):
    k=X.shape[1];m=np.zeros((k,k))
    for gg in np.unique(gr):
        mm=gr==gg;s=X[mm].T@res[mm];m+=np.outer(s,s)
    return m
def ow(X,res,gr):return np.linalg.inv(X.T@X)@meat(gr,X,res)@np.linalg.inv(X.T@X)
def tw(X,res,a,b):
    ab=np.array([f"{x}|{y}" for x,y in zip(a,b)])
    return ow(X,res,a)+ow(X,res,b)-ow(X,res,ab)
def st(p):return "***" if p<.01 else "**" if p<.05 else "*" if p<.1 else "n.s."
print("="*70);print("RG_interp 对替代因变量（双向聚类 CGM2011）");print("="*70)
for dv in ["future_return","ff5_adj_return_lead","excess_return_lead"]:
    rhs=[r+"_w" for r in CTRL]+["RG_interp_w"]
    d=pan.dropna(subset=rhs+[dv+"_w"]).copy()
    m=smf.ols(f"{dv}_w ~ "+" + ".join(rhs)+" + C(year)",data=d).fit(cov_type="cluster",cov_kwds={"groups":d["fund_code"]})
    X=np.asarray(m.model.data.exog,float);res=np.asarray(m.resid,float)
    V2=tw(X,res,d["fund_code"].values.astype(str),d["year"].values.astype(str))
    se2=np.sqrt(np.maximum(np.diag(V2),0));i=[i for i,nm in enumerate(m.params.index) if nm=="RG_interp_w"][0]
    t2=m.params.values[i]/se2[i];p2=2*spstats.t.sf(abs(t2),df=len(res)-X.shape[1])
    print(f"DV={dv:22s} N={int(m.nobs)} R²={m.rsquared:.4f}  RG_interp β={m.params.values[i]:+.5f} t2w={t2:+.2f} p2w={p2:.3f} {st(p2)}")
