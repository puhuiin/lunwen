# -*- coding: utf-8 -*-
"""
合并总表 v2（按实际含义归并）：
- 删除"使用说明与数据质量"(s0)
- 将所有 L1-L3(参考HTML) + L4/L5/M(JSON) 条目按【实际含义】归并到我们自己的规范变量
- 每一层一张大表，列：我们命名 | 测什么(含义) | 文献是怎么做的 | 本论文做法 | 文献来源(末列)
- 所有归并后的变量标 "✓ 采用"（即"我们这个里面有的变量"），六大核心(ARG/RG/收益波动率/DE/LSV/RiskAsym) 额外标 ★
- 重点：每一行着重介绍"参考文献中这些是怎么做的"（构建逻辑+公式+代表文献）
"""
import json, html, os, re, glob
from collections import OrderedDict

BASE = r"D:/Desktop/基金经理行为分析研究/参考文献"
BASE_L13 = r"C:/Users/26955/Downloads/变量指标L1-L3.html"

# ============================================================
# 1. 加载 L1-L3 参考 HTML 的合并变量表
# ============================================================
ref = open(BASE_L13, encoding="utf-8").read()

def parse_table(body):
    m = re.search(r'<table>.*?</table>', body, re.S)
    if not m:
        return []
    tbl = m.group(0)
    rows = re.findall(r'<tr>(.*?)</tr>', tbl, re.S)
    out = []
    for r in rows:
        if '<th' in r:
            continue
        cells = re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', r, re.S)
        cells = [html.unescape(re.sub(r'<[^>]+>', '', c)).strip() for c in cells]
        if cells:
            out.append(cells)
    return out

pat = re.compile(r'(<h3><span class="layer-tag l([123])">L([123])</span>[^<]*?</h3>)', re.S)
parts = pat.split(ref)
L13 = {"L1": [], "L2": [], "L3": []}
k = 0
while True:
    gi = 1 + 4 * k
    if gi >= len(parts):
        break
    h3full = parts[gi]
    layer = "L" + parts[gi + 1]
    body = parts[gi + 3] if (gi + 3) < len(parts) else ""
    vtype = "自变量" if "自变量" in h3full else ("因变量" if "因变量" in h3full else "")
    for r in parse_table(body):
        if len(r) >= 5:
            var, dfn, formula, ds, src = r[0], r[1], r[2], r[3], r[4]
        elif len(r) == 4:
            var, dfn, formula, src = r[0], r[1], r[2], r[3]; ds = ""
        else:
            continue
        L13.setdefault(layer, []).append({
            "name": var, "type": vtype, "def": dfn,
            "formula": formula, "ds": ds, "src": src, "sources": [src] if src else []
        })
    k += 1

# ============================================================
# 2. 加载 L4/L5/M 的 JSON 提取
# ============================================================
jfiles = sorted(glob.glob(os.path.join(BASE, "extracted_variables_*.json")))
raw = []
for f in jfiles:
    try:
        raw.extend(json.load(open(f, encoding="utf-8")))
    except Exception as e:
        print("ERR", f, e)

def norm_layer(r):
    L = str(r.get("layer", ""))
    if L.startswith("L4"): return "L4"
    if L.startswith("L5"): return "L5"
    if L.startswith("M"):  return "M"
    return L

def rec_ds_str(r):
    ds = r.get("data_source", {})
    if isinstance(ds, dict):
        return " ｜ ".join([ds.get("source", ""), ds.get("sample_period", ""), ds.get("sample_size", "")]) \
            .strip(" ｜").strip()
    return str(ds or "")

def src_label(r):
    t = (r.get("authors_year", "") or "").strip()
    f = (r.get("file", "") or "").strip()
    return (t + " 《" + f + "》") if t else f

L456 = {"L4": [], "L5": [], "M": []}
for r in raw:
    layer = norm_layer(r)
    if layer not in L456:
        continue
    src = src_label(r)
    rds = rec_ds_str(r)
    for key in ("independent_variables", "dependent_variables"):
        vlist = r.get(key, []) or []
        vtype = "自变量" if key.startswith("ind") else "因变量"
        if isinstance(vlist, str):
            vlist = [vlist]
        for v in vlist:
            if not isinstance(v, dict):
                v = {"name": str(v), "definition": "", "formula": "", "data_source": ""}
            L456[layer].append({
                "name": v.get("name", ""), "type": vtype,
                "def": v.get("definition", "") or "",
                "formula": v.get("formula", "") or "",
                "ds": v.get("data_source", "") or rds,
                "src": src, "sources": [src]
            })

# 统一条目池（不分来源层，全部按含义归并）
ALL = []
for layer in L13:
    for e in L13[layer]:
        e2 = dict(e); e2["src_layer"] = layer; ALL.append(e2)
for layer in L456:
    for e in L456[layer]:
        e2 = dict(e); e2["src_layer"] = layer; ALL.append(e2)

# ============================================================
# 3. 规范变量体系（我们自己的命名 + 含义 + 文献怎么做的 + 本论文做法 + 关键词）
# ============================================================
G = []
def grp(key, layer, name, meaning, kws, how, ours, formula=""):
    G.append({"key": key, "layer": layer, "name": name, "meaning": meaning,
              "kws": kws, "how": how, "ours": ours, "formula": formula})

# ---------- L1 背景特征层 ----------
grp("tenure","L1","从业/任期 Tenure","经理首次任职至观测时点的累计从业时间，刻画人力资本积累",
    ["从业年限","tenure","任职年限","工作年限","experience","经验","mgr_total"],
    "文献多以『担任基金经理的累计年数/天数』度量（Chevalier & Ellison 1999；Li & Li 2018；赵秀娟2010；吴栩2017）。关系并非线性——经验效应（越老越强）与能力固化（越老越僵化）并存。",
    "论文用 <b>mgr_total_tenure_v2</b> = 经理首次任职至观测时点的累计天数（akshare fund_manager_em）；作控制变量，不对方向做强预设。",
    "tenure = 首次任职日 → 观测时点 的累计天数")
grp("fund_age","L1","基金年龄 Fund Age","基金成立至观测期的存续时长，控制策略成熟度/规模臃肿",
    ["基金年龄","fund age","成立","存续","基金年限","log_fund"],
    "文献以基金成立年限作为存续期与成熟度代理（Golec 1996 用基金年龄控制）。",
    "论文用 <b>log_fund_age</b> = ln(基金成立至观测期月数)，取对数缓解右偏；为自定义控制变量。")
grp("education","L1","学历/学位 Education","学士/硕士/博士等学历层次，作人力资本信号",
    ["学历","学位","master","phd","博士","硕士","学士","education","degree","教育程度"],
    "文献将学历设为分类变量（学士/硕士/博士）作控制（吴栩2017；于静2013；赵秀娟2010；Golec 1996）。",
    "并入 L1 教育背景控制，与院校、CFA 一并纳入。")
grp("school","L1","院校/名校 School","是否名校/985/顶尖院系毕业，作为人力资本质量信号",
    ["院校","名校","985","毕业","school","university","教育背景","毕业院校"],
    "部分文献用『是否名校毕业/985/常春藤』作为专业能力信号（吴栩2017；Golec 1996）。",
    "并入 L1 教育背景控制。")
grp("cert","L1","专业资质 CFA/MBA","CFA/MBA/CPA 等专业资质，作专业训练信号",
    ["cfa","mba","资质","证书","cpa","执业","资格","专业证书"],
    "CFA/MBA/CPA 等作为专业训练与资质信号（吴栩2017；08_L1_CFA_MBA；Golec 1996）。",
    "作分类控制变量。")
grp("gender","L1","性别 Gender","经理性别，考察性别相关的风险偏好/投资风格差异",
    ["性别","gender","男","女","男性","女性"],
    "性别作为个人特征控制（11_L1_Gender；吴栩2017；于静2013）；与风险偏好、投资风格研究呼应（15_性别个人特征）。",
    "作控制变量。")
grp("alumni","L1","校友网络 Alumni Network","同校/同院系关系网络，检验『小圈子』效应",
    ["校友","alumni","关系网络","小圈子","同学"],
    "申宇(2015)用『同校/同院系』构建校友关系网络，检验校友关系网络对基金业绩与『小圈子』效应的影响（16_校友关系网络）。",
    "归入 L1 声誉/关系环境控制。")
grp("incentive","L1","薪酬/激励 Incentive","薪酬契约与业绩挂钩程度，影响风险承担动机",
    ["薪酬","激励","incentive","compensation","奖金","薪酬激励"],
    "文献考察薪酬契约与基金流量、风险承担的关系（12_L1_Mutual_Fund_Managers_Paid；基金经理激励评述）。",
    "归入激励环境控制，与锦标赛理论衔接。")
grp("career_concern","L1","职业忧虑/锦标赛压力 Career Concern","职业忧虑与排名压力，解释风险调整动机",
    ["职业忧虑","career concern","锦标赛","排名压力","职业关注","声誉"],
    "Chevalier & Ellison (1999) 职业忧虑；Brown-Harlow-Starks (1996) 锦标赛理论，解释排名压力下的风险调整动机。",
    "作为 L4 风险调整（ARG/RG）的动机背景。")
grp("tone","L1","文本语调 Manager Tone","经理年报/披露文本的情感倾向，作认知/情绪代理（单变量双角色：L1 背景文本特征 + L5 认知/情绪代理；与 L5 同源，已合并）",
    ["语调","tone","情感","sentiment","文本","年报","bert","措辞","情绪"],
    "基金经理语调/情感分析（基金经理语调与投资行为——基于 BERT 人工智能模型；基金经理语调、基金收益与投资者行为）用年报文本挖掘 manager tone。",
    "单变量双角色：归入 L1 文本特征（背景/描述性），并作为 L5 认知/情绪代理。原 L5『文本语调 Tone/Sentiment』与此测量完全相同，已合并为本条目，L5 认知层不再单列（与 OCI 合并逻辑一致）。")
grp("age","L1","经理年龄 Age","经理周岁年龄，与任期互补的人口学特征",
    ["年龄","age"],
    "文献以经理周岁年龄作为人口学控制（吴栩2017；于静2013）。",
    "作控制变量（与 tenure 互补）。")
grp("background_extra","L1","海外/学科背景 Background","海外留学工作背景、商科/理工科学科背景",
    ["海外背景","overseas","abroad","学科背景","商科","理工科","专业"],
    "文献考察海外背景与学科（商/经济或理工）对投资行为的影响（Li & Li 2018；吴栩2017）。",
    "并入 L1 背景控制。")
grp("flow","L1","资金流/净赎回 Flow","剔除收益影响的净资金流入（比例），反映投资者选择",
    ["资金流","净赎回","申购","赎回","个人/机构","信任断裂","净资金"],
    "基金资金流与业绩关系（19_基金业绩与投资者的选择；20_明星效应与垫底效应；23_赎回异象；22_实证研究；21_申购赎回）。反映投资者选择行为。",
    "归入 L1 投资者环境控制（非经理行为变量，但影响样本构成）。")
grp("career_event","L1","经理变更/离职 Career Event","升/降职、主动离职等经理职业变动事件",
    ["基金经理更换","升职","降职","主动离职","变更","离职"],
    "经理更换作为激励约束事件（基于基金经理更换的激励约束效应研究）；降职/升职 Logit（09_L1_Fund_Flows）。",
    "归入 L1 职业事件控制。")
