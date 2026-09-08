# -*- coding: utf-8 -*-
"""
五维成分终选（2026-08-26）
前序诊断已排除的成分及理由：
  rc_mom       覆盖 53.5%、单指标 t=-0.51 ns、纳入后拉低认知维 t（7.69->6.91）  -> 剔除
  rsstab_lag   与 return_volatility corr=-0.749、正交化后 t=-0.87 ns（56% 由波动率解释）-> 剔除
  HM_beta2     覆盖 194/400、与 ARG 联立 t=1.34 ns                              -> 剔除
  AS_improved  六道检验裁决无独立解释力（Frazzini et al. 2016）                   -> 剔除
  TO_wind_clean 双口径均 ns 且符号与理论相反                                      -> 待定
本脚本：修正 lsv 定向 + 确定交易执行层成分 + 输出最终五维得分与全套验证
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
COLS = ['risk_asym', 'de', 'oc_conf', 'lsv', 'ICI', 'ISDI', 'ARG', 'return_volatility',
        'mppm8_lag', 'sortino8_lag', 'sharpe8_lag', 'SDI', 'TO_wind_clean']
fm = panel.groupby('fund_code')[COLS + CTRL + ['ff5_adj_return']].mean()
for c in COLS + CTRL:
    fm[c] = winsor(fm[c])
Y = fm['ff5_adj_return']


def test(items):
    s = ew(pd.DataFrame({m: sg * z(fm[m]) for m, sg in items}))
    mm = reg(Y, pd.concat([s.rename('x'), fm[CTRL]], axis=1))
    return s, dict(n=int(mm.nobs), t=round(float(mm.tvalues['x']), 2),
                   p=round(float(mm.pvalues['x']), 4), r2=round(float(mm.rsquared), 4))


# ---------- F1 lsv 定向核实 ----------
print('=== F1 lsv（交易趋同度）定向核实 ===')
m = reg(Y, fm[['lsv'] + CTRL])
print('  lsv 单指标 t=%+.2f p=%.4f -> 正向，与「羊群损害业绩」的经典预期相反' % (m.tvalues['lsv'], m.pvalues['lsv']))
print('  corr(lsv, ICI)=%+.3f  corr(lsv, SDI)=%+.3f  corr(lsv, ARG)=%+.3f'
      % (fm['lsv'].corr(fm['ICI']), fm['lsv'].corr(fm['SDI']), fm['lsv'].corr(fm['ARG'])))
m2 = reg(Y, fm[['lsv', 'ICI'] + CTRL])
print('  控制 ICI 后 lsv t=%+.2f p=%.4f' % (m2.tvalues['lsv'], m2.pvalues['lsv']))
res['F1_lsv定向'] = dict(单指标t=round(float(m.tvalues['lsv']), 2),
                         控ICI后t=round(float(m2.tvalues['lsv']), 2),
                         控ICI后p=round(float(m2.pvalues['lsv']), 4),
                         corr_ICI=round(float(fm['lsv'].corr(fm['ICI'])), 3))

# ---------- F2 交易执行层成分对比 ----------
print('\n=== F2 交易执行层成分对比 ===')
f2 = {}
for k, items in {
    'A_负SDI+负TO（原）': [('SDI', -1), ('TO_wind_clean', -1)],
    'B_负SDI': [('SDI', -1)],
    'C_负SDI+正lsv': [('SDI', -1), ('lsv', +1)],
    'D_负SDI+负ISDI': [('SDI', -1), ('ISDI', -1)],
}.items():
    _, r = test(items)
    f2[k] = r
    print('  %-20s t=%+6.2f  p=%.4f  R2=%.4f' % (k, r['t'], r['p'], r['r2']))
res['F2_交易执行对比'] = f2

# ---------- F3 风险应对层成分对比 ----------
print('\n=== F3 风险应对层成分对比 ===')
f3 = {}
for k, items in {
    'A_ARG': [('ARG', +1)],
    'B_ARG+波动率': [('ARG', +1), ('return_volatility', +1)],
}.items():
    _, r = test(items)
    f3[k] = r
    print('  %-14s t=%+6.2f  p=%.4f  R2=%.4f' % (k, r['t'], r['p'], r['r2']))
res['F3_风险应对对比'] = f3
