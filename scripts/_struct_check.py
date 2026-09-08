# -*- coding: utf-8 -*-
"""HTML 结构检查：<table> 直系子元素合法性、img src 路径有效性"""
import re
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(BASE, "merged_manuscript.html")

with open(PATH, encoding="utf-8") as f:
    txt = f.read()

def line_of(pos):
    return txt.count("\n", 0, pos) + 1

problems = []

# ---------- 1. <table> 开标签后、首个合法子元素前的非法内容 ----------
# 合法首子元素: caption / colgroup / thead / tbody / tfoot / tr / 注释
LEGAL_FIRST = re.compile(r"^\s*(<!--.*?-->\s*|<(?:caption|colgroup|thead|tbody|tfoot|tr)\b)", re.S)
for m in re.finditer(r"<table\b[^>]*>", txt):
    tail = txt[m.end():m.end() + 600]
    lm = LEGAL_FIRST.match(tail)
    if not lm:
        snippet = tail[:120].replace("\n", "⏎")
        problems.append((line_of(m.end()), "table 开标签后出现非法元素(应在 caption 前)",
                         snippet))

# ---------- 2. </caption> 与下一合法兄弟之间的非法元素 ----------
LEGAL_AFTER_CAPTION = re.compile(r"^(\s*|<!--.*?-->)((?:<(?:colgroup|thead|tbody|tfoot|tr)\b)|</table)", re.S)
for m in re.finditer(r"</caption\s*>", txt):
    tail = txt[m.end():m.end() + 400]
    if not LEGAL_AFTER_CAPTION.match(tail):
        snippet = tail[:120].replace("\n", "⏎")
        problems.append((line_of(m.end()), "</caption> 之后出现非法元素", snippet))

# ---------- 3. 表尾：最后一个 </tr> 与 </table> 之间 ----------
for m in re.finditer(r"</table\s*>", txt):
    head = txt[max(m.start() - 300, 0):m.start()]
    hm = re.search(r"(</tr\s*>\s*|</tfoot\s*>\s*|</tbody\s*>\s*)$", head)
    if not hm:
        snippet = head[-120:].replace("\n", "⏎")
        problems.append((line_of(m.start()), "</table> 前出现非法结尾元素", snippet))

# ---------- 4. img src 路径有效性 ----------
missing_img = []
for m in re.finditer(r"<img[^>]*?\bsrc=[\"']([^\"']+)[\"']", txt):
    src = m.group(1).strip()
    if src.startswith(("http://", "https://", "data:")):
        continue
    cand = os.path.join(BASE, *src.split("/"))
    if not os.path.exists(cand):
        missing_img.append((line_of(m.start()), src))

# ---------- 汇总 ----------
if problems:
    print(f"[!] 结构问题 {len(problems)} 处:")
    seen = set()
    for ln, kind, snip in problems:
        key = (ln, kind)
        if key in seen:
            continue
        seen.add(key)
        print(f"    L{ln}: {kind}")
        print(f"        …{snip}…")
else:
    print("[OK] 未发现 table 内非法结构")

if missing_img:
    print(f"[!] 缺失图片 {len(missing_img)} 张:")
    for ln, src in missing_img:
        print(f"    L{ln}: {src}")
else:
    n_img = len(re.findall(r"<img[^>]*?\bsrc=", txt))
    print(f"[OK] 图片 src 全部存在（共 {n_img} 张）")
