# -*- coding: utf-8 -*-
"""
画像分型联动验证（2026-08-25）
用六维等权复合得分重跑 §10b 分型，验证复合画像的分型结构与原单指标规则的一致性/差异。
维度映射（原规则 → 复合维度）：
  风控择股型(赢家): RA>=0.5 & ARG>=0.5 & DE<=0.3   → risk_rsp>=0.5 & active>=0.5 & discipl>=-0.3
  行业集中下注型:    ICI>=0.5 & AS<=0.3             → alloc>=0.5（AS 未入六维，降级为单条件，附披露）
  低偏误纪律型:      DE<=-0.5 & |LSV|<=0.5          → discipl>=0.5（LSV 未入六维，降级，附披露）
  高换手噪声型(输家): TO>=0.5 & RA<=0               → cost<=-0.5 & risk_rsp<=0
优先级同原文：赢家→集中下注→纪律→输家→均衡。
输出：各型数量、组均 ff5_adj_return / composite、与均衡型的 Welch t 检验。
"""
import pandas as pd, numpy as np, os
from scipy import stats

BASE = r'd:\Desktop\基金经理行为分析研究'
OUT = os.path.join(BASE, 'output')

df = pd.read_csv(os.path.join(OUT, '六维能力复合得分_2026-08-25.csv'))

def classify(r):
    if r['risk_rsp'] >= 0.5 and r['active'] >= 0.5 and r['discipl'] >= -0.3:
        return '风控择股型(赢家)'
    if r['alloc'] >= 0.5:
        return '行业集中下注型'
    if r['discipl'] >= 0.5:
        return '低偏误纪律型'
    if r['cost'] <= -0.5 and r['risk_rsp'] <= 0:
        return '高换手噪声型(输家)'
    return '均衡型(其他)'

df['archetype'] = df.apply(classify, axis=1)

order = ['风控择股型(赢家)', '行业集中下注型', '低偏误纪律型', '高换手噪声型(输家)', '均衡型(其他)']
base = df.loc[df['archetype'] == '均衡型(其他)', 'ff5_adj_return'].dropna()

print(f'=== 六维复合版分型结果（N={len(df)}）===')
rows = []
for a in order:
    sub = df[df['archetype'] == a]
    alpha = sub['ff5_adj_return'].dropna()
    comp = sub['composite'].dropna()
    if a != '均衡型(其他)' and len(alpha) >= 5:
        t, p = stats.ttest_ind(alpha, base, equal_var=False)
        sig = '***' if p < 0.01 else ('**' if p < 0.05 else ('*' if p < 0.1 else ''))
    else:
        t, p, sig = np.nan, np.nan, ''
    rows.append({'原型': a, '数量': len(sub),
                 '组均alpha': round(alpha.mean(), 4),
                 '组均composite': round(comp.mean(), 3),
                 'vs均衡_t': round(t, 2) if not np.isnan(t) else '',
                 'sig': sig})
    print(f"  {a:14s} N={len(sub):3d}  alpha={alpha.mean():+.4f}  composite={comp.mean():+.3f}  t={t if np.isnan(t) else f'{t:+.2f}'}{sig}")

print('\n>>> 原 §10b 单指标规则分布：赢家33 / 集中下注20 / 纪律29 / 输家57 / 均衡261')

# 赢家 vs 输家 直接对照
w = df.loc[df['archetype'] == '风控择股型(赢家)', 'ff5_adj_return'].dropna()
l = df.loc[df['archetype'] == '高换手噪声型(输家)', 'ff5_adj_return'].dropna()
t, p = stats.ttest_ind(w, l, equal_var=False)
sig = '***' if p < 0.01 else ('**' if p < 0.05 else ('*' if p < 0.1 else ''))
print(f'>>> 赢家({len(w)}) vs 输家({len(l)}) alpha差={w.mean()-l.mean():+.4f}  t={t:+.2f}{sig}')

res = pd.DataFrame(rows)
res.to_csv(os.path.join(OUT, '复合分型联动_2026-08-25.csv'), index=False, encoding='utf-8-sig')
df[['fund_code', 'archetype', 'composite', 'ff5_adj_return']].to_csv(
    os.path.join(OUT, '复合分型明细_2026-08-25.csv'), index=False, encoding='utf-8-sig')
print('\n已保存 output/复合分型联动_2026-08-25.csv 与 复合分型明细_2026-08-25.csv')
