# -*- coding: utf-8 -*-
"""
AS 裁决收官：条件效应检验

前置发现：
  AS 单变量对 FF5 alpha 无解释力（横截面 t=-0.26；五分位 Q5-Q1 t=1.36 ns；十分位曲线平坦）；
  季度面板单变量的 +5.33 在控制 ICI/ISDI 后衰减，全模型转负且不稳；
  U 型在 2020 后子样本与全控制下消失，判定为不稳健。

文献对照：Petajisto (2013, FAJ) 指出高主动份额只在"集中选股型"中带来超额，
而"分散型高主动"（diversified stock pickers）不跑赢；
Frazzini, Friedman & Pomorski (2016, FAJ) 进一步指出 AS 本身不预测业绩，
其表观预测力来自与基准选择、行业集中度的混杂。

因此本脚本做最后一步：检验 AS 是否为**条件有效**（依赖行业集中度），
若交互项显著为正、且分组结果一致，则报告写"条件有效"；否则统一写"无独立解释力"。

  T1 AS × ICI 交互（基金层 + 季度面板，均去中心化）
  T2 按 ICI 中位数分组，组内 AS 单变量回归
  T3 2×2 分组：AS 高低 × ICI 高低 的 alpha 均值矩阵

输出 output/AS条件效应_2026-08-26.json
"""
import json
import numpy as np
import pandas as pd
import statsmodels.api as sm
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
V3 = ROOT / 'output' / '分析面板_v3_2026-08-26.csv'
OUT = ROOT / 'output'

CTRL = ['mgr_total_tenure_v2', 'log_fund_age', 'log_aum']


def winsor(s, p=0.01):
    s = pd.to_numeric(s, errors='coerce')
    return s.clip(s.quantile(p), s.quantile(1 - p))


