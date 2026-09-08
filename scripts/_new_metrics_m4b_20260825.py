# -*- coding: utf-8 -*-
"""
补充验证（2026-08-25）
A. rc_mom 前向预测（future_return）
B. 过度自信候选 oc_conf = ΔTO × I(上季盈利) 的同期与前向
C. OCI_two_sided 同期（面板已有但未入M4）
D. sharpe8 前向（参照）
"""
import pandas as pd, numpy as np, statsmodels.api as sm, os

BASE = r'd:\Desktop\基金经理行为分析研究'
OUT  = os.path.join(BASE, 'output')

panel = pd.read_csv(os.path.join(BASE, '指标计算流水线', 'output', '主分析面板_重建_含TOwind.csv'))
panel['report_date'] = pd.to_datetime(panel['report_date'])
rc  = pd.read_csv(os.path.join(OUT, '认知指标_rc追涨杀跌_2026-08-25.csv'), parse_dates=['report_date'])
rsk = pd.read_csv(os.path.join(OUT, '风险转化指标_2026-08-25.csv'), parse_dates=['report_date'])
df = panel.merge(rc[['fund_code','report_date','rc_mom']], on=['fund_code','report_date'], how='left') \
          .merge(rsk, on=['fund_code','report_date'], how='left')
df['log_aum'] = np.log(df['avg_aum'].clip(lower=1e-9))

# 过度自信：上季盈利后的换手变化（Gervais-Odean 思路）
df = df.sort_values(['fund_code','report_date'])
g = df.groupby('fund_code')
df['to_prev']   = g['TO_wind'].shift(1)
df['ret_prev']  = g['quarter_return'].shift(1)
df['oc_conf']   = (df['TO_wind'] - df['to_prev']) * (df['ret_prev'] > 0).astype(float)

CTRL = ['mgr_total_tenure_v2','log_fund_age','log_aum']
OLD9 = ['risk_asym','de','lsv','ICI','AS_improved','ISDI','ARG','return_volatility','TO_wind']

def winsor(s, p=0.01):
    lo, hi = s.quantile(p), s.quantile(1-p)
    return s.clip(lo, hi)

def fit(dv, rhs, tag, winsor_dv=True):
    d = df[[dv,'fund_code','year'] + rhs + CTRL].dropna()
    y = winsor(d[dv]) if winsor_dv else d[dv]
    X = sm.add_constant(d[rhs + CTRL])
    X = X.join(pd.get_dummies(d['year'], prefix='y', drop_first=True).astype(float))
    m = sm.OLS(y, X).fit(cov_type='cluster', cov_kwds={'groups': d['fund_code']})
    print(f'\n=== {tag}  N={len(d)}  R2={m.rsquared:.3f} ===')
    for v in rhs:
        b,t,p = m.params[v], m.tvalues[v], m.pvalues[v]
        star = '***' if p<0.01 else ('**' if p<0.05 else ('*' if p<0.1 else ''))
        print(f'  {v:20s} {b:+.4f} ({t:+.2f}){star}')

fit('future_return', OLD9 + ['rc_mom'],  'A. rc→下季收益（前向，原始收益）')
fit('ff5_adj_return', OLD9 + ['oc_conf'], 'B. 过度自信 同期')
fit('future_return',  OLD9 + ['oc_conf'], 'B. 过度自信 前向')
fit('ff5_adj_return', OLD9 + ['OCI_two_sided'], 'C. OCI 同期')
fit('future_return',  OLD9 + ['sharpe8'], 'D. sharpe8 前向')
