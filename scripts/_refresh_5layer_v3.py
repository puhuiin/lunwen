# -*- coding: utf-8 -*-
"""5层架构完整研究方案.html -> v3 诚实覆盖层刷新。
策略：顶部免责横幅 + v3更正对照总表 + 各方法学红线就地更正框 + 变量字典修正。
不删除 v20 叙事（保留研究方案历史价值），但用 v3 权威值可见覆盖。
"""
import io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

SRC = r"D:\Desktop\基金经理行为分析研究\5层架构完整研究方案\5层架构完整研究方案.html"
s = open(SRC, encoding='utf-8').read()

reps = []  # (old, new, tag)

# ---------------------------------------------------------------------------
# 0) 顶部免责横幅 + v3 更正对照总表（插入到 </header> 之后、<div class="container"> 之前）
# ---------------------------------------------------------------------------
RECON = r'''
<section style="border:2px solid #c0392b;border-radius:10px;margin:18px 0;padding:4px 18px;background:#fff6f5">
  <div class="callout danger" style="border-left:6px solid #c0392b;margin:16px 0">
    <p><strong>⚠️ 版本状态声明（2026-08-16 更新）</strong>：本文档生成于 <strong>2026-08-08</strong>，
    基于 <strong>v20 扩展面板</strong>与当时的分析脚本，整体呈现"L5 三指标全显著 / Oster δ&gt;1 / WCB-S 全通过 /
    IV 2SLS 确认内生性 / 规范曲线 100% / 十项高级计量全达标"的叙事。该叙事已被
    <strong>v3 诚实重分析（基于重建主面板 9,974 行 / 400 基金，双向聚类 SE，全样本 1%/99% 缩尾）</strong>
    全面推翻。下列结论在 v3 下已不成立或被大幅修正：</p>
    <ul>
      <li><strong>LSV 在诚实 M4 中不再显著</strong>（t=1.23，p=0.22）；原稿 t=3.88*** 为 v20 口径。</li>
      <li><strong>Oster δ 全部为负</strong>（de −2.87 / lsv −2.66 / risk_asym −1.65）→ 原"稳健"结论被推翻。</li>
      <li><strong>IV / 2SLS / Hausman 不可复现</strong>：诚实面板下滞后一期 L5 工具变量交集塌缩（iv_N=0），一律作废。</li>
      <li><strong>WCB-S 仅 RiskAsym 边际显著</strong>（p=0.049，10% 水平）；de / lsv 均不显著。</li>
      <li><strong>规范曲线（60 设定）显著比例大幅下调</strong>：DE 52/60、RiskAsym 43/60、LSV 34/60（原稿称 100%）。</li>
      <li><strong>L5 增量 R² 仅 0.0224</strong>（占 M4 R² 约 17%），非原稿的 0.0728（34.9%）。</li>
      <li><strong>中介效应仅 RA_RV、DE_RV 显著</strong>；LSV_RV 与全部 TO 路径均不显著。</li>
    </ul>
    <p><strong>权威 v3 来源</strong>：<code>merged_manuscript.html</code>（已全量刷新至 v3）、
    <code>_repro_all_OptionA_2026-08-15.json</code>、<code>_repro_M4_derived_2026-08-15.json</code>、
    <code>figures/spec_curve_summary.json</code>。本文档第 7 章（7.1–7.12）保留为 v20 研究方案历史快照，
    其具体数值以本表与下方各"v3 更正"框为准。</p>
  </div>

  <h2 style="color:#c0392b">零、v3 诚实重分析更正对照总表（核心实证主张逐条核对）</h2>
  <div class="table-wrap">
  <table>
  <tr><th>实证主张</th><th>v20-era 文档声明</th><th>v3 诚实重分析（权威值）</th><th>状态</th></tr>
  <tr><td>M4 核心模型 L5 系数</td><td>de t=−2.22** / lsv t=3.88*** / risk_asym t=5.49***（三指标全显著）</td><td>de β=−0.00606 t=−2.50** / lsv β=0.01548 t=1.23（<strong>不显著</strong>）/ risk_asym β=0.07311 t=4.53***</td><td><span class="tag tag-problem">LSV 不显著</span></td></tr>
  <tr><td>L5 增量 R²</td><td>ΔR²=0.0728（占 M4 R² 34.9%）</td><td>同样本 dR²_L5=0.0224（占 M4 R² 约 17%）；全样本 M3→M4 ΔR²=0.0352</td><td><span class="tag tag-problem">高估约 3 倍</span></td></tr>
  <tr><td>Oster δ（遗漏变量界）</td><td>δ=1.03(DE)/1.19(LSV)/2.25(RA) 均&gt;1 → 稳健</td><td>δ 全负：de −2.87 / lsv −2.66 / risk_asym −1.65 → 稳健性被推翻</td><td><span class="tag tag-problem">全部逆转</span></td></tr>
  <tr><td>IV / 2SLS 内生性</td><td>F&gt;240（LSV 262 / RA 243）确认内生性，IV 校正后效应增强</td><td>诚实面板下滞后一期 L5 工具变量交集塌缩（iv_N=0），IV/2SLS/Hausman 不可复现 → 一律作废</td><td><span class="tag tag-problem">方法作废</span></td></tr>
  <tr><td>WCB-S（Wild Cluster Bootstrap）</td><td>"全通过"（risk_asym/de/lsv 均一致显著）</td><td>WCB-S p：de 0.188 / lsv 0.343 / risk_asym 0.049（仅 RA 边际显著 10%）</td><td><span class="tag tag-problem">仅 RA 边际</span></td></tr>
  <tr><td>规范曲线（p-hacking 排除）</td><td>RiskAsym 36/36=100%、LSV/RA 7/7=100%、94.4%</td><td>60 设定：DE 52/60（86.7%）、RiskAsym 43/60（71.7%）、LSV 34/60（56.7%；前向显著为负）</td><td><span class="tag tag-problem">显著比例下调</span></td></tr>
  <tr><td>中介效应（传导机制）</td><td>RiskAsym→TO_calc→业绩 ind=+0.002 CI[0.001,0.003] 显著</td><td>LSV_RV ✗（CI 含 0）；RA_RV ✓**（ind=0.01585）、DE_RV ✓**（ind=−0.00157）；TO 三路径全 ✗</td><td><span class="tag tag-problem">仅 RA/DE→RV 显著</span></td></tr>
  <tr><td>统计功效</td><td>RiskAsym/LSV 100%、DE 64.8%</td><td>有效样本 N=2,264 / 348 基金；DE 在 M4 中 t=−2.50** 仍显著，LSV 不显著</td><td><span class="tag tag-problem">重新评估</span></td></tr>
  <tr><td>牛熊市子样本</td><td>RiskAsym 熊市强、DE 熊市负、LSV 牛市边际</td><td>BULL：de −2.36** / lsv n.s. / RA 4.08***；BEAR：de n.s. / lsv 2.32** / RA 3.74***</td><td><span class="tag tag-problem">方向部分反转</span></td></tr>
  <tr><td>非线性（倒U型）</td><td>RiskAsym 倒U 拐点 0.044</td><td>NONLIN：RA lin 0.0784(p=0.000) / quad −0.2324(p=0.071) 边际倒U；de/lsv 不显著</td><td><span class="tag tag-problem">降级为边际</span></td></tr>
  <tr><td>RESET 设定检验</td><td>M4 提示非线性 p=0.002</td><td>RESET F=1.819 p=0.1638 → 不拒绝线性设定</td><td><span class="tag tag-ok">线性未推翻</span></td></tr>
  <tr><td>面板规模</td><td>9,581 行 / 400 基金 / v20 面板</td><td>v3 主面板 9,974 行 / 400 基金；M4 诚实 N=2,264 / 348 基金</td><td><span class="tag tag-ok">口径更新</span></td></tr>
  </table>
  </div>
</section>
'''

