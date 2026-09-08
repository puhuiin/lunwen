# -*- coding: utf-8 -*-
"""核心识别三表·干净版权威重算（污染季剔除 + 受污染派生指标重估）。

背景：数据法证（_diag_*系列）确认 基金净值历史_全量.csv 在 2025Q3 与 2026Q2
两个季度存在全市场同步的异常收益（86-87%基金|季收益|>30%，季度中位数+48%/+82%，
日度结构呈"全员匀速暴涨"，非真实行情，疑似数据源复权/拼接缺陷）；2026Q3为残缺季。
后果链：① risk_asym=滚动8季σ(盈利)-σ(亏损)，窗口末端触及污染季→2025Q3~2026Q2
截面RA被机械抬升至~0.15-0.25（正常~0.00）；② 表4-6中2025Q2行的fut1恰为+50%的
2025Q3→制造RA×fut1假负相关(t=-22.86)；③ ff5_adj_return时序回归样本含污染季。

处理：
  - 全部三表剔除 (year,quarter) ∈ {(2025,3),(2026,2),(2026,3)}
  - risk_asym 就地重算：镜像 lib_metrics.calc_risk_asym 口径（window=8,min_periods=4,
    按行位置滚动），但在剔除污染季后的干净季收益序列上计算
  - ff5_adj_return 就地重算：镜像 06_因变量._alpha_by_fund/_ts_alpha 口径
    （FF5五因子时序回归截距，有效观测>=因子数+5），在干净面板上估计
  - 其余口径与 _recalc_core_tables.py 完全一致（缩尾/log_aum/SE/bootstrap）
输出：output/core_regs_recalc_clean_2026-08-23.json
"""
import json
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from collections import defaultdict

PANEL = '指标计算流水线/output/主分析面板_重建_含TOwind.csv'
QRET = '指标计算流水线/data/L4_风险应对层/基金季度收益.csv'
OUT_JSON = 'output/core_regs_recalc_clean_2026-08-23.json'
SEED_B1 = 20260823
SEED_B2 = 20260824
B_FUND = 2000
B_2STAGE = 1000
BAD_Q = [(2025, 3), (2026, 2), (2026, 3)]

L5 = ['de', 'lsv', 'risk_asym']


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

# ---- 污染季剔除 ----
n0 = len(df)
bad = df.set_index(['year', 'quarter']).index.isin(BAD_Q)
df = df[~bad].sort_values(['fund_code', 'year', 'quarter']).reset_index(drop=True)
print('剔除污染季 %s：%d -> %d 行' % (BAD_Q, n0, len(df)))

# ---- risk_asym 干净重算（镜像 lib_metrics.calc_risk_asym）----
print('recompute risk_asym on clean quarterly series ...')
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
rdf = pd.DataFrame(
    [(fc, y, q, v) for (fc, y, q), v in ra_map.items()],
    columns=['fund_code', 'year', 'quarter', 'ra_clean'])
df = df.merge(rdf, on=['fund_code', 'year', 'quarter'], how='left')
df['risk_asym'] = df['ra_clean']
df = df.drop(columns=['ra_clean'])
cov_new = df['risk_asym'].notna().mean()
print('新RA覆盖=%.3f' % cov_new)

# ---- ff5_adj_return 干净重算（镜像 06_因变量._alpha_by_fund）----
print('recompute ff5_adj_return on clean sample ...')
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
WCOLS = ['excess_return', 'avg_aum']
wbounds = {}
for c in WCOLS:
    x = df[c].dropna()
    lo, hi = float(x.quantile(.01)), float(x.quantile(.99))
    wbounds[c] = [round(lo, 6), round(hi, 6)]
    df[c + '_w'] = df[c].clip(lo, hi)
for c in L5:
    df[c + '_w'] = winsor(df[c])
df['log_aum'] = np.log(df['avg_aum'].clip(lower=1e-9))

R = {'meta': dict(panel=PANEL, date='2026-08-23',
                  excluded_quarters=[[y, q] for y, q in BAD_Q],
                  exclude_reason='2025Q3/2026Q2净值数据源异常(全市场同步暴涨,86%+基金|收益|>30%),'
                                 '2026Q3残缺季;n_days与MAD扫描见_diag_tail_ndays/_diag_nav_jump_scan',
                  derived_recomputed=['risk_asym(滚动8季窗口于干净序列)',
                                      'ff5_adj_return(FF5时序alpha于干净样本)'],
                  winsor='1%/99% 清洁面板分位数',
                  winsor_bounds=wbounds,
                  log_aum='ln(avg_aum.clip(1e-9))',
                  seed_bootstrap=[SEED_B1, SEED_B2])}
print('clean rows=%d funds=%d span=%dQ%d-%dQ%d' % (
    len(df), df.fund_code.nunique(), df.year.min(), df.quarter.min(),
    df.year.max(), df.quarter.max()))

