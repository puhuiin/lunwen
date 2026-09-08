# -*- coding: utf-8 -*-
"""验证ARG实证矛盾：画像文档(+0.047**/+0.342***) vs 指标总表(t=-2.94***)"""
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

print(f'面板: {len(df)}行, ARG非空={df["ARG"].notna().sum()}({df["ARG"].notna().mean():.0%}), '
      f'ff5_adj非空={df["ff5_adj_return"].notna().sum()}')
print(f'ARG统计: mean={df["ARG"].mean():.4f}, std={df["ARG"].std():.4f}, '
      f'min={df["ARG"].min():.4f}, max={df["ARG"].max():.4f}')

print('\n===== 口径A: 画像文档式——基金层截面(DV=ff5_adj, 控制log_aum/log_fund_age) =====')
fund = df.dropna(subset=['ff5_adj_return','ARG','avg_aum']).copy()
fund['log_aum'] = np.log(fund['avg_aum'].clip(lower=1e-9))
fund['ARG_w'] = winsor(fund['ARG'])
fund['ff5_w'] = winsor(fund['ff5_adj_return'])
m = smf.ols('ff5_w ~ ARG_w + log_aum + log_fund_age', data=fund).fit()
print(f'基金层截面 N={int(m.nobs)}: β={m.params["ARG_w"]:+.4f} t={m.tvalues["ARG_w"]:+.2f}')

print('\n===== 口径B: 面板单变量(DV=ff5_adj_return_w, ARG_w + 年度FE, 基金聚类) =====')
sub = df.dropna(subset=['ff5_adj_return','ARG','avg_aum']).copy()
sub['log_aum'] = np.log(sub['avg_aum'].clip(lower=1e-9))
sub['ARG_w'] = winsor(sub['ARG'])
sub['ff5_w'] = winsor(sub['ff5_adj_return'])
m2 = smf.ols('ff5_w ~ ARG_w + log_aum + C(year)', data=sub).fit(
    cov_type='cluster', cov_kwds={'groups':sub['fund_code']})
print(f'面板 N={int(m2.nobs)}: β={m2.params["ARG_w"]:+.4f} t={m2.tvalues["ARG_w"]:+.2f}')

print('\n===== 口径C: 画像文档式组内FE(DV=quarter_return, 组内去均值+年度FE) =====')
sub3 = df.dropna(subset=['quarter_return','ARG']).copy().reset_index(drop=True)
sub3['year'] = sub3['year'].astype(int)
g = sub3.groupby('fund_code')
sub3['y_dm'] = sub3['quarter_return'] - g['quarter_return'].transform('mean')
sub3['x_dm'] = sub3['ARG'] - g['ARG'].transform('mean')
yr = pd.get_dummies(sub3['year'], prefix='yr', drop_first=True).astype(float)
sub3 = pd.concat([sub3, yr], axis=1)
yr_cols = list(yr.columns)
X = sub3[['x_dm']+yr_cols].values
import statsmodels.api as sm
res = sm.OLS(sub3['y_dm'].values, X).fit(cov_type='cluster',
        cov_kwds={'groups':sub3['fund_code'].values})
print(f'组内FE N={int(res.nobs)}: β={res.params[0]:+.4f} t={res.tvalues[0]:+.2f}')

print('\n===== 口径D: ARG对RG的相关性(检查共线性/口径混用) =====')
if 'RG' in df.columns:
    both = df.dropna(subset=['ARG','RG'])
    print(f'ARG与RG相关: r={both["ARG"].corr(both["RG"]):.3f} (N={len(both)})')
else:
    print('面板中无RG列')
