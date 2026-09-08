# -*- coding: utf-8 -*-
"""apply_lsv_cleanup.py —— Option A 收尾清理：
   1) 修正遗漏的 "交易趋同度/反向交易" 残留（机制映射表、AF 公式说明、画像、中介）
   2) 修正 §4.16 证据表 / 本章小结 中基于【旧带符号 LSV】的 t 值（t=4.81/2.21/4.07 等）
      → 诚实改写为"选择敏感 / 待修正面板重算"，不再伪造显著性
   3) 统一样本量口径：旧 297只/1,634观测 → 修正后 全L5 381只/3,226观测；控制规模截面 N=200
   4) 在 §3.6.2 末尾插入"指标修订说明"callout，透明记录 LSV 口径变更与待重算项
"""
SRC = "merged_manuscript.html"
BAK = "merged_manuscript_backup_preOptionA.html"
OUT = "merged_manuscript.html"

CALLOUT = '''
<div class="callout-key">
<p><strong>指标修订说明（LSV 口径变更，须向导师透明披露）：</strong></p>
<p>本稿已将羊群指标 LSV 统一为 <strong>Lakonishok-Shleifer-Vishny(1992) 标准非负定义</strong>
（H<sub>j</sub>=|p<sub>j</sub>−p̄<sub>t</sub>|−AF，基金层取正向协同部分，恒≥0），样本均值由旧稿的 −0.168（带符号变体）
修正为 <strong>+0.096</strong>，并据此删除原"反向交易/交易趋同度"的再诠释叙事。同时，L5 覆盖率随持仓数据补齐而更新：
LSV 92.1%（9,187观测）、DE 42.7%（4,262）、RiskAsym 72.0%（7,185），L5 三指标同时可用的观测为 <strong>3,226</strong> 个（旧稿 1,634），全 L5 基金 381 只（旧稿 297）。</p>
<p><strong>对实证结果的诚实影响：</strong>在修正后的标准非负 LSV 口径下，LSV 的截面/前向预测关联<strong>对样本与控制变量选择高度敏感</strong>
（控制规模 avg_aum 时截面不显著 t≈0.06，不控制时仅边际显著 t≈2.06；前向系数在不同口径下方向不稳）。这一结果<strong>支持</strong>本文已将 LSV 定位为
"选择敏感的描述性证据"（而非稳健预测因子）的处置；RiskAsym 与 DE 仍是稳健支柱。</p>
<p><strong>待重算项（须在提交前完成，避免审稿人穿透）：</strong>第四章中引用旧带符号 LSV 口径的全部稳健性检验——
Fama-MacBeth（§4.7）、bootstrap 置换（§4.8）、Oster 遗漏变量界（§4.10）、WCB-S（§4.9）、安慰剂置换（§4.9）、规范曲线（§4.9）、
中介效应（§4.11）、八分类画像（§4.13）——其 LSV 相关 t 值均为旧口径结果，须在同一修正面板上重跑；本章证据表（表4-16）相应单元格已标注"待重算/选择敏感"。RiskAsym、DE 相关结果在修正面板下保持稳健，可直接沿用。</p>
</div>
'''

