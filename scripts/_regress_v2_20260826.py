# -*- coding: utf-8 -*-
"""
V2 主回归：五层 17→19 项指标统一表 + AS 三口径统一裁决
DV = ff5_adj_return（1% winsorize），基金聚类 SE，年度固定效应
输出 output/主回归_v2_2026-08-26.json
"""
import json
import numpy as np
import pandas as pd
import statsmodels.api as sm
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PANEL = ROOT / '指标计算流水线' / 'output' / '主分析面板_重建_含TOwind.csv'
V2 = ROOT / 'output' / '指标面板_v2_2026-08-26.csv'
OUT = ROOT / 'output'

CTRL = ['mgr_total_tenure_v2', 'log_fund_age', 'log_aum']


def winsor(s, p=0.01):
    lo, hi = s.quantile(p), s.quantile(1 - p)
    return s.clip(lo, hi)


def reg(d, y, xs, label):
    cols = [y] + xs + CTRL + ['fund_code', 'year']
    dd = d[cols].dropna().copy()
    if len(dd) < 60:
        return {'label': label, 'n': len(dd), 'note': 'insufficient'}
    dd[y] = winsor(dd[y])
    for x in xs:
        dd[x] = winsor(dd[x])
    X = dd[xs + CTRL].copy()
    yr = pd.get_dummies(dd['year'].astype(int), prefix='y', drop_first=True).astype(float)
    X = pd.concat([X, yr.set_index(X.index)], axis=1)
    X = sm.add_constant(X)
    m = sm.OLS(dd[y].astype(float), X.astype(float)).fit(
        cov_type='cluster', cov_kwds={'groups': dd['fund_code']})
    res = {'label': label, 'n': int(len(dd)), 'nfund': int(dd['fund_code'].nunique()),
           'r2': round(float(m.rsquared), 4), 'coef': {}}
    for x in xs + CTRL:
        res['coef'][x] = {'b': round(float(m.params[x]), 6),
                          't': round(float(m.tvalues[x]), 2),
                          'p': round(float(m.pvalues[x]), 4)}
    return res


