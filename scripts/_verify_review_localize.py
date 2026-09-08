# -*- coding: utf-8 -*-
"""定位 M4 重算与 _v4_benchmark.json 的差异来源。"""
import os, json, warnings, numpy as np, pandas as pd
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
m=smf.ols(form,data=d).fit(cov_type="cluster",cov_kwds={"groups":d["fund_code"]})
bench=json.load(open(os.path.join(HERE,"_v4_benchmark.json"),encoding="utf-8"))["coefs"]
rows=[]
for nm in m.params.index:
    if nm=="Intercept" or nm.startswith("C(year)"): continue
    base=nm[:-2] if nm.endswith("_w") else nm
    if base in bench:
        bt=float(m.params[nm]); bj=bench[base]["beta"]
        rows.append((base, bt, bj, bt-bj))
rows.sort(key=lambda r:-abs(r[3]))
print("%-18s %14s %14s %14s"%("var","recomp","json","diff"))
for base,bt,bj,dd in rows:
    print("%-18s %+14.6e %+14.6e %+14.6e"%(base,bt,bj,dd))
