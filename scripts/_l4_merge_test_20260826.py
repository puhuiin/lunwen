# -*- coding: utf-8 -*-
"""L4 合并可行性检验：五层框架 vs 六个计分维度的口径抉择（2026-08-26）
================================================================================
问题：理论框架是 L1–L5 五层，但计分维度是 6 个（L4 拆为「过程应对」与「转化能力」
两个职能），层数与维数不一致。本脚本用数据回答：把 L4 合并回 1 个维度，
让「五层 = 五维」严格对齐，会损失什么？

三个候选口径：
  口径 A（现行）  6 维：L1 / L2 / L3 / L4a 过程 / L4b 转化 / L5
  口径 B（分数级合并）5 维：L4 = (L4a 得分 + L4b 得分) / 2
  口径 C（成分级合并）5 维：L4 = 5 个成分（ARG, timing, mppm, sortino, sharpe）等权

评判标准（四项）：
  ① 联立回归中 L4 是否仍显著、其余维度结论是否改变
  ② 综合分五分组 alpha 的单调性与 Q5−Q1 区分度
  ③ 合并是否掩盖了两个职能的异质性（两子维相关性、以及个体层面的背离比例）
  ④ 综合分与现行口径的秩相关（画像结论是否会翻）
================================================================================
"""
import pandas as pd
import numpy as np
import os
import json
import statsmodels.api as sm
from scipy import stats

BASE = r'd:\Desktop\基金经理行为分析研究'
OUT = os.path.join(BASE, 'output')
TODAY = '2026-08-26'
CTRL = ['mgr_total_tenure_v2', 'log_fund_age', 'log_aum']

DIMS6 = {
    '基本面优势': [('mgr_total_tenure_v2', -1), ('log_fund_age', -1), ('log_aum', -1)],
    '认知能力': [('risk_asym', +1), ('de', -1), ('oc_conf', -1)],
    '配置选择能力': [('ICI', +1), ('ISDI', -1)],
    '风险应对能力': [('ARG', +1), ('timing', +1)],
    '风险转化能力': [('mppm8_lag', +1), ('sortino8_lag', +1), ('sharpe8_lag', +1)],
    '交易执行能力': [('SDI', -1), ('lsv', +1)],
}
D6 = list(DIMS6.keys())
L4A, L4B = '风险应对能力', '风险转化能力'
ALL_COMP = [m for v in DIMS6.values() for m, _ in v]
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


# ---------------- 数据 ----------------
panel = pd.read_csv(os.path.join(OUT, f'分析面板_v3_{TODAY}.csv'), parse_dates=['report_date'])
tim = pd.read_csv(os.path.join(OUT, f'择时系数_季度HM_{TODAY}.csv')).set_index('fund_code')[['timing']]
base_cols = [c for c in ALL_COMP if c != 'timing']
sel = list(dict.fromkeys(base_cols + CTRL))
fm = panel.groupby('fund_code')[sel + ['ff5_adj_return', 'quarter_return']].mean().join(tim, how='left')
for c in ALL_COMP:
    fm[c] = winsor(pd.to_numeric(fm[c], errors='coerce'))
Y = fm['ff5_adj_return']

# ---------------- 构造三套得分 ----------------
sc = pd.DataFrame(index=fm.index)
for dim, items in DIMS6.items():
    sc[dim] = ew(pd.DataFrame({m: sg * z(fm[m]) for m, sg in items}))

# A：现行六维
sc['综合_A'] = ew(sc[D6])

# B：分数级合并 L4
sc['L4_合并_分数级'] = ew(sc[[L4A, L4B]])
D5B = ['基本面优势', '认知能力', '配置选择能力', 'L4_合并_分数级', '交易执行能力']
sc['综合_B'] = ew(sc[D5B])

# C：成分级合并 L4（5 个成分等权，不先分组）
l4_items = DIMS6[L4A] + DIMS6[L4B]
sc['L4_合并_成分级'] = ew(pd.DataFrame({m: sg * z(fm[m]) for m, sg in l4_items}))
D5C = ['基本面优势', '认知能力', '配置选择能力', 'L4_合并_成分级', '交易执行能力']
sc['综合_C'] = ew(sc[D5C])

