# -*- coding: utf-8 -*-
"""解剖fut1样本中"有t+1但未来4季不全"的行：它们是谁、为何撬动系数。"""
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
has4 = np.zeros(len(df), dtype=bool)
dist_to_end = np.full(len(df), np.nan)
resume_after_gap = np.zeros(len(df), dtype=bool)
for fc, mp in byf.items():
    tmax = max(mp)
    for t, i in mp.items():
        j = mp.get(t + 1)
        if j is not None:
            fut1[i] = ex[j]
            has4[i] = all((t + k) in mp for k in (1, 2, 3, 4))
            dist_to_end[i] = tmax - t
            resume_after_gap[i] = any((t + k) in mp for k in (5, 6, 7, 8))
df['fut1w'] = winsor(pd.Series(fut1))
df['has4'] = has4
df['dist_to_end'] = dist_to_end
df['resume_after_gap'] = resume_after_gap

sub = df.dropna(subset=L5 + ['fut1w', 'log_aum', 'log_fund_age']).copy()
g = sub[sub.has4]
ng = sub[~sub.has4]

print('== 样本构成 ==')
print('fut1回归样本 N=%d；其中"未来4季不齐"行 n=%d (%.1f%%)，涉及基金 %d 只' % (
    len(sub), len(ng), 100 * len(ng) / len(sub), ng['fund_code'].nunique()))

print('\n== 间隙行的位置特征 ==')
print('距基金末行的季度距离分布：')
print(ng['dist_to_end'].value_counts().sort_index().to_string())
print('其中未来第5-8季又恢复出行的(内部空洞)占比=%.3f' % ng['resume_after_gap'].mean())

print('\n== 间隙行 vs 正常行 描述 ==')
cols = ['risk_asym', 'lsv', 'de', 'fut1w', 'excess_return']
desc = pd.DataFrame({
    'gap_mean': ng[cols].mean(), 'normal_mean': g[cols].mean(),
    'gap_sd': ng[cols].std(), 'normal_sd': g[cols].std()})
print(desc.round(4).to_string())

print('\n== 分样本与混合回归 ==')
FORM = '{dv} ~ risk_asym + lsv + de + log_aum + log_fund_age + C(year)'


def run(tag, s, dv='fut1w'):
    m = smf.ols(FORM.format(dv=dv), data=s)\
        .fit(cov_type='cluster', cov_kwds={'groups': s['fund_code'].values})
    print('%-14s N=%4d RA %+.4f(%+.2f) LSV %+.4f(%+.2f) DE %+.4f(%+.2f)' % (
        tag, int(m.nobs),
        m.params['risk_asym'], m.tvalues['risk_asym'],
        m.params['lsv'], m.tvalues['lsv'],
        m.params['de'], m.tvalues['de']))


run('only_gap   ', ng)
run('only_normal', g)
run('mixed      ', sub)

print('\n== 混合样本 RA 的DFBETA Top15 ==')
m = smf.ols(FORM.format(dv='fut1w'), data=sub)\
    .fit(cov_type='cluster', cov_kwds={'groups': sub['fund_code'].values})
db = m.get_influence().dfbetas[:, list(m.params.index).index('risk_asym')]
top = pd.Series(np.abs(db), index=sub.index).nlargest(15)
out = sub.loc[top.index, ['fund_code', 'year', 'quarter', 'risk_asym', 'fut1w',
                          'excess_return']].copy()
out['dfbeta'] = db[top.index]
out['is_gap'] = ~sub.loc[top.index, 'has4']
print(out.round(4).to_string())

print('\n== 剔除Top-50影响行后 ==')
drop_idx = pd.Series(np.abs(db), index=sub.index).nlargest(50).index
run('excl_top50 ', sub.drop(index=drop_idx))
print('top50中间隙行个数=%d' % int((~sub.loc[drop_idx, 'has4']).sum()))
