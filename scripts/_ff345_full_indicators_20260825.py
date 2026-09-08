# -*- coding: utf-8 -*-
"""全量L1-L5指标 × FF3/FF4/FF5三口径 alpha 回归对比（2026-08-25）。

因变量：每只基金的时序回归截距 alpha
  - ff3 = excess_return ~ 1 + MKT_excess + SMB + HML
  - ff4 = excess_return ~ 1 + MKT_excess + SMB + HML + MOM
  - ff5 = excess_return ~ 1 + ff5_MKT_excess + ff5_SMB + ff5_HML + ff5_RMW + ff5_CMA
自变量：L1-L5 全部指标 + log_aum 控制（基金层聚合均值，HC1 稳健SE）
口径对齐：
  - 污染季剔除 (2025,3)/(2026,2)/(2026,3)
  - risk_asym 在干净季收益序列上重算（滚动8季，min_periods=4）
  - 全指标 1%/99% 缩尾
  - 与 ff34_alpha_clean / batch2 的变量命名一致
输出：output/ff345_full_indicators_2026-08-25.json
"""
import json
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

PANEL = '指标计算流水线/output/主分析面板_重建_含TOwind.csv'
QRET = '指标计算流水线/data/L4_风险应对层/基金季度收益.csv'
OUT = 'output/ff345_full_indicators_2026-08-25.json'
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

# ---- risk_asym 干净重算（镜像 06/lib：滚动8季窗口，min_periods=4）----
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

# ---- 三口径 alpha（时序回归截距，min obs = 因子数+5）----
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
        if len(y) < X.shape[1] + 5:
            continue
        A = np.column_stack([np.ones(len(y)), X])
        beta, *_ = np.linalg.lstsq(A, y, rcond=None)
        amap[fc] = float(beta[0])
    alpha_maps[nm] = amap
    print(nm, 'alpha可估基金数=%d' % len(amap))
for nm in alpha_maps:
    df[nm + '_a'] = df['fund_code'].map(alpha_maps[nm])

# ---- 缩尾（全指标 1%/99%）----
for c in ALL:
    df[c + '_w'] = winsor(df[c])

# ---- 基金层聚合（均值，口径同 ff34/batch2 参照）----
agg = {c + '_w': 'mean' for c in ALL}
g = df.groupby('fund_code').agg(**{k: (k, 'first') for k in ['ff3_a', 'ff4_a', 'ff5_a']},
                                **{k: (k, 'mean') for k in list(agg)}).reset_index()

out = {}
for dv in ['ff3_a', 'ff4_a', 'ff5_a']:
    rhs = [c + '_w' for c in L1 + L2 + L3 + L4 + L5 + [CTRL]]
    sub = g.dropna(subset=[dv] + rhs)
    # 防御性剔除零方差列（NAV 子样本 SDI 为结构零）
    keep = [c for c in rhs if sub[c].std() > 1e-12]
    dropped = [c for c in rhs if c not in keep]
    fml = '%s ~ %s' % (dv, ' + '.join(keep))
    m = smf.ols(fml, data=sub).fit(cov_type='HC1')
    base = {k[:-2] if k.endswith('_w') else k: v for k, v in pack(m, keep).items()}
    out[dv] = dict(N=int(m.nobs), r2=round(float(m.rsquared), 4),
                   alpha_mean=round(float(sub[dv].mean()), 4),
                   dropped_cols=dropped, coef=base)
    print(dv, 'N=%d R2=%.4f dropped=%s' % (m.nobs, m.rsquared, dropped))
    for k, v in base.items():
        print('   %-22s b=%+.5f t=%+.2f %s' % (k, v['b'], v['t'], v['stars']))

with open(OUT, 'w', encoding='utf-8') as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
print('saved', OUT)