# -*- coding: utf-8 -*-
"""朴素DV五口径压力测试 + SDI/ISDI对照（2026-08-25，M4-b ISDI主规格）
DV五口径: ①纯收益 ②vs市场 ③vs同侪 ④FF5季调(主口径) ⑤FF5基金层α
RHS: M4-b全指标(9行为+3控制) + 年度FE, 基金聚类SE
"""
import os, json, warnings
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
warnings.filterwarnings('ignore')

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
df = pd.read_csv(os.path.join(ROOT,'指标计算流水线','output','主分析面板_重建_含TOwind.csv'),
                 dtype={'fund_code':str})
BAD_Q = [(2025,3),(2026,2),(2026,3)]
df = df[~df.set_index(['year','quarter']).index.isin(BAD_Q)]
df = df.sort_values(['fund_code','report_date']).reset_index(drop=True)

def winsor(s, lo=0.01, hi=0.99):
    s = s.astype(float); a,b = s.quantile(lo), s.quantile(hi); return s.clip(a,b)

df['log_aum'] = np.log(df['avg_aum'].clip(lower=1e-9))

print('面板列:', list(df.columns))
print()

# excess_return 口径检查：quarter−excess 若随季度大幅波动→减市场；若近似常数→减无风险
sub = df.dropna(subset=['quarter_return','excess_return'])
diff = sub['quarter_return'] - sub['excess_return']
gm = diff.groupby(sub['report_date']).mean()
print(f'excess_return口径: quarter−excess 季度间均值std={gm.std():.4f}, 总std={diff.std():.4f}')
print()

BEH = ['risk_asym','de','lsv','ICI','AS_improved','ISDI','ARG','return_volatility','TO_wind']
CTRL = ['mgr_total_tenure_v2','log_fund_age','log_aum']
for c in BEH + CTRL + ['SDI']:
    df[c+'_w'] = winsor(df[c])

df['dv1_raw'] = winsor(df['quarter_return'])
# ② vs市场：市场季度收益 = MKT_excess + rf（先验证两者在报告期内无基金间变异）
for col in ['MKT_excess','rf']:
    v = df.groupby('report_date')[col].std().max()
    print(f'{col} 报告期内最大基金间std = {v:.6f}')
df['mkt_q'] = df['MKT_excess'] + df['rf']
print(f'市场季度收益: mean={df["mkt_q"].mean():.4f}, std={df["mkt_q"].std():.4f}')
df['dv2_excess'] = winsor(df['quarter_return'] - df['mkt_q'])
df['dv3_peer'] = winsor(df['quarter_return'] - df.groupby('report_date')['quarter_return'].transform('mean'))
df['dv4_ff5adj'] = winsor(df['ff5_adj_return'])

def run_panel(dv, rhs_w, label):
    sub = df.dropna(subset=[dv]+rhs_w).copy().reset_index(drop=True)
    fml = dv + ' ~ ' + ' + '.join(rhs_w) + ' + C(year)'
    m = smf.ols(fml, data=sub).fit(cov_type='cluster', cov_kwds={'groups':sub['fund_code']})
    out = {'N': int(m.nobs), 'R2': round(float(m.rsquared),4), 'coefs': {}}
    for c in rhs_w:
        out['coefs'][c[:-2]] = {'b': round(float(m.params[c]),4), 't': round(float(m.tvalues[c]),2),
                                'p': round(float(m.pvalues[c]),4)}
    print(f'[{label}] N={out["N"]} R2={out["R2"]}')
    return out

results = {}

# ===== Part 1: SDI/ISDI 对照（与今日M4同规格）=====
BEH_SDI = [('SDI' if c == 'ISDI' else c) for c in BEH]
r_sdi  = run_panel('dv4_ff5adj', [c+'_w' for c in BEH_SDI+CTRL], 'M4-a 仅SDI')
r_isdi = run_panel('dv4_ff5adj', [c+'_w' for c in BEH+CTRL],       'M4-b 仅ISDI(主)')
r_both = run_panel('dv4_ff5adj', [c+'_w' for c in BEH+['SDI']+CTRL], 'M4-c 两者同入')
for nm, r, k in [('M4-a',r_sdi,'SDI'), ('M4-b',r_isdi,'ISDI'), ('M4-c',r_both,'SDI'), ('M4-c',r_both,'ISDI')]:
    c = r['coefs'][k]
    print(f'   {nm} {k}: b={c["b"]:+.4f} t={c["t"]:+.2f} p={c["p"]:.4f}')
results['sdi_isdi_compare'] = {'M4a_SDI': r_sdi, 'M4b_ISDI': r_isdi, 'M4c_both': r_both}
tmp = df.dropna(subset=['SDI','ISDI'])
results['sdi_isdi_corr'] = {'pearson': round(float(tmp['SDI'].corr(tmp['ISDI'])),3),
                            'spearman': round(float(tmp['SDI'].corr(tmp['ISDI'], method='spearman')),3)}
print()

# ===== Part 2: 朴素DV口径 =====
calibers = [('①纯收益','dv1_raw'), ('②vs市场','dv2_excess'), ('③vs同侪','dv3_peer'),
            ('④FF5季调(主口径)','dv4_ff5adj')]
results['five_caliber'] = {}
for name, dv in calibers:
    r = run_panel(dv, [c+'_w' for c in BEH+CTRL], name)
    results['five_caliber'][name] = r
    for c in BEH:
        cc = r['coefs'][c]
        st = '***' if cc['p']<.01 else '**' if cc['p']<.05 else '*' if cc['p']<.1 else ''
        print(f'   {c:20s} b={cc["b"]:+.4f} t={cc["t"]:+.2f}{st}')
    print()

# ===== Part 3: ⑤ 基金层横截面（各变量取基金内均值，DV=平均FF5季调收益）=====
fund = df.groupby('fund_code').agg(
    dv5=('dv4_ff5adj','mean'),
    **{c+'_w': (c+'_w','mean') for c in BEH+CTRL}
).reset_index().dropna()
fml5 = 'dv5 ~ ' + ' + '.join(c+'_w' for c in BEH+CTRL)
m5 = smf.ols(fml5, data=fund).fit(cov_type='HC1')
r5 = {'N': int(m5.nobs), 'R2': round(float(m5.rsquared),4), 'coefs': {}}
for c in BEH+CTRL:
    r5['coefs'][c] = {'b': round(float(m5.params[c+'_w']),4), 't': round(float(m5.tvalues[c+'_w']),2),
                      'p': round(float(m5.pvalues[c+'_w']),4)}
results['five_caliber']['⑤基金层横截面'] = r5
print('[⑤基金层横截面] N=%d R2=%.4f' % (r5['N'], r5['R2']))
for c in BEH:
    cc = r5['coefs'][c]
    st = '***' if cc['p']<.01 else '**' if cc['p']<.05 else '*' if cc['p']<.1 else ''
    print(f'   {c:20s} b={cc["b"]:+.4f} t={cc["t"]:+.2f}{st}')
print()

with open(os.path.join(ROOT,'output','naive_dv_and_sdi_compare_2026-08-25.json'),'w',encoding='utf-8') as f:
    json.dump(results, f, ensure_ascii=False, indent=1)
print('saved output/naive_dv_and_sdi_compare_2026-08-25.json')
