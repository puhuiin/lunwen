# -*- coding: utf-8 -*-
"""报告 HTML：插入 Req1-4 内容（CFA核查 / R3白话 / 前向RHS解释 / 打分分型）。"""
import json
base="D:/Desktop/基金经理行为分析研究/"
F=base+"实证结果完整报告与论文写作指南.html"
html=open(F,encoding="utf-8").read()
heat=open(base+"scoring_heatmap.svg",encoding="utf-8").read()
typebar=open(base+"scoring_typebar.svg",encoding="utf-8").read()
J=json.load(open(base+"scoring_results.json",encoding="utf-8"))
top=J["top"][:5]; bot=J["bottom"][:5]
rows=""
for i in range(5):
    t=top[i]; b=bot[i]
    rows+=f'<tr><td>{i+1}</td><td>{t["fund"]}</td><td class="num sigx">+{t["score"]:.2f}</td>' \
          f'<td>{b["fund"]}</td><td class="num sign">{b["score"]:.2f}</td></tr>\n'

cfa_box='''<div class="box warn">
<b>CFA 哑变量误导性核查（用户：CFA 负向不符合逻辑 → 已查实）</b>
<p><b>结论：CFA 列是误导性变量，负系数不可作因果/能力解读。</b>基金层重统：400 只中仅 <b>19 只（4.75%）</b>标"有 CFA"；"有 CFA"组 ff5 alpha 均值 0.0124 <b>低于</b>"无 CFA"组 0.0207，正是 β=−0.0265(t−5.34) 的来源。</p>
<ul>
<li>联网调研：中国公募经理 CFA <b>实际持证率约 4–5%</b>（天天基金/Wind/脉脉），与我们的 4.75% 一致→数据"数得准"，<b>非人人有 CFA</b>；</li>
<li>但 CFA 仅<b>单一证书标识</b>；大量经理持 CPA/FRM/ACCA/法律资格/海外证书（公开报道 CFA+FRM+CPA+司考常见，"实际持证远超披露"），这些在表中全编码为"否"；</li>
<li>故 <code>cfa_d</code> 哑变量<b>非"有无专业资质"代理</b>，"否"={无证书}∪{有其他证书}∪{未调查}，负系数=样本/选择特征。</li>
</ul>
<p><b>论文处理：</b>CFA 行标注"选择偏差/数据局限，作控制、勿因果解读"；加注"覆盖率仅 4.75% 且不代全部资质"；未来应合并为"持证情况"复合变量。与表 2.9 / §3.5 的"CFA 负→作控制"一致。</p>
</div>
'''

r3_box='''<div class="box note">
<b>R3 白话详解（写给审稿人/读者，非专业版）</b>
<p><b>一句话：</b>R3 是"证伪压力测试"——确认画像的 <b>RiskAsym（RA）</b>是经理<b>真实行为特征</b>，而非"底层股票波动规律"的伪装。</p>
<p><b>为什么需要它：</b>股票有<b>杠杆效应</b>——跌时波动比涨时放大更厉害，这是股票物理属性、与经理无关。若 RA 只是该效应的"倒影"，就不配当行为轴。</p>
<p><b>自变量 <code>egarch_gamma</code> 是什么、怎么算：</b>对<b>每只基金</b>日收益拟合 <b>EGARCH(1,1)</b>（≥250 日），模型 <code>log(σ²_t)=ω+α·|z|+γ·z+β·log(σ²)</code>，其中 <b>γ&lt;0 = 杠杆效应</b>。γ 是"每只基金一个数字"，度量其持仓波动在跌时是否比涨时更放大。</p>
<p><b>为什么截尾：</b>43 只基金 γ 拟合失败成哨兵值 <b>−8869</b>（正常 ±0.1 内），撑爆尺度造出假显著（t=26.3）。在 1%/99% 截尾（γ_wins∈[−0.087,0.071]）后重跑。</p>
<p><b>检验逻辑（表 2.7）：</b>DV=future_return，M1 仅 RA+控制，M2 再加 γ_wins。若 RA 是伪装，加 γ 后 RA 系数应缩水。结果：γ_wins 仅 <b>温和独立</b>效应 β=0.319(t3.3)**；RA 系数<b>几乎不动</b>（0.915→0.924，t 18.7→19.1）。→ <b>RA 是真实行为构念，非杠杆效应机械穿透</b>。这就是 RA 轴的"真信号合格证"。</p>
</div>
'''

