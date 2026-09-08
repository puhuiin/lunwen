# -*- coding: utf-8 -*-
"""
维度成分定稿诊断（2026-08-26）
解决两个悬置问题：
  Q1 rc_mom（追涨杀跌）单指标 t=-0.51 不显著，是否纳入认知能力复合？
  Q2 rsstab_lag 与 return_volatility corr=-0.749，实为反向波动率代理，
     其 t=-4.28 与 Huang, Sialm & Zhang (2011) 理论方向冲突 -> 正交化后重判
"""
import pandas as pd, numpy as np, os, json
import statsmodels.api as sm

BASE = r'd:\Desktop\基金经理行为分析研究'
OUT = os.path.join(BASE, 'output')
CTRL = ['mgr_total_tenure_v2', 'log_fund_age', 'log_aum']
res = {}


def winsor(s, p=0.01):
    return s.clip(s.quantile(p), s.quantile(1 - p))


def z(s):
    return (s - s.mean()) / s.std()


def ew(frame):
    return frame.sum(axis=1, skipna=True) / frame.notna().sum(axis=1)


def reg(y, X):
    d = pd.concat([y, X], axis=1).dropna()
    return sm.OLS(d.iloc[:, 0], sm.add_constant(d.iloc[:, 1:])).fit(cov_type='HC1')


panel = pd.read_csv(os.path.join(OUT, '分析面板_v3_2026-08-26.csv'), parse_dates=['report_date'])
new = pd.read_csv(os.path.join(OUT, '新增指标面板_2026-08-25.csv'), parse_dates=['report_date'])
panel = panel.merge(new[['fund_code', 'report_date', 'rc_mom']], on=['fund_code', 'report_date'], how='left')

COLS = ['risk_asym', 'de', 'oc_conf', 'rc_mom', 'ICI', 'ISDI', 'ARG',
        'rsstab_lag', 'return_volatility', 'mppm8_lag', 'sortino8_lag',
        'sharpe8_lag', 'SDI', 'TO_wind_clean', 'lsv']
fm = panel.groupby('fund_code')[COLS + CTRL + ['ff5_adj_return']].mean()
for c in COLS + CTRL:
    fm[c] = winsor(fm[c])
Y = fm['ff5_adj_return']

# ============ Q1 rc_mom 是否纳入认知复合 ============
print('=== Q1 认知能力复合：含 rc_mom vs 不含 rc_mom ===')
opts = {
    'A_四成分_含rc_mom': [('risk_asym', +1), ('de', -1), ('oc_conf', -1), ('rc_mom', -1)],
    'B_三成分_去rc_mom': [('risk_asym', +1), ('de', -1), ('oc_conf', -1)],
    'C_四成分_加lsv': [('risk_asym', +1), ('de', -1), ('oc_conf', -1), ('lsv', -1)],
    'D_五成分_全': [('risk_asym', +1), ('de', -1), ('oc_conf', -1), ('lsv', -1), ('rc_mom', -1)],
}
q1 = {}
for k, items in opts.items():
    s = ew(pd.DataFrame({m: sg * z(fm[m]) for m, sg in items}))
    m_ = reg(Y, pd.concat([s.rename('cog'), fm[CTRL]], axis=1))
    q1[k] = dict(n=int(m_.nobs), t=round(float(m_.tvalues['cog']), 2),
                 p=round(float(m_.pvalues['cog']), 4), r2=round(float(m_.rsquared), 4),
                 有效基金数=int(s.notna().sum()))
    print('  %-18s n=%3d  t=%+6.2f  p=%.4f  R2=%.4f' % (k, m_.nobs, m_.tvalues['cog'], m_.pvalues['cog'], m_.rsquared))
print('  lsv 单指标 t=%+.2f' % reg(Y, fm[['lsv'] + CTRL]).tvalues['lsv'])
res['Q1_认知复合方案对比'] = q1

