# -*- coding: utf-8 -*-
"""
改进主动份额（AS_improved）显著性专项裁决

背景：v3 回归中 AS 在五个口径下符号与显著性摇摆
  I  基金层横截面 单变量  t=-0.26 ns
  I  基金层横截面 加控制  t=-0.65 ns
  I  基金层横截面 全模型  t=-3.06 **
  II 季度面板   单变量  t=+5.33 ***
  II 季度面板   全模型  t=-1.41 ns

本脚本的目的不是再多跑一个规格，而是找出摇摆的机制，从而给出唯一结论。
四步诊断：
  Step1 相关结构：AS 与其余指标的相关系数 + 全模型 VIF
  Step2 逐步加入：AS -> +控制 -> +ICI -> +ICI/ISDI -> 全模型，观察系数迁移路径
  Step3 分组检验：按 AS 五分位分组比较 FF5 alpha（Cremers & Petajisto 2009 原文做法）
  Step4 非线性与子样本：AS + AS^2；2020 年后子样本

输出 output/AS专项裁决_2026-08-26.json
"""
import json
import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.stats.outliers_influence import variance_inflation_factor
from pathlib import Path
import sys, io
if hasattr(sys.stdout, 'buffer') and getattr(sys.stdout, 'encoding', '').lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'buffer') and getattr(sys.stderr, 'encoding', '').lower() != 'utf-8':
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')


ROOT = Path(__file__).resolve().parents[1]
_v3_0 = ROOT / '原始数据' / '分析面板' / '分析面板_v3_2026-08-26.csv'
V3 = _v3_0 if _v3_0.exists() else ROOT / 'output' / '分析面板_v3_2026-08-26.csv'
OUT = ROOT / 'output'
OUT.mkdir(exist_ok=True)

CTRL = ['mgr_total_tenure_v2', 'log_fund_age', 'log_aum']
ALL_M = ['risk_asym', 'de', 'lsv', 'oc_conf', 'AS_improved', 'ICI', 'ISDI',
         'ARG', 'return_volatility', 'rsstab_lag', 'mppm8_lag', 'SDI',
         'TO_wind_clean']


def winsor(s, p=0.01):
    s = pd.to_numeric(s, errors='coerce')
    return s.clip(s.quantile(p), s.quantile(1 - p))


def reg_hc1(d, y, xs):
    dd = d[[y] + list(xs)].dropna().copy()
    if len(dd) < 40:
        return {'n': len(dd), 'note': 'insufficient'}
    dd[y] = winsor(dd[y])
    for x in xs:
        dd[x] = winsor(dd[x])
    X = sm.add_constant(dd[list(xs)].astype(float))
    m = sm.OLS(dd[y].astype(float), X).fit(cov_type='HC1')
    return {'n': int(len(dd)), 'r2': round(float(m.rsquared), 4),
            'coef': {x: {'b': round(float(m.params[x]), 6),
                         't': round(float(m.tvalues[x]), 2),
                         'p': round(float(m.pvalues[x]), 4)} for x in xs}}


def reg_panel(d, y, xs, ctrl=True):
    cols = [y] + list(xs) + (CTRL if ctrl else []) + ['fund_code', 'report_date']
    dd = d[cols].dropna().copy()
    if len(dd) < 60:
        return {'n': len(dd), 'note': 'insufficient'}
    dd[y] = winsor(dd[y])
    for x in xs:
        dd[x] = winsor(dd[x])
    rhs = list(xs) + (CTRL if ctrl else [])
    X = dd[rhs].astype(float).reset_index(drop=True)
    qd = pd.get_dummies(dd['report_date'].astype(str), prefix='q',
                        drop_first=True).astype(float).reset_index(drop=True)
    X = sm.add_constant(pd.concat([X, qd], axis=1))
    m = sm.OLS(dd[y].astype(float).reset_index(drop=True), X).fit(
        cov_type='cluster', cov_kwds={'groups': dd['fund_code'].values})
    return {'n': int(len(dd)), 'nfund': int(dd['fund_code'].nunique()),
            'r2': round(float(m.rsquared), 4),
            'coef': {x: {'b': round(float(m.params[x]), 6),
                         't': round(float(m.tvalues[x]), 2),
                         'p': round(float(m.pvalues[x]), 4)} for x in xs}}


