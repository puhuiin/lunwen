# -*- coding: utf-8 -*-
"""独立复核脚本（2026-08-17）：从原始面板重算两套回归规格，与既有 JSON 比对，
并用 linearmodels 金标准交叉验证自实现 CGM2011 双向聚类。"""
import os, json, warnings, numpy as np, pandas as pd
from scipy import stats as spstats
warnings.filterwarnings("ignore")

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PANEL = os.path.join(HERE, "指标计算流水线", "output", "主分析面板_重建_含TOwind.csv")
panel = pd.read_csv(PANEL, dtype={"fund_code": str})
panel["report_date"] = panel["report_date"].astype(str)
panel["year"] = panel["report_date"].str[:4].astype(int)

out = {}

# ---------- 1. 面板覆盖统计 ----------
keyvars = ["SDI","TO_wind","TO_two_sided","OCI_two_sided","ARG","return_volatility",
           "de","lsv","risk_asym","AS_improved","ICI","industry_hhi",
           "ff5_adj_return","quarter_return","avg_aum"]
cov = {}
for c in keyvars:
    if c in panel.columns:
        cov[c] = {"nonnull": int(panel[c].notna().sum()),
                  "pct": round(float(panel[c].notna().mean()*100), 2)}
out["panel"] = {
    "rows": int(len(panel)),
    "funds": int(panel["fund_code"].nunique()),
    "period_min": panel["report_date"].min(),
    "period_max": panel["report_date"].max(),
    "coverage": cov,
}

# ---------- 通用：手动 CGM2011 双向聚类 ----------
def _meat(groups, X, resid):
    k = X.shape[1]; meat = np.zeros((k, k))
    for gg in np.unique(groups):
        m = groups == gg; s = X[m].T @ resid[m]; meat += np.outer(s, s)
    return meat
def _oneway_V(X, resid, groups):
    XtX_inv = np.linalg.inv(X.T @ X)
    return XtX_inv @ _meat(groups, X, resid) @ XtX_inv
def two_way_V(X, resid, g1, g2):
    g12 = np.array([f"{a}|{b}" for a, b in zip(g1, g2)])
    return _oneway_V(X, resid, g1) + _oneway_V(X, resid, g2) - _oneway_V(X, resid, g12)

# ---------- 2. 重算 M4（与 _v4_benchmark_table.py 完全一致：混合OLS + C(year) + 双向聚类，无基金FE）----------
FF5  = ["ff5_MKT_excess","ff5_SMB","ff5_HML","ff5_RMW","ff5_CMA"]
CONT = ["log_aum"]; L1=["log_fund_age","mgr_total_tenure_v2"]
L2=["AS_improved","ICI","industry_hhi"]; L3=["SDI","TO_wind"]
L4=["ARG","return_volatility"]; L5=["de","lsv","risk_asym"]
ALLRHS = CONT+FF5+L1+L2+L3+L4+L5
panel["log_aum"] = np.log(panel["avg_aum"].clip(lower=1e-9))
panel["ff5_adj_return"] = pd.to_numeric(panel["ff5_adj_return"], errors="coerce")
def wins(s): 
    s=s.astype(float); lo,hi=s.quantile(0.01),s.quantile(0.99); return s.clip(lo,hi)
for v in ALLRHS+["ff5_adj_return"]:
    panel[v+"_w"]=wins(panel[v])

import statsmodels.formula.api as smf
d = panel.dropna(subset=[r+"_w" for r in ALLRHS]+["ff5_adj_return_w"]).copy()
form = "ff5_adj_return_w ~ " + " + ".join(r+"_w" for r in ALLRHS) + " + C(year)"
m = smf.ols(form, data=d).fit(cov_type="cluster", cov_kwds={"groups": d["fund_code"]})
X = np.asarray(m.model.data.exog, float); resid=np.asarray(m.resid,float)
g1=d["fund_code"].values.astype(str); g2=d["year"].values.astype(str)
V2=two_way_V(X,resid,g1,g2); se2=np.sqrt(np.maximum(np.diag(V2),0))
t2=m.params.values/se2
names=list(m.params.index)
m4_recomp={}
for i,nm in enumerate(names):
    if nm=="Intercept" or nm.startswith("C(year)"): continue
    base=nm[:-2] if nm.endswith("_w") else nm
    m4_recomp[base]={"beta":float(m.params.values[i]),"t2w":float(t2[i])}
# 与 _v4_benchmark.json 比对
bench=json.load(open(os.path.join(HERE,"_v4_benchmark.json"),encoding="utf-8"))
diff={}
for k in bench["coefs"]:
    if k in m4_recomp:
        diff[k]={"beta_d":m4_recomp[k]["beta"]-bench["coefs"][k]["beta"],
                 "t_d":m4_recomp[k]["t2w"]-bench["coefs"][k]["t2w"]}
