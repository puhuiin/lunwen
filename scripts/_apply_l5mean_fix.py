# -*- coding: utf-8 -*-
"""修复L5描述统计跨位置不一致：
A. 幽灵数字 +0.089 -> +0.088 （8处，逐处上下文锚定）
B. L593 -0.1274 -> -0.1266 （对齐表4-2缩尾口径）
C. 表3-2脚注补充口径声明
"""
import shutil, sys

P = 'merged_manuscript.html'
BAK = 'merged_manuscript_bak_l5mean_0723.html'

with open(P, encoding='utf-8') as f:
    s = f.read()

applied, fails = [], []

def rep(old, new, label):
    global s
    n = s.count(old)
    if n == 1:
        s = s.replace(old, new)
        applied.append(label)
    else:
        fails.append((label, n))

# A. +0.089 -> +0.088 (8处，每处独立上下文锚定，避开p值0.089和Adj R² 0.0895)
rep('中国基金LSV均值为+0.089（正向羊群强度）',
    '中国基金LSV均值为+0.088（正向羊群强度）', 'L179')
rep('中国基金整体LSV均值为+0.089（标准LSV1992非负羊群强度',
    '中国基金整体LSV均值为+0.088（标准LSV1992非负羊群强度', 'L201')
rep('正向羊群（LSV均值=+0.089，标准LSV1992非负口径）',
    '正向羊群（LSV均值=+0.088，标准LSV1992非负口径）', 'L220')
rep('基金层均值恒为非负（本文样本均值+0.089）',
    '基金层均值恒为非负（本文样本均值+0.088）', 'L353')
rep('中国基金经理LSV均值为<strong>+0.089</strong>',
    '中国基金经理LSV均值为<strong>+0.088</strong>', 'L417')
rep('修正为 <strong>+0.089</strong>',
    '修正为 <strong>+0.088</strong>', 'L426')
rep('样本均值 +0.089（基金层均值恒≥0）',
    '样本均值 +0.088（基金层均值恒≥0）', 'L515')
rep('样本中LSV均值为正（+0.089）',
    '样本中LSV均值为正（+0.088）', 'L1554')

# B. -0.1274 -> -0.1266 (对齐§4.1.3缩尾口径)
rep('<strong>第一，处置效应(DE)均值为-0.1274</strong>',
    '<strong>第一，处置效应(DE)均值为-0.1266</strong>', 'L593')

# C. 表3-2脚注补充口径声明
rep('注：覆盖率以全面板9,974个基金-季度观测为分母。',
    '注：覆盖率以全面板9,974个基金-季度观测为分母。表中均值与标准差为原始（未缩尾）口径，'
    '刻画指标构建后的原生分布；变量进入回归前的1%/99%缩尾口径描述统计见表4-2（如DE由-0.126变为-0.1266）。',
    '表3-2脚注')

if fails:
    print('FAILS:', fails)
    sys.exit(1)

shutil.copy(P, BAK)
with open(P, 'w', encoding='utf-8') as f:
    f.write(s)

print('APPLIED %d/%d:' % (len(applied), len(applied)))
for x in applied:
    print('  ok', x)
