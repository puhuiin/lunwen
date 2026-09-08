# -*- coding: utf-8 -*-
"""逐指标单回归对比：DV=FF3_alpha 或 FF5_alpha；RHS=任一L1-L5行为变量 + log_aum控制。

每一个行为指标单独入模（不与其它指标竞争），观察其"纯边际效应"。
口径：
  - 污染季剔除{(2025,3),(2026,2),(2026,3)}
  - risk_asym 于干净季滚动8季重算
  - 行为指标与log_aum 1%/99%缩尾后基金层均值聚合
  - 截面OLS，HC1稳健标准误
输出: output/one_by_one_reg_2026-08-25.json
"""
import json
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

PANEL = '指标计算流水线/output/主分析面板_重建_含TOwind.csv'
QRET = '指标计算流水线/data/L4_风险应对层/基金季度收益.csv'
OUT = 'output/one_by_one_reg_2026-08-25.json'
BAD_Q = [(2025, 3), (2026, 2), (2026, 3)]

# 所有要单跑的行为指标（逐个入模）
INDICATORS = {
    # L1 基本面
    'mgr_total_tenure_v2': 'L1 从业年限',
    'log_fund_age':       'L1 基金年龄(ln)',
    # L2 选择
    'AS_improved':        'L2 改进主动份额AS',
    'ICI':                'L2 行业集中度ICI',
    'industry_hhi':       'L2 行业分散度HHI',
    # L3 交易执行
    'SDI':                'L3 风格漂移指数SDI',
    'TO_wind':            'L3 换手率TO',
    'ARG':                'L3 调仓收益ARG',
    # L4 风控
    'return_volatility':  'L4 收益波动率RV',
    # L5 认知
    'de':                 'L5 处置效应DE',
    'lsv':                'L5 羊群效应LSV',
    'risk_asym':          'L5 风险不对称RA',
}
CTRL = 'log_aum'


def winsor(s, lo=0.01, hi=0.99):
    x = s.dropna()
    return s.clip(x.quantile(lo), x.quantile(hi))


def pack_simple(m):
    stars = lambda p: '***' if p < .01 else '**' if p < .05 else '*' if p < .1 else ''
    out = {}
    for k in m.params.index:
        if k == 'Intercept':
            continue
        out[k] = dict(b=round(float(m.params[k]), 4),
                      t=round(float(m.tvalues[k]), 2),
                      p=round(float(m.pvalues[k]), 4),
                      stars=stars(m.pvalues[k]))
    return out


print('load', PANEL)
df = pd.read_csv(PANEL)
df['fund_code'] = df['fund_code'].astype(str)
bad = df.set_index(['year', 'quarter']).index.isin(BAD_Q)
df = df[~bad].sort_values(['fund_code', 'year', 'quarter']).reset_index(drop=True)
df['log_aum'] = np.log(df['avg_aum'].clip(lower=1e-9))

# ---- risk_asym 干净重算（滚动8季，min_periods=4）----
print('recompute risk_asym on clean series ...')
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
        if len(seg) < MINP: continue
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
df['risk_asym'] = df['ra_clean']; df = df.drop(columns=['ra_clean'])

# ---- 三口径 alpha（时序回归截距）----
FACS = {
    'ff3': ['MKT_excess', 'SMB', 'HML'],
    'ff5': ['ff5_MKT_excess', 'ff5_SMB', 'ff5_HML', 'ff5_RMW', 'ff5_CMA'],
}
alpha_maps = {}
for nm, fac in FACS.items():
    amap = {}
    for fc, g in df.groupby('fund_code'):
        gg = g.dropna(subset=['excess_return'] + fac)
        y = gg['excess_return'].values.astype(float)
        X = gg[fac].values.astype(float)
        if len(y) < X.shape[1] + 5: continue
        A = np.column_stack([np.ones(len(y)), X])
        beta, *_ = np.linalg.lstsq(A, y, rcond=None)
        amap[fc] = float(beta[0])
    alpha_maps[nm] = amap
    print(nm, 'alpha可估基金数=%d' % len(amap))
for nm in alpha_maps: df[nm + '_a'] = df['fund_code'].map(alpha_maps[nm])

# ---- 缩尾（行为指标与控制）----
for c in list(INDICATORS.keys()) + [CTRL]:
    df[c + '_w'] = winsor(df[c])

# ---- 基金层聚合：行为均值 / alpha 取first(基金级常数) ----
agg_d = {c + '_w': 'mean' for c in INDICATORS}
agg_d[CTRL + '_w'] = 'mean'
g = df.groupby('fund_code').agg(
    ff3_a=('ff3_a', 'first'),
    ff5_a=('ff5_a', 'first'),
    **{k: (k, 'mean') for k in agg_d}
).reset_index()
print('基金层聚合后 N_funds=%d' % len(g))

# ---- 逐指标单回归 ----
out = {}
for dv_key, dv_name in [('ff3_a', 'FF3_alpha'), ('ff5_a', 'FF5_alpha')]:
    out[dv_key] = {}
    print('\n=== DV = %s ===' % dv_name)
    for col, label in INDICATORS.items():
        rhs = [col + '_w', CTRL + '_w']
        sub = g.dropna(subset=[dv_key] + rhs)
        # 防御性：若某指标在子样本内方差为0（如SDI结构零），跳过
        if sub[rhs].std().min() < 1e-12:
            print('   %-22s  [SKIP 零方差]' % label)
            continue
        fml = '%s ~ %s + %s' % (dv_key, col + '_w', CTRL + '_w')
        m = smf.ols(fml, data=sub).fit(cov_type='HC1')
        res = pack_simple(m)
        # 仅保留下标行为指标的条目，log_aum作为控制保留
        out[dv_key][col] = dict(label=label, N=int(m.nobs),
                                r2=round(float(m.rsquared), 4),
                                dv=res.get(col + '_w'),
                                ctrl_log_aum=res.get(CTRL + '_w'))
        d = out[dv_key][col]['dv']
        if d:
            print('   %-22s  N=%d  R²=%.4f  β=%+.5f  t=%+.2f %s' % (
                label, out[dv_key][col]['N'], out[dv_key][col]['r2'],
                d['b'], d['t'], d['stars']))
        else:
            print('   %-22s  [无法解析系数]' % label)

with open(OUT, 'w', encoding='utf-8') as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
print('\nsaved', OUT)

# ---- 终端简表输出（对齐中文表格）----
print('\n===== 简表（β / t / 显著性）=====')
print('指标                           | FF3 alpha           | FF5 alpha')
print('-' * 84)
for col, label in INDICATORS.items():
    row = []
    for dv in ['ff3_a', 'ff5_a']:
        b = out[dv].get(col)
        if not b or not b['dv']:
            row.append('  --- ')
            continue
        d = b['dv']
        row.append('%+.4f / %+.2f %-3s' % (d['b'], d['t'], d['stars']))
    print('%-28s | %-19s | %s' % (label, row[0], row[1]))