grp("team_struct","L1","决策权/团队结构 Team","单独 vs 团队管理、兼职管理等决策结构",
    ["决策权","团队管理","兼职","side-by-side","单独","团队"],
    "决策权分配与投资策略选择（决策权分配与投资策略选择）；兼职基金经理（兼职基金经理能做得更好吗）。",
    "归入 L1 管理结构控制。")
grp("peers","L1","同辈竞争 Peers","同辈基金数量构成的竞争网络",
    ["同辈竞争","peers","竞争网络"],
    "中心基金的同辈基金数量作为竞争网络代理（共同激励机制下基金经理短视投资研究）。",
    "归入 L1 竞争环境控制。")

# ---------- L2 持仓偏离层 ----------
grp("active_share","L2","主动份额 Active Share (AS)","组合权重与基准权重偏离之和的一半，度量主动管理程度",
    ["主动份额","active share","主动程度","主动管理","as"],
    "Cremers & Petajisto (2009/2013)：AS = ½·Σ|w_fund − w_bench|∈[0,1]，0=完全复制基准。以单一基准指数度量。",
    "论文 <b>AS_improved</b> 以沪深300+中证500合并真实成分股权重为基准重算，解决单一指数（如沪深300）系统性低估主动度的问题；在当前可复现管线下截面区分度与原始口径相当（CV约0.15），改进意义在基准真实性而非数值放大。",
    "AS = (1/2)·Σᵢ|w_fund,i − w_bench,i|")
grp("ici","L2","行业集中度 ICI","行业配置相对市场平均的偏离平方和，度量行业选择的主动性",
    ["行业集中度","ici","icr","行业偏离","行业积极配置","行业活跃度","行业集中度指数","行业集中度（持股）"],
    "Kacperczyk et al. (2005)：ICI = Σ(wᵢ − W̄ᵢ)²，度量行业选择的主动性/主动下注程度；另有 ICR/ASR 量纲修正、IC/IA 等变体。",
    "沿用 ICI 定义；与 HHI 近似正交（诚实截面相关仅 0.20，VIF 1.25/1.08）。",
    "ICI = Σᵢ(wᵢ − W̄ᵢ)²")
grp("hhi","L2","行业分散度 HHI","行业权重平方和，度量组合本身的集中程度",
    ["hhi","行业分散度","分散度","herfindahl"],
    "组合行业权重平方和 Σwᵢ²（Kacperczyk 2005 用 HHI 度量组合集中度），∈[1/K,1]，与同业做什么无关。",
    "论文 <b>industry_hhi</b> 自定义，刻画组合本身集中程度；ICI 与 HHI 非镜像（ICI = HHI_基金 + HHI_市场 − 2Σ(wᵢ·W̄ᵢ)）。",
    "HHI = Σᵢ(wᵢ)²")
grp("tracking_error","L2","跟踪误差 Tracking Error","组合收益与基准收益差的标准差，主动风险",
    ["跟踪误差","tracking error","te","样本外跟踪误差"],
    "组合收益与基准收益之差的标准差（主动风险），Cremers&Petajisto 等用于刻画偏离；另有样本外 TE 波动率评价基准优劣。",
    "由 AS 派生/佐证主动程度。")
grp("holding_conc","L2","持仓集中度 TopN","前十大重仓股占比/持股赫芬达尔，度量组合集中",
    ["持仓集中度","top10","前十大","持股集中度","重仓","基金持股比例"],
    "前十大重仓股占比或持股赫芬达尔（赵秀娟2010；肖峻2011）；基金持股比例（持某股/流通股）。",
    "归入 L2 组合结构刻画。")
grp("style_expo","L2","风格暴露/资产配置 Style & Allocation","规模/价值-成长因子暴露与战略资产配置比例",
    ["风格暴露","style","规模","价值","成长","因子暴露","资产配置","积极管理程度","政策性","brinson"],
    "规模/价值-成长因子暴露（Fama-French 风格箱）；资产配置比例（股/债/现金）；Brinson 积极管理程度（实际−政策基准）。",
    "用于 L3 风格漂移 SDI 的四宫格（规模×价值成长）划分。")
grp("breadth","L2","组合广度/持股数 Breadth","组合持股数量，度量分散化程度",
    ["持股数","股票数","breadth","组合广度","分散投资"],
    "组合持股数量度量分散化程度（Kacperczyk 2005）。",
    "辅助刻画组合结构。")
grp("index_alpha","L2","公开信息依赖度 RPI / 基准 Alpha","组合对公开信息的依赖度与基准偏误",
    ["rpi","公开信息依赖度","基准调整后收益","index alpha","基准指数","异常收益","业绩持续性","基准偏误"],
    "Kacperczyk & Seru (RPI)：组合持仓变动对分析师建议变动回归的 R²，越高越依赖公开信息（能力越低）；基准指数 Alpha 测基准偏误；DGTW 特征匹配异常收益。",
    "归入 L2 主动绩效/能力刻画。")

# ---------- L3 交易行为层 ----------
grp("return_gap","L4","收益缺口 Return Gap (RG)","披露间歇期『隐形交易』的净效应：实际净收益与维持上期持仓模拟收益之差",
    ["return gap","收益缺口","rg"],
    "Kacperczyk, Sialm & Zheng (2008, RFS)：RG = (RF − EXP) − RH，RF=投资者净收益(扣费后)，RH=按上期披露持仓构建的买入持有毛收益，EXP=费用率。度量『若维持上期持仓不变』的模拟收益与实际净收益之差，RG>0 表示隐形交易创造超额。",
    "与 ARG 衔接，作为 L4 风险调整的观测背景；论文在 L4 以 RG 的跨期绝对值加总得 ARG。",
    "RG = (RF − EXP) − RH")
grp("turnover","L3","换手率 Turnover (TO)","区间内买卖金额（取买卖较小者）除以平均净资产",
    ["换手率","turnover","to","转手","交易频率","min(买入"],
    "TR = min(买入总额, 卖出总额)/平均TNA（Carhart 1997；Lan 2015），剔除申购赎回引起的被动交易。高换手侵蚀业绩。",
    "论文 <b>TO_calc</b> 取 min 剔除申赎被动交易；并由其派生 OCI。",
    "TO = min(买入,卖出)/平均净资产")
grp("oci","L3","过度自信/过度交易 Overconfidence (OCI)","换手率相对基金自身历史的标准化偏离，既是过度交易的代理、也是过度自信的行为测度（与 L5『过度自信』同源合并）",
    ["oci","过度交易","overconfidence","过度自信","self-attribution","自归因","自我归因","标准化偏离","风险偏好","bret"],
    "OCI = (TO − TŌ)/σ(TO)（Statman, Thorley & Vorkink 2006）。>0 表示当期交易超出自身常态，是过度自信驱动过度交易的经典代理；Gervais & Odean (2001) 自我归因偏差、性别/经验与过度自信（11_L1_Gender；吴栩2017）、实验测度（BRET 炸弹风险任务）均指向同一构念。原 L5『过度自信 Overconfidence』与此计算方法完全相同，已合并为本条目，L5 认知层不再单列。",
    "论文以 (TO − TŌ)/σ(TO) 对基金自身历史（前 4–8 季）标准化；OCI 由换手率派生，归入 L3 交易行为（行为表现）并作为 L5 过度自信的统一代理（认知驱动）。",
    "OCI = (TO − TŌ)/σ(TO)")
grp("style_drift","L3","风格漂移 Style Drift (SDI)","相邻两期风格资产权重变动绝对值之和，度量策略一致性",
    ["风格漂移","sdi","sds","fsds","漂移"],
    "相邻期风格权重变动（Chan et al. 2002；寇宗来2020 Fsds；易力2021 SDS），漂移大→策略不一致。",
    "论文 <b>SDI</b> = Σ|wₖ,ₜ − wₖ,ₜ₋₁|（规模×价值成长四宫格）。",
    "SDI = Σₖ|wₖ,ₜ − wₖ,ₜ₋₁|")
grp("holding_period","L3","平均持有期限 HH","组合股票的平均持有时间，度量交易频率/耐心",
    ["持有期限","holding period","平均持有","hh"],
    "平均持股期限（Grinblatt & Moskowitz 2001 等）度量交易频率与耐心。",
    "与换手率互补，刻画交易风格。")
grp("momentum_trade","L3","动量/反转交易 Momentum","基金收益动量或反转倾向，度量交易方向持续性",
    ["动量","momentum","反转","reversal","追涨杀跌","外推"],
    "基金收益动量/反转（Grinblatt et al. 1995；易力2021），度量交易方向的持续性。",
    "归入交易风格（与 L5 认知刻画联动）。")
grp("trade_conc","L3","交易集中度 Trade Concentration","交易金额在前 N 只股票上的集中，辅助刻画交易风格",
    ["交易集中度","trade concentration","交易金额集中"],
    "交易金额在前 N 只股票上的集中，辅助刻画交易风格。",
    "归入 L3。")
grp("short_sight","L3","短视/行为异化 Myopic & Alienation","短视投资（击鼓传花类持股）与投资行为异化指标",
    ["短视","parcel","投资行为异化","异化"],
    "短视投资（『击鼓传花类』股票持有比例）；投资行为异化（系统性风险偏离、非系统性风险偏离、行业选择偏离、股票周转率、仓位变化率 ROC）。",
    "归入 L3 交易行为异化刻画。")

# ---------- L4 风险应对层 ----------
grp("arg","L4","风险调整幅度 ARG","各季度风险水平变化量绝对值之和，度量风控主动程度/排名压力下的摇摆",
    ["arg","风险调整幅度","修正隐形","隐形交易","隐形"],
    "申宇等(2013) 隐形交易口径 ARG = Σ|R − (RH − Fee)|（Fee=1.5%+0.25%年化）纠正正负抵消低估；Kacperczyk (2008) return gap 系同源。锦标赛理论（Brown-Harlow-Starks 1996）解释排名压力下的风险调整。",
    "论文 <b>ARG = Σ|RGₜ|</b>，度量风险暴露水平的变动（『承担多少风险』），与 L3 风格漂移 SDI（『持有什么』）作用域不同。",
    "ARG = Σₜ|RGₜ|")
grp("return_vol","L4","收益波动率 Return Volatility","滚动窗口收益率标准差，风险管理的結果性指标",
    ["收益波动率","return volatility","波动率","std","标准差"],
    "基金收益滚动标准差（标准总风险测度）。Brown-Harlow-Starks (1996) 的 RAR=σ₂/σ₁（上下半年标准差比）同属风险维度测度。",
    "论文 <b>return_volatility</b> = 滚动 8 季度收益率标准差（约 2 年窗口），权衡估计精度与时效性。",
    "σ₈Q = √[(1/7)·Σₜ(Rₜ−R̄)²]")
grp("downside_risk","L4","下行风险 Downside Risk","低于目标收益的半方差/下方风险，刻画尾部下行",
    ["下行风险","downside","下方风险","半方差","lower partial"],
    "下行半方差/下方风险（Sortino 框架；Ang et al. 2006 下行风险溢价）。",
    "归入 L4 风险维度。")
grp("beta","L4","系统性风险 Beta","对市场的敏感度，CAPM/因子模型暴露",
    ["beta","β","系统性风险","市场暴露"],
    "CAPM/FF beta 度量系统性风险（市场暴露）。",
    "由因子模型控制（FF5 回归系数）。")
grp("idio_vol","L4","特质波动率 Idiosyncratic Vol","残差收益标准差，非系统性风险",
    ["特质波动率","idiosyncratic","残余波动率","特异性","特质风险"],
    "残差收益标准差（Ang et al. 2006 特质波动率溢价）。",
    "归入风险维度。")
