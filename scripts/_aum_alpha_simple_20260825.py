# -*- coding: utf-8 -*-
"""纯双变量：FF3_alpha / FF5_alpha  vs log_aum（仅规模，无其它控制）。
输出：output/aum_alpha_simple_2026-08-25.json，外加终端打印散点分位数均值
"""
import json
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

PANEL = '指标计算流水线/output/主分析面板_重建_含TOwind.csv'
QRET = '指标计算流水线/data/L4_风险应对层/基金季度收益.csv'
OUT = 'output/aum_alpha_simple_2026-08-25.json'
BAD_Q = [(2025, 3), (2026, 2), (2026, 3)]

df = pd.read_csv(PANEL)
df['fund_code'] = df['fund_code'].astype(str)
bad = df.set_index(['year', 'quarter']).index.isin(BAD_Q)
df = df[~bad].sort_values(['fund_code', 'year', 'quarter']).reset_index(drop=True)
df['log_aum'] = np.log(df['avg_aum'].clip(lower=1e-9))

# alpha 计算（FF3 / FF5 时序截距）
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

# 缩尾（1%/99%），基金层聚合均值
def winsor(s, lo=0.01, hi=0.99):
    x = s.dropna(); return s.clip(x.quantile(lo), x.quantile(hi))
df['aum_w'] = winsor(df['avg_aum'])
df['laum_w'] = np.log(df['aum_w'].clip(lower=1e-9))
g = df.groupby('fund_code').agg(
    ff3_a=('ff3_a', 'first'),
    ff5_a=('ff5_a', 'first'),
    avg_aum=('aum_w', 'mean'),
    log_aum=('laum_w', 'mean'),
).reset_index()
print('基金层样本 N=', len(g), 'ff3可用=', g.ff3_a.notna().sum(), 'ff5可用=', g.ff5_a.notna().sum())

out = {}
for dv, dvname in [('ff3_a', 'FF3_alpha'), ('ff5_a', 'FF5_alpha')]:
    sub = g.dropna(subset=[dv, 'log_aum'])
    print('\n=== DV =', dvname, 'N=', len(sub), '===')
    # 线性：alpha ~ log_aum
    m1 = smf.ols('%s ~ log_aum' % dv, data=sub).fit(cov_type='HC1')
    print('[线性 alpha ~ ln(AUM)] β_log_aum = %.5f (t=%.2f %s)  R²=%.4f  alpha_mean=%.5f' % (
        m1.params['log_aum'], m1.tvalues['log_aum'],
        '***' if m1.pvalues['log_aum']<.01 else '**' if m1.pvalues['log_aum']<.05 else '*' if m1.pvalues['log_aum']<.1 else '',
        m1.rsquared, sub[dv].mean()))
    # 线性 + 二次项（检验U型或反U型规模效应）
    sub['laum2'] = sub['log_aum'] ** 2
    m2 = smf.ols('%s ~ log_aum + laum2' % dv, data=sub).fit(cov_type='HC1')
    print('[二次 alpha ~ lnAUM + lnAUM²] β1=%.5f(t=%.2f) β2=%.5f(t=%.2f)  R²=%.4f' % (
        m2.params['log_aum'], m2.tvalues['log_aum'],
        m2.params['laum2'],   m2.tvalues['laum2'],  m2.rsquared))
    # 也跑原始AUM水平值（检验线性规模效应）
    m0 = smf.ols('%s ~ avg_aum' % dv, data=sub).fit(cov_type='HC1')
    print('[线性 alpha ~ AUM(水平)] β=%.8f (t=%.2f)  R²=%.4f' % (
        m0.params['avg_aum'], m0.tvalues['avg_aum'], m0.rsquared))

    # 按规模十分位分组的 alpha 均值
    sub['dec'] = pd.qcut(sub['avg_aum'], 10, labels=False, duplicates='drop')
    grp = sub.groupby('dec').agg(n=('dec', 'count'),
                                 avg_aum_亿=('avg_aum', lambda s: round(s.mean()*100, 2)),
                                 alpha_mean=(dv, lambda s: round(s.mean()*100, 3)),
                                 alpha_med=(dv,  lambda s: round(s.median()*100, 3))).reset_index()
    print('  规模十分位 -> alpha(%) 均值/中位数 [十分位1=最小, 10=最大]：')
    for _, r in grp.iterrows():
        print('   Q%d n=%3d  均值AUM=%6.2f亿  α均值=%+6.3f%%  α中位=%+6.3f%%' % (
            int(r.dec)+1, r.n, r.avg_aum_亿, r.alpha_mean, r.alpha_med))

    # 保存
    out[dv] = dict(
        N=int(len(sub)),
        alpha_mean=round(float(sub[dv].mean()), 5),
        linear_log=dict(b=round(float(m1.params['log_aum']), 5),
                        t=round(float(m1.tvalues['log_aum']), 2),
                        p=round(float(m1.pvalues['log_aum']), 4),
                        r2=round(float(m1.rsquared), 4)),
        quadratic_log=dict(b1=round(float(m2.params['log_aum']), 5),
                           t1=round(float(m2.tvalues['log_aum']), 2),
                           b2=round(float(m2.params['laum2']), 5),
                           t2=round(float(m2.tvalues['laum2']), 2),
                           r2=round(float(m2.rsquared), 4)),
        linear_level=dict(b=round(float(m0.params['avg_aum']), 8),
                          t=round(float(m0.tvalues['avg_aum']), 2),
                          p=round(float(m0.pvalues['avg_aum']), 4),
                          r2=round(float(m0.rsquared), 4)),
        decile=grp.to_dict(orient='records'),
    )

with open(OUT, 'w', encoding='utf-8') as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
print('\nsaved', OUT)
