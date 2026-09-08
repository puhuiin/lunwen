# -*- coding: utf-8 -*-
import io, sys

PATH = r"D:\Desktop\基金经理行为分析研究\基金经理能力画像与业绩评价.html"
with io.open(PATH, "r", encoding="utf-8") as f:
    s = f.read()

# minus sign U+2212 used in tables
M = "\u2212"

repls = []

# ---- 表 6.1 (L454-456) ----
repls.append(("+0.113 (2.76)***", "+0.113 (2.75)***", 1))          # risk_asym 截面
repls.append(("+0.061 (0.94)", "+0.064 (0.97)", 1))                 # risk_asym 组内FE
repls.append(("+0.112 (2.04)**", "+0.101 (1.64)", 1))               # lsv 截面 (降为 ns)
repls.append((M+"0.111 ("+M+"1.84)", M+"0.191 ("+M+"3.08)***", 1))  # lsv 组内FE (翻为显著负)
repls.append((M+"0.073 ("+M+"4.50)***", M+"0.070 ("+M+"4.23)***", 1))  # de 截面
repls.append((M+"0.026 ("+M+"3.33)***", M+"0.026 ("+M+"3.27)***", 1))  # de 组内FE

# ---- L469 解读框 ----
old_lsv = "LSV 截面正向（抱团/注意力集中伴随高 alpha，中国市场特征），组内FE转微负，说明其解释力偏截面。"
new_lsv = ("LSV 在<b>新面板下出现口径翻转</b>：截面由正显著(t2.04**)降为<b>不显著</b>(+0.101, t1.64)，"
           "组内FE则由微负("+M+"1.84)升为<b>显著负</b>("+M+"0.191, t"+M+"3.08***)——其符号与显著性高度依赖识别口径，"
           "是整套结果中<b>最脆弱</b>的变量，不可与 RA/de 并列称“均显著”，画像中须降级为“口径依赖/待稳健化”信号。")
repls.append((old_lsv, new_lsv, 1))

repls.append(("显著为正(t2.76)但<b>组内FE不显著(t0.94)</b>",
              "显著为正(t2.75)但<b>组内FE不显著(t0.97)</b>", 1))

# ---- L526 雷达轴说明 ----
old_radar = "L5 认知偏差</b>：RA / lsv 正向、de 负向，三者均显著但方向分化 → 半径次大，是\"混合信号\"维度。"
new_radar = ("L5 认知偏差：de 双口径显著负向；RA 截面显著正、组内FE不显著（分型）；"
             "lsv 口径翻转（截面 ns、组内FE显著负）→ 三者方向分化、证据强度各异，是“混合信号/最需谨慎”维度。")
repls.append((old_radar, new_radar, 1))

# ---- L1069 表11.1 lsv 行 ----
repls.append(("截面 ** / 组内FE 微负", "截面 ns / 组内FE ***（负）", 1))
repls.append(("中国\"抱团/注意力\"截面溢价，非实时技能", "截面溢价在新面板消失；组内FE显著负，符号口径依赖", 1))
repls.append(("截面风格标记", "口径依赖/最脆弱，画像中降格", 1))

# ---- L1105 §11.3 框 ----
old_113 = "risk_asym 组内FE 弱（且 excess 口径翻负）、lsv 组内FE 微负（L5）"
new_113 = "risk_asym 组内FE 弱（且 excess 口径翻负）、lsv 组内FE <b>显著负</b>（新面板口径翻转，L5）"
repls.append((old_113, new_113, 1))

# ---- L1136 原型③ ----
repls.append(("处置效应 de <b>稳定负向</b>、风险不对称/lsv 受控",
              "处置效应 de <b>稳定负向</b>、风险不对称受控、lsv 口径依赖（组内FE显著负）", 1))

# ---- barchart: lsv 行 (L549-551) ----
repls.append(('<rect x="410" y="116" width="219.255" height="16" rx="3" fill="#dc2626"/>',
              '<rect x="410" y="116" width="198.0" height="16" rx="3" fill="#94a3b8"/>', 1))
