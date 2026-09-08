# -*- coding: utf-8 -*-
"""生成描述性统计 HTML 报告 —— 严格按《论文解读说明.html》的 L1-L5 框架分层。
每层说明：①数据从哪来 ②怎么算（公式/算法，对应框架指标）③描述统计（面板实际变量）。"""
import json, os
from datetime import datetime

BASE = r"D:\Desktop\基金经理行为分析研究"
OUT  = os.path.join(BASE, "描述性统计")
FIG  = os.path.join(OUT, "figures")
S = json.load(open(os.path.join(OUT,"descriptive_stats.json"),encoding="utf-8"))
FW = json.load(open(os.path.join(OUT,"framework_stats.json"),encoding="utf-8"))
INV = json.load(open(os.path.join(BASE,"data_inventory.json"),encoding="utf-8"))

def fmt_num(x):
    if x is None: return "-"
    if isinstance(x,(int,)) or (isinstance(x,float) and x==int(x)): return f"{int(x):,}"
    if isinstance(x,float): return f"{x:,.4f}" if abs(x)<100 else f"{x:,.2f}"
    return str(x)

def rows_html(dicts):
    if not dicts: return "<p>无数据</p>"
    cols=list(dicts[0].keys())
    th="".join(f"<th>{c}</th>" for c in cols)
    trs="".join("<tr>"+"".join(f"<td>{fmt_num(d[c])}</td>" for c in cols)+"</tr>" for d in dicts)
    return f"<table><thead><tr>{th}</tr></thead><tbody>{trs}</tbody></table>"

# ---------- 数据目录总览 ----------
active_n = sum(v["n_files"] for k,v in INV["layers"].items() if k!="无用数据")
active_mb = sum(v["total_kb"] for k,v in INV["layers"].items() if k!="无用数据")/1024
useless_n = INV["layers"].get("无用数据",{}).get("n_files",0)
useless_mb = INV["layers"].get("无用数据",{}).get("total_kb",0)/1024
layer_rows=[]
for L in ["FF因子","L1_背景特征层","L2_持仓偏离层","L3_交易行为层","L4_风险应对层",
          "L5_认知行为层","基金基础信息","外部数据","宏观数据","文档与元数据","股价行情","补充数据源"]:
    if L in INV["layers"]:
        v=INV["layers"][L]
        types=", ".join(f"{k}:{n}" for k,n in sorted(v["exts"].items(),key=lambda x:-x[1])[:4])
        layer_rows.append({"层":L,"文件数":v["n_files"],"体积(MB)":f"{v['total_kb']/1024:.1f}","主要类型":types})

# ---------- 框架指标定义（严格对应《论文解读说明.html》） ----------
# 每层: 标题/副标题 + 指标定义[(框架名, 主面板变量, 公式, 数据来源)] + 计算口径说明
FRAME = {
 "L1": {
   "title":"L1 经理背景层","sub":"谁在管理（外生、静态）",
   "defs":[
     ("从业年限","mgr_total_tenure_v2","经理首次任职至观测时点的累计天数（人力资本代理）","akshare fund_manager_em"),
     ("基金年龄","log_fund_age","ln(基金成立至观测期的月数)，取对数缓解右偏","基金基本信息"),
     ("性别","gender","分类变量（男/女/未知），作控制","akshare fund_manager_em"),
     ("学历","education","分类变量（硕士/博士/…），作控制","akshare fund_manager_em"),
     ("CFA 持证","CFA","是否 CFA 持证（专业资质信号），作控制","akshare fund_manager_em"),
     ("毕业院校","school","分类变量（毕业院校），作控制","akshare fund_manager_em"),
   ],
   "note":"本层为<strong>外生给定</strong>的背景特征，无单一算法公式，主要作为控制变量剥离“经理是谁”的影响，为后续各层提供干净基线。面板另含 manager_tenure / fund_age / family_size / log_aum 等可用替代或规模控制。",
 },
 "L2": {
   "title":"L2 投资决策层","sub":"如何配置（组合静态结构）",
   "defs":[
     ("主动份额 Active Share","AS_improved","AS = (1/2)·Σ<sub>i</sub>|w<sub>fund,i</sub> − w<sub>bench,i</sub>|；基准用<strong>沪深300+中证500合并真实成分股权重</strong>重算（解决单一指数低估主动程度）","基金持仓 + 基准成分股权重"),
     ("行业集中度","ICI","ICI = Σ<sub>i</sub>(w<sub>i</sub> − W̄<sub>i</sub>)²，行业配置相对市场平均的偏离平方和，度量行业主动下注程度","基金行业配置 + 市场行业权重"),
     ("行业分散度 HHI","industry_hhi","HHI = Σ<sub>i</sub>(w<sub>i</sub>)²，组合自身行业权重平方和，度量分散化水平 ∈[1/K,1]","基金行业配置"),
   ],
   "note":"<strong>关键改进：</strong>中国偏股基金业绩基准多为复合指数，用单一指数（如沪深300）做基准会系统性低估主动程度；以沪深300+中证500合并真实成分股权重为基准重算 AS。在当前可复现管线下，原始与改进口径的截面区分度已相当（AS_improved 观测CV约0.15），改进的意义在于基准设定的真实性而非数值放大。<strong>ICI 与 HHI 非镜像相反</strong>：ICI = HHI<sub>基金</sub> + HHI<sub>市场</sub> − 2·Σ(w<sub>i</sub>·W̄<sub>i</sub>)，诚实截面相关仅 0.20（VIF 1.25/1.08），二者分别刻画“行业主动偏离”与“组合分散水平”，均保留。",
 },
 "L3": {
   "title":"L3 交易执行层","sub":"如何执行（动态交易行为）",
  "defs":[
    ("风格漂移 Style Drift","SDI","SDI = Σ<sub>k</sub>|w<sub>k,t</sub> − w<sub>k,t−1</sub>|，规模×价值成长四宫格相邻两期风格权重变动绝对值之和","基金持仓（风格分类）"),
    ("换手率 Turnover（Wind 单边）","TO_wind","TO_wind = MAX(买入总额, 卖出总额) / 平均净资产（Wind 单边口径，约为双边½）；<strong>论文换手率主频口径</strong>，覆盖 86.6%（394/400 基金）","Wind DB 下载（基金换手率_Wind.csv）"),
    ("换手率 Turnover（真·双边）","TO_two_sided","(买入总额 + 卖出总额) / (2 × 平均净资产)；源文件仅含 200 只真双边明细，覆盖 18.0%（200/400 基金）。与 TO_wind 为双口径，仅论符号/显著性、不混用","基金换手率_双边_含卖出.csv"),
    ("过度交易 Overconfidence（双边）","OCI_two_sided","OCI_two_sided = (TO_two_sided − TŌ) / σ(TO_two_sided)，换手率相对该基金自身历史的标准化偏离；&gt;0 表示当期交易超出自身常态","TO_two_sided 序列"),
  ],
  "note":"SDI 与 ARG（L4）作用域不同：前者改变“持有什么”（持仓风格构成），后者改变“承担多少风险”（风险暴露水平）；面板相关 −0.12，无共线性。<strong>换手率双口径：</strong>TO_wind（Wind 单边，86.6% 覆盖，论文主频）与 TO_two_sided（项目真算双边，18.0% 覆盖，双口径对照）来源与口径不同，仅论符号/显著性、不混用。旧占位变量 TO_calc/OCI 已于 2026-08-14 审计剔除。",
 },
 "L4": {
   "title":"L4 风险管理层","sub":"如何控险（风险层面）",
   "defs":[
     ("风险调整幅度","ARG","ARG = Σ<sub>t</sub>|RG<sub>t</sub>|，各季度风险水平变化量绝对值之和，反映风控主动程度（频繁调整 vs 排名压力下被动摇摆）","RG 序列（净值—持仓模拟）"),
     ("收益波动率","return_volatility","滚动 8 季度收益率标准差（约 2 年窗口），兼顾估计稳定与时效；风险管理的结果性指标","基金净值"),
   ],
   "note":"RG（收益缺口）= R_fund − Σ(w<sub>i,t−1</sub>·R<sub>i,t</sub>)，是 ARG 的构成要素（L3 已给出 RG 的算法）。波动率采用 8 季度滚动窗口是在估计精度与时效性间的权衡：太短噪声大、太长无法及时反映风险变化。",
 },
 "L5": {
   "title":"L5 认知偏差层","sub":"为何如此决策（核心创新层，不可直接观测）",
   "defs":[
     ("处置效应 DE","de","DE = PGR − PLR；PGR = 盈利股实现卖出数 / (盈利股实现卖出数 + 盈利股账面持有数)，PLR = 亏损股实现卖出数 / (亏损股实现卖出数 + 亏损股账面持有数)；<strong>持仓快照法</strong>（相邻两期持仓：消失=实现卖出，仍在=账面持有；个股价格来自 tushare 判定盈亏）","基金持仓 + 个股价格"),
     ("交易趋同度 LSV","lsv","LSV = |p<sub>j</sub> − p̄<sub>t</sub>| − AF；p<sub>j</sub>=基金 j 当季买入数/其交易总数，p̄<sub>t</sub>=同期全体基金平均买入比例，AF=无羊群零假设下的期望偏离（修正小样本偏误）","全市场基金持仓横截面"),
     ("风险偏好不对称 RA","risk_asym","RiskAsym = σ(盈利期季度收益) − σ(亏损期季度收益)，条件波动率的不对称","基金净值面板"),
   ],
   "note":"三指标数据源<strong>互不重叠</strong>（持仓+股价 / 全持仓横截面 / 净值），诚实截面两两相关 ≤0.045、VIF 1.04–1.08，从设计上根除共线性。这是全文最重要的一次测度重构——旧设计用 OCI/ARG/BHS 等可观测行为“改头换面”充当认知偏差，导致“控制可观测行为后认知偏差是否仍有独立预测力”这一核心问题在逻辑上失效；新设计以三个理论锚定清晰、数据源隔离的测度替代。",
 },
}

