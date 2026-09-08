# -*- coding: utf-8 -*-
# ============================================================================
#  规范曲线分析（Specification Curve Analysis, Simonsohn-Simmons-Nelson 2020）
#  —— 本脚本现为 **v3 诚实面板** 版本（2026-08-16 适配）
#  【历史数据治理记录】本脚本初版读取 `数据/mvp_panel_v20.csv`（模拟占位面板），
#  其产出（Aug-8 的 spec_curve.png / 36·36 / 29·36 等计数）曾误用于 §4.9，
#  已于 2026-08-16 重算并替换。模拟占位面板已被隔离至 `模拟数据隔离区_20260814/`。
#  【当前数据源】指标计算流水线/output/主分析面板_重建_含TOwind.csv（v3 诚实面板）
#  控制集对齐诚实 M4：OCI 因仅18%覆盖已排除；L3 换手率用 TO_wind（86.6%覆盖）。
#  输出：figures/spec_curve_results.csv、figures/spec_curve_summary.json
# ============================================================================
"""
扩展规范曲线分析（Specification Curve Analysis, Simonsohn-Simmons-Nelson 2020）
协议先于估计确定：三大识别家族 x 合理设定维度的全组合网格，全部报告、无选择。

家族1 截面（基金层面均值，N=基金数）:
    dep: ff5_adj_return(FF5 alpha) / excess_return均值      [2]
    winsorize: 1%/99% / 不缩尾                              [2]
    推断: HC1 / HC3 / 经典OLS                               [3]
    控制组: base(log_aum) / mid(+age+tenure) / full M4(L1-L4) [3]
    -> 36 specs
家族2 前向预测（面板, 基金聚类SE）:
    horizon: 未来1季度 / 未来4季度均值                       [2]
    winsorize: 是/否                                        [2]
    控制组: mid / full M4                                   [2]
    FE: 仅年份(pooled预测, 正文头条设定) / 基金+年份(更严)      [2]
    -> 16 specs
家族3 组内（excess_return时变, 基金聚类SE）:
    FE: 基金+年份 / 仅基金                                   [2]
    winsorize: 是/否                                        [2]
    控制组: mid / full M4                                   [2]
    -> 8 specs
合计 60 个设定。同一家族内所有设定使用同一样本（对控制变量并集dropna），
符合SNS"同一数据、不同分析"的规范曲线原则。
"""
import os, json, itertools
import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf

# ---- v3 诚实面板适配（2026-08-16）--------------------------------------------
# 历史：本脚本最初读取 `数据/mvp_panel_v20.csv`（模拟占位面板），其产出曾用于
# §4.9 但不可用于实证（详见脚本顶部警告）。现将协议固定为诚实 v3 面板重算：
#   * 数据源：指标计算流水线/output/主分析面板_重建_含TOwind.csv（9,974 观测）
#   * v3 面板无 `date` 列（仅 report_date/year/quarter），`date` 由 report_date 派生
#   * 无 `log_aum`，由 avg_aum 取对数派生
#   * 诚实 M4 控制集不含 OCI（仅18%覆盖，已从诚实M4排除）；L3 换手率用 TO_wind
#     （86.6%覆盖）而非模拟时代的 TO_calc/OCI（真实面板已不存在）
#   * 输出改到项目内 figures/，便于稿件引用与可复现
# -------------------------------------------------------------------------------
base = r'D:\Desktop\基金经理行为分析研究\指标计算流水线\output'
figdir = r'D:\Desktop\基金经理行为分析研究\figures'
os.makedirs(figdir, exist_ok=True)

panel_path = base + r'\主分析面板_重建_含TOwind.csv'
df = pd.read_csv(panel_path, encoding='utf-8', low_memory=False)
df['date'] = pd.to_datetime(df['report_date'])
df = df.sort_values(['fund_code', 'date']).reset_index(drop=True)
df['log_aum'] = np.log(df['avg_aum'].astype(float))

L5 = ['de', 'lsv', 'risk_asym']
CTRL_MID = ['log_aum', 'log_fund_age', 'mgr_total_tenure_v2']
CTRL_FULL = ['log_aum', 'log_fund_age', 'mgr_total_tenure_v2',
             'AS_improved', 'ICI', 'industry_hhi',
             'SDI', 'TO_wind', 'ARG', 'return_volatility']
ALLCTRL = sorted(set(CTRL_MID + CTRL_FULL))
for _c in L5 + ['ff5_adj_return', 'excess_return'] + ALLCTRL:
    df[_c] = pd.to_numeric(df[_c], errors='coerce')

def winsz(x, lo=0.01, hi=0.99):
    a, b = x.quantile(lo), x.quantile(hi)
    return x.clip(a, b)

rows = []

# ================= 家族1：截面 =================
l5mask = df[L5].notna().all(axis=1)
dc = df.loc[l5mask, ['fund_code', 'ff5_adj_return', 'excess_return'] + L5 + ALLCTRL].copy()
agg = dc.groupby('fund_code').agg({c: 'mean' for c in dc.columns if c != 'fund_code'}).reset_index()
xsec = agg.dropna(subset=['ff5_adj_return', 'excess_return'] + L5 + ALLCTRL).reset_index(drop=True)
N_xsec = len(xsec)
print('[family1] cross-section N =', N_xsec)

