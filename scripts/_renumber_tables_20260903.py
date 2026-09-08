# -*- coding: utf-8 -*-
"""表号顺延（2026-09-03）：插入新「表 2 逐年统计性描述」后，原表 2–9 → 表 3–10。

同时修正一处历史遗留的指向错误：群体画像段原写「（表 5）」，
实际指向的是「群体画像：Top5% 与 Bottom5% 的能力维度差异」表（原表 7 → 新表 8）。

所有替换串均带标题/上下文，保证唯一且不构成链式误替换。
"""
import io, os, sys

P = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                 'scripts', '_draft_docx_20260826.py')
src = io.open(P, encoding='utf-8').read()

PAIRS = [
    # --- caption 顺延 ---
    ("caption(doc, '表 3  因变量口径对照", "caption(doc, '表 4  因变量口径对照"),
    ("caption(doc, '表 4  能力维度得分", "caption(doc, '表 5  能力维度得分"),
    ("caption(doc, '表 5  入选指标的详细显著性", "caption(doc, '表 6  入选指标的详细显著性"),
    ("caption(doc, '表 6  改进主动份额", "caption(doc, '表 7  改进主动份额"),
    ("caption(doc, '表 7  群体画像", "caption(doc, '表 8  群体画像"),
    ("caption(doc, '表 8  综合能力五分组背景", "caption(doc, '表 9  综合能力五分组背景"),
    ("caption(doc, '表 9  典型画像", "caption(doc, '表 10  典型画像"),
    # --- 正文引用顺延 ---
    ("单维结果见表 5）", "单维结果见表 6）"),
    ("（表 6，前五道为回归口径", "（表 7，前五道为回归口径"),
    ("（见表 3）；", "（见表 4）；"),
    ("综合能力五分组的背景对照（表 8）", "综合能力五分组的背景对照（表 9）"),
    ("故表 8 占比按有效样本为分母", "故表 9 占比按有效样本为分母"),
    ("见表 9 与图 3。", "见表 10 与图 3。"),
    # --- 纠错：群体画像段原指向表 5，实为群体画像表 ---
    ("按六个能力维度比较两组得分（表 5）", "按六个能力维度比较两组得分（表 8）"),
    # --- 注释同步 ---
    ("→ 表 6 占比改用有效样本分母", "→ 表 7 占比改用有效样本分母"),
]

for old, new in PAIRS:
    n = src.count(old)
    assert n == 1, f'匹配数异常 {n}: {old!r}'
    src = src.replace(old, new)

io.open(P, 'w', encoding='utf-8').write(src)
print(f'OK：{len(PAIRS)} 处表号已更新')