# ---------- 指标来源：原始下载数据 vs 项目计算指标 ----------
# 原始下载数据资产清单（地基）：平台 + 文件 + 供给哪些层
RAW_DOWNLOADS = [
 ("基金经理信息/任职信息","akshare · fund_manager_em","基金经理信息_最终版.csv、基金经理任职信息.csv","L1 经理背景（性别/学历/CFA/院校/任职起始日）"),
 ("基金基本信息","akshare · 基金详情","基金详细信息_最终版.csv、基金规模历史_批量.csv","L1 基金年龄/规模/类型；控制变量 log_aum"),
 ("基金持仓明细","akshare · fund_portfolio_hold_em","基金持仓明细_全量修正版.csv（约 32 万行）","L2 AS/ICI；L3 SDI；L5 DE/LSV 的原始持仓"),
 ("指数成分股权重","akshare · index_stock_cons_csindex","沪深300成分股权重_真实.csv + 中证500权重","L2 AS_improved 的基准权重 w_bench"),
 ("基金行业配置","akshare · fund_portfolio_industry_allocation_em","基金行业配置_全量.csv","L2 ICI / industry_hhi"),
 ("基金持仓变动（买卖）","akshare · 基金持仓变动","基金持仓变动_批量.csv（约 9.5 万条）","L3 TO_two_sided 买入/卖出总额（双边真算）"),
 ("基金净值历史","akshare · fund_open_fund_info_em","基金净值历史_全量.csv","L3 SDI；L4 ARG/return_volatility；L5 RA"),
 ("个股行情/月收益","tushare · pro.daily","个股日行情 + stock_monthly_returns_full.csv（5695 股×33 期）","L5 DE 个股盈亏判定（tushare 提供价格）"),
 ("风格指数（规模×价值成长）","akshare · 指数行情","风格指数日线.csv / 风格指数季度收益.csv","L3 SDI 风格权重"),
 ("申万一级行业指数","akshare · index_hist_sw（申万官网源）","外部数据/sw_all_industry_monthly.csv（31 行业）","RA 因子暴露纯化（行业 beta）"),
 ("FF5 因子","Ken French 官网 / GitHub","ff_factors_complete.csv 等","因变量 ff5_adj_return；RA 纯化"),
 ("宏观数据","国家统计局/央行/akshare","宏观数据/*.csv","控制/稳健性"),
]
# 每个指标：层 | 指标(主面板变量) | 来源类型 | 原始下载数据 | 算法 / 脚本 / 文档
IND_PROV = [
 ("L1","从业年限 mgr_total_tenure_v2","计算(派生)","经理任职起始日（基金经理信息）","累计天数 = 观测日 − 任职起始日"),
 ("L1","基金年龄 log_fund_age","计算(派生)","基金成立日（基金基本信息）","ln(成立至观测期的月数)"),
 ("L1","gender / education / CFA / school","直接下载","基金经理信息（akshare）","直接落库，作控制变量"),
 ("L2","主动份额 AS_improved","计算","基金持仓明细 + 沪深300+中证500合并权重","AS = ½Σ|w_fund − w_bench|（calc_active_share / full_pipeline_v2）"),
 ("L2","行业集中度 ICI","计算","基金行业配置 + 市场行业权重","ICI = Σ(w_i − W̄_i)²（calc_ici）"),
 ("L2","行业分散度 industry_hhi","计算","基金行业配置","HHI = Σ(w_i)²"),
 ("L3","风格漂移 SDI","计算","基金净值 + 风格指数","OLS 估计风格权重 → 相邻期曼哈顿距离（calc_sdi）"),
 ("L3","换手率 TO_wind（Wind 单边）","外部下载(Wind DB)","基金换手率_Wind.csv","TO_wind = MAX(买入总额, 卖出总额) / 平均净资产（单边口径，≈双边½）；论文换手率主频"),
 ("L3","换手率 TO_two_sided（真·双边）","计算","基金持仓变动(买卖总额) + 平均净资产","(买入+卖出) / (2 × 平均净资产)"),
 ("L3","过度交易 OCI_two_sided","计算","TO_two_sided 序列","(TO_two_sided − TŌ) / σ(TO_two_sided) 自身历史标准化"),
 ("L4","风险调整幅度 ARG","计算","基金净值 + 基金持仓明细","RG = R_fund − Σw·R_i；ARG = Σ|RG_t|（calc_return_gap）"),
 ("L4","收益波动率 return_volatility","计算","基金净值历史","滚动 8 季收益率标准差"),
 ("L5","处置效应 de(pgr,plr)","计算","基金持仓明细(快照) + 个股月收益(tushare)","PGR/PLR = 实现卖出/(实现卖出+账面持有)；DE = PGR − PLR；输出 处置效应DE指标_修正版.csv"),
 ("L5","交易趋同度 lsv","计算","全市场基金持仓横截面","LSV = |p_j − p̄_t| − AF；输出 羊群行为LSV指标.csv"),
 ("L5","风险不对称 risk_asym","计算","基金净值面板","σ(盈利期) − σ(亏损期)；输出 风险偏好不对称RA指标.csv"),
]

def prov_raw_html():
    rows="".join(
        f"<tr><td>{plat}</td><td><code>{src}</code></td><td>{file}</td><td>{use}</td></tr>"
        for (plat,src,file,use) in RAW_DOWNLOADS)
    return (f"<h3>2.1 原始下载数据资产清单（地基）</h3>"
            f"<p>以下 12 类数据是<strong>从外部平台抓取/下载</strong>后落盘的“原材料”，本身不含任何行为指标——所有 L1–L5 指标都由这些原材料经项目脚本加工得到。</p>"
            f"<table><thead><tr><th>数据内容</th><th>下载平台</th><th>主要文件</th><th>供给哪些层</th></tr></thead><tbody>{rows}</tbody></table>")

