"""修正核验：仅用 v2 的 6月/12月 全持仓快照（剔除3/9月前十大），最近过去、无前视、无插值，
重算干净 RG（RG_clean），并与原 RG（非v2）交叉验证 + 检验未来收益/alpha。
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
# 仅保留 6月/12月 全持仓快照
h=h[h["rd"].dt.month.isin([6,12])]
snaps={}
for fc,fdf in h.groupby("fund_code"):
    fdf=fdf.sort_values("rd"); snaps[fc]=list(zip(fdf["q"],fdf["rd"],[dict(zip(gg["stock_code"],gg["w"])) for _,gg in fdf.groupby("q")]))
pan=pd.read_csv(PANEL,dtype={"fund_code":str}); pan["fund_code"]=pan["fund_code"].apply(nf)
pan["rd"]=pd.to_datetime(pan["report_date"]); pan["q"]=pan["rd"].dt.to_period("Q"); pan["qr"]=pd.to_numeric(pan["quarter_return"],errors="coerce")
rows=[]
for _,r in pan[["fund_code","report_date","rd","q","qr"]].iterrows():
    fc=r["fund_code"];q=r["q"];tgt=r["rd"];qr=r["qr"];rd=r["report_date"]
    if pd.isna(qr): rows.append((fc,rd,np.nan)); continue
    sp=snaps.get(fc)
    if not sp: rows.append((fc,rd,np.nan)); continue
    past=[s for s in sp if s[1]<=tgt]   # 最近过去半年频全持仓（无前视、无前十大）
    if not past: rows.append((fc,rd,np.nan)); continue
    wmap=past[-1][2]
    y,qn=int(q.year),int(q.quarter); port=0.0; ws=0.0
    for stk,w in wmap.items():
        sr=stock_q.get((stk,y,qn))
        if sr is not None and not pd.isna(sr): port+=w*sr; ws+=w
    if ws>0 and not pd.isna(port): rows.append((fc,rd,(qr-port)/ws))
    else: rows.append((fc,rd,np.nan))
RG=pd.DataFrame(rows,columns=["fund_code","report_date","RG_clean"])
print(f"RG_clean 非空: {RG['RG_clean'].notna().sum()}/{len(RG)}")
pan=pan.merge(RG,on=["fund_code","report_date"],how="left")
# 与原 RG 相关性
sub=pan.dropna(subset=["RG","RG_clean"])
print(f"RG_clean 与 原RG 相关: {sub[['RG','RG_clean']].corr().iloc[0,1]:.3f} (N={len(sub)})")
# 检验
pan["log_aum"]=np.log(pd.to_numeric(pan["avg_aum"],errors="coerce").clip(lower=1e-9))
for c in ["ff5_adj_return","future_return","ff5_MKT_excess","ff5_SMB","ff5_HML","ff5_RMW","ff5_CMA","log_fund_age","mgr_total_tenure_v2","AS_improved","ICI","industry_hhi","ARG","return_volatility","de","lsv","risk_asym"]:
    pan[c]=pd.to_numeric(pan[c],errors="coerce")
CTRL=["log_aum","ff5_MKT_excess","ff5_SMB","ff5_HML","ff5_RMW","ff5_CMA","log_fund_age","mgr_total_tenure_v2","AS_improved","ICI","industry_hhi","ARG","return_volatility","de","lsv","risk_asym"]
def w(s):s=s.astype(float);lo,hi=s.quantile(.01),s.quantile(.99);return s.clip(lo,hi)
for v in CTRL+["RG_clean","future_return","ff5_adj_return"]: pan[v+"_w"]=w(pan[v])
def meat(gr,X,res):
    k=X.shape[1];m=np.zeros((k,k))
    for gg in np.unique(gr):
        mm=gr==gg;s=X[mm].T@res[mm];m+=np.outer(s,s)
    return m
def ow(X,res,gr):return np.linalg.inv(X.T@X)@meat(gr,X,res)@np.linalg.inv(X.T@X)
def tw(X,res,a,b):
    ab=np.array([f"{x}|{y}" for x,y in zip(a,b)]);return ow(X,res,a)+ow(X,res,b)-ow(X,res,ab)
def st(p):return "***" if p<.01 else "**" if p<.05 else "*" if p<.1 else "n.s."
print("\n=== RG_clean 检验（双向聚类 CGM2011）===")
for dv in ["future_return","ff5_adj_return"]:
    rhs=[r+"_w" for r in CTRL]+["RG_clean_w"]
    d=pan.dropna(subset=rhs+[dv+"_w"]).copy()
    m=smf.ols(f"{dv}_w ~ "+" + ".join(rhs)+" + C(year)",data=d).fit(cov_type="cluster",cov_kwds={"groups":d["fund_code"]})
    X=np.asarray(m.model.data.exog,float);res=np.asarray(m.resid,float)
    V2=tw(X,res,d["fund_code"].values.astype(str),d["year"].values.astype(str))
    se2=np.sqrt(np.maximum(np.diag(V2),0));i=[i for i,nm in enumerate(m.params.index) if nm=="RG_clean_w"][0]
    t2=m.params.values[i]/se2[i];p2=2*spstats.t.sf(abs(t2),df=len(res)-X.shape[1])
    print(f"  DV={dv:16s} N={int(m.nobs)} R²={m.rsquared:.4f}  RG_clean β={m.params.values[i]:+.5f} t2w={t2:+.2f} p2w={p2:.3f} {st(p2)}")
RG.to_csv(f"{ROOT}/output/RG_clean_2026-08-21.csv",index=False,encoding="utf-8-sig")
print("\n[已写出] output/RG_clean_2026-08-21.csv")
