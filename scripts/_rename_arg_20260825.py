# -*- coding: utf-8 -*-
"""把「调仓收益 ARG」统一改名为「调仓收益」（保留英文缩写ARG/变量名不变）"""
import os

ROOT = r'd:\Desktop\基金经理行为分析研究'
# 活跃文件（backups/、.workbuddy/ 中的历史备份不动）
TARGETS = [
    '指标总表_五层框架.html',
    '指标总表_计算方式与含义.csv',
    '指标总表_计算方式与含义.xlsx',  # xlsx无法文本替换，跳过并提示
]

# reports/ 和 scripts/ 下的活跃文件
for d in ['reports', 'scripts']:
    dp = os.path.join(ROOT, d)
    if os.path.isdir(dp):
        for fn in os.listdir(dp):
            if fn.endswith(('.md', '.html', '.py', '.csv', '.json')):
                TARGETS.append(os.path.join(d, fn))

changed = []
skipped_xlsx = []
for rel in TARGETS:
    fp = os.path.join(ROOT, rel)
    if not os.path.exists(fp):
        continue
    if fp.endswith('.xlsx'):
        skipped_xlsx.append(rel)
        continue
    with open(fp, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()
    # 主替换：调仓收益 → 调仓收益
    new = content.replace('调仓收益', '调仓收益')
    # 残余形式：调仓收益缺口（不带波动）也统一改
    new = new.replace('调仓收益缺口', '调仓收益缺口')
    if new != content:
        with open(fp, 'w', encoding='utf-8') as f:
            f.write(new)
        n1 = content.count('调仓收益')
        n2 = content.count('调仓收益缺口') - n1
        changed.append((rel, n1, n2))

print(f'已修改 {len(changed)} 个文件:')
for rel, n1, n2 in changed:
    print(f'  {rel}: 替换「调仓收益」x{n1}, 「调仓收益缺口」x{n2}')
if skipped_xlsx:
    print(f'\n[提示] xlsx需手动改: {skipped_xlsx}')