grp("max_drawdown","L4","最大回撤 Max Drawdown","峰值到谷值最大跌幅，直观风险度量",
    ["最大回撤","drawdown","mdd"],
    "峰值到谷值最大跌幅（风险管理常用）。",
    "归入 L4 风险维度。")
grp("var","L4","在险价值 VaR/ES","历史/参数 VaR、预期短缺，尾部风险",
    ["var","在险价值","风险价值","尾部","es","条件尾部"],
    "历史/参数 VaR、预期短缺（尾部风险测度）。",
    "归入 L4 尾部风险。")
grp("sharpe","L4","风险调整收益 Sharpe/Sortino","单位风险所获超额收益，绩效风险调整",
    ["sharpe","夏普","sortino","风险调整收益","信息比率","风险调整后"],
    "Sharpe/Sortino/信息比率度量风险调整后绩效（Jensen 1967 alpha 同属）。",
    "与 FF5 alpha 衔接（因变量）。")
grp("vol_timing","L4","波动率/市场择时 Timing","波动率择时或市场择时能力",
    ["波动率择时","volatility timing","择时","市场择时"],
    "波动率择时（Busse 1999）；市场择时（Henriksson-Merton 1981）。",
    "用于 RiskAsym 构念纯化（控制择时，RA 对择时+规模正交化后截面 t=6.26 仍显著）。")
grp("rar","L4","风险变化比 RAR","上下半年波动率之比，锦标赛框架下的风险调整",
    ["rar","风险变化","上下半年标准差比"],
    "Brown-Harlow-Starks (1996) RAR = σ₂/σ₁（上下半年波动率比），度量风险调整方向。",
    "与 ARG 同属 L4 风险调整；ARG 为其跨期绝对值加总的近亲。")
grp("tournament","L4","锦标赛 Tournament RTN","排名压力下的风险调整动机",
    ["锦标赛","tournament","rtn","排名"],
    "锦标赛理论解释下半年风险调整（Brown-Harlow-Starks 1996）。",
    "归入 ARG 动机背景。")
grp("pumping","L4","粉饰/窗饰 Pumping","季末粉饰持仓抬高短期业绩",
    ["粉饰","pumping","窗饰","window dressing","洗售"],
    "季末粉饰/窗饰（window dressing）抬高短期业绩（Carhart 等）。",
    "归入 L4 操纵性风险。")
grp("crash","L4","暴跌风险 Crash","收益左偏/崩盘风险，尾部下行",
    ["暴跌","crash","崩盘","尾部下行","左偏"],
    "崩盘风险/收益左偏（Chen et al. 2001；基金暴跌风险）。",
    "归入 L4 尾部风险。")

# ---------- L5 认知行为层 ----------
grp("de","L5","处置效应 Disposition Effect (DE)","盈亏状态下的卖出倾向偏差：售盈持亏(DE>0)或其反向(DE<0)",
    ["处置效应","disposition","pgr","plr","de"],
    "Odean (1998, JF) PGR−PLR 范式；Shefrin & Statman (1985)；Grinblatt & Han (2005, JFE) PPD；李学峰(2011/2013)。DE = PGR − PLR，PGR=盈利股实现卖出/(实现+持有)，PLR=亏损股同理。",
    "论文 <b>DE = PGR − PLR</b>（季度持仓快照口径，保守下界）；PGR=0.891<PLR=0.919 呈反向处置。季中交易不可观测使 |DE| 向零衰减，故方向性结论依赖组内效应（t=−3.64）而非 PGR/PLR 绝对水平。",
    "DE = PGR − PLR")
grp("lsv","L5","交易趋同度 LSV (羊群)","相对同业的买卖方向趋同/反向程度",
    ["lsv","交易趋同","羊群","herding","uhm","shm","趋同","跟风"],
    "Lakonishok, Shleifer & Vishny (1992, JFE) LSV；Wermers (1999, JF) BHM/SHM；祁斌2006、魏立波2010 等为修正应用。LSV = |p_j − p̄_t| − AF（AF=零假设期望偏离）。经典语义为羊群强度(>0 跟随市场)。",
    "论文 <b>LSV = |p_j − p̄_t| − AF</b>，样本整体为负→准确含义为『交易趋同度』（回归正系数读作『越贴近市场共识业绩越好』）。纠正幸存者偏差后截面符号反转，按『选择敏感的描述性证据(B−)』处理。",
    "LSV = |pⱼ − p̄ₜ| − AF")
grp("riskasym","L5","条件波动率不对称 RiskAsym","盈利期与亏损期风险承担的差异（赌资效应 vs 锦标赛效应）",
    ["riskasym","条件波动率不对称","波动率不对称","不对称"],
    "Brown, Harlow & Starks (1996, JF) 问题意识（盈利/亏损期风险差异）；前景理论价值函数不对称。RiskAsym = σ(盈利期收益) − σ(亏损期收益)。",
    "论文 <b>RiskAsym = σ(盈利期季度收益) − σ(亏损期季度收益)</b>。理论解释不唯一（风险偏好 or 择时能力），故配 Henriksson–Merton 择时控制+构念纯化（对择时与规模正交化后截面 t=6.26、前向4季 t=4.27 仍显著）。",
    "RiskAsym = σ(gain) − σ(loss)")
# 注：原 L5『过度自信 Overconfidence』与 L3『过度交易 OCI』计算方法完全相同（均 OCI=(TO−TŌ)/σ(TO)），
#     已合并入 L3 的 oci 条目，此处不再单列。
grp("loss_aversion","L5","损失厌恶/前景理论 Loss Aversion","损失规避与参考点依赖，认知偏差的理论基础",
    ["损失厌恶","loss aversion","前景理论","prospect","参考点"],
    "前景理论损失规避（Kahneman & Tversky 1979）；参考点依赖（Barberis & Huang 2001）。",
    "为 DE/RiskAsym 的理论基础（L5 三指标理论锚点）。")
grp("attention","L5","有限关注/注意力 Attention","注意力驱动交易，有限关注偏差",
    ["注意力","attention","有限关注","limited attention","关注度","媒体"],
    "有限关注/注意力驱动交易（Barber & Odean 2008；基金关注度）。",
    "归入认知刻画（描述性）。")
grp("home_bias","L5","本地/熟悉度偏好 Home Bias","本地或熟悉标的偏好，熟悉度偏差",
    ["本地偏好","home bias","熟悉度","local bias","地域"],
    "本地/熟悉度偏好（Huberman 2001；基金本地偏好）。",
    "归入认知偏差。")
grp("anchoring","L5","锚定 Anchoring","锚定于买入成本/历史高价，参考点效应",
    ["锚定","anchoring","参考价","成本锚"],
    "锚定于买入成本/历史高价（前景理论参考点；Odean 处置效应机制）。",
    "为 DE 的机制解释。")
grp("representativeness","L5","代表性/外推偏差 Representativeness","基于近期模式的过度外推",
    ["代表性","representativeness","外推","extrapolation"],
    "代表性偏差/外推（Barberis et al. 1998；基金外推交易）。",
    "归入认知偏差。")
grp("ml_behavior","L5","机器学习行为分类 ML Behavior","AI/ML 识别行为偏差/行为画像",
    ["机器学习","machine learning","ai","行为分类","聚类","画像"],
    "AI/ML 识别行为偏差（12_AI_Manage_Behavioural_Biases；15_Dissecting_AI_Trading）。",
    "归入方法工具（描述性）。")

# ---------- M 方法论层 ----------
grp("factor_models","M","因子模型/Alpha FF3-FF5-Carhart","多因子模型与时序 alpha，因变量构造",
    ["ff5","ff3","carhart","因子","fama","alpha","五因子","四因子","三因子"],
    "FF3 (Fama-French 1993)；Carhart 四因子 (1997)；FF5 (Fama-French 2015)。对每只基金用月度超额收益做时序回归，截距即 alpha。",
    "论文以 <b>FF5 alpha</b> 为基准因变量（系统性风险控制最完整、RA 信号最干净）；FF3/FF4 作稳健对照（RA 在三种口径均显著，FF5 下最强）。",
    "r−r_f = α + β·factors + ε")
grp("fama_macbeth","M","Fama-MacBeth 截面回归","两阶段截面回归+时序平均 t 值",
    ["fama-macbeth","fm","截面回归","两阶段"],
    "Fama-MacBeth 截面回归 + 时序平均 t 值（标准资产定价实证）。",
    "用于 M0→M4 递进回归（截面 N=297，HC1）。")
grp("clustered_se","M","聚类/稳健标准误 Clustered SE","基金层面聚类或 HC1 稳健 SE",
    ["聚类","cluster","稳健","hc1","标准误"],
    "基金层面聚类 SE / HC1 稳健标准误（Petersen 2009）。",
    "截面用 HC1、面板用基金层面聚类 SE。")
grp("oster","M","Oster 遗漏变量界","遗漏变量稳健性界 δ",
    ["oster","遗漏变量","δ","敏感性"],
    "Oster (2019) 遗漏变量界 δ 检验稳健性。",
    "δ: DE 1.03 / LSV 1.19 / RA 2.25，均>1，排除不可观测遗漏变量。")
grp("sensemakr","M","sensemakr 敏感性","近似遗漏变量敏感性分析",
    ["sensemakr","近似遗漏"],
    "sensemakr 稳健性/近似遗漏变量检验。",
    "归入敏感性分析。")
grp("quantile","M","分位数回归 Quantile","条件分布异质，捕捉分位效应",
    ["分位数","quantile","条件分布"],
    "分位数回归捕捉条件分布异质。",
    "归入稳健性。")
grp("iv_2sls","M","工具变量/2SLS","滞后行为作 IV 处理内生性",
    ["工具变量","iv","2sls","滞后","内生"],
    "滞后行为作 IV（2SLS）；Hansen J 检验拒绝外生性→放弃因果。",
    "论文据此主动放弃全部因果声称，全篇最高只到 B 级（DE 组内 B+）。")
grp("oos","M","样本外/证伪 OOS & Robustness","样本外预测、置换安慰剂、规范曲线、BH-FDR",
    ["样本外","oos","证伪","置换","安慰剂","bootstrap","规范曲线","bh-fdr"],
    "样本外预测、置换安慰剂（2,000 次）、60 设定规范曲线（SNS 2020）、BH-FDR 多重检验校正。",
    "PS 样本外 Q5−Q1=4.1%—5.6%/季（置换 p<0.0005）；证伪检验表。")
grp("bootstrap","M","两阶段 Bootstrap","校正生成因变量 SE 低估",
    ["两阶段","校正下限"],
    "两阶段 bootstrap 校正生成因变量（FF5 alpha）的第一阶段不确定性传入第二阶段。",
    "给出保守下限 t 值（RA≈1.8、LSV≈2.1、DE≈−0.6）。")
grp("perf_outcome","M","基金业绩/Alpha（多种度量）","净值收益、Sharpe/Treynor、Jensen/FF/Carhart α、DEA、序数回报等业绩度量",
    ["基金业绩","jensen","treynor","超效率","序数回报","复权净值","异常收益","业绩持续性","基准调整后","净值收益率","α","rank","原始/复权"],
    "文献以净值增长率、Sharpe/Treynor、Jensen's α(CAPM)、FF3/Carhart α、超效率 DEA、序数回报 Rank、DGTW 特征调整异常收益等多种方式度量基金业绩。",
    "论文以 FF5 alpha 为统一因变量（基准），避免多业绩度量口径混杂；其余作为稳健性/描述。")