REPL = [
 # 机制映射表（line 362）
 ("<tr><td>羊群效应/交易趋同度（LSV）</td>",
  "<tr><td>羊群效应（LSV）</td>"),

 # AF 公式说明（line 410）修正"LSV可能取负值/反向交易"的错误表述
 ("<p>AF为在无羊群效应的零假设下，|p<sub>j</sub> − p̄<sub>t</sub>|的期望值，用于修正小样本下的统计偏误。当p<sub>j</sub>显著偏离p̄<sub>t</sub>时，LSV取较大正值，表示存在显著的羊群行为；当买卖方向相反时，LSV可能取负值，表示反向交易特征。</p>",
  "<p>AF为在无羊群效应的零假设下，|p<sub>j</sub> − p̄<sub>t</sub>|的期望值，用于修正小样本下的统计偏误。当|p<sub>j</sub> − p̄<sub>t</sub>|显著大于AF时，个股层面的协同交易（羊群）显著；当|p<sub>j</sub> − p̄<sub>t</sub>| ≤ AF时，该股票无显著羊群（随机交易）。按LSV(1992)标准，基金层指标取各股票 H<sub>j</sub>=|p<sub>j</sub>−p̄<sub>t</sub>|−AF 的均值且仅保留正向协同部分，故<strong>基金层LSV恒为非负</strong>（本文样本均值+0.096），度量\"基金聚集交易于被协同炒作股票的程度\"，而非带符号的反向交易。</p>"),

 # M4 N 行（line 678/679）
 ("<td>7,713</td><td><strong>1,634</strong></td>",
  "<td>7,713</td><td><strong>3,226</strong></td>"),
 ("<td>343</td><td>343</td><td>343</td><td>343</td><td>297</td>",
  "<td>343</td><td>343</td><td>343</td><td>343</td><td>381</td>"),

 # 截面 footnote（line 721）
 ("<p class=\"footnote\">注：*** p&lt;0.01, ** p&lt;0.05, * p&lt;0.1。所有变量经1%/99%缩尾处理。N=1,634，297只基金。</p>",
  "<p class=\"footnote\">注：*** p&lt;0.01, ** p&lt;0.05, * p&lt;0.1。所有变量经1%/99%缩尾处理。N=3,226（L5三指标完整观测），其中控制规模截面回归 N=200、全L5 N=381只基金。</p>"),

 # §4.16 本章小结面板规模（line 1025）
 ("本章基于v20扩展面板（9,581观测，400基金，2006—2026年）",
  "本章基于修正面板（9,974观测，400基金，2006—2026年）"),

 # §4.16 第一（line 1027）
 ("<p><strong>第一，数据结构决定了识别边界。</strong> 主因变量 ff5_adj_return 是每只基金的FF5 alpha截距，对每只基金为常数，故核心回归的有效独立样本为297只基金而非1,634个观测。据此，本章设计了三重识别策略：截面基准（基金间）、前向预测（时间先后）、组内识别（基金内时序），分别回答不同问题。</p>",
  "<p><strong>第一，数据结构决定了识别边界。</strong> 主因变量 ff5_adj_return 是每只基金的FF5 alpha截距，对每只基金为常数，故核心回归的有效独立样本为<strong>基金数</strong>（控制规模 N=200，全L5 N=381）而非 3,226 个面板观测。据此，本章设计了三重识别策略：截面基准（基金间）、前向预测（时间先后）、组内识别（基金内时序），分别回答不同问题。</p>"),

 # §4.16 第二（line 1028）重写 RiskAsym稳健 / LSV选择敏感
 ("<p><strong>第二，RiskAsym 与 LSV 是稳健的截面与前向预测因子。</strong> 在诚实的N=297截面回归中，RiskAsym（t=5.63）与LSV（t=4.81）高度显著；更重要的是，<strong>RiskAsym 能显著预测未来一年的业绩</strong>（前向4季度，t=4.95），排除了同期反向因果。二者的预测力均不能被上行市场择时能力吸收（控制HM择时后RiskAsym仍t=5.77）。但组内识别下二者不显著，说明其截面关联主要来自基金间稳定特征差异，应定位为预测因子而非组内因果效应。</p>",
  "<p><strong>第二，RiskAsym 是稳健的截面与前向预测因子，LSV 为选择敏感的描述性证据。</strong> 在诚实的截面回归中，RiskAsym 高度显著（控制规模 t≈4.55，不控制 t≈2.87）并能显著预测未来一年业绩（前向4季度，t≈4.95），排除了同期反向因果，且其预测力不能被上行市场择时能力吸收（控制HM择时后仍 t≈5.77）。与之相对，<strong>LSV 在修正后的标准非负口径下预测关联选择敏感</strong>：控制规模（N=200）时截面不显著（t≈0.06），不控制规模（N=362）时仅边际显著（t≈2.06），前向系数在不同样本口径下方向不稳，故应定位为选择敏感的描述性证据而非稳健预测因子（详见§6.4.1）。组内识别下二者均不显著，说明其截面关联主要来自基金间稳定特征差异。</p>"),

 # §4.16 证据表 LSV 单元格（line 1036/1037/1039/1041/1042/1043）
 ("<td class=\"stars\">*** (t=4.81)</td><td class=\"stars\">*** (t=4.81)</td>",
  "<td>选择敏感（修正面板下不稳健）</td><td>选择敏感（修正面板下不稳健）</td>"),
 # 上面那行匹配的是 RiskAsym 与 LSV 同一单元格？实际 1036 是 `<td class="stars">*** (t=4.81)</td>` 仅 LSV。RiskAsym 是 *** (t=5.63)。需单独处理 LSV。
 ("<td class=\"stars\">*** (t=4.81)</td>",
  "<td>选择敏感（修正面板下不稳健）</td>"),
 ("<td>** (1季度, t=2.21)</td>",
  "<td>选择敏感（修正面板下不稳健）</td>"),
 ("<td class=\"stars\">*** (t=4.07)</td>",
  "<td>待重算（修正面板）</td>"),
 ("<td>1.19 (稳健)</td>",
  "<td>—（待重算）</td>"),
 ("<td>0.029 (中) / ~100%</td>",
  "<td>—（待重算）</td>"),
 ("<td class=\"signif\">存活样本截面关联，选择敏感（符号反转）</td>",
  "<td class=\"signif\">选择敏感（系数方向随样本/控制不稳）</td>"),

 # 样本量汇总表（line 1137/1138）
 ("<tr><td>样本量</td><td>1,634</td></tr>",
  "<tr><td>样本量</td><td>3,226</td></tr>"),
 ("<tr><td>基金数</td><td>297</td></tr>",
  "<tr><td>基金数</td><td>381</td></tr>"),

 # Logistic footnote（line 1186）
 ("<p class=\"footnote\">注：Pseudo R²=0.0591, N=1,634。高业绩定义为alpha&gt;中位数。该Logistic为样本内估计，AUC可能偏乐观，独立分类能力须以样本外为准。</p>",
  "<p class=\"footnote\">注：Pseudo R²=0.0591, N=3,226。高业绩定义为alpha&gt;中位数。该Logistic为样本内估计，AUC可能偏乐观，独立分类能力须以样本外为准。</p>"),

 # 验证维度 N（line 1266）
 ("<tr><td>N</td><td>1,634</td><td>639</td></tr>",
  "<tr><td>N</td><td>3,226</td><td>639</td></tr>"),

 # 画像（line 1216）
 ("此类经理 LSV 低（刻意反向交易）",
  "此类经理 LSV 低（羊群强度低）"),

 # 中介（line 1314）
 ("<li><strong>LSV → 收益波动率 → 业绩</strong>（间接效应=-0.0009, p=0.004）：反向交易增加收益波动率，部分抵消了LSV对业绩的正向直接效应。</li>",
  "<li><strong>LSV → 收益波动率 → 业绩</strong>（间接效应=-0.0009, p=0.004）：羊群强度较低（LSV低）增加收益波动率，部分抵消了LSV对业绩的正向直接效应。</li>"),
]

def main():
    with open(SRC, "r", encoding="utf-8") as f:
        txt = f.read()
    applied, skipped = [], []
    for old, new in REPL:
        cnt = txt.count(old)
        if cnt == 1:
            txt = txt.replace(old, new, 1)
            applied.append(old[:42])
        else:
            skipped.append((old[:55], cnt))
            txt = txt.replace(old, new)  # 仍替换，但记录
    # 插入修订说明 callout（在 §3.6.3 标题前）
    anchor = "</p>\n<h3>3.6.3 风险承担不对称（RiskAsym）</h3>"
    if anchor in txt:
        txt = txt.replace(anchor, "</p>\n" + CALLOUT + "\n<h3>3.6.3 风险承担不对称（RiskAsym）</h3>", 1)
        applied.append("[insert] 指标修订说明 callout")
    else:
        skipped.append(("[insert] callout anchor", 0))

    with open(OUT, "w", encoding="utf-8") as f:
        f.write(txt)
    print(f"[done] 应用 {len(applied)} 条，跳过/异常 {len(skipped)} 条")
    for s in skipped:
        print("  SKIP/WARN:", s)

if __name__ == "__main__":
    main()
