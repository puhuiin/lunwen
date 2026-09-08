# -*- coding: utf-8 -*-
"""核查 L1 控制变量的回归证据（full 模型系数 + 面板）。"""
import json

d = json.load(open(r'output\主回归_v3_2026-08-26.json', encoding='utf-8'))
spec1 = d['spec1_cross_section']

for key in ['full', 'compact']:
    fm = spec1.get(key)
    if not fm:
        continue
    print('=== spec1.' + key, 'n=', fm.get('n'), 'r2=', fm.get('r2'))
    for k, v in fm.get('coef', {}).items():
        print('  %-18s b=%+.4f  t=%+.2f  p=%.4f' % (k, v['b'], v['t'], v['p']))

# 面板全模型
spec2 = d['spec2_panel']
fm2 = spec2.get('full') or spec2.get('compact')
if fm2:
    print('\n=== spec2.full n=', fm2.get('n'), 'r2=', fm2.get('r2'))
    for k, v in fm2.get('coef', {}).items():
        print('  %-18s b=%+.4f  t=%+.2f  p=%.4f' % (k, v['b'], v['t'], v['p']))

# diag
print('\n=== diag:', json.dumps(d.get('diag', {}), ensure_ascii=False)[:600])
