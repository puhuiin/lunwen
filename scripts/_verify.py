# -*- coding: utf-8 -*-
import re
t = open(r"D:/Desktop/基金经理行为分析研究/回归结果展示与解读_v4_2026-08-17.html", encoding="utf-8").read()
o = len(re.findall(r"<div\b", t)); c = len(re.findall(r"</div>", t))
with open(r"D:/Desktop/基金经理行为分析研究/_verify_out.txt", "w", encoding="utf-8") as g:
    g.write(f"div_open={o} div_close={c} diff={o-c}\n")
    g.write(f"len={len(t)}\n")
    g.write(f"svg_open={t.count('<svg')} svg_close={t.count('</svg>')}\n")
    g.write(f"has_gA={('gA' in t)} has_gC={('gC' in t)}\n")
    g.write(f"has_FOREST_label={'基金年龄对数' in t}\n")
    g.write(f"has_cross_grid={'cv-cell' in t}\n")
    g.write(f"has_mechanism={'AS 为负' in t or '主动份额 AS' in t}\n")
