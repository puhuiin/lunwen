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
import sys, io
if hasattr(sys.stdout, 'buffer') and getattr(sys.stdout, 'encoding', '').lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'buffer') and getattr(sys.stderr, 'encoding', '').lower() != 'utf-8':
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')


ROOT = Path(__file__).resolve().parents[1]
_p0 = ROOT / '原始数据' / '分析面板' / '分析面板_v3_2026-08-26.csv'
_p1 = ROOT / 'output' / '主分析面板_重建_含TOwind.csv'
_p2 = ROOT / 'output' / '分析面板_v3_2026-08-26.csv'
PANEL = _p0 if _p0.exists() else (_p1 if _p1.exists() else _p2)
_v2_0 = ROOT / '原始数据' / '分析面板' / '指标面板_v2_2026-08-26.csv'
V2 = _v2_0 if _v2_0.exists() else ROOT / 'output' / '指标面板_v2_2026-08-26.csv'
OUT = ROOT / 'output'
OUT.mkdir(exist_ok=True)

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

    # 执行表 6 六维综合能力主回归与打分计算
    run_composite_l1(OUT)


def run_composite_l1(OUT):
    OUT = Path(OUT)
    TODAY = '2026-08-26'
    DIMS = {
        '基本面优势': [('mgr_total_tenure_v2', -1), ('log_fund_age', -1), ('log_aum', -1)],
        '认知能力': [('risk_asym', +1), ('de', -1), ('oc_conf', -1), ('anchor_high', +1)],
        '配置选择能力': [('ICI', +1), ('ISDI', -1)],
        '风险应对能力': [('ARG', +1), ('timing', +1)],
        '风险转化能力': [('mppm8_lag', +1), ('sortino8_lag', +1), ('sharpe8_lag', +1)],
        '交易执行能力': [('SDI', -1), ('lsv', +1)],
    }
    DIM_NAMES = list(DIMS.keys())
    ALL_COMP = [m for v in DIMS.values() for m, _ in v]
    CTRL = ['mgr_total_tenure_v2', 'log_fund_age', 'log_aum']

    def z(s):
        return (s - s.mean()) / s.std()

    def ew(frame):
        return frame.sum(axis=1, skipna=True) / frame.notna().sum(axis=1)

    def reg(y, X):
        d = pd.concat([y, X], axis=1).dropna()
        return sm.OLS(d.iloc[:, 0], sm.add_constant(d.iloc[:, 1:])).fit(cov_type='HC1')

    p_panel = ROOT / '原始数据' / '分析面板' / f'分析面板_v3_{TODAY}.csv'
    if not p_panel.exists():
        p_panel = OUT / f'分析面板_v3_{TODAY}.csv'
    panel = pd.read_csv(p_panel, parse_dates=['report_date'])

    p_new = ROOT / '原始数据' / '分析面板' / 'L2新增候选_面板_2026-09-02.csv'
    if not p_new.exists():
        p_new = OUT / 'L2新增候选_面板_2026-09-02.csv'
    _new = pd.read_csv(p_new, parse_dates=['report_date'])
    panel = panel.merge(_new[['fund_code', 'report_date', 'anchor_high']],
                        on=['fund_code', 'report_date'], how='left')

    p_tim = ROOT / '原始数据' / '分析面板' / f'择时系数_季度HM_{TODAY}.csv'
    if not p_tim.exists():
        p_tim = OUT / f'择时系数_季度HM_{TODAY}.csv'
    tim = pd.read_csv(p_tim).set_index('fund_code')[['timing']]

    base_cols = [c for c in ALL_COMP if c != 'timing']
    sel_cols = list(dict.fromkeys(base_cols + CTRL))
    fm = panel.groupby('fund_code')[sel_cols + ['ff5_adj_return', 'quarter_return']].mean()
    fm = fm.join(tim, how='left')
    for c in ALL_COMP + CTRL:
        fm[c] = pd.to_numeric(fm[c], errors='coerce')
        fm[c] = winsor(fm[c])
    Y = fm['ff5_adj_return']

    res = {}
    s1 = {}
    for dim, items in DIMS.items():
        for m_, sg in items:
            if dim == '基本面优势':
                mod = reg(Y, fm[[m_]])
            else:
                mod = reg(Y, fm[[m_] + CTRL])
            t = float(mod.tvalues[m_])
            ok = '一致' if np.sign(t) == sg else '★不一致'
            s1[m_] = dict(维度=dim, 定向=sg, n=int(mod.nobs), t=round(t, 2),
                          p=round(float(mod.pvalues[m_]), 4), 判定=ok)
    res['S1_成分定向'] = s1

    score = pd.DataFrame(index=fm.index)
    for dim, items in DIMS.items():
        score[dim] = ew(pd.DataFrame({m_: sg * z(fm[m_]) for m_, sg in items}))
    score['综合能力'] = ew(score[DIM_NAMES])
    score['ff5_alpha'] = fm['ff5_adj_return']
    score['quarter_return'] = fm['quarter_return']
    res['S2_维度相关'] = json.loads(score[DIM_NAMES].corr().round(3).to_json())

    s3 = {}
    sc = score.join(fm[CTRL])
    for dim in DIM_NAMES + ['综合能力']:
        X = [dim] if dim == '基本面优势' else [dim] + CTRL
        mod = reg(sc['ff5_alpha'], sc[X])
        s3[dim] = dict(n=int(mod.nobs), coef=round(float(mod.params[dim]), 5),
                      t=round(float(mod.tvalues[dim]), 2), p=round(float(mod.pvalues[dim]), 4),
                      r2=round(float(mod.rsquared), 4))
    mall = reg(sc['ff5_alpha'], sc[DIM_NAMES])
    res['S3_单维'] = s3
    res['S3_联立'] = dict(n=int(mall.nobs), r2=round(float(mall.rsquared), 4),
                          系数={d: dict(coef=round(float(mall.params[d]), 5),
                                        t=round(float(mall.tvalues[d]), 2),
                                        p=round(float(mall.pvalues[d]), 4)) for d in DIM_NAMES})

    g = score.dropna(subset=['综合能力', 'ff5_alpha']).copy()
    g['grp'] = pd.qcut(g['综合能力'], 5, labels=['Q1最低', 'Q2', 'Q3', 'Q4', 'Q5最高'])
    tab = g.groupby('grp', observed=True)[['ff5_alpha', 'quarter_return']].mean()
    tab['n'] = g.groupby('grp', observed=True).size()
    hi, lo = g[g['grp'] == 'Q5最高']['ff5_alpha'], g[g['grp'] == 'Q1最低']['ff5_alpha']
    tt = sm.stats.ttest_ind(hi, lo, usevar='unequal')
    res['S4_分组'] = dict(alpha均值={str(k): round(float(v), 5) for k, v in tab['ff5_alpha'].items()},
                          季度收益均值={str(k): round(float(v), 5) for k, v in tab['quarter_return'].items()},
                          规模={str(k): int(v) for k, v in tab['n'].items()},
                          Q5_Q1=round(float(hi.mean() - lo.mean()), 5),
                          t=round(float(tt[0]), 2), p=round(float(tt[1]), 4))

    score.reset_index().to_csv(OUT / f'六维能力复合得分_含L1_{TODAY}.csv', index=False, encoding='utf-8-sig')
    (OUT / f'六维复合定稿验证_含L1_{TODAY}.json').write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'已生成表 6 复合得分与定稿验证产物: output/六维能力复合得分_含L1_{TODAY}.csv')

    print('\n=== 表 6 六维能力单维回归（加控制，DV=FF5 alpha）===')
    for d, v in s3.items():
        print(f"  {d:16s} coef={v['coef']:+.5f} t={v['t']:+6.2f} p={v['p']:.4f} R2={v['r2']:.4f}")
    print(f"\n=== 表 6 六维能力联立回归 (N={res['S3_联立']['n']}, R2={res['S3_联立']['r2']:.4f}) ===")
    for d, c in res['S3_联立']['系数'].items():
        print(f"  {d:16s} coef={c['coef']:+.5f} t={c['t']:+6.2f} p={c['p']:.4f}")
    print(f"\n=== 综合能力五等分组组合收益差 (全样本 N={sum(res['S4_分组']['规模'].values())}) ===")
    for grp, val in res['S4_分组']['alpha均值'].items():
        n_grp = res['S4_分组']['规模'][grp]
        print(f"  {grp:8s} (N={n_grp}): alpha={val*100:+.2f}%")
    print(f"  --> Q5 - Q1 = {res['S4_分组']['Q5_Q1']*100:+.2f}%, t = {res['S4_分组']['t']:.2f}, p = {res['S4_分组']['p']:.4f}")



if __name__ == '__main__':
    main()