anchor_header = "</header>\n\n<div class=\"container\">"
assert anchor_header in s, "header anchor not found"
reps.append((anchor_header, "</header>\n\n" + RECON + "\n<div class=\"container\">", "top-recon"))

# ---------------------------------------------------------------------------
# 1) meta 横幅：标记为 v20-era 快照
# ---------------------------------------------------------------------------
OLD_META = ('<div class="meta">生成日期：2026-08-08 | 面板v20（9,581行×154列，400基金，222经理）| '
            '7.12节v20面板核心实证：L5三指标首次全显著(RiskAsym***t=5.49/LSV***t=3.88/DE**t=-2.22) + '
            'L5增量R²=34.9% + IV 2SLS确认内生性(F>240) + WCB-S全通过 + Oster δ>1 + 规范曲线100% + '
            '十项高级计量全维度达标 | 学术严谨性7.7~7.12六节完整</div>')
NEW_META = ('<div class="meta" style="color:#c0392b">生成日期：2026-08-08（<strong>v20-era 快照，未更新至 v3</strong>）'
            ' | 面板v20（9,581行×154列，400基金，222经理）| '
            '⚠️ 下列"全显著/δ&gt;1/WCB-S全通过/IV F&gt;240/规范曲线100%/十项全达标"声明已被 v3 诚实重分析推翻，'
            '见顶部《v3 诚实重分析更正对照总表》。权威 v3 结果以 merged_manuscript.html 为准。</div>')
