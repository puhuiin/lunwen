# -*- coding: utf-8 -*-
"""画像 HTML：插入 Req1-4 内容（CFA核查 / R3白话 / 前向RHS解释 / 打分分型可视化）。"""
import json
base="D:/Desktop/基金经理行为分析研究/"
F=base+"基金经理能力画像与业绩评价.html"
html=open(F,encoding="utf-8").read()
heat=open(base+"scoring_heatmap.svg",encoding="utf-8").read()
typebar=open(base+"scoring_typebar.svg",encoding="utf-8").read()
J=json.load(open(base+"scoring_results.json",encoding="utf-8"))

# Top/Bottom 5 配对行
top=J["top"][:5]; bot=J["bottom"][:5]
rows=""
for i in range(5):
    t=top[i]; b=bot[i]
    rows+=f'<tr><td>{i+1}</td><td>{t["fund"]}</td><td class="num sigx">+{t["score"]:.2f}</td>' \
          f'<td>{b["fund"]}</td><td class="num sign">{b["score"]:.2f}</td></tr>\n'

# ---------- Req2 CFA box ----------
cfa_box='''<div class="box warn">
<b>⑦ CFA 哑变量误导性核查（用户：CFA 负向不符合逻辑 → 我们查了）</b>
<p><b>结论先说：CFA 那列是"误导性变量"，负系数不是真实效应，不能写进结论。</b>我们按基金层重新统计：400 只基金里只有 <b>19 只（4.75%）</b>被标为"有 CFA"，其余 381 只全是"否"。而"有 CFA"那组的 ff5 alpha 均值（0.0124）反而<b>低于</b>"无 CFA"组（0.0207）——这正是负系数（β=−0.0265, t−5.34）的来源。</p>
<p><b>为什么这是数据假象，不是"CFA 损害业绩"？我们联网调研了真实情况：</b></p>
<ul>
<li>天天基金/雪球、Wind、脉脉等公开统计显示，中国公募基金经理的 <b>CFA 实际持证率仅约 4–5%</b>（与我们的 4.75% 几乎一致）——说明数据"数得准"，<b>并非人人都有 CFA</b>。</li>
<li>但 CFA 只是<b>单一证书标识</b>。大量经理持的是 <b>CPA、FRM、ACCA、法律资格、海外证书（CAIA/CIIA 等）</b>（公开报道：CFA+FRM+CPA+司考组合很常见，且"实际持证人数远超披露"）。这些人在我们的表里全被编码成"否"。</li>
<li>所以 <code>cfa_d</code> 哑变量<b>不是"有无专业资质"的代理</b>：它的"否" = {真无证书} ∪ {有其他证书} ∪ {未调查} 的混合物。用它回归得到的负系数，反映的是"被标为 CFA 的那 19 只恰好业绩偏弱"的样本/选择特征，<b>不可作因果或能力解读</b>。</li>
</ul>
<p><b>处理建议（已采纳）：</b>① 把 CFA 行明确标注为"选择偏差/数据局限，作控制变量，勿因果解读"；② 表内加注"CFA 覆盖率仅 4.75%，且不代表全部专业资质"；③ 若未来拿到完整资质字段，应合并为"持证情况"复合变量，而非单独用 CFA。这与 §3.5 / 表 11.1 的"CFA 负→作控制、勿因果"结论一致。</p>
</div>
'''

