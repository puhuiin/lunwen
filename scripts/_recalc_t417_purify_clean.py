# -*- coding: utf-8 -*-
"""表4-17（HM择时控制）与构念纯化检验·干净版权威重算。

镜像 _recalc_core_tables_clean.py 的口径：
  - 剔除 (year,quarter) ∈ {(2025,3),(2026,2),(2026,3)}
  - risk_asym 于干净季收益序列重估（滚动8季，min_periods=4）
  - ff5_adj_return 于干净样本重估（FF5五因子时序回归截距，观测>=因子数+5）
  - 缩尾/HC1/log_aum 与主脚本一致

新增：
  - HM上行择时系数 b2 于干净序列估计：r_t = a + b1*MKT_t + b2*max(MKT_t,0)，
    要求有效观测 >= 16 期（沿用正文"至少16期"口径）
  - 表4-17 两行：不控制择时 / 控制HM择时（同一基金子集，均含 log_aum，HC1）
  - 构念纯化：面板行级 risk_asym_w 对 (b2, log_aum) 正交化取残差 ra_pur，
    重跑 截面(ff5)/前向4Q/前向1Q/组内(双向FE) 四个回归
输出：output/t417_purify_clean_2026-08-23.json
"""
import json
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

PANEL = '指标计算流水线/output/主分析面板_重建_含TOwind.csv'
QRET = '指标计算流水线/data/L4_风险应对层/基金季度收益.csv'
OUT_JSON = 'output/t417_purify_clean_2026-08-23.json'
BAD_Q = [(2025, 3), (2026, 2), (2026, 3)]
L5 = ['de', 'lsv', 'risk_asym']
MIN_OBS_TIMING = 16


def winsor(s, lo=0.01, hi=0.99):
    x = s.dropna()
    a, b = x.quantile(lo), x.quantile(hi)
    return s.clip(a, b)


def pack(m, keys):
    return {k: dict(b=round(float(m.params[k]), 4), t=round(float(m.tvalues[k]), 2),
                    p=round(float(m.pvalues[k]), 4),
                    stars=('***' if m.pvalues[k] < .01 else '**' if m.pvalues[k] < .05
                           else '*' if m.pvalues[k] < .1 else '')) for k in keys}


print('load', PANEL)
df = pd.read_csv(PANEL)
df['fund_code'] = df['fund_code'].astype(str)

n0 = len(df)
bad = df.set_index(['year', 'quarter']).index.isin(BAD_Q)
df = df[~bad].sort_values(['fund_code', 'year', 'quarter']).reset_index(drop=True)
print('剔除污染季 %s：%d -> %d 行' % (BAD_Q, n0, len(df)))

# ---- risk_asym 干净重算（镜像主脚本）----
print('recompute risk_asym ...')
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
    ys = g['year'].astype(int).values
    qs = g['qtr'].astype(int).values
    for k, v in zip(zip(ys, qs), ra):
        ra_map[(str(fc), k[0], k[1])] = v
rdf = pd.DataFrame([(fc, y, q, v) for (fc, y, q), v in ra_map.items()],
                   columns=['fund_code', 'year', 'quarter', 'ra_clean'])
df = df.merge(rdf, on=['fund_code', 'year', 'quarter'], how='left')
df['risk_asym'] = df['ra_clean']
df = df.drop(columns=['ra_clean'])

# ---- ff5_adj_return 干净重算（镜像主脚本）----
print('recompute ff5_adj_return ...')
fac = ['ff5_MKT_excess', 'ff5_SMB', 'ff5_HML', 'ff5_RMW', 'ff5_CMA']
alpha_map = {}
for fc, g in df.groupby('fund_code'):
    gg = g.dropna(subset=['excess_return'] + fac)
    y = gg['excess_return'].values.astype(float)
    X = gg[fac].values.astype(float)
    if len(y) < X.shape[1] + 5:
        continue
    A = np.column_stack([np.ones(len(y)), X])
    beta, *_ = np.linalg.lstsq(A, y, rcond=None)
    alpha_map[fc] = float(beta[0])
df['ff5_clean'] = df['fund_code'].map(alpha_map)
print('alpha可估基金数=%d' % len(alpha_map))

# ---- 缩尾（干净样本边界）----
for c in ['excess_return', 'avg_aum']:
    x = df[c].dropna()
    lo, hi = float(x.quantile(.01)), float(x.quantile(.99))
    df[c + '_w'] = df[c].clip(lo, hi)
