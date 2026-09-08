# -*- coding: utf-8 -*-
"""批量提取PDF文本，为研读卡片做准备"""
import fitz, os, re
from pathlib import Path

BASE = Path(r'D:\Desktop\基金经理行为分析研究\参考文献')
OUT = BASE / '文献' / '研读卡片_AI' / '_extracted_text'
OUT.mkdir(parents=True, exist_ok=True)

# 我负责的文献：L2全+L3全+L5英文+因变量全
cats_to_extract = {
    'L2_持仓偏离层': None,  # None=全部
    'L3_交易行为层': None,
    'L5_认知行为层': 'en',  # 仅英文
    '因变量测度': None,
}

results = []
for cat, mode in cats_to_extract.items():
    p = BASE / cat
    if not p.is_dir(): continue
    pdfs = sorted([f for f in os.listdir(p) if f.endswith('.pdf')])
    if mode == 'en':
        pdfs = [f for f in pdfs if not re.search(r'[\u4e00-\u9fff]', f)]
    for f in pdfs:
        src = p / f
        try:
            doc = fitz.open(str(src))
            full_text = ''
            for page in doc:
                full_text += page.get_text()
            doc.close()
            # 保存文本
            stem = Path(f).stem
            txt_path = OUT / f'{cat}_{stem}.txt'
            with open(txt_path, 'w', encoding='utf-8') as fp:
                fp.write(full_text)
            has_text = len(full_text.strip()) > 100
            results.append((cat, f, len(full_text), has_text, str(txt_path)))
        except Exception as e:
            results.append((cat, f, 0, False, f'ERR:{e}'))

# 统计
print(f'提取完成: {len(results)}篇')
text_ok = [r for r in results if r[3]]
scan = [r for r in results if not r[3]]
print(f'有文本: {len(text_ok)}篇')
print(f'扫描件/无文本: {len(scan)}篇')
if scan:
    print('扫描件清单:')
    for cat, f, _, _, _ in scan:
        print(f'  {cat}/{f}')
print()
print(f'文本已保存到: {OUT}')
