# -*- coding: utf-8 -*-
"""P0 修复：为 5层架构 §7.10 / §7.11 / §7.12.1 插入 v3 更正横幅，
覆盖此前遗漏的「全通过 / 28-28=100% / 10-10=100% / IV β=0.34-0.41 / Oster 41.84 / 94.4%」活陈旧主张。
策略：在 §7.10、§7.11 节头之后各插入一个红框，声明整节为 v20/v21/v22-era 历史审计、已被 v3 推翻；
在 §7.12.1 M0-M4 表之前插入红框声明该表为 v20 口径。
"""
import io, sys

PATH = r"D:/Desktop/基金经理行为分析研究/5层架构完整研究方案/5层架构完整研究方案.html"

# 三个锚点
A_710 = '<h3>7.10 严格++审计：WCB-S修正 + 残差诊断 + 内生性深化 + 贝叶斯 + 结构断点 + 面板诊断</h3>'
A_711 = '<h3>7.11 深度审计：IV多方法 + FM序列相关校正 + Oster界 + 随机化推断 + 有效样本量</h3>'
A_7121 = '<h3>7.12.1 M0-M4递进回归核心结果</h3>'

BANNER_710 = (
    '<div class="callout danger"><p><strong>⚠️ v3 更正（7.10 严格++审计 / v20-era）</strong>：'
    '本节为 v20 面板审计结论。v3 诚实重分析下：① WCB-S 仅 risk_asym 边际显著（p=0.049），非「全通过」；'
    '② 贝叶斯 BF&gt;10²²、随机化推断、Hansen J/Anderson-Rubin 等均基于 v20 面板——v3 下 IV/2SLS/Hausman '
    '因滞后一期工具变量交集塌缩（iv_N=0）不可复现，相关因果结论已作废；'
    '③ 「发表就绪率 28/28=100%」为 v20 口径，非 v3 结论。权威值见顶部《v3 诚实重分析更正对照总表》与 merged_manuscript.html。</p></div>'
)
BANNER_711 = (
    '<div class="callout danger"><p><strong>⚠️ v3 更正（7.11 深度审计 / v21·v22-era）</strong>：'
    '本节 LIML/GMM IV、FM-NW、DK SE、随机化推断、有效样本量、LOO-CV 等均为 v20/v21/v22 面板结果。v3 诚实重分析下：'
    '① IV/2SLS/Hausman 不可复现（滞后一期工具变量交集塌缩，iv_N=0），原「IV β=0.34–0.41、OLS 向下偏倚」结论作废；'
    '② Oster δ 全为负（de −2.87 / lsv −2.66 / risk_asym −1.65），原「δ=41.84 极度稳健」被推翻（见 7.11.5）；'
    '③ 规范曲线为 60 设定 DE 52/60(86.7%) / RA 43/60(71.7%) / LSV 34/60(56.7%)，非「94.4%/100%」；'
    '④ 样本量以 v3 诚实 M4 N=2,264 / 348 基金为准（非 v20 的 1,003 / 200）。'
    '「10/10 全维度达标」为 v22 口径，非 v3 结论。</p></div>'
)
BANNER_7121 = (
    '<div class="callout danger"><p><strong>⚠️ v3 更正（7.12.1 M0–M4 表 / v20-era）</strong>：'
    '下表 N=1,634、R²=0.2086、ΔR²=0.0728（34.9%）为 v20 面板结果。v3 诚实 M4（N=2,264 / 348 基金 / R²=0.129）'
    '下 L5 增量 R² 仅 0.0224（同样本），三指标未全显著（见本节顶部更正框）。</p></div>'
)

with io.open(PATH, 'r', encoding='utf-8') as f:
    s = f.read()

def insert_after(s, anchor, banner, tag):
    if anchor not in s:
        raise AssertionError("anchor not found: " + tag)
    if banner in s:
        raise AssertionError("banner already present: " + tag)
    # 在 anchor 行后插入（anchor 独占一行）
    return s.replace(anchor, anchor + "\n" + banner, 1)

s = insert_after(s, A_710, BANNER_710, "7.10")
s = insert_after(s, A_711, BANNER_711, "7.11")
s = insert_after(s, A_7121, BANNER_7121, "7.12.1")

with io.open(PATH, 'w', encoding='utf-8') as f:
    f.write(s)

# 校验：标签平衡 + 红框计数
import re
secs = s.count('<section>')
sec_e = s.count('</section>')
tbl = s.count('<table>'); tbl_e = s.count('</table>')
div = s.count('<div'); div_e = s.count('</div>')
v3 = s.count('v3 更正')
print("insertions done. v3更正 count =", v3)
print("section %d/%d  table %d/%d  div %d/%d" % (secs, sec_e, tbl, tbl_e, div, div_e))
assert secs == sec_e and tbl == tbl_e and div == div_e, "TAG IMBALANCE!"
print("TAG BALANCE OK")
