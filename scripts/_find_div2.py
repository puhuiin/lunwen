# -*- coding: utf-8 -*-
import re
fn = r"D:/Desktop/基金经理行为分析研究/回归结果展示与解读_v4_2026-08-17.html"
text = open(fn, encoding="utf-8").read()
lines = text.split("\n")
with open(r"D:/Desktop/基金经理行为分析研究/_find_div2_out.txt", "w", encoding="utf-8") as g:
    for i, l in enumerate(lines, 1):
        opens = [(m.start(), m.group(0)) for m in re.finditer(r"<div\b[^>]*>", l)]
        closes = [(m.start(), m.group(0)) for m in re.finditer(r"</div>", l)]
        stray = re.finditer(r"<div\b(?![^>]*>)", l)  # <div not followed by a proper tag close
        stray_list = [m.group(0) for m in stray]
        if stray_list:
            g.write(f"line {i}: STRAY <div (no proper tag): {stray_list} | {l.strip()[:120]}\n")
        # also flag any '<div' that's inside quoted attribute or text
        for m in re.finditer(r"<div", l):
            pass
    # count all '<div' (substring) and '</div>'
    g.write(f"\nsubstring '<div' count = {text.count('<div')}\n")
    g.write(f"proper '<div...>' count = {len(re.findall(r'<div\\b[^>]*>', text))}\n")
    g.write(f"'</div>' count = {text.count('</div>')}\n")
