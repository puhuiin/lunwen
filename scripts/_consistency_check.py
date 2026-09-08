# -*- coding: utf-8 -*-
"""全文一致性审计 v2：章节编号连续性、图表首引顺序、显著性对照复核、千分位规范、重复句、表格有效列宽
v2 修正：① 首引顺序排除 caption 自身文本而非邻近引用；② 表格检查按 colspan 计算有效宽度；③ 千分位扫描屏蔽 <style>/公式/参考文献区
"""
import re
import os
from collections import Counter, OrderedDict

BASE = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(BASE, "merged_manuscript.html")

with open(PATH, encoding="utf-8") as f:
    txt = f.read()

def line_of(pos):
    return txt.count("\n", 0, pos) + 1

def strip_tags(s):
    return re.sub(r"<[^>]+>", "", s)

print("=" * 60)
print("一、章节编号连续性")
print("=" * 60)
heads = []
for m in re.finditer(r"<h([123])>(.*?)</h\1>", txt):
    t = strip_tags(m.group(2)).strip()
    nm = re.match(r"第([一二三四五六七八九十]+)章|^(\d+(?:\.\d+){0,2})", t)
    if nm:
        heads.append((m.group(1), nm.group(2) or nm.group(1), t, line_of(m.start())))

num_secs = [(lv, n, t, ln) for lv, n, t, ln in heads if re.match(r"^\d", n)]
by_parent = OrderedDict()
for lv, n, t, ln in num_secs:
    parts = n.split(".")
    parent = ".".join(parts[:-1]) if len(parts) > 1 else ""
    by_parent.setdefault(parent, []).append((int(parts[-1]), n, t, ln))

issues = 0
for parent, items in by_parent.items():
    nums = [x[0] for x in items]
    expect = list(range(nums[0], nums[0] + len(nums)))
    if nums != expect:
        issues += 1
        print(f"[!] {parent or '章'} 下编号不连续: {[x[1] for x in items]}")
if issues == 0:
    print(f"[OK] 全部 {len(num_secs)} 个数字型小节编号连续")

print()
print("=" * 60)
print("二、图表首引位置（正文首引不得晚于图表出现处）")
print("=" * 60)
# 收集 caption / fig-label 位置与其文本区间
cap_spans = []  # (tag, tag_start, span_start, span_end)
for m in re.finditer(r"<caption>\s*(表\d+-\d+)", txt):
    cap_spans.append((m.group(1), m.start(1), m.start(), m.end() + 60))
for m in re.finditer(r">(图\d+-\d+)<", txt):
    cap_spans.append((m.group(1), m.start(1), m.start() - 40, m.end() + 40))
cap_pos = {}
for tag, tpos, _, _ in cap_spans:
    cap_pos.setdefault(tag, tpos)

def in_cap_span(pos):
    return any(a <= pos <= b for _, _, a, b in cap_spans)

seen_first = {}
for m in re.finditer(r"(表\d+-\d+)|(图\d+-\d+)", txt):
    tag = m.group(0)
    if in_cap_span(m.start()):
        continue  # 图表自身标题不算引用
    if tag not in seen_first:
        seen_first[tag] = m.start()

bad_order = []
for tag, first_pos in seen_first.items():
    if tag in cap_pos and first_pos > cap_pos[tag] + 50:
        bad_order.append((tag, line_of(first_pos), line_of(cap_pos[tag])))
if bad_order:
    for tag, l1, l2 in sorted(bad_order):
        print(f"[!] {tag} 正文首引在 L{l1}，但图表出现在 L{l2}")
else:
    print(f"[OK] {len(cap_pos)} 个图表均在出现前（或紧邻处）被正文引用")

print()
print("=" * 60)
print("三、星号与'不显著'同段并存（人工复核清单）")
print("=" * 60)
para_re = re.compile(r"<p[^>]*>(.*?)</p>", re.S)
hits = []
seen = set()
for m in para_re.finditer(txt):
    p = strip_tags(m.group(1))
    if "***" in p and "不显著" in p:
        key = p[:30]
        if key in seen:
            continue
        seen.add(key)
        hits.append((line_of(m.start()), p))
if hits:
    print(f"共 {len(hits)} 段并存（多为牛熊/v3-v4 对照句，逐条确认无同一统计量自相矛盾后视为合法）:")
    for ln, _ in hits:
        print(f"    L{ln}")