assert OLD_META in s, "meta not found"
reps.append((OLD_META, NEW_META, "meta"))

# ---------------------------------------------------------------------------
# 2) 变量字典修正：L3 表（TO_calc -> TO_wind，OCI 覆盖率 + 排除说明）
# ---------------------------------------------------------------------------
# SDI 覆盖率
OLD_SDI_COV = '<td>基金全持仓（跨期对比）</td><td>100%</td></tr>'
NEW_SDI_COV = '<td>基金全持仓（跨期对比）</td><td>63.8%（v3 主面板）</td></tr>'
assert OLD_SDI_COV in s, "SDI cov not found"
reps.append((OLD_SDI_COV, NEW_SDI_COV, "L3-SDI"))
# TO 行
OLD_TO = '<tr><td>换手率</td><td>TO_calc</td><td>min(买入额, 卖出额) / 平均资产</td><td>tushare基金换手率</td><td>100%</td></tr>'
NEW_TO = '<tr><td>换手率</td><td>TO_wind</td><td>Wind 单边换手率（原稿误记 TO_calc = min(买,卖)/平均资产）</td><td>Wind 基金换手率</td><td>86.6%（v3 主面板）</td></tr>'
assert OLD_TO in s, "TO row not found"
reps.append((OLD_TO, NEW_TO, "L3-TO"))
# OCI 行
OLD_OCI = '<tr><td>过度自信指数</td><td>OCI</td><td>OCI = (TO − TŌ) / σ(TO)</td><td>面板已有TO_calc</td><td>100%</td></tr>'
NEW_OCI = '<tr><td>过度自信指数</td><td>OCI</td><td>OCI = (TO − TŌ) / σ(TO)</td><td>面板已有 TO</td><td>18.0%（v3 主面板；<strong>诚实 M4 已排除 OCI</strong>，仅覆盖 18% 且为衍生指标）</td></tr>'
assert OLD_OCI in s, "OCI row not found"
reps.append((OLD_OCI, NEW_OCI, "L3-OCI"))

# VIF 表 TO_calc -> TO_wind
OLD_VIF = '<tr><td>TO_calc</td><td>1.10</td><td>L3</td><td><span class="tag tag-ok">安全</span></td></tr>'
NEW_VIF = '<tr><td>TO_wind</td><td>1.10</td><td>L3</td><td><span class="tag tag-ok">安全</span></td></tr>'
assert OLD_VIF in s, "VIF TO_calc not found"
reps.append((OLD_VIF, NEW_VIF, "VIF"))

