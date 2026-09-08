# -*- coding: utf-8 -*-
import io, re, sys, shutil, datetime

P = r"d:\Desktop\基金经理行为分析研究\merged_manuscript.html"
APPLY = "--apply" in sys.argv

lines = io.open(P, encoding="utf-8").read().split("\n")

UNCITED = [86,222,359,488,518,658,710,763,782,803,814,840,850,865,876,889,917,938,965,
           985,1006,1016,1029,1040,1053,1068,1081,1105,1122,1136,1158,1171,1187,
           1255,1279,1295,1320,1335,1346,1362,1373,1388,1413,1420,1430,1483,1513,1550]


def get_caption(idx):
    for k in (idx, idx + 1):
        if k < len(lines):
            m = re.search(r"<caption>(.*?)</caption>", lines[k])
            if m:
                return re.sub(r"<[^>]+>", "", m.group(1)).strip()
    return None


def split_cap(capt):
    m = re.match(r"(表\d+-\d+)\s*\u3000?\s*(.*)$", capt)
    label, title = m.group(1), m.group(2)
    core = title.split("：")[0]
    core = re.sub(r"（[^）]*）\s*$", "", core).strip()
    return label, core


ops = []
for ln in UNCITED:
    idx = ln - 1
    capt = get_caption(idx)
    label, core = split_cap(capt)

    anchor = idx
    j = idx - 1
    while j >= 0 and lines[j].strip() == "":
        j -= 1
    if j >= 0 and lines[j].strip().startswith('<div class="table-wrap"'):
        anchor = j
        j -= 1
        while j >= 0 and lines[j].strip() == "":
            j -= 1

    prev = lines[j] if j >= 0 else ""
    is_para = prev.lstrip().startswith("<p") and prev.rstrip().endswith("</p>") \
        and 'class="footnote"' not in prev

    if is_para:
        body = prev.rstrip()
        inner = body[:-4]
        if inner.rstrip().endswith("："):
            new = inner.rstrip()[:-1] + "（%s）：</p>" % label
        elif inner.rstrip().endswith("。"):
            new = inner.rstrip() + "%s见%s。</p>" % (core, label)
        else:
            new = inner.rstrip() + "（%s）</p>" % label
        ops.append(("P", j, new, label, core))
    else:
        ops.append(("H", anchor, "<p>%s报告了%s。</p>" % (label, core), label, core))

print("=== 补引预览（P=改写导语 / H=新增导语句）===")
for kind, at, txt, label, core in ops:
    show = re.sub(r"<[^>]+>", "", txt)
    if kind == "P":
        show = "…" + show[-72:]
    print("%s %-5d %-8s | %s" % (kind, at + 1, label, show))
print("\nP改写 =", sum(1 for o in ops if o[0] == "P"), " H新增 =", sum(1 for o in ops if o[0] == "H"))

if not APPLY:
    print("\n[dry-run] 未写入。加 --apply 生效。")
    raise SystemExit

shutil.copyfile(P, P.replace(".html", "_bak_xref_%s.html" % datetime.datetime.now().strftime("%Y%m%d_%H%M%S")))
for kind, at, txt, label, core in sorted(ops, key=lambda o: -o[1]):
    if kind == "P":
        lines[at] = txt
    else:
        lines.insert(at, txt)
io.open(P, "w", encoding="utf-8", newline="\n").write("\n".join(lines))
print("\n已写入。总行数 =", len(lines))
