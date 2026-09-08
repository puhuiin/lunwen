# -*- coding: utf-8 -*-
import re
fn = r"D:/Desktop/基金经理行为分析研究/回归结果展示与解读_v4_2026-08-17.html"
lines = open(fn, encoding="utf-8").read().split("\n")
opens = 0
closes = 0
stack = []
for i, l in enumerate(lines, 1):
    for m in re.finditer(r"<div\b[^>]*>", l):
        opens += 1
        stack.append(i)
    for m in re.finditer(r"</div>", l):
        closes += 1
        if stack:
            stack.pop()
        else:
            print("EXTRA CLOSE line", i)
with open(r"D:/Desktop/基金经理行为分析研究/_divcheck_out.txt", "w", encoding="utf-8") as g:
    g.write(f"opens={opens} closes={closes} unmatched={len(stack)}\n")
    g.write(f"remaining stack tail: {stack[-3:]}\n")
