# -*- coding: utf-8 -*-
"""
V3 正式回归（修正 DV 结构性缺陷）

诊断结论：面板列 ff5_adj_return 在基金内 100% 常数（362 只基金各仅 1 个取值），
它本质是**基金层 FF5 alpha**，不是逐季变量。直接用它跑季度面板回归会把
基金层常数向季度变量回归，等于人为把有效样本从 362 放大到近 3000，
t 值被机械放大 —— 这正是"AS 显著性多处不一致"的根源。

本脚本改用两个口径唯一的规格：
  规格 I  基金层横截面：DV = 基金层 FF5 alpha，RHS = 各指标基金内时序均值，N≈362，HC1
  规格 II 季度面板：DV = 逐季 FF5 残差（按基金做 FF5 时序回归取残差，≥12 季），
                  季度固定效应 + 基金聚类 SE

输出 output/主回归_v3_2026-08-26.json
"""
import json
import numpy as np
import pandas as pd
import statsmodels.api as sm
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_p1 = ROOT / 'output' / '主分析面板_重建_含TOwind.csv'
_p2 = ROOT / '指标计算流水线' / 'output' / '主分析面板_重建_含TOwind.csv'
PANEL = _p1 if _p1.exists() else (_p2 if _p2.exists() else ROOT / 'output' / '分析面板_v3_2026-08-26.csv')
V2 = ROOT / 'output' / '指标面板_v2_2026-08-26.csv'
OUT = ROOT / 'output'

FF5 = ['ff5_MKT_excess', 'ff5_SMB', 'ff5_HML', 'ff5_RMW', 'ff5_CMA']
CTRL = ['mgr_total_tenure_v2', 'log_fund_age', 'log_aum']

METRICS = {
    'L2认知': ['risk_asym', 'de', 'lsv', 'oc_conf'],
    'L3选择': ['AS_improved', 'ICI', 'ISDI'],
    'L4风险应对': ['ARG', 'return_volatility', 'rsstab_lag'],
    'L4b风险转化': ['sharpe8_lag', 'sortino8_lag', 'mppm8_lag'],
    'L5交易执行': ['SDI', 'TO_wind_clean'],
}
ALL_M = [x for v in METRICS.values() for x in v]


def winsor(s, p=0.01):
    s = pd.to_numeric(s, errors='coerce')
    return s.clip(s.quantile(p), s.quantile(1 - p))


def load():
    df = pd.read_csv(PANEL, parse_dates=['report_date'])
    v2 = pd.read_csv(V2, parse_dates=['report_date'])
    v2_cols = [c for c in ['sharpe8_lag', 'sortino8_lag', 'mppm8_lag', 'rsstab_lag', 'oc_conf'] if c in v2.columns]
    dup_cols = [c for c in v2_cols if c in df.columns]
    if dup_cols:
        df = df.drop(columns=dup_cols)
    df = df.merge(v2[['fund_code', 'report_date'] + v2_cols], on=['fund_code', 'report_date'], how='left')
    df['log_aum'] = np.log(df['avg_aum'].clip(lower=1))
    df['rf'] = df['rf'].fillna(0.0025)
    df['ex'] = df['quarter_return'] - df['rf']
    return df.sort_values(['fund_code', 'report_date']).reset_index(drop=True)


def build_quarterly_alpha(df):
    """按基金做 FF5 时序回归，残差即逐季风险调整收益（alpha_it）"""
    out = []
    for fc, g in df.groupby('fund_code'):
        gg = g.dropna(subset=['ex'] + FF5)
        if len(gg) < 12:
            continue
        X = sm.add_constant(gg[FF5].astype(float))
        m = sm.OLS(gg['ex'].astype(float), X).fit()
        out.append(pd.DataFrame({
            'fund_code': fc,
            'report_date': gg['report_date'].values,
            'alpha_q': (m.params['const'] + m.resid).values,
        }))
    res = pd.concat(out, ignore_index=True)
    return res


