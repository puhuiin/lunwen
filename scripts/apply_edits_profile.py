# -*- coding: utf-8 -*-
import io
path = "基金经理能力画像与业绩评价.html"
html = io.open(path, encoding="utf-8").read()

def rep(anchor_old, new, label, count=1):
    c = html.count(anchor_old)
    if c != count:
        print("WARN [%s] anchor count=%d (expected %d)" % (label, c, count))
        # show context
        idx = html.find(anchor_old)
        print("  ctx:", repr(html[idx-40:idx+80]) if idx>=0 else "NOT FOUND")
    else:
        html.replace(anchor_old, new, 1) if count==1 else None
        # do single replacement
        html_local = html
        html = html_local.replace(anchor_old, new, 1)
        print("OK   [%s]" % label)

# ---------- REQ 1: replace box ⑥ (school tier) ----------
box6_new = '''<div class="box note">
<b>⑥ 毕业院校(school)按"院校层次"重跑（用户：按层次划分试一下，QS 亦可）</b>
<ul>
<li><b>清洗与分层规则</b>：原始 school 是脏文本（91 个唯一值，混入"北京大学管理科学""北京大学微电子学""浙江大学电子科学"等院系名，以及"美国伊利诺伊理工大学"等海外校）。先用<b>子串匹配归一</b>到规范校名（如"北京大学管理科学"→北京大学），再按网上公开层次划分：<b>C9</b>（清北复交南浙科哈西交 9 所）→ <b>985</b>（其余 30 所，共 39）→ <b>211</b>（含 985 外的部属/省属重点，约 115）→ <b>海外</b>（中外合办/港澳及明确国别标记）→ <b>其他国内普通院校</b>。school 是<b>基金层面固定属性</b>，故每只基金压成 1 条观测、取 ff5_adj 基金均值，N=<b>226</b>（覆盖非空院校基金）。</li>
<li><b>分层分布</b>：C9=133、985(非C9)=40、211(非985)=13、海外=29、其他国内=11。描述性均值 ff5_adj：C9≈0.020、985≈0.022、211≈0.017、海外≈0.022、其他≈0.022——<b>各层几乎无差</b>（极差仅约 0.5pp），已预示"院校层次不解释业绩"。</li>
<li><b>分层哑变量回归</b>（ff5 ~ is_C9+is_985+is_211+is_overseas + log_aum + log_fund_age，OLS+HC1，基准=其他国内）：
<table class="ptable">
<caption>表 2.1b　院校层次 → 业绩（N=226，OLS+HC1，控制规模+年龄）</caption>
<tr><th>变量</th><th>β (t)</th><th>p</th><th>结论</th></tr>
<tr><td>is_C9</td><td class="num">−0.0007 (−0.16)</td><td class="num">0.875</td><td><span class="muted">ns</span></td></tr>
<tr><td>is_985（非C9）</td><td class="num">+0.0006 (0.12)</td><td class="num">0.904</td><td><span class="muted">ns</span></td></tr>
<tr><td>is_211（非985）</td><td class="num">−0.0003 (−0.04)</td><td class="num">0.965</td><td><span class="muted">ns</span></td></tr>
<tr><td>is_overseas</td><td class="num">−0.0003 (−0.04)</td><td class="num">0.967</td><td><span class="muted">ns</span></td></tr>
<tr><td>log_aum（规模）</td><td class="num sigx">+0.0019 (2.08)**</td><td class="num">0.038</td><td><span class="sigx">正</span></td></tr>
<tr><td>log_fund_age（年龄）</td><td class="num sign">−0.0033 (−4.99)***</td><td class="num">0.000</td><td><span class="sign">负</span></td></tr>
</table>
四个院校层次哑变量<b>全部不显著</b>（|t|≤0.16，p≥0.875），R²=0.116。<b>院校层次对风险调整收益没有可识别的影响。</b></li>
<li><b>对照：top-10 名校哑变量（旧做法）</b>：ff5 ~ top10 + log_aum + log_fund_age（同 N=226）：top10 β=−0.0013(t−0.45, p=0.654) 仍不显著，R²=0.116。与分层法结论一致——无论"名校哑变量"还是"层次梯度"都站不住。<b>分层法优于旧 top-10 法</b>：它避开了"10 个哑变量里碰巧 2 个伪显著"的多重检验假象，且梯度更干净（各层均值本就接近）。</li>
<li><b>真正显著的控制：规模与年龄</b>。规模越大 alpha 略高（log_aum β=+0.0019**），基金越老 alpha 越低（log_fund_age β=−0.0033***）——后者与 Xu &amp; Li (2005) 的"中国经理越资深越保守、年轻经理更敢下注"一致，也呼应本层整体"背景非驱动"的结论。</li>
<li><b>持仓快照能增加 school 覆盖吗？——不能。</b> 持仓明细快照（基金持仓明细_全量修正版.csv）列名为 fund_code/report_date/stock_code/hold_ratio…，是<b>股票持仓</b>，<b>不含任何经理/院校字段</b>。school 属经理背景属性，源自已有的经理信息文件；快照只能扩 L2–L5 行为变量覆盖，<b>扩不了 school</b>。真正提高院校覆盖需更完整的经理档案源（Wind/CSMAR 授权终端补全），即"覆盖上限"规划项。</li>
<li><b>TO 口径约定（顺带明确）</b>：换手率以<b>双边 TO_two_sided 为规范测度</b>（真·双边，覆盖 200 只）；单边买卖分解（TO_buy/TO_sell）仅作探索性稳健性，用于揭示"买/卖活跃方向相反"的微观结构，<b>不提高覆盖、也不进主模型</b>。</li>
</ul>
</div>'''

