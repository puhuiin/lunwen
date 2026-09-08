# -*- coding: utf-8 -*-
import re, io, sys

P = r"d:\Desktop\基金经理行为分析研究\merged_manuscript.html"
lines = io.open(P, encoding="utf-8").read().split("\n")

cur_h1 = cur_h2 = cur_h3 = ""
items = []
for i, ln in enumerate(lines, 1):
    s = ln.strip()
    m = re.match(r"<h1>(.*?)</h1>", s)
    if m:
        cur_h1, cur_h2, cur_h3 = re.sub(r"<.*?>", "", m.group(1)), "", ""
        continue
    m = re.match(r"<h2>(.*?)</h2>", s)
    if m:
        cur_h2, cur_h3 = re.sub(r"<.*?>", "", m.group(1)), ""
        continue
    m = re.match(r"<h3>(.*?)</h3>", s)
    if m:
        cur_h3 = re.sub(r"<.*?>", "", m.group(1))
        continue
    if re.match(r"<table[ >]", s):
        cap = ""
        for j in range(i, min(i + 3, len(lines))):
            mm = re.search(r"<caption>(.*?)</caption>", lines[j])
            if mm:
                cap = mm.group(1)
                break
        hdr = ""
        for j in range(i, min(i + 4, len(lines))):
            if "<th" in lines[j]:
                hdr = " | ".join(re.sub(r"<.*?>", "", x) for x in re.findall(r"<th[^>]*>.*?</th>", lines[j]))
                break
        items.append((i, cur_h1, cur_h2, cur_h3, cap, hdr[:110]))
    if re.match(r"<img ", s):
        alt = re.search(r'alt="(.*?)"', s)
        items.append((i, cur_h1, cur_h2, cur_h3, "[IMG]", alt.group(1) if alt else ""))

out = io.open(r"d:\Desktop\基金经理行为分析研究\_table_index.txt", "w", encoding="utf-8")
for n, (i, h1, h2, h3, cap, hdr) in enumerate(items, 1):
    out.write("%02d L%-5d | %s | %s | %s | cap=%s | %s\n" % (n, i, h1[:8], h2[:28], h3[:34], cap, hdr))
out.close()
print("total", len(items))
