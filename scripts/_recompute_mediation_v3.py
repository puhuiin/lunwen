# -*- coding: utf-8 -*-
"""精确复刻 v3 JSON mediate()：仅按 [X_w, M_w, Y_w] 三列 dropna（控制变量缺失由
smf.ols 内部再剔除），并补算间接效应 bootstrap p 值。输出与 v3 JSON E_mediation
完全对齐的 a/b/ind/CI/ind_p，供 §4.11/§5.1 回填。"""
import json, warnings, numpy as np, pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
warnings.filterwarnings("ignore")

PANEL = r"指标计算流水线/output/主分析面板_重建_含TOwind.csv"
df = pd.read_csv(PANEL)
df["log_aum"] = np.log(df["avg_aum"].clip(lower=1e-9))
df["ff5_adj_return"] = pd.to_numeric(df["ff5_adj_return"], errors="coerce")

CONT=["log_aum"]; FF5=["ff5_MKT_excess","ff5_SMB","ff5_HML","ff5_RMW","ff5_CMA"]
L1=["log_fund_age","mgr_total_tenure_v2"]; L2=["AS_improved","ICI","industry_hhi"]
L3=["SDI","TO_wind"]; L4=["ARG","return_volatility"]; L5=["de","lsv","risk_asym"]
ALLRHS=CONT+FF5+L1+L2+L3+L4+L5
def winsor(s):
    s=s.astype(float); lo,hi=s.quantile(0.01),s.quantile(0.99); return s.clip(lo,hi)
for v in ALLRHS+["ff5_adj_return"]:
    df[v+"_w"]=winsor(df[v])
Y="ff5_adj_return_w"
m4_rhs=CONT+FF5+L1+L2+L3+L4+L5

def mediate(Xname,Mname):
    # 仅按 [X_w, M_w, Y_w] dropna —— 复刻 v3 JSON
    d=df.dropna(subset=[Xname+"_w",Mname+"_w",Y]).copy()
    # a 路径：原始表达式用 RAW Mname/Xname（v3 JSON 无 _w）
    a=smf.ols(f"{Mname} ~ {Xname}",data=d).fit()
    ctrl=[r for r in m4_rhs if r!=Xname]
    # b 路径：原始表达式用 RAW Mname/Xname/ctrl，Y 为 _w（v3 JSON 混合口径）
    form=f"{Y} ~ {Mname} + {Xname} + "+" + ".join(ctrl)
    b=smf.ols(form,data=d).fit()
    a_coef=a.params[Xname]; b_coef=b.params[Mname]
    ind=a_coef*b_coef
    rng=np.random.default_rng(20260815); idx=np.arange(len(d)); bs=[]
    for _ in range(500):
        s=rng.choice(idx,size=len(idx),replace=True); dd=d.iloc[s]
        aa=smf.ols(f"{Mname} ~ {Xname}",data=dd).fit()
        bb=smf.ols(form,data=dd).fit()
        bs.append(aa.params[Xname]*bb.params[Mname])
    bs=np.array(bs)
    ci=(round(float(np.percentile(bs,2.5)),5),round(float(np.percentile(bs,97.5)),5))
    p=round(2*float(min((bs<=0).mean(),(bs>=0).mean())),4)
    return dict(a=round(float(a_coef),4),b=round(float(b_coef),4),
                ind=round(float(ind),5),ci=ci,bt=round(float(b.tvalues[Mname]),3),
                bp=round(float(b.pvalues[Mname]),4),ind_p=p,N=int(len(d)))

paths=[("lsv","return_volatility","LSV_RV"),("risk_asym","return_volatility","RA_RV"),
       ("de","return_volatility","DE_RV"),("lsv","TO_wind","LSV_TO"),
       ("risk_asym","TO_wind","RA_TO"),("de","TO_wind","DE_TO")]
res={}
for X,M,name in paths:
    res[name]=mediate(X,M)
    r=res[name]
    sig_mark = "✓**" if (r["ci"][0]>0 or r["ci"][1]<0) else ("✓*(边际)" if r["ind_p"]<0.1 else "✗")
    print(f"{name}: a={r['a']} b={r['b']} ind={r['ind']} CI={r['ci']} bt={r['bt']} ind_p={r['ind_p']} N={r['N']} -> {sig_mark}")

json.dump(res,open("_recompute_mediation_v3.json","w",encoding="utf-8"),ensure_ascii=False,indent=1)
print("\nsaved _recompute_mediation_v3.json (与 v3 JSON E_mediation 对齐)")
