# -*- coding: utf-8 -*-
"""
重建版：基金经理行为分析 — 变量指标体系（每层一张合并大表 + 文献来源末列）
- 解析 L1-L3 参考 HTML 的合并表
- 合并 L4/L5/M 的 JSON 提取，去重并归集文献来源
- 优化公式显示（Unicode 数学符号 + 专业公式块）
- 新增：L1-L3 指标 × 文献对照表；ARG/RG/收益波动率( L4 )、DE/LSV/RiskAsys( L5 ) 重点详解
"""
import json, html, os, re, glob
from collections import OrderedDict

BASE = r"D:/Desktop/基金经理行为分析研究/参考文献"
BASE_L13 = r"C:/Users/26955/Downloads/变量指标L1-L3.html"

# ============================================================
# 1. 解析 L1-L3 参考 HTML 的合并变量表
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

# 按带 layer-tag 的 h3 切分
pat = re.compile(r'(<h3><span class="layer-tag l([123])">L([123])</span>[^<]*?</h3>)', re.S)
parts = pat.split(ref)
# parts: [text0, g1, g2, g3, text1, g1, g2, g3, text2, ...]
L13 = {"L1": [], "L2": [], "L3": []}
k = 0
while True:
    gi = 1 + 4 * k
    if gi >= len(parts):
        break
    h3full = parts[gi]
    layer = "L" + parts[gi + 1]
    body = parts[gi + 3] if (gi + 3) < len(parts) else ""
    if "自变量" in h3full:
        vtype = "自变量"
    elif "因变量" in h3full:
        vtype = "因变量"
    else:
        vtype = ""
    for r in parse_table(body):
        if len(r) >= 5:                       # IV 表: 变量|定义|公式|数据来源|代表文献
            var, dfn, formula, ds, src = r[0], r[1], r[2], r[3], r[4]
        elif len(r) == 4:                    # DV 表: 变量|定义|公式|代表文献
            var, dfn, formula, src = r[0], r[1], r[2], r[3]
            ds = ""
        else:
            continue
        L13.setdefault(layer, []).append({
            "name": var, "type": vtype, "def": dfn,
            "formula": formula, "ds": ds, "src": src
        })
    k += 1

# ============================================================
# 2. 合并 L4/L5/M 的 JSON 提取
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

def norm_name(s):
    s = str(s).lower()
    s = re.sub(r'\([^)]*\)', '', s)
    s = re.sub(r'[\s\-_./,;:（）【】\[\]（）]', '', s)
    s = re.sub(r'[^a-z0-9一-鿿]', '', s)
    return s

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

# 收集 L4/L5/M 条目
L456 = {"L4": [], "L5": [], "M": []}
for r in raw:
    layer = norm_layer(r)
    if layer not in L456:
        continue
    title = r.get("title", "")
    ay = r.get("authors_year", "")
    fname = r.get("file", "")
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
                "src": src
            })

# 去重归集（按归一化变量名）
def dedup(entries):
    groups = OrderedDict()
    for e in entries:
        key = norm_name(e["name"]) or ("_u%d" % len(groups))
        if key not in groups:
            groups[key] = {"name": e["name"], "type": e["type"], "def": "",
                           "formula": "", "ds": "", "sources": []}
        g = groups[key]
        if not g["def"] and e["def"]:
            g["def"] = e["def"]
        if not g["formula"] and e["formula"]:
            g["formula"] = e["formula"]
        if not g["ds"] and e["ds"]:
            g["ds"] = e["ds"]
        if e["src"] and e["src"] not in g["sources"]:
            g["sources"].append(e["src"])
    return list(groups.values())

for layer in L456:
    L456[layer] = dedup(L456[layer])

# ============================================================
# 3. 重点指标强调（ARG/RG/收益波动率; DE/LSV/RiskAsys）
# ============================================================
EMPH = {
    "ARG": ["arg", "修正隐形交易", "风险调整幅度"],
    "RG":  ["returngap", "收益缺口"],
    "RVOL":["收益波动率", "return_volatility", "returnvolatility"],
    "DE":  ["处置效应", "disposition", "pgr", "plr"],
    "LSV": ["lsv", "交易趋同", "交易趋同度"],
    "RISKASYM": ["riskasym", "条件波动率不对称", "risasym"],
}
def emph_tag(name, dfn, formula):
    n = norm_name(name)
    toks = set(re.findall(r'[a-z]+', n))
    def has(*words):
        return any(w in toks for w in words)
    if has("arg") or "修正隐形交易" in n or "风险调整幅度" in n:
        return "ARG"
    if has("returngap") or "收益缺口" in n:
        return "RG"
    if has("returnvolatility") or "收益波动率" in n:
        return "RVOL"
    if has("pgr", "plr") or "disposition" in n or "处置效应" in n:
        return "DE"
    if has("lsv") or "交易趋同" in n or "羊群行为" in n:
        return "LSV"
    if has("riskasym", "risasym") or "条件波动率不对称" in n:
        return "RISKASYM"
    return None

