# -*- coding: utf-8 -*-
"""把 _frag_empirical_20260902.py 的内容拼入 _draft_docx_20260826.py，
插入位置：'# ---- 4 投资经理画像' 注释行之前；同时把 _nary 改为支持 sup=None。"""

MAIN = r'D:\Desktop\基金经理行为分析研究\scripts\_draft_docx_20260826.py'
FRAG = r'D:\Desktop\基金经理行为分析研究\scripts\_frag_empirical_20260902.py'

src = open(MAIN, encoding='utf-8').read()
frag = open(FRAG, encoding='utf-8').read()

# 0) _nary 支持 sup=None
old_nary = '''def _nary(chr_, sub, sup, body):
    """求和/积分等 n 元运算符。"""
    return (f'<m:nary><m:naryPr><m:chr m:val="{chr_}"/>'
            f'<m:limLoc m:val="undOvr"/><m:supHide m:val="0"/>'
            f'<m:subHide m:val="0"/></m:naryPr>'
            f'<m:sub>{sub}</m:sub><m:sup>{sup}</m:sup><m:e>{body}</m:e></m:nary>')'''
new_nary = '''def _nary(chr_, sub, sup, body):
    """求和/积分等 n 元运算符；sup=None 时隐藏上标。"""
    _sh = '1' if sup is None else '0'
    _sup = '' if sup is None else f'<m:sup>{sup}</m:sup>'
    return (f'<m:nary><m:naryPr><m:chr m:val="{chr_}"/>'
            f'<m:limLoc m:val="undOvr"/><m:supHide m:val="{_sh}"/>'
            f'<m:subHide m:val="0"/></m:naryPr>'
            f'<m:sub>{sub}</m:sub>{_sup}<m:e>{body}</m:e></m:nary>')'''
assert old_nary in src, 'nary def not found'
src = src.replace(old_nary, new_nary)

# 1) 拼接位置
marker = "heading(doc, '三、投资经理画像', 1)"
assert marker in src, 'marker not found'
src = src.replace(marker, frag + '\n' + marker)

open(MAIN, 'w', encoding='utf-8').write(src)
print('spliced OK')
