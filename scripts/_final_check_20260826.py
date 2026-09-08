# -*- coding: utf-8 -*-
"""终检：自评页标签配平 + docx 与 HTML 的关键数字一致性抽查。"""
import re
import zipfile

REP = r'D:\Desktop\基金经理行为分析研究\reports'

# ---- 1) 自评页标签配平 ----
f = REP + r'\修改说明与自评_2026-08-25.html'
s = open(f, encoding='utf-8').read()
ok = True
for tag in ['div', 'table', 'tr', 'td', 'th', 'p', 'span', 'ul', 'ol', 'li',
            'h1', 'h2', 'h3', 'dl', 'section', 'footer', 'header']:
    o = len(re.findall(r'<' + tag + r'[ >]', s))
    c = len(re.findall(r'</' + tag + r'>', s))
    if o != c:
        print('TAG MISMATCH:', tag, o, c)
        ok = False
print('自评页标签配平:', 'OK' if ok else 'FAIL')

# 关键状态抽查
checks = [
    ('第5项自评转达成', '5 · 全文不要太冗长' in s and 'stamp ok">达成' in s.split('5 · 全文不要太冗长')[1][:200]),
    ('正文成文待办转已完成', '大纲正文成文</b>——' in s and 'p-done">已完成</span><b>大纲正文成文' in s),
    ('第三轮清单存在', '第三轮：大纲正文成文' in s),
    ('总评五条达成', '五条意见全部达成' in s),
]
for name, v in checks:
    print(('PASS' if v else 'FAIL'), name)

# ---- 2) docx 关键数字抽查（与已知定稿值对照）----
p = REP + r'\论文初稿_2026-08-26.docx'
z = zipfile.ZipFile(p)
xml = z.read('word/document.xml').decode('utf-8')
flat = ''.join(re.findall(r'<w:t[^>]*>([^<]*)</w:t>', xml))

num_checks = [
    ('样本 400 只', '400' in flat),
    ('观测 9,974', '9,974' in flat),
    ('回归基金 362', '362' in flat),
    ('AS 横截面全模型 t=-3.06', '-3.06' in flat),
    ('AS 面板单变量 t=+5.33', '+5.33' in flat),
    ('Q5-Q1 差 3.35', '3.35' in flat),
    ('单调 t=11.87', '11.87' in flat),
    ('Top5% alpha 6.65%', '6.65%' in flat),
    ('manager 残留已清除', 'manager 的时间序列' not in flat),
    ('投资经理的时间序列已入文', '投资经理的时间序列行为' in flat),
    ('结论局限：幸存者偏差', '幸存者偏差' in flat),
    ('参考文献含李志冰2017', '李志冰' in flat),
]
for name, v in num_checks:
    print(('PASS' if v else 'FAIL'), name)

# docx 结构
print('docx 段落(有字):', len([x for x in re.findall(r'<w:p[ >].*?</w:p>', xml, re.S) if re.findall(r'<w:t[^>]*>([^<]*)</w:t>', x)]),
      '| 表格:', xml.count('<w:tbl>'))
