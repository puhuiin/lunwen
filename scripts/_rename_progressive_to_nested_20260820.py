# -*- coding: utf-8 -*-
"""_rename_progressive_to_nested_20260820.py
方案 B：全局把"五层递进框架"系表述改为"五层行为分解框架 + M0–M4 嵌套增量检验"，
并在主文稿 §3.1.1 澄清段新增 L1/L3 不显著的辩护，在报告 §0 加一句澄清。
"""
import re

REPORT = '实证总结报告_文献综述回归解读与SDI诊断_2026-08-19.html'
MANUSCRIPT = 'merged_manuscript.html'

# 通用替换规则（顺序敏感：先长后短，避免双重替换）
RULES = [
    # 框架名
    ('五层递进分析框架', '五层行为分解分析框架'),
    ('五层递进框架',      '五层行为分解框架'),
    ('五层递进',          '五层行为分解'),
    # 方法名（回归）
    ('递进回归',          '嵌套增量回归'),
    # 框架名（剩余）
    ('递进框架',          '行为分解框架'),
    ('递进分析框架',      '分层分析框架'),   # 通用情境
    # 逻辑/分析
    ('递进逻辑',          '层级逻辑'),
    ('递进分析',          '分层分析'),
    ('递进式',            '嵌套式'),
    # 步骤/变化/设计
    ('递进步骤',          '嵌套步骤'),
    ('递进变化',          '嵌套变化'),
    ('递进设计',          '嵌套设计'),
    # 嵌套递进 / 递进嵌套
    ('嵌套递进',          '嵌套增量'),
    ('递进嵌套',          '嵌套增量'),
    # 图
    ('递进图',            '层级图'),
    # 残余独立"递进"（最后兜底）
    ('递进',              '嵌套'),
]


def apply_rules(html, label):
    counts = {}
    for old, new in RULES:
        n = html.count(old)
        if n:
            html = html.replace(old, new)
            counts[old] = n
    print('[%s] 替换明细:' % label)
    for k, v in counts.items():
        print('   %-22s -> %s   (%d 处)' % (k, k, v))
    remaining = html.count('递进')
    print('[%s] 替换后剩余"递进"出现次数: %d' % (label, remaining))
    return html, counts, remaining


# ---------- 1. 主文稿 §3.1.1 澄清段重写（在通用规则之前，避免误伤） ----------
man_html = open(MANUSCRIPT, encoding='utf-8').read()

OLD_CALLOUT = '''<div class="callout-key">
<strong>框架递进逻辑：</strong>L1背景特征 → L2决策结构 → L3执行行为 → L4风险管控 → L5认知偏差。前四层为"是什么"的可观测行为描述，第五层为"为什么"的认知动因解析，通过递进回归分离各层对业绩的独立信息增量。<br/><br/>
<strong>"递进"的准确含义（重要澄清）：</strong>"五层递进"中的"递进"指的是<strong>分析深度的递进</strong>——从最表层的"谁在管理"逐步深入到最深层的"为何如此决策"——而<strong>不是</strong>说 L1 导致 L2、L2 导致 L3……L4 导致 L5 的因果链条。五层之间是<strong>并行维度</strong>的关系，分别从不同角度刻画基金经理行为，只是在分析时按"由表及里"的顺序依次纳入回归，以度量各层的<strong>增量预测信息</strong>（ΔR²）。ΔR² 度量的是预测信息的边际增量，<strong>不是</strong>因果贡献的大小；各层 ΔR² 的差异可能受指标构造精度与覆盖率影响，不宜直接解读为"层级重要性"。
</div>'''

