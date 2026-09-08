# -*- coding: utf-8 -*-
import io

DP = r"D:/Desktop/基金经理行为分析研究/.workbuddy/memory/2026-08-16.md"
MP = r"D:/Desktop/基金经理行为分析研究/.workbuddy/memory/MEMORY.md"

daily = (
    "\n## 实证结论—证据强度总览（深度优化 · 收口整合）\n"
    "- 动机：将 v4 诚实重估 + lsv/DE 两审计 + 稳健性章集成 的成果收口为单一审稿人可穿透的\"证据强度总览\"。\n"
    "- 落点：① manuscript 新增 §6.1.7「实证结论与证据强度总览」，单一数据源（_build_evidence_overview.py）生成 L1–L5 共 12 行证据表（M4 双向聚类系数/t/p + WCB p + 置换 p + A/B/C 分级 + 效度边界与稳健性索引）；A 级=RiskAsym/DE/AS/ICI/ARG/基金年龄，C 级=LSV/SDI/TO_wind/收益波动率/经理任期/行业HHI；② 独立工件 实证结论_证据强度总览_2026-08-16.html（同表+总览结论+分级图例）；③ 修正 §6.1.2 残留 DE 覆盖率 46.5%→46.6%；④ 补充口径说明（DE 观测层 46.6% vs 基金层约 46.5%，分母不同非矛盾）。\n"
    "- 校验：插入后 h2/h3/table/div 平衡（54/54、108/108、56/56、118/118），数值与 v4 基准表 / lsv·de 审计 CSV 逐字一致；grade 配色 CSS 已注入 §6.1.7 作用域。\n"
    "- 至此整条\"审查—诊断—披露—收口\"闭环完成：v4 重估 → 画像文档对齐 → lsv 脆弱性(§4.4.8) → de 选择性(§4.4.9) → 稳健性章集成 → 全稿一致性 → 证据强度总览。\n"
)
d = io.open(DP, encoding="utf-8").read()
assert "证据强度总览（深度优化" not in d
io.open(DP, "w", encoding="utf-8").write(d.rstrip() + "\n" + daily)
print("daily log appended")

m = io.open(MP, encoding="utf-8").read()
anchor = "稳健性章已集成 L5 指标专门诊断（2026-08-16）"
assert anchor in m, "MEMORY anchor missing"
bullet = (
    "；另已新增 **§6.1.7 证据强度总览**（A/B/C 分级表，单一数据源 `_build_evidence_overview.py`，"
    "独立工件 `实证结论_证据强度总览_2026-08-16.html`）。"
)
m2 = m.replace(anchor, anchor + bullet, 1)
assert m2 != m
io.open(MP, "w", encoding="utf-8").write(m2)
print("MEMORY.md pointer added")