# box ⑥ is delimited by <div class="box note">\n<b>⑥ 院校 ... up to its closing </div>
start_marker = '<div class="box note">\n<b>⑥ 院校(school)回归尝试与结果'
si = html.find(start_marker)
if si < 0:
    print("WARN [req1] start marker NOT FOUND")
else:
    ei = html.find('</div>', si)
    if ei < 0:
        print("WARN [req1] closing </div> NOT FOUND")
    else:
        html = html[:si] + box6_new + html[ei+len('</div>'):]
        print("OK   [req1] box ⑥ replaced")

# update school row conclusion cell (line 158)
a_row='覆盖率 45.9%，未进主回归'; b_row='覆盖率 45.9%，层次重跑仍 ns（见⑥）'
if html.count(a_row)==1:
    print("OK   [req1-row]")
else:
    print("WARN [req1-row] count=%d" % html.count(a_row))
html=html.replace(a_row,b_row,1)

# ---------- REQ 2: insert HC robust SE box before C2 ----------
hc_box = '''
<div class="box ctrl">
<b>稳健标准误（HC）：为什么"修正异方差"、怎么算（流程与原理）</b>
<ul>
<li><b>问题从哪来</b>：OLS 估计 β̂ 的"标准误"默认假设<b>同方差</b>——每个观测的误差方差相同（Var(ε_i)=σ²）。其标准公式 Var(β̂)=σ²(X'X)⁻¹ 只在同方差下成立。但金融面板几乎必然<b>异方差</b>（大基金与小基金的残差波动天差地别），此时 OLS 系数虽仍无偏，但公式算出的 SE <b>系统性偏小</b> → t 值虚高 → 把噪声当显著。这就是"修正异方差的稳健标准误"要解决的问题。</li>
<li><b>三明治（sandwich）估计量</b>：真实协方差 Var(β̂)=(X'X)⁻¹ X'ΩX (X'X)⁻¹，其中 Ω=diag(σ_i²) 是对角但<b>非恒定</b>的残差方差矩阵。我们不知道真实 σ_i²，用<b>残差平方 û_i² 估计</b>：Ω̂=diag(û_i²)。于是稳健 SE 的协方差写成"<b>面包−肉−面包</b>"：bread=(X'X)⁻¹、meat=X'Ω̂X、再 bread，故称 sandwich / "三明治"估计量。SE=√(对角线)。</li>
<li><b>HC0 → HC3 的演进（本项目截面用 HC1）</b>：
  <ul>
  <li><b>HC0</b>：Ω̂_ii=û_i²（最原始）。</li>
  <li><b>HC1</b>：在 HC0 上乘 <b>n/(n−k)</b>（n 样本量、k 参数个数），做小样本自由度修正。<b>本项目截面 R1–R5 一律用 HC1</b>——大样本下最稳健、最常用的默认。</li>
  <li><b>HC2</b>：Ω̂_ii=û_i²/(1−h_ii)，h_ii 是该观测的<b>杠杆值</b>（hat matrix 对角线），对高杠杆点降权。</li>
  <li><b>HC3</b>：Ω̂_ii=û_i²/(1−h_ii)²，对高杠杆点<b>更狠的降权</b>。当数据有强影响点/离群观测时用 HC3 更保险。</li>
  </ul></li>
<li><b>计算流程（5 步）</b>：① 跑普通 OLS，得系数 β̂ 与残差 û；② 算 û_i² 组成 Ω̂；③ 算 meat=X'Ω̂X；④ 三明治 Û=(X'X)⁻¹·meat·(X'X)⁻¹；⑤ SE(β̂)=√(diag Û)，再算 t=β̂/SE 判星。</li>
<li><b>HC 不是万能：面板要用"聚类稳健"而非 HC</b>。HC 家族只修正"<b>截面异方差</b>"，但<b>改不了"同一基金多季度观测互相不独立"</b>——同一经理的不同季度，残差是相关的。若对面板直接用 HC，SE 仍会偏小。本项目<b>面板回归（R6 组内FE、前向回归）一律用"基金聚类稳健标准误"</b>：把 meat 换成 Σ_g X_g' û_g û_g' X_g（按 fund 聚类的"肉"），在基金内允许相关、仅要求基金间独立。一句话：<b>截面用 HC1，面板用基金聚类</b>。</li>
</ul>
</div>
'''
anchor_c2 = '\n<!-- ============ C2 ============ -->'
assert html.count(anchor_c2) == 1, "c2 anchor count=%d" % html.count(anchor_c2)
html = html.replace(anchor_c2, '\n' + hc_box + anchor_c2, 1)
print("OK   [req2] HC box inserted")