# ============================================================
# 4. 渲染合并大表
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
    shown = sources[:4]
    s = "；".join(esc(s) for s in shown)
    if len(sources) > 4:
        s += ' 等 %d 篇' % len(sources)
    return s

LAYER_NAME = {
    "L1": "L1 背景特征层", "L2": "L2 持仓偏离层", "L3": "L3 交易行为层",
    "L4": "L4 风险应对层", "L5": "L5 认知行为层", "M": "M 方法论与识别检验层",
}
LAYER_CLS = {"L1": "l1", "L2": "l2", "L3": "l3", "L4": "l4", "L5": "l5", "M": "lm"}

def render_master_table(layer, rows):
    tag = LAYER_CLS[layer]
    body_rows = []
    n_emp = 0
    for r in rows:
        et = emph_tag(r["name"], r["def"], r["formula"])
        star = ""
        cls = ""
        if et:
            star = '<span class="star" title="重点指标">★ %s</span>' % et
            cls = ' class="emp"'
            n_emp += 1
        ds = r["ds"] if r["ds"] else "—"
        body_rows.append(
            '<tr%s><td><b>%s</b>%s</td><td class="ct">%s</td><td>%s</td><td>%s</td>'
            '<td>%s</td><td class="src">%s</td></tr>' % (
                cls, esc(r["name"]), star, esc(r["type"]),
                esc(r["def"]) or '<span class="muted">—</span>',
                fcell(r["formula"]), esc(ds),
                src_cell(r.get("sources", [])) if layer in L456 else esc(r["src"])
            ))
    table = ('<div class="tbl-wrap"><table class="master"><thead><tr>'
             '<th style="width:17%">变量 / 指标</th>'
             '<th style="width:7%">类型</th>'
             '<th style="width:30%">定义与度量方式</th>'
             '<th style="width:21%">计算公式</th>'
             '<th style="width:13%">数据来源</th>'
             '<th style="width:12%">文献来源</th>'
             '</tr></thead><tbody>' + "".join(body_rows) + '</tbody></table></div>')
    return table, n_emp