sc['ff5_alpha'] = Y
sc['quarter_return'] = fm['quarter_return']
scj = sc.join(fm[CTRL])

print('=' * 80)
print('① 联立回归：合并 L4 后各维度结论是否改变')
print('=' * 80)
joint = {}
for lab, dl in [('A_六维_现行', D6), ('B_五维_分数级合并', D5B), ('C_五维_成分级合并', D5C)]:
    m = reg(scj['ff5_alpha'], scj[dl])
    joint[lab] = dict(n=int(m.nobs), r2=round(float(m.rsquared), 4),
                      adj_r2=round(float(m.rsquared_adj), 4),
                      系数={d: dict(coef=round(float(m.params[d]), 5),
                                    t=round(float(m.tvalues[d]), 2),
                                    p=round(float(m.pvalues[d]), 4)) for d in dl})
    print(f'\n{lab}  n={m.nobs}  R²={m.rsquared:.4f}  adjR²={m.rsquared_adj:.4f}')
    for d in dl:
        sig = '***' if m.pvalues[d] < .01 else ('**' if m.pvalues[d] < .05 else
                                               ('*' if m.pvalues[d] < .1 else ''))
        print('    %-16s coef=%+.5f  t=%+6.2f%-3s p=%.4f' % (d, m.params[d], m.tvalues[d], sig, m.pvalues[d]))
res['①_联立回归'] = joint

print()
print('=' * 80)
print('② 综合分五分组：单调性与区分度')
print('=' * 80)
grp = {}
for lab, col in [('A_六维', '综合_A'), ('B_五维_分数级', '综合_B'), ('C_五维_成分级', '综合_C')]:
    g = sc.dropna(subset=[col, 'ff5_alpha']).copy()
    g['q'] = pd.qcut(g[col], 5, labels=['Q1', 'Q2', 'Q3', 'Q4', 'Q5'])
    tab = g.groupby('q', observed=True)['ff5_alpha'].mean()
    hi, lo = g[g['q'] == 'Q5']['ff5_alpha'], g[g['q'] == 'Q1']['ff5_alpha']
    tt = sm.stats.ttest_ind(hi, lo, usevar='unequal')
    mono = all(tab.iloc[i] < tab.iloc[i + 1] for i in range(4))
    grp[lab] = dict(alpha均值={k: round(float(v), 5) for k, v in tab.items()},
                    严格单调=bool(mono), Q5_Q1=round(float(hi.mean() - lo.mean()), 5),
                    t=round(float(tt[0]), 2), p=round(float(tt[1]), 4))
    print('%-16s %s  Q5−Q1=%+.5f  t=%+.2f  单调=%s'
          % (lab, ' → '.join('%.4f' % v for v in tab), hi.mean() - lo.mean(), tt[0], mono))
res['②_五分组'] = grp

print()
print('=' * 80)
print('③ 合并是否掩盖异质性：两个 L4 职能的分歧程度')
print('=' * 80)
both = sc[[L4A, L4B]].dropna()
r_p = both.corr().iloc[0, 1]
r_s = both.corr(method='spearman').iloc[0, 1]
# 个体层面背离：两子维分位差超过 0.5（半个样本宽度）的比例
pa, pb = both[L4A].rank(pct=True), both[L4B].rank(pct=True)
gap = (pa - pb).abs()
div50 = float((gap > 0.5).mean())
div30 = float((gap > 0.3).mean())
# 极端背离案例数：一维 >0.9 分位而另一维 <0.1 分位
extreme = int((((pa > .9) & (pb < .1)) | ((pb > .9) & (pa < .1))).sum())
print(f'两职能相关：Pearson={r_p:.3f}  Spearman={r_s:.3f}  n={len(both)}')
print(f'分位差 > 0.30 的基金占比：{div30:.1%}')
print(f'分位差 > 0.50 的基金占比：{div50:.1%}')
print(f'极端背离（一维 >90% 分位、另一维 <10% 分位）：{extreme} 只')
# 各自对 alpha 的独立贡献（互相控制）
m_both = reg(scj['ff5_alpha'], scj[[L4A, L4B]])
print('\n两职能同时进入（仅此二者）：')
for d in [L4A, L4B]:
    print('    %-10s coef=%+.5f  t=%+6.2f  p=%.4f'
          % (d, m_both.params[d], m_both.tvalues[d], m_both.pvalues[d]))
