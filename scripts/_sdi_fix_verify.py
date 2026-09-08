# -*- coding: utf-8 -*-
"""修正SDI后，重跑逐指标单回归（FF3/FF5 alpha）和全指标M4面板，验证结论变化。"""
import json, os, warnings
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
warnings.filterwarnings('ignore')

PANEL = r'指标计算流水线\output\主分析面板_重建_含TOwind.csv'
QRET = r'指标计算流水线\data\L4_风险应对层\基金季度收益.csv'
OUT = 'output/sdi_fix_regressions_2026-08-25.json'
BAD_Q = [(2025,3),(2026,2),(2026,3)]

L1 = ['mgr_total_tenure_v2','log_fund_age']
L2 = ['AS_improved','ICI','industry_hhi']
L3 = ['SDI','TO_wind','ARG']
L4 = ['return_volatility']
L5 = ['de','lsv','risk_asym']
CTRL = 'log_aum'
ALL_BEH = L2+L3+L4+L5

df = pd.read_csv(PANEL, dtype={'fund_code':str})
bad = df.set_index(['year','quarter']).index.isin(BAD_Q)
df = df[~bad].sort_values(['fund_code','year','quarter']).reset_index(drop=True)
df['log_aum'] = np.log(df['avg_aum'].clip(lower=1e-9))
print('面板行数:', len(df), '基金数:', df.fund_code.nunique())
print('SDI非空:', df.SDI.notna().sum(), '覆盖:', round(df.SDI.notna().mean()*100,1), '%')

# ---- risk_asym干净重算（与之前一致）----
qret = pd.read_csv(QRET, encoding='utf-8-sig')
qret['report_date']=pd.to_datetime(qret['report_date'])
qret['year']=qret['report_date'].dt.year; qret['qtr']=qret['report_date'].dt.quarter
qb=qret.set_index(['year','qtr']).index.isin(BAD_Q); qret=qret[~qb].sort_values(['fund_code','report_date'])
WINDOW,MINP=8,4; ra_map={}
for fc,g in qret.groupby('fund_code'):
    r=g['quarter_return'].values; ra=np.full(len(r),np.nan)
    for i in range(len(r)):
        seg=r[max(0,i-WINDOW+1):i+1]
        if len(seg)<MINP: continue
        gain,loss=seg[seg>0],seg[seg<=0]
        sg=gain.std() if len(gain)>1 else np.nan; sl=loss.std() if len(loss)>1 else np.nan
        if not(np.isnan(sg) or np.isnan(sl)): ra[i]=sg-sl
    for k,v in zip(zip(g['year'].astype(int).values,g['qtr'].astype(int).values),ra):
        ra_map[(str(fc),k[0],k[1])]=v
df=df.merge(pd.DataFrame([(fc,y,q,v) for (fc,y,q),v in ra_map.items()],
                          columns=['fund_code','year','quarter','ra_clean']),
             on=['fund_code','year','quarter'],how='left')
df['risk_asym']=df['ra_clean']; df.drop(columns=['ra_clean'],inplace=True)

# ---- FF3/FF5 alpha (基金级时序截距) ----
FACS={'ff3':['MKT_excess','SMB','HML'],
      'ff5':['ff5_MKT_excess','ff5_SMB','ff5_HML','ff5_RMW','ff5_CMA']}
amaps={}
for nm,fac in FACS.items():
    am={}
    for fc,g in df.groupby('fund_code'):
        gg=g.dropna(subset=['excess_return']+fac)
        y=gg['excess_return'].values.astype(float); X=gg[fac].values.astype(float)
        if len(y)<X.shape[1]+5: continue
        A=np.column_stack([np.ones(len(y)),X])
        beta,*_=np.linalg.lstsq(A,y,rcond=None)
        am[fc]=float(beta[0])
    amaps[nm]=am; print(nm,'alpha可估=',len(am))
for nm in amaps: df[nm+'_a']=df['fund_code'].map(amaps[nm])

def winsor(s,lo=0.01,hi=0.99):
    x=s.dropna(); return s.clip(x.quantile(lo),x.quantile(hi))
for c in ALL_BEH+L1+[CTRL]:
    df[c+'_w']=winsor(df[c])

# ---- 基金层聚合 ----
agg_d={c+'_w':'mean' for c in ALL_BEH+L1+[CTRL]}
g=df.groupby('fund_code').agg(
    ff3_a=('ff3_a','first'),ff5_a=('ff5_a','first'),
    **{k:(k,'mean') for k in agg_d}
).reset_index()