# ============================================================
# 5. 重点指标公式详解
# ============================================================
EMPH_DETAIL = r'''
<h2 id="s9">九、重点指标公式详解（L4 / L5 核心认知与风险变量）</h2>
<p>以下六个指标是本论文方法论的核心构件，也是论文解读说明中明确要求着重强调的变量。逐一给出其<strong>变量构建逻辑、计算公式（Unicode 数学符号，便于直接引用）、计算步骤与文献出处</strong>。表中标 ★ 的行与本节一一对应。</p>

<div class="kbd">
  <div class="kbd-head"><span class="layer-tag l4">L4</span> ARG — 风险调整幅度（Risk Adjustment / 修正隐形交易）</div>
  <div class="formula-display">
    <div class="eq">ARG = Σ<sub>t</sub> |RG<sub>t</sub>|</div>
    <div class="eq-sub">论文解读说明 L4：各季度风险水平变化量绝对值之和</div>
  </div>
  <p><b>构建逻辑：</b>ARG 度量基金在相邻期间<strong>风险暴露水平的变动幅度</strong>。频繁调整可能是主动管理，也可能是排名压力下的被动摇摆（Brown, Harlow &amp; Starks 1996 锦标赛理论）。它刻画的是"承担多少风险"的变化，与 L3 的风格漂移 SDI（持仓构成变化）作用域不同。</p>
  <p><b>计算步骤：</b>① 由净值/半年度持仓推算各季度收益缺口 RG<sub>t</sub>；② 取绝对值后跨期加总。申宇等 (2013) 的修正隐形交易口径为 ARG = Σ<sub>t</sub>|R − (RH − Fee)|，Fee = 1.5% + 0.25%（年化），用于纠正正负抵消导致的低估（N=8,662，328 只基金，ARG 均值 0.4112）。</p>
  <p class="src-line">文献出处：申宇等 (2013)《隐形交易》；Brown, Harlow &amp; Starks (1996, JF) 锦标赛理论；Kacperczyk et al. (2008) Return Gap。</p>
</div>

<div class="kbd">
  <div class="kbd-head"><span class="layer-tag l4">L4</span> RG — 收益缺口 / Return Gap</div>
  <div class="formula-display">
    <div class="eq">RG = (RF − EXP) − RH</div>
    <div class="eq-sub">RF = 投资者净收益(扣费后) ｜ RH = 按上期披露持仓构建的买入持有毛收益 ｜ EXP = 费用率</div>
  </div>
  <p><b>构建逻辑：</b>RG 衡量"披露日之后隐形交易的净效应"——即基金实际净收益与"若维持上期持仓不变"的模拟收益之差。RG &gt; 0 表示隐形交易创造了超额收益。</p>
  <p><b>计算步骤：</b>① 取基金投资者净收益 RF（扣管理费后）；② 用上一期披露持仓构建买入持有组合，得 RH；③ RG = (RF − EXP) − RH。数据来源：CRSP + 前期披露持仓（Kacperczyk et al. 2008, RFS）。</p>
  <p class="src-line">文献出处：Kacperczyk, Sialm &amp; Zheng (2008, RFS)；申宇等 (2013) 修正隐形交易 ARG。</p>
</div>

<div class="kbd">
  <div class="kbd-head"><span class="layer-tag l4">L4</span> 收益波动率 — return_volatility</div>
  <div class="formula-display">
    <div class="eq">σ<sub>8Q</sub> = √[ (1/(8−1)) · Σ<sub>t=1</sub><sup>8</sup> (R<sub>t</sub> − R̄)² ]</div>
    <div class="eq-sub">滚动 8 个季度收益率的标准差（约 2 年窗口）</div>
  </div>
  <p><b>构建逻辑：</b>收益波动率是风险管理的<strong>结果性指标</strong>，反映基金承担的总风险水平。采用 8 季度滚动窗口，是在估计精度（窗口太短噪声大）与时效性（太长无法及时反映风险变化）之间的权衡。</p>
  <p><b>计算步骤：</b>① 由日净值复合出季度收益率 R<sub>t</sub>；② 取最近 8 个季度，计算样本标准差。数据来源：基金净值面板（akshare / 东方财富）。</p>
  <p class="src-line">文献出处：论文解读说明 L4（风险管理层）；与 Brown-Harlow-Starks (1996) 的 RAR = σ2/σ1（上下半年标准差比）同属风险维度测度。</p>
</div>

<div class="kbd hl5">
  <div class="kbd-head"><span class="layer-tag l5">L5</span> DE — 处置效应（Disposition Effect）</div>
  <div class="formula-display">
    <div class="eq">DE = PGR − PLR</div>
    <div class="eq-sub">PGR = N<sub>卖,盈</sub> / (N<sub>卖,盈</sub> + N<sub>持,盈</sub>)　｜　PLR = N<sub>卖,亏</sub> / (N<sub>卖,亏</sub> + N<sub>持,亏</sub>)</div>
  </div>
  <p><b>构建逻辑：</b>DE 刻画"盈亏状态下的卖出倾向偏差"——售盈持亏（DE &gt; 0，经典处置效应）或其反向（DE &lt; 0，止损倾向强）。理论锚点为前景理论的损失规避与参考点依赖。</p>
  <p><b>计算步骤：</b>① 用持仓快照 + 持仓成本（个股价格来自 tushare）判定每只持仓股相对成本价的盈亏状态；② 对比相邻两期：消失的持仓记为"实现卖出"，仍在的记为"账面持有"；③ 按盈利/亏损分别计算实现比率 PGR、PLR，相减得 DE。<strong>测量误差方向：</strong>季度快照看不到季中交易，会把 |DE| 向零衰减，故本文 DE 证据是保守下界；PGR=0.891/PLR=0.919 偏高，存在状态误分类风险，故方向性结论依赖组内效应（t=−3.64）而非 PGR/PLR 绝对水平。</p>
  <p class="src-line">文献出处：Odean (1998, JF) PGR−PLR 范式；Shefrin &amp; Statman (1985)；Grinblatt &amp; Han (2005, JFE) PPD；李学峰 (2011/2013)。</p>
</div>

<div class="kbd hl5">
  <div class="kbd-head"><span class="layer-tag l5">L5</span> LSV — 交易趋同度（Trading Convergence / 羊群）</div>
  <div class="formula-display">
    <div class="eq">LSV = |p<sub>j</sub> − p̄<sub>t</sub>| − AF</div>
    <div class="eq-sub">p<sub>j</sub> = 买入股票数<sub>j</sub> / 交易股票总数<sub>j</sub>　｜　p̄<sub>t</sub> = 同期全体基金平均买入比例　｜　AF = E[|p<sub>j</sub> − p̄<sub>t</sub>|]（零假设期望偏离）</div>
  </div>
  <p><b>构建逻辑：</b>LSV 度量基金相对同业的买卖方向趋同/反向程度。经典语义为"羊群强度"（&gt;0 跟随市场）。<strong>本文语义校正：</strong>样本整体 LSV 为负，故准确含义是"交易趋同度"——回归中 LSV 正系数读作"越贴近市场共识业绩越好（过度反向损害业绩）"。纠正幸存者偏差（并入清盘基金）后截面符号反转，故按"选择敏感的描述性证据"处理（B−级）。</p>
  <p><b>计算步骤：</b>① 对每只基金-季度，用全持仓统计买入/卖出/持有的股票集合；② 算个体买入比例 p<sub>j</sub> 与全市场均值 p̄<sub>t</sub>；③ 减去二项分布零假设下的期望偏离 AF。数据来源：全市场基金持仓横截面。</p>
  <p class="src-line">文献出处：Lakonishok, Shleifer &amp; Vishny (1992, JFE)；Wermers (1999, JF) BHM/SHM；中文文献（祁斌 2006、魏立波 2010 等）均为此框架的修正应用。</p>
</div>

<div class="kbd hl5">
  <div class="kbd-head"><span class="layer-tag l5">L5</span> RiskAsym — 条件波动率不对称（Conditional Volatility Asymmetry）</div>
  <div class="formula-display">
    <div class="eq">RiskAsym = σ(盈利期季度收益) − σ(亏损期季度收益)</div>
  </div>
  <p><b>构建逻辑：</b>RiskAsym 刻画盈利期与亏损期风险承担的差异，对应"怎么赌"的维度。&gt;0 = 盈利期风险承担更高（"赌资效应"）；&lt;0 = 亏损期更激进（"锦标赛效应"）。理论锚点为前景理论价值函数的不对称 + 锦标赛理论。</p>
  <p><b>计算步骤：</b>① 由日净值复合出季度收益率；② 按收益符号划分为盈利期/亏损期；③ 分别求两段标准差后相减。数据来源：基金净值面板。<strong>注意：</strong>该指标度量的是条件波动率的不对称，理论解释不唯一（风险偏好 or 择时能力），故正文配 Henriksson–Merton 择时控制 + 构念纯化（对择时与规模正交化后，截面 t=6.26、前向4季 t=4.27 仍显著）。</p>
  <p class="src-line">文献出处：Brown, Harlow &amp; Starks (1996, JF) 问题意识；论文解读说明 L5（认知偏差层核心三指标之一）。</p>
</div>
'''