# ================= 表4-5 截面基准 =================
print('\n== 表4-5 截面基准 ==')
g = df.groupby('fund_code').agg(
    de=('de_w', 'mean'), lsv=('lsv_w', 'mean'), risk_asym=('risk_asym_w', 'mean'),
    ex=('excess_return_w', 'mean'), ff5=('ff5_clean', 'first'),
    aum=('avg_aum_w', 'mean')).reset_index()
g['log_aum'] = np.log(g['aum'].clip(lower=1e-9))
t45 = {}
for dv in ['ff5', 'ex']:
    for ctl in [True, False]:
        fml = dv + ' ~ risk_asym + lsv + de' + (' + log_aum' if ctl else '')
        sub = g.dropna(subset=(L5 + [dv, 'log_aum']) if ctl else (L5 + [dv]))
        m = smf.ols(fml, data=sub).fit(cov_type='HC1')
        key = ('with_aum' if ctl else 'no_aum') + '_' + dv
        t45[key] = dict(N=int(m.nobs), r2=round(float(m.rsquared), 4),
                        coef=pack(m, ['risk_asym', 'lsv', 'de'] + (['log_aum'] if ctl else [])))
        print(key, 'N=%d R2=%.4f' % (m.nobs, m.rsquared),
              {k: (v['b'], v['t'], v['stars']) for k, v in t45[key]['coef'].items()})
R['table45'] = t45

# --- 脚注① 基金层bootstrap ---
head = g.dropna(subset=L5 + ['ff5', 'log_aum']).reset_index(drop=True)
Y = head['ff5'].values
Xh = np.column_stack([np.ones(len(head)), head[['risk_asym', 'lsv', 'de', 'log_aum']].values])
rng1 = np.random.default_rng(SEED_B1)
nf = len(head)
ts = {k: [] for k in ['risk_asym', 'lsv', 'de']}
for _ in range(B_FUND):
    idx = rng1.integers(0, nf, nf)
    Xb, yb = Xh[idx], Y[idx]
    beta, *_ = np.linalg.lstsq(Xb, yb, rcond=None)
    res = yb - Xb @ beta
    dof = nf - Xb.shape[1]
    sigma2 = float(res @ res) / dof
    se = np.sqrt(np.diag(np.linalg.inv(Xb.T @ Xb)) * sigma2 * nf / dof)
    tv = beta / se
    for j, k in zip([1, 2, 3], ts):
        ts[k].append(abs(float(tv[j])))
boot = {}
for k, arr in ts.items():
    arr = np.array(arr)
    boot[k] = dict(mean_abs_t=round(float(arr.mean()), 2),
                   share_gt_196=round(float((arr > 1.96).mean()), 3),
                   share_gt_258=round(float((arr > 2.58).mean()), 3))
print('bootstrap:', boot)
R['table45_bootstrap'] = dict(B=B_FUND, seed=SEED_B1, spec='with_aum+ff5', **boot)

# --- 脚注② 两阶段bootstrap ---
stage_rows = {}
for fc, gg in df.groupby('fund_code'):
    gg = gg.dropna(subset=['excess_return'] + fac)
    if len(gg) >= 12:
        stage_rows[fc] = (gg['excess_return'].values.astype(float),
                          np.column_stack([np.ones(len(gg)), gg[fac].values.astype(float)]))
funds2 = [fc for fc in head['fund_code'] if fc in stage_rows]
h2 = head.set_index('fund_code').loc[funds2].reset_index()
lo5, hi5 = float(np.nanquantile(df['ff5_clean'].dropna(), .01)), \
    float(np.nanquantile(df['ff5_clean'].dropna(), .99))
rng2 = np.random.default_rng(SEED_B2)
n2 = len(h2)
A2 = h2[['risk_asym', 'lsv', 'de']].values
AU = h2['log_aum'].values
ts2 = {k: [] for k in ['risk_asym', 'lsv', 'de']}
for _ in range(B_2STAGE):
    alphas = np.empty(n2)
    for i, fc in enumerate(funds2):
        y, Xm = stage_rows[fc]
        idx = rng2.integers(0, len(y), len(y))
        alphas[i] = np.linalg.lstsq(Xm[idx], y[idx], rcond=None)[0][0]
    alphas = np.clip(alphas, lo5, hi5)
    idx = rng2.integers(0, n2, n2)
    Xb = np.column_stack([np.ones(n2), A2[idx], AU[idx]])
    beta, *_ = np.linalg.lstsq(Xb, alphas[idx], rcond=None)
    res = alphas[idx] - Xb @ beta
    dof = n2 - Xb.shape[1]
    se = np.sqrt(np.diag(np.linalg.inv(Xb.T @ Xb)) * float(res @ res) / dof * n2 / dof)
    tv = beta / se
    for j, k in zip([1, 2, 3], ts2):
        ts2[k].append(float(tv[j]))
