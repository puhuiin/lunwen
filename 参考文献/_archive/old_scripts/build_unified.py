# -*- coding: utf-8 -*-
"""
统一生成：基金经理行为分析 — 变量指标与构建方法全解（L1–L5 + M）
1) 以 L1-L3 参考文件为基，注入 L4/L5/M 变量明细（由 JSON 渲染）
2) 新增「核心变量构建方法精要」：最佳参考文献推荐 + 指标计算详解
"""
import json, html, os, glob
from collections import defaultdict

BASE = r"D:/Desktop/基金经理行为分析研究/参考文献"
BASE_L13 = r"C:/Users/26955/Downloads/变量指标L1-L3.html"

# ---------- 读取 L1-L3 基文件 ----------
base = open(BASE_L13, encoding="utf-8").read()

# ---------- 读取 L4/L5/M JSON ----------
jfiles = sorted(glob.glob(os.path.join(BASE, "extracted_variables_*.json")))
records = []
for f in jfiles:
    try:
        records.extend(json.load(open(f, encoding="utf-8")))
    except Exception as e:
        print("ERR", f, e)
print("L4/L5/M 记录数:", len(records))

def norm_layer(r):
    L = str(r.get("layer", ""))
    if L.startswith("L4"): return "L4"
    if L.startswith("L5"): return "L5"
    if L.startswith("M"):  return "M"
    return L
for r in records:
    r["layer"] = norm_layer(r)

LAYER_ORDER = {"L4": 0, "L5": 1, "M": 2}
LAYER_NAME = {"L4": "L4 风险应对层", "L5": "L5 认知行为层", "M": "M 方法论与识别检验"}
records.sort(key=lambda r: (LAYER_ORDER.get(r.get("layer", ""), 9), r.get("file", "")))

def esc(x):
    return html.escape("" if x is None else str(x))

def var_rows(vars, kind):
    if not vars:
        return f'<tr><td colspan="4" class="muted">（本节未单独列出{"自" if kind=="iv" else "因"}变量）</td></tr>'
    if isinstance(vars, str):
        return f'<tr><td colspan="4">{esc(vars)}</td></tr>'
    rows = []
    for v in vars:
        if not isinstance(v, dict):
            rows.append(f'<tr><td colspan="4">{esc(v)}</td></tr>'); continue
        name = esc(v.get("name", ""))
        defn = esc(v.get("definition", ""))
        formula = esc(v.get("formula", ""))
        ds = esc(v.get("data_source", ""))
        fcell = f"<code>{formula}</code>" if formula else "—"
        dscell = ds if ds else "—"
        rows.append(f"<tr><td><b>{name}</b></td><td>{defn}</td><td>{fcell}</td><td>{dscell}</td></tr>")
    return "".join(rows)

def render_paper(r):
    layer = r.get("layer", "")
    tagcls = {"L4":"l4","L5":"l5","M":"lm"}.get(layer, "l4")
    fname = esc(r.get("file", ""))
    title = esc(r.get("title", ""))
    ay = esc(r.get("authors_year", ""))
    topic = esc(r.get("topic", ""))
    iv = r.get("independent_variables", [])
    dv = r.get("dependent_variables", [])
    cv = esc(r.get("control_variables", ""))
    kf = esc(r.get("key_formulas", ""))
    desc = esc(r.get("descriptive_stats", ""))
    notes = esc(r.get("notes", ""))
    ds = r.get("data_source", {})
    if isinstance(ds, dict):
        ds_str = f'{esc(ds.get("source",""))} ｜ {esc(ds.get("sample_period",""))} ｜ {esc(ds.get("sample_size",""))}'
    else:
        ds_str = esc(ds)
    mismatch = ("文件名与内容严重不符" in notes) or ("【文件名" in notes)
    warn = '<div class="warn">⚠ 文件名与 PDF 实际内容不符，已按真实内容提取，请核对文件命名。</div>' if mismatch else ""
    return f'''
    <h3><span class="layer-tag {tagcls}">{layer}</span> {fname}</h3>
    <p class="sub">{title} — {ay}</p>
    {warn}
    <p class="topic">{topic}</p>
    <table><thead><tr><th>自变量（IV）</th><th>定义 / 度量</th><th>公式</th><th>数据来源</th></tr></thead>
    <tbody>{var_rows(iv,"iv")}</tbody></table>
    <table><thead><tr><th>因变量（DV）</th><th>定义 / 度量</th><th>公式</th><th>数据来源</th></tr></thead>
    <tbody>{var_rows(dv,"dv")}</tbody></table>
    <div class="kv-wrap">
      <div class="kv"><span class="k">控制变量</span><span class="v">{cv if cv else '—'}</span></div>
      <div class="kv"><span class="k">数据来源</span><span class="v">{ds_str}</span></div>
    </div>
    <div class="section"><div class="sec-label">核心公式</div><div class="vdef"><code>{kf if kf else '—'}</code></div></div>
    <div class="section"><div class="sec-label">描述性统计</div><div class="vdef">{desc if desc else '—'}</div></div>
    {('<div class="section"><div class="sec-label">备注</div><div class="vdef">'+notes+'</div></div>') if notes else ''}
    '''

