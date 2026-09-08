# -*- coding: utf-8 -*-
"""表4-18 干净版扩展：FF3/FF4 alpha 于干净样本重估（镜像 _recalc_core_tables_clean.py）。

背景：数据法证确认 2025Q3/2026Q2 为净值数据源异常季、2026Q3 为残缺季。
本脚本复用同一污染剔除与 risk_asym 干净重算管线，将因变量换成
FF3（MKT/SMB/HML）与 FF4（+动量MOM）的时序回归截距，供稿件表4-18同步修订；
另保留干净 ff5_adj_return 截面作与主脚本输出的一致性交叉校验。
输出：output/ff34_alpha_clean_2026-08-23.json
"""
import json
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

PANEL = '指标计算流水线/output/主分析面板_重建_含TOwind.csv'
QRET = '指标计算流水线/data/L4_风险应对层/基金季度收益.csv'
OUT_JSON = 'output/ff34_alpha_clean_2026-08-23.json'
BAD_Q = [(2025, 3), (2026, 2), (2026, 3)]
L5 = ['de', 'lsv', 'risk_asym']


def winsor(s, lo=0.01, hi=0.99):
    x = s.dropna()
    return s.clip(x.quantile(lo), x.quantile(hi))


df = pd.read_csv(PANEL)
df['fund_code'] = df['fund_code'].astype(str)
bad = df.set_index(['year', 'quarter']).index.isin(BAD_Q)
df = df[~bad].sort_values(['fund_code', 'year', 'quarter']).reset_index(drop=True)

# ---- risk_asym 干净重算（与主脚本完全一致）----
qret = pd.read_csv(QRET, encoding='utf-8-sig')
qret['report_date'] = pd.to_datetime(qret['report_date'])
qret['year'] = qret['report_date'].dt.year
qret['qtr'] = qret['report_date'].dt.quarter
qb = qret.set_index(['year', 'qtr']).index.isin(BAD_Q)
qret = qret[~qb].sort_values(['fund_code', 'report_date'])
WINDOW, MINP = 8, 4
ra_map = {}
for fc, g in qret.groupby('fund_code'):
    r = g['quarter_return'].values
    ra = np.full(len(r), np.nan)
    for i in range(len(r)):
        seg = r[max(0, i - WINDOW + 1):i + 1]
        if len(seg) < MINP:
            continue
        gain, loss = seg[seg > 0], seg[seg <= 0]
        sg = gain.std() if len(gain) > 1 else np.nan
        sl = loss.std() if len(loss) > 1 else np.nan
        if not (np.isnan(sg) or np.isnan(sl)):
            ra[i] = sg - sl
    for k, v in zip(zip(g['year'].astype(int).values, g['qtr'].astype(int).values), ra):
        ra_map[(str(fc), k[0], k[1])] = v
rdf = pd.DataFrame([(fc, y, q, v) for (fc, y, q), v in ra_map.items()],
                   columns=['fund_code', 'year', 'quarter', 'ra_clean'])
df = df.merge(rdf, on=['fund_code', 'year', 'quarter'], how='left')
df['risk_asym'] = df['ra_clean']
df = df.drop(columns=['ra_clean'])

# ---- FF3 / FF4 alpha 干净重算（镜像 06_因变量._ts_alpha：min obs = k+5）----
FACS = {
    'ff3': ['MKT_excess', 'SMB', 'HML'],
    'ff4': ['MKT_excess', 'SMB', 'HML', 'MOM'],
}
alpha_maps = {}
for nm, fac in FACS.items():
    amap = {}
    for fc, g in df.groupby('fund_code'):
        gg = g.dropna(subset=['excess_return'] + fac)
        y = gg['excess_return'].values.astype(float)
        X = gg[fac].values.astype(float)
        if len(y) < X.shape[1] + 5:
            continue
        A = np.column_stack([np.ones(len(y)), X])
        beta, *_ = np.linalg.lstsq(A, y, rcond=None)
        amap[fc] = float(beta[0])
    alpha_maps[nm] = amap
    print(nm, 'alpha可估基金数=%d' % len(amap))
alpha_maps['ff5'] = {}
fac5 = ['ff5_MKT_excess', 'ff5_SMB', 'ff5_HML', 'ff5_RMW', 'ff5_CMA']
for fc, g in df.groupby('fund_code'):
    gg = g.dropna(subset=['excess_return'] + fac5)
    y = gg['excess_return'].values.astype(float)
    X = gg[fac5].values.astype(float)
    if len(y) < X.shape[1] + 5:
        continue
    A = np.column_stack([np.ones(len(y)), X])
    beta, *_ = np.linalg.lstsq(A, y, rcond=None)
    alpha_maps['ff5'][fc] = float(beta[0])
print('ff5 alpha可估基金数=%d' % len(alpha_maps['ff5']))
df['ff3_clean'] = df['fund_code'].map(alpha_maps['ff3'])
df['ff4_clean'] = df['fund_code'].map(alpha_maps['ff4'])
df['ff5_clean'] = df['fund_code'].map(alpha_maps['ff5'])

# ---- 缩尾与聚合（与主脚本表4-5口径一致）----
for c in ['excess_return', 'avg_aum']:
    x = df[c].dropna()
    df[c + '_w'] = df[c].clip(x.quantile(.01), x.quantile(.99))
for c in L5:
    df[c + '_w'] = winsor(df[c])
df['log_aum'] = np.log(df['avg_aum'].clip(lower=1e-9))

g = df.groupby('fund_code').agg(
    de=('de_w', 'mean'), lsv=('lsv_w', 'mean'), risk_asym=('risk_asym_w', 'mean'),
    ex=('excess_return_w', 'mean'),
    ff5=('ff5_clean', 'first'),
    ff3=('ff3_clean', 'first'), ff4=('ff4_clean', 'first'),
    aum=('avg_aum_w', 'mean')).reset_index()
g['log_aum'] = np.log(g['aum'].clip(lower=1e-9))

out = {}
for dv in ['ff3', 'ff4']:
    sub = g.dropna(subset=L5 + [dv, 'log_aum'])
    m = smf.ols(dv + ' ~ risk_asym + lsv + de + log_aum', data=sub).fit(cov_type='HC1')
    stars = lambda p: ('***' if p < .01 else '**' if p < .05 else '*' if p < .1 else '')
    coef = {k: dict(b=round(float(m.params[k]), 4), t=round(float(m.tvalues[k]), 2),
                    p=round(float(m.pvalues[k]), 4), stars=stars(m.pvalues[k]))
            for k in ['risk_asym', 'lsv', 'de']}
    out[dv] = dict(N=int(m.nobs), r2=round(float(m.rsquared), 4),
                   alpha_mean=round(float(sub[dv].dropna().mean()), 4), coef=coef)
    print(dv, out[dv])

# 一致性交叉校验：干净 ff5 截面应复现主脚本 with_aum_ff5（0.2904/4.82/N=358）
chk = g.dropna(subset=L5 + ['ff5', 'log_aum'])
mc = smf.ols('ff5 ~ risk_asym + lsv + de + log_aum', data=chk).fit(cov_type='HC1')
out['ff5_crosscheck'] = dict(N=int(mc.nobs), r2=round(float(mc.rsquared), 4),
                             ra_b=round(float(mc.params['risk_asym']), 4),
                             ra_t=round(float(mc.tvalues['risk_asym']), 2),
                             alpha_mean=round(float(chk['ff5'].mean()), 4))
print('crosscheck', out['ff5_crosscheck'], '(期望 0.2904/4.82/N358)')

with open(OUT_JSON, 'w', encoding='utf-8') as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
print('saved', OUT_JSON)
