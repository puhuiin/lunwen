# -*- coding: utf-8 -*-
"""fut1q极端负系数的死亡临近效应归因检验。"""
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
fut1 = np.full(len(df), np.nan)
fut4 = np.full(len(df), np.nan)
second_last = np.zeros(len(df), dtype=bool)
has_t2 = np.zeros(len(df), dtype=bool)
has_t4 = np.zeros(len(df), dtype=bool)
survivor = np.zeros(len(df), dtype=bool)
gmax = int(tidx.max())
for fc, mp in byf.items():
    tmax_fund = max(mp)
    for t, i in mp.items():
        if t == tmax_fund - 1:
            second_last[i] = True
        if (t + 1 in mp) and (t + 2 in mp):
            has_t2[i] = True
        if all(t + k in mp for k in (1, 2, 3, 4)):
            has_t4[i] = True
        if tmax_fund >= gmax:
            survivor[i] = True
        j = mp.get(t + 1)
        if j is not None:
            fut1[i] = ex[j]
        ps = [mp.get(t + k) for k in (1, 2, 3, 4)]
        if all(p is not None for p in ps):
            fut4[i] = float(np.mean([ex[p] for p in ps]))
df['fut1'] = winsor(pd.Series(fut1))
df['fut4'] = winsor(pd.Series(fut4))
df['second_last'] = second_last
df['has_t2'] = has_t2
df['has_t4'] = has_t4
df['survivor'] = survivor

FORM = '{dv} ~ risk_asym + lsv + de + log_aum + log_fund_age + C(year)'


def run(tag, s, dv='fut1'):
    s = s.dropna(subset=L5 + [dv, 'log_aum', 'log_fund_age'])
    m = smf.ols(FORM.format(dv=dv), data=s)\
        .fit(cov_type='cluster', cov_kwds={'groups': s['fund_code'].values})
    print('%-24s N=%4d RA %+.4f(%+.2f) LSV %+.4f(%+.2f) DE %+.4f(%+.2f)' % (
        tag, int(m.nobs),
        m.params['risk_asym'], m.tvalues['risk_asym'],
        m.params['lsv'], m.tvalues['lsv'],
        m.params['de'], m.tvalues['de']))


print('== fut1 样本构成 ==')
sub = df.dropna(subset=L5 + ['fut1', 'log_aum', 'log_fund_age'])
print('倒数第二行占比=%.3f  存续到面板末端占比=%.3f' % (
    sub['second_last'].mean(), sub['survivor'].mean()))
print('倒数第二行: mean fut1=%+.4f mean RA=%.4f n=%d' % (
    sub.loc[sub['second_last'], 'fut1'].mean(),
    sub.loc[sub['second_last'], 'risk_asym'].mean(),
    int(sub['second_last'].sum())))
print('其余行    : mean fut1=%+.4f mean RA=%.4f n=%d' % (
    sub.loc[~sub['second_last'], 'fut1'].mean(),
    sub.loc[~sub['second_last'], 'risk_asym'].mean(),
    int((~sub['second_last']).sum())))

print('\n== 死亡临近效应：fut1 分样本回归 ==')
run('all             ', df)
run('has_t2          ', df[df['has_t2']])
run('has_t4(=fut4样本)', df[df['has_t4']])
run('survivors_only  ', df[df['survivor']])
run('excl_second_last', df[~df['second_last']])
d2 = df.copy()
d2['lag_ex'] = d2.groupby('fund_code')['excess_return'].shift(1)
d2['lag_ex_w'] = winsor(d2['lag_ex'])
run('+lag_ex控制     ', d2)

print('\n== 对照：fut4 全样本 ==')
run('fut4 all        ', df, dv='fut4')

print('\n== RA 描述（按时段）==')
ra = df.dropna(subset=['risk_asym']).copy()
ra['era'] = np.where(ra['year'] <= 2015, 'pre2016', 'y2016+')
print(ra.groupby('era')['risk_asym'].describe().round(4).to_string())
