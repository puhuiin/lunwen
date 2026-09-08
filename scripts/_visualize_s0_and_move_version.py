# -*- coding: utf-8 -*-
"""可视化 §0 + 把版本/数据来源说明从 header 移到结尾附录。"""
import re, os

PATH = '实证总结报告_文献综述回归解读与SDI诊断_2026-08-19.html'
html = open(PATH, encoding='utf-8').read()
orig_len = len(html)

# ============ 1. 新增 CSS（流程图 + 结论卡片网格）============
NEW_CSS = """
.flow5{display:flex;flex-wrap:wrap;align-items:stretch;gap:0;margin:16px 0}
.flow5 .flayer{flex:1 1 150px;min-width:138px;background:#fff;border:1px solid #e5e7eb;border-radius:10px;padding:12px 10px;text-align:center}
.flow5 .arrow{display:flex;align-items:center;justify-content:center;color:#94a3b8;font-size:20px;font-weight:800;flex:0 0 16px}
.flow5 .fno{font-size:13px;font-weight:800;color:#1e3a8a}
.flow5 .ft{font-size:15px;font-weight:700;margin:2px 0}
.flow5 .fs{font-size:12px;color:#6b7280;margin-bottom:8px}
.flow5 .badge{display:inline-block;font-size:11.5px;font-weight:700;padding:3px 8px;border-radius:20px;white-space:nowrap}
.flow5 .badge.sig{background:#dcfce7;color:#14532d}
.flow5 .badge.ns{background:#f1f5f9;color:#64748b}
.concl-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:12px;margin:10px 0}
.concl-grid .ccard{background:#fff;border:1px solid #e5e7eb;border-left:4px solid #1d4ed8;border-radius:8px;padding:12px 14px}
.concl-grid .cnum{font-size:13px;font-weight:800;color:#1d4ed8}
.concl-grid .ct{font-weight:700;margin:2px 0 6px;font-size:14.5px;line-height:1.4}
.concl-grid .cb{font-size:12.5px;color:#374151;line-height:1.65}
"""
assert '</style>' in html
html = html.replace('</style>', NEW_CSS + '</style>', 1)

# ============ 2. Header：移除版本/数据来源三行（保留封面信息）============
HEADER_OLD = ('''权威数值源：<code>_v4_benchmark.json</code>（M4 双向聚类 v4 基准）· <code>L3_L1_regression_HONEST_TOWind_2026-08-15.json</code>（H1–H5）· 主文稿 §4.2–§4.4 · 面板实测（2026-08-19）<br>
生成日期：2026-08-19 · 由 <code>_gen_summary_report_2026-08-19.py</code> 可复现生成<br>深度优化版（2026-08-19 晚）：新增 §0 导师导览 · §1.1 框架一览与 §1.2 M0–M4 详解 · §2 完整文献综述重写（叙事型，数值全部对齐 v4 基准）
</div>''')
assert HEADER_OLD in html, 'header version block not found'
html = html.replace(HEADER_OLD, '</div>', 1)

# ============ 3. §0：在研究问题盒后插入"五层框架一览"递进图 ============
FLOW = '''
<h3>▍五层框架一览（从"谁在管"到"为何决策"）</h3>
<div class="flow5">
  <div class="flayer"><div class="fno">L1</div><div class="ft">经理背景</div><div class="fs">谁在管</div><div class="badge ns">基本不显著</div></div>
  <div class="arrow">→</div>
  <div class="flayer"><div class="fno">L2</div><div class="ft">持仓决策</div><div class="fs">持什么</div><div class="badge sig">ICI*** · AS**</div></div>
  <div class="arrow">→</div>
  <div class="flayer"><div class="fno">L3</div><div class="ft">交易执行</div><div class="fs">怎么交易</div><div class="badge ns">全部不显著</div></div>
  <div class="arrow">→</div>
  <div class="flayer"><div class="fno">L4</div><div class="ft">风险管理</div><div class="fs">管什么风险</div><div class="badge sig">ARG**</div></div>
  <div class="arrow">→</div>
  <div class="flayer" style="border-left:4px solid #dc2626"><div class="fno">L5</div><div class="ft">认知偏差</div><div class="fs">为何决策</div><div class="badge sig">RA*** · DE***</div></div>
</div>
<p class="muted" style="margin-top:6px">箭头表示 M0→M4 的<b>嵌套递进</b>：每一层在控制前序所有层之后加入，单独检验该层的增量解释力。绿色＝该层有显著信号，灰色＝该层在主模型中基本无独立信号。最右 L5 是本研究的理论增量核心层。</p>
'''
RESEARCH_BOX_OPEN = '''<div class="box key">
<p><b>研究问题：</b>在控制经理背景（L1）、持仓决策（L2）、交易执行（L3）、风险管理（L4）等全部可观测行为后，认知偏差（L5：处置效应 DE / 羊群 LSV / 风险不对称 RA）是否仍独立解释基金业绩？</p>
</div>'''
assert RESEARCH_BOX_OPEN in html, 'research question box not found'
html = html.replace(RESEARCH_BOX_OPEN, RESEARCH_BOX_OPEN + FLOW, 1)