repls.append(('<text x="635.255" y="128" font-size="12" fill="#dc2626" font-family="sans-serif" text-anchor="start" font-weight="600">+0.112 **</text>',
              '<text x="614.0" y="128" font-size="12" fill="#94a3b8" font-family="sans-serif" text-anchor="start" font-weight="600">+0.101</text>', 1))

# ---- barchart: de 行 (L554-555) ----
repls.append(('<rect x="268.158" y="146" width="141.842" height="16" rx="3" fill="#16a34a"/>',
              '<rect x="274.0" y="146" width="136.0" height="16" rx="3" fill="#16a34a"/>', 1))
repls.append(('<text x="262.158" y="158" font-size="12" fill="#16a34a" font-family="sans-serif" text-anchor="end" font-weight="600">-0.073 *** ⚡组内FE验证</text>',
              '<text x="268.0" y="158" font-size="12" fill="#16a34a" font-family="sans-serif" text-anchor="end" font-weight="600">-0.070 *** ⚡组内FE验证</text>', 1))

# ---- footer date ----
repls.append(("生成日期 2026-08-14。", "生成日期 2026-08-16。", 1))

# ---- v4 复核 callout 插入 (在 L469 解读框之后、C7 注释之前) ----
callout = '''
<div class="box note">
<b>v4 复核（2026-08-16 独立验证）与口径对照：</b>
<ul>
<li><b>复现性</b>：本画像文档的 L5 双口径系数在新面板（主分析面板_重建，MD5=bc0942ce）上重跑复现；RA 与 de 在两种口径下保持显著方向与量级，结论稳健。</li>
<li><b>lsv 脆弱性（重要更新）</b>：注意力偏差 lsv 在 08-14 旧值（截面 +0.112 t2.04**、组内FE '''+M+'''0.111 t'''+M+'''1.84）到新面板发生<b>实质性口径翻转</b>——截面降为 +0.101(t1.64, ns)、组内FE升为 '''+M+'''0.191(t'''+M+'''3.08***)。其符号/显著性高度依赖识别口径，是 L5 三个指标中<b>最脆弱</b>的一个，文档已将它从“均显著”降级为“口径依赖/待稳健化”信号，不再与 RA、de 并列。</li>
<li><b>de 选择性子样本提示</b>：de 仅由半年报 PGR/PLR 构造，覆盖约 46%（结构性、非随机缺失）；其“双口径显著负”结论<b>不外推至全样本</b>，属诚实披露的方法局限。</li>
<li><b>与主文稿 M4 面板模型对照</b>（M4 用主分析面板_重建_含TOwind、FF5 五因子、CGM2011 双向聚类 SE，N=2264/348）：权威双向聚类 t 值下 de β='''+M+'''0.00606(t'''+M+'''2.99***)、lsv β=+0.01548(t+0.77, ns)、risk_asym β=+0.07311(t+3.57***)。<b>注意事项</b>：M4 的 de 是“选择性子样本”（仅含 de 非缺失观测，N 由 9914 降至 2264，降幅 77.3%），且 M4 的口径（面板 FE + 双向聚类）与本画像文档的“截面 + 组内FE 双口径”是<b>不同识别策略</b>，二者不可直接比较数值，仅作敏感性/稳健性参照。</li>
</ul>
</div>
'''
anchor = '<!-- ============ C7 ============ -->'
assert s.count(anchor) == 1, "C7 anchor not unique"
assert anchor not in callout
s_with_callout = s.replace(anchor, callout + "\n" + anchor, 1)

# apply replacements
for old, new, cnt in repls:
    got = s_with_callout.count(old)
    if got != cnt:
        raise SystemExit("ASSERT FAIL: expected %d occurrence(s) of:\n%r\nbut found %d" % (cnt, old, got))
    s_with_callout = s_with_callout.replace(old, new)

with io.open(PATH, "w", encoding="utf-8") as f:
    f.write(s_with_callout)

print("OK: all %d replacements applied; file rewritten." % len(repls))
