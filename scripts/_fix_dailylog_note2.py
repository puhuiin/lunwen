# -*- coding: utf-8 -*-
import io

DP = r"D:/Desktop/基金经理行为分析研究/.workbuddy/memory/2026-08-16.md"
MP = r"D:/Desktop/基金经理行为分析研究/.workbuddy/memory/MEMORY.md"

# ---- daily log append ----
note = """
## manuscript 一致性对齐（深度优化 · 续）
- 动机：将 §4.4.8(LSV 脆弱性)/§4.4.9(DE 选择性) 两节与主文稿其余部分对齐，消除数字与引用不一致，并修正一个章节锚点错位。
- 落点（`merged_manuscript.html`，脚本 `_align_manuscript_de_robust.py` + 一处 Edit）：
  1. **§4.5 锚点错位修正**：原 `<!-- 4.5 内生性与因果推断的边界 -->` 注释错误置于 §4.4.7 之前（line 843），已移至真正的 `<h2>4.5>` 之前（line 903），章节导航恢复正确。
  2. **§6.4.2 集成 DE 选择性审计**：DE 覆盖率由 46.5% 校正为 v4 面板真值 46.6%（观测 4,650/9,974），并交叉引用 §4.4.9，写入 de_avail 独立预测 alpha(+0.0048,t2.18**)、AS_improved SMD=+1.502、结果 SMD=−0.043、均值插补下 β=−0.00712(t−2.87***) 与“不外推全样本/效度边界≈46.6%子群”结论。
  3. **§6.3 证据分级表补 DE 外推边界**：A级说明后新增“DE外推边界”特别说明，明确 A级建议（止损平衡、风险承担优化）外推限于该≈46.6%子群。
  4. **§4.3 与修订说明覆盖率校正**：DE 46.5%→46.6%（含观测数 4,642→4,650），与 v4 面板一致。
- 校验：插入/替换后 h2 54/54、h3 107/107、table 55/55、div 117/117 平衡；全文无残留 DE 46.5%；§4.9 引用经核实指向真实存在的 §4.9 规范曲线分析章（非 dangling），未改动。
"""

d = io.open(DP, encoding="utf-8").read()
io.open(DP, "w", encoding="utf-8").write(d.rstrip() + "\n" + note)
print("daily log appended, new len", len(d) + len(note))

# ---- MEMORY.md pointer ----
m = io.open(MP, encoding="utf-8").read()
anchor = "稳健性章已集成 L5 指标专门诊断（2026-08-16）"
i = m.find(anchor)
assert i >= 0, "anchor not found in MEMORY.md"
add = ("稳健性章已集成 L5 指标专门诊断（2026-08-16）"
       "；并进一步将 §4.4.8/§4.4.9 与主文稿 §6.4.2（覆盖率校正+DE审计交叉引用）、"
       "§6.3 证据分级表（DE 外推边界）、§4.3 对齐，修正 §4.5 注释锚点错位（2026-08-16 续）。")
m = m[:i] + add + m[i+len(anchor):]
io.open(MP, "w", encoding="utf-8").write(m)
print("MEMORY.md pointer updated")
