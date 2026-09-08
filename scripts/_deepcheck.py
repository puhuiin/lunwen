# -*- coding: utf-8 -*-
"""第六维深度审计：
一、关键统计量口径一致性（限定词缺失即失败）
二、陈旧数字/排序残留审计清单
三、核心 ΔR² 数值出现分布
四、全角半角标点规范
五、锚点 href 与 id 对账 + id 唯一性
"""
import re
import os
from collections import Counter

BASE = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(BASE, "merged_manuscript.html")

with open(PATH, encoding="utf-8") as f:
    txt = f.read()

def line_of(pos):
    return txt.count("\n", 0, pos) + 1

def strip_tags(s):
    return re.sub(r"<[^>]+>", "", s)

# 段落级纯文本 + 行号
paras = []
for m in re.finditer(r"<p[^>]*>(.*?)</p>", txt, re.S):
    paras.append((line_of(m.start()), strip_tags(m.group(1))))
# 表格单元格文本也纳入（表格中也会引用这些数值）
for m in re.finditer(r"<td\b[^>]*>(.*?)</td>", txt, re.S):
    paras.append((line_of(m.start()), strip_tags(m.group(1))))

def sentences(line, p):
    return [(line, s) for s in re.split(r"(?<=[。；！？])", p) if s.strip()]

print("=" * 60)
print("一、关键统计量限定词检查")
print("=" * 60)
fails = 0
RULES = [
    (r"1\.48%", r"样本内|同一样本|仅作参考", "1.48%(样本内分位差)需带'样本内'类限定"),
    (r"1\.28%", r"样本外|严格协议", "1.28%(样本外分位差)需带'样本外'类限定"),
    (r"46\.5%", r"基金层|基金层面|按基金|399", "46.5% 需带'基金层'限定"),
    (r"N\s*[=＝]\s*2,\s?264|2,\s?264只|2,264（", r"", None),  # 占位不查
]
for pat, need, desc in RULES:
    if desc is None:
        continue
    for ln, p in paras:
        for m in re.finditer(pat, p):
            seg = m.string[max(m.start() - 60, 0):m.end() + 60]
            if not re.search(need, seg):
                fails += 1
                print(f"[!] L{ln}: {desc}")
                print(f"      …{seg.strip()[:100]}…")
if fails == 0:
    print("[OK] 所有关键统计量均带正确限定词")

print()
print("=" * 60)
print("二、陈旧数字/排序残留审计")
print("=" * 60)
stale = 0
# 2a. 旧的 L5 显著指标计数（权威为 43/34/52，总数口径见 §4.16）
for ln, p in paras:
    for m in re.finditer(r"(?:仅|只有)?\s*(24|36)\s*只", p):
        ctx = p[max(m.start() - 50, 0):m.end() + 40]
        if "牛" in ctx or "熊" in ctx or "子样本" in ctx:
            continue  # 牛熊子期计数可能合法
        stale += 1
        print(f"[?] L{ln}: 疑似旧计数 '{m.group(0)}': …{ctx[:90]}…")
# 2b. L5 与 '第二' 并存句（统一口径下应为第三；牛市/子样本可能合法）
n2b = 0
for ln, p in paras:
    if "L5" in p and "第二" in p:
        n2b += 1
        print(f"[?] L{ln}: L5+第二 并存: …{p[:110]}…")
# 2c. 'L2最大/L2居首' 类表述应伴随 0.0463 或 表4-12
for ln, p in paras:
    if re.search(r"L2[^。]{0,12}(?:最大|居首|最高)", p):
        ok = ("0.0463" in p) or ("表4-12" in p) or ("统一" in p)
        if not ok:
            stale += 1
            print(f"[?] L{ln}: L2 最大类表述缺统一口径标注: …{p[:100]}…")
if stale == 0 and n2b == 0:
    print("[OK] 无陈旧数字或排序残留")

print()
print("=" * 60)
print("三、核心 ΔR² 数值出现分布（0.0463/0.0301/0.0224/0.0199）")
print("=" * 60)
core = ["0.0463", "0.0301", "0.0224", "0.0199"]
alltxt_lines = [(ln, p) for ln, p in paras]
for v in core:
    locs = [ln for ln, p in alltxt_lines if v in p]
    print(f"  {v}: {len(locs)} 处 @行 {sorted(set(locs))[:10]}")

print()
print("=" * 60)
print("四、全角半角标点规范（CJK 语境）")
print("=" * 60)
cjk = r"[\u4e00-\u9fff]"
cats = Counter()
samples = {}
def scan(pat, name, limit=4):
    for ln, p in paras:
        for m in re.finditer(pat, p):
            cats[name] += 1
            if len(samples.get(name, [])) < limit:
                samples.setdefault(name, []).append((ln, m.group(0)[:40]))

scan(cjk + r"," + cjk, "CJK间半角逗号")
scan(cjk + r";" + cjk, "CJK间半角分号")
scan(cjk + r":" + cjk, "CJK间半角冒号")
scan(cjk + r"\(" + cjk, "CJK(中文)用半角括号")
scan(r"[a-zA-Z0-9%）]" + r"（" + cjk + r"[^）]{0,20}）", "英文后接全角括号包中文")
scan(cjk + r"\." + cjk, "CJK间半角句点")

if cats:
    for k, v in cats.most_common():
        print(f"  [?] {k}: {v} 处，示例:")
        for ln, s in samples.get(k, []):
            print(f"      L{ln}: …{s}…")
else:
    print("[OK] CJK 语境无半角标点混用")

print()
print("=" * 60)
print("五、锚点与 id 对账")
print("=" * 60)
ids = re.findall(r'id="([^"]+)"', txt)
dup_ids = [k for k, v in Counter(ids).items() if v > 1]
hrefs = re.findall(r'href="#([^"]+)"', txt)
idset = set(ids)
dangling = [h for h in hrefs if h not in idset]
print(f"id 总数 {len(ids)}（唯一 {len(idset)}），重复: {dup_ids if dup_ids else '无'}")
print(f"内部锚点链接 {len(hrefs)} 条，悬空: {dangling if dangling else '无'}")
