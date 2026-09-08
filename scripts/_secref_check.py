import re
import sys

sys.stdout.reconfigure(encoding="utf-8")

PATH = "merged_manuscript.html"
txt = open(PATH, encoding="utf-8").read()
lines = txt.splitlines()

# ---------- 1. 收集标题编号 ----------
heads = {}
order = []
hpat = re.compile(r"<h([123])>(.*?)</h\1>")
for i, s in enumerate(lines, 1):
    m = hpat.search(s)
    if not m:
        continue
    title = re.sub(r"<[^>]+>", "", m.group(2)).strip()
    nm = re.match(r"\s*(\d+(?:\.\d+){0,2})", title)
    if nm:
        num = nm.group(1)
        heads[num] = (i, title[:46])
        order.append((num, i))

# 编号重复检测
seen = {}
for num, i in order:
    seen.setdefault(num, []).append(i)
dups = {k: v for k, v in seen.items() if len(v) > 1}

# 父级缺失检测
orphans = []
for num in heads:
    parts = num.split(".")
    for k in range(1, len(parts)):
        parent = ".".join(parts[:k])
        if parent not in heads:
            orphans.append((num, parent))

# ---------- 2. 收集正文 § 引用 ----------
rpat = re.compile(r"§(\d+(?:\.\d+){0,2})")
cites = {}
for i, s in enumerate(lines, 1):
    for m in rpat.finditer(s):
        num = m.group(1)
        start = max(0, m.start() - 55)
        ctx = s[start : min(len(s), m.end() + 30)]
        ctx = re.sub(r"<[^>]+>", "", ctx)
        cites.setdefault(num, []).append((i, ctx.strip()))

# ---------- 3. 输出 ----------
print("=== 标题编号清单 ===")
print(f"共 {len(heads)} 个编号小节")
if dups:
    print("!! 编号重复:")
    for k, v in dups.items():
        print(f"   {k} -> 行 {v}")
else:
    print("编号重复: 无")
if orphans:
    print("!! 父级缺失:", orphans)
else:
    print("父级完整")

print()
print("=== 悬空 § 引用（指向不存在的小节）===")
dangling = False
for num in sorted(cites):
    if num not in heads:
        dangling = True
        locs = ", ".join(f"L{i}" for i, _ in cites[num])
        print(f"  §{num}  被引于 {locs}")
        for i, ctx in cites[num][:3]:
            print(f"      L{i}: …{ctx}…")
if not dangling:
    print("无")

print()
print("=== 各目标被引上下文（供语义人工复核；每目标最多3条）===")
for num in sorted(cites, key=lambda x: [int(p) for p in x.split(".")]):
    tgt = heads.get(num)
    tgt_str = f"(L{tgt[0]} {tgt[1]})" if tgt else "(不存在!)"
    lst = cites[num]
    print(f"\n§{num} <- {len(lst)}次  目标{tgt_str}")
    for i, ctx in lst[:3]:
        print(f"   L{i}: …{ctx}…")
    if len(lst) > 3:
        print(f"   …另有 {len(lst)-3} 条")