# 核心指标 ★ 标签
CORE = {
    "arg": "ARG", "return_gap": "RG", "return_vol": "RVOL",
    "de": "DE", "lsv": "LSV", "riskasym": "RISKASYM",
}

# 用户指定强调的变量（蓝条/★ 标记仅限于此集合）
# 17 个：L1 五维(tenure/fund_age/education/age/cert) + L2 三维(active_share/ici/hhi)
#        + L3 三维(turnover/oci/style_drift) + L4 三核心(return_gap/arg/return_vol)
#        + L5 三核心(de/lsv/riskasym)。其中六大核心(ARG/RG/RVOL/DE/LSV/RISKASYM) 额外标 ★
EMPHASIS = {
    "tenure","fund_age","education","age","cert",
    "active_share","ici","hhi",
    "turnover","oci","style_drift",
    "return_gap","arg","return_vol",
    "de","lsv","riskasym",
}

# ============================================================
# 3b. 14 个强调变量的「原文计算讲解」+ 截图路径
# ============================================================
SHOTS_DIR = os.path.join(BASE, "shots")

def _img_b64(key):
    """读取 shots/<key>.png 并返回 data:image/png;base64,..."""
    p = os.path.join(SHOTS_DIR, key + ".png")
    if not os.path.exists(p):
        return ""
    import base64
    with open(p, "rb") as f:
        return "data:image/png;base64," + base64.b64encode(f.read()).decode()

VAR_DETAIL = {
    "tenure": dict(
        title="从业/任期 Tenure — 原文计算讲解",
        src_paper="Li & Li (2018) 《China's Fund Manager Characteristics and Fund Performance》; Chevalier & Ellison (1999, QJE)",
        calc_html=(
            "<p><b>文献度量方式：</b>Li & Li (2018) 将 <code>tenure</code> 定义为基金经理"
            "在当前基金任职的累计时间（年），作为人力资本积累的代理变量。"
            "具体而言，<b>「tenure measures the fund manager's time spent in the management"
            " of the fund」</b>，<b>「experience refers to the fund manager's years working"
            " in investment and related industries」</b>。文献普遍以任职年限（连续变量）或"
            "从业年限（对数化）刻画经验效应——Chevalier & Ellison (1999) 发现年轻经理"
            "业绩-流量关系更敏感（职业忧虑更强），而经验丰富的经理可能因能力固化"
            "而表现下降（倒 U 型）。</p>"
            "<p><b>本论文做法：</b><code>mgr_total_tenure_v2</code> = 经理首次任职至观测时点"
            "的累计天数（akshare <code>fund_manager_em</code>）。取天数而非年份以保留精度；"
            "作控制变量，不预设方向。</p>"
        ),
    ),
    "fund_age": dict(
        title="基金年龄 Fund Age — 原文计算讲解",
        src_paper="Li & Li (2018); Golec (1996) 控制变量传统",
        calc_html=(
            "<p><b>文献度量方式：</b>Golec (1996) 首次系统使用基金成立年限（Fund Age）"
            "作为控制变量，用于剥离策略成熟度与规模臃肿效应。基金年龄反映基金的存续期长度："
            "老基金可能因品牌优势吸引资金流（明星效应），也可能因规模过大而灵活性下降。"
            "Li & Li (2018) 在中国样本中纳入 <code>fund term</code>（基金存续期）与 "
            "<code>total fund assets (yuan)</code> 等控制变量。</p>"
            "<p><b>本论文做法：</b><code>log_fund_age</code> = ln(基金成立至观测期的月数)。"
            "取对数缓解右偏（新基金多、老基金少的长尾分布）。为自定义控制变量，"
            "用于控制基金层面的时间固定效应。</p>"
        ),
    ),
    "education": dict(
        title="学历/学位 Education — 原文计算讲解",
        src_paper="吴栩 (2017); 于静 (2013); 赵秀娟 (2010); Golec (1996)",
        calc_html=(
            "<p><b>文献度量方式：</b>学历是经典的人力资本信号变量。吴栩 (2017) 采用分类变量："
            "是否拥有硕士及以上学位（<code>X₁=1</code> 表示硕士/博士）、毕业院校层次（985/211）、"
            "MBA 教育背景、CPA/CFA 专业证书等，共 10 个个人特征变量进入多元回归模型。"
            "Golec (1996) 以 MBA dummy 度量商科教育背景。于静 (2013) 与赵秀娟 (2010) 同样将学历"
            "设为有序分类变量（学士/硕士/博士）作控制。</p>"
            "<p><b>本论文做法：</b>并入 L1 教育背景控制组，与院校（名校/985）、CFA/MBA 资质一并"
            "纳入。采用分类哑变量（硕士=1, 博士=2, 其他=0）或连续教育年限指标。</p>"
        ),
    ),
    "age": dict(
        title="经理年龄 Age — 原文计算讲解",
        src_paper="Li & Li (2018); 吴栩 (2017); 于静 (2013)",
        calc_html=(
            '<p><b>文献度量方式：</b>Li & Li (2018) 明确定义：<b>「"age" is set as a continuous variable」</b>，'
            "取基金经理的周岁年龄。该样本中中国基金经理平均年龄 38.92 岁（远低于美国同行的 44.18 岁）。"
            "年龄与任期互补：年龄大→可能任期长但未必（中途转行）；年龄小→职业忧虑强但学习能力高。"
            "吴栩 (2017) 和于静 (2013) 同样将年龄作为人口学控制变量纳入回归。</p>"
            "<p><b>本论文做法：</b>直接取 akshare <code>fund_manager_em</code> 中的经理出生日期推算周岁年龄，"
            "作连续控制变量（与 tenure 互补但不完全共线）。</p>"
        ),
    ),
    "cert": dict(
        title="专业资质 CFA/MBA — 原文计算讲解",
        src_paper="08_L1_CFA_MBA_Mutual_Fund_Performance_2017; 吴栩 (2017); Golec (1996)",
        calc_html=(
            "<p><b>文献度量方式：</b>CFA（特许金融分析师）/MBA/CPA 等专业资质作为专业训练信号。"
            "CFA/MBA Mutual Fund Performance (2017) 专门研究持有 CFA 或 MBA 学位的基金经理是否表现更优。"
            "结果显示：CFA 持证者占比 11.92%（N=1,393），MBA 占比 14.86%。"
            "吴栩 (2017) 将 CFA/CPA 作为哑变量纳入 10 维个人特征回归。"
            "Golec (1996) 以 MBA dummy 捕捉商科训练效应。</p>"
            "<p><b>本论文做法：</b>作分类控制变量（CFA=1 / MBA=1 / 其他资质=1），"
            "归入 L1 教育背景与专业资质控制组。</p>"
        ),
    ),
    "active_share": dict(
        title="主动份额 Active Share (AS) — 原文计算讲解",
        src_paper="Cremers & Petajisto (2009, RFS) 「How Active Is Your Fund Manager?」",
        calc_html=(
            "<p><b>原文定义（见截图）：</b>Cremers & Petajisto (2009) 提出 Active Share 作为主动管理程度的度量："
            "<b>「we label this measure the Active Share of a portfolio… Active Share can thus be easily"
            " interpreted as the 'fraction of the portfolio that is different from the benchmark index'」</b>。</p>"
            "<p><b>公式：</b><code>AS = (1/2) · Σᵢ |w_{fund,i} − w_{bench,i}|</code> ∈ [0, 1]。</p>"
            "<ul><li>w_{fund,i} = 基金在股票 i 上的持仓权重</li>"
            "<li>w_{bench,i} = 基准指数在股票 i 上的成分股权重</li>"
            "<li>AS = 0 → 完全复制基准（closet indexer）；AS > 0.8 → 高度主动</li></ul>"
            "<p><b>本论文改进：</b><code>AS_improved</code> 以沪深300 + 中证500 合并真实成分股权重为基准重算，"
            "解决单一指数系统性低估主动度的问题（当前管线下截面区分度与原始口径相当，CV约0.15）。</p>"
        ),
    ),
    "ici": dict(
        title="行业集中度 ICI — 原文计算讲解",
        src_paper="Kacperczyk, Sialm & Zheng (2005, JF) 「Industry Concentration of Actively Managed Equity Funds」",
        calc_html=(
            "<p><b>原文定义（见截图公式 ①）：</b>Kacperczyk et al. (2005) 定义 Industry Concentration Index："
            "<br><code>ICI_t = Σⱼ₌₁¹⁰ (w_{j,t} − w̄_{j,t})²</code></p>"
            "<p>其中 w_{j,t} 为基金在行业 j 的配置权重，w̄_{j,t} 为市场组合在行业 j 的权重。"
            "ICI 度量<strong>行业选择的主动性</strong>——偏离市场行业配置的程度越大，ICI 越高。</p>"
            "<p><b>与 HHI 的关系：</b>ICI 与 Herfindahl Index 高度相关（r=0.93），但含义不同："
            "HHI 度量组合本身集中程度（与市场无关），ICI 度量相对市场的行业偏离。"
            "本文同时采用两者（截面相关仅 0.20，VIF 1.25/1.08，近似正交）。</p>"
            "<p><b>本论文做法：</b>沿用 ICI 原始定义，基于申万一级分类（28 行业）计算。</p>"
        ),
    ),
    "hhi": dict(
        title="行业分散度 HHI — 原文计算讲解",
        src_paper="Kacperczyk et al. (2005, JF) Table I Summary Statistics",
        calc_html=(
            "<p><b>原文定义（见截图 Table I Panel A 及脚注 ④）：</b>Kacperczyk (2005) 使用 Herfindahl Index"
            "度量组合的行业集中程度：<code>HI_t = Σᵢ (w_{i,t})²</code>，∈[1/K, 1]，K 为行业数。</p>"
            "<p>脚注明确说明：<b>「The Herfindahl Index is defined as HI_t = Σ(w_i,t)²」</b>，"
            "并指出选用 ICI 而非 HHI 不改变定性结论。</p>"
            "<p><b>关键区分：</b>HHI 是组合内属性（集中度），ICI 是组合 vs 市场的偏离。"
            "一个基金可以 HHI 高（集中在少数行业）但 ICI 低（与市场行业配置一致）。"
            "数学关系：<code>ICI = HHI_基金 + HHI_市场 − 2·Σ(w_i · w̄_i)</code>。</p>"
            "<p><b>本论文做法：</b><code>industry_hhi</code> 自定义，基于申万一级行业权重平方和。</p>"
        ),
    ),
    "turnover": dict(
        title="换手率 Turnover (TO) — 原文计算讲解",
        src_paper="Lan, Wang & Zhang (2015, CFR) 「Do Funds With Shorter Holding Periods Perform Better?」;"
            " Kacperczyk et al. (2008, RFS)",
        calc_html=(
            "<p><b>文献度量方式：</b>Lan et al. (2015) 对比了两种换手率度量："
            "(1) CRSP 报告的年度换手率（基于买卖金额）；(2) 基于持仓计算的换手率。"
            "文中指出：<b>「CRSP normally reports turnover at an annual frequency」</b>，"
            "且 <b>「using either CRSP reported turnover or holdings-based turnover delivers the same message」</b>。</p>"
            "<p><b>标准公式：</b><code>TO = min(买入总额, 卖出总额) / 平均 TNA</code>（Carhart 1997）。"
            "取 min 是为了剔除申购赎回引起的被动交易，保留主动交易信号。"
            "高换手通常侵蚀业绩（交易成本 + 过度自信）。</p>"
            "<p><b>本论文做法：</b><code>TO_calc</code> 取 min 剔除申赎被动交易；"
            "并由 TO 派生 OCI（过度交易指数）。</p>"
        ),
    ),
    "oci": dict(
        title="过度自信/过度交易 Overconfidence (OCI) — 原文计算讲解",
        src_paper="Statman, Thorley & Vorkink (2006); Gervais & Odean (2001); L4 overconfidence PDF (experience × overconfidence herding)",
        calc_html=(
            "<p><b>理论来源：</b>过度自信的经典代理是 OCI = (TO − T̄O)/σ(TO)，源自 Statman 等 (2006)。"
            "该指标将当期换手率相对于基金自身历史标准化：>0 表示当期交易超出自身常态，"
            "暗示过度自信驱动的过度交易。Gervais & Odean (2001) 自我归因偏差、性别/经验与过度自信"
            "（11_L1_Gender；吴栩2017）、实验测度（BRET 炸弹风险任务）均指向同一构念。</p>"
            "<p><b>文献背景（见截图）：</b>L4 来源 PDF 讨论了经验与过度自信的关系："
            "<b>「young inexperienced funds managers would be more overconfident and would choose,"
            " therefore, riskier portfolios」</b>（引用 Odean 1998; Locke & Mann 2001 等）。"
            "过度自信随经验递减是行为金融的核心发现之一。</p>"
            "<p><b>本论文做法：</b>OCI 由 TO 派生：<code>(TO − T̄_TO) / σ_TO(TO)</code>，"
            "对基金自身历史（前 4–8 季）标准化。原 L3『过度交易 OCI』与 L5『过度自信 Overconfidence』"
            "计算方法完全相同，已合并为本统一条目：作为 L3 交易行为（行为表现）与 L5 过度自信（认知驱动）"
            "的同一测度，L5 认知层不再单列。</p>"
        ),
    ),
    "style_drift": dict(
        title="风格漂移 Style Drift (SDI) — 原文计算讲解",
        src_paper="寇宗来、王飞 (2020, 金融学季刊) 「基金业绩如何影响风格漂移和经理离职?」;"
            " Chan et al. (2002); 易力 (2021)",
        calc_html=(
            "<p><b>原文定义（见截图）：</b>寇宗来 (2020) 开篇即定义风格漂移："
            "<b>「许多基金往往'挂羊头卖狗肉'，在实际操作中显著违背其在募集资金时预先设定的投资风格，"
            "即存在'风格漂移'现象」</b>。文中引用 Chan et al. (1999)、Yin et al. (2017)、肖继辉等 (2015)"
            "等文献，指出<strong>现有研究未提供统一的分析框架来解释各种因素到底是以何种方式影响基金风格漂移</strong>。</p>"
            "<p><b>测度方法：</b>相邻两期风格资产权重变动绝对值之和。"
            "本文采用 Fama-French 四宫格（规模×价值成长）划分风格："
            "<code>SDI = Σ_k |w_{k,t} − w_{k,t−1}|</code>，k ∈ {小盘成长, 小盘价值, 大盘成长, 大盘价值}。</p>"
            "<p><b>本论文做法：</b><code>SDI</code> 基于四宫格风格权重变动计算，"
            "度量策略一致性（漂移大→策略不一致→可能暗示追逐热点或被迫调仓）。</p>"
        ),
    ),
    "return_gap": dict(
        title="收益缺口 Return Gap (RG) — 原文计算讲解",
        src_paper="Kacperczyk, Sialm & Zheng (2008, RFS) 「Unobserved Actions of Mutual Funds」",
        calc_html=(
            "<p><b>原文定义（见截图）：</b>Kacperczyk et al. (2008) 的 Return Gap 衡量披露间歇期内"
            "隐形交易的净效应。截图中显示：<b>「the return gap after adjusting for disclosed expenses equals"
            " −1.0 basis points per month and is not significantly different from zero」</b>，"
            "说明总体上隐藏成本与中间交易收益大致相抵。</p>"
            "<p><b>公式：</b><code>RG = (RF − EXP) − RH</code></p>"
            "<ul><li>RF = 投资者实际净收益（扣费后）</li>"
            "<li>RH = 按上期披露持仓构建的买入持有毛收益（buy-and-hold return）</li>"
            "<li>EXP = 费用率（expense ratio ≈ 0.88%/年）</li>"
            "<li>RG > 0 → 隐形交易创造超额；RG < 0 → 隐藏成本占优</li></ul>"
            "<p><b>本论文衔接：</b>RG 是 ARG 的构建基础：<code>ARG = Σ_t |RG_t|</code>（跨期绝对值加总，"
            "纠正正负抵消低估）。详见 §九 ARG 详解。</p>"
        ),
    ),
    "arg": dict(
        title="风险调整幅度 ARG — 原文计算讲解",
        src_paper="申宇等 (2013, 管理世界) 「隐形交易与基金业绩」;"
            " Kacperczyk et al. (2008, RFS)",
        calc_html=(
            "<p><b>原文定义（见截图 Table 8 回归结果）：</b>申宇 (2013) 修正隐形交易口径 ARG，"
            "纠正 Kacperczyk (2008) RG 正负抵消的低估问题。截图中 Table 8 显示 ARG 系数为 "
            "<b>5.004*** (t=2.79)</b>，表明风险调整幅度越大，基金业绩越好。</p>"
            "<p><b>公式：</b><code>ARG = Σ_t |R_t − (RH_t − Fee)|</code></p>"
            "<ul><li>Fee = 1.5% + 0.25%（年化管理费+交易成本）</li>"
            "<li>|·| 绝对值防止正负 RG 抵消</li>"
            "<li>跨季加总得到年度风险调整幅度</li></ul>"
            "<p><b>理论动机：</b>Brown-Harlow-Starks (1996) 锦标赛理论——排名压力下的下半年风险调整。"
            "ARG 度量「承担多少风险的变化」，与 SDI（持有什么变化）作用域不同。</p>"
            "<p><b>本论文做法：</b><code>ARG = Σ|RG_t|</code>，由 RG 派生。★ 核心指标。</p>"
        ),
    ),
    "return_vol": dict(
        title="收益波动率 Return Volatility — 原文计算讲解",
        src_paper="蒋志平、田益祥、郑焕刚 (2013) 「业绩波动率、投资者资金流与基金经理冒险行为」;"
            " Ang, Chen & Xing (2006, RFS) Downside Risk",
        calc_html=(
            "<p><b>原文定义（见截图）：</b>蒋志平等 (2013) 专门研究<strong>基金业绩波动率</strong>对投资者行为的影响。"
            "截图中开篇定义：<b>「本文构建了一个投资者理性预期的解析模型……研究了基金业绩波动率对"
            "基金投资者资金流入的影响」</b>。研究发现我国投资者并未表现出期望中的「风险厌恶」（负相关），"
            "反而呈现一定程度的<strong>「风险追逐」</strong>倾向。</p>"
            "<p><b>标准公式：</b><code>σ_{8Q} = √[(1/(8−1)) · Σ_{t=1}^8 (R_t − R̄)²]</code></p>"
            "<ul><li>滚动 8 个季度收益率的标准差（约 2 年窗口）</li>"
            "<li>权衡估计精度（窗口越长越准）与时效性（窗口越短越灵敏）</li>"
            "<li>Brown-Harlow-Starks (1996) RAR = σ₂/σ₁（上下半年标准差比）同属风险维度</li></ul>"
            "<p><b>本论文做法：</b><code>return_volatility</code> = 滚动 8Q 收益率标准差。★ 核心指标。</p>"
        ),
    ),
}

