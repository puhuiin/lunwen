import re

html = open(r'd:\Desktop\基金经理行为分析研究\指标总表_五层框架.html', encoding='utf-8').read()
m = re.search(r'<table>.*?</table>', html, re.S)
tbl = m.group(0)
rows = re.findall(r'<tr>.*?</tr>', tbl, re.S)
print('total tr:', len(rows))

pending = 0
ok = True
for i, r in enumerate(rows):
    rm = re.search(r'rowspan="(\d+)"', r)
    cells = len(re.findall(r'<td', r))
    eff = cells + (1 if pending > 0 else 0)
    if pending > 0:
        pending -= 1
    if rm:
        pending = int(rm.group(1)) - 1
        badge = re.search(r'badge (l\d)', r)
        print('row%d: layer %s rowspan=%s' % (i, badge.group(1) if badge else '?', rm.group(1)))
    if i > 0 and eff != 5:
        ok = False
        print('row%d: eff cells=%d != 5  <-- MISMATCH' % (i, eff))
print('STRUCTURE OK' if ok else 'STRUCTURE BROKEN')