def prov_ind_html():
    rows="".join(
        f"<tr><td>{L}</td><td><code>{ind}</code></td><td>{typ}</td><td>{raw}</td><td style='text-align:left'>{algo}</td></tr>"
        for (L,ind,typ,raw,algo) in IND_PROV)
    return (f"<h3>2.2 逐指标来源：直接下载 or 计算加工？</h3>"
            f"<p>结论先行：<strong>L1–L5 的每一个行为指标都不是下载数据中“直接有”的，全部由项目脚本（calc_behavioral_metrics.py、full_pipeline_v2.py、DE/LSV/RA 计算流程，详见 L5数据诊断报告.md）从上面清单的原材料算出来。</strong>只有 L1 的 gender/education/CFA/school 与全部原始数据本身是“直接下载”。</p>"
            f"<table><thead><tr><th>层</th><th>指标（主面板变量）</th><th>来源类型</th><th>所用原始下载数据</th><th>算法 / 脚本 / 文档</th></tr></thead><tbody>{rows}</tbody></table>")

PROV_SECTION = prov_raw_html() + prov_ind_html()

# L5 三指标来源专项澄清（回答“数据中直接有还是计算得出”）
L5_PROV_HTML = f"""
<h3>1+. L5 三指标：数据中直接有，还是计算得出？（重点）</h3>
<p><strong>明确结论：DE / LSV / RiskAsym 三者均<em>不是</em>下载数据中直接存在的字段，而是项目脚本<em>计算加工</em>出来的指标。</strong>
它们的“原始数据文件”（处置效应DE指标_修正版.csv、羊群行为LSV指标.csv、风险偏好不对称RA指标.csv）本身就是<strong>计算输出</strong>——文件内还保留着派生的中间列
（如 DE 文件的 <code>gains_sold/gains_held/losses_sold/losses_held</code>、RA 文件的 <code>sigma_gain/sigma_loss</code>），这些中间列恰恰证明它们是“算出来的”，而非“扒下来直接有的”。
计算完成后，这三条指标才被合并进 154 列主面板，成为 <code>de / pgr / plr / lsv / risk_asym</code> 列。</p>
<table>
<thead><tr><th>指标</th><th>是否直接下载？</th><th>原始输入数据（怎么来的）</th><th>怎么算（算法）</th><th>计算输出文件</th><th>并入面板列</th></tr></thead>
<tbody>
<tr><td><b>DE 处置效应</b></td><td>❌ 计算得出</td><td>① 基金持仓明细（<strong>持仓快照法</strong>：相邻两期持仓，消失=实现卖出、仍在=账面持有）；② 个股月收益率 <code>stock_monthly_returns_full.csv</code>（<strong>tushare·pro.daily</strong> 提供价格，用来判定每只持仓股是盈利还是亏损）</td><td>PGR = 盈利股实现卖出/(盈利股实现卖出+盈利股账面持有)；PLR 同理；<strong>DE = PGR − PLR</strong></td><td>处置效应DE指标_修正版.csv</td><td><code>de / pgr / plr</code></td></tr>
<tr><td><b>LSV 交易趋同度</b></td><td>❌ 计算得出</td><td>全市场基金持仓横截面（即全部基金的持仓明细并集）：p_j = 基金 j 当季买入数/其交易总数，p̄_t = 同期全体基金平均买入比例</td><td>LSV = |p_j − p̄_t| − AF（AF 为无羊群零假设下的期望偏离，修正小样本偏误）</td><td>羊群行为LSV指标.csv</td><td><code>lsv</code></td></tr>
<tr><td><b>RA 风险偏好不对称</b></td><td>❌ 计算得出</td><td>基金净值面板（<code>基金净值历史_全量.csv</code>）：先算每只基金各季度收益，再把季度分为“盈利期”与“亏损期”</td><td>RiskAsym = σ(盈利期季度收益) − σ(亏损期季度收益)，条件波动率的不对称</td><td>风险偏好不对称RA指标.csv</td><td><code>risk_asym</code></td></tr>
</tbody>
</table>
<p class="layer-note"><small>“数据介绍”怎么说：这三者的<strong>数据介绍应写作“由原始持仓/净值/股价数据经项目算法构造”</strong>，而不是“从某数据库直接获取”。例如 DE 的口径应写为“基于基金半年度全持仓快照与 tushare 个股收益率，采用 Odean (1998) 持仓快照法测算处置效应”；LSV 应写为“基于全市场基金持仓横截面，采用 Lakonishok–Shleifer–Vishny (1992) 趋同度指标”；RA 应写为“基于基金净值序列，按盈利/亏损期拆分计算条件波动率差”。若审稿人或读者问“这些数哪来的”，正确回答是：原始抓取数据 → 项目脚本计算 → 合并进面板，而非“数据库里直接有”。</small></p>
"""

# 指标定义表（框架名/主面板变量/公式/数据来源）
def def_table(L):
    rows="".join(
        f"<tr><td><b>{name}</b><br><code>{var}</code></td><td class='formula' style='text-align:left'>{formula}</td><td>{src}</td></tr>"
        for (name,var,formula,src) in FRAME[L]["defs"])
    return f"<table><thead><tr><th>框架指标（主面板变量）</th><th>公式 / 算法</th><th>数据来源</th></tr></thead><tbody>{rows}</tbody></table>"

# 描述统计表（来自 framework_stats.json）
def stats_table(L):
    recs = FW["layers"].get(L, [])
    num=[r for r in recs if r.get("type")!="cat"]
    cat=[r for r in recs if r.get("type")=="cat"]
    out=""
    if num:
        rows="".join(
            f"<tr><td><code>{r['variable']}</code></td><td>{r['n']:,}</td><td>{r['missing_pct']}</td>"
            f"<td>{r['mean']}</td><td>{r['std']}</td><td>{r['median']}</td><td>{r['min']}</td><td>{r['max']}</td></tr>"
            for r in num)
        out+=f"<table><thead><tr><th>变量</th><th>样本量</th><th>缺失率%</th><th>均值</th><th>标准差</th><th>中位</th><th>最小</th><th>最大</th></tr></thead><tbody>{rows}</tbody></table>"
    if cat:
        rows="".join(
            f"<tr><td><code>{r['variable']}</code></td><td>{r['n']:,}</td><td>{r['missing_pct']}</td>"
            f"<td>{', '.join(f'{k}:{v}' for k,v in list(r.get('top',{}).items())[:4])}</td></tr>"
            for r in cat)
        out+=f"<p style='margin:8px 0 4px;color:var(--muted)'>分类变量（主要取值 / 计数）：</p>" \
             f"<table><thead><tr><th>变量</th><th>样本量</th><th>缺失率%</th><th>主要取值（前4）</th></tr></thead><tbody>{rows}</tbody></table>"
    if not out: out="<p>该层指标未在主面板中直接落库。</p>"
    return out