# 按层分组渲染
layer_html = {}
for layer in ["L4","L5","M"]:
    recs = [r for r in records if r.get("layer")==layer]
    blocks = "\n".join(render_paper(r) for r in recs)
    layer_html[layer] = blocks

# ============================================================
# 第二部分：核心变量构建方法精要（最佳参考文献 + 指标计算详解）
# ============================================================
PARTB = r'''
<h2 id="s11">十一、核心变量构建方法精要（最佳参考文献与指标计算详解）</h2>
<p>本节面向本篇论文（基金经理行为分析）的研究框架，按「背景特征 → 持仓偏离/风格漂移 → 交易行为/隐形交易 → 锦标赛/风险调整 → 羊群行为 → 处置效应 → 过度自信/前景理论 → 方法论识别」八大主题，筛选最值得引用的<b>经典与权威文献</b>，并逐一拆解其<b>变量如何构建、指标如何计算</b>。凡标注「推荐首选」者，即对应主题的最优方法参照。</p>

<!-- 主题一 -->
<h3>主题一　背景特征变量（L1：刻画"谁在管理"）</h3>
<div class="note">本主题回答"基金经理个人与治理特征如何影响行为与业绩"。最优参照为 Chevalier &amp; Ellison (1999) 的职业忧虑框架，以及国内大样本个人特征实证（吴栩 2017、赵秀娟 2010、于静 2013、Li &amp; Li 2018）。</div>

<h4>① Chevalier &amp; Ellison (1999, QJE) — 职业忧虑与风格漂移【推荐首选】</h4>
<p>以"年轻→职业忧虑强→更冒险/更趋同于基准"为核心机制。变量构建：</p>
<div class="formula">职业忧虑代理 = 经理年龄 / 任职年限 / 历史相对排名（越年轻、任职越短、排名越靠后，忧虑越强）</div>
<div class="formula">风格漂移代理 = 基金收益对"申报投资目标"回归的 R² 下降，或跟踪误差（TE）相对同风格基金的偏离；年轻经理 R² 更低（更偏离宣称风格）</div>
<p>数据来源： Morningstar 自报基准 + 基金净值/持仓（CRSP）。该文奠定了"背景特征→行为"的因果识别思路（工具变量：同期同校毕业的经理供给冲击）。</p>

<h4>② Li &amp; Li (2018) — 经理特征与综合业绩（超效率 DEA + 门槛面板）</h4>
<div class="formula">超效率 DEA：产出 = 年化收益率；投入 = 托管费用率 + 收益标准差（标准差↓、收益↑ ⇒ 效率↑）</div>
<div class="formula">门槛面板：以经理特征（性别/年龄/学历/证券从业年限/MBA/CFA/管理基金数）作门槛变量，检验其对业绩的非线性影响</div>
<p>数据来源： Wind + CSMAR；样本为开放式主动偏股基金，连续变量 1% 缩尾。</p>

<h4>③ 国内个人特征实证（吴栩 2017 / 赵秀娟 2010 / 于静 2013）</h4>
<table>
<thead><tr><th>变量</th><th>度量方式</th><th>取值</th><th>数据来源</th></tr></thead>
<tbody>
<tr><td>性别 Gender</td><td>男性=1（或女性=1）</td><td>虚拟变量</td><td>Wind / 简历</td></tr>
<tr><td>年龄 / 任期</td><td>周岁年龄；任基金经理年限（均值约 7.22 年）</td><td>连续</td><td>Wind / 天相</td></tr>
<tr><td>学历（硕/博）</td><td>是否硕士 / 博士</td><td>虚拟</td><td>Wind / 简历</td></tr>
<tr><td>MBA / CFA / CPA</td><td>是否持有</td><td>虚拟</td><td>Wind / 简历</td></tr>
<tr><td>海外背景 / 名校</td><td>是否有海外留学或 985 背景</td><td>虚拟</td><td>简历</td></tr>
</tbody></table>

<h4>④ 申宇等 (2015) — 校友关系网络中心度（"小圈子"效应）</h4>
<div class="formula">Degree_i = Σⱼ I{校友(i,j)} / (g−1)　（程度中心度，广度）</div>
<div class="formula">Betweenness（中介中心度）＋ Closeness（亲疏中心度，深度）；均来自简历构建的校友网络</div>
<p>数据来源： 锐思(RESSet) 高管/经理简历。用于检验"校友网络→信息优势/业绩"的治理特征渠道。</p>

<!-- 主题二 -->
<h3>主题二　持仓偏离与风格漂移（L2 + L4：刻画"组合如何偏离基准"）</h3>
<div class="note">刻画基金主动管理程度与风格一致性。持仓偏离的黄金标尺是 Cremers &amp; Petajisto (2009) 的 Active Share；风格漂移的国内权威测度为寇宗来等 (2020) 与易力 &amp; 盛冰心 (2021)。</div>

<h4>① Cremers &amp; Petajisto (2009/2013) — Active Share 与 Tracking Error【推荐首选】</h4>
<div class="formula">Active Share：AS = ½ Σᵢ |w_fund,i − w_index,i|　（取值 0%–100%，越高越主动）</div>
<div class="formula">Tracking Error：TE = Stdev(R_fund − R_index)　或回归残差标准差</div>
<p>数据来源： Thomson CDA/Spectrum 半年度持仓 + CRSP 收益 + 19 个基准指数。结论：高 Active Share 基金长期跑赢，且并非高费率。</p>

<h4>② Kacperczyk, Sialm &amp; Zheng (2005, JF) — 行业集中度 ICI</h4>
<div class="formula">ICI = Σⱼ₌₁¹⁰ (w_j − w̄_j)²　（10 个行业权重相对市场权重的平方偏差和，市场调整后 Herfindahl）</div>
<p>数据来源： Thomson + CRSP；样本 1,771 只基金，ICI 均值 5.98%。用于度量"行业层主动集中度"。</p>

<h4>③ 寇宗来等 (2020, 金融研究) — 风格漂移 Fsds（Sharpe 强式模型）</h4>
<div class="formula">Fsds1_i,t = Σ |w*_imt − w*_im(t−1)|　（基于 Sharpe 强式风格模型估计的风格权重，相邻期绝对变化之和）</div>
<div class="formula">业绩排名 Frk（标准化排名，0–1）；logit(Fchgm) 含 Frk×Schg 交互（业绩差→风格漂移↑→离职↑）</div>
<p>数据来源： Wind；2008–2017 季度，21,624 基金-季度、1,579 只基金。Fsds1 均值 0.298。这是国内"业绩→风格漂移→离职"链条的标杆设定。</p>

<h4>④ 易力 &amp; 盛冰心 (2021) — 风格漂移 SDS（Sharpe 多因素风格分析）</h4>
<div class="formula">R_t = Σ w_i·S_i,t + ε，Σw_i=1，w_i≥0（Sharpe 多因素模型估计风格权重）</div>
<div class="formula">SDS = √(Σ Var(w_i))　；SDAR = SDS2 / SDS1（&gt;1 表示漂移上升）</div>
<p>数据来源： 锐思 + 中信标普 A 股风格指数；2006–2019，5,068 观测。</p>

<!-- 主题三 -->
<h3>主题三　交易行为与隐形交易（L3：刻画"动态交易如何演进"）</h3>
<div class="note">刻画披露间歇期的隐性调仓。Return Gap 是"隐形交易"的标杆指标（Kacperczyk et al. 2008），国内延伸为申宇等 (2013) 的 ARG；持仓期限用 Lan et al. (2015) 的 Holding Horizon。</div>

<h4>① Kacperczyk, Sialm &amp; Zheng (2008, RFS) — Return Gap【推荐首选】</h4>
<div class="formula">RG = (RF − EXP) − RH</div>
<p>其中 RF = 基金投资者净收益（扣费后），RH = 按<b>上一期披露持仓</b>构建的买入持有组合毛收益，EXP = 费用率。RG 反映"披露日之后隐形交易"的净效应（RG&gt;0 表示隐形交易创造了超额收益）。</p>
<p>数据来源： CRSP + 前期披露持仓；样本次年 RG 排序组合检验持续性。</p>

<h4>② 申宇等 (2013) — 修正隐形交易 ARG</h4>
<div class="formula">ARG = Σₜ | R − (RH − Fee) |，Fee = 1.5% + 0.25%（年化）</div>
<p>对半年内各期"绝对收益缺口"加总，纠正正负抵消导致的低估。数据来源： RESSET（锐思）；N=8,662，328 只基金，2005–2010；ARG 均值 0.4112。</p>

<h4>③ Lan, Moneta &amp; Wermers (2015) — 持有期限 Holding Horizon</h4>
<div class="formula">单股持仓期 h = s − k（建仓期 k 到清仓期 s）；基金 HH = Σᵢ ωᵢ·hᵢ（市值加权）；Simple / Ex-Ante 两法</div>
<p>数据来源： Thomson 持仓；用于检验"长期持有 vs 频繁换手"与业绩、风格的关系。</p>

<h4>④ Grinblatt, Titman &amp; Wermers (1995) — 动量 LOM/LIM 与羊群 LSV（基金交易风格）</h4>
<div class="formula">动量 LOM：M = (1/40)ΣτΣⱼ (w_{j,3τ−3} − w_{j,3τ−6})·R_{j,3τ−3+k+1}（k=1→LOM，k=2→LIM，经换手调整→TALOM）</div>
<div class="formula">羊群 LSV：pᵢ = Bᵢ/(Bᵢ+Sᵢ)；UHM = |pᵢ − p̄| − E|pᵢ − p̄|（无符号羊群）</div>
<p>数据来源： CRSP 持仓/收益。这是"基金交易行为"度量（动量/羊群）的元方法，被后续 L5 羊群文献广泛沿用。</p>

<!-- 主题四 -->
<h3>主题四　锦标赛与风险调整（L4：刻画"排名压力下的风险应对"）</h3>
<div class="note">刻画年中排名压力如何驱动风险调整。锦标赛假说的奠基是 Brown, Harlow &amp; Starks (1996) 的 RAR 指标；国内权威为肖继辉 (2012/2013) 与山立威 &amp; 王鹏 (2012)。</div>

<h4>① Brown, Harlow &amp; Starks (1996, JF) — 风险调整比率 RAR【推荐首选】</h4>
<div class="formula">锦标赛假说：(σ2_L / σ1_L) &gt; (σ2_W / σ1_W)　（下半年/上半年回报标准差之比；输家组上升 &gt; 赢家组）</div>
<div class="formula">回归：Δσ_it = β₀ + β₁·LOSERᵢ + β₂·POSTₜ + β₃·LOSER×POST + Controls + ε</div>
<p>数据来源： Wiesenberger + CRSP；1976–1991，334 只成长型共同基金。这是"锦标赛→风险调整"的全部后续中文文献（肖继辉、山立威、李学峰 2010 等）的方法源头。</p>

<h4>② 肖继辉 (2012, 南开管理评论) / 管睿、肖继辉 (2013) — 行业锦标赛 RTN 与排名百分位</h4>
<div class="formula">RTN = Nₐ/N_b × Π(1 + Dᵢ/Nᵢ) − 1　（考虑分红的复权净值增长率）</div>
<div class="formula">△RNTPERC = 后半年排名百分位 − 前半年排名百分位（排名落差，锦标赛激励强度）</div>
<div class="formula">RAR（日度）= [1/(D_y−D)·Σ(r−r̄)²]^{1/2} / [1/(D−1)·Σ(r−r̄)²]^{1/2}</div>
<p>数据来源： Wind + 国泰安；2005–2008，按输/中/赢分组检验风险调整，并引入经理特征×排名、公司治理×排名交互。</p>

<h4>③ 山立威 &amp; 王鹏 (2012) — 年度排名与冒险行为</h4>
<div class="formula">RTN_{iMy} = Π(1 + Ret_{imy}) − 1；RAR = Sd2 / Sd1（下半年/上半年标准差比）</div>
<p>数据来源： CSMAR + RESSET；2005–2010，862 基金-年度。结论：年度排名靠后经理显著加大风险（冒险行为）。</p>

<h4>④ 李祥文 &amp; 吴文锋 (2018, 管理世界) — 期末业绩拉升 Pumping</h4>
<div class="formula">Pumping = Σ(k=0~2) FundPerf(T, lastday−k) / 3　（期末最后 3 日平均业绩）</div>
<div class="formula">Reversing = Σ(k=0~2) FundPerf(T+1, firstday+k) / 3　（次期初 3 日）</div>
<div class="formula">Blip = (Pumping − Reversing) / 2　（拉升净效应）；Flow = (TNA_T − TNA_{T−1}(1+FundRt_T))/TNA_{T−1}</div>
<p>数据来源： 基金净值/分红（复权）；Pumping_FF 均值 6.47 bp，Blip_FF 均值 5.32 bp。刻画"排名临界点的窗口操纵"。</p>

<h4>⑤ 许林等 (2020) — 暴跌风险 NCSKEW/DUVOL 与社会网络</h4>
<div class="formula">NCSKEW = −[n(n−1)^{3/2}·ΣW³] / [(n−1)(n−2)(ΣW²)^{3/2}]，W = 特有收益率（市场模型残差取对数）</div>
<div class="formula">DUVOL = log[(n_u−1)·Σ_down W²] / [(n_d−1)·Σ_up W²]；CSAD = (1/N)·Σ|r_i − r_m|（羊群代理）</div>
<div class="formula">相对点中心度 Nrm_Degree = Σⱼ friⱼ/(M−1)；Orth-Nrm_Degree = 回归残差（剔除 Rank 影响）</div>
<p>数据来源： Wind + 简历；NCSKEW 均值 1.713，DUVOL 均值 2.040。将"排名 + 社会网络→羊群→暴跌风险"串成链条。</p>

<!-- 主题五 -->
<h3>主题五　羊群行为（L5：机构/基金同向交易）</h3>
<div class="note">羊群度量的元方法是 Lakonishok, Shleifer &amp; Vishny (1992) 的 LSV，以及 Wermers (1999) 的基金羊群 BHM/SHM。中文文献几乎全部为 LSV 的修正应用。</div>

<h4>① Lakonishok, Shleifer &amp; Vishny (1992, JFE) — LSV 羊群测度【推荐首选】</h4>
<div class="formula">HM = |p − E[p]| − E|p − E[p]|，其中 p = B/(B+S)（买入/卖出基金占比）</div>
<p>E[p] 取同期全市场买卖比；AF = E|p−E[p]| 在"独立交易"零假设下由二项分布 B(n_F, p̄) 求得。HM&gt;0 即存在同向偏离随机水平的羊群。</p>
<p>数据来源： SEI 769 只免税（养老金）基金季度持仓；1985–1989。</p>

<h4>② Wermers (1999, JF) — 共同基金羊群 BHM/SHM</h4>
<div class="formula">HM_{i,t} = |p_{i,t} − E[p_{i,t}]| − E|p_{i,t} − E[p_{i,t}]|</div>
<div class="formula">BHM = HM | p&gt;E[p]（买方羊群）；SHM = HM | p&lt;E[p]（卖方羊群）</div>
<p>数据来源： CDA 基金季度持仓 + CRSP；1975–1994。发现羊群买入股票未来 6 个月跑赢卖出约 4%。</p>

<h4>③ 中文 LSV 修正应用（代表性）</h4>
<table>
<thead><tr><th>文献</th><th>样本</th><th>核心设定</th><th>主要发现</th></tr></thead>
<tbody>
<tr><td>祁斌等 (2006)</td><td>2000H1–2005H1，54–105 只基金/期</td><td>LSV-Wermers；HM=8.1%</td><td>远高于美国(2.5–3.4%)；BHM&gt;SHM；成长型最显著</td></tr>
<tr><td>吴福龙等 (2004)</td><td>2000–2001 中报/年报</td><td>LSV；扩展三项分布 Buy/Sell/Both</td><td>卖方羊群更显著；基金家数越多 HM 越高</td></tr>
<tr><td>魏立波 (2010)</td><td>2006Q1–2009Q1，139 只偏股型</td><td>修正 LSV；HM 均值 16.77%</td><td>BHM(19.46%)&gt;SHM(15.18%)；小盘股 HM 最高</td></tr>
<tr><td>李奇泽等 (2013)</td><td>2006Q1–2012Q2，333+50 只</td><td>LSV + PCM 组合变动</td><td>开放式&gt;封闭式；创业板板块效应最强(0.263)</td></tr>
</tbody></table>
<div class="note">中文文献一致的"配方"：HM=|P−E(P)|−AF；BHM/SHM 按买卖方向拆分；AF 由二项分布调整；参与基金数≥N 才保留样本。可直接沿用此框架。</div>

<!-- 主题六 -->
<h3>主题六　处置效应（L5：盈利过早卖、亏损久持有）</h3>
<div class="note">处置效应的标准度量是 Odean (1998) 的 PGR/PLR；理论根基是 Shefrin &amp; Statman (1985) 与前景理论；Grinblatt &amp; Han (2005) 将其资产定价化（PPD）。国内权威为李学峰 (2011/2013) 与陆蓉等 (2022)。</div>

<h4>① Odean (1998, JF) — PGR / PLR / DISP【推荐首选】</h4>
<div class="formula">PGR = 已实现盈利股数 / (已实现盈利股数 + 仍持有的未实现盈利股数)</div>
<div class="formula">PLR = 已实现亏损股数 / (已实现亏损股数 + 仍持有的未实现亏损股数)</div>
<div class="formula">DISP = PGR − PLR（&gt;0 即存在处置效应）</div>
<p>数据来源： 某折扣券商 10,000 账户，1987–1993。DISP 平均显著为正，且不受税收动机解释（损失不卖反而多税）。</p>

<h4>② Shefrin &amp; Statman (1985, JF) — 处置效应理论</h4>
<p>以前景理论 + 心理账户推导：投资者对各股票盈亏分账，应用 S 形价值函数，导致"卖赢持亏"。奠定 DISP 度量的行为学基础。</p>

<h4>③ Grinblatt &amp; Han (2005, JFE) — 前景理论需求（PPD）与资本利得悬垂</h4>
<div class="formula">价值函数：v(z)=z^α (z≥0，凹)；v(z)=−λ(−z)^β (z&lt;0，凸，λ&gt;1 损失厌恶)</div>
<div class="formula">参考价格递推：R_t = (1 − V_t/P_t)·R_{t−1} + (V_t/P_t)·P_t（成交量加权聚合成本基础）</div>
<p>将"未实现资本利得悬垂"作为处置效应的聚合代理，证明可解释动量收益。数据来源： MiniCRSP，1962–1996。</p>

<h4>④ 李学峰等 (2011/2013) — 基金层面处置效应（D = PGR − PLR）</h4>
<div class="formula">D_{j,k} = PGR_{j,k} − PLR_{j,k}；PGR=实现盈利/(实现盈利+账面盈利)；PLR=实现亏损/(实现亏损+账面亏损)</div>
<div class="formula">前景理论价值函数（李学峰 2011 校准）：v(x)=x^{0.88} (x≥0)，−2.25(−x)^{0.88} (x&lt;0)</div>
<div class="formula">绩效检验：Sharpe_{i,t} = β₀ + β₁·D_{i,t}·I(D&gt;0) + … + ε（处置效应系数 β=−0.0447**，显著负向）</div>
<p>数据来源： Wind；2003Q1–2010Q4，8,394 基金-季度（2011）；2007Q1–2012Q2，69 只基金（2013）。</p>

<h4>⑤ 陆蓉、李金龙、陈实 (2022, 管理世界) — 投资者处置效应画像</h4>
<div class="formula">OLS：Sell = β₀ + β₁·Gain + Controls + ε（Gain=持股收益指示）</div>
<div class="formula">断点回归：Sell = β₀ + β₁·Gain + β₂·Zero + β₃·Holding_Days + …（捕捉不对称 V 形）</div>
<p>数据来源： 某大型券商 14.76 万 A 股账户、2,687 万条观测（2011–2017）。发现处置效应呈不对称 V 形（扳本偏好 + 盈亏敏感性差异）。可与基金数据对比。</p>

<!-- 主题七 -->
<h3>主题七　过度自信与前景理论（L5：认知偏差的个体来源）</h3>

<h4>① Barber &amp; Odean (2001, QJE) — 性别与过度自信</h4>
<div class="formula">过度自信代理 = 交易频率 turnover = 期内卖出金额 / 平均组合市值</div>
<div class="formula">净收益 = 毛收益 − 交易成本（扣除成本后，过度交易者跑输买入持有）</div>
<p>数据来源： 35,000+ 家庭账户，1991–1997。男性交易频率比女性高约 45%；过度交易显著损害净收益。</p>

<h4>② Kahneman &amp; Tversky (1979, Econometrica) — 前景理论价值函数</h4>
<div class="formula">V = π(p)·v(x) + π(q)·v(y)；v(x)=x^α (x&gt;0，凹)，v(x)=−λ(−x)^β (x&lt;0，凸，λ&gt;1)</div>
<p>这是全部"损失厌恶→风险承担/处置效应/赌博式交易"度量的理论基础。在基金研究中常用于解释排名压力下的非线性风险偏好（如主题四的 RAR 在输家组的放大）。</p>

<h4>③ Puetz &amp; Ruenzi (2008, CFR) — 基金经理过度自信</h4>
<p>以"过度交易/换手率偏高 + 集中持仓"作为基金经理过度自信的行为代理，实证其损害风险调整后业绩。可补充 Barber &amp; Odean 的"交易频率"代理。</p>

<!-- 主题八 -->
<h3>主题八　方法论与识别检验（M：模型设定与因果识别）</h3>
<div class="note">本主题为论文的"方法引擎"：因子模型用于业绩归因，Fama-MacBeth 用于横截面检验，多向聚类/系数稳定性/遗漏变量敏感性用于稳健性。</div>

<h4>① Fama &amp; MacBeth (1973, JPE) — 两步回归【推荐首选·横截面】</h4>
<div class="formula">第一步（时间序列）：R_pt = γ₀ₜ + γ₁ₜ·β_{p,t−1} + γ₂ₜ·β² + γ₃ₜ·s(e) + η_pt</div>
<div class="formula">第二步（横截面）：对每月 γ 系数均值做 t 检验：t(γ̄) = γ̄ / [s(γ)/√n]（修正残差横截面相关）</div>
<p>数据来源： CRSP，1926–1968。这是所有"基金经理特征→业绩"横截面回归的标准估计框架。</p>

<h4>② Fama &amp; French (1993 / 2015) 与 Carhart (1997) — 因子模型【推荐首选·业绩归因】</h4>
<div class="formula">三因子：R−RF = α + b·(RM−RF) + s·SMB + h·HML + e</div>
<div class="formula">五因子(2015)：+ r·RMW（盈利） + c·CMA（投资）</div>
<div class="formula">四因子(Carhart 1997)：+ p·PR1YR（动量）；PR1YR = 过去11月收益最高30%等权 − 最低30%等权（跳过1月，每月重构）</div>
<p>数据来源： CRSP + Compustat + Ken French 因子库。Carhart 四因子 α 是国内基金"业绩/能力"度量的事实标准（Jiang &amp; Verardo 2013、申宇 2013 等均用）。</p>

<h4>③ Jegadeesh &amp; Titman (1993, JF) — 动量因子构建</h4>
<div class="formula">J/K 策略：每月按过去 J 月收益排序十分位，买赢家(top)、卖输家(bottom)，持有 K 月</div>
<p>最优 12/3 策略月均收益 1.49%；收益来源为公司层面收益序列相关（反应不足），非系统性风险。</p>

<h4>④ Cameron, Gelbach &amp; Miller (2011, JBES) — 多向聚类稳健标准误</h4>
<div class="formula">双向：V̂(β) = (X'X)⁻¹[S_G + S_H − S_{G∩H}](X'X)⁻¹；M 向推广同理</div>
<p><b>对本论文至关重要</b>：基金数据同时聚于"基金经理"与"时间/基金"维度，必须用双向（经理×时间）聚类，否则标准误严重低估。直接沿用此框架。</p>

<h4>⑤ Oster (2019, JBES) — 系数稳定性（不可观测选择）</h4>
<div class="formula">β* = β̃ − δ(β̂ − β̃)·(R_max − R̃)/(R̃ − R̂)；建议 R_max = 1.3·R̃；Stata: psacalc</div>
<p>用于回答"不可观测的经理能力/动机是否会推翻核心结论"——给定可观测控制能解释的方差，反推需要多强的遗漏变量才能推翻结果。</p>

<h4>⑥ Cinelli &amp; Hazlett (2020, JRSSB) — 遗漏变量敏感性（sensemakr）</h4>
<div class="formula">偏误因子 BF = √(R²_{Y~Z|D,X}·R²_{D~Z|X} / (1−R²_{D~Z|X}))；鲁棒性值 RV_q = ½(√(f⁴+4f²) − f²)，f = q·|f_{Y~D|X}|</div>
<p>R 包 <code>sensemakr</code> 自动化。用于量化"需要多强的混杂因素才能使处理效应减半/归零"，是 Oster 的可视化升级。</p>

<div class="note"><b>本论文方法建议组合</b>：因子模型（Carhart 四因子 α 作业绩/能力 Y）→ Fama-MacBeth 横截面（特征→业绩）→ 双向聚类（经理×时间）→ Oster / sensemakr 稳健性。这一组合可直接支撑"背景特征→行为→业绩"全链条的识别。</div>
'''

