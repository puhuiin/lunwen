# -*- coding: utf-8 -*-
"""SDI与ISDI共线性诊断：相关系数 + VIF + 系数稳定性"""
import os, warnings
import numpy as np
import pandas as pd
warnings.filterwarnings('ignore')

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
df = pd.read_csv(os.path.join(ROOT,'指标计算流水线','output','主分析面板_重建_含TOwind.csv'),
                 dtype={'fund_code':str})
BAD_Q = [(2025,3),(2026,2),(2026,3)]
df = df[~df.set_index(['year','quarter']).index.isin(BAD_Q)]

def winsor(s, lo=0.01, hi=0.99):
    s = s.astype(float); a,b = s.quantile(lo), s.quantile(hi); return s.clip(a,b)

for c in ['SDI','ISDI']:
    df[c+'_w'] = winsor(df[c])

d = df[['SDI_w','ISDI_w']].dropna()
print(f'===== 双变量关系（N={len(d)}）=====')
print(f'Pearson  r = {d.SDI_w.corr(d.ISDI_w):+.4f}')
print(f'Spearman ρ = {d.SDI_w.corr(d.ISDI_w, method="spearman"):+.4f}')

# VIF（含所有M4 RHS）
from statsmodels.stats.outliers_influence import variance_inflation_factor
df['log_aum'] = np.log(df['avg_aum'].clip(lower=1e-9))
BASE = ['ICI','AS_improved','TO_wind','ARG','return_volatility','de','lsv',
        'risk_asym','mgr_total_tenure_v2','log_fund_age','log_aum']
for c in BASE:
    df[c+'_w'] = winsor(df[c])
X = df[[c+'_w' for c in BASE]+['SDI_w','ISDI_w']].dropna()
print(f'\n===== VIF（全RHS，N={len(X)}）=====')
for i, col in enumerate(X.columns):
    vif = variance_inflation_factor(X.values, i)
    flag = ' ←' if col in ('SDI_w','ISDI_w') else ''
    print(f'  {col:22s} VIF={vif:6.2f}{flag}')
