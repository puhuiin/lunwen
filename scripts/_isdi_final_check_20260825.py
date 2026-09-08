# -*- coding: utf-8 -*-
import pandas as pd, os, warnings
import numpy as np
import statsmodels.formula.api as smf
warnings.filterwarnings('ignore')

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
df = pd.read_csv(os.path.join(ROOT,'指标计算流水线','output','主分析面板_重建_含TOwind.csv'),
                 dtype={'fund_code':str})
BAD_Q = [(2025,3),(2026,2),(2026,3)]
bad = df.set_index(['year','quarter']).index.isin(BAD_Q)
df = df[~bad]
print(f'面板: {len(df)}行, ISDI非空: {df.ISDI.notna().sum()} ({df.ISDI.notna().mean():.1%})')

def winsor(s, lo=0.01, hi=0.99):
    s = s.astype(float); a,b = s.quantile(lo), s.quantile(hi); return s.clip(a,b)

df['log_aum'] = np.log(df['avg_aum'].clip(lower=1e-9))
CTRL = ['ISDI','SDI','ICI','AS_improved','TO_wind','ARG','return_volatility',
        'de','lsv','risk_asym','mgr_total_tenure_v2','log_fund_age','log_aum']
for c in CTRL:
    df[c+'_w'] = winsor(df[c])

# 用ff5_adj_return需要处理ff5_adj_return不在 winsor 前列 —— 面板已有
RHS = [c+'_w' for c in CTRL]
sub = df.dropna(subset=['ff5_adj_return']+RHS).copy().reset_index(drop=True)
m = smf.ols('ff5_adj_return ~ ' + ' + '.join(RHS) + ' + C(year)', data=sub).fit(
    cov_type='cluster', cov_kwds={'groups':sub['fund_code']})
print(f'\n最终面板全指标回归: N={int(m.nobs)}, R2={m.rsquared:.4f}')
for c in ['ISDI','SDI','ICI','AS_improved','risk_asym','de','TO_wind']:
    k = c+'_w'
    b, t, p = m.params[k], m.tvalues[k], m.pvalues[k]
    stars = '***' if p<.01 else '**' if p<.05 else '*' if p<.1 else ''
    print(f'  {c:16s} b={b:+.5f}  t={t:+.2f}{stars}')
