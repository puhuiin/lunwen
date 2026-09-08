# -*- coding: utf-8 -*-
"""
sharpe8 滞后窗口修正（2026-08-25）
原 sharpe8 滚动8季窗口含当季收益，与同期DV ff5_adj_return 机械重叠。
修正为 lag 版：截至上季末的滚动8季夏普（shift(1) 后 rolling(8)），再进同期M4。
同时汇总最终新指标面板：sharpe8_lag / sortino8_lag / rc_mom / oc_conf。
"""
import pandas as pd, numpy as np, statsmodels.api as sm, os

BASE = r'd:\Desktop\基金经理行为分析研究'
OUT  = os.path.join(BASE, 'output')

panel = pd.read_csv(os.path.join(BASE, '指标计算流水线', 'output', '主分析面板_重建_含TOwind.csv'))
panel['report_date'] = pd.to_datetime(panel['report_date'])

q = panel[['fund_code','report_date','quarter_return','rf']].drop_duplicates().sort_values(['fund_code','report_date'])
q['ex'] = q['quarter_return'] - q['rf']

def roll_lag(g):
    g = g.sort_values('report_date')
    ex_lag = g['ex'].shift(1)  # 截至上季末
    m  = ex_lag.rolling(8, min_periods=4).mean()
    sd = ex_lag.rolling(8, min_periods=4).std()
    g['sharpe8_lag'] = m / sd
    dn = ex_lag.where(ex_lag < 0)
    dd = dn.rolling(8, min_periods=4).std()
    g['sortino8_lag'] = np.where(dd > 1e-6, m / dd, np.nan)
    return g

q = q.groupby('fund_code', group_keys=False).apply(roll_lag).reset_index(drop=True)
if 'fund_code' not in q.columns:
    q['fund_code'] = panel[['fund_code','report_date']].drop_duplicates().sort_values(['fund_code','report_date'])['fund_code'].values

rc  = pd.read_csv(os.path.join(OUT, '认知指标_rc追涨杀跌_2026-08-25.csv'), parse_dates=['report_date'])
df = panel.merge(q[['fund_code','report_date','sharpe8_lag','sortino8_lag']], on=['fund_code','report_date'], how='left') \
          .merge(rc[['fund_code','report_date','rc_mom']], on=['fund_code','report_date'], how='left')
df['log_aum'] = np.log(df['avg_aum'].clip(lower=1e-9))
df = df.sort_values(['fund_code','report_date'])
g = df.groupby('fund_code')
df['oc_conf'] = (df['TO_wind'] - g['TO_wind'].shift(1)) * (g['quarter_return'].shift(1) > 0).astype(float)

CTRL = ['mgr_total_tenure_v2','log_fund_age','log_aum']
OLD9 = ['risk_asym','de','lsv','ICI','AS_improved','ISDI','ARG','return_volatility','TO_wind']

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
        print(f'  {v:20s} {b:+.4f} ({t:+.2f}){star}')

print('>>> sharpe8_lag 与当期收益/DV相关（应≈0 才无机械重叠）')
print(df[['sharpe8_lag','quarter_return','ff5_adj_return']].corr().round(3).to_string())

fit('ff5_adj_return', OLD9 + ['sharpe8_lag'], 'M4 + sharpe8_lag（滞后，无机械重叠）')
fit('ff5_adj_return', OLD9 + ['sharpe8_lag','rc_mom','oc_conf'], 'M4 + 三新指标同入')
fit('ff5_adj_return', [v for v in OLD9 if v!='return_volatility'] + ['sharpe8_lag','rc_mom','oc_conf'],
    'M4 以sharpe8_lag替代RV + rc + oc')
fit('future_return',  OLD9 + ['sharpe8_lag','rc_mom','oc_conf'], '前向参照')

df[['fund_code','report_date','sharpe8_lag','sortino8_lag','rc_mom','oc_conf']].to_csv(
    os.path.join(OUT, '新增指标面板_2026-08-25.csv'), index=False, encoding='utf-8-sig')
print('\n已保存 output/新增指标面板_2026-08-25.csv')
