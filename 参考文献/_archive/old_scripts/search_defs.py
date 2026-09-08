# -*- coding: utf-8 -*-
import fitz, os, re, glob

REF = r"D:/Desktop/基金经理行为分析研究/参考文献"
PDFS = []
for root, _, files in os.walk(REF):
    if "截图" in root or "envs" in root:
        continue
    for f in files:
        if f.lower().endswith(".pdf"):
            PDFS.append(os.path.join(root, f))

# keyword groups -> variable
GROUPS = {
 "tenure": ["tenure", "从业", "任职年限"],
 "fund_age": ["fund age", "基金年龄", "age of the fund"],
 "education": ["education", "学历", "degree", "学士", "硕士"],
 "age": ["manager age", "经理年龄", "age of the manager"],
 "cert": ["CFA", "MBA", "certification", "资质"],
 "active_share": ["active share"],
 "ici": ["industry concentration", "ICI", "行业集中度"],
 "hhi": ["Herfindahl", "HHI"],
 "turnover": ["portfolio turnover", "换手", "turnover ratio"],
 "oci": ["overconfidence index", "overconfident", "过度自信", "self-attribution"],
 "style_drift": ["style drift", "风格漂移", "style persistence"],
 "return_gap": ["return gap"],
 "arg": ["隐形交易", "unobserved action", "修正隐形"],
 "return_vol": ["return volatility", "收益波动", "standard deviation of return", "波动率"],
}

def search(pdf, kws):
    try:
        doc = fitz.open(pdf)
    except Exception as e:
        return []
    res = []
    for pno in range(len(doc)):
        try:
            t = doc[pno].get_text().lower()
        except Exception:
            continue
        c = sum(t.count(k.lower()) for k in kws)
        if c > 0:
            res.append((pno, c))
    doc.close()
    return res

for var, kws in GROUPS.items():
    print("\n===== %s  (kws=%s) =====" % (var, kws))
    agg = []  # (pdf, pno, count)
    for pdf in PDFS:
        r = search(pdf, kws)
        for pno, c in r:
            agg.append((pdf, pno, c))
    agg.sort(key=lambda x: -x[2])
    for pdf, pno, c in agg[:5]:
        short = os.path.relpath(pdf, REF)
        print("  %3d  p%-3d  %s" % (c, pno + 1, short))