# ---------- Req3 R3 白话 ----------
r3_box='''<div class="box note">
<b>R3 白话详解：这一步到底在干嘛、那个 γ 是什么、怎么算的</b>
<p><b>一句话：</b>R3 是一个"证伪压力测试"——我们要确认画像里的 <b>RiskAsym（风险不对称，RA）</b>是经理的<b>真实行为特征</b>，而不是"底层股票天然波动规律"在基金层面的伪装。</p>
<p><b>背景知识（为什么需要这一步）：</b>股票有个著名现象叫<b>杠杆效应</b>——股价<b>跌</b>的时候，波动往往会比<b>涨</b>的时候放大得更厉害（跌了公司更危险，投资者更慌）。这是股票本身的物理属性，跟经理能力无关。如果我们的 RA 测度其实只是这个股票杠杆效应的"倒影"，那它就不配当"行为画像轴"。</p>
<p><b>自变量 <code>egarch_gamma</code>（条件波动不对称系数）是什么、怎么算：</b></p>
<ul>
<li>我们对<b>每只基金</b>的日净值收益序列，拟合一个 <b>EGARCH(1,1)</b> 模型（至少需要 250 个交易日的收益）。这个模型专门用来刻画"今天的冲击如何不对称地影响明天的波动"。</li>
<li>模型里有一个关键参数 <b>γ（gamma）</b>：<code>log(σ²_t) = ω + α·|z| + γ·z + β·log(σ²_{t-1})</code>，其中 z 是标准化收益。<b>γ &lt; 0 就表示杠杆效应</b>——负冲击比同等正冲击更放大波动。</li>
<li>所以这个 γ 是<b>每只基金一个数字</b>（从它自己的日收益里"反推"出来的），它衡量的是"这只基金持仓的波动，在跌的时候是不是比涨的时候放大得更多"。</li>
</ul>
<p><b>为什么要对 γ 截尾（winsorize）：</b>拟合偶尔会失败。我们的数据里有 <b>43 只基金</b>的 γ 算成了极端哨兵值 <b>−8869</b>（正常 γ 应在 ±0.1 附近）。这个 −8869 会把回归的尺度撑爆，造出"γ 极显著（t=26.3）"的假象。所以我们在 1%/99% 分位把 γ 截断（γ_wins 落在 [−0.087, +0.071]），再重跑。</p>
<p><b>回归在检验什么（看表 8.1）：</b>我们跑两个模型，DV 都是未来收益 <code>future_return</code>：
<span class="formula">M1: future_return = α + β·RA      + 控制变量
M2: future_return = α + β·RA + θ·γ_wins + 控制变量</span>
逻辑是：<b>如果 RA 只是杠杆效应的伪装，那么把 γ 控制进去后，RA 的系数应大幅缩水甚至消失。</b>结果：</p>
<ul>
<li>γ_wins 自己只有 <b>温和且独立</b>的效应：β=0.319 (t=3.3)**，说明股票层杠杆效应真实存在但很弱；</li>
<li>RA 的系数<b>几乎没动</b>（0.915 → 0.924，反而略升），t 从 18.7 升到 19.1。</li>
</ul>
<p><b>结论（大白话）：</b>控制了"股票跌了波动更大"这个底层规律后，RA 依然强力预测未来业绩——所以 <b>RA 是经理真实的行为风险偏好，不是数据假象</b>。这就是给 RA 轴发的"真信号合格证"。</p>
</div>
'''

# ---------- Req4 前向 RHS 解释 ----------
fwd_box='''<div class="box note">
<b>为什么前向预测方程只放了 risk_asym / lsv / de 三个变量？</b>
<p>表 9.1 的前向回归 RHS = <code>risk_asym + lsv + de</code> + 控制（规模/年龄/年份FE）。这<b>不是因为其他层不能预测未来</b>，而是当时把前向研究<b>聚焦在 L5「认知偏差/行为」构念</b>上做"画像→预测"的概念验证。我们刚刚把<b>每一层代表变量单独</b>对 fut4q 跑了一遍前向回归（控制相同，基金聚类 SE），结果很多层都显著：</p>
<table class="ptable">
<caption>表 9.2　各层变量单独前向预测力（fut4q，基金聚类）</caption>
<tr><th>层级</th><th>变量</th><th>fut4q β (t)</th><th>是否预测未来</th></tr>
<tr><td>L2</td><td>AS_improved</td><td class="num sigx">+0.090 (12.7)***</td><td>是</td></tr>
<tr><td>L2</td><td>ICI</td><td class="num sigx">+0.030 (4.05)***</td><td>是</td></tr>
<tr><td>L3</td><td>TO_two_sided</td><td class="num sigx">+0.020 (2.29)**</td><td>是（仅200只）</td></tr>
<tr><td>L4</td><td>ARG</td><td class="num sigx">+0.154 (15.3)***</td><td>是（最强之一）</td></tr>
<tr><td>L4</td><td>return_volatility</td><td class="num sigx">+0.487 (18.1)***</td><td>是（最强）</td></tr>
<tr><td>L4</td><td>RG</td><td class="num sigx">+0.037 (5.64)***</td><td>是</td></tr>
<tr><td>L5</td><td>risk_asym</td><td class="num sigx">+0.642 (24.1)***</td><td>是</td></tr>
<tr><td>L5</td><td>lsv</td><td class="num sign">−0.050 (−3.24)***</td><td>是（负）</td></tr>
<tr><td>L5</td><td>de</td><td class="num sign">−0.090 (−13.0)***</td><td>是（负）</td></tr>
</table>
<p><b>所以"只放三个"是设定偏窄，不是证据偏窄。</b>论文若想做"全画像预测力"的 horse race，应把 L4 的 ARG / return_volatility 也纳入前向模型（它们预测力甚至强于 L5 部分变量），并报告<b>增量 R²</b>。注意：ARG 与 return_volatility 高度相关，纳入时需警惕共线——建议用"代表变量逐层加入"的递进式前向回归来展示每层画像的<b>增量</b>预测力。这一扩展已列入下一步。</p>
</div>
'''

