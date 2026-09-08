import re
import sys

sys.stdout.reconfigure(encoding="utf-8")

txt = open("merged_manuscript.html", encoding="utf-8").read()
lines = txt.splitlines()

# ---------- 1. 定位参考文献区 ----------
ref_start = None
for i, s in enumerate(lines, 1):
    if re.search(r"<h[12]>[^<]*参考文献", s):
        ref_start = i
        break
print(f"参考文献区起始行: {ref_start}")

# ---------- 2. 文献表条目 ----------
# 假设文献表为 <li>[n] ...</li> 或表格形式，两种都试
entries = {}
if ref_start:
    ref_txt = "\n".join(lines[ref_start - 1 :])
    # 形式A: <li>[n] / 形式B: <td>[n] / 形式C: <p class="ref">[n]
    for m in re.finditer(r"<li[^>]*>\s*\[(\d+)\]", ref_txt):
        entries[int(m.group(1))] = "li"
    if not entries:
        for m in re.finditer(r'<p class="ref">\s*\[(\d+)\]', ref_txt):
            entries[int(m.group(1))] = "p.ref"
    if not entries:
        for m in re.finditer(r"<td>\s*\[(\d+)\]", ref_txt):
            entries[int(m.group(1))] = "td"
print(f"文献表条目数: {len(entries)}; 编号范围: {min(entries)}–{max(entries) if entries else '-'}")
missing_in_table = [n for n in range(1, max(entries) + 1) if n not in entries] if entries else []
if missing_in_table:
    print(f"!! 编号空洞（表中缺失）: {missing_in_table}")
else:
    print("编号连续: 无空洞")

# ---------- 3. 正文引文号（排除参考文献区自身） ----------
body_txt = "\n".join(lines[: ref_start - 1]) if ref_start else txt
cites = {}
for i, s in enumerate(lines[: (ref_start - 1) if ref_start else len(lines)], 1):
    # 排除公式/代码块中的方括号误报：只取 <sup>[n]</sup> 或 [数字] 紧跟中文/英文语境
    for m in re.finditer(r"<sup>\s*[\[（]?\s*(\d+)\s*[\]）]?\s*</sup>", s):
        n = int(m.group(1))
        cites.setdefault(n, []).append(i)
    # 也匹配裸 [n] 形式（部分正文可能不用 sup）
    for m in re.finditer(r"(?<![\w\d])\[(\d{1,3})\](?![\w\d(\[])", s):
        n = int(m.group(1))
        cites.setdefault(n, []).append(i)

all_cited = sorted(cites)
print(f"\n正文引用的编号数: {len(all_cited)}")

# 双向对账
uncited = [n for n in entries if n not in cites]
dangling = [n for n in cites if n not in entries]
print(f"表中存在但正文未引用: {uncited if uncited else '无'}")
print(f"正文引用但表中不存在: {dangling if dangling else '无'}")
for n in dangling:
    print(f"  [{n}] 首现 L{cites[n][0]}: …{re.sub(r'<[^>]+>', '', lines[cites[n][0]-1])[:80]}…")

# ---------- 4. 首现顺序检查（GB/T 7714 顺序编码制要求按首现顺序编号） ----------
first_occurrence = []
seen = set()
for i, s in enumerate(lines[: (ref_start - 1) if ref_start else len(lines)], 1):
    for m in re.finditer(r"<sup>\s*[\[（]?\s*(\d+)\s*[\]）]?\s*</sup>", s):
        n = int(m.group(1))
        if n not in seen and n in entries:
            seen.add(n)
            first_occurrence.append((n, i))

out_of_order = []
max_so_far = 0
for n, i in first_occurrence:
    if n < max_so_far:
        out_of_order.append((n, i, max_so_far))
    max_so_far = max(max_so_far, n)
print(f"\n首现顺序检查: 共 {len(first_occurrence)} 个被引文献")
if out_of_order:
    print(f"!! 非首现顺序编号 {len(out_of_order)} 处（前10处）:")
    for n, i, prev_max in out_of_order[:10]:
        print(f"   [{n}] 首现 L{i}（此前已出现 [{prev_max}]）")
else:
    print("严格按首现顺序编号 ✓")