# ============================================================
# 6. L1-L3 指标 × 文献对照表（来自论文解读说明）
# ============================================================
CROSSCHECK = [
    ("从业年限 mgr_total_tenure_v2", "L1", "✓ 文献已覆盖",
     "对应文献「任期/任职年限 Tenure」（Li&Li 2018、赵秀娟2010、吴栩2017）；论文用『首次任职至观测时点的累计天数』口径，概念一致。"),
    ("基金年龄 log_fund_age", "L1", "△ 论文自定义（文献未见）",
     "L1 文献变量表未列『基金年龄』。为论文自定义控制变量（取基金成立至观测期月数的对数），用于剥离策略老化/规模臃肿效应。"),
    ("学历 / 院校 / CFA", "L1", "✓ 文献已覆盖",
     "对应「学历 Master/PhD/学士」「MBA/EMBA」「专业证书 CPA/CFA」「名校毕业/985」（吴栩2017、于静2013、赵秀娟2010），概念一致。"),
    ("主动份额 AS_improved", "L2", "✓ 文献已覆盖（建议重算基准）",
     "对应「Active Share (AS)」Cremers&Petajisto 2009/2013。论文以沪深300+中证500合并真实成分股权重为基准重算，解决单一指数低估主动度问题（变异系数 +65.9%）。"),
    ("行业集中度 ICI", "L2", "✓ 文献已覆盖",
     "对应「行业集中度指数 ICI」Kacperczyk et al. 2005：ICI = Σ(wᵢ − W̄ᵢ)²。"),
    ("行业分散度 industry_hhi", "L2", "△ 论文自定义（文献未见 HHI）",
     "L2 文献变量表以 ICI/ICR/ASR 等刻画行业偏离，未含 HHI。论文新增 HHI = Σwᵢ² 刻画组合本身集中度；与 ICI 近似正交（诚实截面相关仅 0.20，VIF 1.25/1.08）。"),
    ("风格漂移 SDI", "L3", "△ 论文自定义（风格漂移另见 L4）",
     "L3 文献变量表未含 SDI。风格漂移测度见 L4（寇宗来2020 Fsds、易力2021 SDS）。论文 SDI = Σ|wₖ,ₜ − wₖ,ₜ₋₁|（规模×价值成长四宫格权重变动）。"),
    ("换手率 TO_calc", "L3", "✓ 文献已覆盖",
     "对应「换手率 Turnover」TR = min(买入,卖出)/平均TNA（Lan 2015、多文献）；论文取 min 以剔除申购赎回被动交易，口径一致。"),
    ("过度交易 OCI", "L3", "△ 论文自定义派生",
     "L3 文献变量表无 OCI。论文以 (TO − TŌ)/σ(TO) 对基金自身历史标准化，由换手率派生，刻画当期交易超出自身常态的程度。"),
]
def render_crosscheck():
    rows = []
    for ind, layer, status, note in CROSSCHECK:
        cls = "ok" if status.startswith("✓") else "warn"
        rows.append('<tr><td><b>%s</b></td><td class="ct">%s</td>'
                    '<td class="%s">%s</td><td>%s</td></tr>' % (
                        esc(ind), esc(layer), cls, esc(status), esc(note)))
    return ('<h2 id="s8">八、论文解读说明 L1–L3 指标 × 文献对照</h2>'
    '<p>对照《论文全方位解读》第二、三章明确列出的 L1–L3 指标，逐一核查其在<strong>文献变量体系（L1-L3 参考）</strong>中是否已有对应测度。结果：多数指标已被经典文献覆盖；标注 △ 者为论文自定义或派生，文献变量表未见直接对应，正式写作时建议明确其方法来源与差异。</p>'
    '<div class="tbl-wrap"><table class="master"><thead><tr>'
    '<th style="width:24%">论文解读说明中的指标</th><th style="width:8%">层级</th>'
    '<th style="width:18%">对照结论</th><th style="width:50%">说明 / 对应文献</th></tr></thead>'
    '<tbody>' + "".join(rows) + '</tbody></table></div>'
    '<div class="legend">图例：<span class="ok">✓ 文献已覆盖</span>　<span class="warn">△ 论文自定义 / 文献未见</span></div>')

