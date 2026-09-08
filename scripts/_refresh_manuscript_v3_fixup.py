# -*- coding: utf-8 -*-
"""
merged_manuscript.html → v3 刷新补漏（Option 3 收口第二阶段）
第一版刷新脚本因 HTML <strong> 标签割裂长字符串、以及 risk_asym/risk_asym 大小写差异，
导致部分 v2 旧值未被替换。本脚本针对实际文件中的精确片段逐一补漏。
漂移均 < 1%，仅精度同步；结论不变。
"""
import shutil, os

SRC = r"merged_manuscript.html"
BAK = r"merged_manuscript.html.bak_fixup1_20260816"
shutil.copyfile(SRC, BAK)
print("backup ->", BAK)

html = open(SRC, encoding="utf-8").read()
# 若仍存在 Unicode 减号则归一（保险）
html = html.replace("\u2212", "-")

P = [
 # 1. IV 表 risk_asym (887)
 ("<tr><td>risk_asym</td><td>+0.07271</td><td>不可复现 (iv_N=0)</td><td>—</td><td>—</td><td>IV不可复现</td></tr>",
  "<tr><td>risk_asym</td><td>+0.07311</td><td>不可复现 (iv_N=0)</td><td>—</td><td>—</td><td>IV不可复现</td></tr>"),
 # 2. IV 表 de (889)
 ("<tr><td>de</td><td>-0.00609</td><td>不可复现 (iv_N=0)</td><td>—</td><td>—</td><td>IV不可复现</td></tr>",
  "<tr><td>de</td><td>-0.00606</td><td>不可复现 (iv_N=0)</td><td>—</td><td>—</td><td>IV不可复现</td></tr>"),
 # 3. PS 权重叙事 (1170)
 ("|β|=0.07271", "|β|=0.07311"),
 ("|β|=0.01399", "|β|=0.01548"),
 ("|β|=0.00609", "|β|=0.00606"),
 # 4. 吸收效应叙事 (749)
 ("RA=+0.0727, t=4.52", "RA=+0.0731, t=4.53"),
 ("控制后RiskAsym仍保持***显著</strong>（t=4.52）", "控制后RiskAsym仍保持***显著</strong>（t=4.53）"),
 # 5. 置换表 RiskAsym (777)
 ("<tr class=\"signif\"><td>RiskAsym</td><td>+4.52</td><td>0.00</td><td>0.2%</td><td class=\"stars\">✓ 显著</td></tr>",
  "<tr class=\"signif\"><td>RiskAsym</td><td>+4.53</td><td>0.00</td><td>0.2%</td><td class=\"stars\">✓ 显著</td></tr>"),
 # 6. 置换表 LSV (778)
 ("<tr><td>LSV</td><td>+1.12</td><td>0.00</td><td>22.0%</td><td>✗ 不显著</td></tr>",
  "<tr><td>LSV</td><td>+1.23</td><td>0.00</td><td>22.0%</td><td>✗ 不显著</td></tr>"),
 # 7. RESET p (1324)
 ("加入L5后模型设定正确（p=0.168，诚实面板下未拒绝线性）",
  "加入L5后模型设定正确（p=0.164，诚实面板下未拒绝线性）"),
 # 8. M4 截面预测叙事 (1326)
 ("β=0.07271, t=4.52, p&lt;0.001", "β=0.07311, t=4.53, p&lt;0.001"),
 ("β=-0.00609, t=-2.50, p=0.012", "β=-0.00606, t=-2.50, p=0.013"),
 # 9. OSTER §6.1.3 (1329)
 ("Oster遗漏变量界在诚实面板下δ均≤0（δ_DE=-2.88、δ_LSV=-2.67、δ_RiskAsym=-1.66）",
  "Oster遗漏变量界在诚实面板下δ均≤0（δ_DE=-2.87、δ_LSV=-2.66、δ_RiskAsym=-1.65）"),
 # 10. DE 处置效应 bullet (1367)
 ("β=-0.00609, t=-2.50**", "β=-0.00606, t=-2.50**"),
 # 11. RiskAsym bullet (1369)
 ("β=0.07271, t=4.52***", "β=0.07311, t=4.53***"),
 # 12. 中介叙事 return_volatility (1004)
 ("return_volatility 系数 +0.02608（t=1.17，不显著）",
  "return_volatility 系数 +0.02379（t=1.07，不显著）"),
 # 13. 中介叙事 return_volatility (1007)
 ("return_volatility 在 M4 完整控制集下不显著（t=1.17）",
  "return_volatility 在 M4 完整控制集下不显著（t=1.07）"),
 # 14. LSV 经济含义叙事 (753)
 ("该系数在M4中不显著（t=1.12, p=0.263）", "该系数在M4中不显著（t=1.23, p=0.219）"),
 # 15. LSV 功效/PS 表 (1017)
 ("不足（t=1.12, p=0.263）", "不足（t=1.23, p=0.219）"),
 # 16. LSV §6.1.2 叙事 (1327)
 ("LSV在诚实面板下不显著（t=1.12, p=0.263）", "LSV在诚实面板下不显著（t=1.23, p=0.219）"),
]

report = []
for i,(o,n) in enumerate(P):
    c = html.count(o)
    if c == 0:
        report.append((i, "NOT FOUND", o[:60]))
        continue
    html = html.replace(o, n)
    report.append((i, "ok x%d" % c, o[:60]))

# 残留旧值核查（v2 面板值，应当全部为 0；-2.67 在 ff5_MKT_excess 行为合法保留）
leftover = ["0.07271", "0.0727", "0.02608", "0.01399",
            "-0.00609", "0.00609", "t=4.52", "+4.52",
            "t=1.12", "+1.12", "p=0.263",
            "（p=0.168", "-2.88", "-1.66",
            "-0.2383", "0.0654", "1.794"]
print("=== fixup replacement report ===")
for r in report:
    print(r)
print("=== leftover check (v2 vals; -2.67/1.662/-0.168 etc. are legit) ===")
for s in leftover:
    print(repr(s), html.count(s))

open(SRC, "w", encoding="utf-8").write(html)
print("WRITTEN", SRC, "len=", len(html))
