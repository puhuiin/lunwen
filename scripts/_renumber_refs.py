import re
import shutil
import sys
import time

sys.stdout.reconfigure(encoding="utf-8")

APPLY = "--apply" in sys.argv

txt = open("merged_manuscript.html", encoding="utf-8").read()

# ---------- 定位参考文献区 ----------
ref_off = txt.index("<h1>参考文献")
body = txt[:ref_off]
rest = txt[ref_off:]

# ---------- 收集正文引文（两种形态） ----------
# 形态a: <sup>[n]</sup> 或 <sup>[n,m,...]</sup>
sup_pat = re.compile(r"<sup>\s*[\[（]?\s*([\d，,\s]+?)\s*[\]）]?\s*</sup>")
# 形态b: 紧贴词字符的裸 [n]（如 Oster[44]）
glued_pat = re.compile(r"(?<= [\w\u4e00-\u9fff]) \[(\d{1,3})\]", re.X)
# 形态c: 游离裸 [n]（前后均非词字符）
free_pat = re.compile(r"(?<![\w\u4e00-\u9fff])\[(\d{1,3})\](?![\w\u4e00-\u9fff(\[])")

sup_hits, glued_hits, free_hits = [], [], []
formula_spans = [ (m.start(), m.end()) for m in re.finditer(r'<div class="formula">.*?</div>', body, re.S) ]
def in_formula(pos):
    return any(a <= pos < b for a, b in formula_spans)
for m in sup_pat.finditer(body):
    if in_formula(m.start()):
        continue
    nums = [int(x) for x in re.split(r"[，,\s]+", m.group(1)) if x]
    sup_hits.append((m.start(), nums))
for m in glued_pat.finditer(body):
    glued_hits.append((m.start(), int(m.group(1))))
for m in free_pat.finditer(body):
    # 排除已被 sup 包裹者：检查该位置是否位于某个 <sup> 区间内
    pos = m.start()
    inside_sup = False
    for s2, _ in sup_hits:
        pass
    ls = body.rfind("<sup>", 0, pos)
    le = body.rfind("</sup>", 0, pos)
    if ls > le:
        inside_sup = True
    if not inside_sup:
        free_hits.append((pos, int(m.group(1))))

print(f"形态a <sup>包裹 引文实例: {len(sup_hits)}")
print(f"形态b 紧贴词字符裸[n]: {len(glued_hits)}")
for pos, n in glued_hits[:15]:
    print(f"   @{pos} [{n}]: …{re.sub(r'<[^>]+>', '', body[max(0,pos-40):pos+12])}…")
print(f"形态c 游离裸[n]（疑似误报或需人工判断）: {len(free_hits)}")
for pos, n in free_hits[:15]:
    print(f"   @{pos} [{n}]: …{body[max(0,pos-45):pos+12]}…")

if free_hits:
    print("\n!! 存在游离裸[n]，中止自动重编号，请先人工甄别")
    sys.exit(1)
if not APPLY:
    print("\n(dry-run 通过；加 --apply 执行重编号)")
    sys.exit(0)

# ---------- 构建首现顺序映射 ----------
order_seq = []
seen = set()
for pos, nums in sorted(sup_hits + [(p, [n]) for p, n in glued_hits]):
    for n in nums:
        if n not in seen:
            seen.add(n)
            order_seq.append(n)

entries_new = {old: new for new, old in enumerate(order_seq, 1)}
print(f"\n映射构建: {len(order_seq)} 个唯一编号")
assert len(order_seq) == len(set(order_seq)), "重复!"

# ---------- 应用替换 ----------
def map_nums_in_sup(m):
    inner = m.group(1)
    parts = re.split(r"([，,\s]+)", inner)
    out = []
    for p in parts:
        if re.fullmatch(r"\d+", p):
            out.append(str(entries_new[int(p)]))
        else:
            out.append(p)
    return "<sup>[" + "".join(out) + "]</sup>"

new_body = sup_pat.sub(map_nums_in_sup, body)
new_body = glued_pat.sub(lambda m: f"[{entries_new[int(m.group(1))]}]", new_body)

# ---------- 文献表：改标签并按新序排序 ----------
ref_lines = re.findall(r'<p class="ref">\s*\[(\d+)\][^\n]*', rest)
assert ref_lines, "未找到文献条目"
seg = re.search(r'(<h1>参考文献</h1>\n)(.*?)(\n</body>|$)', rest, re.S)
assert seg, "未定位文献块"
block = seg.group(2)
items = []
for line in block.splitlines():
    m = re.match(r'\s*(<p class="ref">\s*\[(\d+)\].*)$', line)
    if m:
        old = int(m.group(2))
        items.append((entries_new[old], re.sub(r"\[(\d+)\]", f"[{entries_new[old]}]", m.group(1), count=1)))
items.sort(key=lambda x: x[0])
new_block = "\n".join(it for _, it in items)
new_rest = rest[: seg.start(2)] + new_block + rest[seg.end(2) :]

out = new_body + new_rest
bak = f"merged_manuscript_bak_refnum_{time.strftime('%Y%m%d_%H%M%S')}.html"
shutil.copyfile("merged_manuscript.html", bak)
open("merged_manuscript.html", "w", encoding="utf-8").write(out)
changed = sum(1 for o, n in entries_new.items() if o != n)
print(f"已写回; 备份: {bak}; 编号变动的文献数: {changed}/51")
