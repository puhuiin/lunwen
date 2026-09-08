# -*- coding: utf-8 -*-
"""同样本对照：分离 SDI→ISDI替换 / HHI去留 对 RA/ICI/LSV 的影响"""
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
df['dv1'] = winsor(df['quarter_return'])

CTRL = ['mgr_total_tenure_v2','log_fund_age','log_aum']
BASE = ['risk_asym','de','lsv','ICI','AS_improved','ARG','return_volatility','TO_wind']
need = ['dv1','ISDI','SDI','industry_hhi'] + BASE + CTRL
sub = df.dropna(subset=need).copy().reset_index(drop=True)
for c in BASE + CTRL + ['ISDI','SDI','industry_hhi']:
    sub[c+'_w'] = winsor(sub[c])
print(f'同一样本 N={len(sub)}（ISDI与SDI与HHI全非缺失）')

def fit(beh, label):
    W = [c+'_w' for c in beh+CTRL]
    fml = 'dv1 ~ ' + ' + '.join(W) + ' + C(year)'
    m = smf.ols(fml, data=sub).fit(cov_type='cluster', cov_kwds={'groups':sub['fund_code']})
    out = {}
    for c in ['risk_asym','de','lsv','ICI','ISDI','SDI','industry_hhi']:
        k = c+'_w'
        if k in m.params.index:
            out[c] = (m.params[k], m.tvalues[k])
    print(f'[{label}] R2={m.rsquared:.4f}')
    return out

res = {}
res['A'] = fit(BASE+['ISDI'],               'A: ISDI版(无HHI) = 当前主表规格')
res['B'] = fit(BASE+['SDI'],                'B: SDI版(无HHI) = 旧表漂移槽位')
res['C'] = fit(BASE+['SDI','industry_hhi'], 'C: SDI+HHI版 = 旧表完整规格')
res['D'] = fit(BASE+['ISDI','industry_hhi'],'D: ISDI+HHI版')

print()
hdr = f'{"变量":14s}' + ''.join(f'{k+":":>18s}' for k in 'ABCD')
print(hdr)
for c in ['risk_asym','de','lsv','ICI','ISDI','SDI','industry_hhi']:
    row = f'{c:14s}'
    for k in 'ABCD':
        if c in res[k]:
            b,t = res[k][c]
            st = '***' if abs(t)>2.58 else '**' if abs(t)>1.96 else '*' if abs(t)>1.64 else ''
            row += f'  {b:+.3f}({t:+.1f}){st:4s}'
        else:
            row += f'  {"—":>16s}'
    print(row)
print('\n读法: A vs B = SDI换ISDI的净效应; B vs C = 加HHI的净效应; A vs D = ISDI版加HHI')