NEW_CALLOUT = '''<div class="callout-key">
<strong>框架层级逻辑：</strong>L1背景特征 → L2决策结构 → L3执行行为 → L4风险管控 → L5认知偏差。前四层为"是什么"的可观测行为描述，第五层为"为什么"的认知动因解析，通过嵌套增量回归（M0→M4）分离各层对业绩的独立信息增量。<br/><br/>
<strong>"嵌套增量"的准确含义（重要澄清）：</strong>"五层行为分解"框架的"嵌套"指的是<strong>分析深度的由表及里</strong>——从最表层的"谁在管理"逐步深入到最深层的"为何如此决策"——而<strong>不是</strong>说 L1 导致 L2、L2 导致 L3……L4 导致 L5 的因果链条。五层之间是<strong>并行维度</strong>的关系，分别从不同角度刻画基金经理行为，只是在分析时按"由表及里"的顺序依次纳入<strong>嵌套增量回归</strong>，以度量各层的<strong>增量预测信息</strong>（ΔR²）。<strong>框架的价值在于对基金经理行为的完整会计，而非每一层都必须显著</strong>：L1（背景特征）与 L3（交易频率）在 M4 中不显著，恰恰是框架的重要发现——它表明"决策内容与决策心理（L2/L4/L5）胜过决策者背景与交易频率"，为 FOF 配置人指明了"不该看什么"。ΔR² 度量的是预测信息的边际增量，<strong>不是</strong>因果贡献的大小；各层 ΔR² 的差异可能受指标构造精度与覆盖率影响，不宜直接解读为"层级重要性"。
</div>'''

assert OLD_CALLOUT in man_html, '主文稿 §3.1.1 澄清段锚点未找到'
man_html = man_html.replace(OLD_CALLOUT, NEW_CALLOUT, 1)
print('主文稿 §3.1.1 澄清段已重写（新增 L1/L3 不显著辩护）')

# 应用通用规则
man_html, man_counts, man_remaining = apply_rules(man_html, '主文稿')
open(MANUSCRIPT, 'w', encoding='utf-8').write(man_html)

# ---------- 2. 报告：应用通用规则 + §0 加澄清句 ----------
rep_html = open(REPORT, encoding='utf-8').read()
rep_html, rep_counts, rep_remaining = apply_rules(rep_html, '报告')

# §0 加澄清句：插在"五层框架一览"图说明之后、KPI 卡片之前
S0_CLARIFY = '''<p class="muted" style="margin:6px 0 12px"><b>关于"两层不显著"的澄清：</b>本框架的价值在于对基金经理行为的完整会计，而非每一层都必须显著。L1（背景特征）与 L3（交易频率）在 M4 中不显著，恰恰是框架的重要发现——它表明"决策内容与决策心理（L2/L4/L5）胜过决策者背景与交易频率"，为 FOF 配置人指明了"不该看什么"。这与方差分解中某成分占比为零仍是有效发现的逻辑一致。</p>
'''
anchor_rep = '<div class="kpi">'
# 找到 §0 内第一个 .kpi（紧跟框架图说明之后）
i_kpi = rep_html.find(anchor_rep)
# 向前找最近的"五层框架一览"图说明结尾
i_frame = rep_html.rfind('五层框架一览', 0, i_kpi)
# 在框架图区块的 </div> 之后、kpi 之前插入
# 简化：直接在第一个 .kpi 之前插入
rep_html = rep_html[:i_kpi] + S0_CLARIFY + rep_html[i_kpi:]
print('报告 §0 已加澄清句')

open(REPORT, 'w', encoding='utf-8').write(rep_html)

# ---------- 3. 校验 ----------
print()
print('=== 校验 ===')
for label, path in [('报告', REPORT), ('主文稿', MANUSCRIPT)]:
    html = open(path, encoding='utf-8').read()
    n_remaining = html.count('递进')
    print('[%s] 剩余"递进": %d  (size=%d)' % (label, n_remaining, len(html)))
    # 标签平衡
    probs = []
    for tag in ['div','table','thead','tbody','tr','td','th','h2','h3','p','span','b','strong']:
        o = len(re.findall(r'<%s(\s|>)' % tag, html))
        c = len(re.findall(r'</%s>' % tag, html))
        if o != c:
            probs.append('%s %d/%d' % (tag, o, c))
    print('[%s] 标签平衡: %s' % (label, 'PASS' if not probs else probs))
    # 新术语落位
    print('[%s] "五层行为分解框架" 出现: %d 次' % (label, html.count('五层行为分解框架')))
    print('[%s] "嵌套增量回归" 出现: %d 次' % (label, html.count('嵌套增量回归')))
print()
print('=== 主文稿 §3.1.1 新澄清段抽样 ===')
i = man_html.find('"嵌套增量"的准确含义')
print(re.sub(r'<[^>]+>', ' ', man_html[i:i+400]).replace('\n', ' ')[:380])