# ============================================================
# 7. 组装 CSS + 页面
# ============================================================
CSS = """
:root{
  --bg:#ffffff; --fg:#1f2a37; --muted:#64748b; --line:#e3e8ef; --soft:#f7fafc;
  --brand:#16407a; --brand2:#0b6e4f; --accent:#b4231f;
  --l1:#16407a; --l2:#0b6e4f; --l3:#9a4b00; --l4:#6b3fa0; --l5:#0d7a8a; --lm:#c2410c;
  --emp:#fff7ed; --empb:#f97316;
}
*{box-sizing:border-box}
body{margin:0;font-family:"Segoe UI","Microsoft YaHei","PingFang SC",system-ui,sans-serif;
     color:var(--fg);background:var(--bg);line-height:1.78;font-size:15px}
.wrap{max-width:1240px;margin:0 auto;padding:30px 30px 80px}
header.top{border-bottom:3px solid var(--brand);padding-bottom:16px;margin-bottom:6px}
header.top h1{font-size:26px;margin:0 0 6px;color:var(--brand);letter-spacing:.4px}
header.top .sub{color:var(--muted);font-size:14px}
.meta{margin-top:10px;font-size:13px;color:var(--muted)}
nav.toc{position:sticky;top:0;background:rgba(255,255,255,.95);backdrop-filter:blur(6px);
        border:1px solid var(--line);border-radius:10px;padding:12px 16px;margin:18px 0 26px;z-index:20;
        box-shadow:0 2px 10px rgba(20,40,80,.05)}
nav.toc b{color:var(--brand);margin-right:4px}
nav.toc a{color:var(--fg);text-decoration:none;margin:0 8px 4px 0;display:inline-block;font-size:13px}
nav.toc a:hover{color:var(--brand);text-decoration:underline}
h2{font-size:21px;color:var(--brand);border-left:6px solid var(--brand);padding-left:12px;margin:36px 0 14px;scroll-margin-top:70px}
h3{font-size:17px;color:var(--brand2);margin:24px 0 10px}
.note{background:var(--soft);border:1px solid var(--line);border-left:4px solid var(--brand);
      border-radius:8px;padding:12px 16px;margin:14px 0;font-size:14px}
.warn{background:#fff6f5;border:1px solid #f3c9c5;border-left:4px solid var(--accent);border-radius:8px;padding:12px 16px;margin:14px 0;font-size:14px}
.layer-tag{display:inline-block;font-size:12px;font-weight:700;color:#fff;border-radius:5px;padding:1px 8px;margin-right:6px;vertical-align:middle}
.l1{background:var(--l1)} .l2{background:var(--l2)} .l3{background:var(--l3)}
.l4{background:var(--l4)} .l5{background:var(--l5)} .lm{background:var(--lm)}
.tbl-wrap{overflow-x:auto;margin:12px 0 22px;border-radius:10px;border:1px solid var(--line)}
table.master{border-collapse:collapse;width:100%;font-size:13.2px;margin:0}
table.master th,table.master td{border:1px solid var(--line);padding:8px 10px;vertical-align:top;text-align:left}
table.master thead th{background:linear-gradient(180deg,#eef4fb,#e2ecf8);color:var(--brand);
  font-weight:700;position:sticky;top:52px;z-index:5;border-bottom:2px solid #c9d8ee}
table.master tbody tr:nth-child(even) td{background:#fafcff}
table.master tbody tr:hover td{background:#eef5ff}
table.master td.ct{text-align:center;white-space:nowrap;color:var(--muted)}
table.master td.src{font-size:12px;color:#3b5168}
table.master tr.emp td{background:var(--emp)!important;box-shadow:inset 3px 0 0 var(--empb)}
.star{display:inline-block;margin-left:6px;font-size:11px;font-weight:700;color:#fff;
  background:var(--empb);border-radius:10px;padding:1px 7px;vertical-align:middle}
code.fx{background:#eef2f7;padding:2px 6px;border-radius:5px;font-family:"Cambria Math","Consolas",monospace;
  font-size:12.8px;color:#0a3a66;white-space:nowrap}
.muted{color:var(--muted)}
.formula-display{background:linear-gradient(135deg,#f4f8ff,#eaf2fb);border:1px solid #cfe0f5;
  border-left:4px solid var(--brand);border-radius:10px;padding:14px 18px;margin:12px 0;text-align:center}
.formula-display .eq{font-family:"Cambria Math","Times New Roman",serif;font-size:19px;color:#0a2a4d;
  letter-spacing:.3px}
.formula-display .eq-sub{font-size:13px;color:var(--muted);margin-top:8px;font-family:"Consolas",monospace}
.kbd{border:1px solid var(--line);border-radius:12px;padding:16px 20px;margin:16px 0;background:var(--soft)}
.kbd.hl5{background:#f1fafc;border-color:#bfe6ee}
.kbd-head{font-size:16px;font-weight:700;color:var(--brand);margin-bottom:6px}
.kbd p{margin:8px 0;font-size:14px}
.src-line{font-size:12.5px;color:var(--muted);border-top:1px dashed var(--line);padding-top:8px;margin-top:10px}
.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin:16px 0}
.card{border:1px solid var(--line);border-radius:10px;padding:14px 16px;background:var(--soft)}
.card h4{margin:0 0 8px}
.pill{display:inline-block;background:#eef3fb;border:1px solid var(--line);border-radius:20px;
  padding:2px 10px;font-size:12px;margin:2px 4px 2px 0;color:var(--brand)}
.legend{font-size:13px;margin-top:8px}
.legend .ok{color:var(--brand2);font-weight:600}
.legend .warn{color:var(--accent);font-weight:600}
footer{margin-top:50px;border-top:1px solid var(--line);padding-top:14px;color:var(--muted);font-size:12.5px}
#search{width:100%;padding:10px 14px;font-size:14px;border:1px solid var(--line);border-radius:8px;margin:8px 0 4px}
@media(max-width:820px){.grid{grid-template-columns:1fr}.wrap{padding:18px 14px}}
"""

