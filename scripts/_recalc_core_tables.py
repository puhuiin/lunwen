# -*- coding: utf-8 -*-
"""核心识别三表（表4-5截面/表4-6前向/表4-7组内）权威重算并落盘。

背景：三张表的旧数值出自v23旧面板时代（表4-7旧值可追溯至 数据/L4_风险应对层/
最终结果_v23_识别修正.json，其时全样本303只基金；表4-5/4-6无任何持久化出处）。
面板重建为381只/9554行后未同步。本脚本按稿件声明口径从现行权威面板重算。

口径（与M4权威管线一致，见 _batch2_regress_v2_20260822.py 等）：
  - 1%/99% 全面板分位数缩尾（L5指标、各因变量、avg_aum），边界取自全面板dropna分位
  - log_aum = ln(avg_aum.clip(lower=1e-9))
  - 表4-5：基金层时间均值折叠，HC1稳健SE；四规格（{ff5,ex}×{含,不含log_aum}）
  - 表4-6：DV=fut4q/fut1q（由excess_return严格构造：t+1..t+k全部季度均在样本内），
           控制log_aum/log_fund_age+C(year)，基金层面聚类SE；另附敏感性小网格
  - 表4-7：DV=当期excess_return，C(fund_code)+C(year)双向FE，基金聚类SE；
           组内R² = 1 − SSR/TSS_within（TSS按基金均值中心化，FWL精确等价）
  - 表4-5脚注①：基金层有放回bootstrap B=2000（seed 20260823），HC1
  - 表4-5脚注②：两阶段bootstrap B=1000（seed 20260824）：先按基金内重抽季度行
           重估FF5 alpha（clip回原缩尾边界），再抽基金重估截面回归
输出：output/core_regs_recalc_2026-08-23.json
"""
import json
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from collections import defaultdict

PANEL = '指标计算流水线/output/主分析面板_重建_含TOwind.csv'
OUT_JSON = 'output/core_regs_recalc_2026-08-23.json'
SEED_B1 = 20260823
SEED_B2 = 20260824
B_FUND = 2000
B_2STAGE = 1000

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
df = df.sort_values(['fund_code', 'year', 'quarter']).reset_index(drop=True)

WCOLS = L5 + ['excess_return', 'ff5_adj_return', 'future_return', 'avg_aum']
wbounds = {}
for c in WCOLS:
    x = df[c].dropna()
    lo, hi = float(x.quantile(.01)), float(x.quantile(.99))
    wbounds[c] = [round(lo, 6), round(hi, 6)]
    df[c + '_w'] = df[c].clip(lo, hi)
df['log_aum'] = np.log(df['avg_aum'].clip(lower=1e-9))
R = {'meta': dict(panel=PANEL, date='2026-08-23', winsor='1%/99% 全面板',
                  winsor_bounds={k: v for k, v in wbounds.items()},
                  log_aum='ln(avg_aum.clip(1e-9))',
                  seed_bootstrap=[SEED_B1, SEED_B2])}
print('rows=%d funds=%d span=%dQ%d-%dQ%d' % (
    len(df), df.fund_code.nunique(), df.year.min(), df.quarter.min(),
    df.year.max(), df.quarter.max()))

# ================= 表4-5 截面基准 =================
print('\n== 表4-5 截面基准 ==')
g = df.groupby('fund_code').agg(
    de=('de_w', 'mean'), lsv=('lsv_w', 'mean'), risk_asym=('risk_asym_w', 'mean'),
    ex=('excess_return_w', 'mean'), ff5=('ff5_adj_return_w', 'first'),
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

# --- 脚注① 基金层bootstrap（headline: with_aum + ff5）---
head = g.dropna(subset=L5 + ['ff5', 'log_aum']).reset_index(drop=True)
Y = head['ff5'].values
Xh = np.column_stack([np.ones(len(head)), head[['risk_asym', 'lsv', 'de', 'log_aum']].values])
names = ['const', 'risk_asym', 'lsv', 'de', 'log_aum']
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
    XtXi = np.linalg.inv(Xb.T @ Xb)
    se = np.sqrt(np.diag(XtXi) * sigma2 * nf / dof)          # HC0近似（重抽样内同方差合理）
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
fac = ['ff5_MKT_excess', 'ff5_SMB', 'ff5_HML', 'ff5_RMW', 'ff5_CMA']
stage_rows = {}
for fc, gg in df.groupby('fund_code'):
    gg = gg.dropna(subset=['excess_return'] + fac)
    if len(gg) >= 12:
        stage_rows[fc] = (gg['excess_return'].values.astype(float),
                          np.column_stack([np.ones(len(gg)), gg[fac].values.astype(float)]))
funds2 = [fc for fc in head['fund_code'] if fc in stage_rows]
h2 = head.set_index('fund_code').loc[funds2].reset_index()
lo5, hi5 = wbounds['ff5_adj_return']
rng2 = np.random.default_rng(SEED_B2)
n2 = len(h2)
A2 = h2[['risk_asym', 'lsv', 'de']].values
AU = h2['log_aum'].values
sizes = {fc: stage_rows[fc][0].shape[0] for fc in funds2}
maxn = max(sizes.values())
alpha_hat = np.array([np.linalg.lstsq(stage_rows[fc][1], stage_rows[fc][0], rcond=None)[0][0]
                      for fc in funds2])
ts2 = {k: [] for k in ['risk_asym', 'lsv', 'de']}
meds = {k: [] for k in ['risk_asym', 'lsv', 'de']}
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
        meds[k].append(abs(float(tv[j])))
two = {}
for k in ts2:
    a1 = np.array(ts2[k])
    two[k] = dict(median_t=round(float(np.median(a1)), 2),
                  mean_abs_t=round(float(np.mean(np.abs(a1))), 2),
                  share_pos=round(float((a1 > 0).mean()), 3))
print('two-stage:', two)
R['table45_twostage'] = dict(B=B_2STAGE, seed=SEED_B2, spec='with_aum+ff5',
                             note='阶段1基金内重抽季度行重估FF5 alpha并clip回缩尾边界；阶段2抽基金重估截面(HC1)',
                             **two)

# ================= 表4-6 前向预测 =================
print('\n== 表4-6 前向预测 ==')
tidx = (df['year'] * 4 + df['quarter']).astype(int)
assert not df.duplicated(['fund_code', 'year', 'quarter']).any()
fut4 = np.full(len(df), np.nan)
fut1 = np.full(len(df), np.nan)
ex_raw = df['excess_return'].values
byf = defaultdict(dict)
tf_pos = tidx.values
for i, fc in enumerate(df['fund_code'].values):
    byf[fc][int(tf_pos[i])] = i
miss1 = miss4 = 0
for fc, mp in byf.items():
    for t, i in mp.items():
        j = mp.get(t + 1)
        if j is not None:
            fut1[i] = ex_raw[j]
        else:
            miss1 += 1
        ps = [mp.get(t + k) for k in (1, 2, 3, 4)]
        if all(p is not None for p in ps):
            fut4[i] = float(np.mean([ex_raw[p] for p in ps]))
        else:
            miss4 += 1
df['fut4q'] = fut4
df['fut1q'] = fut1
for c in ['fut4q', 'fut1q']:
    df[c + '_w'] = winsor(df[c])
print('fut4q可用行=%d 缺后续季行=%d; fut1q缺次季行=%d' % (
    df.fut4q.notna().sum(), miss4, miss1))
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
# 敏感性小网格：原始(未缩尾)×有无年份FE，检验结论方向
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
