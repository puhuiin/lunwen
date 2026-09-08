# -*- coding: utf-8 -*-
"""
AS 非线性（U 型）稳健性验证 —— 决定能否写入报告

Step4 在基金层横截面发现 AS 一次项 -0.662***、二次项 +0.431***（U 型，顶点 0.768）。
本脚本检验该形态在以下条件下是否稳健：
  A 季度面板（DV=alpha_q，季度FE+基金聚类）
  B 2020 年后子样本
  C 加入全部控制指标后
  D 十分位非参数曲线（不依赖二次式假设）
  E 顶点位置的 Delta 法置信区间

输出 output/AS非线性验证_2026-08-26.json
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
ALL_M = ['risk_asym', 'de', 'lsv', 'oc_conf', 'AS_improved', 'ICI', 'ISDI',
         'ARG', 'return_volatility', 'rsstab_lag', 'mppm8_lag', 'SDI',
         'TO_wind_clean']


def winsor(s, p=0.01):
    s = pd.to_numeric(s, errors='coerce')
    return s.clip(s.quantile(p), s.quantile(1 - p))


def fit_hc1(d, y, xs):
    dd = d[[y] + xs].dropna().copy()
    dd[y] = winsor(dd[y])
    for x in xs:
        if x != 'AS_sq':
            dd[x] = winsor(dd[x])
    X = sm.add_constant(dd[xs].astype(float))
    return sm.OLS(dd[y].astype(float), X).fit(cov_type='HC1'), len(dd)


def fit_panel(d, y, xs):
    cols = [y] + xs + CTRL + ['fund_code', 'report_date']
    dd = d[cols].dropna().copy()
    dd[y] = winsor(dd[y])
    for x in xs:
        if x != 'AS_sq':
            dd[x] = winsor(dd[x])
    X = dd[xs + CTRL].astype(float).reset_index(drop=True)
    qd = pd.get_dummies(dd['report_date'].astype(str), prefix='q',
                        drop_first=True).astype(float).reset_index(drop=True)
    X = sm.add_constant(pd.concat([X, qd], axis=1))
    m = sm.OLS(dd[y].astype(float).reset_index(drop=True), X).fit(
        cov_type='cluster', cov_kwds={'groups': dd['fund_code'].values})
    return m, len(dd), dd['fund_code'].nunique()


def vertex(m):
    """U 型顶点 = -b1/(2*b2)，Delta 法求标准误"""
    b1 = float(m.params['AS_improved'])
    b2 = float(m.params['AS_sq'])
    v = -b1 / (2 * b2)
    V = m.cov_params().loc[['AS_improved', 'AS_sq'], ['AS_improved', 'AS_sq']].values
    g = np.array([-1 / (2 * b2), b1 / (2 * b2 ** 2)])
    se = float(np.sqrt(g @ V @ g))
    return round(v, 4), round(se, 4), (round(v - 1.96 * se, 4), round(v + 1.96 * se, 4))


def pack(m, n, nf=None):
    out = {'n': int(n), 'r2': round(float(m.rsquared), 4)}
    if nf is not None:
        out['nfund'] = int(nf)
    for x in ['AS_improved', 'AS_sq']:
        out[x] = {'b': round(float(m.params[x]), 6),
                  't': round(float(m.tvalues[x]), 2),
                  'p': round(float(m.pvalues[x]), 4)}
    v, se, ci = vertex(m)
    out['vertex'] = {'value': v, 'se': se, 'ci95': list(ci)}
    return out


def main():
    df = pd.read_csv(V3, parse_dates=['report_date'])
    df['year'] = df['report_date'].dt.year
    df['AS_sq'] = df['AS_improved'] ** 2
    fm = df.groupby('fund_code')[ALL_M + CTRL + ['ff5_adj_return', 'alpha_q']
                                 ].mean().dropna(subset=['ff5_adj_return'])
    fm['AS_sq'] = fm['AS_improved'] ** 2

    res = {}

    # A 基金层：基准（对照 Step4）
    m, n = fit_hc1(fm, 'ff5_adj_return', ['AS_improved', 'AS_sq'] + CTRL)
    res['A_基金层_仅控制'] = pack(m, n)

    # C 基金层：加全部指标控制
    others = [x for x in ALL_M if x != 'AS_improved']
    m, n = fit_hc1(fm, 'ff5_adj_return', ['AS_improved', 'AS_sq'] + others + CTRL)
    res['C_基金层_全指标控制'] = pack(m, n)

    # A2 季度面板
    m, n, nf = fit_panel(df, 'alpha_q', ['AS_improved', 'AS_sq'])
    res['A2_季度面板_仅控制'] = pack(m, n, nf)
    m, n, nf = fit_panel(df, 'alpha_q', ['AS_improved', 'AS_sq'] + others)
    res['C2_季度面板_全指标控制'] = pack(m, n, nf)

    # B 2020 后子样本
    sub = df[df['year'] >= 2020]
    fsub = sub.groupby('fund_code')[ALL_M + CTRL + ['ff5_adj_return']
                                    ].mean().dropna(subset=['ff5_adj_return'])
    fsub['AS_sq'] = fsub['AS_improved'] ** 2
    m, n = fit_hc1(fsub, 'ff5_adj_return', ['AS_improved', 'AS_sq'] + CTRL)
    res['B_基金层_2020后'] = pack(m, n)
    m, n, nf = fit_panel(sub, 'alpha_q', ['AS_improved', 'AS_sq'])
    res['B2_季度面板_2020后'] = pack(m, n, nf)

    # D 十分位非参数曲线
    q = fm.dropna(subset=['AS_improved', 'ff5_adj_return']).copy()
    q['d10'] = pd.qcut(q['AS_improved'], 10, labels=False) + 1
    dec = q.groupby('d10').agg(n=('ff5_adj_return', 'size'),
                               AS=('AS_improved', 'mean'),
                               alpha=('ff5_adj_return', 'mean'),
                               alpha_med=('ff5_adj_return', 'median'))
    res['D_十分位曲线'] = {int(i): {k: round(float(v), 6) for k, v in r.items()}
                       for i, r in dec.iterrows()}

    # 中段 vs 两端（U 型的直接检验）
    mid = q[q['d10'].isin([4, 5, 6, 7])]['ff5_adj_return']
    ends = q[q['d10'].isin([1, 2, 9, 10])]['ff5_adj_return']
    tt = sm.stats.ttest_ind(ends, mid, usevar='unequal')
    res['D_两端减中段'] = {'ends_mean': round(float(ends.mean()), 6),
                       'mid_mean': round(float(mid.mean()), 6),
                       'diff': round(float(ends.mean() - mid.mean()), 6),
                       't': round(float(tt[0]), 2), 'p': round(float(tt[1]), 4)}

    (OUT / 'AS非线性验证_2026-08-26.json').write_text(
        json.dumps(res, ensure_ascii=False, indent=1), encoding='utf-8')

    print('=== AS 二次项在各规格下的表现 ===')
    print(f'{"规格":24s} {"n":>6s} {"一次项t":>8s} {"二次项t":>8s} {"顶点":>8s} {"顶点95%CI":>20s}')
    for k, v in res.items():
        if not k[0].isalpha() or 'AS_sq' not in v:
            continue
        ci = v['vertex']['ci95']
        print(f'{k:24s} {v["n"]:6d} {v["AS_improved"]["t"]:+8.2f} '
              f'{v["AS_sq"]["t"]:+8.2f} {v["vertex"]["value"]:8.4f} '
              f'[{ci[0]:.3f}, {ci[1]:.3f}]')

    print('\n=== 十分位非参数曲线（DV=基金层 FF5 alpha）===')
    print(f'  {"十分位":>6s} {"n":>4s} {"AS均值":>8s} {"alpha均值":>10s} {"alpha中位":>10s}')
    for k, v in res['D_十分位曲线'].items():
        print(f'  {k:6d} {int(v["n"]):4d} {v["AS"]:8.4f} '
              f'{v["alpha"]:10.5f} {v["alpha_med"]:10.5f}')
    d = res['D_两端减中段']
    print(f'  两端(D1,2,9,10)={d["ends_mean"]:.5f}  中段(D4-7)={d["mid_mean"]:.5f}  '
          f'差={d["diff"]:+.5f} t={d["t"]:+.2f} p={d["p"]}')


if __name__ == '__main__':
    main()