# ---------- REQ 3: insert literature box after L1 key conclusion ----------
lit_box = '''
<div class="box note">
<b>⑦ 文献对话：人力资本假说（Golec 1996；Niessen &amp; Ruenzi 2007）与本文 L1 的异同</b>
<ul>
<li><b>Golec (1996, 美国 1988–1990)</b>：样本期早、经理技能差异大。发现<b>更年轻、持 MBA、任期更长</b>的经理带来更高的风险调整超额收益（alpha）；MBA 经理更年轻、任期更短；<b>工作任期对业绩的影响最大</b>。→ 经典"教育/经验 → 业绩"假说的最强支持。</li>
<li><b>Niessen &amp; Ruenzi (2007, "Sex Matters", 美国, 13,547 年-观测 / 3,333 只基金)</b>：女性经理更风险厌恶、风格更不极端、交易更少（更少过度自信）；<b>男女平均业绩无差异</b>；但女性管理的基金获得<b>约 17–18% 更低的资金净流入</b>（投资者刻板印象）。→ 关键结论是"无业绩差异 + 有资金歧视"，而非"女性业绩差"。</li>
<li><b>Chevalier &amp; Ellison (1999, 本文 L1 锚点)</b>：大学质量（用 SAT/选拔度代理）能预测风险调整收益；但<b>MBA 效应弱且不显著</b>。→ 已提示"学历≠能力"的雏形。</li>
<li><b>本文 L1 实测结果</b>：任期 β≈0(t1.20) <b>ns</b>；性别 β=+0.003(t0.75) <b>ns</b>；CFA β=−0.0265(t−5.34)*** 但<b>为负</b>（选择偏差）；院校层次（⑥）全部 ns。即<b>个人信息单看都不驱动业绩</b>。</li>
<li><b>为什么和 Golec 不一样？——猜测</b>：① <b>样本时代</b>：Golec 是 1988–1990 美国早期共同基金，经理技能/学历离散度大；本文是 2018–2025 A 股，经理已高度职业化、名校/高学历近乎"准入门槛"，<b>截面变异被压缩</b>，难再解释收益。② <b>中国特有反向关系</b>：Xu &amp; Li (2005) 发现中国经理<b>年龄/任期与业绩负相关</b>——年轻、新上任的经理更敢冒险博短期收益；本文 log_fund_age 在 L1 与院校回归中均显著为负（β=−0.0033***），与中国模式一致，而与 Golec 的"任期越长越好"相反。③ <b>幸存偏差/成熟度</b>：本文样本基金普遍成熟，任期跨度窄，经验变量信息量低。</li>
<li><b>哪里和文献一致？</b>：① 与 Chevalier &amp; Ellison 一致——<b>学历/MBA 效应本就弱</b>；② 与 Niessen &amp; Ruenzi 一致——<b>性别无业绩差异</b>（本文性别 ns；他们更进一步指出差异在资金流而非业绩，本文无资金流数据故无法检验，但方向不冲突）；③ CFA 负向属中国样本的自我选择（CFA 持有者集中于特定策略/规模），与"资质≠能力"的整体叙事吻合。</li>
<li><b>一句话定位</b>：Golec 的"教育/经验→业绩"在<b>成熟、职业化的 A 股经理群体里未被复制</b>，最稳妥的解释是"资质变异被压缩 + 中国年轻经理更敢下注"；本文因此把 L1 降为<b>控制变量</b>而非能力轴——这与现代文献的细微结论（MBA 弱、性别无差）其实是自洽的。</li>
</ul>
</div>
'''
anchor_lit = '控制而非驱动"的角色。\n</div>\n'
assert html.count(anchor_lit) >= 1, "lit anchor count=%d" % html.count(anchor_lit)
# insert after the FIRST occurrence (the L1 key-conclusion box close)
first = html.find(anchor_lit)
html = html[:first+len(anchor_lit)] + '\n' + lit_box + '\n' + html[first+len(anchor_lit):]
print("OK   [req3] literature box inserted")