# ============ Q2 rsstab 正交化 ============
print('\n=== Q2 rsstab_lag 剥离波动率成分后重判 ===')
d = fm[['rsstab_lag', 'return_volatility']].dropna()
mo = sm.OLS(d['rsstab_lag'], sm.add_constant(d['return_volatility'])).fit()
fm['rsstab_orth'] = np.nan
fm.loc[d.index, 'rsstab_orth'] = mo.resid
print('  rsstab_lag = a + b*return_volatility 的 R2 = %.4f（b t=%+.2f）'
      % (mo.rsquared, mo.tvalues['return_volatility']))
for v in ['rsstab_lag', 'rsstab_orth']:
    m_ = reg(Y, fm[[v] + CTRL])
    print('  %-14s t=%+6.2f  p=%.4f' % (v, m_.tvalues[v], m_.pvalues[v]))
    res.setdefault('Q2_rsstab正交化', {})[v] = dict(
        t=round(float(m_.tvalues[v]), 2), p=round(float(m_.pvalues[v]), 4))
res['Q2_rsstab正交化']['解释度R2'] = round(float(mo.rsquared), 4)

# ============ Q2b 风险应对能力成分方案 ============
print('\n=== Q2b 风险应对能力复合方案对比 ===')
opts2 = {
    'A_ARG+负rsstab（数据向）': [('ARG', +1), ('rsstab_lag', -1)],
    'B_ARG+正rsstab（理论向）': [('ARG', +1), ('rsstab_lag', +1)],
    'C_ARG单指标': [('ARG', +1)],
    'D_ARG+正交rsstab': [('ARG', +1), ('rsstab_orth', +1)],
    'E_ARG+波动率': [('ARG', +1), ('return_volatility', +1)],
}
q2b = {}
for k, items in opts2.items():
    s = ew(pd.DataFrame({m: sg * z(fm[m]) for m, sg in items}))
    m_ = reg(Y, pd.concat([s.rename('rr'), fm[CTRL]], axis=1))
    q2b[k] = dict(n=int(m_.nobs), t=round(float(m_.tvalues['rr']), 2),
                  p=round(float(m_.pvalues['rr']), 4), r2=round(float(m_.rsquared), 4))
    print('  %-24s t=%+6.2f  p=%.4f  R2=%.4f' % (k, m_.tvalues['rr'], m_.pvalues['rr'], m_.rsquared))
res['Q2b_风险应对方案对比'] = q2b

# ============ Q3 交易执行能力（原方案 t=+0.48 无效）============
print('\n=== Q3 交易执行能力方案对比（原 -SDI-TO t=+0.48 无效）===')
opts3 = {
    'A_负SDI+负TO': [('SDI', -1), ('TO_wind_clean', -1)],
    'B_负SDI单指标': [('SDI', -1)],
    'C_负SDI+ARG': [('SDI', -1), ('ARG', +1)],
}
q3 = {}
for k, items in opts3.items():
    s = ew(pd.DataFrame({m: sg * z(fm[m]) for m, sg in items}))
    m_ = reg(Y, pd.concat([s.rename('ex')], axis=1).join(fm[CTRL]))
    q3[k] = dict(t=round(float(m_.tvalues['ex']), 2), p=round(float(m_.pvalues['ex']), 4),
                 r2=round(float(m_.rsquared), 4))
    print('  %-16s t=%+6.2f  p=%.4f  R2=%.4f' % (k, m_.tvalues['ex'], m_.pvalues['ex'], m_.rsquared))
print('  TO_wind_clean 覆盖 %.1f%%（面板）' % (panel['TO_wind_clean'].notna().mean() * 100))
res['Q3_交易执行方案对比'] = q3

with open(os.path.join(OUT, '维度成分定稿诊断_2026-08-26.json'), 'w', encoding='utf-8') as f:
    json.dump(res, f, ensure_ascii=False, indent=2)
print('\n已保存 output/维度成分定稿诊断_2026-08-26.json')
