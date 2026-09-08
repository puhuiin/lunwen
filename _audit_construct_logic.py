# -*- coding: utf-8 -*-
"""构建链条审查：分层合理性、指标实质含义、方向一致性"""
import pandas as pd, numpy as np, os, json

OUT = 'output'
panel = pd.read_csv(os.path.join(OUT, '分析面板_v3_2026-08-26.csv'))
tim = pd.read_csv(os.path.join(OUT, '择时系数_季度HM_2026-08-26.csv')).set_index('fund_code')[['timing']]

COMP = ['risk_asym', 'de', 'oc_conf', 'ICI', 'ISDI', 'ARG', 'timing',
        'mppm8_lag', 'sortino8_lag', 'sharpe8_lag', 'SDI', 'lsv']
DV = 'ff5_adj_return'

fm = panel.groupby('fund_code')[[c for c in COMP if c in panel.columns] + [DV]].mean()
fm = fm.join(tim, how='left')
for c in fm.columns:
    fm[c] = pd.to_numeric(fm[c], errors='coerce')
    lo, hi = fm[c].quantile([0.01, 0.99])
    fm[c] = fm[c].clip(lo, hi)

print('=== 一、观测层：ARG 是否恒非负（判断是否取了绝对值）===')
if 'ARG' in panel.columns:
    a = panel['ARG'].dropna()
    print('  n=%d  负数占比=%.2f%%  min=%.4f  max=%.4f  mean=%.4f' %
          (len(a), (a < 0).mean() * 100, a.min(), a.max(), a.mean()))
    print('  → 若负数占比≈0，说明 ARG 取了绝对值，测的是「调仓活跃度」而非带符号的「调仓收益」')

print('\n=== 二、观测层：risk_asym 符号分布（前景理论方向检验）===')
if 'risk_asym' in panel.columns:
    r = panel['risk_asym'].dropna()
    print('  n=%d  正值占比=%.1f%%  mean=%+.4f' % (len(r), (r > 0).mean() * 100, r.mean()))
    print('  前景理论预测：亏损期 risk-seeking → σ(亏损)>σ(盈利) → risk_asym<0 为「偏差」')
    print('  本文实证 risk_asym 正向显著 → 与前景理论的偏差预测方向相反')

print('\n=== 三、分层合理性：两个「漂移」指标是否重复 ===')
if 'ISDI' in fm.columns and 'SDI' in fm.columns:
    d = fm[['ISDI', 'SDI']].dropna()
    print('  corr(ISDI, SDI) = %+.3f  (n=%d)' % (d['ISDI'].corr(d['SDI']), len(d)))
    print('  ISDI 在 L3 选择层、SDI 在 L5 交易执行层；若相关过高则分层重复')

print('\n=== 四、L4a 内部：ARG 与 timing 是否重复 ===')
if 'ARG' in fm.columns and 'timing' in fm.columns:
    d = fm[['ARG', 'timing']].dropna()
    print('  corr(ARG, timing) = %+.3f  (n=%d)' % (d['ARG'].corr(d['timing']), len(d)))

print('\n=== 五、基金层成分相关矩阵（|r|>0.4 高亮）===')
sub = fm[[c for c in COMP if c in fm.columns]]
cm = sub.corr()
print('        ' + ''.join('%8s' % c[:7] for c in cm.columns))
for i in cm.index:
    row = '%8s' % i[:7]
    for j in cm.columns:
        v = cm.loc[i, j]
        row += '%8s' % ('—' if i == j else ('%.2f*' % v if abs(v) > 0.4 else '%.2f' % v))
    print(row)

print('\n=== 六、方向一致性核对（论文定向 vs 实证符号）===')
exp = {'risk_asym': '+', 'de': '-', 'oc_conf': '-', 'ICI': '+', 'ISDI': '-',
       'ARG': '+', 'timing': '+', 'mppm8_lag': '+', 'sortino8_lag': '+',
       'sharpe8_lag': '+', 'SDI': '-', 'lsv': '+'}
for c, e in exp.items():
    if c not in fm.columns:
        continue
    d = fm[[c, DV]].dropna()
    r = float(d[c].corr(d[DV]))
    actual = '+' if r > 0 else '-'
    ok = '✓' if actual == e else '✗ 不一致'
    print('  %-14s 论文定向=%s  实证符号=%s (r=%+.3f)  %s' % (c, e, actual, r, ok))

# ---------- 落盘（供结论源与论文引用，禁止手写数字） ----------
def _pair(a, b):
    if a not in fm.columns or b not in fm.columns:
        return None
    d = fm[[a, b]].dropna()
    return round(float(d[a].corr(d[b])), 4)

res = {
    '口径': '基金层时序均值，1%/99% 缩尾',
    '关键跨层相关': {
        'ARG_x_SDI': _pair('ARG', 'SDI'),
        'risk_asym_x_sortino8': _pair('risk_asym', 'sortino8_lag'),
        'mppm8_x_sharpe8': _pair('mppm8_lag', 'sharpe8_lag'),
        'ISDI_x_SDI': _pair('ISDI', 'SDI'),
        'ARG_x_timing': _pair('ARG', 'timing'),
        'ICI_x_ISDI': _pair('ICI', 'ISDI'),
    },
    'ARG绝对值检验': {
        '观测层n': int(panel['ARG'].notna().sum()) if 'ARG' in panel.columns else None,
        '负数占比': round(float((panel['ARG'].dropna() < 0).mean()), 4) if 'ARG' in panel.columns else None,
        'min': round(float(panel['ARG'].dropna().min()), 4) if 'ARG' in panel.columns else None,
        '结论': '负数占比为 0 → ARG = Σ|RG_t|，测「调仓活跃度」而非带符号的「调仓收益」',
    },
    'risk_asym方向检验': {
        '正值占比': round(float((panel['risk_asym'].dropna() > 0).mean()), 4) if 'risk_asym' in panel.columns else None,
        '结论': '多数观测为正 → 与前景理论「亏损期 risk-seeking」的偏差预测方向相反',
    },
}
with open(os.path.join(OUT, '构建链条诊断_2026-08-29.json'), 'w', encoding='utf-8') as f:
    json.dump(res, f, ensure_ascii=False, indent=2)
print('\n已落盘 output/构建链条诊断_2026-08-29.json')
