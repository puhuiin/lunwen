# -*- coding: utf-8 -*-
"""论文正文补丁（2026-08-30）· 第二十三轮：在 §5 外部效度段后、局限段前插入 B/C/D 三段

B 候选：运气 vs 实力 Bootstrap
C 候选：α 分解（RA/DE 全部来自选股α）
D 候选：类型异质性（小基金 Q5−Q1 最大）

写法：用最小字符表达核心结论；用对".."或"/"等缩字符；f-string 拼接。
"""
import io
import json
import os

P = 'scripts/_draft_docx_20260826.py'
s = io.open(P, encoding='utf-8').read()

# ---------- 1) 加载 B/C/D JSON ----------
add_load = (
    "# 批次③ BCD 候选汇总（2026-08-30 第二十~二十二轮：Bootstrap + α 分解 + 异质性）\n"
    "B_BCD = json.loads((OUT / 'bootstrap_q5q1_2026-08-30.json').read_text(encoding='utf-8'))\n"
    "C_BCD = json.loads((OUT / 'alpha_decomposition_summary_2026-08-30.json').read_text(encoding='utf-8'))\n"
    "D_BCD = json.loads((OUT / 'heterogeneity_by_size_and_market_2026-08-30.json').read_text(encoding='utf-8'))"
)
if 'B_BCD = json.loads' not in s:
    anchor = "# 负号排版统一：全文用 U+2212（−），而 Python 的 {:+.3f} 产出 ASCII 减号，故预先转好。"
    if anchor in s:
        s = s.replace(anchor, add_load + '\n' + anchor, 1)
        print('[1] 已加载 BCD JSON')
    else:
        print('[1] MISS: 未找到加载锚点')
else:
    print('[1] BCD 已存在，跳过')

# ---------- 2) 在外部效度段后、局限段前插入 B/C/D 三段 ----------
anchor_ext_end = "是最稳健外部支持；L4a timing ρ=0.130 n.s.、<b>是负面证据</b>。"
anchor_lim_start = "para(doc, f\"局限有五"

if 'BCD 写入' not in s:
    if anchor_ext_end in s and anchor_lim_start in s:
        bcd = (
            "# ---------- 批次③ BCD 三个候选（2026-08-30 第二十~二十二轮） BCD 写入 ----------\n"
            "para(doc,\n"
            "    f\"<b>运气 vs 实力</b>。Q5−Q1 经验 95% CI = \"\n"
            "    f\"[{B_BCD['ff5_alpha_bootstrap']['ci_lo']*100:.2f}pp, \"\n"
            "    f\"{B_BCD['ff5_alpha_bootstrap']['ci_hi']*100:.2f}pp]，\"\n"
            "    f\"{B_BCD['ff5_alpha_bootstrap']['n_valid']} 次 Bootstrap 全在 0 之上，\"\n"
            "    f\"<b>综合能力区分度不可被截面运气解释</b>。\")\n"
            "para(doc,\n"
            "    f\"<b>α 分解</b>。RA/DE 对选股α 预测力稳健显著\"\n"
            "    f\"（截面 t={C_BCD['截面_选股α_DV1']['risk_asym']['t']:+.2f}/\"\n"
            "    f\"{C_BCD['截面_选股α_DV1']['de']['t']:+.2f}，\"\n"
            "    f\"前向 t→t+1 RA t={C_BCD['前向t→t+1_选股α']['risk_asym']['t']:+.2f}），\"\n"
            "    f\"对择时贡献全部 n.s.（RA t={C_BCD['截面_择时贡献_DV2']['risk_asym']['t']:+.2f}）；\"\n"
            "    f\"<b>认知层预测力来自选股能力，非择时</b>。\")\n"
            "para(doc,\n"
            "    f\"<b>类型异质性</b>。按规模 3 等分：\"\n"
            "    f\"小基金 n={D_BCD['规模_3分位']['小']['n']} Q5−Q1=\"\n"
            "    f\"{D_BCD['规模_3分位']['小']['Q5_minus_Q1']*100:+.2f}pp (t={D_BCD['规模_3分位']['小']['t_top_vs_bottom']:+.2f})，\"\n"
            "    f\"中 n={D_BCD['规模_3分位']['中']['n']} \"\n"
            "    f\"{D_BCD['规模_3分位']['中']['Q5_minus_Q1']*100:+.2f}pp \"\n"
            "    f\"(t={D_BCD['规模_3分位']['中']['t_top_vs_bottom']:+.2f})，\"\n"
            "    f\"大 n={D_BCD['规模_3分位']['大']['n']} \"\n"
            "    f\"{D_BCD['规模_3分位']['大']['Q5_minus_Q1']*100:+.2f}pp \"\n"
            "    f\"(t={D_BCD['规模_3分位']['大']['t_top_vs_bottom']:+.2f})，\"\n"
            "    f\"均显著为正；<b>小基金 Q5−Q1 最大</b>，与 L1 边界条件论断一致。\")\n"
        )
        # 插入到"局限" para 之前
        s = s.replace(anchor_lim_start, bcd + anchor_lim_start, 1)
        print('[2] BCD 三段已插入')
    else:
        print('[2] MISS: 锚点')
else:
    print('[2] BCD 已存在，跳过')

io.open(P, 'w', encoding='utf-8').write(s)
print('补丁已写入', P)