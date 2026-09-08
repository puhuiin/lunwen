# -*- coding: utf-8 -*-
"""M1-M4 递进面板回归（2026-08-25 ISDI主口径版）
DV = ff5_adj_return（FF5风险调整后季度收益）
M1: 单指标 + lnAUM
M2: 单指标 + lnAUM + 年度FE
M3: 单指标 + lnAUM + 年度FE + 经理/基金特征
M4: 全部行为指标 + 控制变量 + 年度FE（主表）
SE: 基金聚类
"""
import os, json, warnings
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
warnings.filterwarnings('ignore')

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
df = pd.read_csv(os.path.join(ROOT,'指标计算流水线','output','主分析面板_重建_含TOwind.csv'),
                 dtype={'fund_code':str})
BAD_Q = [(2025,3),(2026,2),(2026,3)]
df = df[~df.set_index(['year','quarter']).index.isin(BAD_Q)]
df = df.sort_values(['fund_code','report_date']).reset_index(drop=True)

def winsor(s, lo=0.01, hi=0.99):
    s = s.astype(float); a,b = s.quantile(lo), s.quantile(hi); return s.clip(a,b)

df['log_aum'] = np.log(df['avg_aum'].clip(lower=1e-9))
df['ff5_adj_return_w'] = winsor(df['ff5_adj_return'])

BEH = ['risk_asym','de','lsv','ICI','AS_improved','ISDI','ARG','return_volatility','TO_wind']
MGR = ['mgr_total_tenure_v2','log_fund_age']
ALLRHS = BEH + MGR + ['log_aum']
for c in ALLRHS:
    df[c+'_w'] = winsor(df[c])

def fit(rhs, label, fe_year=True):
    W = [c+'_w' for c in rhs]
    sub = df.dropna(subset=['ff5_adj_return_w']+W).copy().reset_index(drop=True)
    keep = [c for c in W if sub[c].std() > 1e-12]
    fml = 'ff5_adj_return_w ~ ' + ' + '.join(keep) + (' + C(year)' if fe_year else '')
    m = smf.ols(fml, data=sub).fit(cov_type='cluster', cov_kwds={'groups':sub['fund_code']})
    return m, keep

results = {}
print('='*100)
for x in BEH:
    m1,_ = fit([x,'log_aum'], '', fe_year=False)
    m2,_ = fit([x,'log_aum'], '')
    m3,_ = fit([x,'log_aum']+MGR, '')
    print(f'\n### {x}')
    for nm, m in [('M1',m1),('M2',m2),('M3',m3)]:
        k = x+'_w'
        b,t,p = m.params[k], m.tvalues[k], m.pvalues[k]
        st = '***' if p<.01 else '**' if p<.05 else '*' if p<.1 else ''
        results.setdefault(x,{})[nm] = dict(b=round(b,5),t=round(t,2),p=round(p,4),
                                             N=int(m.nobs),r2=round(m.rsquared,4))
        print(f'  {nm}: b={b:+.5f}  t={t:+.2f}{st}  N={int(m.nobs)}  R2={m.rsquared:.4f}')

# M4 全指标
m4,_ = fit(ALLRHS, 'M4')
print(f'\n### M4 全指标面板: N={int(m4.nobs)}, R2={m4.rsquared:.4f}')
print('-'*100)
hdr = f'{"变量":22s} {"系数":>10s} {"t":>8s} {"p":>8s} {"显著性":>6s}'
print(hdr); print('-'*100)
for c in ALLRHS:
    k = c+'_w'
    if k not in m4.params.index: continue
    b,t,p = m4.params[k], m4.tvalues[k], m4.pvalues[k]
    st = '***' if p<.01 else '**' if p<.05 else '*' if p<.1 else ''
    results.setdefault(c,{})['M4'] = dict(b=round(b,5),t=round(t,2),p=round(p,4))
    print(f'{c:22s} {b:+10.5f} {t:+8.2f}{st}  {p:8.4f}')
try:
    ycols = [c for c in m4.params.index if c.startswith('C(year)')]
    if len(ycols) > 1:
        from scipy import stats as spstats
        R = np.zeros((len(ycols)-1, len(m4.params)))
        for i, yc in enumerate(ycols[:-1]):
            R[i, list(m4.params.index).index(yc)] = 1
            R[i, list(m4.params.index).index(ycols[-1])] = -1
        V = np.asarray(m4.cov_params())
        chi2 = float(R @ m4.params.values @ R.T @ np.linalg.pinv(R @ V @ R.T) @ R @ m4.params.values)
        print(f'\n  年度FE联合显著: chi2={chi2:.1f} (df={len(ycols)-1})')
except Exception as e:
    print(f'  (FE检验跳过: {e})')
r2s = {'M1_avg': np.mean([v['M1']['r2'] for v in results.values() if 'M1' in v]),
       'M4': round(m4.rsquared,4)}
out = dict(results=results, m4=dict(N=int(m4.nobs), r2=round(float(m4.rsquared),4),
                                    rhs=ALLRHS, dv='ff5_adj_return_w',
                                    se='cluster by fund', fe='C(year)'),
           note='M1:单指标+lnAUM无FE; M2:+年度FE; M3:+经理特征; M4:全行为指标')
with open(os.path.join(ROOT,'output','m1_m4_progression_ISDI_2026-08-25.json'),'w',encoding='utf-8') as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
print('\nsaved output/m1_m4_progression_ISDI_2026-08-25.json')
