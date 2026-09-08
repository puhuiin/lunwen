# -*- coding: utf-8 -*-
"""merged_manuscript.html → v3 补漏（第三阶段：§6.2.3 牛熊叙事）
fixup2 的 #6/#7/#8 因 <strong> 闭合标签位于标签词与括号之间而未命中。
本脚本按实际 HTML 上下文补漏 line 1372。"""
import shutil, os
SRC = r"merged_manuscript.html"
BAK = r"merged_manuscript.html.bak_fixup3_20260816"
shutil.copyfile(SRC, BAK)
print("backup ->", BAK)
html = open(SRC, encoding="utf-8").read()
html = html.replace("\u2212", "-")
P = [
 ("RiskAsym两市均显著且牛市更强</strong>（牛市t=4.06 vs 熊市t=3.70，均***）",
  "RiskAsym两市均显著且牛市更强</strong>（牛市t=4.08 vs 熊市t=3.74，均***）"),
 ("LSV仅熊市显著</strong>（熊市t=2.36**, 牛市不显著）",
  "LSV仅熊市显著</strong>（熊市t=2.32**, 牛市不显著）"),
 ("DE仅牛市显著</strong>（牛市t=-2.39**, 熊市不显著）",
  "DE仅牛市显著</strong>（牛市t=-2.36**, 熊市不显著）"),
]
rep=[]
for i,(o,n) in enumerate(P):
    c=html.count(o)
    if c==0:
        rep.append((i,"NOT FOUND",o[:60])); continue
    html=html.replace(o,n); rep.append((i,"ok x%d"%c,o[:60]))
bb_old=["-2.39","t=2.36**","t=-2.39","t=4.06","t=3.70","2.36）","2.36**,","4.06 vs","3.70，"]
print("=== fixup3 report ===")
for r in rep: print(r)
print("=== bull-bear OLD (expect all 0) ===")
bad=0
for s in bb_old:
    c=html.count(s)
    if c: bad+=1
    print(repr(s),c)
print("SUMMARY bb_old_nonzero=%d"%bad)
open(SRC,"w",encoding="utf-8").write(html)
print("WRITTEN",SRC,"len=",len(html))