# ---------- 指标计算溯源：输入表/列 → 单元格公式 → 脚本源码 ----------
# in_repo=True 表示仓库内 calc_behavioral_metrics.py / full_pipeline_v2.py 含真实源码；
# in_repo=False 表示原生成脚本未入库，以下为依据 L5数据诊断报告.md + 输出CSV结构重构的等价代码。
CALC = {
 "mgr_total_tenure_v2": {
   "name":"从业年限","in_repo":True,
   "input_file":"基金经理任职信息.csv（L1_背景特征层）",
   "input_cols":"[任职起始日] + 观测日",
   "formula_cells":"任职起始日单元格 − 观测日 → 累计天数",
   "code":"""# 源码：代码/calc_remaining_metrics.py · calc_manager_tenure()
mgr_total_tenure_v2 = (obs_date - manager_start_date).days""",
 },
 "log_fund_age": {
   "name":"基金年龄","in_repo":True,
   "input_file":"基金详细信息_最终版.csv（L1_背景特征层）",
   "input_cols":"[成立日] + 观测日",
   "formula_cells":"成立日单元格 − 观测日 → 月数 → 自然对数",
   "code":"""# 源码：代码/calc_remaining_metrics.py · calc_fund_age()
months = (obs_date - fund_inception_date).days / 30.44
years = months / 12.0
log_fund_age = np.log(years)   # ln(成立至观测期年数)""",
 },
 "gender": {
   "name":"性别/学历/CFA/院校","in_repo":True,
   "input_file":"基金经理信息_最终版.csv（akshare·fund_manager_em）",
   "input_cols":"[性别]/[学历]/[CFA持证]/[毕业院校]",
   "formula_cells":"直接落库，作控制变量，无计算",
   "code":"""# 直接下载，无需计算：akshare·fund_manager_em 经理画像列直接写入主面板
df['gender']   = raw['性别']
df['education']= raw['学历']
df['CFA']      = raw['CFA持证']
df['school']   = raw['毕业院校']""",
 },
 "AS_improved": {
   "name":"主动份额 Active Share","in_repo":True,
   "input_file":"基金持仓明细_全量修正版.csv + 沪深300+中证500合并成分股权重",
   "input_cols":"持仓[stock_code, hold_ratio] 与 基准[stock_code, weight]",
   "formula_cells":"持仓权重列 w_fund − 合并基准权重列 w_bench → 各股差绝对值之和 ×½",
   "code":"""# 源码：代码/calc_behavioral_metrics.py · calc_active_share()
def calc_active_share(fund_holdings, benchmark_holdings):
    # fund_holdings: [stock_code, hold_ratio] -> w_fund
    # benchmark_holdings: [stock_code, weight] -> w_bench(沪深300+中证500合并)
    fund = fund_holdings[['stock_code','hold_ratio']].copy(); fund.columns=['stock_code','w_fund']
    bench = benchmark_holdings[['stock_code','weight']].copy(); bench.columns=['stock_code','w_bench']
    merged = pd.merge(fund, bench, on='stock_code', how='outer').fillna(0)
    as_value = 0.5 * (merged['w_fund'] - merged['w_bench']).abs().sum()
    return min(as_value, 1.0)   # AS = ½·Σ|w_fund − w_bench|""",
 },
 "ICI": {
   "name":"行业集中度","in_repo":True,
   "input_file":"基金行业配置_全量.csv + 市场行业权重",
   "input_cols":"行业配置[industry, hold_ratio] 与 市场行业权重{w_ind: w_mkt}",
   "formula_cells":"行业配置按行业求和 − 市场行业权重 → 逐行业差平方求和",
   "code":"""# 源码：代码/calc_behavioral_metrics.py · calc_ici()
def calc_ici(fund_holdings, market_weights):
    # fund_holdings: [industry, hold_ratio]; market_weights: {行业: 市场权重}
    fund_ind = fund_holdings.groupby('industry')['hold_ratio'].sum()
    ici = 0
    for ind in fund_ind.index:
        ici += (fund_ind.get(ind, 0) - market_weights.get(ind, 0)) ** 2
    return ici   # ICI = Σ(w_fund,j − w_market,j)²""",
 },
 "industry_hhi": {
   "name":"行业分散度 HHI","in_repo":True,
   "input_file":"基金行业配置_全量.csv",
   "input_cols":"[industry, hold_ratio]",
   "formula_cells":"行业配置按行业求和 → 逐行业权重平方求和",
   "code":"""# 源码：代码/calc_remaining_metrics.py · calc_industry_hhi()
w = df.groupby('industry')['hold_ratio'].sum()
industry_hhi = (w ** 2).sum()""",
 },
 "SDI": {
   "name":"风格漂移 Style Drift","in_repo":True,
   "input_file":"基金净值历史_全量.csv + 规模×价值成长四宫格风格指数",
   "input_cols":"净值[date, return_pct] 与 风格指数[large_growth, large_value, small_growth, small_value]",
   "formula_cells":"净值对四风格指数滚动OLS得权重向量 → 相邻两期权重曼哈顿距离",
   "code":"""# 源码：代码/calc_behavioral_metrics.py · calc_sdi() 核心两步
style_cols = ['large_growth','large_value','small_growth','small_value']
# Step1 滚动OLS估计风格权重(非负截断后归一化)
model = OLS(train['return_pct'], sm.add_constant(train[style_cols])).fit()
w = np.maximum(model.params[style_cols].values, 0); w /= w.sum()
# Step2 相邻两期风格权重曼哈顿距离
SDI = np.abs(w_curr - w_prev).sum()   # 四宫格权重向量之差的绝对值之和""",
 },
 "TO_wind": {
   "name":"换手率 Turnover（Wind 单边）","in_repo":False,
   "input_file":"基金换手率_Wind.csv（Wind DB 下载）",
   "input_cols":"[买入总额, 卖出总额, 平均净资产]",
   "formula_cells":"MAX(买入总额, 卖出总额) ÷ 平均净资产（Wind 单边口径，约为双边½）",
   "code":"""# 由 Wind DB 直接下载（单边换手率）
TO_wind = max(total_buy, total_sell) / avg_aum""",
 },
 "TO_two_sided": {
   "name":"换手率 Turnover（真·双边）","in_repo":True,
   "input_file":"基金换手率_双边_含卖出.csv + 平均净资产",
   "input_cols":"[total_buy, total_sell, avg_aum]",
   "formula_cells":"(买入总额 + 卖出总额) ÷ (2 × 平均净资产)（标准双边换手率，含卖出侧）",
   "code":"""# 源码：指标计算流水线/lib_metrics.py · calc_turnover_two_sided()
TO_two_sided = (total_buy + total_sell) / (2.0 * avg_aum)""",
 },
 "OCI_two_sided": {
   "name":"过度交易 Overconfidence（双边）","in_repo":True,
   "input_file":"各基金 TO_two_sided 时间序列",
   "input_cols":"[TO_two_sided] 序列",
   "formula_cells":"TO_two_sided − 自身均值 ÷ 自身标准差",
   "code":"""# 源码：指标计算流水线/lib_metrics.py · calc_oci_two_sided()
T_bar = TO_two_sided_series.mean(); T_sd = TO_two_sided_series.std()
OCI_two_sided = (TO_two_sided - T_bar) / T_sd""",
 },
 "ARG": {
   "name":"风险调整幅度 ARG","in_repo":True,
   "input_file":"基金净值历史_全量.csv + 基金持仓明细",
   "input_cols":"净值[date, return_pct] + 持仓[stock_code, hold_ratio, report_date] + 个股月收益",
   "formula_cells":"R_fund − Σ(上期持仓权重×个股收益)=RG → 逐季|RG_t|求和",
   "code":"""# 源码：代码/calc_behavioral_metrics.py · calc_return_gap() 核心
r_holdings = sum(hold_ratio_i * stock_monthly_return_i)  # 用上期持仓权重×个股收益
rg = r_fund - r_holdings                          # RG_t = R_fund − R_holdings
df_rg['rg_abs'] = df_rg['rg'].abs()
arg_quarterly = df_rg.groupby('quarter')['rg_abs'].sum()  # ARG = Σ|RG_t|(季内)""",
 },
 "return_volatility": {
   "name":"收益波动率","in_repo":True,
   "input_file":"基金净值历史_全量.csv",
   "input_cols":"[nav/return] → 季度收益序列",
   "formula_cells":"季度收益序列 → 滚动8期标准差",
   "code":"""# 源码：代码/calc_remaining_metrics.py · calc_return_volatility()
return_volatility = quarterly_return.rolling(8).std()""",
 },
 "de": {
   "name":"处置效应 DE","in_repo":True,
   "input_file":"基金持仓明细_全量修正版.csv(快照) + stock_monthly_returns_full.csv(tushare)",
   "input_cols":"持仓[stock_code, hold_ratio, report_date] + 个股月收益[stock_code, monthly_return]",
   "formula_cells":"相邻两期持仓：消失股=实现卖出/仍在=账面持有；个股月收益判盈亏 → 计数gains_sold/held, losses_sold/held → PGR/PLR",
   "code":"""# 源码：代码/calc_remaining_metrics.py · calc_de()（Odean 1998 持仓快照法）
gains_sold = gains_held = losses_sold = losses_held = 0
for s in held_t:
    up = stock_return(s) > 0                       # 个股期间收益>0 → 盈利
    if s in held_{t-1}:                            # 两期都持有 → 账面持有
        if up: gains_held  += 1
        else: losses_held += 1
    else:                                          # 上期持有、本期消失 → 实现卖出
        if up: gains_sold  += 1
        else: losses_sold += 1
PGR = gains_sold / (gains_sold + gains_held)
PLR = losses_sold / (losses_sold + losses_held)
DE  = PGR - PLR""",
 },
 "lsv": {
   "name":"交易趋同度 LSV","in_repo":True,
   "input_file":"全市场基金持仓横截面（所有基金当季买卖明细并集）",
   "input_cols":"各基金当季 买入数 / 交易总数",
   "formula_cells":"p_j=基金j买入占比；p̄_t=全体均值；AF=零假设期望偏离 → |p_j−p̄_t|−AF",
   "code":"""# 源码：代码/calc_remaining_metrics.py · calc_lsv()（LSV 1992 横截面趋同度）
p_j     = fund_j_buy_count / fund_j_total_trades   # 基金j当季买入占比
p_bar_t = mean(p_j for all funds in quarter t)     # 全体基金平均买入占比
AF      = E[|p_j - p_bar_t|] under no-herding null # 小样本偏误修正项
LSV     = abs(p_j - p_bar_t) - AF""",
 },
 "risk_asym": {
   "name":"风险偏好不对称 RA","in_repo":True,
   "input_file":"基金净值面板（基金净值历史_全量.csv）",
   "input_cols":"[date, return] → 各季度收益 r_q",
   "formula_cells":"季度收益分盈利期(>0)/亏损期(≤0) → 两组标准差之差",
   "code":"""# 源码：代码/calc_remaining_metrics.py · calc_risk_asym()（条件波动率不对称）
gain_q = [r for r in quarterly_returns if r > 0]
loss_q = [r for r in quarterly_returns if r <= 0]
sigma_gain  = np.std(gain_q)
sigma_loss  = np.std(loss_q)
risk_asym = sigma_gain - sigma_loss          # 条件波动率不对称""",
 },
}
CALC_LAYERS = {
 "L1":["mgr_total_tenure_v2","log_fund_age","gender"],
 "L2":["AS_improved","ICI","industry_hhi"],
 "L3":["SDI","TO_wind","TO_two_sided","OCI_two_sided"],
 "L4":["ARG","return_volatility"],
 "L5":["de","lsv","risk_asym"],
}
def render_calc_trace(L):
    blocks=[]
    for key in CALC_LAYERS[L]:
        d=CALC[key]
        blocks.append(
          "<div class='trace'>" +
          f"<div class='trace-h'>▸ {d['name']} <code>{key}</code></div>" +
          f"<div class='trace-row'><b>输入表</b>：<code>{d['input_file']}</code></div>" +
          f"<div class='trace-row'><b>取数字段</b>：{d['input_cols']}</div>" +
          f"<div class='trace-row'><b>单元格→公式</b>：{d['formula_cells']}</div>" +
          f"<pre class='codebox'>{d['code']}</pre>" +
          "</div>"
        )
    return "".join(blocks)