# ============================================================
# 4. 语义归并：将每条目映射到规范 group
# ============================================================
def match_group(e):
    hay = (e.get("name","") + " " + e.get("def","") + " " + e.get("formula","")).lower()
    best = None
    for g in G:
        for kw in g["kws"]:
            if kw.lower() in hay:
                best = g; break
        if best: break
    return best

groups_by_key = OrderedDict()
for g in G:
    groups_by_key[g["key"]] = {"g": g, "entries": [], "sources": []}

unmapped = []
for e in ALL:
    g = match_group(e)
    if g is None:
        unmapped.append(e)
        continue
    key = g["key"]
    groups_by_key[key]["entries"].append(e)
    for s in e.get("sources", []):
        if s and s not in groups_by_key[key]["sources"]:
            groups_by_key[key]["sources"].append(s)

# 未归并条目按来源层归入"其他"组
other_by_layer = {}
for e in unmapped:
    lay = e["src_layer"]
    other_by_layer.setdefault(lay, []).append(e)
    grp_key = "other_" + lay
    if grp_key not in groups_by_key:
        G.append({"key": grp_key, "layer": lay, "name": "其他（未单独归并）",
                  "meaning": "文献中提及但未归入上述规范变量的测度", "kws": [],
                  "how": "文献中的其他相关测度，按实际含义可进一步拆分。", "ours": "归入本层，按需补充。", "formula": ""})
        groups_by_key[grp_key] = {"g": G[-1], "entries": [], "sources": []}
    groups_by_key[grp_key]["entries"].append(e)
    for s in e.get("sources", []):
        if s and s not in groups_by_key[grp_key]["sources"]:
            groups_by_key[grp_key]["sources"].append(s)

# ============================================================
# 5. 渲染
# ============================================================
def esc(x):
    return html.escape("" if x is None else str(x))

def fcell(formula):
    if not formula or not formula.strip():
        return '<span class="muted">—</span>'
    return '<code class="fx">' + esc(formula) + '</code>'

def src_cell(sources):
    if not sources:
        return '<span class="muted">—</span>'
    shown = sources[:6]
    s = "；".join(esc(x) for x in shown)
    if len(sources) > 6:
        s += ' 等 %d 篇' % len(sources)
    return s

LAYER_NAME = {
    "L1": "L1 背景特征层", "L2": "L2 持仓偏离层", "L3": "L3 交易行为层",
    "L4": "L4 风险应对层", "L5": "L5 认知行为层", "M": "M 方法论与识别检验层",
}
LAYER_CLS = {"L1": "l1", "L2": "l2", "L3": "l3", "L4": "l4", "L5": "l5", "M": "lm"}

