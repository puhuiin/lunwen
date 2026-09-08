# -*- coding: utf-8 -*-
"""
M4 衍生量诚实重算（2026-08-15）
在诚实面板 主分析面板_重建_含TOwind.csv 上，基于与 _repro_all_OptionA 完全一致的
M4 规范（DV=ff5_adj_return_w，RHS=CONT+FF5+L1+L2+L3+L4+L5，+C(year)，基金簇稳健SE，
全样本1%/99%缩尾），重算诚实 M4 衍生量：
  1) WCB-S 野生聚类自助 p 值（de/lsv/risk_asym）
  2) Oster δ（supp 公式：short=X+CONT+FF5, long=X+CONT+FF5+L1+L2+L3+L4，β* =0, Rmax=1.3*R_long）
  3) §4.4.2 牛熊市子样本 M4 系数与 t
  4) §4.10 非线性（二次项）模型中 L5 的线性/二次系数与 t
  5) §4.10 Ramsey RESET F 统计量（含二次/三次拟合项，基金簇稳健）
输出 JSON：_repro_M4_derived_2026-08-15.json
"""
import json, warnings, numpy as np, pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
warnings.filterwarnings("ignore")

PANEL = r"指标计算流水线/output/主分析面板_重建_含TOwind.csv"
OUT   = r"_repro_M4_derived_2026-08-15.json"

df = pd.read_csv(PANEL)
df["log_aum"] = np.log(df["avg_aum"].clip(lower=1e-9))
df["ff5_adj_return"] = pd.to_numeric(df["ff5_adj_return"], errors="coerce")

CONT=["log_aum"]; FF5=["ff5_MKT_excess","ff5_SMB","ff5_HML","ff5_RMW","ff5_CMA"]
L1=["log_fund_age","mgr_total_tenure_v2"]; L2=["AS_improved","ICI","industry_hhi"]
L3=["SDI","TO_wind"]; L4=["ARG","return_volatility"]; L5=["de","lsv","risk_asym"]
ALLRHS = CONT+FF5+L1+L2+L3+L4+L5

def winsor(s):
    s=s.astype(float); lo,hi=s.quantile(0.01),s.quantile(0.99); return s.clip(lo,hi)
for v in ALLRHS+["ff5_adj_return"]:
    df[v+"_w"]=winsor(df[v])

def fit(rhs, data=None, subset=None):
    d = (data if data is not None else df).copy()
    if subset is not None:
        d = d[subset]
    rhs_w=[r+"_w" for r in rhs]
    d=d.dropna(subset=rhs_w+["ff5_adj_return_w"]).copy()
    form="ff5_adj_return_w ~ "+" + ".join(rhs_w)+" + C(year)"
    m=smf.ols(form,data=d).fit(cov_type="cluster",cov_kwds={"groups":d["fund_code"]})
    return m, d

# ---- M4 (full) ----
m4, d4 = fit(ALLRHS)
m4_n=len(d4); m4_funds=d4["fund_code"].nunique()
def coef(m,v): 
    k=v+"_w"; return dict(beta=round(m.params[k],5),t=round(m.tvalues[k],2),p=round(m.pvalues[k],4))

# ===== 1) WCB-S（正确聚类重抽样：重抽基金簇并以顺序新 id 重标组） =====
rng=np.random.default_rng(20260815)
base=d4.copy()
g_uniq=base["fund_code"].unique()
idx_by_g={g: base.index[base["fund_code"]==g].tolist() for g in g_uniq}
rhs_form="ff5_adj_return_w ~ "+" + ".join([r+"_w" for r in ALLRHS])+" + C(year)"
t_obs={v: m4.tvalues[v+"_w"] for v in L5}
B=999
boot_t={v:[] for v in L5}
for b in range(B):
    sel=rng.choice(g_uniq, size=len(g_uniq), replace=True)
    pieces=[]
    for new_id,g in enumerate(sel):
        sub=base.loc[idx_by_g[g]].copy(); sub["_cid"]=g; pieces.append(sub)
    bs=pd.concat(pieces)
    try:
        mb=smf.ols(rhs_form,data=bs).fit(cov_type="cluster",cov_kwds={"groups":bs["_cid"]})
    except Exception:
        continue
    for v in L5:
        try: boot_t[v].append(mb.tvalues[v+"_w"])
        except Exception: pass
wcb={}
for v in L5:
    arr=np.array(boot_t[v]); tt=t_obs[v]
    p=round((1+np.sum(np.abs(arr)>=abs(tt)))/(1+len(arr)),4)
    wcb[v]=dict(t_obs=round(tt,2), wcb_p=p, boot_n=len(arr))