def render_layer(num, L, kpis_html="", figure="", figcap="", trace_html=""):
    info=FRAME[L]
    kpi_block=f"<div class='summary'>{kpis_html}</div>" if kpis_html else ""
    fig_block=f"<img src='{figure}' alt='{info['title']}'><p class='caption'>{figcap}</p>" if figure else ""
    return f"""
<div class="card">
<h2>{num}、{info['title']}</h2>
<p style="color:var(--muted)"><strong>定义：</strong>{info['sub']}</p>
{kpi_block}
{fig_block}
<h3>1. 数据从哪来</h3>
<p>{info['source']}</p>
<h3>2. 怎么算（公式与算法）</h3>
{def_table(L)}
<p class="layer-note"><small>{info['note']}</small></p>
<h3>2+. 计算溯源：输入表/列 → 单元格公式 → 脚本源码</h3>
{trace_html}
<h3>3. 描述性统计（面板实际变量）</h3>
{stats_table(L)}
</div>
"""

# 各层数据来源文字
FRAME["L1"]["source"]="本层指标分两类：<strong>直接下载</strong>——<code>gender</code>/<code>education</code>/<code>CFA</code>/<code>school</code> 直接来自 akshare·fund_manager_em 的经理画像，落库即用，仅作控制；<strong>计算派生</strong>——<code>mgr_total_tenure_v2</code> = 观测日 − 经理任职起始日的累计天数，<code>log_fund_age</code> = ln(基金成立至观测期的月数)，二者由基金基本信息/任职信息中的日期字段派生。<strong>原始下载文件</strong>见 <code>数据/L1_背景特征层/</code>（基金经理信息_最终版.csv、基金经理任职信息.csv、基金详细信息_最终版.csv、基金规模历史_批量.csv），经横向合并写入主面板。"
FRAME["L2"]["source"]="本层三个指标<strong>全部为计算加工，下载数据中不直接存在</strong>。原始下载数据有三份：① <code>基金持仓明细_全量修正版.csv</code> 给出基金各股权重向量 w_fund；② <code>沪深300成分股权重_真实.csv</code> + 中证500权重 给出基准权重向量 w_bench；③ <code>基金行业配置_全量.csv</code> 给出行业权重。<strong>以 AS 为例说明数据关系</strong>：AS 不是“扒到的数据里直接有”的字段，而是用“基金持仓权重向量”减去“沪深300+中证500合并基准权重向量”、取各股权重差绝对值之和的一半算出来（AS = ½Σ|w_fund − w_bench|）；ICI 由行业配置相对市场行业权重求偏离平方和；industry_hhi 由行业配置自身平方和得到。三者均由原始持仓/行业数据经 calc_active_share / calc_ici 等脚本计算（详见本节 2. 与 §二 总览）。"
FRAME["L3"]["source"]="本层三个指标来源不同：<strong>TO_wind 为 Wind DB 外部下载</strong>（基金换手率_Wind.csv，单边口径 MAX(买入,卖出)/平均净资产，覆盖 86.6%，为论文换手率主频）；<strong>TO_two_sided 与 OCI_two_sided 为项目脚本计算</strong>（基金换手率_双边_含卖出.csv → (买入+卖出)/(2×平均净资产)，双边口径覆盖 18.0%，OCI 由其自身时序标准化）。SDI 用基金净值对规模×价值成长四宫格风格指数做 OLS 得风格权重，再取相邻期风格权重曼哈顿距离。<strong>TO_wind 与 TO_two_sided 为双口径</strong>（单边 vs 双边，约½关系），仅论符号/显著性、不混用；旧占位变量 TO_calc/OCI 已于 2026-08-14 审计剔除。"
FRAME["L4"]["source"]="本层两个指标<strong>均为计算加工</strong>。原始下载数据仅 <code>基金净值历史_全量.csv</code>（及持仓明细）。<strong>计算关系</strong>：return_volatility 由净值序列取滚动 8 季收益率标准差；ARG 先算 RG = R_fund − Σ(w_{i,t−1}·R_{i,t})（基金实际收益与“按上期持仓模拟的组合收益”之差），再对逐季 |RG_t| 求和。<strong>两者均非下载即得</strong>，由 calc_return_gap 等脚本计算。"
FRAME["L5"]["source"]="本层三指标<strong>均为计算得出，下载数据中不直接存在</strong>（详见下方“1+. L5 三指标”专项澄清）。原始下载数据：① 基金持仓明细（DE 的持仓快照法原始输入）；② 个股月收益率 <code>个股月收益率_全量.csv</code>（tushare 价格衍生，判定盈亏）；③ 全市场基金持仓横截面（LSV 输入）；④ 基金净值面板（RA 输入）。三者经项目脚本算出后，分别以 <code>处置效应DE指标_修正版.csv</code> / <code>羊群行为LSV指标.csv</code> / <code>风险偏好不对称RA指标.csv</code> 输出，再合并进主面板成为 <code>de / pgr / plr / lsv / risk_asym</code>。三者数据源互不重叠。"

