# -*- coding: utf-8 -*-
"""一次性批量替换：方法详解 HTML 生成脚本改为 L1-L5 五层表述。"""
from pathlib import Path

P = Path(r'd:\Desktop\基金经理行为分析研究\scripts\_detail_html_20260826.py')
s = P.read_text(encoding='utf-8')

# 1) INDS 字典 dim 字段改五层
repl = [
    ("'dim': '认知能力',", "'dim': 'L2 认知层',"),
    ("'dim': '配置选择能力',", "'dim': 'L3 选择层',"),
    ("'dim': '风险应对能力',", "'dim': 'L4 风险应对层·过程',"),
    ("'dim': '风险转化能力',", "'dim': 'L4 风险应对层·转化',"),
    ("'dim': '交易执行能力',", "'dim': 'L5 交易执行层',"),
    # 2) why 字段中的维度名标注
    ('【风险转化能力新增指标 1】', '【L4 转化效率职能·新增指标 1】'),
    ('【风险转化能力新增指标 2】', '【L4 转化效率职能·新增指标 2】'),
    ('【风险转化能力新增指标 3】', '【L4 转化效率职能·新增指标 3】'),
    # 3) 维度汇总表表头与数据行（COMP 字典键为维度名，保留键名改显示）
    ('<th>单维 t</th><th>单维 R²</th><th>联立 t</th>', '<th>单维 t</th><th>单维 R²</th><th>联立 t</th>'),
]
for a, b in repl:
    s = s.replace(a, b)

# 4) §1 汇总表的维度行显示名加 L 前缀（LAYER 映射在渲染处）
#    先在文件头（DIMS 定义后）插入 LAYER 映射
anchor = "DIMS = ['认知能力', '配置选择能力', '风险应对能力', '风险转化能力', '交易执行能力']"
layer_def = anchor + """

# L1-L5 五层分类学显示映射（与《指标总表_五层框架》一致）
LAYER = {
    '认知能力': 'L2 认知层',
    '配置选择能力': 'L3 选择层',
    '风险应对能力': 'L4 风险应对层·过程',
    '风险转化能力': 'L4 风险应对层·转化',
    '交易执行能力': 'L5 交易执行层',
}"""
assert anchor in s
s = s.replace(anchor, layer_def)

# 5) §1 汇总表：<b>{d}</b> → <b>{LAYER[d]}</b>
old = "H.append(f'<tr><td class=\"l\"><b>{d}</b></td><td class=\"l\">{comp_txt}</td>'"
new = "H.append(f'<tr><td class=\"l\"><b>{LAYER[d]}</b></td><td class=\"l\">{comp_txt}</td>'"
assert old in s
s = s.replace(old, new)

# 6) 6.1 群体画像表：<b>{d}</b> → <b>{LAYER[d]}</b>
old6 = "H.append(f'<tr><td class=\"l\"><b>{d}</b></td><td>{f4(GP[\"五维\"][\"Top5%\"][d])}</td>'"
new6 = "H.append(f'<tr><td class=\"l\"><b>{LAYER[d]}</b></td><td>{f4(GP[\"五维\"][\"Top5%\"][d])}</td>'"
assert old6 in s
s = s.replace(old6, new6)

# 7) 典型画像五维显示
old7 = "for d in DIMS:\\n        v = c['五维'].get(d)"
new7 = "for d in DIMS:\\n        v = c['五维'].get(d)"
# 典型画像处用 LAYER 显示
old7f = "fives.append(f'<span class=\"{cls}\">{d} {v:+.2f}（{pc:.0%}）</span>')"
new7f = "fives.append(f'<span class=\"{cls}\">{LAYER[d]} {v:+.2f}（{pc:.0%}）</span>')"
assert old7f in s
s = s.replace(old7f, new7f)

P.write_text(s, encoding='utf-8')
print('OK, all assertions passed')