# ============================================================
# 组装：注入 L4/L5/M 章节 + Part B，更新标题/TOC/CSS
# ============================================================
# CSS 增加 L4/L5/M 标签色
css_add = """
    :root{ --l4:#6b3fa0; --l5:#0d7a8a; --lm:#c2410c; }
    .l4{background:var(--l4)} .l5{background:var(--l5)} .lm{background:var(--lm)}
    .topic{color:var(--brand2);font-size:13px;margin:4px 0 8px}
    .section{margin:8px 0}
    .sec-label{font-size:12.5px;font-weight:600;color:var(--brand);margin-bottom:4px}
    .vdef{color:var(--fg)}
"""
base = base.replace("  --l3:#9a4b00;\n", "  --l3:#9a4b00;\n" + css_add)

# 更新标题与元信息
base = base.replace(
    "<title>基金经理投资行为画像 — 变量指标体系汇总（L1/L2/L3）</title>",
    "<title>基金经理行为分析 — 变量指标与构建方法全解（L1–L5 + M）</title>")
base = base.replace(
    "基于 L1 背景特征层 · L2 持仓偏离层 · L3 交易行为层 三层级文献的系统梳理",
    "基于 L1 背景特征层 · L2 持仓偏离层 · L3 交易行为层 · L4 风险应对层 · L5 认知行为层 · M 方法论层 六层级文献的系统梳理")
