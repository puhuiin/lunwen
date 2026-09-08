# -*- coding: utf-8 -*-
"""
rc_mom 机制深化：前向收益衰减检验（2026-08-25）
检验 rc_mom（追涨杀跌动量行为）对前向 1Q / 2Q / 4Q 收益的预测衰减形态。
DV: lead1=future_return, lead2=q(t+2), fut4q=未来4季累计（简单和）
规格同 M4：winsor1% + CTRL + yearFE + 基金聚类。
同时给出与同期 ff5_adj_return 的对照。
"""
import pandas as pd, numpy as np, statsmodels.api as sm, os

BASE = r'd:\Desktop\基金经理行为分析研究'
OUT = os.path.join(BASE, 'output')

panel = pd.read_csv(os.path.join(BASE, '指标计算流水线', 'output', '主分析面板_重建_含TOwind.csv'),
                    parse_dates=['report_date'])
newm = pd.read_csv(os.path.join(OUT, '新增指标面板_2026-08-25.csv'), parse_dates=['report_date'])

df = panel.merge(newm[['fund_code','report_date','rc_mom','sharpe8_lag']],
                 on=['fund_code','report_date'], how='left')
df['log_aum'] = np.log(df['avg_aum'].clip(lower=1e-9))
df = df.sort_values(['fund_code','report_date'])

g = df.groupby('fund_code')['quarter_return']
df['lead2'] = g.shift(-2)
f = df.groupby('fund_code')['quarter_return']
df['fut4q'] = f.shift(-1) + f.shift(-2) + f.shift(-3) + f.shift(-4)

CTRL = ['mgr_total_tenure_v2','log_fund_age','log_aum']

def winsor(s, p=0.01):
    lo, hi = s.quantile(p), s.quantile(1-p)
    return s.clip(lo, hi)

def fit(dv, rhs, tag):
    d = df[[dv,'fund_code','year'] + rhs + CTRL].dropna()
    y = winsor(d[dv])
    X = sm.add_constant(d[rhs + CTRL])
    X = X.join(pd.get_dummies(d['year'], prefix='y', drop_first=True).astype(float))
    m = sm.OLS(y, X).fit(cov_type='cluster', cov_kwds={'groups': d['fund_code']})
    print(f'\n=== {tag}  N={len(d)}  R2={m.rsquared:.3f} ===')
    for v in rhs:
        b,t,p = m.params[v], m.tvalues[v], m.pvalues[v]
        star = '***' if p<0.01 else ('**' if p<0.05 else ('*' if p<0.1 else ''))
        print(f'  {v:16s} {b:+.4f} ({t:+.2f}){star}')
    return m

RHS = ['rc_mom','sharpe8_lag','ICI','AS_improved','ARG']

print('>>> rc_mom 前向收益衰减检验（RHS 仅列关键变量）')
fit('ff5_adj_return', RHS, '同期 FF5 alpha（对照）')
fit('future_return', RHS, '前向 1 季')
fit('lead2', RHS, '前向 2 季')
fit('fut4q', RHS, '前向 4 季累计')

# 换手成本通道交叉验证：rc_mom × TO_wind 是否同向恶化前向收益
df['rcXto'] = df['rc_mom'] * df['TO_wind']
fit('future_return', ['rc_mom','TO_wind','rcXto','ICI','ARG'], '前向1季 + rc×TO 交互（换手成本通道）')

df[['fund_code','report_date','rc_mom','lead2','fut4q']].to_csv(
    os.path.join(OUT, 'rc_mom前向衰减_2026-08-25.csv'), index=False, encoding='utf-8-sig')
print('\n已保存 output/rc_mom前向衰减_2026-08-25.csv')
