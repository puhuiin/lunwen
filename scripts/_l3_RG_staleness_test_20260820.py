"""纯净对照：隔离'插值'效应。
同一 v2 持仓源 + 同一对齐 + 同一聚合，仅差异：
  A) RG_interp  : 过去两快照合法插值（仅 Q1 生效）
  B) RG_nointerp: 永远用最近过去快照（=原始口径，v2源）
两者都测 future_return（无 alpha 机械重叠）。若 B 不显著而 A 显著 → 滞后导致伪零。
"""
import os, numpy as np, pandas as pd
import statsmodels.formula.api as smf
from scipy import stats as spstats
ROOT="D:/Desktop/基金经理行为分析研究"
PANEL=f"{ROOT}/指标计算流水线/output/主分析面板_重建_含TOwind.csv"
HOLD=f"{ROOT}/指标计算流水线/data/L2_持仓偏离层/基金持仓明细_全量修正版_v2.csv"
STK=f"{ROOT}/指标计算流水线/data/股价行情/个股月收益率_全量.csv"
def nf(s): return str(int(float(s)))
sm=pd.read_csv(STK,encoding="utf-8-sig"); sm["stock_code"]=sm["stock_code"].astype(str).str.zfill(6)
sm["date"]=pd.to_datetime(sm["date"]); sm["yrq"]=sm["date"].dt.to_period("Q"); sm["r"]=pd.to_numeric(sm["monthly_return"],errors="coerce")
g=sm.groupby(["stock_code","yrq"])["r"].apply(lambda x:np.prod(1+x.dropna())-1)
stock_q={(str(k[0]).zfill(6),int(k[1].year),int(k[1].quarter)):float(v) for k,v in g.items()}
h=pd.read_csv(HOLD,encoding="utf-8-sig",low_memory=False)
h["fund_code"]=h["fund_code"].apply(nf); h["stock_code"]=h["stock_code"].astype(str).str.zfill(6)
h["w"]=pd.to_numeric(h["hold_ratio"],errors="coerce").fillna(0)/100.0
h["rd"]=pd.to_datetime(h["report_date"]); h["q"]=h["rd"].dt.to_period("Q")
snaps={}
for fc,fdf in h.groupby("fund_code"):
    fdf=fdf.sort_values("rd")
    snaps[fc]=list(zip(fdf["q"],fdf["rd"],[dict(zip(gg["stock_code"],gg["w"])) for _,gg in fdf.groupby("q")]))
pan=pd.read_csv(PANEL,dtype={"fund_code":str}); pan["fund_code"]=pan["fund_code"].apply(nf)
pan["rd"]=pd.to_datetime(pan["report_date"]); pan["q"]=pan["rd"].dt.to_period("Q"); pan["qr"]=pd.to_numeric(pan["quarter_return"],errors="coerce")
def port_ret(wmap,y,qn):
    port=0.0;ws=0.0
    for stk,w in wmap.items():
        sr=stock_q.get((stk,y,qn))
        if sr is not None and not pd.isna(sr): port+=w*sr;ws+=w
    return port/ws if ws>0 else np.nan
rowsA=[];rowsB=[]
for _,r in pan[["fund_code","report_date","rd","q","qr"]].iterrows():
    fc=r["fund_code"];q=r["q"];tgt=r["rd"];qr=r["qr"];rd=r["report_date"]
    if pd.isna(qr): rowsA.append((fc,rd,np.nan));rowsB.append((fc,rd,np.nan));continue
    sp=snaps.get(fc)
    if not sp: rowsA.append((fc,rd,np.nan));rowsB.append((fc,rd,np.nan));continue
    past=[(s[0],s[1],s[2]) for s in sp if s[1]<=tgt]
    if not past: rowsA.append((fc,rd,np.nan));rowsB.append((fc,rd,np.nan));continue
    ps=sorted(past,key=lambda x:x[1]); p1=ps[-1]; p0=ps[-2] if len(ps)>=2 else None
    # A 插值
    if p0 is not None and p0[1]<tgt<p1[1]:
        span=(p1[1]-p0[1]).days; f=(tgt-p0[1]).days/span if span>0 else 0
        wA={}
        for stk in set(p0[2])|set(p1[2]): wA[stk]=p0[2].get(stk,0)*(1-f)+p1[2].get(stk,0)*f
    else: wA=p1[2]
    # B 最近过去
    wB=p1[2]
    y,qn=int(q.year),int(q.quarter)
    pA=port_ret(wA,y,qn); pB=port_ret(wB,y,qn)
    rowsA.append((fc,rd,(qr-pA) if not pd.isna(pA) else np.nan))
    rowsB.append((fc,rd,(qr-pB) if not pd.isna(pB) else np.nan))
