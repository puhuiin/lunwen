# -*- coding: utf-8 -*-
"""
merged_manuscript.html → v3 刷新补漏（第二阶段：牛熊子样本）
第一/二补漏脚本因第二张牛熊表（含"理论解释"列的 5 列表）与多处叙事未覆盖，
导致牛熊旧值 -2.39 / -1.07 / 0.043 / -0.0011 / 0.0648 / 0.1027 / 4.06 / 3.70 残留。
本脚本按 v3 牛熊值（BULL: de -0.0066 t-2.36 / lsv +0.0014 t0.10 / RA +0.0651 t4.08；
BEAR: de -0.0049 t-1.11 / lsv +0.0424 t2.32 / RA +0.1034 t3.74）补漏。
"""
import shutil, os

SRC = r"merged_manuscript.html"
BAK = r"merged_manuscript.html.bak_fixup2_20260816"
shutil.copyfile(SRC, BAK)
print("backup ->", BAK)

html = open(SRC, encoding="utf-8").read()
html = html.replace("\u2212", "-")

P = [
 # 1. 第二张牛熊表 RiskAsym 行 (1135)
 ("+0.0648 (4.06)***</td><td>+0.1027 (3.70)***",
  "+0.0651 (4.08)***</td><td>+0.1034 (3.74)***"),
 # 2. 第二张牛熊表 LSV 行 (1136)
 ("-0.0011 (-0.07) n.s.</td><td>+0.043 (2.36)**",
  "+0.0014 (0.10) n.s.</td><td>+0.0424 (2.32)**"),
 # 3. 第二张牛熊表 DE 行 (1137)
 ("-0.0066 (-2.39)**</td><td>-0.0047 (-1.07) n.s.",
  "-0.0066 (-2.36)**</td><td>-0.0049 (-1.11) n.s."),
 # 4. §4.4.2 callout LSV 部分 (794)
 ("LSV仅在熊市显著</strong>（+0.043, t=2.36），在牛市中系数近乎零且不显著（-0.0011, t=-0.07）",
  "LSV仅在熊市显著</strong>（+0.0424, t=2.32），在牛市中系数近乎零且不显著（+0.0014, t=0.10）"),
 # 5. §4.4.2 callout DE 部分 (794)
 ("DE仅在牛市显著</strong>（-0.0066, t=-2.39），熊市中反而弱化至不显著（-0.0047, t=-1.07）",
  "DE仅在牛市显著</strong>（-0.0066, t=-2.36），熊市中反而弱化至不显著（-0.0049, t=-1.11）"),
 # 6. §4.4.x 叙事 DE (1143)
 ("DE在<b>牛市</b>显著（t=-2.39）、熊市不显著（t=-1.07）",
  "DE在<b>牛市</b>显著（t=-2.36）、熊市不显著（t=-1.11）"),
 # 7. §6.2.3 RiskAsym 叙事 (1372)
 ("RiskAsym两市均显著且牛市更强（牛市t=4.06 vs 熊市t=3.70，均***）",
  "RiskAsym两市均显著且牛市更强（牛市t=4.08 vs 熊市t=3.74，均***）"),
 # 8. §6.2.3 LSV 叙事 (1372)
 ("LSV仅熊市显著（熊市t=2.36**, 牛市不显著）",
  "LSV仅熊市显著（熊市t=2.32**, 牛市不显著）"),
 # 9. §6.2.3 DE 叙事 (1372)
 ("DE仅牛市显著（牛市t=-2.39**, 熊市不显著）",
  "DE仅牛市显著（牛市t=-2.36**, 熊市不显著）"),
]

report = []
for i,(o,n) in enumerate(P):
    c = html.count(o)
    if c == 0:
        report.append((i, "NOT FOUND", o[:60]))
        continue
    html = html.replace(o, n)
    report.append((i, "ok x%d" % c, o[:60]))

# 牛熊旧值残留核查（应全为 0）
bb_old = ["-2.39", "-1.07", "0.043 (2.36)", "-0.0011", "0.0648", "0.1027",
          "(4.06)", "(3.70)", "t=2.36**", "t=-2.39", "t=4.06", "t=3.70",
          "+0.043", "0.043,", "2.36）", "2.36**,", "4.06 vs", "3.70，"]
# 牛熊新值应出现
bb_new = ["-2.36", "-1.11", "+0.0424", "+0.0014", "0.0651", "0.1034",
          "(4.08)", "(3.74)", "t=2.32", "t=-2.36", "t=4.08", "t=3.74",
          "+0.0424 (2.32)", "+0.0014 (0.10)", "0.0049 (-1.11)"]

print("=== fixup2 replacement report ===")
for r in report:
    print(r)
print("=== bull-bear OLD (expect all 0) ===")
bad=0
for s in bb_old:
    c=html.count(s); 
    if c: bad+=1
    print(repr(s), c)
print("=== bull-bear NEW (expect >0) ===")
miss=0
for s in bb_new:
    c=html.count(s)
    if c==0: miss+=1
    print(repr(s), c)
print("\nSUMMARY: bb_old_nonzero=%d  bb_new_missing=%d"%(bad,miss))

open(SRC, "w", encoding="utf-8").write(html)
print("WRITTEN", SRC, "len=", len(html))
