import pandas as pd, numpy as np, statsmodels.formula.api as smf
import warnings; warnings.filterwarnings('ignore')

panel = pd.read_csv("指标计算流水线/output/主分析面板_重建.csv")
hf = pd.read_csv("数据/L2_持仓偏离层/基金持仓明细_全量修正版.csv")

# normalize weights within each snapshot so sum=1
hf['fund_code']=hf['fund_code'].astype(str)
hf['hold_ratio']=pd.to_numeric(hf['hold_ratio'],errors='coerce')
hf['w']=hf.groupby(['fund_code','report_date'])['hold_ratio'].transform(lambda s: s/ s.sum())
hf['w']=pd.to_numeric(hf['w'],errors='coerce')
hf=hf.dropna(subset=['w'])

def tn_per_fund(g, strict_q=False):
    g=g.sort_values('report_date')
    dates=list(g['report_date'].unique())
    rows=[]
    for i in range(1,len(dates)):
        d0,d1=dates[i-1],dates[i]
        if strict_q:
            # require exactly one quarter apart
            y0,q0=int(d0[:4]),(int(d0[5:7])-1)//3+1
            y1,q1=int(d1[:4]),(int(d1[5:7])-1)//3+1
            gap=(y1-y0)*4+(q1-q0)
            if gap!=1: continue
        a=g[g['report_date']==d0].groupby('stock_code')['w'].sum()
        b=g[g['report_date']==d1].groupby('stock_code')['w'].sum()
        idx=a.index.union(b.index)
        a=a.reindex(idx).fillna(0); b=b.reindex(idx).fillna(0)
        tn=0.5*np.abs(a-b).sum()
        rows.append((d1,tn))
    return rows

rec=[]; stq=[]
for fid,g in hf.groupby('fund_code'):
    for d,tn in tn_per_fund(g,strict_q=False): rec.append((fid,d,tn))
    for d,tn in tn_per_fund(g,strict_q=True):  stq.append((fid,d,tn))

rec_df=pd.DataFrame(rec,columns=['fund_code','report_date','hold_turnover'])
stq_df=pd.DataFrame(stq,columns=['fund_code','report_date','hold_turnover_q'])

print("Consecutive-snapshot funds:", rec_df['fund_code'].nunique())
print("Strict-quarterly-adjacent funds:", stq_df['fund_code'].nunique())

# fund-level mean turnover
fund_tn=rec_df.groupby('fund_code')['hold_turnover'].mean().rename('hold_turnover')
fund_tnq=stq_df.groupby('fund_code')['hold_turnover_q'].mean().rename('hold_turnover_q')

reg=panel.groupby('fund_code').agg(ff5=('ff5_adj_return','mean'),aum=('avg_aum','mean'),age=('log_fund_age','first')).dropna(subset=['ff5','aum']).copy()
reg.index=reg.index.astype(str)
reg['log_aum']=np.log(reg['aum'])

m1=reg.join(fund_tn).dropna(subset=['hold_turnover'])
m1b=smf.ols("ff5 ~ hold_turnover + log_aum + age",data=m1).fit(cov_type='HC1')
print("\n[CONSECUTIVE] N=%d R2=%.4f"%(int(m1b.nobs),m1b.rsquared))
print("  hold_turnover beta=%.4f t=%.2f p=%.3f"%(m1b.params['hold_turnover'],m1b.tvalues['hold_turnover'],m1b.pvalues['hold_turnover']))

m2=reg.join(fund_tnq).dropna(subset=['hold_turnover_q'])
m2b=smf.ols("ff5 ~ hold_turnover_q + log_aum + age",data=m2).fit(cov_type='HC1')
print("\n[STRICT-QUARTERLY] N=%d R2=%.4f"%(int(m2b.nobs),m2b.rsquared))
print("  hold_turnover_q beta=%.4f t=%.2f p=%.3f"%(m2b.params['hold_turnover_q'],m2b.tvalues['hold_turnover_q'],m2b.pvalues['hold_turnover_q']))

# overlap & corr vs trade-based TO
to=pd.read_csv("指标计算流水线/data/L3_交易行为层/基金换手率_双边_含卖出.csv")
to['fund_code']=to['fund_code'].astype(str)
to_funds=set(to['fund_code']); hold_funds=set(fund_tn.index)
print("\nOverlap(holdings ∩ TO) =", len(hold_funds & to_funds), "/ TO funds", len(to_funds))
merged=fund_tn.reset_index().merge(to[['fund_code','TO_two_sided']],on='fund_code')
print("corr(holdings_turnover, TO_two_sided) = %.3f (N=%d)"%(merged['hold_turnover'].corr(merged['TO_two_sided']),len(merged)))
