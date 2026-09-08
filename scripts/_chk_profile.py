# -*- coding: utf-8 -*-
import re
fn = r"D:/Desktop/基金经理行为分析研究/基金经理能力画像与业绩评价.html"
lines = open(fn, encoding="utf-8").read().split("\n")
opens = 0; closes = 0; stack = []
for i, l in enumerate(lines, 1):
    for m in re.finditer(r"<div\b[^>]*>", l):
        opens += 1; stack.append(i)
    for m in re.finditer(r"</div>", l):
        closes += 1
        if stack: stack.pop()
        else: print("EXTRA CLOSE line", i)
svg_o = len(re.findall(r"<svg\b", "".join(lines)))
svg_c = len(re.findall(r"</svg>", "".join(lines)))
with open(r"D:/Desktop/基金经理行为分析研究/_chk_profile_out.txt", "w", encoding="utf-8") as g:
    g.write(f"div opens={opens} closes={closes} unmatched={len(stack)}\n")
    g.write(f"svg open={svg_o} close={svg_c}\n")
    g.write(f"has mcard-grid={'mcard-grid' in ''.join(lines)}\n")
    g.write(f"has cw-title={'cw-title' in ''.join(lines)}\n")
    g.write(f"has polygon title={'<title>' in ''.join(lines)}\n")
    g.write(f"card count={'mcard\" style' in ''.join(lines)}\n")
