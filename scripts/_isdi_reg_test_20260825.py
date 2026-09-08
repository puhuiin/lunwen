# -*- coding: utf-8 -*-
"""ISDI并入主面板 + 快速回归验证（FF5 adj return作DV）"""
import os, warnings
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
warnings.filterwarnings('ignore')

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PANEL = os.path.join(ROOT, '指标计算流水线', 'output', '主分析面板_重建_含TOwind.csv')
ISDI_CSV = os.path.join(ROOT, '指标计算流水线', 'data', 'L2_持仓偏离层', '行业风格漂移ISDI.csv')
BAD_Q = [(2025,3),(2026,2),(2026,3)]

df = pd.read_csv(PANEL, dtype={'fund_code':str})
bad = df.set_index(['year','quarter']).index.isin(BAD_Q)
df = df[~bad].sort_values(['fund_code','report_date']).reset_index(drop=True)
df['fund_code'] = df['fund_code'].str.strip()

isd = pd.read_csv(ISDI_CSV, dtype={'fund_code':str})
isd['fund_code'] = isd['fund_code'].str.strip()
# ISDI的report_date已是面板口径（期末+1天），直接格式化
isd['report_date'] = pd.to_datetime(isd['report_date']).dt.strftime('%Y-%m-%d')

before = len(df)
df = df.merge(isd, on=['fund_code','report_date'], how='left')
print(f'面板 {before} 行, ISDI匹配 {df.ISDI.notna().sum()} 行 ({df.ISDI.notna().mean():.1%})')
s = df['ISDI'].dropna()
print(f'ISDI: mean={s.mean():.4f}, std={s.std():.4f}, N={len(s)}')

# 与SDI、行业HHI的相关
for c in ['SDI','industry_hhi','ICI','AS_improved','TO_wind']:
    if c in df.columns:
        d = df[[c,'ISDI']].dropna()
        print(f'corr(ISDI, {c}) = {d.ISDI.corr(d[c]):+.3f}  (N={len(d)})')

# ====== 回归 ======
def winsor(s, lo=0.01, hi=0.99):
    s = s.astype(float); a,b = s.quantile(lo), s.quantile(hi); return s.clip(a,b)

df['log_aum'] = np.log(df['avg_aum'].clip(lower=1e-9))
CTRL = ['ISDI','SDI','industry_hhi','ICI','AS_improved','TO_wind','ARG','return_volatility',
        'de','lsv','risk_asym','mgr_total_tenure_v2','log_fund_age','log_aum']
for c in CTRL:
    df[c+'_w'] = winsor(df[c])

RHS = [c+'_w' for c in CTRL]
print('\n===== 1. ISDI单变量（FF5 adj DV）=====')
sub = df.dropna(subset=['ff5_adj_return','ISDI_w','log_aum_w'])
m = smf.ols('ff5_adj_return ~ ISDI_w + log_aum_w + C(year)', data=sub).fit(
    cov_type='cluster', cov_kwds={'groups':sub['fund_code']})
print(f'  ISDI: b={m.params["ISDI_w"]:+.4f}, t={m.tvalues["ISDI_w"]:+.2f}, p={m.pvalues["ISDI_w"]:.4f}, N={int(m.nobs)}')

print('\n===== 2. 全指标面板（含ISDI）=====')
sub = df.dropna(subset=['ff5_adj_return']+RHS).copy().reset_index(drop=True)
keep = [c for c in RHS if sub[c].std() > 1e-12]
m = smf.ols('ff5_adj_return ~ ' + ' + '.join(keep) + ' + C(year)', data=sub).fit(
    cov_type='cluster', cov_kwds={'groups':sub['fund_code']})
print(f'  N={int(m.nobs)}, R2={m.rsquared:.4f}')
for c in ['ISDI','SDI','industry_hhi','ICI','risk_asym','de']:
    k = c+'_w'
    if k in m.params.index:
        b, t, p = m.params[k], m.tvalues[k], m.pvalues[k]
        stars = '***' if p<.01 else '**' if p<.05 else '*' if p<.1 else ''
        print(f'  {c:16s} b={b:+.5f}  t={t:+.2f}{stars}')
