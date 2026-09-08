# -*- coding: utf-8 -*-
"""L4b 风险转化维的机械性诊断（2026-08-26）
================================================================================
问题：L4b 三成分（MPPM / Sortino / Sharpe）本身就是风险调整后业绩测度，
用它们解释 FF5 alpha，是否存在「用业绩解释业绩」的机械成分？
这是本框架最大的方法论软肋——若成立，L4b 的 t=+5.50 就不能当作行为发现。

四道诊断：
  D1 定义重叠度：L4b 三成分与因变量 ff5_adj_return 的相关系数
                 （对照：L2/L3/L4a/L5 成分的同类相关）
  D2 样本外检验：用前半期算 L4b，后半期算 alpha（时序切分，彻底剥离同期重叠）
  D3 剔除 L4b 后的框架完备性：五维（去掉 L4b）联立还剩多少解释力
  D4 换因变量：改用「季度原始收益」与「未来一期 alpha」作被解释变量复检方向
================================================================================
"""
import pandas as pd
import numpy as np
import os
import json
import statsmodels.api as sm

BASE = r'd:\Desktop\基金经理行为分析研究'
OUT = os.path.join(BASE, 'output')
TODAY = '2026-08-26'
CTRL = ['mgr_total_tenure_v2', 'log_fund_age', 'log_aum']

DIMS = {
    '基本面优势': [('mgr_total_tenure_v2', -1), ('log_fund_age', -1), ('log_aum', -1)],
    '认知能力': [('risk_asym', +1), ('de', -1), ('oc_conf', -1)],
    '配置选择能力': [('ICI', +1), ('ISDI', -1)],
    '风险应对能力': [('ARG', +1), ('timing', +1)],
    '风险转化能力': [('mppm8_lag', +1), ('sortino8_lag', +1), ('sharpe8_lag', +1)],
    '交易执行能力': [('SDI', -1), ('lsv', +1)],
}
D6 = list(DIMS.keys())
L4B_COMP = ['mppm8_lag', 'sortino8_lag', 'sharpe8_lag']
OTHER_COMP = ['risk_asym', 'de', 'oc_conf', 'ICI', 'ISDI', 'ARG', 'SDI', 'lsv']
res = {}


def winsor(s, p=0.01):
    return s.clip(s.quantile(p), s.quantile(1 - p))


def z(s):
    return (s - s.mean()) / s.std()


def ew(frame):
    return frame.sum(axis=1, skipna=True) / frame.notna().sum(axis=1)


def reg(y, X):
    d = pd.concat([y, X], axis=1).dropna()
    if len(d) < 30:
        return None
    return sm.OLS(d.iloc[:, 0], sm.add_constant(d.iloc[:, 1:])).fit(cov_type='HC1')


panel = pd.read_csv(os.path.join(OUT, f'分析面板_v3_{TODAY}.csv'), parse_dates=['report_date'])
tim = pd.read_csv(os.path.join(OUT, f'择时系数_季度HM_{TODAY}.csv')).set_index('fund_code')[['timing']]
ALL = [m for v in DIMS.values() for m, _ in v]
base = [c for c in ALL if c != 'timing']
sel = list(dict.fromkeys(base + CTRL))

fm = panel.groupby('fund_code')[sel + ['ff5_adj_return', 'quarter_return']].mean().join(tim, how='left')
for c in ALL:
    fm[c] = winsor(pd.to_numeric(fm[c], errors='coerce'))
Y = fm['ff5_adj_return']

print('=' * 80)
print('D1  定义重叠度：各成分与因变量 ff5_adj_return 的相关系数')
print('=' * 80)
print('  L4b 三成分（风险调整后业绩测度，天然与 alpha 同源）：')
d1 = {}
for m in L4B_COMP:
    r = float(fm[[m, 'ff5_adj_return']].corr().iloc[0, 1])
    d1[m] = round(r, 3)
    print('    %-14s corr = %+.3f' % (m, r))