# ---------------------------------------------------------------------------
# 3) 就地更正框（方法学红线）
# ---------------------------------------------------------------------------
CALL_IV = ('<div class="callout danger"><p><strong>⚠️ v3 更正（IV / 2SLS）</strong>：诚实面板下滞后一期 L5 工具变量'
           '与当期收益的交集样本塌缩（iv_N=0），2SLS / Hausman 估计不可复现，<strong>本节 IV 结论一律作废</strong>。'
           '原稿"F&gt;240 确认内生性、IV 校正后效应增强 2–4 倍"为 v20 口径，不应作为 v3 实证依据。</p></div>')
a = '本研究三个L5指标的Hausman检验均显著(p < 0.05)，确认OLS向下偏倚——IV校正后效应增强2-4倍。</p>'
assert a in s, "IV anchor not found"
reps.append((a, a + CALL_IV, "iv"))

CALL_WCB = ('<div class="callout danger"><p><strong>⚠️ v3 更正（WCB-S）</strong>：v3 诚实 M4 下 WCB-S p 值：'
            'de=0.188 / lsv=0.343 / risk_asym=0.049（仅 RA 在 10% 水平边际显著）。原稿"聚类数=297、WCB-S 全通过"'
            '为 v20 口径，且 v3 聚类数为 348（非 297）。</p></div>')
a = 'WCB-S作为额外稳健性检验，进一步确认了推断的可靠性。</p>'
assert a in s, "WCB anchor not found"
reps.append((a, a + CALL_WCB, "wcb"))

CALL_OSTER = ('<div class="callout danger"><p><strong>⚠️ v3 更正（Oster δ）</strong>：v3 诚实重分析下三指标 δ '
             '<strong>全部为负</strong>：de=−2.87 / lsv=−2.66 / risk_asym=−1.65，不满足 δ&gt;1 基准，'
             '原"稳健"结论被推翻。原稿 δ=1.03/1.19/2.25 为 v20 口径。</p></div>')
a = '本研究中三个L5指标的δ分别为1.03(DE)、1.19(LSV)和2.25(RiskAsym)，均超过阈值1'
assert a in s, "Oster anchor not found"
reps.append((a, a + CALL_OSTER, "oster"))

CALL_SPEC = ('<div class="callout danger"><p><strong>⚠️ v3 更正（规范曲线）</strong>：v3 真实面板（60 设定）下显著比例为 '
             'DE 52/60（86.7%）、RiskAsym 43/60（71.7%）、LSV 34/60（56.7%；且前向 1 季度显著为负，方向跨家族不稳定）。'
             '原稿"7/7=100%、94.4%"基于模拟/ v20 口径，已不可信。</p></div>')
a = 'RiskAsym和LSV在7/7(100%)设定下均***显著且方向一致——彻底排除p-hacking。</p>'
assert a in s, "spec anchor not found"
reps.append((a, a + CALL_SPEC, "spec6a10"))

CALL_MED = ('<div class="callout danger"><p><strong>⚠️ v3 更正（中介效应）</strong>：v3 诚实重分析下，'
            'LSV→return_volatility 间接效应不显著（CI 含 0）；仅 RiskAsym→RV（ind=0.01585, p=0.012）与 '
            'DE→RV（ind=−0.00157, p=0.008）显著；三条 TO 路径（LSV/RA/DE→TO→业绩）<strong>全部不显著</strong>。'
            '原稿"RiskAsym→TO_calc→业绩 ind=+0.002"为 v20 口径。</p></div>')
a = '确认RiskAsym部分通过影响交易频率来影响业绩。这揭示了'
assert a in s, "med anchor not found"
reps.append((a, a + CALL_MED, "med"))

