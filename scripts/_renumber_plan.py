# -*- coding: utf-8 -*-
"""为全稿表/图分配"章节内连续编号"，输出待写入的编号方案（不改文件）。"""
import re, io

P = r"d:\Desktop\基金经理行为分析研究\merged_manuscript.html"
lines = io.open(P, encoding="utf-8").read().split("\n")

CH = {"第一章": 1, "第二章": 2, "第三章": 3, "第四章": 4, "第五章": 5, "第六章": 6}


def chap_of(h1):
    for k, v in CH.items():
        if h1.startswith(k):
            return v
    m = re.match(r"^(\d+)", h1)
    return int(m.group(1)) if m else 0


cur_h1 = cur_h2 = cur_h3 = ""
tcnt, icnt = {}, {}
items = []
for i, ln in enumerate(lines, 1):
    s = ln.strip()
    m = re.match(r"<h1>(.*?)</h1>", s)
    if m:
        cur_h1 = re.sub(r"<.*?>", "", m.group(1)); cur_h2 = cur_h3 = ""; continue
    m = re.match(r"<h2>(.*?)</h2>", s)
    if m:
        cur_h2 = re.sub(r"<.*?>", "", m.group(1)); cur_h3 = ""; continue
    m = re.match(r"<h3>(.*?)</h3>", s)
    if m:
        cur_h3 = re.sub(r"<.*?>", "", m.group(1)); continue

    is_tab = bool(re.search(r"<table[ >]", s))
    is_img = bool(re.search(r"<img ", s))
    if not (is_tab or is_img):
        continue

    c = chap_of(cur_h1)
    cap_old, hdr = "", ""
    if is_tab:
        tcnt[c] = tcnt.get(c, 0) + 1
        label = "表%d-%d" % (c, tcnt[c])
        for j in range(i, min(i + 3, len(lines))):
            mm = re.search(r"<caption>(.*?)</caption>", lines[j])
            if mm:
                cap_old = mm.group(1); break
        for j in range(i, min(i + 4, len(lines))):
            if "<th" in lines[j]:
                hdr = " | ".join(re.sub(r"<.*?>", "", x)
                                 for x in re.findall(r"<th[^>]*>.*?</th>", lines[j]))
                break
    else:
        icnt[c] = icnt.get(c, 0) + 1
        label = "图%d-%d" % (c, icnt[c])
        mm = re.search(r'alt="(.*?)"', s)
        hdr = mm.group(1) if mm else ""
    items.append((label, i, cur_h2 or cur_h1, cur_h3, cap_old, hdr[:100]))

out = io.open(r"d:\Desktop\基金经理行为分析研究\_renumber_plan.txt", "w", encoding="utf-8")
for label, i, h2, h3, cap_old, hdr in items:
    out.write("%-8s L%-5d | %-30s | %-36s | old=%s | %s\n"
              % (label, i, h2[:30], h3[:36], cap_old or "-", hdr))
out.close()
print("表:", tcnt, " 图:", icnt, " 合计:", len(items))
