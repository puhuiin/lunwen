# Apply edits to the literature-review HTML:
#  - Replace the six-dim radar figure with a redesigned, rigor-audited version
#  - Replace the misplaced dual-mode slider with a static "case x v4" matrix
#  - Remove the orphaned toggle <script>

import re

SRC = r"D:\Desktop\基金经理行为分析研究\文献综述与案例_投资经理行为指标_2026-08-16.html"
with open(SRC, encoding="utf-8") as f:
    html = f.read()

with open(r"D:\Desktop\基金经理行为分析研究\_radar_svg.txt", encoding="utf-8") as f:
    radar_svg = f.read().strip()

# ---------- NEW RADAR FIGURE ----------
NEW_FIGURE = '''<div class="figure">
<h4 id="profileviz" style="margin:22px 0 6px">图　六位经理的序数行为画像（六维雷达，1=低 → 5=极高）</h4>
<div class="viz-legend">
  <span class="lg"><span class="sw" style="background:#2e7d8a"></span>张坤</span>
  <span class="lg"><span class="sw" style="background:#1f6b3a"></span>朱少醒</span>
  <span class="lg"><span class="sw" style="background:#9a3412"></span>葛兰</span>
  <span class="lg"><span class="sw" style="background:#7c3aed"></span>蔡嵩松</span>
  <span class="lg"><span class="sw" style="background:#1f4e79"></span>巴菲特</span>
  <span class="lg"><span class="sw" style="background:#be123c"></span>林奇</span>
</div>
''' + radar_svg + '''
<p class="sub" style="font-size:12.5px;margin-top:6px"><strong>维度重设计（严谨性审计，#268）：</strong>原"集中度（前十大占比）"与"行业聚焦（单一行业偏离度）"高度共线——二者同属"集中程度"家族，几何上近似同向，会虚增雷达面积并误导"多维度"观感。现以<strong>主动份额 AS</strong>（组合相对基准的整体偏离度，Cremers &amp; Petajisto 2009 的规范度量）替换冗余的"行业聚焦"，使六个轴分属三个互斥家族：</p>
<ul class="sub" style="font-size:12.5px;margin:4px 0 0;color:#5b6b7b">
  <li><b>偏离/集中家族</b>（构造相关，须同读）：① 集中度=个股前十大占比；② 行业偏离=单一行业权重偏离（ICI）；③ 主动份额 AS=相对基准的整体偏离。三者刻画"多集中/多主动"的不同切面，AS 最具规范性。</li>
  <li><b>交易活跃度家族</b>（互补维度）：④ 换手率=年买卖频率；⑤ 持股周期=平均持有年限（与换手率近逆，但保留以显式呈现"耐心"）。</li>
  <li><b>独立维度</b>：⑥ 风险偏好=对高波动/回撤的承受度。</li>
</ul>
<p class="sub" style="font-size:12.5px;margin-top:6px"><strong>刻度与边界：</strong>1=低 / 2=中低 / 3=中 / 4=中高 / 5=极高，为基于已核验公开披露（季报前十大、行业分布、定期报告换手区间、任职年限与公开访谈）的<strong>序数定性映射，非精确度量</strong>，故雷达仅用于直观比较"行为形状"而非量化大小。<strong>L5 认知偏差（DE/LSV/RiskAsym）因公开数据不可算，未纳入雷达</strong>，其刻画边界见评分卡与方法学声明。各经理取值与案例正文一致（如巴菲特极端 AS+极低换手+极长持有→"集中恒久"型；林奇低 AS+高换手+短持有→"广度采样"型）。</p>
</div>'''

