# -*- coding: utf-8 -*-
"""
生成分工清单：252篇核心文献按层类对半分配
我(AI)：L2+L3+L5英文+因变量前N，负责方法论/英文/批量
用户：L1+L4+L5中文+因变量后N，负责情境/中文/判断
平衡到各约126篇
"""
import os, re
from pathlib import Path

BASE = Path(r'D:\Desktop\基金经理行为分析研究\参考文献')
cats = ['L1_背景特征层','L2_持仓偏离层','L3_交易行为层','L4_风险应对层','L5_认知行为层','因变量测度']

# 收集各类文献
inventory = {}
for cat in cats:
    p = BASE / cat
    if not p.is_dir(): continue
    pdfs = sorted([f for f in os.listdir(p) if f.endswith('.pdf')])
    cn = [f for f in pdfs if re.search(r'[\u4e00-\u9fff]', f)]
    en = [f for f in pdfs if f not in cn]
    inventory[cat] = {'all': pdfs, 'cn': cn, 'en': en}

# 分工方案
ai_picks = []
user_picks = []

# L2, L3 全归AI（方法论层，英文为主）
for cat in ['L2_持仓偏离层','L3_交易行为层']:
    for f in inventory[cat]['all']:
        ai_picks.append((cat, f))

# L5 英文归AI，中文归用户
for f in inventory['L5_认知行为层']['en']:
    ai_picks.append(('L5_认知行为层', f))
for f in inventory['L5_认知行为层']['cn']:
    user_picks.append(('L5_认知行为层', f))

# L1, L4 全归用户（情境层，中文为主）
for cat in ['L1_背景特征层','L4_风险应对层']:
    for f in inventory[cat]['all']:
        user_picks.append((cat, f))

# 因变量测度：对半分（前N归AI，后N归用户），AI多担一些平衡
dy = inventory['因变量测度']['all']
# 目标：AI总约126，当前AI=L2(15)+L3(14)+L5英(25)=54，需补72到126
# 用户当前=L1(53)+L4(23)+L5中(57)=133，已超126，用户少分因变量
ai_dy = 65  # AI担因变量大部分
user_dy = 0
ai_picks += [('因变量测度', f) for f in dy[:ai_dy]]
# 用户因变量0篇（已133篇）

print(f'AI负责: {len(ai_picks)}篇')
print(f'用户负责: {len(user_picks)}篇')
print(f'AI各类: ', end='')
from collections import Counter
ai_cat = Counter(c for c,_ in ai_picks)
user_cat = Counter(c for c,_ in user_picks)
for cat in cats:
    print(f'{cat.split("_")[0]}={ai_cat.get(cat,0)}/{user_cat.get(cat,0)}', end=' ')
print()

# 写分工清单
out = ['# 文献研读分工清单\n', f'> 生成时间：2026-08-11 | 总计{len(ai_picks)+len(user_picks)}篇\n\n']
out.append('## 一、分工原则\n')
out.append('- **WorkBuddy（AI）**：负责方法论层（L2/L3）、L5英文理论文献、因变量测度大部分。擅长批量PDF阅读与结构化提取。\n')
out.append('- **用户**：负责情境层（L1/L4）、L5中文文献。需专业判断与中国本土情境理解。\n\n')

out.append(f'## 二、WorkBuddy 负责（{len(ai_picks)}篇）\n\n')
out.append('| 序号 | 层类 | 文件名 |\n|------|------|--------|\n')
for i, (cat, f) in enumerate(ai_picks, 1):
    out.append(f'| {i} | {cat} | {f} |\n')

out.append(f'\n## 三、用户 负责（{len(user_picks)}篇）\n\n')
out.append('| 序号 | 层类 | 文件名 |\n|------|------|--------|\n')
for i, (cat, f) in enumerate(user_picks, 1):
    out.append(f'| {i} | {cat} | {f} |\n')

out.append('\n## 四、文献卡片模板（每篇产出）\n\n')
out.append('```markdown\n### [文献编号] 作者(年份) 简称\n')
out.append('- **核心观点**：一句话概括主结论\n')
out.append('- **方法**：实证方法/模型（如OLS/FM回归/事件研究）\n')
out.append('- **数据**：样本范围（如"中国偏股基金2010-2020"）\n')
out.append('- **关键变量**：自变量/因变量定义\n')
out.append('- **主要结论**：系数方向+显著性\n')
out.append('- **与本文关联**：⭐⭐⭐核心/⭐⭐重要/⭐边缘 + 具体用途（如"DE指标方法依据"）\n')
out.append('- **可引用段落**：可直接用于论文的表述（可选）\n```\n')

out.append('\n## 五、产出文件位置\n\n')
out.append('- WorkBuddy产出：`文献/研读卡片_AI/` 目录，每类一个md文件\n')
out.append('- 用户产出：`文献/研读卡片_用户/` 目录\n')
out.append('- 命名：`[层类]_[序号]_[文献简称].md`\n')

with open(BASE / '文献研读分工清单.md', 'w', encoding='utf-8') as f:
    f.write(''.join(out))
print(f'\n已保存: 参考文献/文献研读分工清单.md')
print(f'AI: {len(ai_picks)}篇, 用户: {len(user_picks)}篇')