print()
print("=" * 60)
print("四、千分位格式一致性（正文区，排除 style/formula/参考文献）")
print("=" * 60)
# 构造等长掩码：屏蔽 <style> 块、formula 区、参考文献区
masked = list(txt)
def mask_region(pattern, flags=re.S):
    for mm in re.finditer(pattern, txt, flags):
        masked[mm.start():mm.end()] = " " * (mm.end() - mm.start())

mask_region(r"<style>.*?</style>")
mask_region(r'<div class="formula">.*?</div>')
ref_m = re.search(r"<h1>参考文献", txt)
if ref_m:
    masked[ref_m.start():] = " " * (len(txt) - ref_m.start())
body = "".join(masked)

fmt_counter = Counter()
raw_big = []
for m in re.finditer(r"(?<![\d.,])\d{1,3}(?:,\d{3})+(?!\d)", body):
    fmt_counter["千分位"] += 1
for m in re.finditer(r"(?<![\d.,])([1-9]\d{3,5})(?![\d.%])", body):
    iv = int(m.group(1))
    if 1900 <= iv <= 2030:
        continue
    ctx = body[max(m.start() - 25, 0):m.end()].replace("\n", " ")
    fmt_counter["裸4-6位数"] += 1
    raw_big.append((line_of(m.start()), m.group(1), ctx[:55]))

for k, v in fmt_counter.items():
    print(f"  {k}: {v}")
big = [s for s in raw_big if int(s[1]) >= 1000]
if big:
    print(f"[!] ≥1000 的裸数字 {len(big)} 处，示例:")
    for ln, n, ctx in big[:8]:
        print(f"    L{ln}: {n}  | …{ctx}…")
elif "裸4-6位数" in fmt_counter:
    print(f"[OK] 裸数字均 <1000 或为年份，无需千分位")

print()
print("=" * 60)
print("五、疑似重复语句（≥40字段落级重复）")
print("=" * 60)
paras = []
for m in para_re.finditer(txt):
    p = strip_tags(m.group(1)).strip()
    if len(p) >= 40:
        paras.append((line_of(m.start()), p))
cnt = Counter(p for _, p in paras)
dups = [(p, c) for p, c in cnt.items() if c > 1]
if dups:
    for p, c in sorted(dups, key=lambda x: -x[1]):
        locs = [ln for ln, pp in paras if pp == p]
        print(f"[!] 重复 {c} 次 @L{locs}: {p[:70]}…")
else:
    print("[OK] 无 ≥40 字重复段落")

print()
print("=" * 60)
print("六、caption 唯一性 + 表格有效列宽（按 colspan 折算）")
print("=" * 60)
cap_nums = [t for t, _, _, _ in cap_spans]
dup_caps = [k for k, v in Counter(cap_nums).items() if v > 1]
print(f"caption 总数 {len(cap_nums)}，重复: {dup_caps if dup_caps else '无'}")

col_bad = 0
for tm in re.finditer(r"<table\b[^>]*>(.*?)</table>", txt, re.S):
    tb = tm.group(1)
    rows = re.findall(r"<tr\b[^>]*>(.*?)</tr>", tb, re.S)
    if not rows:
        continue
    eff = []
    pending = []  # [剩余覆盖行数(不含声明行), 宽度]，自下一行起生效
    for r in rows:
        prev = pending
        carried = sum(pw for rem, pw in prev if rem > 0)
        w = carried
        new = []
        for cell in re.finditer(r"<t([hd])\b([^>]*)>", r):
            attrs = cell.group(2)
            cmo = re.search(r'colspan="(\d+)"', attrs)
            rso = re.search(r'rowspan="(\d+)"', attrs)
            cw = int(cmo.group(1)) if cmo else 1
            w += cw
            if rso and int(rso.group(1)) > 1:
                new.append([int(rso.group(1)) - 1, cw])
        eff.append(w)
        pending = [[rem - 1, pw] for rem, pw in prev if rem - 1 > 0] + new
    if len(set(eff)) > 1:
        col_bad += 1
        print(f"[!] L{line_of(tm.start())}: 有效列宽异常 {eff}")
if col_bad == 0:
    print("[OK] 全部表格按 colspan/rowspan 折算后列宽一致")
