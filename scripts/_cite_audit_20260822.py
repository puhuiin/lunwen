# -*- coding: utf-8 -*-
"""参考文献引用闭环审计：正文 <sup>[N]</sup> 引用 vs 文献表 [N] 双向对账。"""
import re, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

PATH = "merged_manuscript.html"
txt = open(PATH, encoding="utf-8").read()
lines = txt.splitlines()

# 1) 文献表条目：形如 <p class="ref">[N] ...
listed = {}
for i, s in enumerate(lines, 1):
    m = re.match(r'<p class="ref">\[(\d+)\]', s.strip())
    if m:
        n = int(m.group(1))
        listed.setdefault(n, []).append(i)

# 2) 正文引用：<sup>[N]</sup> 或 [N]（排除文献表行本身与 caption）
cited = {}
for i, s in enumerate(lines, 1):
    if re.match(r'\s*<p class="ref">', s):
        continue
    for m in re.finditer(r"\[(\d{1,3})\]", s):
        n = int(m.group(1))
        if 1 <= n <= 200:
            cited.setdefault(n, []).append(i)

nums_listed = sorted(listed)
print(f"=== 文献表 ===")
print(f"  条目数 = {len(nums_listed)}  编号范围 = {nums_listed[0]}–{nums_listed[-1]}")
dup = {n: v for n, v in listed.items() if len(v) > 1}
print(f"  表内重复编号: {dup if dup else '无'}")
missing_in_seq = [n for n in range(nums_listed[0], nums_listed[-1]+1) if n not in listed]
print(f"  序列缺口: {missing_in_seq if missing_in_seq else '无'}")

print(f"=== 正文引用 ===")
print(f"  被引编号数 = {len(cited)}")

never_cited = [n for n in nums_listed if n not in cited]
print(f"=== 在表但从未被正文引用 ===")
print(f"  {never_cited if never_cited else '无'}  (合计 {len(never_cited)})")

dangling = sorted(n for n in cited if n not in listed)
print(f"=== 被引用但不在文献表 ===")
print(f"  {dangling if dangling else '无'}")

out_of_range = sorted(n for n in cited if n > max(nums_listed))
print(f"=== 引用超出文献表最大编号({max(nums_listed)}) ===")
print(f"  {out_of_range if out_of_range else '无'}")

# 3) 引用顺序首现检查（GB/T 7714 顺序编码制：应按首次出现顺序编号）
first_occurrence = {}
for n, locs in sorted(cited.items()):
    first_occurrence[n] = min(locs)
order_by_line = sorted(first_occurrence.items(), key=lambda kv: kv[1])
seq = [n for n, _ in order_by_line]
violations = []
seen = []
for idx, n in enumerate(seq):
    expected = idx + 1
    if n != expected:
        violations.append((idx+1, n, first_occurrence[n]))
if violations:
    print("=== 首现顺序 vs 编号（顺序编码制偏差）===")
    for exp, got, ln in violations[:20]:
        print(f"  第{exp}个被引文献应为[{exp}]，实际[{got}]，首现于 L{ln}")
else:
    print("=== 首现顺序检查 ===")
    print("  全部按首次出现顺序编号，符合 GB/T 7714 顺序编码制")

# 4) 单处多引连排格式抽查：如 [12-14] 展开是否都在表中
range_refs = []
for i, s in enumerate(lines, 1):
    if re.match(r'\s*<p class="ref">', s):
        continue
    for m in re.finditer(r"\[(\d{1,3})-(\d{1,3})\]", s):
        a, b = int(m.group(1)), int(m.group(2))
        range_refs.append((i, a, b))
bad_ranges = [(i,a,b) for i,a,b in range_refs if any(x not in listed for x in range(a,b+1))]
print(f"=== 连排区间引用 [a-b] ===")
print(f"  共 {len(range_refs)} 处；展开后缺表: {bad_ranges if bad_ranges else '无'}")