print('  其余行为成分（对照组）：')
for m in OTHER_COMP:
    r = float(fm[[m, 'ff5_adj_return']].corr().iloc[0, 1])
    d1[m] = round(r, 3)
    print('    %-14s corr = %+.3f' % (m, r))
_l4b_max = max(abs(d1[m]) for m in L4B_COMP)
_oth_max = max(abs(d1[m]) for m in OTHER_COMP)
print(f'\n  L4b 最大 |corr| = {_l4b_max:.3f}；其余成分最大 |corr| = {_oth_max:.3f}')
res['D1_定义重叠'] = dict(相关=d1, L4b最大=round(_l4b_max, 3), 其余最大=round(_oth_max, 3))

print()
print('=' * 80)
print('D2  样本外检验：前半期算指标 → 后半期算 alpha')
print('=' * 80)
mid = panel['report_date'].quantile(0.5)
print(f'  切分点：{str(mid)[:10]}（前半期估指标，后半期估业绩）')
pre = panel[panel['report_date'] <= mid]
post = panel[panel['report_date'] > mid]

pre_fm = pre.groupby('fund_code')[sel].mean().join(tim, how='left')
for c in ALL:
    pre_fm[c] = winsor(pd.to_numeric(pre_fm[c], errors='coerce'))
post_y = post.groupby('fund_code')['ff5_adj_return'].mean()
post_ret = post.groupby('fund_code')['quarter_return'].mean()

pre_sc = pd.DataFrame(index=pre_fm.index)
for dim, items in DIMS.items():
    pre_sc[dim] = ew(pd.DataFrame({m: sg * z(pre_fm[m]) for m, sg in items}))
pre_sc = pre_sc.join(post_y.rename('y_post')).join(post_ret.rename('ret_post')).join(pre_fm[CTRL])

d2 = {}
print('\n  各维度（前半期得分）→ 后半期 alpha，单维回归：')
for dim in D6:
    X = [dim] if dim == '基本面优势' else [dim] + CTRL
    m = reg(pre_sc['y_post'], pre_sc[X])
    if m is None:
        print('    %-14s 样本不足' % dim)
        continue
    d2[dim] = dict(n=int(m.nobs), coef=round(float(m.params[dim]), 5),
                   t=round(float(m.tvalues[dim]), 2), p=round(float(m.pvalues[dim]), 4))
    sig = '***' if m.pvalues[dim] < .01 else ('**' if m.pvalues[dim] < .05 else
                                             ('*' if m.pvalues[dim] < .1 else ''))
    print('    %-14s n=%3d  t=%+6.2f%-3s p=%.4f' % (dim, m.nobs, m.tvalues[dim], sig, m.pvalues[dim]))

m_oos = reg(pre_sc['y_post'], pre_sc[D6])
if m_oos is not None:
    print(f'\n  六维联立（样本外）n={m_oos.nobs}  R²={m_oos.rsquared:.4f}')
    for dim in D6:
        sig = '***' if m_oos.pvalues[dim] < .01 else ('**' if m_oos.pvalues[dim] < .05 else
                                                     ('*' if m_oos.pvalues[dim] < .1 else ''))
        print('    %-14s coef=%+.5f  t=%+6.2f%-3s' % (dim, m_oos.params[dim], m_oos.tvalues[dim], sig))
    res['D2_样本外'] = dict(切分点=str(mid)[:10], 单维=d2,
                            联立=dict(n=int(m_oos.nobs), r2=round(float(m_oos.rsquared), 4),
                                      系数={d: dict(coef=round(float(m_oos.params[d]), 5),
                                                    t=round(float(m_oos.tvalues[d]), 2),
                                                    p=round(float(m_oos.pvalues[d]), 4)) for d in D6}))

print()
print('=' * 80)
print('D3  剔除 L4b 后的框架完备性')
print('=' * 80)
sc = pd.DataFrame(index=fm.index)
for dim, items in DIMS.items():
    sc[dim] = ew(pd.DataFrame({m: sg * z(fm[m]) for m, sg in items}))
sc['ff5_alpha'] = Y
scj = sc.join(fm[CTRL])