def main():
    df = pd.read_csv(PANEL, parse_dates=['report_date'])
    v2 = pd.read_csv(V2, parse_dates=['report_date'])
    df = df.merge(v2, on=['fund_code', 'report_date'], how='left')
    df['log_aum'] = np.log(df['avg_aum'].clip(lower=1))
    df = df.sort_values(['fund_code', 'report_date'])

    out = {}
    Y = 'ff5_adj_return'

    # ---------- 1. AS 三口径统一裁决 ----------
    as_specs = {
        'A_单变量_无控制': ['AS_improved'],
        'B_加控制变量': ['AS_improved'],
        'C_全模型_五层同入': ['AS_improved', 'risk_asym', 'de', 'lsv', 'ICI', 'ISDI',
                          'ARG', 'return_volatility', 'TO_wind_clean'],
        'D_全模型_加新指标': ['AS_improved', 'risk_asym', 'de', 'lsv', 'ICI', 'ISDI',
                         'ARG', 'return_volatility', 'TO_wind_clean',
                         'oc_conf', 'mppm8_lag', 'rsstab_lag'],
    }
    as_res = {}
    for k, xs in as_specs.items():
        if k == 'A_单变量_无控制':
            dd = df[[Y, 'AS_improved', 'fund_code']].dropna().copy()
            dd[Y] = winsor(dd[Y])
            X = sm.add_constant(dd[['AS_improved']].astype(float))
            m = sm.OLS(dd[Y].astype(float), X).fit(
                cov_type='cluster', cov_kwds={'groups': dd['fund_code']})
            as_res[k] = {'n': int(len(dd)), 'r2': round(float(m.rsquared), 4),
                         'coef': {'AS_improved': {
                             'b': round(float(m.params['AS_improved']), 6),
                             't': round(float(m.tvalues['AS_improved']), 2),
                             'p': round(float(m.pvalues['AS_improved']), 4)}}}
        else:
            as_res[k] = reg(df, Y, xs, k)
    # 补：基金层横截面（时序均值）
    fm = df.groupby('fund_code')[[Y, 'AS_improved'] + CTRL].mean().dropna()
    X = sm.add_constant(fm[['AS_improved'] + CTRL].astype(float))
    m = sm.OLS(winsor(fm[Y]).astype(float), X).fit(cov_type='HC1')
    as_res['E_基金层横截面'] = {'n': int(len(fm)), 'r2': round(float(m.rsquared), 4),
                          'coef': {'AS_improved': {
                              'b': round(float(m.params['AS_improved']), 6),
                              't': round(float(m.tvalues['AS_improved']), 2),
                              'p': round(float(m.pvalues['AS_improved']), 4)}}}
    out['AS_verdict'] = as_res

    # ---------- 2. 分层逐指标（单指标 + 控制变量） ----------
    layers = {
        'L2认知': ['risk_asym', 'de', 'lsv', 'oc_conf'],
        'L3选择': ['AS_improved', 'ICI', 'industry_hhi', 'ISDI'],
        'L4风险应对': ['ARG', 'return_volatility', 'rsstab_lag'],
        'L4b风险转化': ['sharpe8_lag', 'sortino8_lag', 'mppm8_lag'],
        'L5交易执行': ['SDI', 'TO_wind_clean', 'OCI_two_sided'],
    }
    uni = {}
    for lay, xs in layers.items():
        for x in xs:
            uni[x] = reg(df, Y, [x], f'{lay}|{x}')
    out['univariate'] = uni

    # ---------- 3. 全模型（19 项同入，能进的都进） ----------
    full_x = ['risk_asym', 'de', 'lsv', 'oc_conf', 'AS_improved', 'ICI', 'ISDI',
              'ARG', 'return_volatility', 'rsstab_lag', 'mppm8_lag', 'TO_wind_clean']
    out['full_model'] = reg(df, Y, full_x, 'full_19')

    # ---------- 4. 未来一期业绩（前瞻检验） ----------
    df['fwd'] = df.groupby('fund_code')['ff5_adj_return'].shift(-1)
    fwd_x = ['risk_asym', 'de', 'lsv', 'oc_conf', 'AS_improved', 'ICI', 'ISDI',
             'ARG', 'return_volatility', 'rsstab_lag', 'mppm8_lag', 'TO_wind_clean']
    out['forward_model'] = reg(df, 'fwd', fwd_x, 'forward_next_quarter')

    (OUT / '主回归_v2_2026-08-26.json').write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')

    print('=== AS 三口径 ===')
    for k, v in as_res.items():
        c = v.get('coef', {}).get('AS_improved')
        print(f"{k:22s} n={v.get('n')} b={c['b']:+.4f} t={c['t']:+.2f} p={c['p']}")
    print('\n=== 单指标（+控制） ===')
    for k, v in uni.items():
        if 'coef' in v:
            c = v['coef'][k]
            print(f"{v['label']:26s} n={v['n']:5d} b={c['b']:+.6f} t={c['t']:+.2f} p={c['p']}")
    print('\n=== 全模型 ===')
    fmres = out['full_model']
    print(f"n={fmres['n']} nfund={fmres['nfund']} r2={fmres['r2']}")
    for k, c in fmres['coef'].items():
        print(f"  {k:22s} b={c['b']:+.6f} t={c['t']:+.2f} p={c['p']}")
    print('\n=== 前瞻模型 ===')
    fw = out['forward_model']
    print(f"n={fw['n']} r2={fw['r2']}")
    for k, c in fw['coef'].items():
        print(f"  {k:22s} b={c['b']:+.6f} t={c['t']:+.2f} p={c['p']}")


if __name__ == '__main__':
    main()
