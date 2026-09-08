# -*- coding: utf-8 -*-
"""扫描论文正文（参考文献之前）中的英文残留与术语白名单外的词。"""
import zipfile
import re

P = r'D:\Desktop\基金经理行为分析研究\reports\论文初稿_2026-08-26.docx'

z = zipfile.ZipFile(P)
xml = z.read('word/document.xml').decode('utf-8')
paras = re.findall(r'<w:p[ >].*?</w:p>', xml, re.S)
texts = []
for p_ in paras:
    ts = re.findall(r'<w:t[^>]*>([^<]*)</w:t>', p_)
    t = ''.join(ts).strip()
    if t:
        texts.append(t)

ref_start = next(i for i, t in enumerate(texts) if t.startswith('参考文献'))
body = texts[:ref_start]

WHITELIST = set('''risk_asym de oc_conf ICI ISDI ARG timing mppm8_lag sortino8_lag
sharpe8_lag SDI lsv FF5 alpha MKT HC1 OLS PGR PLR LSV AF HM gamma RHO tenure
log_aum log_age TO AS AS_improved rc_mom rsstab RV Q1 Q2 Q3 Q4 Q5 R i j t k w p g ex
VIF ctrl ctrl_it Fischer Sharpe Sortino MPPM Henriksson Merton'''.split())
WL_LOWER = {x.lower() for x in WHITELIST}

found = 0
for i, t in enumerate(body):
    for w in re.findall(r'[A-Za-z_]{3,}', t):
        base = re.sub(r'[0-9_]+$', '', w)
        if w not in WHITELIST and base not in WHITELIST and w.lower() not in WL_LOWER:
            found += 1
            print(i, '|', w, '|', t[:100])

print('---- body paras:', len(body), '| suspicious words:', found)