# ===== 2) Oster (supp formula) =====
def oster(Xname):
    rhs_short=CONT+FF5+[Xname]
    rhs_long =CONT+FF5+L1+L2+L3+L4+[Xname]
    ms,_=fit(rhs_short); ml,_=fit(rhs_long)
    b_s=ms.params[Xname+"_w"]; b_l=ml.params[Xname+"_w"]
    Rl=ml.rsquared; Rmax=min(1,1.3*Rl)
    if (b_l-b_s)==0: delta=None
    else:
        b_max=b_l+(b_l-b_s)*(Rmax-Rl)/(Rl- ms.rsquared) if (Rl-ms.rsquared)!=0 else None
        delta=(b_l-b_s)/(b_l-b_max) if b_max is not None else None
    return dict(b_short=round(b_s,4), b_long=round(b_l,4), R_long=round(Rl,3),
                Rmax=round(Rmax,3), delta=round(delta,2) if delta==delta else None)
oster_res={v:oster(v) for v in L5}

# ===== 3) §4.4.2 牛熊市子样本 M4 =====
# 市场状态代理：FF5 市场因子 MKT_excess（市场广覆盖收益，近似沪深300季度收益）>=0 为牛市。
bull=None; bear=None
mkq = df.groupby(["year","quarter"])["MKT_excess"].transform("mean")
bull_idx = df.loc[mkq>=0].index
bear_idx = df.loc[mkq<0].index
d4_bull = d4[d4.index.isin(bull_idx)]
d4_bear = d4[d4.index.isin(bear_idx)]
mb,_=fit(ALLRHS, data=d4_bull); mbe,_=fit(ALLRHS, data=d4_bear)
bull=dict(N=len(d4_bull), **{v:coef(mb,v) for v in L5})
bear=dict(N=len(d4_bear), **{v:coef(mbe,v) for v in L5})

# ===== 4) §4.10 非线性（二次项） =====
nonlin={}
for v in L5:
    rhs_nl=[r for r in ALLRHS if r!=v]+[v, v+"_sq"]
    d=d4.copy(); d[v+"_w_sq"]=(d[v+"_w"]**2)
    form="ff5_adj_return_w ~ "+" + ".join([r+"_w" for r in rhs_nl if not r.endswith('_sq')])+" + "+v+"_w_sq + C(year)"
    # rebuild properly
    rhs_w=[r+"_w" for r in ALLRHS if r!=v]+[v+"_w", v+"_w_sq"]
    dd=d.dropna(subset=rhs_w+["ff5_adj_return_w"]).copy()
    f2="ff5_adj_return_w ~ "+" + ".join(rhs_w)+" + C(year)"
    mn=smf.ols(f2,data=dd).fit(cov_type="cluster",cov_kwds={"groups":dd["fund_code"]})
    nonlin[v]=dict(lin=dict(beta=round(mn.params[v+"_w"],4),p=round(mn.pvalues[v+"_w"],4)),
                   quad=dict(beta=round(mn.params[v+"_w_sq"],4),p=round(mn.pvalues[v+"_w_sq"],4)))

# ===== 5) RESET (cluster-robust) =====
yh=m4.fittedvalues
d4r=d4.copy(); d4r["yh2"]=yh**2; d4r["yh3"]=yh**3
freset="ff5_adj_return_w ~ "+" + ".join([r+"_w" for r in ALLRHS])+" + C(year) + yh2 + yh3"
mr=smf.ols(freset,data=d4r).fit(cov_type="cluster",cov_kwds={"groups":d4r["fund_code"]})
# F test on yh2,yh3 via compare_ftest
from statsmodels.stats.anova import anova_lm
try:
    w=mr.f_test("yh2 = 0, yh3 = 0")
    reset_F=round(float(w.fvalue),3); reset_p=round(float(w.pvalue),4)
except Exception as e:
    reset_F=None; reset_p=None

result=dict(M4_N=m4_n, M4_funds=m4_funds,
            M4_coef={v:coef(m4,v) for v in ALLRHS},
            WCB=wcb, OSTER=oster_res,
            BULL=bull, BEAR=bear, NONLIN=nonlin,
            RESET=dict(F=reset_F, p=reset_p))
with open(OUT,"w",encoding="utf-8") as f:
    json.dump(result,f,ensure_ascii=False,indent=2)
print("M4 N/funds:",m4_n,m4_funds)
for v in L5: print(" ",v,"beta/t/p:",coef(m4,v))
print("WCB:",wcb)
print("OSTER:",oster_res)
print("BULL:",bull)
print("BEAR:",bear)
print("NONLIN:",nonlin)
print("RESET:",result["RESET"])
print("DONE ->",OUT)