# ============ 4. §0：五句话结论 由 5 段长文 → 卡片网格 ============
NEW_CONCL = '''<div class="box">
<h3>▍五句话看懂结论（一眼扫完）</h3>
<div class="concl-grid">
  <div class="ccard"><div class="cnum">①</div><div class="ct">认知偏差有独立信息，但量级有限</div><div class="cb">控制全部可观测行为后 L5 仍显著（RA***、DE***），同样本增量 R²≈2.2pp；不是冗余代理，也非业绩主导因素。</div></div>
  <div class="ccard"><div class="cnum">②</div><div class="ct">三重识别给出三种证据性质</div><div class="cb">截面 RA 强；前向预测 RA/DE 显著；组内 FE 仅 DE 稳健（t=−3.64***）。RA/LSV 是"分型变量"，DE 是"行为效应"。</div></div>
  <div class="ccard"><div class="cnum">③</div><div class="ct">中国语境两条反向发现</div><div class="cb">主动份额 AS 显著负、行业偏离 ICI 显著正——"主动的方向说了算，主动的量反而拖累"（与美股相反）；机构反向处置、果断止损。</div></div>
  <div class="ccard"><div class="cnum">④</div><div class="ct">不显著 ≠ 无信息</div><div class="cb">SDI/TO/HHI/RV/LSV 的不显著各有明确机制（构念正交、共线吸收、覆盖率、通道 vs 信号）；SDI 失效恰证 FF5 剥离风格择时（§6）。</div></div>
  <div class="ccard"><div class="cnum">⑤</div><div class="ct">诚实边界</div><div class="cb">Oster δ 全负（遗漏变量稳健性不成立）；IV 不可复现（作废）；LSV 选择敏感；DE 外推限 ~46.6% 子群。全部为预测关联非因果。</div></div>
</div>
<p class="muted" style="margin-top:8px">五句话的实证支撑与机制详见 §4（主结果）、§5（稳健性）、§6（SDI 专题）、§7（不显著机制）、§8（证据分级）。</p>
</div>'''
pattern = re.compile(r'<div class="box">\s*<p><b>五句话结论：</b></p>.*?</div>', re.S)
m = pattern.search(html)
assert m, '五句话结论 box not found'
html = pattern.sub(NEW_CONCL, html, count=1)

# ============ 5. 结尾新增附录：版本与数据来源说明 ============
APPENDIX = '''
<h2 id="s11">附录 · 版本与数据来源说明</h2>
<div class="box info">
<p><b>数据来源与权威数值源：</b><code>_v4_benchmark.json</code>（M4 双向聚类 v4 基准）· <code>L3_L1_regression_HONEST_TOWind_2026-08-15.json</code>（H1–H5）· 主文稿 §4.2–§4.4（v4 刷新版）· 主分析面板_重建_含TOwind.csv（2026-08-19 实测）。</p>
<p><b>生成与可复现：</b>本报告由 <code>_gen_summary_report_2026-08-19.py</code> 生成；底层数值由 <code>run_full.py</code> 一键复现，2026-08-19 全流水线重跑与 v4 基准逐字段差 = 0（见《出稿终值验证报告_2026-08-19.html》）。</p>
<p><b>版本与修订记录：</b></p>
<p>· <b>基础版（2026-08-19 日）：</b>首次生成总结性报告（§0–§10 全结构）。</p>
<p>· <b>深度优化版（2026-08-19 晚）：</b>新增 §0 导师导览 · §1.1 框架一览与 §1.2 M0–M4 详解 · §2 完整文献综述重写（叙事型，数值全部对齐 v4 基准）。</p>
<p>· <b>2026-08-20（上）：</b>新增 §1.4 五层自变量全景（每层自变量清单 + 显著性 + 特色指标与显著信号）。</p>
<p>· <b>2026-08-20（下）：</b>删除"§0 给导师的三分钟导览"小标题；将本版本/数据来源说明由报告开头移至本附录（结尾）；§0 摘要改为可视化——新增"五层框架一览"递进图，并将"五句话结论"由长文改为卡片网格。</p>
</div>
'''
# 插入到 .footnote 之后、</div> 之前
FOOTNOTE_CLOSE = '</p>\n\n</div>'
assert FOOTNOTE_CLOSE in html, 'footnote close not found'
html = html.replace(FOOTNOTE_CLOSE, '</p>\n' + APPENDIX + '\n</div>', 1)

# ============ 6. TOC 增加附录入口 ============
TOC_OLD = '<a href="#s10">§10 总结与边界</a>\n</div>'
assert TOC_OLD in html, 'toc s10 anchor not found'
html = html.replace(TOC_OLD, '<a href="#s10">§10 总结与边界</a>\n<a href="#s11">附录 · 版本与数据来源说明</a>\n</div>', 1)

open(PATH, 'w', encoding='utf-8').write(html)

# ============ 校验 ============
probs = []
for tag in ['div','table','thead','tbody','tr','td','th','h2','h3','p','span','b','style','header']:
    o = len(re.findall(r'<%s(\s|>)' % tag, html)); c = len(re.findall(r'</%s>' % tag, html))
    if o != c: probs.append('%s %d/%d' % (tag, o, c))
print('size: %d -> %d' % (orig_len, len(html)))
print('tag balance:', 'PASS' if not probs else probs)
print('header version removed:', '深度优化版' not in html[:html.find('</header>')])
print('appendix present:', 'id="s11"' in html)
print('framework diagram present:', 'flow5' in html)
print('concl grid present:', 'concl-grid' in html)
print('五句话长文 removed:', '五句话结论：' not in html)
