# -*- coding: utf-8 -*-
"""四个方法论追问的实证诊断（2026-08-26）
================================================================================
Q1 基本面优势升格计分是否合理？——加它到底带来什么
Q2 过度自信为什么替代换手率之后就显著了？
Q3 timing 与 ARG 会不会高度相关／多重共线？
Q4 sharpe8／sortino8／mppm8 三者相关性多大，全放进去合理吗？

输出：output/四问诊断_2026-08-26.json
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


panel = pd.read_csv(os.path.join(OUT, f'分析面板_v3_{TODAY}.csv'), parse_dates=['report_date'])
tim = pd.read_csv(os.path.join(OUT, f'择时系数_季度HM_{TODAY}.csv')).set_index('fund_code')[['timing']]

DIMS6 = {
    '基本面优势': [('mgr_total_tenure_v2', -1), ('log_fund_age', -1), ('log_aum', -1)],
    '认知能力': [('risk_asym', +1), ('de', -1), ('oc_conf', -1)],
    '配置选择能力': [('ICI', +1), ('ISDI', -1)],
    '风险应对能力': [('ARG', +1), ('timing', +1)],
    '风险转化能力': [('mppm8_lag', +1), ('sortino8_lag', +1), ('sharpe8_lag', +1)],
    '交易执行能力': [('SDI', -1), ('lsv', +1)],
}
ALL = [m for v in DIMS6.values() for m, _ in v]
sel = list(dict.fromkeys([m for m in ALL if m != 'timing'] +
                         CTRL + ['TO_wind_clean',
                                 'ff5_adj_return', 'quarter_return']))
fm = panel.groupby('fund_code')[sel].mean().join(tim, how='left')
for c in ALL + CTRL:
    fm[c] = winsor(pd.to_numeric(fm[c], errors='coerce'))
Y = fm['ff5_adj_return']

sc = pd.DataFrame(index=fm.index)
for dim, items in DIMS6.items():
    sc[dim] = ew(pd.DataFrame({m: sg * z(fm[m]) for m, sg in items}))
sc['综合_六维'] = ew(sc[list(DIMS6.keys())])
D5 = [d for d in DIMS6 if d != '基本面优势']
sc['综合_五维'] = ew(sc[D5])
sc['alpha'] = Y

# ================= Q1 =================
print('=' * 80)
print('Q1  基本面优势：加入它的增量价值在哪里')
print('=' * 80)
# ① 同期口径：五维 vs 六维 综合分的分组区分度
q1 = {}
for lab, col in [('五维_不含L1', '综合_五维'), ('六维_含L1', '综合_六维')]:
    g = sc.dropna(subset=[col, 'alpha']).copy()
    g['q'] = pd.qcut(g[col], 5, labels=['Q1', 'Q2', 'Q3', 'Q4', 'Q5'])
    tab = g.groupby('q', observed=True)['alpha'].mean()
    hi, lo = g[g['q'] == 'Q5']['alpha'], g[g['q'] == 'Q1']['alpha']
    tt = sm.stats.ttest_ind(hi, lo, usevar='unequal')
    mono = all(tab.iloc[i] < tab.iloc[i + 1] for i in range(4))
    q1[lab] = dict(Q5_Q1=round(float(hi.mean() - lo.mean()), 5),
                   t=round(float(tt[0]), 2), 单调=bool(mono))
    print(f'{lab}: Q5−Q1={hi.mean()-lo.mean():+.5f}  t={tt[0]:+.2f}  单调={mono}')

# ② 样本外口径（决定性证据）：前半期算综合分 → 后半期 alpha 分组
mid = panel['report_date'].quantile(0.5)
pre = panel[panel['report_date'] <= mid]
post = panel[panel['report_date'] > mid]
pre_fm = pre.groupby('fund_code')[
    list(dict.fromkeys([m for m in ALL if m != 'timing'] + CTRL))].mean().join(tim, how='left')
for c in ALL:
    pre_fm[c] = winsor(pd.to_numeric(pre_fm[c], errors='coerce'))
post_y = post.groupby('fund_code')['ff5_adj_return'].mean()

pre_sc = pd.DataFrame(index=pre_fm.index)
for dim, items in DIMS6.items():
    pre_sc[dim] = ew(pd.DataFrame({m: sg * z(pre_fm[m]) for m, sg in items}))
pre_sc['综合_六维'] = ew(pre_sc[list(DIMS6.keys())])
pre_sc['综合_五维'] = ew(pre_sc[D5])
pre_sc = pre_sc.join(post_y.rename('y_post'))

print(f'\n样本外（{str(mid)[:10]} 前算分 → 后算 alpha）：')
for lab, col in [('五维_不含L1', '综合_五维'), ('六维_含L1', '综合_六维')]:
    g = pre_sc.dropna(subset=[col, 'y_post']).copy()
    g['q'] = pd.qcut(g[col], 5, labels=['Q1', 'Q2', 'Q3', 'Q4', 'Q5'])
    tab = g.groupby('q', observed=True)['y_post'].mean()
    hi, lo = g[g['q'] == 'Q5']['y_post'], g[g['q'] == 'Q1']['y_post']
    tt = sm.stats.ttest_ind(hi, lo, usevar='unequal')
    mono = all(tab.iloc[i] < tab.iloc[i + 1] for i in range(4))
    q1[f'OOS_{lab}'] = dict(Q5_Q1=round(float(hi.mean() - lo.mean()), 5),
                            t=round(float(tt[0]), 2), 单调=bool(mono))
    print(f'{lab}: Q5−Q1={hi.mean()-lo.mean():+.5f}  t={tt[0]:+.2f}  单调={mono}')

# ③ L1 对样本外预测的边际贡献：两个嵌套模型对比
X5 = reg(pre_sc['y_post'], pre_sc[D5])
X6 = reg(pre_sc['y_post'], pre_sc[list(DIMS6.keys())])
r2_5, r2_6 = float(X5.rsquared), float(X6.rsquared)
n5, n6 = int(X5.nobs), int(X6.nobs)
fstat = ((r2_6 - r2_5) / 1) / ((1 - r2_6) / (n6 - 7))
from scipy import stats as _st
p_f = 1 - _st.f.cdf(fstat, 1, n6 - 7)
q1['OOS_嵌套F'] = dict(r2_五维=round(r2_5, 4), r2_六维=round(r2_6, 4),
                       F=round(float(fstat), 2), p=round(float(p_f), 4))
print(f'\n嵌套对比（样本外，H0: L1 联立系数=0）：R² {r2_5:.4f} → {r2_6:.4f}，'
      f'F={fstat:.2f}，p={p_f:.4f}')
res['Q1_L1'] = q1

# ================= Q2 =================
print()
print('=' * 80)
print('Q2  换手率为什么不显著、oc_conf 为什么显著')
print('=' * 80)
to = fm['TO_wind_clean']
occ = fm['oc_conf']
r_pt = float(fm[['TO_wind_clean', 'oc_conf']].corr().iloc[0, 1])
r_sp = float(fm[['TO_wind_clean', 'oc_conf']].corr(method='spearman').iloc[0, 1])
# TO 与 alpha 的原始相关 vs oc_conf 与 alpha 的原始相关
r_to_y = float(fm[['TO_wind_clean', 'ff5_adj_return']].corr().iloc[0, 1])
r_oc_y = float(fm[['oc_conf', 'ff5_adj_return']].corr().iloc[0, 1])
# 控制行为变量后 TO 还剩多少信号
ctrl_dims = ['认知能力', '配置选择能力', '风险应对能力', '风险转化能力',
             '交易执行能力', '基本面优势']
_to_df = sc[ctrl_dims + ['alpha']].join(fm[['TO_wind_clean']]).rename(
    columns={'alpha': 'ff5_adj_return'})
m_to = reg(_to_df['ff5_adj_return'], _to_df[ctrl_dims + ['TO_wind_clean']])
t_to_net = float(m_to.tvalues['TO_wind_clean'])
print(f'corr(TO, oc_conf)：Pearson={r_pt:.3f}  Spearman={r_sp:.3f}')
print(f'与 alpha 的原始相关：TO r={r_to_y:+.3f}   oc_conf r={r_oc_y:+.3f}')
print(f'控制六个维度后 TO 的净 t = {t_to_net:+.2f}（仍不显著则说明其信号已被行为维度覆盖）')
res['Q2_TO_vs_OC'] = dict(
    pearson=round(r_pt, 3), spearman=round(r_sp, 3),
    corr_TO_alpha=round(r_to_y, 3), corr_OC_alpha=round(r_oc_y, 3),
    TO_净t=round(t_to_net, 2))

# ================= Q3 =================
print()
print('=' * 80)
print('Q3  ARG × timing：相关性与共线性')
print('=' * 80)
arg, tm = fm['ARG'], fm['timing']
both = pd.concat([arg, tm], axis=1).dropna()
r_p = float(both.corr().iloc[0, 1])
r_s = float(both.corr(method='spearman').iloc[0, 1])
# 两变量互控后的净效应
d = pd.concat([Y.rename('y'), arg.rename('ARG'), tm.rename('TIMING')], axis=1).dropna()
m2 = sm.OLS(d['y'], sm.add_constant(d[['ARG', 'TIMING']])).fit(cov_type='HC1')
# VIF：1/(1-R²_aux)
aux = sm.OLS(both['ARG'] - both['ARG'].mean(), sm.add_constant(both['timing'])).fit()
vif = 1 / (1 - float(aux.rsquared))
print(f'corr(ARG, timing)：Pearson={r_p:.3f}  Spearman={r_s:.3f}  n={len(both)}')
print(f'两变量互控：ARG t={m2.tvalues["ARG"]:+.2f}  timing t={m2.tvalues["TIMING"]:+.2f}')
print(f'VIF(ARG|timing) = {vif:.2f}（经验阈值 10）')
res['Q3_ARG_timing'] = dict(pearson=round(r_p, 3), spearman=round(r_s, 3),
                            n=int(len(both)), vif=round(vif, 2),
                            ARG_净t=round(float(m2.tvalues['ARG']), 2),
                            timing_净t=round(float(m2.tvalues['TIMING']), 2))

# ================= Q4 =================
print()
print('=' * 80)
print('Q4  sharpe8 / sortino8 / mppm8：含义重叠度与"三个都放"的合理性')
print('=' * 80)
trio = ['sharpe8_lag', 'sortino8_lag', 'mppm8_lag']
sub = fm[trio].dropna()
cm = sub.corr()
print('两两相关（基金层，winsor 后）：')
print(cm.round(3).to_string())
csm = sub.rank().corr()
print('\nSpearman：')
print(csm.round(3).to_string())
# 若把三个成分当独立变量塞进一次回归会怎样（演示性 VIF）
vifs = {}
for k in trio:
    others = [x for x in trio if x != k]
    aux = sm.OLS(sub[k] - sub[k].mean(), sm.add_constant(sub[others])).fit()
    vifs[k] = round(1 / (1 - float(aux.rsquared)), 1)
print(f'\n若强行三变量同入回归的 VIF：{vifs}（说明三者高度重叠）')
# 但实际做法：合成一个维度分。检查单成分维度 vs 三成分维度的差异
dim3 = sc['风险转化能力']
single = {k: z(winsor(fm[k])) for k in trio}
rob = {}
for k in trio:
    rob[k] = dict(corr_with_dim3=round(float(pd.concat([z(single[k]).rename('a'),
                                                        dim3.rename('b')],
                                                       axis=1).dropna().corr().iloc[0, 1]), 4))
print('\n单成分维度 vs 三成分复合维度 的相关：')
for k, v in rob.items():
    print(f'  仅用 {k:<14} 与复合维度相关 {v["corr_with_dim3"]}')
# 三成分复合 vs 单成分：对 alpha 的单维解释力对比
print('\n单成分维度 vs 复合维度 对 alpha 的单维 t：')
comp_t = {}
for lab, series in [('仅sharpe8', z(single['sharpe8_lag'])),
                    ('仅sortino8', z(single['sortino8_lag'])),
                    ('仅mppm8', z(single['mppm8_lag'])),
                    ('三成分复合', dim3)]:
    dd = pd.concat([Y.rename('y'), series.rename('x')], axis=1).dropna()
    mm = sm.OLS(dd['y'], sm.add_constant(dd[['x']])).fit(cov_type='HC1')
    comp_t[lab] = dict(t=round(float(mm.tvalues['x']), 2),
                       r2=round(float(mm.rsquared), 4))
    print(f'  {lab:<12} t={mm.tvalues["x"]:+.2f}  R²={mm.rsquared:.4f}')
res['Q4_trio'] = dict(pearson=cm.round(3).to_dict(), spearman=csm.round(3).to_dict(),
                      vif_if_separate=vifs, 单成分vs复合相关=rob,
                      单维解释力=comp_t)

with open(os.path.join(OUT, f'四问诊断_{TODAY}.json'), 'w', encoding='utf-8') as f:
    json.dump(res, f, ensure_ascii=False, indent=2)
print('\n已落盘：output/四问诊断_%s.json' % TODAY)