def render_layer_table(layer):
    rows_html = []
    n_ours = 0
    n_core = 0
    n_aux = 0
    for key, val in groups_by_key.items():
        g = val["g"]
        if g["layer"] != layer:
            continue
        # ---- 辅助/控制测度（未纳入本框架）：降级为灰行、去强调 ----
        if key.startswith("other_"):
            cnt = len(val["entries"])
            n_aux += cnt
            name = "辅助 / 控制测度（未纳入本框架）· 本层 %d 项" % cnt
            meaning = "文献中出现的控制变量、哑变量与辅助指标；本论文未将其作为独立自变量，故不单独强调。"
            src = src_cell(val["sources"])
            rows_html.append(
                '<tr class="aux"><td><b>%s</b></td><td>%s</td>'
                '<td class="how"><span class="muted">—</span></td>'
                '<td class="ourscol"><span class="muted">不纳入本框架（仅作文献覆盖说明）</span></td>'
                '<td class="src">%s</td></tr>' % (esc(name), esc(meaning), src))
            continue
        n_ours += 1
        core = CORE.get(key)
        star = ('<span class="star" title="重点指标">★ %s</span>' % core) if (core and key in EMPHASIS) else ""
        if key in EMPHASIS:
            if core:
                n_core += 1
                trcls = ' class="emp"'
            else:
                trcls = ' class="ours"'
        else:
            trcls = ''
        how_html = g["how"]
        if g["formula"]:
            how_html += '<div class="eqmini">' + fcell(g["formula"]) + '</div>'
        ours_html = g["ours"]
        src = src_cell(val["sources"])
        rows_html.append(
            '<tr%s><td><b>%s</b>%s</td>'
            '<td>%s</td><td class="how">%s</td><td class="ourscol">%s</td>'
            '<td class="src">%s</td></tr>' % (
                trcls, esc(g["name"]), star,
                esc(g["meaning"]), how_html, ours_html, src
            ))
        # ---- 嵌入原文截图 + 计算讲解（仅 14 个强调变量）----
        if key in VAR_DETAIL:
            vd = VAR_DETAIL[key]
            img = _img_b64(key)
            img_tag = ('<div class="shot-wrap"><img src="%s" alt="原文截图：%s" '
                       'loading="lazy"/></div>' % (img, esc(vd["src_paper"]))) if img else ""
            detail = (
                '<tr class="detail-row"><td colspan="5">'
                '<div class="var-detail">'
                '<div class="detail-head">📖 %s</div>'
                '<div class="detail-body">%s%s'
                '<p class="detail-src">📄 文献来源：%s</p></div></div></td></tr>'
                % (esc(vd["title"]), img_tag, vd["calc_html"], esc(vd["src_paper"]))
            )
            rows_html.append(detail)
    table = ('<div class="tbl-wrap"><table class="master"><thead><tr>'
             '<th style="width:18%">自变量</th>'
             '<th style="width:20%">测什么（含义）</th>'
             '<th style="width:30%">文献是怎么做的（构建/计算）</th>'
             '<th style="width:16%">本论文做法（与文献异同）</th>'
             '<th style="width:16%">文献来源</th>'
             '</tr></thead><tbody>' + "".join(rows_html) + '</tbody></table></div>')
    return table, n_ours, n_core, n_aux

# ---- CSS ----
CSS = """
:root{
  --bg:#ffffff; --fg:#1f2a37; --muted:#64748b; --line:#e3e8ef; --soft:#f7fafc;
  --brand:#16407a; --brand2:#0b6e4f; --accent:#b4231f;
  --l1:#16407a; --l2:#0b6e4f; --l3:#9a4b00; --l4:#6b3fa0; --l5:#0d7a8a; --lm:#c2410c;
  --emp:#fff7ed; --empb:#f97316; --toc-h:70px;
}
*{box-sizing:border-box}
body{margin:0;font-family:"Segoe UI","Microsoft YaHei","PingFang SC",system-ui,sans-serif;
     color:var(--fg);background:var(--bg);line-height:1.78;font-size:15px}
.wrap{max-width:1280px;margin:0 auto;padding:30px 30px 80px}
header.top{border-bottom:3px solid var(--brand);padding-bottom:16px;margin-bottom:6px}
header.top h1{font-size:25px;margin:0 0 6px;color:var(--brand);letter-spacing:.4px}
header.top .sub{color:var(--muted);font-size:14px}
.meta{margin-top:10px;font-size:13px;color:var(--muted)}
nav.toc{position:sticky;top:0;background:rgba(255,255,255,.95);backdrop-filter:blur(6px);
        border:1px solid var(--line);border-radius:10px;padding:12px 16px;margin:18px 0 26px;z-index:20;
        box-shadow:0 2px 10px rgba(20,40,80,.05)}
nav.toc b{color:var(--brand);margin-right:4px}
nav.toc a{color:var(--fg);text-decoration:none;margin:0 8px 4px 0;display:inline-block;font-size:13px}
nav.toc a:hover{color:var(--brand);text-decoration:underline}
h2{font-size:21px;color:var(--brand);border-left:6px solid var(--brand);padding-left:12px;margin:36px 0 14px;scroll-margin-top:calc(var(--toc-h,70px) + 10px)}
h3{font-size:17px;color:var(--brand2);margin:24px 0 10px}
.note{background:var(--soft);border:1px solid var(--line);border-left:4px solid var(--brand);
      border-radius:8px;padding:12px 16px;margin:14px 0;font-size:14px}
.layer-tag{display:inline-block;font-size:12px;font-weight:700;color:#fff;border-radius:5px;padding:1px 8px;margin-right:6px;vertical-align:middle}
.l1{background:var(--l1)} .l2{background:var(--l2)} .l3{background:var(--l3)}
.l4{background:var(--l4)} .l5{background:var(--l5)} .lm{background:var(--lm)}
.tbl-wrap{margin:12px 0 22px;border-radius:10px;border:1px solid var(--line)}
table.master{border-collapse:collapse;width:100%;font-size:13px;margin:0}
table.master th,table.master td{border:1px solid var(--line);padding:8px 10px;vertical-align:top;text-align:left}
table.master thead th{background:linear-gradient(180deg,#eef4fb,#e2ecf8);color:var(--brand);
  font-weight:700;position:sticky;top:var(--toc-h,70px);z-index:5;border-bottom:2px solid #c9d8ee}
table.master tbody tr:nth-child(even) td{background:#fafcff}
table.master tbody tr:hover td{background:#eef5ff}
table.master td.src{font-size:11.5px;color:#3b5168}
table.master td.how{font-size:12.5px}
table.master td.ourscol{font-size:12.5px;color:#0b6e4f}
.vtype{font-size:11px;color:var(--muted);margin-top:3px}
.eqmini{margin-top:6px}
table.master tr.ours td{box-shadow:inset 3px 0 0 var(--brand);background:#fbfdff}
table.master tr.ours:nth-child(even) td{background:#f4f9ff}
table.master tr.emp td{background:var(--emp)!important;box-shadow:inset 4px 0 0 var(--empb)}
table.master tr.aux td{background:#fafafa;color:var(--muted);font-size:12.5px;box-shadow:inset 3px 0 0 #cfcfcf}
table.master tr.aux td b{color:#8a8a8a;font-weight:600}
table.master tr.aux:hover td{background:#f2f2f2}
.star{display:inline-block;margin-left:6px;font-size:11px;font-weight:700;color:#fff;
  background:var(--empb);border-radius:10px;padding:1px 7px;vertical-align:middle}
code.fx{background:#eef2f7;padding:2px 6px;border-radius:5px;font-family:"Cambria Math","Consolas",monospace;
  font-size:12.5px;color:#0a3a66;white-space:nowrap}
.muted{color:var(--muted)}
.legend{font-size:13px;margin-top:8px}
.legend .ok{color:var(--brand2);font-weight:600}
.legend .warn{color:var(--accent);font-weight:600}
.legend .emp{color:var(--empb);font-weight:600}
/* ---- §一 总览统计表 + 图例 ---- */
table.master.ov{font-size:13.5px;margin:10px 0 4px}
table.master.ov th{background:#eef4fb;color:var(--brand)}
table.master.ov td:first-child{white-space:nowrap}
table.master.ov tr.ov-tot td{background:#eaf1fb;font-size:14px;border-top:2px solid #c9d8ee}
.conventions{background:#f0f7ff;border:1px solid #cfe0f5;border-radius:8px;padding:11px 15px;
             margin:14px 0 4px;font-size:13px;line-height:1.95}
.conventions .lg{font-weight:700;margin:0 2px;white-space:nowrap}
.conventions .lg.emp{color:var(--empb)}
.conventions .lg.star{color:var(--empb)}
.conventions .lg.aux{color:#8a8a8a}
/* ---- 原文截图 + 计算讲解（14 个强调变量）---- */
table.master tr.detail-row td{padding:0;border-left:none;border-right:none}
.var-detail{margin:0;padding:16px 20px;background:#fafbff;border-top:2px solid #e8eef6}
.detail-head{font-size:14px;font-weight:700;color:var(--brand);margin-bottom:10px;
             display:flex;align-items:center;gap:6px}
.detail-body{font-size:13px;line-height:1.75;color:#334155}
.detail-body p{margin:6px 0}
.detail-body ul{margin:4px 0;padding-left:20px}
.detail-body li{margin:2px 0}
.detail-body code{background:#eef2f7;padding:1px 5px;border-radius:4px;font-size:12.3px;color:#0a3a66}
.detail-src{margin-top:10px;padding-top:8px;border-top:1px dashed #d0d7de;font-size:12px;color:var(--muted)}
.shot-wrap{margin:10px 0;text-align:center}
.shot-wrap img{max-width:100%;height:auto;border:1px solid #d0d7de;border-radius:6px;box-shadow:0 1px 6px rgba(0,0,0,.08)}
footer{margin-top:50px;border-top:1px solid var(--line);padding-top:14px;color:var(--muted);font-size:12.5px}
#search{width:100%;padding:10px 14px;font-size:14px;border:1px solid var(--line);border-radius:8px;margin:8px 0 4px}
@media(max-width:840px){.wrap{padding:18px 14px}}
"""

# 页头 + TOC（无 s0）
header = '''
<header class="top">
  <h1>基金经理行为分析 — 变量指标体系（按实际含义归并）</h1>
  <div class="sub">L1 背景特征层 · L2 持仓偏离层 · L3 交易行为层 · L4 风险应对层 · L5 认知行为层（M 方法论与识别检验内容并入 §八 公式详解 与 §九 数据来源）</div>
  <div class="meta">编制日期：2026-08-11 ｜ 文献覆盖：L1–L3 参考 82 篇 · L4 23 篇 · L5 82 篇 · M 11 篇（合计 198 篇 PDF）<br>
  本表<strong>按实际含义归并</strong>：名称不一致的文献测度，只要算的是同一种东西，即归为<strong>同一个自变量</strong>，并逐行着重介绍<strong>参考文献是怎么做的</strong>。
  带蓝条的 <strong>17</strong> 个行为变量（从业/任期、基金年龄、学历、年龄、资质、主动份额、ICI、HHI、换手率、OCI、风格漂移、RG、ARG、收益波动率、DE、LSV、RiskAsym）为<strong>用户指定重点强调</strong>，其中 L1–L3 的 14 个附原文截图与详细计算讲解以增强可信度。
  其中 ARG / RG / 收益波动率 / DE / LSV / RiskAsym 六大核心指标全部加蓝条 + ★（详见 §八 公式详解）。</div>
</header>

<nav class="toc">
  <b>目录</b><br>
  <a href="#s1">一、变量指标总览</a>
  <a href="#s2">二、L1 变量总表</a>
  <a href="#s3">三、L2 变量总表</a>
  <a href="#s4">四、L3 变量总表</a>
  <a href="#s5">五、L4 变量总表</a>
  <a href="#s6">六、L5 变量总表</a>
  <a href="#s7">七、L1–L3 指标×文献对照</a>
  <a href="#s8">八、重点指标公式详解</a>
  <a href="#s9">九、数据来源汇总</a>
</nav>
<input id="search" placeholder="🔍 全局搜索变量 / 文献（按关键词过滤各层表格）…" onkeyup="filterRows(this.value)">
'''

# 一 总览
overview = '''
<h2 id="s1">一、变量指标总览（按层归并）</h2>
<div class="note">归并原则：<b>同名不同写、异名同义，皆归一</b>。例如文献中的 Active Share / 主动份额 / 主动程度，统一为 <b>主动份额 AS</b>；PGR−PLR 处置效应、Disposition Effect、售盈持亏，统一为 <b>处置效应 DE</b>；LSV / 羊群 / 交易趋同，统一为 <b>交易趋同度 LSV</b>。下表为本框架在各层采纳的规范变量（完整定义与文献做法见各层大表）。</div>
'''
layer_summary = []  # (layer, n_ours, n_core, n_aux, n_emp)

