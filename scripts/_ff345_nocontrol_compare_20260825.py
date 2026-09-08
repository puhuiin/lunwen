# -*- coding: utf-8 -*-
"""FF3/FF4/FF5 × 有无L1控制 四规格对比（利用上一步脚本构建的g表直接用，省去重算alpha/RA）。
口径：全指标截面回归（10行为指标 + SDI/TO + RA/DE/LSV + 行业HHI）
- 规格有控制：L1 三控制 (tenure + log_fund_age + log_aum)
- 规格无控制：剔除 tenure / log_fund_age / log_aum 三个变量
输出 output/ff345_nocontrol_compare_2026-08-25.json
"""
import json, subprocess, sys, os
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

# 直接复用同一路径与构造逻辑（重走一遍alpha/RA重算以拿到干净的g）
PANEL = '指标计算流水线/output/主分析面板_重建_含TOwind.csv'
QRET = '指标计算流水线/data/L4_风险应对层/基金季度收益.csv'
OUT = 'output/ff345_nocontrol_compare_2026-08-25.json'
BAD_Q = [(2025, 3), (2026, 2), (2026, 3)]

L1 = ['mgr_total_tenure_v2', 'log_fund_age']
L2 = ['AS_improved', 'ICI', 'industry_hhi']
L3 = ['SDI', 'TO_wind', 'ARG']
L4 = ['return_volatility']
L5 = ['de', 'lsv', 'risk_asym']
CTRL = 'log_aum'
ALL = L1 + L2 + L3 + L4 + L5 + [CTRL]


def winsor(s, lo=0.01, hi=0.99):
    x = s.dropna()
    return s.clip(x.quantile(lo), x.quantile(hi))


def pack(m, keys):
    return {k: dict(b=round(float(m.params[k]), 4), t=round(float(m.tvalues[k]), 2),
                    p=round(float(m.pvalues[k]), 4),
                    stars=('***' if m.pvalues[k] < .01 else '**' if m.pvalues[k] < .05
                           else '*' if m.pvalues[k] < .1 else '')) for k in keys}


print('load', PANEL)
df = pd.read_csv(PANEL)
df['fund_code'] = df['fund_code'].astype(str)
bad = df.set_index(['year', 'quarter']).index.isin(BAD_Q)
df = df[~bad].sort_values(['fund_code', 'year', 'quarter']).reset_index(drop=True)
df['log_aum'] = np.log(df['avg_aum'].clip(lower=1e-9))

# risk_asym 干净重算
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

FACS = {
    'ff3': ['MKT_excess', 'SMB', 'HML'],
    'ff4': ['MKT_excess', 'SMB', 'HML', 'MOM'],
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
for c in ALL: df[c + '_w'] = winsor(df[c])

agg = {c + '_w': 'mean' for c in ALL}
g = df.groupby('fund_code').agg(**{k: (k, 'first') for k in ['ff3_a', 'ff4_a', 'ff5_a']},
                                **{k: (k, 'mean') for k in list(agg)}).reset_index()

BEH = L2 + L3 + L4 + L5  # 11个纯行为变量（不含L1/CTRL）
RHS_CTRL = [c + '_w' for c in L1 + [CTRL]]   # 3个控制变量
out = {}
for dv in ['ff3_a', 'ff4_a', 'ff5_a']:
    for mode, rhscols in [
        ('controlled', [c+'_w' for c in ALL]),
        ('no_control', [c+'_w' for c in BEH])]:
        sub = g.dropna(subset=[dv] + rhscols)
        keep = [c for c in rhscols if sub[c].std() > 1e-12]
        dropped = [c for c in rhscols if c not in keep]
        fml = '%s ~ %s' % (dv, ' + '.join(keep))
        m = smf.ols(fml, data=sub).fit(cov_type='HC1')
        base = {k[:-2] if k.endswith('_w') else k: v for k, v in pack(m, keep).items()}
        key = dv + '__' + mode
        out[key] = dict(N=int(m.nobs), r2=round(float(m.rsquared), 4),
                        alpha_mean=round(float(sub[dv].mean()), 4),
                        dropped_cols=dropped, coef=base)
        print('\n', key, 'N=%d R2=%.4f dropped=%s' % (m.nobs, m.rsquared, dropped))
        for k, v in base.items():
            print('   %-22s b=%+.5f t=%+.2f %s' % (k, v['b'], v['t'], v['stars']))

with open(OUT, 'w', encoding='utf-8') as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
print('\nsaved', OUT)