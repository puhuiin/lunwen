# -*- coding: utf-8 -*-
import io
path = "实证结果完整报告与论文写作指南.html"
html = io.open(path, encoding="utf-8").read()

# ---------- REQ 1: augment school conclusion sentence with tier result ----------
a1='结论：school <b>无稳健解释力</b>，原"不进主模型、作覆盖受限背景控制"的决定正确。'
b1='结论：school <b>无稳健解释力</b>；进一步按<b>院校层次（C9/985/211/海外）</b>重跑——清洗 91 个脏值（"北京大学管理科学"→北京大学等）并归一后，N=226（OLS+HC1），四个层次哑变量<b>全部不显著</b>（|t|≤0.16，p≥0.875），描述性各层均值 ff5_adj 极差仅约 0.5pp，原"不进主模型、作覆盖受限背景控制"的决定正确。'
if html.count(a1)==1:
    html=html.replace(a1,b1,1); print("OK   [req1] school tier sentence added")
else:
    print("WARN [req1] count=%d"%html.count(a1))

# ---------- REQ 2: insert HC robust SE box before S1 ----------
hc_box = '''
<div class="box ctrl">
<b>稳健标准误（HC）：为什么"修正异方差"、怎么算（流程与原理）</b>
<ul>
<li><b>问题从哪来</b>：OLS 标准误默认<b>同方差</b>（Var(ε_i)=σ²），公式 Var(β̂)=σ²(X'X)⁻¹ 只在同方差下成立。金融面板必<b>异方差</b>（大/小基金残差波动天差地别），此时 OLS 系数仍无偏，但 SE <b>系统性偏小</b> → t 虚高 → 把噪声当显著。这就是"修正异方差的稳健标准误"要解决的问题。</li>
<li><b>三明治（sandwich）估计量</b>：真实 Var(β̂)=(X'X)⁻¹ X'ΩX (X'X)⁻¹，Ω=diag(σ_i²) 非恒定。用残差平方估计 Ω̂=diag(û_i²)，协方差写成"面包−肉−面包"：bread=(X'X)⁻¹、meat=X'Ω̂X、再 bread → 故称 sandwich。SE=√(对角线)。</li>
<li><b>HC0→HC3（截面用 HC1）</b>：HC0=û_i²；<b>HC1=HC0×n/(n−k)</b>（小样本修正，本项目 R1–R5 默认）；HC2=û_i²/(1−h_ii)（杠杆降权）；HC3=û_i²/(1−h_ii)²（更狠降权，有强影响点时用）。</li>
<li><b>计算流程</b>：① OLS 得 β̂、û；② 算 û_i² 组 Ω̂；③ meat=X'Ω̂X；④ Û=(X'X)⁻¹·meat·(X'X)⁻¹；⑤ SE=√(diag)，t=β̂/SE 判星。</li>
<li><b>HC 不是万能：面板用"聚类稳健"而非 HC</b>。HC 只修正截面异方差，改不了"同一基金多季度残差相关"。本项目<b>面板（R6 组内FE、前向）一律用基金聚类稳健 SE</b>（meat=Σ_g X_g'û_gû_g'X_g）。一句话：<b>截面 HC1，面板基金聚类</b>。</li>
</ul>
</div>
'''
anchor_s1='\n<!-- ============ S1 ============ -->'
assert html.count(anchor_s1)==1, "s1 count=%d"%html.count(anchor_s1)
html=html.replace(anchor_s1,'\n'+hc_box+anchor_s1,1)
print("OK   [req2] HC box inserted")

# ---------- REQ 3: insert literature box after L1 key conclusion ----------
lit_box = '''
<div class="box note">
<b>文献对话：人力资本假说（Golec 1996；Niessen &amp; Ruenzi 2007）与本文 L1 的异同</b>
<ul>
<li><b>Golec (1996, 美国 1988–1990)</b>：更年轻、持 MBA、任期更长的经理带来更高风险调整收益；<b>任期影响最大</b>。→ "教育/经验→业绩"最强支持。</li>
<li><b>Niessen &amp; Ruenzi (2007, 美国, 13,547 年-观测/3,333 只基金)</b>：女性经理更风险厌恶、交易更少（更少过度自信）；<b>男女业绩无差异</b>；但女性基金获 <b>约 17–18% 更低资金净流入</b>（刻板印象）。→ 关键是"无业绩差 + 有资金歧视"。</li>
<li><b>Chevalier &amp; Ellison (1999)</b>：大学质量（SAT/选拔度）预测收益，但 <b>MBA 效应弱且不显著</b>。→ 已提示"学历≠能力"。</li>
<li><b>本文 L1</b>：任期 ns、性别 ns、CFA 显著为负（选择偏差）、院校层次（见上）全部 ns → 个人信息单看都不驱动业绩。</li>
<li><b>为什么和 Golec 不一样（猜测）</b>：① 样本时代——Golec 早期美国技能离散大，本文 2018–2025 A 股经理高度职业化、<b>资质变异被压缩</b>；② 中国反向关系——Xu &amp; Li (2005) 中国经理年龄/任期与业绩<b>负相关</b>，本文 log_fund_age 显著为负，与之吻合；③ 样本基金成熟、任期跨度窄。</li>
<li><b>一致处</b>：与 Chevalier&Ellison 一致（MBA 弱）、与 Niessen&Ruenzi 一致（性别无业绩差）；CFA 负向中国自我选择，与"资质≠能力"自洽。→ 本文把 L1 降为控制变量，与现代文献细微结论自洽。</li>
</ul>
</div>
'''
anchor_lit='进一步印证"控制而非驱动"的角色。\n</div>\n'
assert html.count(anchor_lit)>=1, "lit anchor count=%d"%html.count(anchor_lit)
first=html.find(anchor_lit)
html=html[:first+len(anchor_lit)]+'\n'+lit_box+'\n'+html[first+len(anchor_lit):]
print("OK   [req3] literature box inserted")

