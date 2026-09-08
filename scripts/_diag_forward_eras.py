# -*- coding: utf-8 -*-
"""前向回归新结果的归因诊断：时段拆分/极端值敏感度/机制定位。"""
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from collections import defaultdict

PANEL = '指标计算流水线/output/主分析面板_重建_含TOwind.csv'
df = pd.read_csv(PANEL)
df['fund_code'] = df['fund_code'].astype(str)
df = df.sort_values(['fund_code', 'year', 'quarter']).reset_index(drop=True)
L5 = ['de', 'lsv', 'risk_asym']


def winsor(s, lo=0.01, hi=0.99):
    x = s.dropna()
    return s.clip(x.quantile(lo), x.quantile(hi))


df['log_aum'] = np.log(df['avg_aum'].clip(lower=1e-9))
tidx = (df['year'] * 4 + df['quarter']).astype(int)
ex = df['excess_return'].values
byf = defaultdict(dict)
for i, fc in enumerate(df['fund_code'].values):
    byf[fc][int(tidx.values[i])] = i
fut4 = np.full(len(df), np.nan)
fut1 = np.full(len(df), np.nan)
for fc, mp in byf.items():
    for t, i in mp.items():
        j = mp.get(t + 1)
        if j is not None:
            fut1[i] = ex[j]
        ps = [mp.get(t + k) for k in (1, 2, 3, 4)]
        if all(p is not None for p in ps):
            fut4[i] = float(np.mean([ex[p] for p in ps]))
df['fut4q'] = winsor(pd.Series(fut4))
df['fut1q'] = winsor(pd.Series(fut1))

print('== L5 描述：分时段 ==')
era = np.where(df['year'] <= 2015, 'pre2016', 'y2016+')
print(df.groupby(era)[L5 + ['excess_return']].agg(['count', 'mean', 'std']).round(4).to_string())

print('\n== 前向回归：分时段（缩尾, 年份FE, 控制aum/age, 基金聚类）==')
for dv in ['fut1q', 'fut4q']:
    sub_all = df.dropna(subset=L5 + [dv, 'log_aum', 'log_fund_age'])
    for tag, s in [('full ', sub_all),
                   ('y16+ ', sub_all[sub_all.year >= 2016]),
                   ('pre16', sub_all[sub_all.year <= 2015])]:
        m = smf.ols(dv + ' ~ risk_asym + lsv + de + log_aum + log_fund_age + C(year)', data=s)\
            .fit(cov_type='cluster', cov_kwds={'groups': s['fund_code'].values})
        print('%s %s N=%d RA %+.4f(%+.2f) LSV %+.4f(%+.2f) DE %+.4f(%+.2f)' % (
            dv, tag, m.nobs,
            m.params['risk_asym'], m.tvalues['risk_asym'],
            m.params['lsv'], m.tvalues['lsv'],
            m.params['de'], m.tvalues['de']))

print('\n== fut1q 极端值敏感度（全样本, 年份FE）==')
sub = df.dropna(subset=L5 + ['fut1q', 'log_aum', 'log_fund_age'])
raw1 = pd.Series(fut1, index=df.index).reindex(sub.index)
for qlo, qhi in [(0, 1), (0.005, 0.995), (0.025, 0.975), (0.05, 0.95)]:
    yv = winsor(raw1, qlo, qhi)
    d = sub.copy(); d['y'] = yv
    m = smf.ols('y ~ risk_asym + lsv + de + log_aum + log_fund_age + C(year)', data=d)\
        .fit(cov_type='cluster', cov_kwds={'groups': d['fund_code'].values})
    print('clip[%.3f,%.3f] N=%d RA %+.4f(%+.2f)' % (qlo, qhi, m.nobs,
          m.params['risk_asym'], m.tvalues['risk_asym']))
m = smf.ols('y ~ risk_asym + lsv + de + log_aum + log_fund_age + C(year)',
            data=sub.assign(y=sub.fut1q.rank() / len(sub)))\
    .fit(cov_type='cluster', cov_kwds={'groups': sub['fund_code'].values})
print('rankDV      N=%d RA %+.4f(%+.2f)' % (m.nobs, m.params['risk_asym'], m.tvalues['risk_asym']))

print('\n== RA 与未来收益的简单相关（分时段）==')
for tag, s in [('full ', df.dropna(subset=['risk_asym', 'fut1q'])),
               ('y16+ ', df[(df.year >= 2016)].dropna(subset=['risk_asym', 'fut1q'])),
               ('pre16', df[(df.year <= 2015)].dropna(subset=['risk_asym', 'fut1q']))]:
    print(tag, 'corr(RA,fut1q)=%.4f  corr(RA,fut4q)=%.4f' % (
        s[['risk_asym', 'fut1q']].corr().iloc[0, 1],
        s[['risk_asym', 'fut4q']].corr().iloc[0, 1]))

print('\n== RA 是否近似基金常量：组内/总体方差分解 ==')
ra = df.dropna(subset=['risk_asym'])
gm = ra.groupby('fund_code')['risk_asym'].transform('mean')
between = ra.groupby('fund_code')['risk_asym'].mean().var()
within = (ra['risk_asym'] - gm).var()
total = ra['risk_asym'].var()
print('between_var=%.6f within_var=%.6f total=%.6f between_share=%.3f' % (
    between, within, total, between / total))
print(ra.groupby(era)['risk_asym'].describe().round(4).to_string())