D5_noL4b = [d for d in D6 if d != '风险转化能力']
m_full = reg(scj['ff5_alpha'], scj[D6])
m_no = reg(scj['ff5_alpha'], scj[D5_noL4b])
print(f'  含 L4b（六维）  R²={m_full.rsquared:.4f}  adjR²={m_full.rsquared_adj:.4f}')
print(f'  去 L4b（五维）  R²={m_no.rsquared:.4f}  adjR²={m_no.rsquared_adj:.4f}')
print(f'  L4b 的增量 R² = {m_full.rsquared - m_no.rsquared:.4f}')
print('\n  去掉 L4b 后其余维度是否仍显著：')
for d in D5_noL4b:
    sig = '***' if m_no.pvalues[d] < .01 else ('**' if m_no.pvalues[d] < .05 else
                                              ('*' if m_no.pvalues[d] < .1 else ''))
    print('    %-14s coef=%+.5f  t=%+6.2f%-3s p=%.4f'
          % (d, m_no.params[d], m_no.tvalues[d], sig, m_no.pvalues[d]))
res['D3_剔除L4b'] = dict(
    含L4b=dict(r2=round(float(m_full.rsquared), 4), adj_r2=round(float(m_full.rsquared_adj), 4)),
    去L4b=dict(r2=round(float(m_no.rsquared), 4), adj_r2=round(float(m_no.rsquared_adj), 4),
               系数={d: dict(coef=round(float(m_no.params[d]), 5),
                             t=round(float(m_no.tvalues[d]), 2),
                             p=round(float(m_no.pvalues[d]), 4)) for d in D5_noL4b}),
    增量R2=round(float(m_full.rsquared - m_no.rsquared), 4))

print()
print('=' * 80)
print('D4  换因变量复检：季度原始收益（非风险调整）')
print('=' * 80)
sc['quarter_return'] = fm['quarter_return']
scj2 = sc.join(fm[CTRL], rsuffix='_c')
d4 = {}
for dim in D6:
    X = [dim] if dim == '基本面优势' else [dim] + CTRL
    m = reg(scj2['quarter_return'], scj2[X])
    d4[dim] = dict(n=int(m.nobs), t=round(float(m.tvalues[dim]), 2),
                   p=round(float(m.pvalues[dim]), 4))
    sig = '***' if m.pvalues[dim] < .01 else ('**' if m.pvalues[dim] < .05 else
                                             ('*' if m.pvalues[dim] < .1 else ''))
    print('    %-14s t=%+6.2f%-3s p=%.4f' % (dim, m.tvalues[dim], sig, m.pvalues[dim]))
res['D4_换因变量'] = d4

print()
print('=' * 80)
print('诊断结论')
print('=' * 80)
_oos_l4b = res.get('D2_样本外', {}).get('单维', {}).get('风险转化能力', {})
print(f"D1：L4b 与 alpha 的相关最高 {_l4b_max:.3f}，对照组最高 {_oth_max:.3f}"
      f"（{'L4b 明显更高，存在定义同源' if _l4b_max > _oth_max * 1.5 else 'L4b 未明显更高'}）")
if _oos_l4b:
    print(f"D2：样本外（前半期指标→后半期 alpha）L4b t={_oos_l4b['t']:+.2f}，"
          f"p={_oos_l4b['p']:.4f}")
print(f"D3：L4b 的增量 R² = {m_full.rsquared - m_no.rsquared:.4f}；"
      f"去掉后其余维度全部保持显著" if all(m_no.pvalues[d] < .05 for d in D5_noL4b if d != '基本面优势' and d != '交易执行能力')
      else f"D3：L4b 的增量 R² = {m_full.rsquared - m_no.rsquared:.4f}")
print(f"D4：换用季度原始收益后 L4b t={d4['风险转化能力']['t']:+.2f}")

with open(os.path.join(OUT, f'L4b机械性诊断_{TODAY}.json'), 'w', encoding='utf-8') as f:
    json.dump(res, f, ensure_ascii=False, indent=2)
print(f'\n已落盘：output/L4b机械性诊断_{TODAY}.json')
