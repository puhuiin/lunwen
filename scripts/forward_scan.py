import pandas as pd, numpy as np, statsmodels.api as sm, os
base="D:/Desktop/基金经理行为分析研究/"
panel=pd.read_csv(base+"指标计算流水线/output/主分析面板_重建.csv",dtype={"fund_code":str})
panel["log_aum"]=np.log(panel["avg_aum"].clip(lower=1.0))
panel["log_age"]=panel["log_fund_age"]
panel["year_c"]=panel["year"].astype(int)
panel["CFA_bin"]=(panel["CFA"]=="是").astype(int)

d=panel.sort_values(["fund_code","year","quarter"]).copy()
d["fut4q"]=d.groupby("fund_code")["excess_return"].transform(lambda s:s.shift(-1).rolling(4,min_periods=4).mean())
d["fut1q"]=d.groupby("fund_code")["excess_return"].shift(-1)

ctr=["log_aum","log_age","year_c"]
cands={
 "L1_tenure":"mgr_total_tenure_v2","L1_gender":"gender","L1_CFA":"CFA_bin",
 "L2_AS":"AS_improved","L2_ICI":"ICI","L2_HHI":"industry_hhi",
 "L3_TO":"TO_two_sided","L3_OCI":"OCI_two_sided","L3_SDI":"SDI",
 "L4_ARG":"ARG","L4_retvol":"return_volatility","L4_RG":"RG",
 "L5_de":"de","L5_pgr":"pgr","L5_plr":"plr","L5_lsv":"lsv","L5_risk_asym":"risk_asym",
}
def encode(col):
    if col=="gender":
        return (d[col]=="男").astype(float)
    return d[col].astype(float)
rows=[]
for lab,col in cands.items():
    x=encode(col)
    sub=pd.DataFrame({"dv":d["fut4q"],"x":x,"log_aum":d["log_aum"],"log_age":d["log_age"],"year_c":d["year_c"],"fc":d["fund_code"]}).dropna()
    X=sm.add_constant(sub[["x"]+ctr])
    m=sm.OLS(sub["dv"],X).fit(cov_type="cluster",cov_kwds={"groups":sub["fc"].values})
    rows.append(dict(var=lab,b=round(float(m.params["x"]),4),t=round(float(m.tvalues["x"]),2),
                     n=int(m.nobs),nf=sub["fc"].nunique()))
res=pd.DataFrame(rows)
pd.set_option("display.width",200)
print("=== 各层变量 单独 对 fut4q 的前向预测力（控制 log_aum/log_age/yearFE, 基金聚类SE）===")
print(res.to_string(index=False))

# CFA 基金层统计
print("\n=== CFA 基金层分布 ===")
cf=panel.dropna(subset=["CFA"])
print("观测数",len(cf),"基金数",cf["fund_code"].nunique())
print(cf.groupby("fund_code")["CFA"].first().value_counts())
cfv=panel.copy()
cfv["CFA_bin"]=(cfv["CFA"]=="是").astype(int)
fund_cfa=cfv.groupby("fund_code")["CFA_bin"].first()
print(f"有CFA=是 的基金数: {int(fund_cfa.sum())} / 总基金 {fund_cfa.shape[0]} = {fund_cfa.mean()*100:.2f}%")
# 对比 CFA=是 vs 否 的 ff5_adj 均值
agg=cfv.groupby("fund_code").agg(cfa=("CFA_bin","first"),ff5=("ff5_adj_return","mean")).dropna()
print("CFA=是 基金 ff5均值:",round(agg[agg.cfa==1].ff5.mean(),4)," N=",int((agg.cfa==1).sum()))
print("CFA=否 基金 ff5均值:",round(agg[agg.cfa==0].ff5.mean(),4)," N=",int((agg.cfa==0).sum()))