def reg_hc1(d, y, xs, extra=()):
    cols = [y] + list(xs) + list(extra)
    dd = d[cols].dropna().copy()
    if len(dd) < 40:
        return {'n': len(dd), 'note': 'insufficient'}
    dd[y] = winsor(dd[y])
    for x in xs:
        dd[x] = winsor(dd[x])
    X = sm.add_constant(dd[list(xs) + list(extra)].astype(float))
    m = sm.OLS(dd[y].astype(float), X).fit(cov_type='HC1')
    return {'n': int(len(dd)), 'r2': round(float(m.rsquared), 4),
            'coef': {x: {'b': round(float(m.params[x]), 6),
                         't': round(float(m.tvalues[x]), 2),
                         'p': round(float(m.pvalues[x]), 4)}
                     for x in list(xs) + list(extra)}}


def reg_panel(d, y, xs):
    cols = [y] + list(xs) + CTRL + ['fund_code', 'report_date']
    dd = d[cols].dropna().copy()
    if len(dd) < 60:
        return {'n': len(dd), 'note': 'insufficient'}
    dd[y] = winsor(dd[y])
    for x in xs:
        dd[x] = winsor(dd[x])
    X = dd[list(xs) + CTRL].astype(float)
    qd = pd.get_dummies(dd['report_date'].astype(str), prefix='q',
                        drop_first=True).astype(float)
    X = sm.add_constant(pd.concat([X.reset_index(drop=True),
                                   qd.reset_index(drop=True)], axis=1))
    m = sm.OLS(dd[y].astype(float).reset_index(drop=True), X).fit(
        cov_type='cluster', cov_kwds={'groups': dd['fund_code'].values})
    return {'n': int(len(dd)), 'nfund': int(dd['fund_code'].nunique()),
            'r2': round(float(m.rsquared), 4),
            'coef': {x: {'b': round(float(m.params[x]), 6),
                         't': round(float(m.tvalues[x]), 2),
                         'p': round(float(m.pvalues[x]), 4)}
                     for x in list(xs) + CTRL}}


