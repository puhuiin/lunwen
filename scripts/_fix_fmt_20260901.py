# -*- coding: utf-8 -*-
"""修两处排版瑕疵（2026-09-01）

1. 表 4 注里误用 <b> 标签：note() 不做 HTML 解析，会原样输出字面 <b> 文字。
2. 结论首段「t=+5.38数值相同」缺分隔符。
"""
import io
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = os.path.join(ROOT, 'scripts', '_draft_docx_20260826.py')

src = io.open(P, encoding='utf-8').read()
NL = chr(10)
pairs = [
    ("'规格I 为基金层横截面、规格II 为季度面板，两者均为<b>同期</b>口径，'",
     "'规格I 为基金层横截面、规格II 为季度面板，两者均为同期口径，'"),
    ('          f"{spec_t(\'sortino8_lag\', \'spec2_panel\')[\'t\']:+.2f}"' + NL
     + "          '数值相同纯属巧合，前者为跨期的复合维度、后者为同期的单一成分，'",
     '          f"{spec_t(\'sortino8_lag\', \'spec2_panel\')[\'t\']:+.2f} "' + NL
     + "          '数值相同纯属巧合，前者为跨期的复合维度、后者为同期的单一成分，'"),
]
hit = 0
for old, new in pairs:
    if old in src:
        src = src.replace(old, new, 1)
        hit += 1
    else:
        print('!! 未命中：%s' % old[:70].replace(NL, '\\n'))
bak = P + '.bak_fmt_20260901'
if not os.path.exists(bak):
    io.open(bak, 'w', encoding='utf-8').write(io.open(P, encoding='utf-8').read())
io.open(P, 'w', encoding='utf-8').write(src)
print('替换 %d/%d' % (hit, len(pairs)))
sys.exit(0 if hit == len(pairs) else 1)
