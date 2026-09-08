# -*- coding: utf-8 -*-
"""三个基本面控制变量一起跑：FF3_alpha / FF5_alpha  ~ log_aum + tenure + log_fund_age
口径：基金层截面，HC1稳健标准误，1%/99%缩尾后聚合。
输出: output/three_controls_reg_2026-08-25.json
"""
import json
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

PANEL = '指标计算流水线/output/主分析面板_重建_含TOwind.csv'
QRET = '指标计算流水线/data/L4_风险应对层/基金季度收益.csv'
OUT = 'output/three_controls_reg_2026-08-25.json'
BAD_Q = [(2025, 3), (2026, 2), (2026, 3)]

df = pd.read_csv(PANEL)
df['fund_code'] = df['fund_code'].astype(str)
bad = df.set_index(['year', 'quarter']).index.isin(BAD_Q)
df = df[~bad].sort_values(['fund_code', 'year', 'quarter']).reset_index(drop=True)
df['log_aum'] = np.log(df['avg_aum'].clip(lower=1e-9))

# risk_asym 重算（即使这里不直接用，保证口径与此前一致）
qret = pd.read_csv(QRET, encoding='utf-8-sig')
qret['report_date'] = pd.to_datetime(qret['report_date'])
qret['year'] = qret['report_date'].dt.year; qret['qtr'] = qret['report_date'].dt.quarter
qb = qret.set_index(['year', 'qtr']).index.isin(BAD_Q)
qret = qret[~qb].sort_values(['fund_code', 'report_date'])
WINDOW, MINP = 8, 4
ra_map = {}
for fc, g in qret.groupby('fund_code'):
    r = g['quarter_return'].values; ra = np.full(len(r), np.nan)
    for i in range(len(r)):
        seg = r[max(0,i-WINDOW+1):i+1]
        if len(seg) < MINP: continue
        gain, loss = seg[seg>0], seg[seg<=0]
        sg = gain.std() if len(gain)>1 else np.nan
        sl = loss.std() if len(loss)>1 else np.nan
        if not (np.isnan(sg) or np.isnan(sl)): ra[i] = sg - sl
    for k,v in zip(zip(g['year'].astype(int).values, g['qtr'].astype(int).values), ra):
        ra_map[(str(fc), k[0], k[1])] = v
df = df.merge(pd.DataFrame([(fc,y,q,v) for (fc,y,q),v in ra_map.items()],
                           columns=['fund_code','year','quarter','ra_clean']),
              on=['fund_code','year','quarter'], how='left')
df['risk_asym'] = df['ra_clean']; df.drop(columns=['ra_clean'], inplace=True)

# alpha
FACS = {
    'ff3': ['MKT_excess','SMB','HML'],
    'ff5': ['ff5_MKT_excess','ff5_SMB','ff5_HML','ff5_RMW','ff5_CMA'],
}
for nm, fac in FACS.items():
    amap = {}
    for fc, g in df.groupby('fund_code'):
        gg = g.dropna(subset=['excess_return']+fac)
        y = gg['excess_return'].values.astype(float); X = gg[fac].values.astype(float)
        if len(y) < X.shape[1]+5: continue
        A = np.column_stack([np.ones(len(y)), X])
        beta, *_ = np.linalg.lstsq(A, y, rcond=None)
        amap[fc] = float(beta[0])
    df[nm+'_a'] = df['fund_code'].map(amap)
    print(nm, 'alpha可估基金数=', len(amap))

# 缩尾 + 聚合
def winsor(s, lo=0.01, hi=0.99):
    x = s.dropna(); return s.clip(x.quantile(lo), x.quantile(hi))
for c in ['avg_aum','mgr_total_tenure_v2','log_fund_age']:
    df[c+'_w'] = winsor(df[c])
df['log_aum_w'] = np.log(df['avg_aum_w'].clip(lower=1e-9))

g = df.groupby('fund_code').agg(
    ff3_a=('ff3_a','first'),
    ff5_a=('ff5_a','first'),
    log_aum=('log_aum_w','mean'),
    tenure=('mgr_total_tenure_v2_w','mean'),
    fund_age=('log_fund_age_w','mean'),
).reset_index()

# 跑三组回归：分别单跑、两两、三者全跑
specs = [
    ('S1 仅规模', '~ log_aum'),
    ('S2 仅从业年限', '~ tenure'),
    ('S3 仅基金年龄', '~ fund_age'),
    ('S4 规模+年限', '~ log_aum + tenure'),
    ('S5 规模+年龄', '~ log_aum + fund_age'),
    ('S6 年限+年龄', '~ tenure + fund_age'),
    ('S7 三控制全部', '~ log_aum + tenure + fund_age'),
]

def stars(p):
    return '***' if p<.01 else '**' if p<.05 else '*' if p<.1 else ''

out = {}
for dv, dvn in [('ff3_a','FF3_alpha'), ('ff5_a','FF5_alpha')]:
    out[dv] = []
    print('\n===== DV = %s =====' % dvn)
    for name, rhs in specs:
        cols = [c.strip() for c in rhs.replace('~','').split('+')]
        sub = g.dropna(subset=[dv]+cols)
        fml = dv + ' ' + rhs
        m = smf.ols(fml, data=sub).fit(cov_type='HC1')
        coefs = {}
        for k in cols:
            coefs[k] = dict(b=round(float(m.params[k]), 5),
                            t=round(float(m.tvalues[k]), 2),
                            p=round(float(m.pvalues[k]), 4),
                            stars=stars(m.pvalues[k]))
        rec = dict(name=name, N=int(m.nobs), r2=round(float(m.rsquared), 4),
                   adj_r2=round(float(m.rsquared_adj), 4),
                   alpha_mean=round(float(sub[dv].mean()), 5),
                   coef=coefs)
        out[dv].append(rec)
        # 打印行
        parts = []
        for k in cols:
            d = coefs[k]; parts.append('%s=%+.4f(t=%+.2f%s)' % (k, d['b'], d['t'], d['stars']))
        print('  %-20s N=%d  R²=%.4f  %s' % (name, rec['N'], rec['r2'], '  '.join(parts)))

with open(OUT,'w',encoding='utf-8') as f:
    json.dump(out,f,ensure_ascii=False,indent=1)
print('\nsaved', OUT)

# ---- 额外：三者之间的相关性 ----
corr = g[['log_aum','tenure','fund_age']].corr()
print('\n三控制变量之间的Pearson相关：')
print(corr.round(3).to_string())
