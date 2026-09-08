# -*- coding: utf-8 -*-
"""分期稳健性：2020 年结构性扩张前后的队列对照（2026-08-26）
================================================================================
背景：样本基金数从 2019 年 61 只跃升至 2020 年末 286 只，主表使用全样本。
审稿人必问：结论是否被 2020 年后的新基金队列驱动？
做法：按基金首次出现在样本中的报告期划分队列——
  老基金队列（首次报告期 < 2020-01-01）
  新基金队列（首次报告期 ≥ 2020-01-01）
分别做六维联立回归（与主表方程 7 同口径），对照系数符号与显著性。
输出：output/分期稳健性_2026-08-26.json
"""
import pandas as pd
import numpy as np
import os
import json
import statsmodels.api as sm

BASE = r'd:\Desktop\基金经理行为分析研究'
OUT = os.path.join(BASE, 'output')
TODAY = '2026-08-26'

DIMS6 = {
    '基本面优势': [('mgr_total_tenure_v2', -1), ('log_fund_age', -1), ('log_aum', -1)],
    '认知能力': [('risk_asym', +1), ('de', -1), ('oc_conf', -1)],
    '配置选择能力': [('ICI', +1), ('ISDI', -1)],
    '风险应对能力': [('ARG', +1), ('timing', +1)],
    '风险转化能力': [('mppm8_lag', +1), ('sortino8_lag', +1), ('sharpe8_lag', +1)],
    '交易执行能力': [('SDI', -1), ('lsv', +1)],
}
ALL = [m for v in DIMS6.values() for m, _ in v]
DIM_NAMES = list(DIMS6.keys())


def winsor(s, p=0.01):
    return s.clip(s.quantile(p), s.quantile(1 - p))


def z(s):
    return (s - s.mean()) / s.std()


def ew(frame):
    return frame.sum(axis=1, skipna=True) / frame.notna().sum(axis=1)


def reg(y, X):
    d = pd.concat([y, X], axis=1).dropna()
    return sm.OLS(d.iloc[:, 0], sm.add_constant(d.iloc[:, 1:])).fit(cov_type='HC1')


panel = pd.read_csv(os.path.join(OUT, f'分析面板_v3_{TODAY}.csv'), parse_dates=['report_date'])
tim = pd.read_csv(os.path.join(OUT, f'择时系数_季度HM_{TODAY}.csv')).set_index('fund_code')[['timing']]
sel = list(dict.fromkeys([m for m in ALL if m != 'timing'] + ['ff5_adj_return']))
fm = panel.groupby('fund_code')[sel].mean().join(tim, how='left')
first_seen = panel.groupby('fund_code')['report_date'].min()
for c in ALL:
    fm[c] = winsor(pd.to_numeric(fm[c], errors='coerce'))

sc = pd.DataFrame(index=fm.index)
for dim, items in DIMS6.items():
    sc[dim] = ew(pd.DataFrame({m: sg * z(fm[m]) for m, sg in items}))
sc['ff5_adj_return'] = fm['ff5_adj_return']
sc['首次报告期'] = first_seen

CUT = pd.Timestamp('2020-01-01')
res = {'切分标准': '按基金首次出现在样本中的报告期划分：老基金 <2020-01-01，新基金 ≥2020-01-01',
       '口径': '六维联立（与主表方程 7 同口径，HC1）'}
for lab, mask in [('全样本', pd.Series(True, index=sc.index)),
                  ('老基金队列', sc['首次报告期'] < CUT),
                  ('新基金队列', sc['首次报告期'] >= CUT)]:
    sub = sc[mask]
    m = reg(sub['ff5_adj_return'], sub[DIM_NAMES])
    row = dict(n=int(m.nobs), r2=round(float(m.rsquared), 4), 系数={})
    for d in DIM_NAMES:
        row['系数'][d] = dict(coef=round(float(m.params[d]), 5),
                             t=round(float(m.tvalues[d]), 2),
                             p=round(float(m.pvalues[d]), 4))
    res[lab] = row
    print('%-8s n=%3d  R²=%.4f  ' % (lab, m.nobs, m.rsquared)
          + '  '.join('%s %+.2f%s' % (d[:3], m.tvalues[d],
                                      '***' if m.pvalues[d] < .01 else
                                      ('**' if m.pvalues[d] < .05 else
                                       ('*' if m.pvalues[d] < .1 else '')))
                      for d in DIM_NAMES))

with open(os.path.join(OUT, f'分期稳健性_{TODAY}.json'), 'w', encoding='utf-8') as f:
    json.dump(res, f, ensure_ascii=False, indent=2)
print('\n已落盘：output/分期稳健性_%s.json' % TODAY)