def main():
    df = pd.read_csv(V3, parse_dates=['report_date'])
    df['year'] = df['report_date'].dt.year
    base = ['AS_improved', 'ICI', 'ff5_adj_return', 'alpha_q'] + CTRL
    fm = df.groupby('fund_code')[base].mean().dropna(
        subset=['ff5_adj_return', 'AS_improved', 'ICI'])

    res = {}

    # ---- T1 基金层交互 ----
    d = fm.copy()
    for c in ['AS_improved', 'ICI', 'ff5_adj_return']:
        d[c] = winsor(d[c])
    d['AS_c'] = d['AS_improved'] - d['AS_improved'].mean()
    d['ICI_c'] = d['ICI'] - d['ICI'].mean()
    d['AS_x_ICI'] = d['AS_c'] * d['ICI_c']
    xs = ['AS_c', 'ICI_c', 'AS_x_ICI'] + CTRL
    dd = d[['ff5_adj_return'] + xs].dropna()
    m = sm.OLS(dd['ff5_adj_return'].astype(float),
               sm.add_constant(dd[xs].astype(float))).fit(cov_type='HC1')
    res['T1_基金层交互'] = {'n': int(len(dd)), 'r2': round(float(m.rsquared), 4),
                       **{x: {'b': round(float(m.params[x]), 6),
                              't': round(float(m.tvalues[x]), 2),
                              'p': round(float(m.pvalues[x]), 4)}
                          for x in ['AS_c', 'ICI_c', 'AS_x_ICI']}}

    # ---- T1b 季度面板交互 ----
    p = df[['fund_code', 'report_date', 'alpha_q', 'AS_improved', 'ICI'] + CTRL].dropna().copy()
    for c in ['AS_improved', 'ICI', 'alpha_q']:
        p[c] = winsor(p[c])
    p['AS_c'] = p['AS_improved'] - p['AS_improved'].mean()
    p['ICI_c'] = p['ICI'] - p['ICI'].mean()
    p['AS_x_ICI'] = p['AS_c'] * p['ICI_c']
    X = p[['AS_c', 'ICI_c', 'AS_x_ICI'] + CTRL].astype(float).reset_index(drop=True)
    qd = pd.get_dummies(p['report_date'].astype(str), prefix='q',
                        drop_first=True).astype(float).reset_index(drop=True)
    mm = sm.OLS(p['alpha_q'].astype(float).reset_index(drop=True),
                sm.add_constant(pd.concat([X, qd], axis=1))).fit(
        cov_type='cluster', cov_kwds={'groups': p['fund_code'].values})
    res['T1b_季度面板交互'] = {'n': int(len(p)), 'nfund': int(p['fund_code'].nunique()),
                         'r2': round(float(mm.rsquared), 4),
                         **{x: {'b': round(float(mm.params[x]), 6),
                                't': round(float(mm.tvalues[x]), 2),
                                'p': round(float(mm.pvalues[x]), 4)}
                            for x in ['AS_c', 'ICI_c', 'AS_x_ICI']}}

    # ---- T2 按 ICI 分组，组内 AS 回归 ----
    med = fm['ICI'].median()
    res['T2_分组内AS'] = {}
    for lab, sel in [('低集中度组', fm['ICI'] <= med), ('高集中度组', fm['ICI'] > med)]:
        g = fm[sel][['ff5_adj_return', 'AS_improved'] + CTRL].dropna().copy()
        g['ff5_adj_return'] = winsor(g['ff5_adj_return'])
        g['AS_improved'] = winsor(g['AS_improved'])
        mg = sm.OLS(g['ff5_adj_return'].astype(float),
                    sm.add_constant(g[['AS_improved'] + CTRL].astype(float))
                    ).fit(cov_type='HC1')
        res['T2_分组内AS'][lab] = {
            'n': int(len(g)), 'r2': round(float(mg.rsquared), 4),
            'b': round(float(mg.params['AS_improved']), 6),
            't': round(float(mg.tvalues['AS_improved']), 2),
            'p': round(float(mg.pvalues['AS_improved']), 4)}

    # ---- T3 2x2 矩阵 ----
    q = fm.dropna(subset=['AS_improved', 'ICI', 'ff5_adj_return']).copy()
    q['AS_hi'] = q['AS_improved'] > q['AS_improved'].median()
    q['ICI_hi'] = q['ICI'] > q['ICI'].median()
    cell = q.groupby(['ICI_hi', 'AS_hi'])['ff5_adj_return'].agg(['size', 'mean', 'median'])
    res['T3_2x2'] = {f'ICI{"高" if a else "低"}_AS{"高" if b else "低"}':
                     {'n': int(r['size']), 'alpha_mean': round(float(r['mean']), 6),
                      'alpha_median': round(float(r['median']), 6)}
                     for (a, b), r in cell.iterrows()}
    for lab, sel in [('低集中度组', ~q['ICI_hi']), ('高集中度组', q['ICI_hi'])]:
        s = q[sel]
        hi = s[s['AS_hi']]['ff5_adj_return']
        lo = s[~s['AS_hi']]['ff5_adj_return']
        tt = sm.stats.ttest_ind(hi, lo, usevar='unequal')
        res['T3_2x2'][f'{lab}_ASHigh减ASLow'] = {
            'diff': round(float(hi.mean() - lo.mean()), 6),
            't': round(float(tt[0]), 2), 'p': round(float(tt[1]), 4)}

    (OUT / 'AS条件效应_2026-08-26.json').write_text(
        json.dumps(res, ensure_ascii=False, indent=1), encoding='utf-8')

    print('=== T1 AS × 行业集中度 交互项 ===')
    for k in ['T1_基金层交互', 'T1b_季度面板交互']:
        v = res[k]
        print(f'  [{k}] n={v["n"]} R2={v["r2"]}')
        for x in ['AS_c', 'ICI_c', 'AS_x_ICI']:
            c = v[x]
            print(f'    {x:10s} b={c["b"]:+.6f} t={c["t"]:+.2f} p={c["p"]}')

    print('\n=== T2 按行业集中度中位数分组，组内 AS 系数 ===')
    for k, v in res['T2_分组内AS'].items():
        print(f'  {k:10s} n={v["n"]:4d} b={v["b"]:+.6f} t={v["t"]:+.2f} p={v["p"]}')

    print('\n=== T3 2x2 分组 alpha 均值 ===')
    for k, v in res['T3_2x2'].items():
        if 'diff' in v:
            print(f'  {k:24s} 差={v["diff"]:+.6f} t={v["t"]:+.2f} p={v["p"]}')
        else:
            print(f'  {k:24s} n={v["n"]:4d} 均值={v["alpha_mean"]:.5f} '
                  f'中位={v["alpha_median"]:.5f}')


if __name__ == '__main__':
    main()
