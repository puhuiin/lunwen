# -*- coding: utf-8 -*-
"""重算 §4.4.1 置换 与 §4.7 WCB-S（正确全缩尾 M4 + 双向聚类 t）。结果增量写 JSON。"""
import os, json, numpy as np, pandas as pd, warnings
import statsmodels.formula.api as smf
warnings.filterwarnings("ignore")

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PANEL = os.path.join(HERE, "指标计算流水线", "output", "主分析面板_重建_含TOwind.csv")
OUT = os.path.join(HERE, "_v4_robust.json")
res = {"ok": False}

def save():
    json.dump(res, open(OUT, "w"), ensure_ascii=False, indent=1)

FF5=["ff5_MKT_excess","ff5_SMB","ff5_HML","ff5_RMW","ff5_CMA"]; CONT=["log_aum"]
L1=["log_fund_age","mgr_total_tenure_v2"]; L2=["AS_improved","ICI","industry_hhi"]
L3=["SDI","TO_wind"]; L4=["ARG","return_volatility"]; L5=["de","lsv","risk_asym"]
ALLRHS = CONT+FF5+L1+L2+L3+L4+L5

def winsor(s):
    s=s.astype(float); lo,hi=s.quantile(0.01),s.quantile(0.99); return s.clip(lo,hi)

def main():
    df = pd.read_csv(PANEL, dtype={"fund_code": str})
    df["log_aum"] = np.log(df["avg_aum"].clip(lower=1e-9))
    df["ff5_adj_return"] = pd.to_numeric(df["ff5_adj_return"], errors="coerce")
    for v in ALLRHS+["ff5_adj_return"]:
        df[v+"_w"]=winsor(df[v])
    rhs_w=[r+"_w" for r in ALLRHS]
    d=df.dropna(subset=rhs_w+["ff5_adj_return_w"]).copy()
    form="ff5_adj_return_w ~ "+" + ".join(rhs_w)+" + C(year)"
    m=smf.ols(form,data=d).fit(cov_type="cluster",cov_kwds={"groups":d["fund_code"]})
    X=np.asarray(m.model.data.exog,float); y=np.asarray(m.model.data.endog,float)
    beta=m.params.values; resid=y-X@beta
    g1=d["fund_code"].values.astype(str); g2=d["year"].values.astype(str)
    names=list(m.params.index); idx={v:names.index(v+"_w") for v in L5}
    # 预计算分组行索引
    def grp(groups):
        u=np.unique(groups); return u, {g:np.where(groups==g)[0] for g in u}
    g1u,g1map=grp(g1); g2u,g2map=grp(g2); g12=np.array([f"{a}|{b}" for a,b in zip(g1,g2)]); g12u,g12map=grp(g12)
    def meat(mapd,k):
        M=np.zeros((k,k))
        for rows in mapd.values():
            s=X[rows].T@resid[rows]; M+=np.outer(s,s)
        return M
    def oneway_V(mapd,k):
        XtX_inv=np.linalg.inv(X.T@X); return XtX_inv@meat(mapd,k)@XtX_inv
    def twoway_V(k):
        return oneway_V(g1map,k)+oneway_V(g2map,k)-oneway_V(g12map,k)
    k=X.shape[1]
    V2=twoway_V(k); se2=np.sqrt(np.maximum(np.diag(V2),0)); t2=beta/se2
    true_t2w={v:float(t2[idx[v]]) for v in L5}
    res["true_t2w"]={kk:round(v,3) for kk,v in true_t2w.items()}
    res["N"]=int(m.nobs); res["funds"]=int(d["fund_code"].nunique())
    save(); print("fit done", res["true_t2w"], flush=True)

    rng=np.random.default_rng(20260815)
    # 置换
    N_PERM=300
    perm_t={v:[] for v in L5}
    for it in range(N_PERM):
        Xp=X.copy()
        for v in L5: Xp[:,idx[v]]=rng.permutation(X[:,idx[v]])
        bp,_,_,_=np.linalg.lstsq(Xp,y,rcond=None); rp=y-Xp@bp
        def meat_p(mapd):
            M=np.zeros((k,k))
            for rows in mapd.values():
                s=Xp[rows].T@rp[rows]; M+=np.outer(s,s)
            return M
        V2p=np.linalg.inv(Xp.T@Xp)@meat_p(g1map)@np.linalg.inv(Xp.T@Xp) \
            + np.linalg.inv(Xp.T@Xp)@meat_p(g2map)@np.linalg.inv(Xp.T@Xp) \
            - np.linalg.inv(Xp.T@Xp)@meat_p(g12map)@np.linalg.inv(Xp.T@Xp)
        se2p=np.sqrt(np.maximum(np.diag(V2p),0)); t2p=bp/se2p
        for v in L5: perm_t[v].append(float(t2p[idx[v]]))
    perm_p={}
    for v in L5:
        arr=np.array(perm_t[v]); tt=abs(true_t2w[v])
        perm_p[v]=float(max(2.0*min((arr>=tt).mean(),(arr<=-tt).mean()),1.0/N_PERM))
    res["perm_p"]={kk:round(v,4) for kk,v in perm_p.items()}; save()
    print("perm done", res["perm_p"], flush=True)

    # WCB
    B=499; fidx={f:np.where(g1==f)[0] for f in g1u}; XtX_inv=np.linalg.inv(X.T@X)
    L5cols=np.array([idx[v] for v in L5]); L5beta=beta[L5cols]
    wcb_t={v:[] for v in L5}
    for b in range(B):
        w=rng.choice([-1.0,1.0],size=len(g1u)); rb=resid.copy()
        for i,f in enumerate(g1u): rb[fidx[f]]*=w[i]
        # 在 H0: β_L5=0 下构造：y* = X@beta + rb - X_L5@beta_L5
        yb=X@beta+rb-X[:,L5cols]@L5beta
        bb=XtX_inv@(X.T@yb)
        t2b=bb/se2   # 用原始双向聚类 SE 作为检验尺度
        for v in L5: wcb_t[v].append(float(t2b[idx[v]]))
    wcb_p={}
    for v in L5:
        arr=np.abs(np.array(wcb_t[v])); tt=abs(true_t2w[v]); wcb_p[v]=float((arr>=tt).mean())
    res["wcb_p"]={kk:round(v,4) for kk,v in wcb_p.items()}; save()
    print("wcb done", res["wcb_p"], flush=True)
    res["ok"]=True; save()

if __name__=="__main__":
    try:
        main()
    except Exception as e:
        import traceback; res["err"]=traceback.format_exc()[:3000]; save()
    print("FINAL ok=%s" % res.get("ok"), flush=True)