# ---------- REQ 4: insert holdings-turnover box before C5 ----------
hold_box = '''
<div class="box note">
<b>用持仓快照算"换手率"：对比相邻两期持仓（用户：能不能用持仓快照做换手）</b>
<ul>
<li><b>做法</b>：对每只基金，取相邻两期持仓快照，算组合权重变化 turnover_t = ½·Σ|w_t − w_{t−1}|（w 为个股持仓占比、期内归一化 Σ=1）。这是"持仓视角的换手"——不依赖双边交易额，只看组合长得变了没有。</li>
<li><b>两种相邻定义</b>：
  <ul>
  <li><b>连续可用快照</b>（任两期相邻即可）：342 只基金有 ≥2 期快照。回归 ff5 ~ hold_turnover + log_aum + log_fund_age（HC1）：<b>β=−0.0059 (t=−0.65) ns</b>，N=331，R²=0.083。</li>
  <li><b>严格季度相邻</b>（两期恰好隔 1 个季度）：142 只基金。<b>β=−0.0493 (t=−3.12)***</b>，N=131，R²=0.106。</li>
  </ul></li>
<li><b>怎么读</b>：在干净的"严格季度相邻"口径下，组合权重换手越高，alpha 反而<b>越低</b>（***）——与"频繁调仓侵蚀业绩"直觉一致；在"连续快照"口径下不显著，可能因为半年度披露间隔把调仓平滑掉了。两种口径方向一致（均为负）。</li>
<li><b>它能不能扩大 TO 覆盖？——不能，但能"换个角度"。</b> 持仓快照覆盖 342 只基金，看似多于交易口径的 200 只；但<b>交集=200</b>（200 只交易 TO 基金全部也在持仓快照里），即持仓快照<b>没有净增新基金</b>，只是把同一批基金的"组合变化"用另一种方式量出来。两者相关仅 <b>corr=0.125</b>（弱）——说明"持仓权重换手"与"双边交易额换手"是<b>不同概念</b>：前者量"组合长没变样"，后者量"买卖做了多少"，交易成本损耗只体现在后者。</li>
<li><b>定位</b>：持仓换手是 trade-based TO 的<b>互补视角</b>（揭示"组合再平衡强度"），而非替代；它同样无法突破"仅凭现有快照"的覆盖上限，提高覆盖仍需 CSMAR/Wind 全样本持仓/交易数据。</li>
</ul>
</div>
'''
anchor_c5 = '\n<!-- ============ C5 ============ -->'
assert html.count(anchor_c5) == 1, "c5 anchor count=%d" % html.count(anchor_c5)
html = html.replace(anchor_c5, '\n' + hold_box + anchor_c5, 1)
print("OK   [req4] holdings-turnover box inserted")