# ---------- STATIC MATRIX (replaces misplaced slider) ----------
STATIC_MATRIX = '''<h3 id="coefbridge">案例经理 × v4 显著层 对照矩阵（静态桥接）</h3>
<p>下表把上方案例画像与本项目 v4 实证（双向聚类基准，详见 <code>基金经理能力画像与业绩评价.html</code> §7.1）显式桥接：每一行标明该经理的 L1–L5 行为特征，以及这些行为在本项目实证中<strong>显著（***/**）的层</strong>——这正是"行为画像 → 绩效信号"的落点。L4 的 ARG / return_volatility / RG 精确值需面板实测，故以公开长期回报作结果锚；<span class="badge-fe">⚡组内FE</span> 表示组内固定效应下同样显著（双证据最可信）。本表为定性桥接，<strong>不构成对单只基金的因果推断</strong>。</p>
<div class="panel-manager">
<table class="mm-table">
  <tr><th>经理</th><th>L1 背景</th><th>L2 持仓</th><th>L3 交易</th><th>L4 风险调整绩效</th><th>L5 认知偏差</th><th>与 v4 显著层</th></tr>
  <tr><td><b>张坤</b></td><td>14年+，"公募一哥"</td><td>高AS(历史85%→近期39%)·高ICI(消费+港股+能源)</td><td>低-中换手·超长持有</td><td>高波动深回撤(ARG等需实测)</td><td>DE低·LSV低</td><td><span class="grade-a">L4</span> 低换手→return_vol/RG/ARG 正向</td></tr>
  <tr><td><b>朱少醒</b></td><td>20年+，仅管1只</td><td>高AS·行业均衡(低ICI)</td><td>极低换手·超长持有</td><td>年化~15–16%(ARG需实测)</td><td>DE低·分散</td><td><span class="grade-a">L4</span>+<span class="grade-a">L2</span> ICI正向</td></tr>
  <tr><td><b>葛兰</b></td><td>医药主题</td><td>高AS·极端ICI(单一医药)</td><td>中高换手·行业零漂移</td><td>连续跑输基准(高Beta)</td><td>行业Beta主导</td><td><span class="grade-a">L2</span> ICI正向(但全押→高Beta回撤)</td></tr>
  <tr><td><b>蔡嵩松</b></td><td>芯片博士</td><td>高AS·极致ICI(半导体)</td><td>历史极高换手</td><td>高波动深回撤(2022~50%)</td><td>高LSV·高RiskAsym</td><td><span class="grade-a">L4</span> return_vol正向 + <span class="grade-c">L3</span>组内FE(双刃)</td></tr>
  <tr><td><b>巴菲特</b></td><td>60年</td><td>极端AS(5只67%)·中ICI</td><td>极低换手·恒久</td><td>年化19.9%</td><td>DE极低</td><td><span class="grade-a">L4</span> 全面正向 + <span class="grade-a">L2</span> ICI正向（原型）</td></tr>
  <tr><td><b>林奇</b></td><td>13年</td><td>低AS(~1000只)·低ICI</td><td>高换手</td><td>年化29.2%</td><td>分散稀释</td><td><span class="grade-a">L4</span> return_vol正向(高换手→高波动)</td></tr>
</table>
</div>'''

# ---- 1. replace radar figure ----
idx_a = html.index('<div class="figure">\n<h4 id="profileviz"')
idx_b = html.index('<h3 id="scorecard">')
assert idx_a < idx_b, "radar figure anchors out of order"
html = html[:idx_a] + NEW_FIGURE + "\n" + html[idx_b:]

# ---- 2. replace misplaced slider with static matrix ----
idx_c = html.index('<h3 id="coefmode">')
idx_d = html.index('<h3 id="caveat">')
assert idx_c < idx_d, "slider anchors out of order"
html = html[:idx_c] + STATIC_MATRIX + "\n" + html[idx_d:]

# ---- 3. remove orphaned toggle script ----
idx_e = html.index('<script>')
idx_f = html.index('</script>', idx_e) + len('</script>')
html = html[:idx_e] + html[idx_f+1:]

with open(SRC, "w", encoding="utf-8") as f:
    f.write(html)

# ---- validate ----
checks = {
    "coefmode_removed": "id=\"coefmode\"" not in html,
    "modeToggle_removed": "modeToggle" not in html,
    "coef-view_removed": "coef-view" not in html,
    "script_removed": "<script>" not in html,
    "new_radar_AS_axis": "主动份额" in html,
    "行业聚焦_gone": "行业聚焦" not in html,
    "static_matrix_kept": "coefbridge" in html,
    "profileviz_kept": "id=\"profileviz\"" in html,
}
print("CHECKS:", checks)
opens = len(re.findall(r'<div(?:\s|>)', html))
closes = len(re.findall(r'</div>', html))
print("div open/close:", opens, closes, "diff", opens-closes)
for tag in ["h2","h3","h4","svg","style","body","html"]:
    o=len(re.findall(r'<%s(?:\s|>)'%tag, html)); c=len(re.findall(r'</%s>'%tag, html))
    print(f"  {tag}: {o}/{c} diff {o-c}")