def main():
    df = load()
    # Drop existing alpha_q columns to prevent _x/_y collision upon merge
    drop_cols = [c for c in df.columns if c == 'alpha_q' or c.startswith('alpha_q_')]
    if drop_cols:
        df = df.drop(columns=drop_cols)
    qa = build_quarterly_alpha(df)
    df = df.merge(qa, on=['fund_code', 'report_date'], how='left')
    df.to_csv(OUT / '分析面板_v3_2026-08-26.csv', index=False, encoding='utf-8-sig')

    # 基金层横截面数据集
    fm = df.groupby('fund_code').agg(
        **{c: (c, 'mean') for c in ALL_M + CTRL + ['ff5_adj_return', 'alpha_q',
                                                    'quarter_return']}).dropna(
        subset=['ff5_adj_return'])

    res = {'diag': {
        'ff5_adj_return_within_fund_constant': True,
        'n_fund_with_ff5_alpha': int(df.dropna(subset=['ff5_adj_return'])['fund_code'].nunique()),
        'quarterly_alpha_obs': int(df['alpha_q'].notna().sum()),
        'quarterly_alpha_funds': int(df.dropna(subset=['alpha_q'])['fund_code'].nunique()),
        'quarters': int(df['report_date'].nunique()),
    }}

    # ---- 规格 I：基金层横截面 ----
    spec1 = {'univariate': {}, 'full': None}
    for x in ALL_M:
        spec1['univariate'][x] = reg_hc1(fm, 'ff5_adj_return', [x], CTRL)
    spec1['full'] = reg_hc1(fm, 'ff5_adj_return', ALL_M, CTRL)
    # 去掉覆盖率低的 sortino8_lag/SDI 的紧凑版
    compact = [x for x in ALL_M if x not in ('sortino8_lag', 'sharpe8_lag')]
    spec1['compact'] = reg_hc1(fm, 'ff5_adj_return', compact, CTRL)
    res['spec1_cross_section'] = spec1

    # ---- 规格 II：季度面板，DV=alpha_q ----
    spec2 = {'univariate': {}, 'full': None}
    for x in ALL_M:
        spec2['univariate'][x] = reg_panel(df, 'alpha_q', [x])
    spec2['full'] = reg_panel(df, 'alpha_q', compact)
    res['spec2_panel'] = spec2

    # ---- AS 专项：五口径一次讲清 ----
    as_v = {}
    as_v['I_基金层横截面_单变量'] = reg_hc1(fm, 'ff5_adj_return', ['AS_improved'])
    as_v['I_基金层横截面_加控制'] = reg_hc1(fm, 'ff5_adj_return', ['AS_improved'], CTRL)
    as_v['I_基金层横截面_全模型'] = {'coef': {'AS_improved':
        spec1['full']['coef']['AS_improved']}, 'n': spec1['full']['n'],
        'r2': spec1['full']['r2']}
    as_v['II_季度面板_单变量'] = reg_panel(df, 'alpha_q', ['AS_improved'])
    as_v['II_季度面板_全模型'] = {'coef': {'AS_improved':
        spec2['full']['coef']['AS_improved']}, 'n': spec2['full']['n'],
        'r2': spec2['full']['r2']}
    res['AS_five_specs'] = as_v

    (OUT / '主回归_v3_2026-08-26.json').write_text(
        json.dumps(res, ensure_ascii=False, indent=1), encoding='utf-8')

    print('=== 诊断 ===')
    for k, v in res['diag'].items():
        print(f'  {k} = {v}')
    print(f'\n基金层横截面样本 N={len(fm)}')

    print('\n=== 规格 I 基金层横截面（DV=FF5 alpha, HC1）单指标 ===')
    for x in ALL_M:
        v = spec1['univariate'][x]
        if 'coef' in v:
            c = v['coef'][x]
            print(f'  {x:20s} n={v["n"]:4d} b={c["b"]:+.6f} t={c["t"]:+.2f} p={c["p"]}')
        else:
            print(f'  {x:20s} {v}')
    print(f'\n  全模型 n={spec1["full"]["n"]} r2={spec1["full"]["r2"]}')
    for x, c in spec1['full']['coef'].items():
        print(f'    {x:20s} b={c["b"]:+.6f} t={c["t"]:+.2f} p={c["p"]}')
    print(f'\n  紧凑模型 n={spec1["compact"]["n"]} r2={spec1["compact"]["r2"]}')
    for x, c in spec1['compact']['coef'].items():
        print(f'    {x:20s} b={c["b"]:+.6f} t={c["t"]:+.2f} p={c["p"]}')

    print('\n=== 规格 II 季度面板（DV=逐季 FF5 残差, 季度FE+基金聚类）单指标 ===')
    for x in ALL_M:
        v = spec2['univariate'][x]
        if 'coef' in v:
            c = v['coef'][x]
            print(f'  {x:20s} n={v["n"]:5d} nf={v["nfund"]:4d} b={c["b"]:+.6f} t={c["t"]:+.2f} p={c["p"]}')
        else:
            print(f'  {x:20s} {v}')
    print(f'\n  全模型 n={spec2["full"]["n"]} nf={spec2["full"]["nfund"]} r2={spec2["full"]["r2"]}')
    for x, c in spec2['full']['coef'].items():
        print(f'    {x:20s} b={c["b"]:+.6f} t={c["t"]:+.2f} p={c["p"]}')

    print('\n=== AS 五口径 ===')
    for k, v in as_v.items():
        c = v['coef']['AS_improved']
        print(f'  {k:22s} n={v["n"]:5d} b={c["b"]:+.6f} t={c["t"]:+.2f} p={c["p"]}')


if __name__ == '__main__':
    main()