# ---------- REQ 5a: insert 画像速览 executive card before C1 ----------
profile_card = '''
<div class="box" style="border-left:5px solid #0f7b4d;background:#f0fdf7;">
<b>基金经理画像速览（一眼看懂"什么样的经理能跑赢"）</b>
<p style="margin:6px 0 0;">把 L1–L5 五层证据合成，一只<b>能在 A 股持续跑赢的主动股基经理</b>长这样：</p>
<ul style="margin:6px 0 0;">
<li><b>风险应对层(L4)有真能力</b>：主动增益 ARG/RG 双证据强正、收益波动正向——敢下注且押对，是全文最强、最逼近因果的能力轴；</li>
<li><b>行业层(L2)有方向感</b>：行业偏离 ICI 正向***，但主动份额 AS 负向**——赢在"行业下注的方向"，而非"偏离基准的量"；</li>
<li><b>认知偏误层(L5)低拖累</b>：处置效应 de 稳定为负（不死扛亏损）、风险不对称/lsv 受控——纪律性好；</li>
<li><b>交易层(L3)不靠折腾</b>：原始换手 TO 不显著、甚至"组合换手越高 alpha 越低"（严格季度口径 ***）——少做无用交易；</li>
<li><b>背景层(L1)基本中立</b>：院校层次、任期、性别均不显著，CFA 负相关属选择偏差——<b>画像是关于"行为"，不是"人口学"</b>。</li>
</ul>
<p class="muted" style="margin:6px 0 0;">后面的章节不是"一堆回归的清单"，而是沿着这五条维度，逐一用真实数据证明上面的画像为什么成立。</p>
</div>
'''
anchor_c1 = '\n<!-- ============ C1 ============ -->'
assert html.count(anchor_c1) == 1, "c1 anchor count=%d" % html.count(anchor_c1)
html = html.replace(anchor_c1, '\n' + profile_card + anchor_c1, 1)
print("OK   [req5a] profile overview card inserted")

