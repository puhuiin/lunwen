# -*- coding: utf-8 -*-
"""L1 变量单变量回归 + 教育变量可得性核查，决定 L1 计分口径。"""
import numpy as np
import pandas as pd
import statsmodels.api as sm
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PANEL = ROOT / '指标计算流水线' / 'output' / '主分析面板_重建_含TOwind.csv'
V2 = ROOT / 'output' / '指标面板_v2_2026-08-26.csv'

df = pd.read_csv(PANEL, parse_dates=['report_date'])
v2 = pd.read_csv(V2, parse_dates=['report_date'])
df = df.merge(v2, on=['fund_code', 'report_date'], how='left', suffixes=('', '_v2'))
for c in ['sharpe8_lag', 'sortino8_lag', 'mppm8_lag', 'rsstab_lag', 'oc_conf']:
    if c + '_v2' in df.columns:
        df[c] = df[c + '_v2']
df['log_aum'] = np.log(df['avg_aum'].clip(lower=1))

print('panel columns with school/edu:', [c for c in df.columns if 'school' in c.lower() or 'edu' in c.lower() or 'cfa' in c.lower()])

# 基金层数据：DV = ff5_adj_return
fund = df.groupby('fund_code').agg(
    ff5=('ff5_adj_return', 'mean'),
    tenure=('mgr_total_tenure_v2', 'mean'),
    age=('log_fund_age', 'mean'),
    aum=('log_aum', 'mean'),
).dropna()
print('\nfund-level N =', len(fund))
print(fund.describe().T[['count', 'mean', 'std', 'min', 'max']].round(4))

print('\n--- 单变量回归：ff5_adj_return ~ X ---')
for x in ['tenure', 'age', 'aum']:
    dd = fund[['ff5', x]].dropna()
    m = sm.OLS(dd['ff5'], sm.add_constant(dd[[x]])).fit(cov_type='HC1')
    b = m.params[x]
    print('%-8s b=%+.5f  t=%+.2f  p=%.4f  R2=%.4f  N=%d'
          % (x, b, m.tvalues[x], m.pvalues[x], m.rsquared, len(dd)))

# 相关矩阵
print('\n相关矩阵：')
print(fund[['ff5', 'tenure', 'age', 'aum']].corr().round(3))