two = {}
for k in ts2:
    a1 = np.array(ts2[k])
    two[k] = dict(median_t=round(float(np.median(a1)), 2),
                  mean_abs_t=round(float(np.mean(np.abs(a1))), 2),
                  share_pos=round(float((a1 > 0).mean()), 3))
print('two-stage:', two)
R['table45_twostage'] = dict(B=B_2STAGE, seed=SEED_B2, spec='with_aum+ff5',
                             note='阶段1基金内重抽季度行重估FF5 alpha并clip回清洁缩尾边界；阶段2抽基金重估截面(HC1)',
                             **two)

# ================= 表4-6 前向预测 =================
print('\n== 表4-6 前向预测 ==')
tidx = (df['year'] * 4 + df['quarter']).astype(int)
assert not df.duplicated(['fund_code', 'year', 'quarter']).any()
fut4 = np.full(len(df), np.nan)
fut1 = np.full(len(df), np.nan)
ex_raw = df['excess_return'].values
byf = defaultdict(dict)
for i, fc in enumerate(df['fund_code'].values):
    byf[fc][int(tidx.values[i])] = i
for fc, mp in byf.items():
    for t, i in mp.items():
        j = mp.get(t + 1)
        if j is not None:
            fut1[i] = ex_raw[j]
        ps = [mp.get(t + k) for k in (1, 2, 3, 4)]
        if all(p is not None for p in ps):
            fut4[i] = float(np.mean([ex_raw[p] for p in ps]))
df['fut4q'] = fut4
df['fut1q'] = fut1
for c in ['fut4q', 'fut1q']:
    df[c + '_w'] = winsor(df[c])
t46 = {}
for dv in ['fut4q', 'fut1q']:
    sub = df.dropna(subset=L5 + [dv + '_w', 'log_aum', 'log_fund_age'])
    fml = dv + '_w ~ risk_asym + lsv + de + log_aum + log_fund_age + C(year)'
    m = smf.ols(fml, data=sub).fit(cov_type='cluster',
                                   cov_kwds={'groups': sub['fund_code'].values})
    t46[dv] = dict(N=int(m.nobs), n_funds=int(sub.fund_code.nunique()),
                   r2=round(float(m.rsquared), 4),
                   coef=pack(m, ['risk_asym', 'lsv', 'de']))
    print(dv, 'N=%d funds=%d R2=%.4f' % (m.nobs, sub.fund_code.nunique(), m.rsquared),
          {k: (v['b'], v['t'], v['stars']) for k, v in t46[dv]['coef'].items()})
grid = {}
for dv in ['fut4q', 'fut1q']:
    for wz in ['', '_w']:
        sub = df.dropna(subset=L5 + [dv + wz, 'log_aum', 'log_fund_age'])
        for fe in [True, False]:
            fml = dv + wz + ' ~ risk_asym + lsv + de + log_aum + log_fund_age'
            fml += ' + C(year)' if fe else ''
            m = smf.ols(fml, data=sub).fit(cov_type='cluster',
                                           cov_kwds={'groups': sub['fund_code'].values})
            grid['%s%s_%s' % (dv, wz, 'yrFE' if fe else 'noFE')] = dict(
                N=int(m.nobs), ra=dict(b=round(float(m.params['risk_asym']), 4),
                                       t=round(float(m.tvalues['risk_asym']), 2)),
                de=dict(b=round(float(m.params['de']), 4), t=round(float(m.tvalues['de']), 2)))
            print('grid', dv + wz, 'yrFE' if fe else 'noFE', 'RA', grid[list(grid)[-1]]['ra'])
R['table46'] = t46
R['table46_grid'] = grid

# ================= 表4-7 组内双向FE =================
print('\n== 表4-7 组内双向FE ==')
sub = df.dropna(subset=L5 + ['excess_return_w'])
m = smf.ols('excess_return_w ~ de + lsv + risk_asym + C(fund_code) + C(year)', data=sub)\
    .fit(cov_type='cluster', cov_kwds={'groups': sub['fund_code'].values})
ssr = float(m.resid @ m.resid)
wmean = sub.groupby('fund_code')['excess_return_w'].transform('mean')
tss_w = float(((sub['excess_return_w'] - wmean) ** 2).sum())
t47 = dict(N=int(m.nobs), n_funds=int(sub.fund_code.nunique()),
           r2_within=round(1 - ssr / tss_w, 4),
           coef=pack(m, ['de', 'lsv', 'risk_asym']))
print('twFE N=%d funds=%d r2w=%.4f' % (m.nobs, sub.fund_code.nunique(), t47['r2_within']),
      {k: (v['b'], v['t'], v['stars']) for k, v in t47['coef'].items()})
R['table47'] = t47

with open(OUT_JSON, 'w', encoding='utf-8') as f:
    json.dump(R, f, ensure_ascii=False, indent=1)
print('\nsaved', OUT_JSON)