# 页头 + TOC
header = '''
<header class="top">
  <h1>基金经理行为分析 — 变量指标体系与构建方法全解</h1>
  <div class="sub">L1 背景特征层 · L2 持仓偏离层 · L3 交易行为层 · L4 风险应对层 · L5 认知行为层 · M 方法论层</div>
  <div class="meta">编制日期：2026-08-11 ｜ 文献覆盖：L1 53 篇 · L2 15 篇 · L3 14 篇 · L4 23 篇 · L5 82 篇 · M 11 篇（合计 198 篇 PDF）<br>
  每层以<strong>一张合并变量总表</strong>呈现，末列标注<strong>文献来源</strong>；★ 标记为本论文重点强调指标。</div>
</header>

<nav class="toc">
  <b>目录</b><br>
  <a href="#s0">〇、使用说明与数据质量</a>
  <a href="#s1">一、变量指标总览</a>
  <a href="#s2">二、L1 变量总表</a>
  <a href="#s3">三、L2 变量总表</a>
  <a href="#s4">四、L3 变量总表</a>
  <a href="#s5">五、L4 变量总表</a>
  <a href="#s6">六、L5 变量总表</a>
  <a href="#s7">七、M 变量总表</a>
  <a href="#s8">八、L1–L3 指标×文献对照</a>
  <a href="#s9">九、重点指标公式详解</a>
  <a href="#s10">十、数据来源汇总</a>
  <a href="#s11">十一、附录文献清单</a>
</nav>
<input id="search" placeholder="🔍 全局搜索变量 / 文献（按关键词过滤各层表格）…" onkeyup="filterRows(this.value)">
'''

