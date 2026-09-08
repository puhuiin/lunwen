# -*- coding: utf-8 -*-
"""重算稿件核心识别回归（表4-5截面 / 表4-6前向 / 表4-7组内），探索可复现口径。"""
import json
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

PANEL = '指标计算流水线/output/主分析面板_重建_含TOwind.csv'
df = pd.read_csv(PANEL)
df = df.sort_values(['fund_code', 'year', 'quarter']).reset_index(drop=True)

L5 = ['de', 'lsv', 'risk_asym']


def winsor(s, lo=0.01, hi=0.99):
    x = s.dropna()
    a, b = x.quantile(lo), x.quantile(hi)
    return s.clip(a, b)


def fit_ols(formula, data, cov='HC1', groups=None):
    kw = {'cov_type': cov}
    if groups is not None:
        kw['cov_kwds'] = {'groups': groups.values}
    m = smf.ols(formula, data=data).fit(**kw)
    return m


def show(tag, m, keys=('risk_asym', 'lsv', 'de')):
    out = ['%s N=%d R2=%.4f' % (tag, int(m.nobs), m.rsquared)]
    for k in keys:
        if k in m.params.index:
            out.append('%s b=%+.4f t=%+.2f p=%.4f' % (k, m.params[k], m.tvalues[k], m.pvalues[k]))
    print(' | '.join(out))


# ---------- 目标值 ----------
T45 = dict(N=200, r2_ff5=0.177, r2_ex=0.175,
           ra=(0.205, 4.55), lsv=(0.004, 0.06), de=(-0.057, -3.28))
T46 = dict(N=1355, r2_4q=0.146, r2_1q=0.179,
           ra4=(0.313, 10.51), ra1=(-0.064, -1.14),
           de4=(-0.056, -7.11), de1=(-0.071, -4.81))
T47 = dict(N=1642, nfund=302, wr2=0.341,
           de=(-0.041, -3.64), lsv=(-0.005, -0.15), ra=(-0.076, -1.29))

print('=' * 25, '表4-5 截面基准：基金层时间均值折叠')
# 缩尾口径选择：面板级缩尾后折叠 vs 折叠后再缩尾
df_w = df.copy()
for c in L5 + ['excess_return', 'ff5_adj_return', 'avg_aum']:
    df_w[c] = winsor(df[c])

for tag, src in [('panel-winsor', df_w), ('raw', df)]:
    g = src.groupby('fund_code').agg(
        de=('de', 'mean'), lsv=('lsv', 'mean'), risk_asym=('risk_asym', 'mean'),
        ex=('excess_return', 'mean'), aum=('avg_aum', 'mean'),
        ff5=('ff5_adj_return', 'first')).dropna().reset_index()
    g['log_aum'] = np.log(g['aum'])
    print('--', tag, 'complete-case funds:', len(g))
    m = fit_ols('ff5 ~ risk_asym + lsv + de + log_aum', g)
    show('ff5~aum', m)
    m = fit_ols('ex ~ risk_asym + lsv + de + log_aum', g)
    show('ex~aum ', m)

print()
print('=' * 25, '表4-7 组内双向FE（先探样本）')
base = df.dropna(subset=L5 + ['excess_return'])
print('rows with L5+excess:', len(base), 'funds:', base.fund_code.nunique())
m = fit_ols('excess_return ~ de + lsv + risk_asym + C(fund_code) + C(year)', base,
            cov='cluster', groups=base['fund_code'])
print('twFE N=%d funds=%d r2=%.4f within_r2~%.4f' % (
    int(m.nobs), base.fund_code.nunique(), m.rsquared, m.rsquared_within if hasattr(m, 'rsquared_within') else float('nan')))
show('twFE', m)

print()
print('=' * 25, '表4-6 前向：构造4Q/1Q前瞻因变量')
d = df.copy()
d['tidx'] = d['year'] * 4 + d['quarter']
fut4 = np.full(len(d), np.nan)
fut1 = np.full(len(d), np.nan)
pos = {k: i for i, k in enumerate(d.index)}
byfund = {fc: gidx for fc, gidx in d.groupby('fund_code').groups.items()}
for fc, idx in byfund.items():
    arr_t = d.loc[idx, 'tidx'].values
    arr_e = d.loc[idx, 'excess_return'].values
    for j, ti in enumerate(arr_t):
        nxt = arr_e[(arr_t > ti) & (arr_t <= ti + 4)]
        if len(nxt) == 4:
            fut4[pos[idx[j]]] = np.nanmean(nxt)
        nx1 = arr_e[arr_t == ti + 1]
        if len(nx1) == 1:
            fut1[pos[idx[j]]] = nx1[0]
d['fut4q'] = fut4
d['fut1q'] = fut1
sub = d.dropna(subset=L5 + ['fut4q'])
print('complete L5+fut4q rows:', len(sub))
subw = sub.copy()
for c in L5 + ['excess_return', 'avg_aum', 'log_fund_age']:
    subw[c] = winsor(d[c])
for tag, s in [('raw', sub), ('winsor', subw)]:
    s2 = s.dropna(subset=['avg_aum']).copy()
    s2['log_aum'] = np.log(s2['avg_aum'])
    m = fit_ols('fut4q ~ risk_asym + lsv + de + log_aum + log_fund_age + C(year)', s2,
                cov='cluster', groups=s2['fund_code'])
    show(tag + ' 4Q', m)
    s3 = d.dropna(subset=L5 + ['fut1q', 'avg_aum']).copy()
    if tag == 'winsor':
        for c in L5 + ['avg_aum', 'log_fund_age']:
            s3[c] = winsor(d[[c]].iloc[:, 0])
        s3['log_aum'] = np.log(s3['avg_aum'])
    else:
        s3['log_aum'] = np.log(s3['avg_aum'])
    m = fit_ols('fut1q ~ risk_asym + lsv + de + log_aum + log_fund_age + C(year)', s3,
                cov='cluster', groups=s3['fund_code'])
    show(tag + ' 1Q', m)
