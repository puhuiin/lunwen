# -*- coding: utf-8 -*-
"""修复 DV 覆盖率陈旧值（v20 残留）为权威面板实测值。断言命中次数，失配不落盘。"""
import io, shutil, datetime

P = r"d:\Desktop\基金经理行为分析研究\merged_manuscript.html"
s = io.open(P, encoding="utf-8").read()
applied, fails = [], []

def fix(old, new, label, expect=1):
    global s
    n = s.count(old)
    if n == expect:
        s = s.replace(old, new)
        applied.append((label, n))
    else:
        fails.append((label, n))

# L477: 数据结构描述节（唯一出现 0.0155 处）
fix('覆盖率为95.2%，覆盖343只基金，均值为0.0155',
    '覆盖率为97.2%（9,698个观测），覆盖362只基金，均值为0.0201', 'l477-desc')

# L478: 核心样本基金数（297 为 v20 面板残留；M4 完整样本为 348 只）
fix('其真正的独立样本量是基金数（核心样本297只）',
    '其真正的独立样本量是基金数（核心样本348只）', 'l478-297')

# 表3-x DV 行
fix('<td>95.2%（343基金）</td>', '<td>97.2%（362基金）</td>', 't-dv-row')

# L158 / L195 / L546: 叙述中的覆盖率（各 1 处）
fix('其在面板中的覆盖率达到95.2%', '其在面板中的覆盖率达到97.2%', 'l158-cov')
fix('本研究采用FF5模型调整后的超额收益作为因变量，覆盖率达95.2%',
    '本研究采用FF5模型调整后的超额收益作为因变量，覆盖率达97.2%', 'l195-cov')
fix('因变量采用Fama-French五因子模型调整后的收益，覆盖率达95.2%',
    '因变量采用Fama-French五因子模型调整后的收益，覆盖率达97.2%', 'l546-cov')

if fails:
    print('FAILS:', fails); print('APPLIED:', applied)
    raise SystemExit(1)
bak = P.replace('.html', '_bak_dvcov_%s.html' % datetime.datetime.now().strftime('%H%M%S'))
shutil.copyfile(P, bak)
io.open(P, 'w', encoding='utf-8').write(s)
print('OK:', applied, '| backup=', bak)
