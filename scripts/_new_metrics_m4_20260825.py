# -*- coding: utf-8 -*-
"""
新指标 M4 验证回归（2026-08-25）
- 风险转化：sharpe8 / sortino8（含等权复合 risk_conv）
- 认知新增：rc_mom（追涨杀跌）
规格对齐主口径 M4-b：DV=FF5季调收益(1/99缩尾)，9旧指标+新指标，
控制 mgr_total_tenure_v2/log_fund_age/log_aum + 年度FE，基金聚类SE。
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

# 风险转化等权复合（z标准化后等权；sortino缺失时退化为sharpe）
for c in ['sharpe8','sortino8']:
    df[c+'_z'] = (df[c] - df[c].mean()) / df[c].std()
df['risk_conv'] = df[['sharpe8_z','sortino8_z']].mean(axis=1, skipna=True)
df.loc[df[['sharpe8_z','sortino8_z']].isna().all(axis=1), 'risk_conv'] = np.nan

CTRL = ['mgr_total_tenure_v2','log_fund_age','log_aum']
OLD9 = ['risk_asym','de','lsv','ICI','AS_improved','ISDI','ARG','return_volatility','TO_wind']

def winsor(s, p=0.01):
    lo, hi = s.quantile(p), s.quantile(1-p)
    return s.clip(lo, hi)

def fit(dv, rhs_vars, tag):
    d = df[[dv,'fund_code','year'] + rhs_vars + CTRL].dropna()
    y = winsor(d[dv])
    X = d[rhs_vars + CTRL].copy()
    X = sm.add_constant(X)
    X = X.join(pd.get_dummies(d['year'], prefix='y', drop_first=True).astype(float))
    m = sm.OLS(y, X).fit(cov_type='cluster', cov_kwds={'groups': d['fund_code']})
    print(f'\n=== {tag}  N={len(d)}  R2={m.rsquared:.3f} ===')
    for v in rhs_vars:
        b, t, p = m.params[v], m.tvalues[v], m.pvalues[v]
        star = '***' if p<0.01 else ('**' if p<0.05 else ('*' if p<0.1 else ''))
        print(f'  {v:20s} {b:+.4f} ({t:+.2f}){star}')
    return m

print('>>> 新指标与旧9指标相关矩阵（关键对角）')
corr = df[OLD9 + ['sharpe8','sortino8','risk_conv','rc_mom','quarter_return']].corr()
print(corr.loc[['sharpe8','sortino8','risk_conv','rc_mom'], ['return_volatility','ARG','de','risk_asym','quarter_return']].round(2).to_string())

fit('ff5_adj_return', OLD9, 'M4-b 基线（旧9指标）')
fit('ff5_adj_return', OLD9 + ['sharpe8'],  'M4+sharpe8')
fit('ff5_adj_return', OLD9 + ['sortino8'], 'M4+sortino8（受限样本）')
fit('ff5_adj_return', OLD9 + ['rc_mom'],   'M4+rc_mom（认知新增，受限样本）')
fit('ff5_adj_return', OLD9 + ['risk_conv','rc_mom'], 'M4+风险转化复合+rc')
# 去掉RV换新指标的版本（RV落榜，看替代效果）
fit('ff5_adj_return', [v for v in OLD9 if v!='return_volatility'] + ['risk_conv','rc_mom'],
    'M4 以risk_conv替代RV + rc_mom')