fwd_box='''<div class="box note">
<b>为什么前向方程只放 risk_asym / lsv / de？</b>
<p>表 2.8 的 RHS = <code>risk_asym + lsv + de</code> + 控制，是当时把前向研究<b>聚焦在 L5 认知偏差构念</b>的概念验证，<b>不代表其他层不能预测未来</b>。我们把各层代表变量单独对 fut4q 跑前向回归（基金聚类），发现 L4 的 ARG(t15.3)/return_volatility(t18.1)、L2 的 AS(t12.7)/ICI(t4.0) 也极显著：</p>
<table class="ptable">
<caption>表 2.8b　各层单独前向预测力（fut4q，基金聚类）</caption>
<tr><th>层</th><th>变量</th><th>β (t)</th></tr>
<tr><td>L2</td><td>AS / ICI</td><td class="num sigx">+0.090(12.7) / +0.030(4.05)***</td></tr>
<tr><td>L3</td><td>TO</td><td class="num sigx">+0.020(2.29)**</td></tr>
<tr><td>L4</td><td>ARG / return_volatility / RG</td><td class="num sigx">+0.154(15.3) / +0.487(18.1) / +0.037(5.64)***</td></tr>
<tr><td>L5</td><td>risk_asym / lsv / de</td><td class="num sigx">+0.642(24.1) / −0.050(−3.24) / −0.090(−13.0)***</td></tr>
</table>
<p><b>"只放三个"是设定偏窄，不是证据偏窄。</b>建议论文补充"全画像预测力"递进式前向回归：逐层加入代表变量并报告<b>增量 R²</b>；注意 ARG 与 return_volatility 共线，宜用代表变量而非全集。已列入下一步。</p>
</div>
'''

scoring_sec=f'''<h3>5.x · 能力评分与分型（可视化落地）</h3>
<p>把画像"产品化"：用<b>前向预测系数</b>给各维度加权，算出每只基金的<b>综合能力得分</b>，再按 z 分数规则分为四类原型。权重透明、可复算（见 <code>compute_scoring.py</code> / <code>scoring_results.json</code>）。</p>
<table class="ptable">
<caption>表 5.x.1　四类经理原型（本样本分布）</caption>
<tr><th>原型</th><th>规则(z)</th><th>样本</th></tr>
<tr><td>风控择股型(赢家)</td><td>RA≥0.5 ∧ ARG≥0.5 ∧ DE≤0.3</td><td class="num">33</td></tr>
<tr><td>行业集中下注型</td><td>ICI≥0.5 ∧ AS≤0.3</td><td class="num">20</td></tr>
<tr><td>低偏误纪律型</td><td>DE≤−0.5 ∧ |LSV|≤0.5</td><td class="num">29</td></tr>
<tr><td>高换手噪声型(输家)</td><td>TO≥0.5 ∧ RA≤0</td><td class="num">57</td></tr>
<tr><td>均衡型(其他)</td><td>其余</td><td class="num">261</td></tr>
</table>
<p>热力图（Top25×8 维，红=有利未来业绩）与分型分布：</p>
{heat}
{typebar}
<table class="ptable">
<caption>表 5.x.2　综合得分 Top/Bottom 各 5（完整 15 见 JSON）</caption>
<tr><th>排名</th><th>基金</th><th>得分</th><th>基金</th><th>得分</th></tr>
{rows}</table>
<p><b>论文如何呈现：</b>此节可作"经理评价/筛选"应用章；热力图与分型条形图直接进正文，Top/Bottom 表进附录；强调"打分用前向预测力加权"的方法论透明度，呼应全文"画像→能力→业绩"主线。</p>
'''

# 插入
a=html.find('一致处</b>：与 Chevalier')
b=html.find('<!-- H R2 前向 -->')
c=html.find('与 R6 形成方法论对照。')
d=html.find('<!-- ============ S5 ============ -->')
assert all(x>0 for x in (a,b,c,d)), (a,b,c,d)
# 从后往前插
html=html[:d]+scoring_sec+html[d:]
html=html[:c+len('与 R6 形成方法论对照。')]+fwd_box+html[c+len('与 R6 形成方法论对照。'):]
html=html[:b]+r3_box+html[b:]
html=html[:a]+cfa_box+html[a:]
open(F,"w",encoding="utf-8").write(html)
print("OK report: cfa@%d r3@%d fwd@%d scoring@%d len=%d"%(a,b,c,d,len(html)))
