# -*- coding: utf-8 -*-
"""prune2: 忠实'只用双边 TO'意图，清理两交付物中残留的单边买卖分解(TO_buy/TO_sell)呈现。
镜像 apply_edits_prune.py 的外科手术式字符串/切片编辑风格。"""
import re

PROFILE = r"D:/Desktop/基金经理行为分析研究/基金经理能力画像与业绩评价.html"
REPORT  = r"D:/Desktop/基金经理行为分析研究/实证结果完整报告与论文写作指南.html"

def apply(path, plain, regex, slices):
    with open(path, encoding="utf-8") as f:
        s = f.read()
    orig_len = len(s)
    log = []
    for old, new, label in plain:
        c = s.count(old)
        if c == 0:
            log.append(f"  [WARN] 未命中: {label}")
        else:
            s = s.replace(old, new)
            log.append(f"  [OK] 替换 {c} 次: {label}")
    for pat, repl, label in regex:
        new_s, c = re.subn(pat, repl, s, flags=re.DOTALL)
        if c == 0:
            log.append(f"  [WARN] 正则未命中: {label}")
        else:
            s = new_s
            log.append(f"  [OK] 正则替换 {c} 次: {label}")
    for start, end, label in slices:
        i = s.find(start)
        j = s.find(end)
        if i == -1 or j == -1:
            log.append(f"  [WARN] 切片未找到: {label} (i={i}, j={j})")
        else:
            s = s[:i] + s[j:]
            log.append(f"  [OK] 切片删除 {label}")
    with open(path, "w", encoding="utf-8") as f:
        f.write(s)
    log.append(f"  [INFO] 长度 {orig_len} -> {len(s)}")
    return log

# ---------------- PROFILE ----------------
profile_plain = [
    ('<li><a href="#c4">L3 交易执行层 —— 交易行为（含换手单边诊断）</a></li>',
     '<li><a href="#c4">L3 交易执行层 —— 交易行为（含换手率与选择性交易）</a></li>',
     'TOC c4'),
    ('<h2 id="c4">4 · L3 交易执行层 —— 交易行为（含换手单边诊断）</h2>',
     '<h2 id="c4">4 · L3 交易执行层 —— 交易行为（含换手率与选择性交易）</h2>',
     'h2 c4'),
    ('<code>output/R3_gamma截尾重跑.csv</code>、<code>output/TO单边分析.csv</code>。',
     '<code>output/R3_gamma截尾重跑.csv</code>。',
     'honest decl file'),
    ('<code>15_R3_gamma截尾重跑.py</code>、<code>16_TO单边分析.py</code> 及既有前向/LSV 回归',
     '<code>15_R3_gamma截尾重跑.py</code> 及既有前向/LSV 回归',
     'source list (x2)'),
    ('需分解/换口径才能显形（TO、SDI）',
     '需换口径才能显形（SDI 择时选择性）',
     'framework bullet'),
]
profile_regex = [
    (r'；单边买卖分解（TO_buy/TO_sell）仅作探索性稳健性，用于揭示.买/卖活跃方向相反.的微观结构，<b>不提高覆盖、也不进主模型</b>。',
     '；不做单边买卖分解。',
     '口径约定'),
    (r'必须靠.买卖分解.或.选择性\(SDI\).提取结构，这正是 L3 的方法论贡献。',
     '必须靠“选择性(SDI) 择时交易”提取结构，这正是 L3 的方法论贡献。',
     '11.3 box'),
    (r'<tr><td>TO_buy / TO_sell.*?</tr>\n',
     '',
     'sumtab row'),
]
profile_slices = [
    ('<h3>11.4', '<h3>11.5', 'remove 11.4 section'),
]

# ---------------- REPORT ----------------
report_plain = [
    ('<code>output/</code> 下的 CSV（分层回归、组内FE、R3 截尾、TO 单边、前向、LSV 重算）',
     '<code>output/</code> 下的 CSV（分层回归、组内FE、R3 截尾、前向、LSV 重算）',
     'lead CSV list'),
    ('双边 ns；买卖分解符号相反（粒度>覆盖）',
     '双边 ns（N=200 受限）',
     'L3 sumtab cell'),
    ('，单边买卖分解仅作探索性稳健性、不进主模型、不提高覆盖。',
     '，不做单边买卖分解。',
     'school box 口径约定'),
    ('<h3>C · L3 交易执行层 + 换手单边诊断</h3>',
     '<h3>C · L3 交易执行层 + 换手与选择性交易</h3>',
     'L3 heading'),
    ('双边=单边=200 只（18%）',
     'TO 双边仅覆盖 200 只（18%）',
     'pres box part1'),
    ('、TO 单边、前向',
     '、前向',
     'honest decl'),
    ('R3_gamma截尾重跑、TO单边分析、前向回归核对',
     'R3_gamma截尾重跑、前向回归核对',
     'source list'),
]
report_regex = [
    (r'<tr><td>买卖分解</td>.*?</tr>\n',
     '',
     'L3 table rows (x2)'),
    (r'<div class="box key">\n<b>结论（含用户提出的.单边能否提高覆盖率.问题，已实测）</b>：.*?</div>\n',
     '<div class="box key">\n<b>结论</b>：底层交易源文件仅覆盖 200 只基金（约 18%），这是“源文件只覆盖 200 只”的结构性限制，覆盖率提升依赖 CSMAR/Wind/iFinD 授权数据导出后重跑 <code>run_all.py</code>，非算法可解。双边换手率 TO_two_sided 与 alpha 无显著关系（ns）——换手是“技能+交易成本损耗”的混合，净效应抵消。组内FE（R6+TO, N=1043）下 SDI β=+0.021(t2.33)** 转显著，提示交易选择性（而非原始换手）在控制基金固定效应后更有解释力。\n</div>\n',
     'L3 conclusion box'),
    (r'主回归表列 \(1\) 双边 TO、(2) 买卖分解，把.买正卖负、符号相反.作为核心发现用<b>加粗异号</b>凸显',
     '主回归表以双边 TO_two_sided 为规范测度，并附 SDI（选择性交易）作为交易行为轴',
     'pres box part2'),
    (r'必须靠.买卖分解.或.选择性\(SDI\).提取结构，这正是 L3 的方法论贡献。',
     '必须靠“选择性(SDI) 择时交易”提取结构，这正是 L3 的方法论贡献。',
     'box rephrase'),
    (r'<tr><td>TO_buy / TO_sell.*?</tr>\n',
     '',
     'sumtab row'),
]
report_slices = [
    ('<h3>3.5.4', '<h3>3.5.5', 'remove 3.5.4 section'),
]

print("== PROFILE ==")
for line in apply(PROFILE, profile_plain, profile_regex, profile_slices):
    print(line)
print("== REPORT ==")
for line in apply(REPORT, report_plain, report_regex, report_slices):
    print(line)
print("DONE")
