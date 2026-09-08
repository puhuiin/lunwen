# -*- coding: utf-8 -*-
"""第三步：定位间隙截面、交互结构、以及面板边缘RA伪影检验。"""
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
gmax = int(tidx.max())
print('全局末季 tidx=%d => %dQ%d' % (gmax, gmax // 4, gmax % 4 if gmax % 4 else 4))
ex = df['excess_return'].values
byf = defaultdict(dict)
for i, fc in enumerate(df['fund_code'].values):
    byf[fc][int(tidx.values[i])] = i
fut1 = np.full(len(df), np.nan)
has4 = np.zeros(len(df), dtype=bool)
dend = np.full(len(df), np.nan)
for fc, mp in byf.items():
    tm = max(mp)
    for t, i in mp.items():
        j = mp.get(t + 1)
        if j is not None:
            fut1[i] = ex[j]
            has4[i] = all((t + k) in mp for k in (1, 2, 3, 4))
            dend[i] = tm - t
df['fut1w'] = winsor(pd.Series(fut1))
df['has4'] = has4
df['dend'] = dend

sub = df.dropna(subset=L5 + ['fut1w', 'log_aum', 'log_fund_age']).copy()
ng = sub[~sub.has4]
g = sub[sub.has4]

print('\n== 间隙行年季分布 ==')
print(ng.groupby(['year', 'quarter']).size().to_string())

FORM = '{dv} ~ risk_asym + lsv + de + log_aum + log_fund_age + C(year)'


def run(tag, s, fml=None):
    m = smf.ols(fml or FORM.format(dv='fut1w'), data=s)\
        .fit(cov_type='cluster', cov_kwds={'groups': s['fund_code'].values})
    print('%-18s N=%4d RA %+.4f(%+.2f)' % (tag, int(m.nobs),
          m.params['risk_asym'], m.tvalues['risk_asym']))
    return m


print('\n== 分样本 / 混合 / 交互 ==')
run('only_gap   ', ng)
run('only_normal', g)
run('mixed      ', sub)
sub['ra_x_gap'] = sub['risk_asym'] * (~sub['has4'])
m = smf.ols('fut1w ~ risk_asym*has4 + lsv + de + log_aum + log_fund_age + C(year)', data=sub)\
    .fit(cov_type='cluster', cov_kwds={'groups': sub['fund_code'].values})
print('交互: RA(normal)=%+.4f(%+.2f)  RA×gap=%+.4f(%+.2f)' % (
    m.params['risk_asym'], m.tvalues['risk_asym'],
    m.params['risk_asym:(~has4)[T.True]'] if 'risk_asym:(~has4)[T.True]' in m.params.index
    else m.params.filter(like='has4').iloc[0],
    m.tvalues.filter(like='has4').iloc[0]))

print('\n== 混合样本 DFBETA Top12（修正索引）==')
mfull = smf.ols(FORM.format(dv='fut1w'), data=sub)\
    .fit(cov_type='cluster', cov_kwds={'groups': sub['fund_code'].values})
db = mfull.get_influence().dfbetas[:, list(mfull.params.index).index('risk_asym')]
pos = int(np.argmax(np.abs(db)))
order = np.argsort(-np.abs(db))[:12]
out = sub.iloc[order][['fund_code', 'year', 'quarter', 'risk_asym', 'fut1w']].copy()
out['dfbeta'] = db[order]
out['is_gap'] = ~sub.iloc[order]['has4']
print(out.round(4).to_string())

print('\n== 面板边缘RA伪影：全行级（不限于fut1样本）按距末行距离分组 ==')
ra_ok = df.dropna(subset=['risk_asym']).copy()
print(ra_ok.groupby(ra_ok['dend'].clip(upper=8))['risk_asym'].agg(
    ['count', 'mean', 'std']).round(4).to_string())

print('\n== 配对检验：同一基金 边缘行(dend==2) vs 自身其余行 的RA差 ==')
edge = ra_ok[ra_ok.dend == 2].set_index('fund_code')
rest_mean = ra_ok[ra_ok.dend != 2].groupby('fund_code')['risk_asym'].mean()
pair = pd.DataFrame({'edge': edge['risk_asym'], 'rest': rest_mean}).dropna()
pair['diff'] = pair['edge'] - pair['rest']
print('n_funds=%d  mean_diff=%+.4f  t=%+.2f' % (
    len(pair), pair['diff'].mean(),
    pair['diff'].mean() / (pair['diff'].std() / np.sqrt(len(pair)))))
print('\n边缘行的其他指标对照（是否整体异常）:')
for c in ['lsv', 'de', 'excess_return', 'turnover_wind'] if 'turnover_wind' in ra_ok.columns \
        else ['lsv', 'de', 'excess_return']:
    e = ra_ok[ra_ok.dend == 2][c]
    r = ra_ok[ra_ok.dend != 2][c]
    print('%-14s edge_mean=%+.4f rest_mean=%+.4f' % (c, e.mean(), r.mean()))

print('\n== 稳健性：fut1剔除边缘两季(dend<=2)后的回归 ==')
run('excl_dend_le2', sub[sub.dend > 2])

print('\n== 同理检查表4-7组内回归对边缘行的敏感性 ==')
w = df.dropna(subset=L5 + ['excess_return', 'log_aum', 'log_fund_age']).copy()


def within(tag, s):
    m = smf.ols('excess_return ~ risk_asym + lsv + de + log_aum + log_fund_age '
                '+ C(fund_code) + C(year)', data=s)\
        .fit(cov_type='cluster', cov_kwds={'groups': s['fund_code'].values})
    print('%-16s N=%d RA %+.4f(%+.2f) LSV %+.4f(%+.2f) DE %+.4f(%+.2f)' % (
        tag, int(m.nobs),
        m.params['risk_asym'], m.tvalues['risk_asym'],
        m.params['lsv'], m.tvalues['lsv'],
        m.params['de'], m.tvalues['de']))


within('within_all  ', w)
within('within_excl2', w[w.dend > 2])
