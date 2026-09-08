# -*- coding: utf-8 -*-
import io

P = r"D:/Desktop/基金经理行为分析研究/.workbuddy/memory/2026-08-16.md"
s = io.open(P, encoding="utf-8").read()

HEADER = "## manuscript 稳健性章集成 lsv+de 两节专门诊断（深度优化 · 收口）"
idx = s.find(HEADER)
assert idx != -1, "note header not found"

# 截断到该 note 之前（保留此前所有日志），重写该 note（无反引号，避免 shell 命令替换问题）
head = s[:idx].rstrip() + "\n"

note = (
    "\n"
    "## manuscript 稳健性章集成 lsv+de 两节专门诊断（深度优化 · 收口）\n"
    "- 动机：前序完成 lsv 脆弱性诊断（11 规格电池）与 de 选择性子样本审计（6 规格敏感性）两份报告，用户确认“继续深度优化”=将其正式写入主文稿稳健性章。\n"
    "- 落点：merged_manuscript.html 的 §4.4 稳健性检验章新增两节（插入脚本 _insert_manuscript_robust_l5.py，断言锚点 <h2>4.5 出现 1 次）：\n"
    "  - §4.4.8 LSV（注意力偏差）稳健性诊断：VIF=1.15（非共线）、B–F 缩尾/去极值/非线性均 ns（非数据假象）、J 隔离同层 de/RA→lsv +0.027(t2.78***)（被掩盖机制）、G 2022+ lsv +0.025(t2.03**) / H 2022前 ns（时期依存）；结论=LSV 非失败变量而是“时期依存+被同层掩盖”。\n"
    "  - §4.4.9 DE（处置效应）选择性子样本审计：组间可比性（结果 SMD=−0.043 均衡、AS_improved SMD=+1.502 失衡）；6 规格敏感性（A 基线 t−2.99*** / B 均值插补+de_avail −0.00712 t−2.87*** / F 仅2016+ 仍 t−2.99*** 内部稳健；E de_avail 独立预测 alpha +0.0048 t2.18** 选择偏倚）；诚实局限（常数插补未能成真边界）。结论=DE 内部显著、外部效度受限（选择偏倚），与 LSV 性质不同。\n"
    "- 校验：插入后 h3 107/107、table 55/55、div 117/117 平衡；数值与 CSV（lsv_脆弱性诊断电池 / de_选择性审计 / de_组间可比性，均 2026-08-16）逐字一致；负号沿用文稿家规（prose 用 U+2212、表格用 ASCII 减号）。\n"
    "- 两份原始报告 lsv_脆弱性诊断报告_2026-08-16.md、de_选择性诊断报告_2026-08-16.md 与画像文档 §6 v4 callout 均已对齐引用。\n"
)

io.open(P, "w", encoding="utf-8").write(head + note)
print("daily log note 已干净重写；文件长度", len(head + note))
print("has merged_manuscript.html:", "merged_manuscript.html" in (head + note))
print("has _insert_manuscript_robust_l5.py:", "_insert_manuscript_robust_l5.py" in (head + note))
print("has lsv_脆弱性诊断报告:", "lsv_脆弱性诊断报告_2026-08-16.md" in (head + note))
print("has de_选择性诊断报告:", "de_选择性诊断报告_2026-08-16.md" in (head + note))