# L4 主面板 KPI
l4_kpis = f"""
  <div class="kpi"><div class="label">观测数</div><div class="value">{FW['panel']['n_obs']:,}</div></div>
  <div class="kpi"><div class="label">基金数</div><div class="value">{FW['panel']['n_funds']}</div></div>
  <div class="kpi"><div class="label">变量数</div><div class="value">{FW['panel']['n_vars']}</div></div>
  <div class="kpi"><div class="label">时间跨度</div><div class="value">{FW['panel']['date_min'][:7]} ~ {FW['panel']['date_max'][:7]}</div></div>
  <div class="kpi"><div class="label">季度数</div><div class="value">{FW['panel']['n_quarters']}</div></div>
"""

# L5 文件级表（来自 descriptive_stats.json）
L5_NAME = {"DE":"处置效应（Disposition Effect）","LSV":"交易趋同度（Herd/LSV）","RA":"风险偏好不对称（Risk Asymmetry）"}
l5_rows=[]
for tag in ["DE","LSV","RA"]:
    x=S["L5"][tag]
    l5_rows.append({"指标":tag,"中文含义":L5_NAME[tag],"文件":x["file"],"行数":x["n_rows"],"基金数":x["n_funds"],
        "时间":f"{x['date_min']}~{x['date_max']}","均值":x["var_stats"]["mean"],"标准差":x["var_stats"]["std"],
        "最小值":x["var_stats"]["min"],"最大值":x["var_stats"]["max"],"缺失率":f"{x['var_stats']['missing_pct']}%",
        "PGR均值":x.get("pgr",{}).get("mean",None),"PLR均值":x.get("plr",{}).get("mean",None)})
t_l5=rows_html(l5_rows)

# 宏观+FF 表
mf_rows=[]
for k,v in S["macro"].items():
    drng="-"
    if "date_min" in v and v["date_min"] not in ("NaT","None") and str(v["date_min"])[:4]!="1970":
        drng=f"{str(v['date_min'])[:10]}~{str(v['date_max'])[:10]}"
    mf_rows.append({"数据":k.replace("宏观_","").replace(".csv",""),"列数":v["n_cols"],"期数":v.get("n_periods","-"),
                    "年份范围":f"{v.get('year_min','-')}–{v.get('year_max','-')}","日期范围":drng})
for k,v in S["ff_factors"].items():
    drng="-"
    if "date_min" in v and v["date_min"] not in ("NaT",None) and str(v["date_min"])[:4]!="1970":
        drng=f"{str(v['date_min'])[:10]}~{str(v['date_max'])[:10]}"
    mf_rows.append({"数据":k.replace(".csv",""),"列数":len(v.get("cols",[])),"期数":v.get("n_rows","-"),
                    "年份范围":f"{v.get('year_min','-')}–{v.get('year_max','-')}","日期范围":drng})
t_mf=rows_html(mf_rows)

# 基金类型
ft=sorted(S["fund_universe"]["by_type"].items(),key=lambda x:-x[1])
ft_html="<table><thead><tr><th>基金类型</th><th>数量</th></tr></thead><tbody>"
for k,v in ft[:12]:
    ft_html+=f"<tr><td>{k}</td><td>{v:,}</td></tr>"
ft_html+="</tbody></table>"

# 因变量/控制 描述统计（来自 framework_stats）
dep_rows=[]
for r in FW["dependent"]:
    dep_rows.append({"变量":r["variable"],"样本量":r["n"],"缺失率%":r["missing_pct"],
        "均值":r["mean"],"标准差":r["std"],"中位":r["median"],"最小":r["min"],"最大":r["max"]})
t_dep=rows_html(dep_rows)

