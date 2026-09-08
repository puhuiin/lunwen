# -*- coding: utf-8 -*-
"""M4全指标面板：SDI vs ISDI 对比（FF5 adj DV，基金聚类SE）"""
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
BASE = ['ICI','AS_improved','TO_wind','ARG','return_volatility','de','lsv',
        'risk_asym','mgr_total_tenure_v2','log_fund_age','log_aum']

def run(drift_vars, label, dv='ff5_adj_return'):
    cols = BASE + drift_vars
    for c in cols + [dv]:
        df[c+'_w'] = winsor(df[c]) if c != dv else df[c]
    sub = df.dropna(subset=[dv]+[c+'_w' for c in cols]).copy().reset_index(drop=True)
    rhs = [c+'_w' for c in cols]
    keep = [c for c in rhs if sub[c].std() > 1e-12]
    m = smf.ols(dv+' ~ '+' + '.join(keep)+' + C(year)', data=sub).fit(
        cov_type='cluster', cov_kwds={'groups':sub['fund_code']})
    print(f'\n===== {label}: N={int(m.nobs)}, R2={m.rsquared:.4f} =====')
    for c in cols:
        k = c+'_w'
        if k in m.params.index:
            b, t, p = m.params[k], m.tvalues[k], m.pvalues[k]
            stars = '***' if p<.01 else '**' if p<.05 else '*' if p<.1 else ''
            mark = ' ←' if c in drift_vars else ''
            print(f'  {c:16s} b={b:+.5f}  t={t:+.2f}{stars}{mark}')
    return m

# 三种规格
run(['SDI'], 'M4-a: 仅SDI（原规格）')
run(['ISDI'], 'M4-b: 仅ISDI（替换）')
run(['SDI','ISDI'], 'M4-c: 两者同入')