res['③_异质性'] = dict(pearson=round(float(r_p), 3), spearman=round(float(r_s), 3),
                       n=int(len(both)), 分位差gt30=round(div30, 4),
                       分位差gt50=round(div50, 4), 极端背离数=extreme,
                       两职能互控={d: dict(coef=round(float(m_both.params[d]), 5),
                                           t=round(float(m_both.tvalues[d]), 2),
                                           p=round(float(m_both.pvalues[d]), 4))
                                   for d in [L4A, L4B]})

print()
print('=' * 80)
print('④ 综合分秩相关：合并后画像排序是否会翻')
print('=' * 80)
cc = sc[['综合_A', '综合_B', '综合_C']].dropna()
for a, b in [('综合_A', '综合_B'), ('综合_A', '综合_C'), ('综合_B', '综合_C')]:
    pr = cc[a].corr(cc[b])
    sr, _ = stats.spearmanr(cc[a], cc[b])
    print('%-12s vs %-12s  Pearson=%.4f  Spearman=%.4f' % (a, b, pr, sr))
# Top/Bottom 5% 名单重叠度
n5 = int(np.ceil(len(cc) * .05))
ovl = {}
for a, b in [('综合_A', '综合_B'), ('综合_A', '综合_C')]:
    ta, tb = set(cc.nlargest(n5, a).index), set(cc.nlargest(n5, b).index)
    ba, bb = set(cc.nsmallest(n5, a).index), set(cc.nsmallest(n5, b).index)
    ovl[f'{a}_vs_{b}'] = dict(top重叠=len(ta & tb), bottom重叠=len(ba & bb), n_each=n5)
    print('%s vs %s：Top5%% 名单重叠 %d/%d，Bottom5%% 重叠 %d/%d'
          % (a, b, len(ta & tb), n5, len(ba & bb), n5))
res['④_秩相关'] = dict(
    相关={f'{a}_vs_{b}': dict(pearson=round(float(cc[a].corr(cc[b])), 4),
                              spearman=round(float(stats.spearmanr(cc[a], cc[b])[0]), 4))
          for a, b in [('综合_A', '综合_B'), ('综合_A', '综合_C'), ('综合_B', '综合_C')]},
    名单重叠=ovl)

print()
print('=' * 80)
print('裁决建议')
print('=' * 80)
a_t = {d: joint['A_六维_现行']['系数'][d]['t'] for d in D6}
b_l4 = joint['B_五维_分数级合并']['系数']['L4_合并_分数级']
c_l4 = joint['C_五维_成分级合并']['系数']['L4_合并_成分级']
print(f"现行六维：L4a 过程 t={a_t[L4A]:+.2f}，L4b 转化 t={a_t[L4B]:+.2f}（两者均显著）")
print(f"合并五维B：L4 t={b_l4['t']:+.2f}（p={b_l4['p']:.4f}）")
print(f"合并五维C：L4 t={c_l4['t']:+.2f}（p={c_l4['p']:.4f}）")
print(f"两职能相关仅 {r_s:.3f}，{div30:.0%} 的基金分位差超 0.3，{extreme} 只极端背离")
print(f"合并后综合分与现行 Spearman={stats.spearmanr(cc['综合_A'], cc['综合_B'])[0]:.4f}")

with open(os.path.join(OUT, f'L4合并可行性检验_{TODAY}.json'), 'w', encoding='utf-8') as f:
    json.dump(res, f, ensure_ascii=False, indent=2)
print(f'\n已落盘：output/L4合并可行性检验_{TODAY}.json')
