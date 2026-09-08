# -*- coding: utf-8 -*-
import fitz, os, sys

REF = r"D:/Desktop/基金经理行为分析研究/参考文献"
KWS = ["return volatility", "standard deviation of return", "standard deviation of the return",
       "收益率波动率", "收益波动率", "收益率的标准差", "total risk", "return standard deviation"]

def search(pdf):
    try:
        if os.path.getsize(pdf) > 30_000_000:
            return []
        doc = fitz.open(pdf)
    except Exception:
        return []
    res = []
    n = min(len(doc), 50)
    for pno in range(n):
        try:
            t = doc[pno].get_text().lower()
        except Exception:
            continue
        if not t.strip():
            continue
        c = sum(t.count(k.lower()) for k in KWS)
        if c > 0:
            res.append((pno, c))
    doc.close()
    return res

agg = []
for root, _, files in os.walk(REF):
    if "envs" in root or "截图" in root:
        continue
    for f in files:
        if not f.lower().endswith(".pdf"):
            continue
        full = os.path.join(root, f)
        try:
            r = search(full)
        except Exception:
            continue
        for pno, c in r:
            agg.append((full, pno, c))
agg.sort(key=lambda x: -x[2])
for full, pno, c in agg[:15]:
    print("%3d  p%-3d  %s" % (c, pno + 1, os.path.relpath(full, REF)))