# 〇 使用说明
usage = '''
<h2 id="s0">〇、使用说明与数据质量说明</h2>
<p>本文档对六个层级文件夹内的学术文献逐篇抽取并汇总变量指标体系，按「自变量 / 因变量 / 数据来源 / 计算公式 / 文献来源」归类。每个变量标注所属层级（<span class="layer-tag l1">L1</span><span class="layer-tag l2">L2</span><span class="layer-tag l3">L3</span><span class="layer-tag l4">L4</span><span class="layer-tag l5">L5</span><span class="layer-tag lm">M</span>）与代表性出处文献。<strong>★</strong> 标记为本论文（基金经理行为分析）方法论核心、论文解读说明中明确要求着重强调的指标（ARG、RG、收益波动率、DE、LSV、RiskAsys）。</p>
<div class="warn"><b>⚠ 数据质量提示（重要）</b>：文本抽取（OCR / PDF 解析）过程中发现部分文件存在扫描缺失、文件名与内容错配、OCR 损坏等问题。其中 L5 第 10–18 篇组有 4 篇文件名与 PDF 真实内容严重不符（实为货币政策、量子化学、劳动经济学、日本社保等无关文献），已按真实内容提取并标注。凡变量定义/数值带「推测 / 据学术通识」者，正式引用前请回原文核对。</div>
<div class="note"><b>公式显示说明</b>：全文档公式采用 Unicode 数学符号（σ、Σ、α、β、λ、下标/上标）配合专业公式块呈现，无需联网即可正确显示；重点指标在第九节以居中大公式展示完整计算式。</div>
'''

# 一 总览
overview = '''
<h2 id="s1">一、变量指标总览（按层）</h2>
<div class="grid">
  <div class="card"><h4><span class="layer-tag l1">L1</span>背景特征层</h4><p>刻画<strong>基金经理是谁</strong>及激励/声誉环境（静态属性）。</p>
    <span class="pill">个人特征</span><span class="pill">学历/证书</span><span class="pill">从业/任期</span><span class="pill">性别</span><span class="pill">校友网络</span><span class="pill">薪酬激励</span><span class="pill">职业忧虑</span><span class="pill">文本语调</span></div>
  <div class="card"><h4><span class="layer-tag l2">L2</span>持仓偏离层</h4><p>刻画<strong>组合相对基准的主动偏离</strong>（持仓结构）。</p>
    <span class="pill">Active Share</span><span class="pill">Tracking Error</span><span class="pill">行业集中度 ICI/ICR</span><span class="pill">行业分散度 HHI</span><span class="pill">RPI</span><span class="pill">指数 Alpha</span></div>
  <div class="card"><h4><span class="layer-tag l3">L3</span>交易行为层</h4><p>刻画<strong>披露间歇期的隐性交易与交易风格</strong>（动态行为）。</p>
    <span class="pill">Return Gap</span><span class="pill">隐形交易 ARG</span><span class="pill">持有期限 HH</span><span class="pill">换手率</span><span class="pill">动量 LOM/LIM</span><span class="pill">羊群 UHM/SHM</span></div>
  <div class="card"><h4><span class="layer-tag l4">L4</span>风险应对层</h4><p>刻画<strong>排名压力下的风险调整与操纵</strong>。</p>
    <span class="pill">ARG ★</span><span class="pill">RG ★</span><span class="pill">收益波动率 ★</span><span class="pill">RAR</span><span class="pill">锦标赛 RTN</span><span class="pill">Pumping</span><span class="pill">暴跌风险</span></div>
  <div class="card"><h4><span class="layer-tag l5">L5</span>认知行为层</h4><p>刻画<strong>不可直接观测的认知偏差</strong>（核心创新层）。</p>
    <span class="pill">DE 处置效应 ★</span><span class="pill">LSV 交易趋同 ★</span><span class="pill">RiskAsys ★</span><span class="pill">羊群</span><span class="pill">过度自信</span><span class="pill">前景理论</span><span class="pill">机器学习行为</span></div>
  <div class="card"><h4><span class="layer-tag lm">M</span>方法论层</h4><p>刻画<strong>模型设定与因果识别</strong>的方法引擎。</p>
    <span class="pill">Fama-MacBeth</span><span class="pill">Carhart 四因子</span><span class="pill">多向聚类</span><span class="pill">Oster</span><span class="pill">sensemakr</span><span class="pill">分位数回归</span></div>
</div>
<p>三层级递进（L1→L2→L3→L4→L5）构成「属性—结构—行为—风控—认知」的完整画像链条，M 层提供识别方法支撑。</p>
'''

