# -*- coding: utf-8 -*-
import re, os, json

BASE = r'd:\Desktop\基金经理行为分析研究'
SRC = os.path.join(BASE, 'reports', 'merged_manuscript.html')

t = open(SRC, encoding='utf-8', errors='ignore').read()
t = re.sub(r'<[^>]+>', '\n', t)
lines = [re.sub(r'\s+', ' ', x).strip() for x in t.split('\n')]
refs = {}
for x in lines:
    m = re.match(r'^\[(\d+)\]\s*(.+)$', x)
    if m and len(x) > 40 and ('[J]' in x or '[M]' in x or '[R]' in x):
        refs[int(m.group(1))] = m.group(2)

print('提取条数:', len(refs))
print('编号范围:', min(refs), '-', max(refs))
missing = [i for i in range(min(refs), max(refs) + 1) if i not in refs]
print('缺号:', missing)
for k in sorted(refs):
    print(k, '|', refs[k])

json.dump(refs, open(os.path.join(BASE, 'output', '文献底库_merged_2026-08-26.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=2)
