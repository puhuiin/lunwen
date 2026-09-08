# -*- coding: utf-8 -*-
import io, re

P = r"d:\Desktop\基金经理行为分析研究\merged_manuscript.html"
lines = io.open(P, encoding="utf-8").read().split("\n")

UNCITED = [86,222,359,488,518,658,710,763,782,803,814,840,850,865,876,889,917,938,965,
           985,1006,1016,1029,1040,1053,1068,1081,1105,1122,1136,1158,1171,1187,
           1255,1279,1295,1320,1335,1346,1362,1373,1388,1413,1420,1430,1483,1513,1550]

def strip(s):
    return re.sub(r"<[^>]+>", "", s).strip()

for ln in UNCITED:
    idx = ln - 1
    cap = re.search(r"<caption>(.*?)</caption>", lines[idx])
    if cap is None and idx + 1 < len(lines):
        cap = re.search(r"<caption>(.*?)</caption>", lines[idx + 1])
    capt = strip(cap.group(1)) if cap else "?"
    prev = ""
    prev_ln = None
    j = idx - 1
    while j >= 0 and j > idx - 8:
        t = strip(lines[j])
        if t and not lines[j].lstrip().startswith("<div"):
            prev = t
            prev_ln = j + 1
            break
        j -= 1
    tail = prev[-58:] if len(prev) > 58 else prev
    kind = "H" if re.match(r"\s*<h[123]", lines[prev_ln - 1] or "") else "P"
    print("%-5d| %-42s | %s%-5s | ...%s" % (ln, capt[:42], kind, prev_ln, tail))