# 各层大表
sections = []
sec_titles = {
    "L1": ('二、L1 背景特征层 — 变量总表', 's2'),
    "L2": ('三、L2 持仓偏离层 — 变量总表', 's3'),
    "L3": ('四、L3 交易行为层 — 变量总表', 's4'),
    "L4": ('五、L4 风险应对层 — 变量总表', 's5'),
    "L5": ('六、L5 认知行为层 — 变量总表', 's6'),
    "M":  ('七、M 方法论与识别检验层 — 变量总表', 's7'),
}
for layer in ["L1", "L2", "L3", "L4", "L5", "M"]:
    rows = L13[layer] if layer in L13 else L456[layer]
    tbl, n_emp = render_master_table(layer, rows)
    title, sid = sec_titles[layer]
    note = ""
    if layer in L456:
        note = '<p class="muted">本表由 %d 篇文献提取变量去重归集，共 %d 个变量条目；标 ★ 者为论文重点指标。</p>' % (
            len([r for r in raw if norm_layer(r) == layer]), len(rows))
    sections.append('<h2 id="%s">%s（共 %d 个变量条目）</h2>%s%s' % (sid, title, len(rows), note, tbl))

# 十 数据来源汇总
sources_sec = '''
<h2 id="s10">十、数据来源汇总</h2>
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

# 十一 附录：从 L1-L3 参考附录 + L4/L5/M 计数
# 提取 L1-L3 参考的 s7 附录表
m_app = re.search(r'<h2 id="s7">.*?</h2>(.*?)<footer>', ref, re.S)
appendix_body = ""
if m_app:
    appendix_body = m_app.group(1)
    # 改写标题与层级标签样式以统一
    appendix_body = re.sub(r'<h2[^>]*>.*?</h2>', '', appendix_body, count=1)
appendix = '''
<h2 id="s11">十一、附录：文献清单与可用性</h2>
<p>L1–L3 文献抽取可用性清单（源自变量指标 L1-L3 参考），并附 L4/L5/M 覆盖说明。</p>
%s
<div class="note">L4 风险应对层 23 篇、L5 认知行为层 82 篇、M 方法论层 11 篇（合计 116 篇）的逐篇变量与文献来源，已并入本文第五、六、七节合并大表；另含 4 篇文件名与内容错配文件（已按真实内容提取并标注）。</div>
''' % appendix_body

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
</script>
"""

OUT = ("<!DOCTYPE html><html lang='zh-CN'><head><meta charset='UTF-8'>"
       "<meta name='viewport' content='width=device-width,initial-scale=1.0'>"
       "<title>基金经理行为分析 — 变量指标体系与构建方法全解（L1–L5 + M）</title>"
       "<style>" + CSS + "</style></head><body><div class='wrap'>"
       + header + usage + overview
       + "".join(sections)
       + render_crosscheck() + EMPH_DETAIL + sources_sec + appendix
       + "<footer>本文档合并《变量指标 L1-L3》参考 + L4/L5/M 文献提取，并重排为每层合并大表（末列文献来源），"
       + "新增 L1–L3 指标×文献对照与重点指标公式详解。生成时间：2026-08-11。</footer>"
       + "</div>" + JS + "</body></html>")

out_path = os.path.join(BASE, "基金经理行为分析_变量指标合并总表_L1-L5+M.html")
with open(out_path, "w", encoding="utf-8") as fh:
    fh.write(OUT)
print("已写出:", out_path, "大小:", os.path.getsize(out_path), "字节")
print("L1/L2/L3 条目:", [len(L13[l]) for l in ['L1','L2','L3']])
print("L4/L5/M 条目:", [len(L456[l]) for l in ['L4','L5','M']])
