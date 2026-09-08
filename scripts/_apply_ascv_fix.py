# -*- coding: utf-8 -*-
"""修复AS_improved变异系数幽灵对比（0.0495->0.0821, 61.8%->0.2%）：
当前权威管线(v2/v3持仓、双基准)重算均不可复现，按诚实披露原则删除量化对比，
保留定性理由。共3处：L282正文、L284 callout、L544本章小结。
"""
import shutil, sys

P = 'merged_manuscript.html'
BAK = 'merged_manuscript_bak_ascv_0723.html'

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

# L282 正文
rep('这一改进显著提升了指标的区分度：AS指标的变异系数从0.0495提升至0.0821，最常见值占比从61.8%降至0.2%，表明改进后的指标能够更有效地区分不同基金的主动管理程度。',
    '这一改进使指标更贴近基金合同的实际业绩比较基准，避免单一指数对主动程度的系统性低估，从而更有效地区分不同基金的主动管理程度。', 'L282')

# L284 callout
rep('<strong>改进效果：</strong>AS_improved相比原始AS指标，变异系数从0.0495提升至0.0821（提升65.9%），最常见值占比从61.8%降至0.2%，有效解决了原始指标区分度不足的问题。',
    '<strong>改进效果：</strong>AS_improved以复合真实成分股权重为基准，缓解了单一指数基准对主动程度的系统性低估；在当前可复现管线下，原始与改进口径的截面区分度已相当（CV约0.15），改进的意义在于基准设定的真实性而非数值放大。',
    'L284')

# L544 本章小结
rep('其中AS_improved通过采用沪深300与中证500合并真实成分股权重作为基准，显著提升了指标区分度（变异系数从0.0495提升至0.0821）；',
    '其中AS_improved通过采用沪深300与中证500合并真实成分股权重作为基准，使指标更贴近基金实际业绩比较基准；', 'L544')

if fails:
    print('FAILS:', fails)
    sys.exit(1)

shutil.copy(P, BAK)
with open(P, 'w', encoding='utf-8') as f:
    f.write(s)

print('APPLIED %d/3:' % len(applied))
for x in applied:
    print('  ok', x)
