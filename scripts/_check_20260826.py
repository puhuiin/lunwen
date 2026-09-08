# -*- coding: utf-8 -*-
import io
import os
import re

SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   'reports', '投资经理行为画像_2026-08-26.html')
h = io.open(SRC, encoding='utf-8').read()

print('chars:', len(h))
print('table pairs:', h.count('<table>'), h.count('</table>'))
print('tbody pairs:', h.count('<tbody>'), h.count('</tbody>'))
print('tr pairs:', h.count('<tr>') + h.count('<tr style'), h.count('</tr>'))
print('literal %% left:', h.count('%%'))
print('None left:', h.count('None'), ' nan left:', h.count('nan'))

CELL = re.compile(r'<t[dh]([^>]*)>')
bad = 0
for i, t in enumerate(re.findall(r'<table>.*?</table>', h, re.S), 1):
    head = re.search(r'<thead>.*?</thead>', t, re.S)
    body = re.search(r'<tbody>.*?</tbody>', t, re.S)
    if not head or not body:
        print('table %d: thead/tbody missing' % i)
        bad += 1
        continue
    th = len(re.findall(r'<th[ >]', head.group()))
    rows = re.findall(r'<tr[^>]*>.*?</tr>', body.group(), re.S)
    carry = [0] * (th + 8)
    for j, row in enumerate(rows, 1):
        col = 0
        while col < len(carry) and carry[col] > 0:
            col += 1
        used = 0
        for attr in CELL.findall(row):
            cs = re.search(r'colspan="(\d+)"', attr)
            rs = re.search(r'rowspan="(\d+)"', attr)
            cs = int(cs.group(1)) if cs else 1
            rs = int(rs.group(1)) if rs else 1
            while col < len(carry) and carry[col] > 0:
                col += 1
            for c in range(col, min(col + cs, len(carry))):
                carry[c] = rs
            col += cs
            used += cs
        filled = sum(1 for c in carry[:th] if c > 0)
        occupied = used + sum(1 for c in carry[:th] if c > 1) - sum(
            1 for c in carry[:th] if c > 1)
        if used + (th - used) != th:
            pass
        span_in = sum(1 for c in range(th) if carry[c] > 1)
        if filled != th:
            print('table %d row %d: th=%d filled=%d (td=%d)' % (i, j, th, filled, used))
            bad += 1
        carry = [max(0, c - 1) for c in carry]
print('column mismatch rows:', bad)

print('cell-level nan:', len(re.findall(r'>\s*nan\s*<', h)))
print('cell-level None:', len(re.findall(r'>\s*None\s*<', h)))
print('dash num cells:', len(re.findall(r'class="num">—<', h)))
print('--- h2 ---')
for x in re.findall(r'<h2>(.*?)</h2>', h):
    print('   ', x)
print('--- h3 ---')
for x in re.findall(r'<h3>(.*?)</h3>', h):
    print('   ', x)

