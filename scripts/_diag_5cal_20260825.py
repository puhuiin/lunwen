# -*- coding: utf-8 -*-
"""诊断五口径新旧结果矛盾：旧规格(12指标含HHI/SDI) vs 新规格(9指标含ISDI)"""
import os, warnings
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
warnings.filterwarnings('ignore')

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
df = pd.read_csv(os.path.join(ROOT,'指标计算流水线','output','主分析面板_重建_含TOwind.csv'),
                 dtype={'fund_code':str})
BAD_Q = [(2025,3),(2026,2),(2026,3)]
df = df[~df.set_index(['year','quarter']).index.isin(BAD_Q)]

def winsor(s, lo=0.01, hi=0.99):
    s = s.astype(float); a,b = s.quantile(lo), s.quantile(hi); return s.clip(a,b)

df['log_aum'] = np.log(df['avg_aum'].clip(lower=1e-9))
df['mkt_q'] = df['MKT_excess'] + df['rf']
df['dv1_raw'] = winsor(df['quarter_return'])
df['dv2_mkt'] = winsor(df['quarter_return'] - df['mkt_q'])
df['dv3_peer'] = winsor(df['quarter_return'] - df.groupby('report_date')['quarter_return'].transform('mean'))
df['dv4_ff5'] = winsor(df['ff5_adj_return'])

# 三种RHS规格
CTRL = ['mgr_total_tenure_v2','log_fund_age','log_aum']
NEW9  = ['risk_asym','de','lsv','ICI','AS_improved','ISDI','ARG','return_volatility','TO_wind']
OLD10 = ['risk_asym','de','lsv','ICI','AS_improved','SDI','ARG','return_volatility','TO_wind','industry_hhi']
OLD12 = OLD10 + ['OCI_two_sided','RG']

def run(dv, beh, label):
    W = [c+'_w' for c in beh+CTRL]
    for c in beh+CTRL:
        df[c+'_w'] = winsor(df[c])
    sub = df.dropna(subset=[dv]+W).copy().reset_index(drop=True)
    keep = [c for c in W if sub[c].std() > 1e-12]
    fml = dv + ' ~ ' + ' + '.join(keep) + ' + C(year)'
    m = smf.ols(fml, data=sub).fit(cov_type='cluster', cov_kwds={'groups':sub['fund_code']})
    out = {}
    for c in ['risk_asym','de','lsv','ICI','AS_improved','ISDI','SDI','ARG','return_volatility','TO_wind','industry_hhi','RG','OCI_two_sided']:
        k = c+'_w'
        if k in m.params.index:
            out[c] = (m.params[k], m.tvalues[k])
    print(f'[{label}] N={int(m.nobs)} R2={m.rsquared:.4f}')
    return out

print('='*80)
print('差异诊断：同一面板、同一DV(①纯收益)、只换RHS规格')
print('='*80)
rA = run('dv1_raw', NEW9,  '新规格: 9指标(ISDI, 无HHI/SDI/OCI/RG)')
rB = run('dv1_raw', OLD10, '旧规格: 10指标(SDI+HHI)')
rC = run('dv1_raw', OLD12, '旧规格: 12指标(SDI+HHI+OCI+RG)')

print('\n关键变量对比（DV=纯收益）:')
print(f'{"变量":16s} {"新9指标":>16s} {"旧10指标":>16s} {"旧12指标":>16s}')
for c in ['risk_asym','de','lsv','ICI','AS_improved','ARG','return_volatility','industry_hhi']:
    row = f'{c:16s}'
    for r in [rA, rB, rC]:
        if c in r:
            b,t = r[c]
            st = '***' if abs(t)>2.58 else '**' if abs(t)>1.96 else '*' if abs(t)>1.64 else ''
            row += f'  {b:+.3f}({t:+.1f}){st:3s}'
        else:
            row += f'  {"—":>14s}'
    print(row)

# SDI→ISDI替换对RA的影响单独测
print('\n===== 单独测：SDI换成ISDI对RA系数的影响（纯收益DV）=====')
rD = run('dv1_raw', [c for c in NEW9], 'ISDI版')
rE = run('dv1_raw', ['risk_asym','de','lsv','ICI','AS_improved','SDI','ARG','return_volatility','TO_wind'], 'SDI版(同槽位)')
for nm, r in [('ISDI版', rD), ('SDI版', rE)]:
    if 'risk_asym' in r:
        b,t = r['risk_asym']
        print(f'  {nm} RA: {b:+.4f} (t={t:+.2f})')

# RA-ISDI/SDI相关性
print('\n===== RA与ISDI/SDI/HHI相关性 =====')
tmp = df.dropna(subset=['risk_asym'])
for c in ['ISDI','SDI','industry_hhi','ARG']:
    t2 = tmp.dropna(subset=[c])
    print(f'  corr(RA, {c}) = {t2["risk_asym"].corr(t2[c]):+.3f}  (N={len(t2)})')
