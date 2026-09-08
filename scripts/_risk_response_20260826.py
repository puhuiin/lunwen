# -*- coding: utf-8 -*-
"""
风险应对能力重构诊断（2026-08-26）
背景：rsstab_lag 正交化后 t=-0.87 ns（其显著性 56% 由 return_volatility 解释），
      不能作为独立的风险应对成分。需要理论内涵更贴切的第二成分。
候选：HM 择时系数 HM_beta2 —— Henriksson & Merton (1981), Journal of Business 54(4), 513-533
      r_p - r_f = a + b1(r_m - r_f) + b2*max(0, -(r_m - r_f)) + e
      b2 > 0 表示市场下行时主动降低暴露，即「风险应对」的直接刻画。
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
hm = pd.read_csv(os.path.join(OUT, 'batch3_hm_factors_2026-08-22.csv'))
print('HM 因子表 %d 行 / %d 基金 / 年份 %s-%s'
      % (len(hm), hm['fund_code'].nunique(), hm['year'].min(), hm['year'].max()))
print('HM_beta2 描述：mean=%.4f std=%.4f min=%.4f max=%.4f'
      % (hm['HM_beta2'].mean(), hm['HM_beta2'].std(), hm['HM_beta2'].min(), hm['HM_beta2'].max()))

# 基金层：HM_beta2 时序均值
hmf = hm.groupby('fund_code')['HM_beta2'].mean().rename('HM_beta2')

COLS = ['ARG', 'rsstab_lag', 'return_volatility', 'risk_asym', 'de', 'oc_conf',
        'ICI', 'ISDI', 'SDI', 'mppm8_lag', 'sortino8_lag', 'sharpe8_lag']
fm = panel.groupby('fund_code')[COLS + CTRL + ['ff5_adj_return']].mean()
fm = fm.join(hmf, how='left')
for c in COLS + CTRL + ['HM_beta2']:
    fm[c] = winsor(fm[c])
Y = fm['ff5_adj_return']
print('HM_beta2 匹配到 %d / %d 只基金' % (fm['HM_beta2'].notna().sum(), len(fm)))

# ---------- H1 HM_beta2 单指标 ----------
print('\n=== H1 HM_beta2 单指标（规格I，HC1，含三控制） ===')
m1 = reg(Y, fm[['HM_beta2'] + CTRL])
print('  HM_beta2  n=%d  coef=%+.5f  t=%+.2f  p=%.4f  R2=%.4f'
      % (m1.nobs, m1.params['HM_beta2'], m1.tvalues['HM_beta2'], m1.pvalues['HM_beta2'], m1.rsquared))
res['H1_HM单指标'] = dict(n=int(m1.nobs), coef=round(float(m1.params['HM_beta2']), 5),
                          t=round(float(m1.tvalues['HM_beta2']), 2),
                          p=round(float(m1.pvalues['HM_beta2']), 4), r2=round(float(m1.rsquared), 4))

print('\n  与既有指标相关：')
cr = fm[['HM_beta2', 'ARG', 'rsstab_lag', 'return_volatility', 'risk_asym', 'mppm8_lag']].corr()['HM_beta2']
print(cr.round(3).to_string())
res['H1_相关'] = {k: round(float(v), 3) for k, v in cr.items() if k != 'HM_beta2'}

# ---------- H2 与 ARG 联立（是否独立） ----------
print('\n=== H2 HM_beta2 与 ARG 联立 ===')
m2 = reg(Y, fm[['HM_beta2', 'ARG'] + CTRL])
for v in ['HM_beta2', 'ARG']:
    print('  %-10s t=%+.2f  p=%.4f' % (v, m2.tvalues[v], m2.pvalues[v]))
print('  R2=%.4f' % m2.rsquared)
res['H2_联立'] = {v: dict(t=round(float(m2.tvalues[v]), 2), p=round(float(m2.pvalues[v]), 4))
                  for v in ['HM_beta2', 'ARG']}

# ---------- H3 风险应对能力最终方案对比 ----------
print('\n=== H3 风险应对能力复合方案终选 ===')
opts = {
    'A_ARG单指标': [('ARG', +1)],
    'B_ARG+HM择时': [('ARG', +1), ('HM_beta2', +1)],
    'C_ARG+HM+risk_asym': [('ARG', +1), ('HM_beta2', +1), ('risk_asym', +1)],
    'D_旧方案_ARG+负rsstab': [('ARG', +1), ('rsstab_lag', -1)],
}
h3 = {}
for k, items in opts.items():
    s = ew(pd.DataFrame({m: sg * z(fm[m]) for m, sg in items}))
    mm = reg(Y, pd.concat([s.rename('rr'), fm[CTRL]], axis=1))
    h3[k] = dict(n=int(mm.nobs), 有效基金=int(s.notna().sum()),
                 t=round(float(mm.tvalues['rr']), 2), p=round(float(mm.pvalues['rr']), 4),
                 r2=round(float(mm.rsquared), 4))
    print('  %-22s n=%3d 有效%3d  t=%+6.2f  p=%.4f  R2=%.4f'
          % (k, mm.nobs, s.notna().sum(), mm.tvalues['rr'], mm.pvalues['rr'], mm.rsquared))
res['H3_方案对比'] = h3

with open(os.path.join(OUT, '风险应对重构_2026-08-26.json'), 'w', encoding='utf-8') as f:
    json.dump(res, f, ensure_ascii=False, indent=2)
print('\n已保存 output/风险应对重构_2026-08-26.json')
