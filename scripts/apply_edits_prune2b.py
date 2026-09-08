# -*- coding: utf-8 -*-
"""prune2b: 修补 prune2 中两处因 &gt; 与全/半角括号未命中而遗留的单边残留。"""
import re

REPORT = r"D:/Desktop/基金经理行为分析研究/实证结果完整报告与论文写作指南.html"

with open(REPORT, encoding="utf-8") as f:
    s = f.read()
orig = s

# 1) L3 总结表单元格：买卖分解符号相反 -> 双边 ns（N=200 受限）
pat1 = r'双边 ns；买卖分解符号相反.*?覆盖）'
s, c1 = re.subn(pat1, '双边 ns（N=200 受限）', s)
print(f"[1] L3 sumtab cell: {c1} 次")

# 2) 论文如何呈现 box: 去掉 (2) 买卖分解 作为核心发现
pat2 = r'主回归表列 .1. 双边 TO、.2. 买卖分解，把.买正卖负、符号相反.作为核心发现用<b>加粗异号</b>凸显'
s, c2 = re.subn(pat2, '主回归表以双边 TO_two_sided 为规范测度，并附 SDI（选择性交易）作为交易行为轴', s)
print(f"[2] pres box part2: {c2} 次")

# 3) KPI 卡片: 买卖不对称有粒度价值 -> SDI 选择性有解释力
old3 = '受覆盖限制偏弱；买卖不对称有粒度价值'
new3 = '受覆盖限制偏弱；SDI 选择性有解释力'
c3 = s.count(old3)
s = s.replace(old3, new3)
print(f"[3] KPI card: {c3} 次")

with open(REPORT, "w", encoding="utf-8") as f:
    f.write(s)
print(f"[INFO] 长度 {len(orig)} -> {len(s)}")
print("DONE")
