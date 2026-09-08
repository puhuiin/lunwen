# -*- coding: utf-8 -*-
"""遗留工程项修复（2026-08-30）

处理论文审查报告遗留的 C 级脚本工程项：
  C5  _timing_metric_20260826.py 与 _timing_robust_20260826.py 写同名文件，
      前者输出无 timing 列，若后运行会覆盖后者并致下游 KeyError（8-27 已踩坑）。
      修复：前者输出改名 → 择时系数_季度HM_原始_2026-08-26.csv
  C6  _timing_metric_20260826.py 注释把 HM γ 符号说反（实现 timing=-γ 正确，仅注释错）。
  C4  方法详解中 oc_conf 输入口径表述（若仍写"200 只"需改为 TO_wind_clean 98.5%）。
"""
import io
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(BASE, 'scripts')
REPORTS = os.path.join(BASE, 'reports')
NL = chr(10)


def rd(p):
    with io.open(p, encoding='utf-8') as f:
        return f.read()


def wr(p, s):
    with io.open(p, 'w', encoding='utf-8') as f:
        f.write(s)


def backup(p):
    bak = p + '.bak_20260830'
    if not os.path.exists(bak):
        wr(bak, rd(p))
    return bak


changed = []

# ---------------- C5 + C6：_timing_metric_20260826.py ----------------
p = os.path.join(SCRIPTS, '_timing_metric_20260826.py')
s = rd(p)
orig = s

old_csv = "tim.reset_index().to_csv(os.path.join(OUT, '择时系数_季度HM_2026-08-26.csv'),"
new_csv = "tim.reset_index().to_csv(os.path.join(OUT, '择时系数_季度HM_原始_2026-08-26.csv'),"
if old_csv in s:
    s = s.replace(old_csv, new_csv, 1)
    changed.append('C5a 输出改名')

old_print = "print('\\n已保存 output/择时系数_季度HM_2026-08-26.csv')"
new_print = "print('\\n已保存 output/择时系数_季度HM_原始_2026-08-26.csv')"
if old_print in s:
    s = s.replace(old_print, new_print, 1)
    changed.append('C5b print 同步')

old_cmt = "         g_i > 0 表示市场下跌时基金实际暴露低于线性预期 = 下行保护能力"
new_cmt = (NL.join([
    "         g_i < 0 表示市场下跌时基金实际暴露低于线性预期 = 下行保护能力",
    "         注：下游统一用 timing = -g_i 取反，使数值越高表示保护越强；本文件输出",
    "         hm_gamma/tm_gamma 原始系数，写入 择时系数_季度HM_原始_2026-08-26.csv，",
    "         勿与 择时系数_季度HM_2026-08-26.csv（含 timing 列，由 _timing_robust 产出）混用。",
]))
if old_cmt in s:
    s = s.replace(old_cmt, new_cmt, 1)
    changed.append('C6 符号注释')

if s != orig:
    backup(p)
    wr(p, s)
    print('[OK] _timing_metric_20260826.py 已修改:', ', '.join(changed))
else:
    print('[SKIP] _timing_metric_20260826.py 无改动（可能已修）')

# ---------------- C5 补充：_timing_robust 加归属注释 ----------------
p2 = os.path.join(SCRIPTS, '_timing_robust_20260826.py')
s2 = rd(p2)
o2 = s2
old_w = "tim.reset_index().to_csv(os.path.join(OUT, '择时系数_季度HM_2026-08-26.csv'), index=False, encoding='utf-8-sig')"
new_w = (NL.join([
    "# 本文件是下游唯一依赖的主产物：必须含 timing 列",
    "# （_harden_20260827 / _improve_indicators_20260827 均读 [['timing']]）。",
    "# 注意：_timing_metric_20260826.py 产出无 timing 列的原始系数，已改名为",
    "# 择时系数_季度HM_原始_2026-08-26.csv，不再覆盖本文件。",
    old_w,
]))
if old_w in s2 and '本文件是下游唯一依赖的主产物' not in s2:
    s2 = s2.replace(old_w, new_w, 1)
    backup(p2)
    wr(p2, s2)
    print('[OK] _timing_robust_20260826.py 已加归属注释')
else:
    print('[SKIP] _timing_robust_20260826.py 无改动')

# ---------------- C4：检查方法详解 oc_conf 口径 ----------------
det = os.path.join(REPORTS, '方法详解_2026-08-26.html')
d = rd(det)
hits = []
for line in d.split(NL):
    if '200 只' in line and ('oc_conf' in line or '换手' in line or '过度自信' in line):
        hits.append(line.strip()[:160])
print('[C4] 方法详解中「200 只」与换手/oc_conf 同现的行数:', len(hits))
for h in hits[:5]:
    print('   -', h)

print('[DONE] 改动项:', changed)