def main():
    df = pd.read_csv(V3, parse_dates=['report_date'])
    if 'alpha_q' not in df.columns and 'alpha_q_x' in df.columns:
        df['alpha_q'] = df['alpha_q_x']
    df['year'] = df['report_date'].dt.year
    fm = df.groupby('fund_code')[ALL_M + CTRL + ['ff5_adj_return', 'alpha_q']
                                 ].mean().dropna(subset=['ff5_adj_return'])

    res = {}

    # ---- Step1 相关结构 ----
    corr_f = fm[ALL_M].corr()['AS_improved'].drop('AS_improved')
    corr_q = df[ALL_M].corr()['AS_improved'].drop('AS_improved')
    res['step1_corr'] = {
        'fund_level': {k: round(float(v), 3) for k, v in corr_f.items()},
        'quarter_level': {k: round(float(v), 3) for k, v in corr_q.items()},
    }
    vd = fm[ALL_M + CTRL].dropna()
    Xv = sm.add_constant(vd.astype(float))
    res['step1_vif'] = {c: round(float(variance_inflation_factor(Xv.values, i)), 2)
                        for i, c in enumerate(Xv.columns) if c != 'const'}

    # ---- Step2 逐步加入 ----
    steps = {
        '1_AS单变量': ['AS_improved'],
        '2_加基础控制': ['AS_improved'] + CTRL,
        '3_加行业集中度ICI': ['AS_improved', 'ICI'] + CTRL,
        '4_加ICI+ISDI': ['AS_improved', 'ICI', 'ISDI'] + CTRL,
        '5_加风险转化mppm': ['AS_improved', 'ICI', 'ISDI', 'mppm8_lag'] + CTRL,
        '6_全模型': ALL_M + CTRL,
    }
    res['step2_sequential_specI'] = {}
    res['step2_sequential_specII'] = {}
    for k, xs in steps.items():
        r1 = reg_hc1(fm, 'ff5_adj_return', xs)
        r2 = reg_panel(df, 'alpha_q', [x for x in xs if x not in CTRL])
        res['step2_sequential_specI'][k] = {
            'n': r1['n'], 'r2': r1.get('r2'),
            'AS': r1['coef']['AS_improved'] if 'coef' in r1 else None}
        res['step2_sequential_specII'][k] = {
            'n': r2['n'], 'nfund': r2.get('nfund'), 'r2': r2.get('r2'),
            'AS': r2['coef']['AS_improved'] if 'coef' in r2 else None}

    # ---- Step3 五分位分组（Cremers & Petajisto 2009 做法）----
    q = fm.dropna(subset=['AS_improved', 'ff5_adj_return']).copy()
    q['grp'] = pd.qcut(q['AS_improved'], 5, labels=['Q1最低', 'Q2', 'Q3', 'Q4', 'Q5最高'])
    tab = q.groupby('grp', observed=True).agg(
        n=('ff5_adj_return', 'size'),
        AS_mean=('AS_improved', 'mean'),
        alpha_mean=('ff5_adj_return', 'mean'),
        alpha_median=('ff5_adj_return', 'median'),
        alpha_std=('ff5_adj_return', 'std'))
    res['step3_quintile'] = {str(i): {k: round(float(v), 6) for k, v in r.items()}
                             for i, r in tab.iterrows()}
    hi = q[q['grp'] == 'Q5最高']['ff5_adj_return']
    lo = q[q['grp'] == 'Q1最低']['ff5_adj_return']
    tt = sm.stats.ttest_ind(hi, lo, usevar='unequal')
    res['step3_Q5_minus_Q1'] = {'diff': round(float(hi.mean() - lo.mean()), 6),
                                't': round(float(tt[0]), 2),
                                'p': round(float(tt[1]), 4)}

    # ---- Step4 非线性与子样本 ----
    fm2 = fm.copy()
    fm2['AS_sq'] = fm2['AS_improved'] ** 2
    res['step4_nonlinear_specI'] = reg_hc1(
        fm2, 'ff5_adj_return', ['AS_improved', 'AS_sq'] + CTRL)

    sub = df[df['year'] >= 2020]
    fsub = sub.groupby('fund_code')[ALL_M + CTRL + ['ff5_adj_return', 'alpha_q']
                                    ].mean().dropna(subset=['ff5_adj_return'])
    res['step4_sub2020_specI_univ'] = reg_hc1(
        fsub, 'ff5_adj_return', ['AS_improved'] + CTRL)
    res['step4_sub2020_specI_full'] = reg_hc1(fsub, 'ff5_adj_return', ALL_M + CTRL)
    res['step4_sub2020_specII_univ'] = reg_panel(sub, 'alpha_q', ['AS_improved'])
    res['step4_sub2020_specII_full'] = reg_panel(sub, 'alpha_q', ALL_M)

    (OUT / 'AS专项裁决_2026-08-26.json').write_text(
        json.dumps(res, ensure_ascii=False, indent=1), encoding='utf-8')

    # ---- 打印 ----
    print('=== Step1 AS 与其他指标相关系数 ===')
    print('  [基金层]')
    for k, v in sorted(res['step1_corr']['fund_level'].items(),
                       key=lambda x: -abs(x[1])):
        print(f'    {k:20s} {v:+.3f}')
    print('  [季度层]')
    for k, v in sorted(res['step1_corr']['quarter_level'].items(),
                       key=lambda x: -abs(x[1]))[:6]:
        print(f'    {k:20s} {v:+.3f}')
    print('  [全模型 VIF]')
    for k, v in sorted(res['step1_vif'].items(), key=lambda x: -x[1])[:6]:
        print(f'    {k:20s} {v}')

    print('\n=== Step2 逐步加入：AS 系数迁移路径 ===')
    print('  规格 I 基金层横截面（DV=FF5 alpha）')
    for k, v in res['step2_sequential_specI'].items():
        a = v['AS']
        print(f'    {k:18s} n={v["n"]:4d} R2={v["r2"]:.4f} '
              f'b={a["b"]:+.6f} t={a["t"]:+.2f} p={a["p"]}')
    print('  规格 II 季度面板（DV=逐季 alpha）')
    for k, v in res['step2_sequential_specII'].items():
        a = v['AS']
        print(f'    {k:18s} n={v["n"]:5d} R2={v["r2"]:.4f} '
              f'b={a["b"]:+.6f} t={a["t"]:+.2f} p={a["p"]}')

    print('\n=== Step3 AS 五分位分组的 FF5 alpha ===')
    print(f'  {"组":8s} {"n":>4s} {"AS均值":>8s} {"alpha均值":>10s} {"alpha中位":>10s}')
    for k, v in res['step3_quintile'].items():
        print(f'  {k:8s} {int(v["n"]):4d} {v["AS_mean"]:8.4f} '
              f'{v["alpha_mean"]:10.5f} {v["alpha_median"]:10.5f}')
    d = res['step3_Q5_minus_Q1']
    print(f'  Q5-Q1 差={d["diff"]:+.6f} t={d["t"]:+.2f} p={d["p"]}')

    print('\n=== Step4 非线性（AS + AS^2）===')
    for x in ['AS_improved', 'AS_sq']:
        c = res['step4_nonlinear_specI']['coef'][x]
        print(f'  {x:14s} b={c["b"]:+.6f} t={c["t"]:+.2f} p={c["p"]}')

    print('\n=== Step4 2020 年后子样本 ===')
    for key in ['step4_sub2020_specI_univ', 'step4_sub2020_specI_full',
                'step4_sub2020_specII_univ', 'step4_sub2020_specII_full']:
        r = res[key]
        if 'coef' in r:
            c = r['coef']['AS_improved']
            print(f'  {key:30s} n={r["n"]:5d} b={c["b"]:+.6f} '
                  f't={c["t"]:+.2f} p={c["p"]}')


if __name__ == '__main__':
    main()
