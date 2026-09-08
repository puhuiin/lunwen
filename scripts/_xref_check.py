# -*- coding: utf-8 -*-
import io, re, collections

P = r"d:\Desktop\基金经理行为分析研究\merged_manuscript.html"
lines = io.open(P, encoding="utf-8").read().split("\n")

caps = {}
for i, s in enumerate(lines, 1):
    for m in re.finditer(r"<caption>\s*(表\d+-\d+)", s):
        caps.setdefault(m.group(1), []).append(i)

figs = {}
for i, s in enumerate(lines, 1):
    for m in re.finditer(r'class="footnote"[^>]*>\s*(图\d+-\d+)', s):
        figs.setdefault(m.group(1), []).append(i)

labels = set(caps) | set(figs)

cites = collections.defaultdict(list)
for i, s in enumerate(lines, 1):
    body = re.sub(r"<caption>.*?</caption>", "", s)
    body = re.sub(r'(<p class="footnote"[^>]*>)\s*(图\d+-\d+)', r"\1", body)
    for m in re.finditer(r"[表图]\d+-\d+", body):
        cites[m.group(0)].append(i)

print("=== caption/label 清单 ===")
for k in sorted(caps, key=lambda x: (int(x[1:].split("-")[0]), int(x.split("-")[1]))):
    if len(caps[k]) > 1:
        print("  [重复]", k, caps[k])
print("  表 caption 数 =", sum(len(v) for v in caps.values()), " 唯一编号 =", len(caps))
print("  图 label 数 =", sum(len(v) for v in figs.values()), " 唯一编号 =", len(figs), sorted(figs))

print()
print("=== 引用了但不存在的编号 ===")
bad = 0
for k in sorted(cites, key=lambda x: (x[0], int(x[1:].split("-")[0]), int(x.split("-")[1]))):
    if k not in labels:
        print("  [悬空]", k, "被引用于行", cites[k])
        bad += 1
if bad == 0:
    print("  无")

print()
print("=== 存在但正文从未引用的编号 ===")
never = [k for k in labels if k not in cites]
def key(x):
    return (x[0], int(x[1:].split("-")[0]), int(x.split("-")[1]))
for k in sorted(never, key=key):
    loc = caps.get(k) or figs.get(k)
    print("  [未引用]", k, "位于行", loc)
print("  合计未引用 =", len(never), "/", len(labels))

print()
print("=== 标签配平 ===")
txt = "\n".join(lines)
for tag in ("table", "tr", "div", "h1", "h2", "h3", "p", "caption", "thead", "tbody"):
    o = len(re.findall(r"<%s[ >]" % tag, txt))
    c = len(re.findall(r"</%s>" % tag, txt))
    flag = "" if o == c else "   <-- 不配平"
    print("  <%s> 开=%d 闭=%d%s" % (tag, o, c, flag))