# ---------- REQ 4: insert holdings-turnover box after L3 key conclusion ----------
hold_box = '''
<div class="box note">
<b>用持仓快照算"换手率"对比相邻两期（用户：能不能用持仓快照做换手）</b>
<ul>
<li><b>做法</b>：turnover_t = ½·Σ|w_t − w_{t−1}|（w=个股持仓占比，期内归一化），不依赖双边交易额。</li>
<li><b>两种相邻</b>：① <b>连续可用快照</b>：342 只基金，ff5 ~ hold_turnover+log_aum+log_fund_age（HC1）β=<b>−0.0059 (t=−0.65) ns</b>，N=331，R²=0.083；② <b>严格季度相邻</b>：142 只，β=<b>−0.0493 (t=−3.12)***</b>，N=131，R²=0.106。</li>
<li><b>读</b>：严格季度口径下组合换手越高 alpha 越低（***），与"频繁调仓侵蚀业绩"一致；连续口径因半年度披露间隔被平滑而不显著。方向均负。</li>
<li><b>扩覆盖？</b> 持仓快照覆盖 342 只，但<b>交集=200</b>（交易 TO 基金全在快照里），无净增新基金；corr(持仓换手, TO)=<b>0.125</b>（弱）→ 两概念不同。定位：trade-based TO 的<b>互补视角</b>，非替代，仍受快照覆盖上限约束。</li>
</ul>
</div>
'''
anchor_hold='提示交易选择性在控制基金固定效应后更有解释力。\n</div>\n'
assert html.count(anchor_hold)>=1, "hold anchor count=%d"%html.count(anchor_hold)
first=html.find(anchor_hold)
html=html[:first+len(anchor_hold)]+'\n'+hold_box+'\n'+html[first+len(anchor_hold):]
print("OK   [req4] holdings-turnover box inserted")

# ---------- REQ 5: insert archetype synthesis box in chapter 5 ----------
arch_box = '''
<div class="box key">
<b>经理画像原型（论文"结论"章可直接落地的四类可识别经理）</b>
<p>沿"强能力轴 vs 弱/负向轴"做有经济含义的类型划分（非聚类），便于经理评价与筛选：</p>
<ul>
<li><b>① 风控择股型（赢家）</b>：L4 ARG/RG 双证据强正、ICI 正 → 敢下注且押对，首选目标。</li>
<li><b>② 行业集中下注型</b>：ICI 高、AS 低（负**）→ 赢在"行业方向"而非"偏离量"，中国语境"主动份额折价、行业偏离溢价"。</li>
<li><b>③ 低偏误纪律型</b>：de 稳定负、risk_asym/lsv 受控 → 不追涨杀跌、不死扛亏损，稳定偏分型控制。</li>
<li><b>④ 高换手噪声型（输家）</b>：换手高、严格季度口径换手越高 alpha 越低（***）→ 频繁调仓侵蚀业绩，应规避。</li>
</ul>
<b>统一结论</b>：L1 背景（院校/任期/性别/CFA）在四类原型中均"中立"——画像是关于<b>行为微观结构</b>而非人口学；筛选应锚定 L4/L5/L2 行为轴。
</div>
'''
anchor_arch='讨论画像如何用于经理评价/筛选（基于 fut4q 预测力）。</li>\n</ul>\n'
assert html.count(anchor_arch)>=1, "arch anchor count=%d"%html.count(anchor_arch)
first=html.find(anchor_arch)
html=html[:first+len(anchor_arch)]+'\n'+arch_box+'\n'+html[first+len(anchor_arch):]
print("OK   [req5] archetype synthesis box inserted")

io.open(path,"w",encoding="utf-8").write(html)
print("\n=== 报告 HTML written, length=%d ==="%len(html))
