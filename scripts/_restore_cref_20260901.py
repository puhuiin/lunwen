# -*- coding: utf-8 -*-
"""恢复章节标题的结论编号标注（2026-09-01）

背景：8-30 深夜那轮重生成后，reports/论文初稿_2026-08-31.docx 的六个二级标题
带「（对应结论 X、Y）」标注，但 _draft_docx_20260826.py 当前版本已无此标注，
导致 xcheck「结论 X 三产物均现」一役掉 11 项（192 中 187→176）。
本脚本把标注写回生成脚本；同时把 8-29 补入的 D9（Brinson）与 X4（TM_β₂/idio_vol）
补进 3.4 节标注（二者正文在 3.4 节段中讨论）。
"""
import io
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = os.path.join(ROOT, 'scripts', '_draft_docx_20260826.py')

CREF = [
    ("heading(doc, '3.2  统计性描述', 2)",
     "heading(doc, '3.2  统计性描述（对应结论 Q1、Q3）', 2)"),
    ("heading(doc, '3.3  检验手段：主要回归方程', 2)",
     "heading(doc, '3.3  检验手段：主要回归方程（对应结论 F3）', 2)"),
    ("heading(doc, '3.4  检验结果', 2)",
     "heading(doc, '3.4  检验结果（对应结论 D1、D5、D6、D7、D9、X1、X2、X3、X4）', 2)"),
    ("heading(doc, '3.5  两项口径稳健性检验', 2)",
     "heading(doc, '3.5  两项口径稳健性检验（对应结论 F1、F2、D2、D3、Q2、D8）', 2)"),
    ("heading(doc, '4.1  群体画像', 2)",
     "heading(doc, '4.1  群体画像（对应结论 P1、P2、P3）', 2)"),
    ("heading(doc, '4.2  典型画像', 2)",
     "heading(doc, '4.2  典型画像（对应结论 P4）', 2)"),
]

src = io.open(P, encoding='utf-8').read()
bak = P + '.bak_cref_20260901'
if not os.path.exists(bak):
    io.open(bak, 'w', encoding='utf-8').write(src)

hit = 0
for old, new in CREF:
    c = src.count(old)
    if c != 1:
        print('  !! 命中 %d 次（应为 1）：%s' % (c, old))
        continue
    src = src.replace(old, new, 1)
    hit += 1

io.open(P, 'w', encoding='utf-8').write(src)
print('标题标注恢复 %d/%d' % (hit, len(CREF)))
sys.exit(0 if hit == len(CREF) else 1)