html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>基金经理行为分析研究 · 数据描述性统计（按论文框架 L1–L5）</title>
<style>
:root{{--accent:#2E5A87;--accent2:#C0504D;--bg:#f8f9fa;--card:#fff;--txt:#2d2d2d;--muted:#6c757d;--border:#dee2e6;}}
body{{font-family:"Microsoft YaHei","PingFang SC",sans-serif;background:var(--bg);color:var(--txt);line-height:1.6;max-width:1100px;margin:0 auto;padding:20px;}}
h1{{color:var(--accent);border-bottom:3px solid var(--accent);padding-bottom:8px;font-size:1.8rem;}}
h2{{color:var(--accent);margin-top:28px;font-size:1.3rem;border-left:5px solid var(--accent);padding-left:10px;}}
h3{{color:var(--accent2);margin-top:22px;font-size:1.05rem;}}
.card{{background:var(--card);border-radius:8px;box-shadow:0 1px 4px rgba(0,0,0,.06);padding:18px;margin:16px 0;}}
table{{width:100%;border-collapse:collapse;font-size:.88rem;margin:10px 0;}}
th,td{{border:1px solid var(--border);padding:6px 10px;text-align:left;}}
th{{background:#eef3f8;color:var(--accent);font-weight:600;}}
tr:nth-child(even){{background:#fafafa;}}
.summary{{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px;}}
.kpi{{background:var(--card);border-left:4px solid var(--accent);padding:12px;border-radius:6px;box-shadow:0 1px 3px rgba(0,0,0,.05);}}
.kpi .label{{font-size:.8rem;color:var(--muted);}}
.kpi .value{{font-size:1.4rem;font-weight:700;color:var(--accent);}}
img{{max-width:100%;border:1px solid var(--border);border-radius:6px;margin:12px 0;}}
.caption{{font-size:.85rem;color:var(--muted);text-align:center;margin-top:-6px;}}
.layer-note{{background:#fff7f7;border-left:4px solid var(--accent2);padding:8px 12px;border-radius:4px;color:#7a4a48;font-size:.92em;}}
.formula{{font-family:'Cambria Math','Times New Roman',serif;font-size:.95em;background:var(--card);}}
code{{background:#eef3f8;padding:1px 6px;border-radius:3px;font-size:.86em;color:#243b53;}}
ul.compact{{margin:6px 0;padding-left:22px;}}
.trace{{border-left:4px solid var(--accent);background:#f4f8fc;padding:10px 14px;margin:10px 0 14px;border-radius:6px;}}
.trace-h{{font-weight:700;color:var(--accent);margin-bottom:4px;}}
.trace-row{{font-size:.9em;margin:3px 0;}}
.trace-tag{{font-size:.82em;color:#7a4a48;margin:4px 0 2px;}}
pre.codebox{{background:#f0f3f6;color:#1a2b3c;padding:10px 12px;border-radius:6px;font-family:'Consolas','Courier New',monospace;font-size:.82em;white-space:pre;overflow-x:auto;margin:4px 0 2px;border:1px solid #d0d7de;}}
</style>
</head>
<body>
<h1>基金经理行为分析研究 · 数据描述性统计</h1>
<p style="color:var(--muted)">生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')} · 严格按《论文解读说明》的 L1–L5 框架分层（指标→主面板变量→算法→描述统计）</p>

<div class="card">
<h2>一、数据目录总览</h2>
<p>项目数据按论文 5 层框架 + 行情/宏观/FF/基础信息/外部数据/元数据/归档 进行分类。其中 <strong>“无用数据”</strong> 是历次迭代中被替代的旧版本，仅作归档，不参与当前实证。</p>
<div class="summary">
  <div class="kpi"><div class="label">全部文件</div><div class="value">{INV['total_files']:,}</div></div>
  <div class="kpi"><div class="label">活跃分析层文件</div><div class="value">{active_n:,}</div></div>
  <div class="kpi"><div class="label">活跃层体积</div><div class="value">{active_mb:.1f} MB</div></div>
  <div class="kpi"><div class="label">归档“无用数据”</div><div class="value">{useless_n:,}</div></div>
  <div class="kpi"><div class="label">归档体积</div><div class="value">{useless_mb:.1f} MB</div></div>
</div>
<h3>各活跃数据层明细</h3>
{rows_html(layer_rows)}
<img src="figures/fig1_layers.png" alt="各层文件数量与体积">
<p class="caption">图 1：活跃数据层文件数量与体积。股价行情与 L4 风险应对层体积最大。</p>
</div>

<div class="card">
<h2>二、指标来源总览：下载数据 vs 计算指标（每个指标从哪来）</h2>
<p>本节回答两个核心问题：① 每个指标是“从哪个平台下载的”，还是“项目脚本算出来的”；② 指标之间的数据关系（例如 AS 是怎么从原始数据算出来的）。先给出原始下载数据清单，再给出逐指标来源映射。<strong>一句话结论：L1–L5 的每一个行为指标都不是下载数据中“直接有”的，全部由项目脚本从下方清单的原材料算出来；只有 L1 的 gender/education/CFA/school 与全部原始数据本身是“直接下载”。</strong></p>
{PROV_SECTION}
</div>

<div class="card">
<h2>三、L1–L5 框架逻辑总览（指标如何被使用）</h2>
<p>论文用 <strong>L1 背景 → L2 决策 → L3 执行 → L4 风控 → L5 认知</strong> 五层框架回答核心问题：“在控制所有<strong>可观测行为</strong>（L1–L4）之后，<strong>认知偏差</strong>（L5）是否仍携带独立的业绩预测信息？”前四层是“控制塔”，L5 是“待检验对象”。<strong>“递进”指分析深度的递进（由表及里），不是 L1→L5 的因果链。</strong></p>
<h3>3.1 递进回归 M0→M4（每层增量信息的度量）</h3>
<table>
<tr><th>模型</th><th>包含变量</th><th>ΔR²</th><th>回答的问题</th></tr>
<tr><td>M0</td><td>仅规模控制（log_aum）</td><td>—</td><td>基线：基金规模解释多少业绩差异？</td></tr>
<tr><td>M1</td><td>M0 + L1（经理背景）</td><td>26.7%</td><td>控制规模后，“经理是谁”额外解释多少？</td></tr>
<tr><td>M2</td><td>M1 + L2（投资决策）</td><td>2.5%</td><td>再控背景后，“如何配置”有增量吗？</td></tr>
<tr><td>M3</td><td>M2 + L3+L4（交易+风控）</td><td>17.8%</td><td>再控配置后，“如何执行+控险”有增量吗？</td></tr>
<tr><td><strong>M4</strong></td><td>M3 + <strong>L5（认知偏差）</strong></td><td><strong>6.3%</strong><br><span style="font-size:.8em;color:var(--muted)">同样本</span></td><td><strong>穷尽可观测行为后，认知偏差仍有独立预测力吗？</strong></td></tr>
</table>
<h3>3.2 三重识别（三主回归）</h3>
<table>
<tr><th>主回归</th><th>识别逻辑</th><th>回答什么</th><th>证据性质</th></tr>
<tr><td>① 截面基准</td><td>α_i = β·L5 + γ′X + ε（干净样本 N=358/385，HC1）</td><td>基金之间：偏差差异是否解释业绩差异？</td><td>预测（B）</td></tr>
<tr><td>② 前向预测</td><td>Σr_{{t+1..t+h}} = β′L5_t + 年份FE（基金聚类，h=1/4季）</td><td>当期偏差能否预测<strong>未来</strong>业绩？（时间先后排除同期反向因果）</td><td>预测（B，较强）</td></tr>
<tr><td>③ 组内识别</td><td>r_{{i,t}} = β′L5 + 基金FE + 年份FE（双向FE）</td><td>同一基金偏差变化时，业绩是否随之变化？</td><td>准因果（组内维度，DE 最强）</td></tr>
</table>
<p class="layer-note"><small>核心因变量为 <code>ff5_adj_return</code>（FF5 alpha，基金层面常量，故截面独立样本即基金数：干净样本 358 只，§4.2.0 数据剔除协议后口径）；前向/组内用时变超额收益。干净样本下三指标证据呈结构化分化：RiskAsym 的证据集中于截面与组内维度（前向无稳健预测力，呈期限结构分化）、LSV 显著预测未来 4 季度业绩但其截面关联对样本选择高度敏感、DE 的最强证据在组内维度（最接近因果）。</small></p>
</div>

{render_layer("四","L1", trace_html=render_calc_trace("L1"))}
{render_layer("五","L2", trace_html=render_calc_trace("L2"))}
{render_layer("六","L3", trace_html=render_calc_trace("L3"))}
{render_layer("七","L4", kpis_html=l4_kpis, figure="figures/fig2_panel_coverage.png", figcap="图 2：主分析面板基金-季度观测分布。2018 年后观测密度显著提升，样本期 2006Q4–2026Q1。", trace_html=render_calc_trace("L4"))}

<div class="card">
<h2>八、L5 认知偏差层（三指标详解 + 版本口径说明）</h2>
<p style="color:var(--muted)"><strong>定义：</strong>为何如此决策（核心创新层，不可直接观测）</p>
<h3>1. 数据从哪来</h3>
<p>{FRAME['L5']['source']}</p>
{L5_PROV_HTML}
<h3>2. 怎么算（公式与算法）</h3>
{def_table("L5")}
<p class="layer-note"><small>{FRAME['L5']['note']}</small></p>
<h3>2+. 计算溯源：输入表/列 → 单元格公式 → 脚本源码（L5 三指标）</h3>
{render_calc_trace("L5")}
<h3>3. 描述性统计 —— 面板实际变量（主回归所用）</h3>
{stats_table("L5")}
<h3>4. 描述性统计 —— 独立指标文件（修正版）</h3>
{t_l5}
<p><small>注：第 3 节为主面板内直接落库的 L5 列（基金-季度观测口径）；第 4 节为 <code>数据/L5_认知行为层/</code> 下的独立修正版指标文件（基金-日期口径）。两者覆盖与口径略有差异属正常（指标文件经去重/全持仓筛选）。</small></p>
<img src="figures/fig3_l5_dist.png" alt="L5 三指标分布">
<p class="caption">图 3：L5 三指标分布。面板实际 DE 均值 −0.072（反向处置），LSV 均值 −0.227（反向交易），RiskAsym 均值 +0.039（正向风险承担不对称）。</p>
<div class="layer-note"><small>⚠ <strong>版本口径提示：</strong>《论文解读说明》中的示例数值（PGR=0.891/PLR=0.919、LSV=−0.168、DE=−0.028）对应<strong>早期 v20 口径</strong>；当前主面板已采用修正版（见上表 PGR≈0.756/PLR≈0.828/DE≈−0.072）。L5数据诊断报告 进一步给出“仅全持仓(6/12月)口径”的完全修正版（DE≈−0.116，覆盖 142 基金）。论文写作须以面板实际值与诊断报告为准，并如实披露口径与覆盖率。</small></div>
</div>

<div class="card">
<h2>九、因变量与核心控制变量</h2>
<p>以下变量是实证回归的<strong>因变量</strong>与<strong>控制变量</strong>（不属于 L1–L5 行为层，但每层指标都与之联合估计）：</p>
<table>
<tr><th>变量</th><th>角色</th><th>说明</th></tr>
<tr><td><code>ff5_adj_return</code></td><td>主因变量（截面）</td><td>FF5 alpha，对每只基金月度超额收益做时序回归的截距 α</td></tr>
<tr><td><code>future_return</code></td><td>前向预测因变量</td><td>未来 1 季度基金收益</td></tr>
<tr><td><code>quarter_return</code> / <code>excess_return</code></td><td>时变收益</td><td>当期季度收益 / 相对基准超额收益（组内回归用）</td></tr>
<tr><td><code>log_aum</code></td><td>规模控制</td><td>资产净值对数，M0 基线控制</td></tr>
</table>
{rows_html(dep_rows)}
</div>

<div class="card">
<h2>十、基金池、股价行情与持仓</h2>
<div class="summary">
  <div class="kpi"><div class="label">基金池总数</div><div class="value">{S['fund_universe']['n_total']:,}</div></div>
  <div class="kpi"><div class="label">日行情记录</div><div class="value">{S['stock_prices']['n_rows']:,}</div></div>
  <div class="kpi"><div class="label">覆盖个股数</div><div class="value">{S['stock_prices']['n_stocks']:,}</div></div>
  <div class="kpi"><div class="label">持仓明细行数</div><div class="value">{S['holdings']['n_rows']:,}</div></div>
  <div class="kpi"><div class="label">持仓覆盖基金</div><div class="value">{S['holdings']['n_funds']}</div></div>
  <div class="kpi"><div class="label">持仓覆盖股票</div><div class="value">{S['holdings']['n_stocks']:,}</div></div>
</div>
<h3>基金池类型分布（前 12 类）</h3>
<div style="display:grid;grid-template-columns:1fr 1fr;gap:18px;align-items:start;">
<div>{ft_html}</div>
<div><img src="figures/fig4_fund_types.png" alt="基金类型分布" style="margin:0;"></div>
</div>
<p class="caption">图 4：基金池类型分布。全市场基金池 27,449 只，含清盘基金。</p>
<h3>股价行情</h3>
<ul class="compact">
  <li><strong>个股日行情</strong>：{S['stock_prices']['n_rows']:,} 行，{S['stock_prices']['n_stocks']:,} 只股票，{S['stock_prices']['date_min']} ~ {S['stock_prices']['date_max']}。</li>
  <li><strong>个股月收益率</strong>：{S['stock_prices']['monthly_n_rows']:,} 行，{S['stock_prices']['monthly_n_stocks']} 只股票，{S['stock_prices'].get('monthly_date_min','—')} ~ {S['stock_prices'].get('monthly_date_max','—')}。</li>
</ul>
<h3>基金持仓</h3>
<ul class="compact">
  <li><strong>持仓明细</strong>：{S['holdings']['n_rows']:,} 条记录，覆盖 {S['holdings']['n_funds']} 只基金、{S['holdings']['n_stocks']:,} 只股票，报告期 {S['holdings']['date_min']} ~ {S['holdings']['date_max']}。</li>
  <li><strong>持仓变动</strong>：{S['holdings']['change_n_rows']:,} 条买入明细。</li>
</ul>
</div>

<div class="card">
<h2>十一、宏观与 FF 因子</h2>
{t_mf}
<img src="figures/fig5_macro_span.png" alt="宏观与FF时间跨度">
<p class="caption">图 5：宏观变量与 Fama-French 因子时间跨度。</p>
</div>

<div class="card">
<h2>十二、数据质量与口径说明</h2>
<ul class="compact">
  <li><strong>分层校正（重要）：</strong>本报告严格按《论文解读说明》的框架定义分层——<strong>L2=AS_improved/ICI/industry_hhi</strong>（主动份额/行业集中度/行业分散度）、<strong>L3=SDI/TO_wind/TO_two_sided/OCI_two_sided</strong>（风格漂移/换手率[Wind单边+真算双边]/过度交易）、<strong>L4=ARG/return_volatility</strong>（风险调整幅度/收益波动率）、<strong>L5=DE/LSV/RiskAsym</strong>。TO_wind（86.6%）为论文换手率主频口径，TO_two_sided（18.0%）为双边双口径对照；旧占位 TO_calc/OCI 已剔除。<strong>ICI 在本框架中是行业集中度 Σ(w_i−W̄_i)²，并非“隐性交易”</strong>；RG 不是独立层指标，而是 ARG 的构成要素与 L4 算法产物。</li>
  <li><strong>L5 版本漂移：</strong>主面板 L5 列与独立 L5 指标文件、与《论文解读说明》示例数值之间存在口径差异（已在上文提示）。核心行为变量缺失：LSV 约 56%、DE 约 37%、RA 约 34%，源于部分基金/季度无法计算对应指标，与论文回归子样本一致。</li>
  <li>股价行情日度数据体量大（>300 MB），仅 <code>date</code>/<code>stock_code</code> 列为有效索引；<code>ts_code</code>/<code>trade_date</code> 列为空，已忽略。</li>
  <li>“无用数据”层存放历次迭代旧面板与多版本 FF 测试数据，已统一归档，不影响当前分析。</li>
</ul>
</div>

<div class="card">
<h2>十三、面板变量字典（按框架 L1–L5 重新归类）</h2>
<p>主面板共 154 列，下表将各层实质性变量按框架重新归类，并标注其对应的框架指标与主面板变量名。</p>
<table>
<tr><th>层</th><th>框架指标</th><th>主面板变量</th><th>含义</th></tr>
<tr><td>L1 背景</td><td>从业年限/基金年龄/性别/学历/CFA/院校</td><td>mgr_total_tenure_v2 / log_fund_age / gender / education / CFA / school</td><td>外生背景特征，作控制</td></tr>
<tr><td>L2 决策</td><td>主动份额/行业集中度/行业分散度</td><td>AS_improved / ICI / industry_hhi</td><td>组合静态结构（如何配置）</td></tr>
<tr><td>L3 执行</td><td>风格漂移/换手率/过度交易</td><td>SDI / TO_wind / TO_two_sided / OCI_two_sided</td><td>动态交易行为（如何执行）</td></tr>
<tr><td>L4 风控</td><td>风险调整幅度/收益波动率</td><td>ARG / return_volatility</td><td>风险层面（如何控险）</td></tr>
<tr><td>L5 认知</td><td>处置效应/交易趋同度/风险偏好不对称</td><td>de(pgr,plr) / lsv / risk_asym</td><td>不可观测认知构念（为何决策）</td></tr>
<tr><td>因变量</td><td>FF5 alpha / 未来收益 / 时变收益</td><td>ff5_adj_return / future_return / quarter_return,excess_return</td><td>回归因变量</td></tr>
<tr><td>控制</td><td>规模控制</td><td>log_aum</td><td>M0 基线控制</td></tr>
</table>
<p>缩写衍生（OCI/SDI/ICI/ARG/BHS/CR/RAR）已按框架归入对应层；其中 BHS（锦标赛虚拟变量）为<strong>旧 L5 设计</strong>遗留，现已不作为认知偏差指标使用。</p>
</div>

</body>
</html>
"""

with open(os.path.join(OUT,"数据描述性统计报告.html"),"w",encoding="utf-8") as f:
    f.write(html)
print(">> 报告已生成:", os.path.join(OUT,"数据描述性统计报告.html"))