# 各层大表
sections = []
sec_titles = {
    "L1": ('二、L1 背景特征层 — 变量总表（按含义归并）', 's2'),
    "L2": ('三、L2 持仓偏离层 — 变量总表（按含义归并）', 's3'),
    "L3": ('四、L3 交易行为层 — 变量总表（按含义归并）', 's4'),
    "L4": ('五、L4 风险应对层 — 变量总表（按含义归并）', 's5'),
    "L5": ('六、L5 认知行为层 — 变量总表（按含义归并）', 's6'),
}
for layer in ["L1", "L2", "L3", "L4", "L5"]:
    tbl, n_ours, n_core, n_aux = render_layer_table(layer)
    title, sid = sec_titles[layer]
    n_emp = sum(1 for k in groups_by_key
                if groups_by_key[k]["g"]["layer"] == layer and k in EMPHASIS)
    layer_summary.append((layer, n_ours, n_core, n_aux, n_emp))
    note = ('<p class="muted">本层归并出 <b>%d</b> 个规范变量（标 ★ 者为论文六大核心：%d 个）；'
            '另有文献提及但未纳入本框架的辅助/控制测度 <b>%d</b> 项（灰行，不强调）。'
            '文献来源已跨 L1–L3 参考与 L4/L5/M 提取聚合。</p>' % (n_ours, n_core, n_aux))
    sections.append('<h2 id="%s">%s</h2>%s%s' % (sid, title, note, tbl))

# —— §一 总览：按层统计表 + 图例（loop 之后基于 layer_summary 生成）——
_LAYER_NAMES = {"L1":"背景特征层","L2":"持仓偏离层","L3":"交易行为层",
                "L4":"风险应对层","L5":"认知行为层"}
_ov_rows = "".join(
    ('<tr><td><span class="layer-tag l%s">%s</span> L%s %s</td>'
     '<td>%d</td><td>%d</td><td>%d</td><td>%d</td></tr>') %
    (L[1:], L, L, _LAYER_NAMES[L], no, nc, ne, na)
    for (L, no, nc, na, ne) in layer_summary)
_ov_tot = tuple(sum(x[i] for x in layer_summary) for i in range(1, 5))
overview += ('<table class="master ov"><thead><tr>'
             '<th>层级</th><th>框架变量</th><th>★ 核心</th><th>蓝条·强调</th><th>灰行·辅助</th>'
             '</tr></thead><tbody>%s'
             '<tr class="ov-tot"><td><b>合计</b></td><td><b>%d</b></td><td><b>%d</b></td>'
             '<td><b>%d</b></td><td><b>%d</b></td></tr>'
             '</tbody></table>'
             '<div class="conventions">'
             '<b>阅读说明（图例）：</b>'
             '<span class="lg emp">▎蓝条</span> = 用户指定重点强调变量（共 %d 个，见上表"蓝条·强调"列）；'
             '<span class="lg star">★</span> = 论文六大核心指标（ARG / RG / RVOL / DE / LSV / RiskAsym，均带蓝条）；'
             '<span class="lg aux">灰行</span> = 文献提及但<b>未纳入本框架</b>的辅助 / 控制测度（不强调）。'
             '表格内<b>展开块</b> = L1–L3 强调变量的<b>原文截图 + 计算讲解</b>。'
             '</div>' % (_ov_rows, _ov_tot[0], _ov_tot[1], _ov_tot[2], _ov_tot[3],
                         sum(x[4] for x in layer_summary)))

# 八 L1-L3 × 文献对照（沿用）
CROSSCHECK = [
    ("从业年限 mgr_total_tenure_v2", "L1", "✓ 文献已覆盖",
     "对应文献「任期/任职年限 Tenure」（Li&Li 2018、赵秀娟2010、吴栩2017）；论文用『首次任职至观测时点的累计天数』口径，概念一致。"),
    ("基金年龄 log_fund_age", "L1", "△ 论文自定义（文献未见）",
     "L1 文献变量表未列『基金年龄』。为论文自定义控制变量（取基金成立至观测期月数的对数），用于剥离策略老化/规模臃肿效应。"),
    ("学历 / 院校 / CFA", "L1", "✓ 文献已覆盖",
     "对应「学历 Master/PhD/学士」「MBA/EMBA」「专业证书 CPA/CFA」「名校毕业/985」（吴栩2017、于静2013、赵秀娟2010），概念一致。"),
    ("主动份额 AS_improved", "L2", "✓ 文献已覆盖（建议重算基准）",
     "对应「Active Share (AS)」Cremers&Petajisto 2009/2013。论文以沪深300+中证500合并真实成分股权重为基准重算，解决单一指数低估主动度问题（当前管线下截面区分度与原始口径相当）。"),
    ("行业集中度 ICI", "L2", "✓ 文献已覆盖",
     "对应「行业集中度指数 ICI」Kacperczyk et al. 2005：ICI = Σ(wᵢ − W̄ᵢ)²。"),
    ("行业分散度 industry_hhi", "L2", "△ 论文自定义（文献未见 HHI）",
     "L2 文献变量表以 ICI/ICR/ASR 等刻画行业偏离，未含 HHI。论文新增 HHI = Σwᵢ² 刻画组合本身集中度；与 ICI 近似正交（诚实截面相关仅 0.20，VIF 1.25/1.08）。"),
    ("风格漂移 SDI", "L3", "△ 论文自定义（风格漂移另见 L4）",
     "L3 文献变量表未含 SDI。风格漂移测度见 L4（寇宗来2020 Fsds、易力2021 SDS）。论文 SDI = Σ|wₖ,ₜ − wₖ,ₜ₋₁|（规模×价值成长四宫格权重变动）。"),
    ("换手率 TO_calc", "L3", "✓ 文献已覆盖",
     "对应「换手率 Turnover」TR = min(买入,卖出)/平均TNA（Lan 2015、多文献）；论文取 min 以剔除申购赎回被动交易，口径一致。"),
    ("过度自信/过度交易 OCI", "L3", "△ 论文自定义派生（已与 L5 过度自信合并）",
     "L3 文献变量表无独立 OCI；论文以 (TO − TŌ)/σ(TO) 对基金自身历史标准化，由换手率派生，刻画交易超出自身常态的程度，并作为 L5『过度自信』的统一测度（原 L3 过度交易与 L5 过度自信计算方法相同，已合并为本条目）。"),
]
def render_crosscheck():
    rows = []
    for ind, layer, status, note in CROSSCHECK:
        cls = "ok" if status.startswith("✓") else "warn"
        rows.append('<tr><td><b>%s</b></td><td class="ct">%s</td>'
                    '<td class="%s">%s</td><td>%s</td></tr>' % (
                        esc(ind), esc(layer), cls, esc(status), esc(note)))
    return ('<h2 id="s7">七、论文解读说明 L1–L3 指标 × 文献对照</h2>'
    '<p>对照《论文全方位解读》第二、三章明确列出的 L1–L3 指标，核查其在<strong>文献变量体系</strong>中是否已有对应测度。多数已被经典文献覆盖；标注 △ 者为论文自定义或派生。</p>'
    '<div class="tbl-wrap"><table class="master"><thead><tr>'
    '<th style="width:24%">论文解读说明中的指标</th><th style="width:8%">层级</th>'
    '<th style="width:18%">对照结论</th><th style="width:50%">说明 / 对应文献</th></tr></thead>'
    '<tbody>' + "".join(rows) + '</tbody></table></div>'
    '<div class="legend">图例：<span class="ok">✓ 文献已覆盖</span>　<span class="warn">△ 论文自定义 / 文献未见</span></div>')