RA=pd.DataFrame(rowsA,columns=["fund_code","report_date","RG_interp"])
RB=pd.DataFrame(rowsB,columns=["fund_code","report_date","RG_nointerp"])
pan=pan.merge(RA,on=["fund_code","report_date"],how="left").merge(RB,on=["fund_code","report_date"],how="left")
pan["log_aum"]=np.log(pd.to_numeric(pan["avg_aum"],errors="coerce").clip(lower=1e-9))
pan["future_return"]=pd.to_numeric(pan["future_return"],errors="coerce")
FF5=["ff5_MKT_excess","ff5_SMB","ff5_HML","ff5_RMW","ff5_CMA"];CONT=["log_aum"]
L1=["log_fund_age","mgr_total_tenure_v2"];L2=["AS_improved","ICI","industry_hhi"]
L4=["ARG","return_volatility"];L5=["de","lsv","risk_asym"];CTRL=CONT+FF5+L1+L2+L4+L5
def winsor(s):s=s.astype(float);lo,hi=s.quantile(.01),s.quantile(.99);return s.clip(lo,hi)
for v in CTRL+["RG_interp","RG_nointerp","future_return"]:
    pan[v+"_w"]=winsor(pd.to_numeric(pan[v],errors="coerce"))
def meat(gr,X,res):
    k=X.shape[1];m=np.zeros((k,k))
    for gg in np.unique(gr):
        mm=gr==gg;s=X[mm].T@res[mm];m+=np.outer(s,s)
    return m
def ow(X,res,gr):return np.linalg.inv(X.T@X)@meat(gr,X,res)@np.linalg.inv(X.T@X)
def tw(X,res,a,b):
    ab=np.array([f"{x}|{y}" for x,y in zip(a,b)]);return ow(X,res,a)+ow(X,res,b)-ow(X,res,ab)
def st(p):return "***" if p<.01 else "**" if p<.05 else "*" if p<.1 else "n.s."
print("="*70);print("纯净对照：插值 vs 最近过去（同v2源/同对齐），DV=future_return");print("="*70)
for col in ["RG_interp","RG_nointerp"]:
    rhs=[r+"_w" for r in CTRL]+[col+"_w"]
    d=pan.dropna(subset=rhs+["future_return_w"]).copy()
    m=smf.ols("future_return_w ~ "+" + ".join(rhs)+" + C(year)",data=d).fit(cov_type="cluster",cov_kwds={"groups":d["fund_code"]})
    X=np.asarray(m.model.data.exog,float);res=np.asarray(m.resid,float)
    V2=tw(X,res,d["fund_code"].values.astype(str),d["year"].values.astype(str))
    se2=np.sqrt(np.maximum(np.diag(V2),0));i=[i for i,nm in enumerate(m.params.index) if nm==col+"_w"][0]
    t2=m.params.values[i]/se2[i];p2=2*spstats.t.sf(abs(t2),df=len(res)-X.shape[1])
    print(f"{col:14s} N={int(m.nobs)} R²={m.rsquared:.4f}  β={m.params.values[i]:+.5f} t2w={t2:+.2f} p2w={p2:.3f} {st(p2)}")
