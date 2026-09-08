# -*- coding: utf-8 -*-
"""merged_manuscript.html → v3 补漏（第四阶段：§6 总结表牛熊 cell）
line 1337 总结表仍含旧牛市 t=4.06（应为 4.08）。另做全文件最终残留扫描。"""
import shutil, os
SRC = r"merged_manuscript.html"
BAK = r"merged_manuscript.html.bak_fixup4_20260816"
shutil.copyfile(SRC, BAK)
print("backup ->", BAK)
html = open(SRC, encoding="utf-8").read()
html = html.replace("\u2212", "-")

# line 1337 牛熊总结 cell
old_cell = "RiskAsym两市均***（牛市t=4.06更强）；LSV仅熊市**（牛市不显著）；DE仅牛市**（熊市不显著）"
new_cell = "RiskAsym两市均***（牛市t=4.08更强）；LSV仅熊市**（牛市不显著）；DE仅牛市**（熊市不显著）"
c = html.count(old_cell)
print("1337 cell match x%d" % c)
html = html.replace(old_cell, new_cell)

# ============ 最终全文件残留扫描（v2 面板专属旧值） ============
# 牛熊
bb_old = ["-2.39","-1.07","0.043 (2.36)","-0.0011","0.0648","0.1027",
          "(4.06)","(3.70)","t=4.06","t=3.70","t=2.36**","t=-2.39",
          "牛市t=4.06","2.36**,","0.043,","+0.043"]
# M4 系数 / 诊断
m4_old = ["0.07271","0.0727（","0.02608","0.01399","-0.00609","0.00609",
          "t=4.52","+4.52","t=1.12","+1.12","p=0.263","（p=0.168",
          "-2.88","-1.66","-0.2383","0.0654","1.794","0.0596","0.0244",
          "2.39","0.0074"]
# 合法保留项（核对未被误清）
legit = ["-2.67","1.662","-0.168","-3.912","0.659","0.785","-0.127",
         "+0.089","0.205","0.00075","0.01676","-0.00155"]
print("=== bull-bear OLD (expect 0) ===")
b=0
for s in bb_old:
    n=html.count(s)
    if n: b+=1
    print("  %-14s %d"%(s,n))
print("=== M4/diag OLD (expect 0) ===")
m=0
for s in m4_old:
    n=html.count(s)
    if n: m+=1
    print("  %-14s %d"%(s,n))
print("=== LEGIT preserved (should be >0) ===")
for s in legit:
    print("  %-14s %d"%(s,html.count(s)))
print("\nSUMMARY: bb_old_nonzero=%d  m4_old_nonzero=%d"%(b,m))
open(SRC,"w",encoding="utf-8").write(html)
print("WRITTEN",SRC,"len=",len(html))