out["m4_repro"]={"n_obs":int(m.nobs),"n_fund":int(d["fund_code"].nunique()),
                 "max_abs_beta_diff":max(abs(v["beta_d"]) for v in diff.values()),
                 "max_abs_t_diff":max(abs(v["t_d"]) for v in diff.values()),
                 "sdi_t":m4_recomp["SDI"]["t2w"],"to_wind_t":m4_recomp["TO_wind"]["t2w"]}

# ---------- 3. 重算 HONEST H1（基金FE demean + 年份虚拟 + 双向聚类，DV=quarter_return）----------
hon=json.load(open(os.path.join(HERE,"L3_L1_regression_HONEST_TOWind_2026-08-15.json"),encoding="utf-8"))
CONTROLS=["log_aum","log_fund_age","mgr_total_tenure_v2","gender_m","cfa_d","edu_postgrad"]
panel["gender_m"]=panel["gender"].astype(str).str.contains("男").astype(float)
panel["cfa_d"]=panel["CFA"].astype(str).str.contains("Y|是|1",case=False,na=False).astype(float)
panel["edu_postgrad"]=panel["education"].astype(str).str.contains("硕士|博士|MBA|研究生",case=False,na=False).astype(float)
for c in ["quarter_return","SDI","log_fund_age","mgr_total_tenure_v2"]:
    panel[c]=panel[c].astype(float)
def wins_h(s): s=s.astype(float); lo,hi=s.quantile(0.01),s.quantile(0.99); return s.clip(lo,hi)
panel["SDI"]=wins_h(panel["SDI"]); panel["quarter_return"]=wins_h(panel["quarter_return"])
dv,iv="quarter_return",["SDI"]+CONTROLS
sub=panel[[dv]+iv+["fund_code","year"]].dropna(subset=[dv]+iv).copy().reset_index(drop=True)
yr=pd.get_dummies(sub["year"],prefix="yr",drop_first=True).astype(float)
sub=pd.concat([sub,yr],axis=1); all_x=iv+list(yr.columns)
g=sub.groupby("fund_code")
Xdm=sub[all_x]-g[all_x].transform("mean"); ydm=(sub[dv]-g[dv].transform("mean")).values
Xf=Xdm[all_x].values.astype(float); yf=ydm.astype(float)
b,*_=np.linalg.lstsq(Xf,yf,rcond=None); res=yf-Xf@b
V=two_way_V(Xf,res,sub["fund_code"].values.astype(str),sub["year"].values.astype(str))
se=np.sqrt(np.maximum(np.diag(V),0)); tf=b/se
j=iv.index("SDI")
# 从 honest json 取 H1 记录
h1_json=None
for name,r in hon["honest"].items():
    if r and "SDI" in [row["v"] for row in r["rows"]]:
        for row in r["rows"]:
            if row["v"]=="SDI":
                h1_json={"spec":name,"b":row["b"],"t2w":row["t"],"t1w":row["t1"]}
out["h1_recomp"]={"sdi_beta":float(b[j]),"sdi_t2w":float(tf[j]),
                  "h1_json":h1_json,
                  "t2w_match": abs(tf[j]-h1_json["t2w"])<1e-6 if h1_json else None}

# ---------- 4. linearmodels 金标准交叉验证（双向FE+双向聚类，作用于 M4 数据）----------
try:
    from linearmodels.panel import PanelOLS
    p=d.copy(); p["entity"]=p["fund_code"].astype(str); p["time"]=p["year"].astype(int)
    p=p.set_index(["entity","time"]).sort_index()
    exog=p[[r+"_w" for r in ALLRHS]]
    mod=PanelOLS(p["ff5_adj_return_w"],exog,entity_effects=True,time_effects=True,
                 drop_absorbed=True).fit(cov_type="clustered",cluster_entity=True,cluster_time=True)
    lm={}
    for nm in ALLRHS:
        idx=[i for i,n in enumerate(mod.params.index) if n==nm+"_w"][0]
        lm[nm]={"beta":float(mod.params.iloc[idx]),"t":float(mod.tstats.iloc[idx])}
    # 与手动 pooled M4 比较 SDI/TO_wind/de/risk_asym 的 t 值差异（model 规格不同，仅看聚类实现一致性量级）
    out["linearmodels"]={"available":True,
        "sdi":lm["SDI"],"to_wind":lm["TO_wind"],"de":lm["de"],"risk_asym":lm["risk_asym"],
        "note":"双向FE+双向聚类金标准；与主脚本 pooled M4 规格不同，仅用于确认聚类SE实现量级合理"}

    # 额外：在 SAME 规格(pooled + C(year) + 手动双向聚类) 与 linearmodels 不可直接比(后者强制双向FE)
    # 故另做 pure 单变量 SDI 的 pooled 双向聚类 vs linearmodels 单向一致性已在前脚本验证。
except Exception as e:
    out["linearmodels"]={"available":False,"error":str(e)[:200]}

print(json.dumps(out, ensure_ascii=False, indent=2, default=str))
json.dump(out, open(os.path.join(HERE,"_verify_review_out_2026-08-17.json"),"w"),
          ensure_ascii=False, indent=2, default=str)