base = base.replace(
    "文献覆盖：L1 背景特征层 53 篇、L2 持仓偏离层 15 篇、L3 交易行为层 14 篇（合计 82 篇 PDF）",
    "文献覆盖：L1 53 篇 · L2 15 篇 · L3 14 篇 · L4 23 篇 · L5 82 篇 · M 11 篇（合计 198 篇 PDF）")

# 更新 TOC：追加 L4/L5/M 与 Part B 锚点
toc_add = '''
  <a href="#s8">八、L4 风险应对层变量明细</a>
  <a href="#s9">九、L5 认知行为层变量明细</a>
  <a href="#s10">十、M 方法论层变量明细</a>
  <a href="#s11">十一、核心变量构建方法精要（最佳参考文献）</a>'''
base = base.replace('<a href="#s7">七、附录：文献清单与可用性</a>',
                     '<a href="#s7">七、附录：文献清单与可用性</a>' + toc_add)

# 注入章节到 footer 之前
l4_sec = f'<h2 id="s8">八、L4 风险应对层变量明细（共 {len([r for r in records if r.get("layer")=="L4"])} 篇）</h2>\n' + layer_html["L4"]
l5_sec = f'<h2 id="s9">九、L5 认知行为层变量明细（共 {len([r for r in records if r.get("layer")=="L5"])} 篇）</h2>\n' + layer_html["L5"]
m_sec  = f'<h2 id="s10">十、M 方法论与识别检验层变量明细（共 {len([r for r in records if r.get("layer")=="M"])} 篇）</h2>\n' + layer_html["M"]

inject = l4_sec + l5_sec + m_sec + PARTB
base = base.replace("<footer>", inject + "\n<footer>")

# 更新页脚
base = base.replace("文件：变量指标_8.11_01.html / .docx",
                    "文件：基金经理行为分析_变量指标与构建方法全解_L1-L5+M.html ｜ 合并 L1–L3 参考 + L4/L5/M 提取，并新增核心变量构建方法精要")

out = os.path.join(BASE, "基金经理行为分析_变量指标与构建方法全解_L1-L5+M.html")
with open(out, "w", encoding="utf-8") as fh:
    fh.write(base)
print("已写出:", out, "大小:", os.path.getsize(out), "字节")