for c in L5:
    df[c + '_w'] = winsor(df[c])
df['log_aum'] = np.log(df['avg_aum'].clip(lower=1e-9))

# ---- HM 择时系数（干净序列，>=16期）----
print('estimate HM timing b2 on clean series ...')
b2_map, ntm = {}, 0
for fc, g in df.groupby('fund_code'):
    gg = g.dropna(subset=['excess_return', 'MKT_excess'])
    if len(gg) < MIN_OBS_TIMING:
        continue
    y = gg['excess_return'].values.astype(float)
    mkt = gg['MKT_excess'].values.astype(float)
    X = np.column_stack([np.ones(len(y)), mkt, np.maximum(mkt, 0.0)])
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    b2_map[fc] = float(beta[2])
    ntm += 1
print('b2可估基金数=%d' % ntm)
df['hm_b2'] = df['fund_code'].map(b2_map)

# ================= 表4-17 =================
print('\n== 表4-17 择时控制 ==')
gall = df.groupby('fund_code').agg(
    de=('de_w', 'mean'), lsv=('lsv_w', 'mean'), risk_asym=('risk_asym_w', 'mean'),
    ff5=('ff5_clean', 'first'), hm_b2=('hm_b2', 'first'),
    aum=('avg_aum_w', 'mean')).reset_index()
gall['log_aum'] = np.log(gall['aum'].clip(lower=1e-9))
need = L5 + ['ff5', 'log_aum', 'hm_b2']
sub17 = gall.dropna(subset=need).reset_index(drop=True)
t417 = {}
m = smf.ols('ff5 ~ risk_asym + lsv + de + log_aum', data=sub17).fit(cov_type='HC1')
t417['no_timing'] = dict(N=int(m.nobs), r2=round(float(m.rsquared), 4),
                         coef=pack(m, ['risk_asym', 'lsv', 'de']))
print('不控制择时 N=%d R2=%.4f' % (m.nobs, m.rsquared),
      {k: (v['b'], v['t'], v['stars']) for k, v in t417['no_timing']['coef'].items()})
m = smf.ols('ff5 ~ risk_asym + lsv + de + log_aum + hm_b2', data=sub17).fit(cov_type='HC1')
t417['with_timing'] = dict(N=int(m.nobs), r2=round(float(m.rsquared), 4),
                           coef=pack(m, ['risk_asym', 'lsv', 'de', 'hm_b2']))
print('控制HM择时 N=%d R2=%.4f' % (m.nobs, m.rsquared),
      {k: (v['b'], v['t'], v['stars']) for k, v in t417['with_timing']['coef'].items()})

# 择时×RA 相关（基金层面，供正文引用）
cc = sub17[['risk_asym', 'hm_b2', 'log_aum']].corr().values
r_ra_tm = float(cc[0, 1])
from scipy import stats as _st
n17 = len(sub17)
t_corr = r_ra_tm * np.sqrt((n17 - 2) / (1 - r_ra_tm ** 2))
p_corr = float(2 * (1 - _st.t.cdf(abs(t_corr), n17 - 2)))
r2_ra_on_tm = r_ra_tm ** 2
# 择时+规模 合计解释RA方差
Xp = np.column_stack([np.ones(n17), sub17['hm_b2'].values, sub17['log_aum'].values])
yp = sub17['risk_asym'].values
bp, *_ = np.linalg.lstsq(Xp, yp, rcond=None)
resid = yp - Xp @ bp
r2_joint = float(1 - resid @ resid / ((yp - yp.mean()) ** 2).sum())
t417['diag'] = dict(corr_ra_b2=round(r_ra_tm, 3), corr_t=round(float(t_corr), 2),
                    corr_p=round(p_corr, 4), r2_b2=round(r2_ra_on_tm, 3),
                    r2_b2_plus_aum=round(r2_joint, 3), n=n17)
print('corr(RA,b2)=%.3f t=%.2f p=%.4f | R2(b2)=%.3f R2(+aum)=%.3f'
      % (r_ra_tm, t_corr, p_corr, r2_ra_on_tm, r2_joint))