# 九 重点指标公式详解（六块，含 RG）
EMPH_DETAIL = r'''
<h2 id="s8">八、重点指标公式详解（L4 / L5 六大核心指标）</h2>
<p>以下六个指标是本论文方法论核心、论文解读说明中明确要求着重强调的变量。逐一给出<strong>构建逻辑、计算公式（Unicode 数学符号）、计算步骤与文献出处</strong>；表中标 ★ 的行与本节一一对应。</p>

<div class="kbd">
  <div class="kbd-head"><span class="layer-tag l4">L4</span> ARG — 风险调整幅度（Risk Adjustment / 修正隐形交易） ★ ARG</div>
  <div class="formula-display">
    <div class="eq">ARG = Σ<sub>t</sub> |RG<sub>t</sub>|</div>
    <div class="eq-sub">论文解读说明 L4：各季度风险水平变化量绝对值之和</div>
  </div>
  <p><b>构建逻辑：</b>ARG 度量基金在相邻期间<strong>风险暴露水平的变动幅度</strong>。频繁调整可能是主动管理，也可能是排名压力下的被动摇摆（Brown, Harlow &amp; Starks 1996 锦标赛理论）。与 L3 风格漂移 SDI（持仓构成变化）作用域不同。</p>
  <p><b>计算步骤：</b>① 由净值/半年度持仓推算各季度收益缺口 RG<sub>t</sub>；② 取绝对值后跨期加总。申宇等 (2013) 修正隐形交易口径 ARG = Σ<sub>t</sub>|R − (RH − Fee)|，Fee = 1.5% + 0.25%（年化），用于纠正正负抵消低估（N=8,662，328 只基金，ARG 均值 0.4112）。</p>
  <p class="src-line">文献出处：申宇等 (2013)《隐形交易》；Brown, Harlow &amp; Starks (1996, JF)；Kacperczyk et al. (2008) Return Gap。</p>
</div>

<div class="kbd">
  <div class="kbd-head"><span class="layer-tag l4">L4</span> RG — 收益缺口 / Return Gap ★ RG</div>
  <div class="formula-display">
    <div class="eq">RG = (RF − EXP) − RH</div>
    <div class="eq-sub">RF = 投资者净收益(扣费后) ｜ RH = 按上期披露持仓构建的买入持有毛收益 ｜ EXP = 费用率</div>
  </div>
  <p><b>构建逻辑：</b>RG 衡量"披露日之后隐形交易的净效应"——基金实际净收益与"若维持上期持仓不变"的模拟收益之差。RG &gt; 0 表示隐形交易创造超额收益。</p>
  <p><b>计算步骤：</b>① 取基金投资者净收益 RF（扣管理费后）；② 用上一期披露持仓构建买入持有组合得 RH；③ RG = (RF − EXP) − RH。数据来源：CRSP + 前期披露持仓（Kacperczyk et al. 2008, RFS）。</p>
  <p class="src-line">文献出处：Kacperczyk, Sialm &amp; Zheng (2008, RFS)；申宇等 (2013) 修正隐形交易 ARG。</p>
</div>

<div class="kbd">
  <div class="kbd-head"><span class="layer-tag l4">L4</span> 收益波动率 — return_volatility ★ RVOL</div>
  <div class="formula-display">
    <div class="eq">σ<sub>8Q</sub> = √[ (1/(8−1)) · Σ<sub>t=1</sub><sup>8</sup> (R<sub>t</sub> − R̄)² ]</div>
    <div class="eq-sub">滚动 8 个季度收益率的标准差（约 2 年窗口）</div>
  </div>
  <p><b>构建逻辑：</b>收益波动率是风险管理的<strong>结果性指标</strong>，反映基金承担的总风险水平。采用 8 季度滚动窗口，是在估计精度与时效性之间的权衡。</p>
  <p><b>计算步骤：</b>① 由日净值复合出季度收益率 R<sub>t</sub>；② 取最近 8 个季度计算样本标准差。数据来源：基金净值面板（akshare / 东方财富）。</p>
  <p class="src-line">文献出处：论文解读说明 L4；蒋志平、田益祥、郑焕刚 (2013) 业绩波动率；Jordan &amp; Riley (2014) "Volatility and mutual fund manager skill"（基金过去收益波动率是未来业绩的强预测变量，且由<b>总波动率</b>而非特质波动率驱动）；Ang, Chen &amp; Xing (2006, RFS) Downside Risk；与 Brown-Harlow-Starks (1996) 的 RAR = σ₂/σ₁ 同属风险维度测度。</p>
</div>

<div class="kbd hl5">
  <div class="kbd-head"><span class="layer-tag l5">L5</span> DE — 处置效应（Disposition Effect） ★ DE</div>
  <div class="formula-display">
    <div class="eq">DE = PGR − PLR</div>
    <div class="eq-sub">PGR = N<sub>卖,盈</sub> / (N<sub>卖,盈</sub> + N<sub>持,盈</sub>)　｜　PLR = N<sub>卖,亏</sub> / (N<sub>卖,亏</sub> + N<sub>持,亏</sub>)</div>
  </div>
  <p><b>构建逻辑：</b>DE 刻画"盈亏状态下的卖出倾向偏差"——售盈持亏（DE &gt; 0，经典处置效应）或其反向（DE &lt; 0，止损倾向强）。理论锚点为前景理论的损失规避与参考点依赖。</p>
  <p><b>计算步骤：</b>① 用持仓快照 + 持仓成本（个股价格来自 tushare）判定盈亏状态；② 对比相邻两期：消失的持仓记为"实现卖出"，仍在的记为"账面持有"；③ 按盈利/亏损分别计算 PGR、PLR，相减得 DE。<strong>测量误差：</strong>季度快照看不到季中交易，会把 |DE| 向零衰减，故本文 DE 证据是保守下界；PGR=0.891/PLR=0.919 偏高，存在状态误分类风险，方向性结论依赖组内效应（t=−3.64）。</p>
  <p class="src-line">文献出处：Odean (1998, JF) PGR−PLR 范式；Shefrin &amp; Statman (1985)；Grinblatt &amp; Han (2005, JFE)；李学峰 (2011/2013)。</p>
</div>

<div class="kbd hl5">
  <div class="kbd-head"><span class="layer-tag l5">L5</span> LSV — 交易趋同度（Trading Convergence / 羊群） ★ LSV</div>
  <div class="formula-display">
    <div class="eq">LSV = |p<sub>j</sub> − p̄<sub>t</sub>| − AF</div>
    <div class="eq-sub">p<sub>j</sub> = 买入股票数<sub>j</sub> / 交易股票总数<sub>j</sub>　｜　p̄<sub>t</sub> = 同期全体基金平均买入比例　｜　AF = E[|p<sub>j</sub> − p̄<sub>t</sub>|]（零假设期望偏离）</div>
  </div>
  <p><b>构建逻辑：</b>LSV 度量基金相对同业的买卖方向趋同/反向程度。经典语义为"羊群强度"（&gt;0 跟随市场）。<strong>本文语义校正：</strong>样本整体 LSV 为负，准确含义是"交易趋同度"——回归中 LSV 正系数读作"越贴近市场共识业绩越好"。纠正幸存者偏差后截面符号反转，按"选择敏感的描述性证据(B−)"处理。</p>
  <p><b>计算步骤：</b>① 用全持仓统计买入/卖出/持有的股票集合；② 算个体买入比例 p<sub>j</sub> 与全市场均值 p̄<sub>t</sub>；③ 减去二项分布零假设下的期望偏离 AF。数据来源：全市场基金持仓横截面。</p>
  <p class="src-line">文献出处：Lakonishok, Shleifer &amp; Vishny (1992, JFE)；Wermers (1999, JF) BHM/SHM；祁斌 2006、魏立波 2010 等修正应用。</p>
</div>

<div class="kbd hl5">
  <div class="kbd-head"><span class="layer-tag l5">L5</span> RiskAsym — 条件波动率不对称（Conditional Volatility Asymmetry） ★ RISKASYM</div>
  <div class="formula-display">
    <div class="eq">RiskAsym = σ(盈利期季度收益) − σ(亏损期季度收益)</div>
  </div>
  <p><b>构建逻辑：</b>RiskAsym 刻画盈利期与亏损期风险承担的差异，对应"怎么赌"。&gt;0 = 盈利期风险承担更高（"赌资效应"）；&lt;0 = 亏损期更激进（"锦标赛效应"）。理论锚点为前景理论价值函数的不对称 + 锦标赛理论。</p>
  <p><b>计算步骤：</b>① 由日净值复合出季度收益率；② 按收益符号划分为盈利期/亏损期；③ 分别求两段标准差后相减。数据来源：基金净值面板。<strong>注意：</strong>理论解释不唯一（风险偏好 or 择时能力），故配 Henriksson–Merton 择时控制 + 构念纯化（对择时与规模正交化后，截面 t=6.26、前向4季 t=4.27 仍显著）。</p>
  <p class="src-line">文献出处：Brown, Harlow &amp; Starks (1996, JF)（"不对称风险承担"思想起源）；Bollerslev, Li &amp; Zhao (2020, JFQA) "Good Volatility, Bad Volatility, and the Cross Section of Stock Returns"（将已实现变异分解为 up/down 半方差 / good·bad volatility，是 σ(gain)−σ(loss) 最近的外部方法；可同理归一化为 [σ(gain)−σ(loss)]/[σ(gain)+σ(loss)] 以消除量级差异）；Barndorff-Nielsen, Kinnebrock &amp; Shephard (2010) "Measuring Downside Risk: Realised Semivariance"（上述分解的计量基础）；论文解读说明 L5。</p>
</div>
'''

# 十 数据来源汇总（沿用）
sources_sec = '''
<h2 id="s9">九、数据来源汇总</h2>
<p>各文献数据底座高度集中，可归纳为「海外库」「国内库」「方法实验」三类：</p>
<h3>① 海外数据库（支撑 L2/L3 国际文献及方法）</h3>
<table class="master"><thead><tr><th>数据库</th><th>提供内容</th><th>典型使用文献</th></tr></thead><tbody>
<tr><td>CRSP</td><td>基金净值/收益/TNA/费用率/换手率；无幸存者偏差基金库</td><td>Cremers&Petajisto、Kacperczyk、Lan 2015、Grinblatt 1995</td></tr>
<tr><td>Thomson CDA/Spectrum</td><td>共同基金半年度/季度持仓库</td><td>Cremers&Petajisto、Kacperczyk、Lan 2015</td></tr>
<tr><td>IBES / Compustat / Ken French</td><td>分析师建议 / 公司财务 / 因子库</td><td>Kacperczyk&Seru(RPI)、Cremers 2012、全部因子 α</td></tr>
<tr><td>MFLINKS / SEC / 指数商</td><td>CRSP-Thomson 链接 / 年刊 / 基准指数</td><td>Cremers 2012、Jensen 1967、Cremers&Petajisto</td></tr>
</tbody></table>
<h3>② 国内数据库（支撑 L1–L5 中国文献）</h3>
<table class="master"><thead><tr><th>数据库</th><th>提供内容</th><th>典型使用文献</th></tr></thead><tbody>
<tr><td>Wind（万得）</td><td>净值/份额/规模/经理简历/持股/薪酬/资金流</td><td>吴栩2017、赵秀娟2010、Li&Li 2018、申宇2013、林树2021</td></tr>
<tr><td>CSMAR（国泰安）</td><td>净值/特征/因子/持仓/财务</td><td>肖峻2011、邢欣羿2015、韩燕2011、张学勇、基金经理个人特征</td></tr>
<tr><td>RESSET（锐思）</td><td>净值/持股/薪酬/简历/高管</td><td>申宇2015(校友网络)、申宇2013(隐形交易)、孔东民2015</td></tr>
<tr><td>聚源 / 天相 / 国泰君安 / CCER / 基金定期报告</td><td>年报文本 / 经理资格 / 行业权重 / 股价收益 / 完整持仓</td><td>沈红波2025、赵秀娟2010、邢欣羿2015、周少甫2009、全部 L2/L3 中国文献</td></tr>
</tbody></table>
<h3>③ 本论文数据接口（论文解读说明第三章）</h3>
<table class="master"><thead><tr><th>数据类型</th><th>来源</th><th>用途</th></tr></thead><tbody>
<tr><td>基金净值 NAV</td><td>akshare（fund_open_fund_info_em）</td><td>季度收益、波动率、RiskAsym</td></tr>
<tr><td>基金持仓</td><td>东方财富 FundArchivesDatas API</td><td>AS、ICI、HHI、SDI、TO、DE、LSV</td></tr>
<tr><td>个股价格</td><td>tushare pro.daily</td><td>DE 盈亏状态判定</td></tr>
<tr><td>FF5 因子 / 经理信息</td><td>本地 FF5_monthly.csv / akshare fund_manager_em</td><td>因变量 FF5 alpha / L1 变量</td></tr>
</tbody></table>
<div class="note">样本区间共性：海外文献多取 1980–2000s；国内文献多取 2003–2020s 开放式主动偏股基金，连续变量普遍 1% 缩尾。本论文样本为 400 只存活基金 + 183 只清盘基金、2006–2026、9,581 基金-季度观测。</div>
'''

# 十一 附录：已按用户要求删除（原附录文献清单并入 §九 数据来源汇总与 §八 公式详解）

JS = """
<script>
function filterRows(q){
  q=q.trim().toLowerCase();
  document.querySelectorAll('table.master').forEach(function(t){
    t.querySelectorAll('tbody tr').forEach(function(tr){
      var txt=tr.textContent.toLowerCase();
      tr.style.display = (!q || txt.indexOf(q)>=0) ? '' : 'none';
    });
  });
}
function setTocH(){
  var toc=document.querySelector('nav.toc');
  if(toc){document.documentElement.style.setProperty('--toc-h',(toc.offsetHeight+4)+'px');}
}
window.addEventListener('load',setTocH);
window.addEventListener('resize',setTocH);
</script>
"""

OUT = ("<!DOCTYPE html><html lang='zh-CN'><head><meta charset='UTF-8'>"
       "<meta name='viewport' content='width=device-width,initial-scale=1.0'>"
       "<title>基金经理行为分析 — 变量指标体系（按含义归并 · L1–L5）</title>"
       "<style>" + CSS + "</style></head><body><div class='wrap'>"
       + header + overview
       + "".join(sections)
       + render_crosscheck() + EMPH_DETAIL + sources_sec
       + "<footer>本文档按『实际含义归并』重排：将 L1–L3 参考与 L4/L5/M 文献提取的全部变量，按同一种东西=同一个变量整合，并逐行着重介绍参考文献的构建方法。生成时间：2026-08-11。</footer>"
       + "</div>" + JS + "</body></html>")

out_path = os.path.join(BASE, "基金经理行为分析_变量指标合并总表_L1-L5+M.html")
with open(out_path, "w", encoding="utf-8") as fh:
    fh.write(OUT)
print("已写出:", out_path, "大小:", os.path.getsize(out_path), "字节")

# 诊断输出
print("\n=== 归并诊断 ===")
for layer in ["L1","L2","L3","L4","L5","M"]:
    keys = [k for k,v in groups_by_key.items() if v["g"]["layer"]==layer]
    nentries = sum(len(groups_by_key[k]["entries"]) for k in keys)
    print("%s: %d 个规范变量, %d 条来源条目" % (layer, len(keys), nentries))
print("未归并条目(已按层放入'其他'组):", len(unmapped))
for e in unmapped[:60]:
    print("   - [%s] %s | %s" % (e["src_layer"], e["name"], (e["def"] or "")[:40]))