def pack(m,keys):
    res={}
    for k in keys:
        if k not in m.params.index: continue
        res[k]=dict(b=round(float(m.params[k]),4),
                    t=round(float(m.tvalues[k]),2),
                    p=round(float(m.pvalues[k]),4),
                    stars='***' if m.pvalues[k]<.01 else '**' if m.pvalues[k]<.05 else '*' if m.pvalues[k]<.1 else '')
    return res

out={}
# ---- 逐指标单回归（单指标+log_aum）----
print('\n===== 逐指标单回归（修正后）=====')
for dv in ['ff3_a','ff5_a']:
    out[dv]={}
    print('\n--- DV =',dv,'---')
    for col,label in [('mgr_total_tenure_v2','L1 从业年限'),('log_fund_age','L1 基金年龄'),
                      ('AS_improved','L2 AS'),('ICI','L2 ICI'),('industry_hhi','L2 HHI'),
                      ('SDI','L3 SDI'),('TO_wind','L3 TO'),('ARG','L3 ARG'),
                      ('return_volatility','L4 RV'),('de','L5 DE'),('lsv','L5 LSV'),
                      ('risk_asym','L5 RA')]:
        rhs=[col+'_w',CTRL+'_w']
        sub=g.dropna(subset=[dv]+rhs)
        if sub[rhs].std().min()<1e-12: continue
        fml='%s ~ %s + %s'%(dv,col+'_w',CTRL+'_w')
        m=smf.ols(fml,data=sub).fit(cov_type='HC1')
        res=pack(m,[col+'_w',CTRL+'_w'])
        out[dv][col]=dict(N=int(m.nobs),r2=round(float(m.rsquared),4),coef=res)
        d=res.get(col+'_w')
        if d:
            print('  %-22s N=%3d b=%+.5f t=%+.2f %s'%(label,m.nobs,d['b'],d['t'],d['stars']))

# ---- 全指标M4面板回归 ----
print('\n===== 全指标M4面板（修正后）=====')
# 构建基金-年面板
panel_cols=['fund_code','year']+ALL_BEH+L1+[CTRL,'ff5_MKT_excess','ff5_SMB','ff5_HML','ff5_RMW','ff5_CMA',
          'ff3_a','ff5_a','excess_return']
p = df[panel_cols].copy()
# 缩尾
for c in ALL_BEH+L1+[CTRL]+['ff5_MKT_excess','ff5_SMB','ff5_HML','ff5_RMW','ff5_CMA']:
    p[c+'_w']=winsor(p[c])
# 因变量：用ff5_alpha（基金级），年度聚合
p_yr = p.groupby(['fund_code','year']).agg(
    ff5_a=('ff5_a','first'),
    **{c+'_w':(c+'_w','mean') for c in ALL_BEH+L1+[CTRL]+['ff5_MKT_excess','ff5_SMB','ff5_HML','ff5_RMW','ff5_CMA']}
).reset_index()
# 剔除污染季所在年
p_yr = p_yr[~p_yr['year'].isin([2025,2026])]  # 2025Q3/2026Q2-Q3污染
rhs_all = [c+'_w' for c in L1+L2+L3+L4+L5+[CTRL]+['ff5_MKT_excess','ff5_SMB','ff5_HML','ff5_RMW','ff5_CMA']]
# 去除零方差列
sub = p_yr.dropna(subset=['ff5_a']+rhs_all)
keep=[c for c in rhs_all if sub[c].std()>1e-12]
dropped=[c for c in rhs_all if c not in keep]
print('SDI是否在keep中:','SDI_w' in keep,' dropped:',dropped)
fml='ff5_a ~ ' + ' + '.join(keep) + ' + C(year)'
m4 = smf.ols(fml,data=sub).fit(cov_type='cluster',cov_kwds={'groups':sub['fund_code']})
out['m4_panel']=dict(N=int(m4.nobs),r2=round(float(m4.rsquared),4),coef=pack(m4,keep))
print('N=',m4.nobs,'R2=',round(m4.rsquared,4))
key_vars=['risk_asym_w','de_w','lsv_w','AS_improved_w','ICI_w','SDI_w','TO_wind_w','ARG_w','return_volatility_w','log_aum_w']
for k in key_vars:
    if k in m4.params.index:
        print('  %-22s b=%+.5f t=%+.2f %s'%(k,float(m4.params[k]),float(m4.tvalues[k]),
              '***' if m4.pvalues[k]<.01 else '**' if m4.pvalues[k]<.05 else '*' if m4.pvalues[k]<.1 else ''))

with open(OUT,'w',encoding='utf-8') as f:
    json.dump(out,f,ensure_ascii=False,indent=1)
print('\nsaved',OUT)
