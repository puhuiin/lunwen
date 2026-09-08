import os, numpy as np, pandas as pd, statsmodels.formula.api as smf, warnings
warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
panel = pd.read_csv(os.path.join(HERE,"指标计算流水线","output","主分析面板_重建_含TOwind.csv"), dtype={"fund_code":str})
panel["log_aum"] = np.log(panel["avg_aum"].clip(lower=1e-9)); panel["year"] = pd.to_datetime(panel["report_date"]).dt.year
b2 = pd.read_csv(os.path.join(HERE,"output","batch2_daily_factors_2026-08-21.csv"), dtype={"fund_code":str}); b2["year"]=b2["year"].astype(int)
def winsor(s): s=s.astype(float); a,b=s.quantile(.01),s.quantile(.99); return s.clip(a,b)
PANELV=["log_aum","log_fund_age","mgr_total_tenure_v2","AS_improved","ICI","industry_hhi","SDI","TO_wind","ARG","return_volatility","de","lsv","risk_asym","ff5_MKT_excess","ff5_SMB","ff5_HML","ff5_RMW","ff5_CMA","ff5_adj_return"]
for v in PANELV: panel[v+"_w"]=winsor(panel[v])
for v in ["TM_beta2","idio_vol_annual","factor_drift"]: b2[v+"_w"]=winsor(b2[v])
df=panel.merge(b2[["fund_code","year","TM_beta2_w","idio_vol_annual_w","factor_drift_w"]],on=["fund_code","year"],how="inner")
V4=["log_aum","log_fund_age","mgr_total_tenure_v2","AS_improved","ICI","industry_hhi","ARG","return_volatility","de","lsv","risk_asym","ff5_MKT_excess","ff5_SMB","ff5_HML","ff5_RMW","ff5_CMA"]
base=[c+"_w" for c in V4]+["TO_wind_w"]; full=[c+"_w" for c in V4 if c!="return_volatility"]+["idio_vol_annual_w","TM_beta2_w","factor_drift_w"]
sub_full=df.dropna(subset=full+["ff5_adj_return_w"]); sub_both=sub_full.dropna(subset=base+["ff5_adj_return_w"])
def r2_of(rhs,d):
    keep=[c for c in rhs if d[c].std()>1e-12]
    m=smf.ols("ff5_adj_return_w ~ "+" + ".join(keep)+" + C(year)",data=d).fit(); return m.rsquared,int(m.nobs)
print("full样本 N=",len(sub_full)," 同时base列非缺失 N=",len(sub_both))
r2b,nb=r2_of(base,sub_both); r2f,nf=r2_of(full,sub_both)
print(f"同样本 N={nb}: R2_base={r2b:.4f}  R2_full={r2f:.4f}  dR2={r2f-r2b:+.4f}")
