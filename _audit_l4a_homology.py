# -*- coding: utf-8 -*-
"""B1 裁定依据：L4a(timing) 与因变量的概念同源程度
对照基准：D1「L4b 与因变量最大相关 0.443，对照组最高 0.313」
          D8「sharpe 族 L4b 复合与 alpha 相关 0.439」
若 corr(timing, alpha) 明显高于对照组 0.313，则 L4a 应纳入同源讨论。
"""
import pandas as pd, numpy as np, os, json

OUT = 'output'
panel = pd.read_csv(os.path.join(OUT, '分析面板_v3_2026-08-26.csv'))
tim = pd.read_csv(os.path.join(OUT, '择时系数_季度HM_2026-08-26.csv')).set_index('fund_code')[['timing']]

COMP = ['risk_asym', 'de', 'oc_conf', 'ICI', 'ISDI', 'ARG', 'timing',
        'mppm8_lag', 'sortino8_lag', 'sharpe8_lag', 'SDI', 'lsv',
        'mgr_total_tenure_v2', 'log_fund_age', 'log_aum']
DV = 'ff5_adj_return'

cols = [c for c in COMP if c in panel.columns] + [DV]
fm = panel.groupby('fund_code')[cols].mean().join(tim, how='left')
for c in fm.columns:
    fm[c] = pd.to_numeric(fm[c], errors='coerce')
    lo, hi = fm[c].quantile([0.01, 0.99])
    fm[c] = fm[c].clip(lo, hi)

Y = fm[DV]
print('=== 各成分与 FF5 alpha 的相关（基金层，1% 缩尾）===')
rows = []
for c in COMP:
    if c not in fm.columns:
        continue
    d = fm[[c, DV]].dropna()
    r = float(d[c].corr(d[DV]))
    rows.append((c, r, len(d)))
for c, r, n in sorted(rows, key=lambda x: -abs(x[1])):
    tag = ''
    if c in ('mppm8_lag', 'sortino8_lag', 'sharpe8_lag'):
        tag = '  [L4b 成分]'
    elif c == 'timing':
        tag = '  [L4a 成分  <== 本次核查对象]'
    elif c == 'ARG':
        tag = '  [L4a 成分]'
    print('  %-18s r=%+.3f  (n=%d)%s' % (c, r, n, tag))


def z(s):
    return (s - s.mean()) / s.std()


print('\n=== 复合维度与 alpha 的相关（与 D8 的 L4b 0.439 可比）===')
dim = {}
dim['L1 基本面优势'] = -(z(fm['mgr_total_tenure_v2']) + z(fm['log_fund_age']) + z(fm['log_aum'])) / 3
dim['L2 认知'] = (z(fm['risk_asym']) - z(fm['de']) - z(fm['oc_conf'])) / 3
dim['L3 配置选择'] = (z(fm['ICI']) - z(fm['ISDI'])) / 2
dim['L4a 过程应对'] = (z(fm['ARG']) + z(fm['timing'])) / 2
dim['L4b 风险转化'] = (z(fm['mppm8_lag']) + z(fm['sortino8_lag']) + z(fm['sharpe8_lag'])) / 3
dim['L5 交易执行'] = (-z(fm['SDI']) + z(fm['lsv'])) / 2
for k, v in dim.items():
    d = pd.concat([v.rename('s'), Y], axis=1).dropna()
    print('  %-14s r=%+.3f  (n=%d)' % (k, float(d['s'].corr(d[DV])), len(d)))

print('\n=== L4a 两成分分别与 alpha（拆分看是谁在贡献同源）===')
for c in ['ARG', 'timing']:
    d = fm[[c, DV]].dropna()
    print('  %-8s r=%+.3f' % (c, float(d[c].corr(d[DV]))))

print('\n=== 裁定参考 ===')
r_time = float(fm[['timing', DV]].dropna()['timing'].corr(fm[['timing', DV]].dropna()[DV]))
r_l4b = float(pd.concat([dim['L4b 风险转化'].rename('s'), Y], axis=1).dropna()['s'].corr(
    pd.concat([dim['L4b 风险转化'].rename('s'), Y], axis=1).dropna()[DV]))
print('  corr(timing, alpha)      = %+.3f' % r_time)
print('  corr(L4b复合, alpha)     = %+.3f   (对照 D8 称 0.439)' % r_l4b)
print('  D1 对照组最高            = 0.313')
print('  判定：timing 是否高于对照组 0.313 ? %s' % (r_time > 0.313))

# ---------- 落盘（供结论源与论文引用，禁止手写数字） ----------
comp_r = {c: round(float(fm[[c, DV]].dropna()[c].corr(fm[[c, DV]].dropna()[DV])), 4)
          for c in COMP if c in fm.columns}
dim_r = {}
for k, v in dim.items():
    d = pd.concat([v.rename('s'), Y], axis=1).dropna()
    dim_r[k] = round(float(d['s'].corr(d[DV])), 4)

res = {
    '口径': '基金层时序均值，1%/99% 缩尾；n 见各表',
    '成分与alpha相关': comp_r,
    '复合维度与alpha相关': dim_r,
    '关键对照': {
        'timing(L4a成分)': round(r_time, 4),
        'L4a复合': dim_r['L4a 过程应对'],
        'L4b复合': dim_r['L4b 风险转化'],
        'D1对照组最高': 0.313,
        'D8记载_L4b复合': 0.439,
    },
    '裁定': {
        'timing高于对照组': bool(r_time > 0.313),
        'timing高于L4b最弱成分sortino8': bool(r_time > comp_r.get('sortino8_lag', 1)),
        'L4a与L4b同源程度相当': bool(abs(dim_r['L4a 过程应对'] - dim_r['L4b 风险转化']) < 0.05),
    },
}
with open(os.path.join(OUT, 'L4a同源诊断_2026-08-29.json'), 'w', encoding='utf-8') as f:
    json.dump(res, f, ensure_ascii=False, indent=2)
print('\n已落盘 output/L4a同源诊断_2026-08-29.json')