# ================= 构念纯化 =================
print('\n== 构念纯化 ==')
pur = df.dropna(subset=['risk_asym_w', 'hm_b2', 'log_aum']).reset_index(drop=True)
Xp = np.column_stack([np.ones(len(pur)), pur['hm_b2'].values, pur['log_aum'].values])
yp = pur['risk_asym_w'].values
bp, *_ = np.linalg.lstsq(Xp, yp, rcond=None)
pur['ra_pur'] = yp - Xp @ bp

R = {'table417': t417}

# 纯化-截面
gp = pur.groupby('fund_code').agg(
    ra_pur=('ra_pur', 'mean'), de=('de_w', 'mean'), lsv=('lsv_w', 'mean'),
    ff5=('ff5_clean', 'first'), aum=('avg_aum_w', 'mean')).reset_index()
gp['log_aum'] = np.log(gp['aum'].clip(lower=1e-9))
subp = gp.dropna(subset=['ra_pur', 'de', 'lsv', 'ff5', 'log_aum'])
m = smf.ols('ff5 ~ ra_pur + lsv + de + log_aum', data=subp).fit(cov_type='HC1')
R['purify_cs'] = dict(N=int(m.nobs), r2=round(float(m.rsquared), 4), coef=pack(m, ['ra_pur']))
print('截面 N=%d R2=%.4f' % (m.nobs, m.rsquared), R['purify_cs']['coef'])

# 前向构造（镜像主脚本）
from collections import defaultdict
tidx = (pur['year'] * 4 + pur['quarter']).astype(int)
fut4 = np.full(len(pur), np.nan)
fut1 = np.full(len(pur), np.nan)
ex_raw = pur['excess_return'].values
byf = defaultdict(dict)
for i, fc in enumerate(pur['fund_code'].values):
    byf[fc][int(tidx.values[i])] = i
for fc, mp in byf.items():
    for t, i in mp.items():
        j = mp.get(t + 1)
        if j is not None:
            fut1[i] = ex_raw[j]
        ps = [mp.get(t + k) for k in (1, 2, 3, 4)]
        if all(p is not None for p in ps):
            fut4[i] = float(np.mean([ex_raw[p] for p in ps]))
pur['fut4q'] = fut4
pur['fut1q'] = fut1
for c in ['fut4q', 'fut1q']:
    pur[c + '_w'] = winsor(pur[c])

for dv in ['fut4q', 'fut1q']:
    sub = pur.dropna(subset=['ra_pur', 'lsv_w', 'de_w', dv + '_w', 'log_aum', 'log_fund_age'])
    fml = dv + '_w ~ ra_pur + lsv + lsv_w + de + de_w'.replace('lsv + lsv_w', 'lsv_w') \
        if False else dv + '_w ~ ra_pur + lsv_w + de_w + log_aum + log_fund_age + C(year)'
    m = smf.ols(fml, data=sub).fit(cov_type='cluster',
                                   cov_kwds={'groups': sub['fund_code'].values})
    R['purify_' + dv] = dict(N=int(m.nobs), coef=pack(m, ['ra_pur']))
    print(dv, 'N=%d' % m.nobs, R['purify_' + dv]['coef'])

# 纯化-组内
sub = pur.dropna(subset=['ra_pur', 'lsv_w', 'de_w', 'excess_return_w'])
m = smf.ols('excess_return_w ~ de_w + lsv_w + ra_pur + C(fund_code) + C(year)', data=sub)\
    .fit(cov_type='cluster', cov_kwds={'groups': sub['fund_code'].values})
ssr = float(m.resid @ m.resid)
wmean = sub.groupby('fund_code')['excess_return_w'].transform('mean')
tss_w = float(((sub['excess_return_w'] - wmean) ** 2).sum())
R['purify_within'] = dict(N=int(m.nobs), r2_within=round(1 - ssr / tss_w, 4),
                          coef=pack(m, ['ra_pur']))
print('组内 N=%d r2w=%.4f' % (m.nobs, 1 - ssr / tss_w), R['purify_within']['coef'])

R['meta'] = dict(date='2026-08-23', bad_quarters=[[y, q] for y, q in BAD_Q],
                 min_obs_timing=MIN_OBS_TIMING,
                 note='镜像 core_regs_recalc_clean 口径；b2于干净序列估计；'
                      '纯化=面板行级risk_asym_w对(b2,log_aum)正交化残差')

with open(OUT_JSON, 'w', encoding='utf-8') as f:
    json.dump(R, f, ensure_ascii=False, indent=1)
print('\nsaved', OUT_JSON)