# ---------- REQ 5b: insert c10 archetype section before final foot ----------
c10 = '''
<h2 id="c10">10 · 基金经理画像原型：从五维指标到可识别的经理类型</h2>
<p>前 9 章给出的是"每个维度分别是否显著"。但读者真正想要的是：<b>把这些维度拼起来，市场上到底存在哪几类经理、哪类能跑赢？</b> 基于 L1–L5 的真实回归证据，我们识别出四类可识别的<b>经理画像原型</b>（archetype）。它们不是聚类结果，而是沿"强能力轴 vs 弱/负向轴"做的有经济含义的类型划分，便于论文在"结论"章直接用于经理评价与筛选。</p>

<div style="display:flex;flex-wrap:wrap;gap:14px;margin:14px 0;">
  <div style="flex:1 1 46%;min-width:280px;border:1px solid #e2e8f0;border-top:4px solid #0f7b4d;border-radius:8px;padding:14px;background:#fff;">
    <b style="color:#0f7b4d;font-size:15px;">① 风控择股型 · 赢家画像</b>
    <p style="margin:8px 0 0;font-size:13px;line-height:1.6;">L4 主动增益 ARG/RG <b>双证据强正</b>（截面+组内FE 均 ***）、收益波动率正向；L2 行业偏离 ICI 正向***。敢下注且押对，是全文最强、最可识别的能力轴。</p>
    <p class="muted" style="margin:8px 0 0;font-size:12px;">业绩暗示：历史与未来 alpha 最强、最稳，画像筛选的<b>首选目标</b>。</p>
  </div>
  <div style="flex:1 1 46%;min-width:280px;border:1px solid #e2e8f0;border-top:4px solid #1d4ed8;border-radius:8px;padding:14px;background:#fff;">
    <b style="color:#1d4ed8;font-size:15px;">② 行业集中下注型</b>
    <p style="margin:8px 0 0;font-size:13px;line-height:1.6;">ICI 高、主动份额 AS <b>低（负**）</b>；不在"主动多少"而在"行业方向"表达观点。与 Cremers &amp; Petajisto (2009) 相反、与本文中国语境一致——<b>主动份额折价、行业偏离溢价</b>。</p>
    <p class="muted" style="margin:8px 0 0;font-size:12px;">业绩暗示：行业层面的有意识集中下注带来 alpha，是"方向 &gt; 量"的典型。</p>
  </div>
  <div style="flex:1 1 46%;min-width:280px;border:1px solid #e2e8f0;border-top:4px solid #7c3aed;border-radius:8px;padding:14px;background:#fff;">
    <b style="color:#7c3aed;font-size:15px;">③ 低偏误纪律型</b>
    <p style="margin:8px 0 0;font-size:13px;line-height:1.6;">处置效应 de <b>稳定负向</b>、风险不对称/lsv 受控；不追涨杀跌、不被抱团裹挟、不的事死扛亏损头寸。认知偏误层拖累小。</p>
    <p class="muted" style="margin:8px 0 0;font-size:12px;">业绩暗示：稳定、偏"分型控制"——不是实时因果驱动，但刻画"属于哪类经理"，利于组合构建时避开高偏误者。</p>
  </div>
  <div style="flex:1 1 46%;min-width:280px;border:1px solid #e2e8f0;border-top:4px solid #b4690e;border-radius:8px;padding:14px;background:#fff;">
    <b style="color:#b4690e;font-size:15px;">④ 高换手噪声型 · 输家画像</b>
    <p style="margin:8px 0 0;font-size:13px;line-height:1.6;">双边/持仓换手高；在<b>严格季度相邻口径下换手越高 alpha 越低（***）</b>；处置效应高。频繁调仓、过早了结赢家、死扛亏损。</p>
    <p class="muted" style="margin:8px 0 0;font-size:12px;">业绩暗示：换手侵蚀业绩，是画像筛选应<b>规避</b>的类型；与 ① 形成对照。</p>
  </div>
</div>

<div class="box">
<b>原型之上的统一结论</b>：四类原型里，<b>L1 背景（院校/任期/性别/CFA）在所有原型中都是"中立"的</b>——它不改变你是哪类经理，也不决定你跑不跑得赢。这正呼应第 7 章雷达图中 <b>L1 在组内FE下塌缩至轴心</b>：画像是关于<b>行为微观结构</b>，不是人口学标签。因此"基于画像的经理评价与筛选"应锚定 L4/L5/L2 的行为轴，而非院校或资历。
</div>
'''
anchor_foot = '\n<div class="foot">'
assert html.count(anchor_foot) == 1, "foot anchor count=%d" % html.count(anchor_foot)
html = html.replace(anchor_foot, '\n' + c10 + anchor_foot, 1)
print("OK   [req5b] c10 archetype section inserted")

io.open(path, "w", encoding="utf-8").write(html)
print("\n=== 画像 HTML written, length=%d ===" % len(html))