# ---------- Req1 打分分型章节 ----------
scoring_sec=f'''<h2 id="c10b">10b · 基金经理能力评分与分型（把画像变成可排序、可定型的"产品"）</h2>
<p>前面 5 层 + 雷达图 + 预测，已经能"解释"经理。但用户要的是——能不能直接<b>打分</b>、能不能<b>分型</b>、能不能一眼看出"谁是好经理"。这一步把画像<b>产品化</b>。</p>
<h4>方法：用"前向预测力"给每个维度加权打分</h4>
<p>最公平的权重不是拍脑袋，而是用<b>每个维度对未来业绩（fut4q）的预测系数</b>当权重——能预测未来的维度，权重就大。流程：</p>
<ul>
<li>每只基金取其各维度的<b>基金层均值</b>，再在基金间做 <b>z 标准化</b>（均值0、标准差1），消除量纲；</li>
<li><b>综合得分</b> = 各维度 z 分数按其前向系数符号与大小加权求和（权重归一化）。正向维度高、或负向维度低 → 高分；</li>
<li>得分再标准化，便于跨基金比较（正值=优于平均，负值=劣于平均）。</li>
</ul>
<p>覆盖说明：12 个维度中 de/lsv/TO 覆盖较低（392/394/200 只），缺失维度在加权时自动跳过并按可用维度重新归一权重——<b>400 只基金全部得到得分</b>。</p>
<h4>分型：四类可识别经理（基于 z 分数的规则匹配）</h4>
<p>在高维打分之上，按行为金融直觉设 4 条原型规则（优先级匹配），把基金归入：</p>
<table class="ptable">
<caption>表 10b.1　四类经理原型定义与在本样本的分布</caption>
<tr><th>原型</th><th>判定规则（z 分数）</th><th>样本数</th><th>含义</th></tr>
<tr><td>风控择股型(赢家)</td><td>RA≥0.5 且 ARG≥0.5 且 DE≤0.3</td><td class="num">33</td><td>有利风险不对称+主动收益强+少处置效应→系统性跑赢</td></tr>
<tr><td>行业集中下注型</td><td>ICI≥0.5 且 AS≤0.3</td><td class="num">20</td><td>集中下注行业（高 ICI）、低主动份额→押赛道</td></tr>
<tr><td>低偏误纪律型</td><td>DE≤−0.5 且 |LSV|≤0.5</td><td class="num">29</td><td>卖盈持亏弱+不盲从→纪律型</td></tr>
<tr><td>高换手噪声型(输家)</td><td>TO≥0.5 且 RA≤0</td><td class="num">57</td><td>高换手但无风险不对称优势→交易磨损收益</td></tr>
<tr><td>均衡型(其他)</td><td>不满足以上</td><td class="num">261</td><td>各维度无明显极端→中庸</td></tr>
</table>
<h4>可视化一：能力热力图（Top25 基金 × 8 维度）</h4>
<p>颜色按"对未来业绩是否有利"定向：<b>红=有利、蓝=不利</b>。一眼可见赢家（如 21626/21627）在 RA/ARG/RV 全红，输家在低分区 RA 偏蓝、TO 偏红。</p>
{heat}
<p class="muted">注：热力图仅展示 Top25；完整 400 只基金得分与分型见 <code>scoring_results.json</code>。DE/LSV 为"负向有利"，已按 −z 定向显示（红=低处置效应=好）。</p>
<h4>可视化二：分型分布</h4>
{typebar}
<h4>Top / Bottom 基金经理（综合得分）</h4>
<table class="ptable">
<caption>表 10b.2　综合得分最高 / 最低各 5 只（完整 15 只见 JSON）</caption>
<tr><th>排名</th><th>基金代码</th><th>得分</th><th>基金代码</th><th>得分</th></tr>
{rows}</table>
<p><b>产品化价值：</b>这套"打分+分型"可直接做成一个<b>基金经理筛选器</b>——按综合得分排序选基，或按原型匹配不同风险偏好的客户（如保守型配"低偏误纪律型"、进取型配"风控择股型"）。它把全文"画像→能力→业绩"的主线，落成了一个可操作的输出。</p>
'''

# ---------- 执行插入 ----------
def ins(anchor, block, label):
    i=html.find(anchor)
    if i<0:
        print("FAIL anchor:",label); return False
    html[0:0]  # noop
    return i

i1=html.find('⑥ 毕业院校(school)按"院校层次"重跑（用户：按层次划分试一下，QS 亦可）')
i2=html.find('<!-- ============ C9 ============ -->')
i3=html.find('<!-- ============ C10 ============ -->')
assert i1>0 and i2>0 and i3>0, (i1,i2,i3)
# 顺序插入（从后往前插避免位移）
html=html[:i3]+fwd_box+scoring_sec+html[i3:]
html=html[:i2]+r3_box+html[i2:]
html=html[:i1]+cfa_box+html[i1:]
open(F,"w",encoding="utf-8").write(html)
print("OK profile: cfa@%d r3@%d fwd+scoring@%d"%(i1,i2,i3),"len",len(html))