CALL_RESET = ('<div class="callout danger"><p><strong>⚠️ v3 更正（RESET / 非线性）</strong>：v3 诚实 M4 下 '
              'RESET F=1.819（p=0.1638），<strong>不拒绝线性设定</strong>；RiskAsym 二次项仅边际（p=0.071），'
              '倒U 型由"显著"降级为"边际"。原稿"M4 提示非线性 p=0.002、倒U β²=−0.41 p&lt;0.001"为 v20 口径。</p></div>')
a = '后续非线性检验确认RiskAsym存在倒U型效应(β²=−0.41, p<0.001)——RESET检验成功识别了这一非线性，指导在模型中加入二次项。</p>'
assert a in s, "reset anchor not found"
reps.append((a, a + CALL_RESET, "reset"))

CALL_712 = ('<div class="callout danger"><p><strong>⚠️ v3 更正（7.12 核心实证）</strong>：本节为 v20 面板结果。'
            'v3 诚实 M4（N=2,264 / 348 基金）下三指标<strong>并未全显著</strong>：de β=−0.00606 t=−2.50**（**）、'
            'lsv β=0.01548 t=1.23（<strong>不显著</strong>）、risk_asym β=0.07311 t=4.53***；'
            'L5 增量 R² 仅 0.0224（非 0.0728 / 34.9%）。"三指标首次全显著"为 v20 口径，已被推翻。</p></div>')
a = '<h2>7.12 v20面板核心实证：三指标全显著 + 十项高级计量验证</h2>'
assert a in s, "712 anchor not found"
reps.append((a, a + CALL_712, "s712"))

CALL_798 = ('<div class="callout danger"><p><strong>⚠️ v3 更正（规范曲线 / 7.9.8）</strong>：v3 真实面板（60 设定）下 '
            'RiskAsym 显著 43/60（71.7%）、方向一致 76.7%；非原稿"94.4% / 100%"。LSV 仅 34/60（56.7%），'
            '前向 1 季度显著为负。原稿 36 种设定的计数基于模拟/ v20 口径。</p></div>')
a = '<h4>7.9.8 规范曲线分析 (Specification Curve Analysis)</h4>'
assert a in s, "798 anchor not found"
reps.append((a, a + CALL_798, "s798"))

CALL_715 = ('<div class="callout danger"><p><strong>⚠️ v3 更正（Oster / 7.11.5）</strong>：v3 诚实重分析下 δ 全部为负 '
            '（de −2.87 / lsv −2.66 / risk_asym −1.65），不满足 δ&gt;1，原"极度稳健（δ=41.84）"结论被推翻。'
            '原稿 δ=41.84 基于 v20 面板与错误的 R²_max 假设。</p></div>')
a = '<h4>7.11.5 Oster (2019) 遗漏变量偏差界</h4>'
assert a in s, "715 anchor not found"
reps.append((a, a + CALL_715, "s715"))

# ---------------------------------------------------------------------------
# 执行
# ---------------------------------------------------------------------------
miss = []
for old, new, tag in reps:
    c = s.count(old)
    if c == 0:
        miss.append(tag)
    elif c > 1:
        miss.append(tag + "(dup=%d)" % c)
    else:
        s = s.replace(old, new, 1)

print("replacements applied:", len(reps) - len(miss))
print("MISSING/BAD:", miss if miss else "none")

# 残留陈旧 token 校验
stale = ["F>240", "Oster δ>1", "δ=41.84", "94.4%", "7/7(100%)", "十项高级计量全维度达标",
         "WCB-S全通过", "L5三指标首次全显著", "TO_calc", "增量R²=0.0728", "ΔR²=0.0728"]
print("\n--- residual stale token check (should only appear inside v3更正 boxes / 对照表 as historical quotes) ---")
for tk in stale:
    n = s.count(tk)
    if n:
        print(f"  {tk}: {n}")

open(SRC, 'w', encoding='utf-8').write(s)
print("\nwritten. new size:", len(s))