ctrl_sets = {'base': ['log_aum'], 'mid': CTRL_MID, 'full': CTRL_FULL}
spec_i = 0
for dep, win, cov, cname in itertools.product(['ff5_adj_return', 'excess_return'], [1, 0],
                                              ['HC1', 'HC3', 'classic'], ['base', 'mid', 'full']):
    spec_i += 1
    d = xsec.copy()
    cols = [dep] + L5 + ctrl_sets[cname]
    if win:
        for c in cols:
            d[c] = winsz(d[c])
    X = sm.add_constant(d[L5 + ctrl_sets[cname]])
    fit = sm.OLS(d[dep], X).fit() if cov == 'classic' else sm.OLS(d[dep], X).fit(cov_type=cov)
    row = dict(spec=f'S1-{spec_i:02d}', family='cross_section', dep=dep, horizon='-',
               winsor=bool(win), cov=cov, controls=cname, N=int(fit.nobs),
               R2=round(float(fit.rsquared), 4))
    for k in L5:
        row[f'b_{k}'] = round(float(fit.params[k]), 5)
        row[f't_{k}'] = round(float(fit.tvalues[k]), 2)
        row[f'p_{k}'] = round(float(fit.pvalues[k]), 4)
    rows.append(row)

# ================= 家族2：前向预测 =================
df['fwd_ret_1q'] = df.groupby('fund_code')['excess_return'].transform(lambda x: x.shift(-1))
df['fwd_ret_4q'] = df.groupby('fund_code')['excess_return'].transform(
    lambda x: x.shift(-1).rolling(4, min_periods=2).mean())

for hz, hcol in [('1q', 'fwd_ret_1q'), ('4q', 'fwd_ret_4q')]:
    dp = df.loc[df[L5 + [hcol] + ALLCTRL].notna().all(axis=1)].copy()
    dp['year'] = dp['date'].dt.year
    dp['fund_id'] = dp['fund_code'].astype(str)
    n0 = len(dp)
    for win, cname, fe in itertools.product([1, 0], ['mid', 'full'], ['year', 'fund+year']):
        spec_i += 1
        d = dp.copy()
        cols = [hcol] + L5 + ctrl_sets[cname]
        if win:
            for c in cols:
                d[c] = winsz(d[c])
        fe_part = ' + C(fund_id) + C(year)' if fe == 'fund+year' else ' + C(year)'
        fml = f'{hcol} ~ ' + ' + '.join(L5 + ctrl_sets[cname]) + fe_part
        fit = smf.ols(fml, data=d).fit(cov_type='cluster', cov_kwds={'groups': d['fund_id']})
        row = dict(spec=f'S2-{spec_i:02d}', family='forward', dep='excess_return', horizon=hz,
                   winsor=bool(win), cov='cluster(fund)', controls=cname, fe=fe, N=int(fit.nobs),
                   R2=round(float(fit.rsquared), 4))
        for k in L5:
            row[f'b_{k}'] = round(float(fit.params[k]), 5)
            row[f't_{k}'] = round(float(fit.tvalues[k]), 2)
            row[f'p_{k}'] = round(float(fit.pvalues[k]), 4)
        rows.append(row)
    print(f'[family2] horizon {hz}: base N = {n0}')

# ================= 家族3：组内双向FE =================
dw = df.loc[df[L5 + ['excess_return'] + ALLCTRL].notna().all(axis=1)].copy()
dw['year'] = dw['date'].dt.year
dw['fund_id'] = dw['fund_code'].astype(str)
print('[family3] within base N =', len(dw))
for win, cname, fe in itertools.product([1, 0], ['mid', 'full'], ['fund+year', 'fund']):
    spec_i += 1
    d = dw.copy()
    cols = ['excess_return'] + L5 + ctrl_sets[cname]
    if win:
        for c in cols:
            d[c] = winsz(d[c])
    fe_part = ' + C(fund_id) + C(year)' if fe == 'fund+year' else ' + C(fund_id)'
    fml = 'excess_return ~ ' + ' + '.join(L5 + ctrl_sets[cname]) + fe_part
    fit = smf.ols(fml, data=d).fit(cov_type='cluster', cov_kwds={'groups': d['fund_id']})
    row = dict(spec=f'S3-{spec_i:02d}', family='within', dep='excess_return', horizon=fe,
               winsor=bool(win), cov='cluster(fund)', controls=cname, N=int(fit.nobs),
               R2=round(float(fit.rsquared), 4))
    for k in L5:
        row[f'b_{k}'] = round(float(fit.params[k]), 5)
        row[f't_{k}'] = round(float(fit.tvalues[k]), 2)
        row[f'p_{k}'] = round(float(fit.pvalues[k]), 4)
    rows.append(row)

res = pd.DataFrame(rows)
res.to_csv(figdir + r'\spec_curve_results.csv', index=False, encoding='utf-8-sig')

# ================= 汇总 =================
summary = {'total_specs': len(res), 'by_family': res.groupby('family').size().to_dict(),
           'cross_section_N': N_xsec}
for k in L5:
    b, p = res[f'b_{k}'], res[f'p_{k}']
    sig = (p < 0.05)
    dom_sign = np.sign(b.median())
    summary[k] = {
        'significant': f'{int(sig.sum())}/{len(res)}',
        'sig_share': round(float(sig.mean()), 3),
        'direction_consistency': round(float((np.sign(b) == dom_sign).mean()), 3),
        'median_coef': round(float(b.median()), 5),
        'coef_range': [round(float(b.min()), 5), round(float(b.max()), 5)],
        'by_family': {}
    }
    for fam, g in res.groupby('family'):
        bs, ps = g[f'b_{k}'], g[f'p_{k}']
        summary[k]['by_family'][fam] = {
            'sig': f'{int((ps < 0.05).sum())}/{len(g)}',
            'median': round(float(bs.median()), 5),
            'range': [round(float(bs.min()), 5), round(float(bs.max()), 5)],
            'same_sign_share': round(float((np.sign(bs) == dom_sign).mean()), 3)
        }
json.dump(summary, open(figdir + r'\spec_curve_summary.json', 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
print(json.dumps(summary, ensure_ascii=False, indent=1))
print('saved spec_curve_results.csv / spec_curve_summary.json')
