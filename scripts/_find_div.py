# -*- coding: utf-8 -*-
import re
fn = r"D:/Desktop/基金经理行为分析研究/回归结果展示与解读_v4_2026-08-17.html"
lines = open(fn, encoding="utf-8").read().split("\n")
stack = []
for i, l in enumerate(lines, 1):
    for m in re.finditer(r"<div\b[^>]*>", l):
        stack.append((i, m.group(0)))
    for m in re.finditer(r"</div>", l):
        if stack:
            stack.pop()
        else:
            print("EXTRA CLOSE at line", i)
with open(r"D:/Desktop/基金经理行为分析研究/_find_div_out.txt", "w", encoding="utf-8") as g:
    g.write("unmatched opens (innermost last):\n")
    for s in stack[-6:]:
        g.write(f"  line {s[0]} -> {s[1][:80]}\n")
