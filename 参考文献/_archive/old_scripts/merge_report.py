# -*- coding: utf-8 -*-
"""
将 L4 / L5 / M 三层文献变量提取 JSON 重新排版为「报告式」HTML，
视觉与结构对齐参考文件 变量指标L1-L3.html（浅色主题、目录、层级标签、表格、公式块）。
"""
import json, html, os, glob
from datetime import datetime
from collections import Counter, defaultdict

BASE = r"D:/Desktop/基金经理行为分析研究/参考文献"
files = [
    "extracted_variables_L4_1_6.json",
    "extracted_variables_L4_7_12.json",
    "extracted_variables_L4_13_18.json",
    "extracted_variables_L4_19_23.json",
    "extracted_variables_M_1_6.json",
    "extracted_variables_M_7_11.json",
    "extracted_variables_L5_G1.json",
    "extracted_variables_L5_G2.json",
    "extracted_variables_L5_G3.json",
    "extracted_variables_L5_G4.json",
    "extracted_variables_L5_G5.json",
    "extracted_variables_L5_G6.json",
    "extracted_variables_L5_G7.json",
    "extracted_variables_L5_G8.json",
    "extracted_variables_L5_G9.json",
]

records = []
for f in files:
    with open(os.path.join(BASE, f), encoding="utf-8") as fh:
        records.extend(json.load(fh))

LAYER_ORDER = {"L4": 0, "L5": 1, "M": 2}
LAYER_NAME = {"L4": "L4 风险应对层", "L5": "L5 认知行为层", "M": "M 方法论与识别检验"}
records.sort(key=lambda r: (LAYER_ORDER.get(r.get("layer", ""), 9), r.get("file", "")))
print("合并总记录数:", len(records))

def esc(x):
    return html.escape("" if x is None else str(x))

# ---- 变量行渲染（表格） ----
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
        rows.append(f"<tr><td>{name}</td><td>{defn}</td><td>{fcell}</td><td>{dscell}</td></tr>")
    return "".join(rows)

def layer_tag(layer):
    return f'<span class="layer-tag l{layer.lower()}">{layer}</span>'

# ---- 错名检测（沿用合并脚本逻辑） ----
def is_mismatch(r):
    n = r.get("notes", "") or ""
    kw = ["文件名与内容严重不符", "文件名与内容不符", "文件名与真实内容", "文件名与 PDF 真实内容"]
    ex = ["文件名与内容一致", "与文件名一致", "与内容一致"]
    return any(k in n for k in kw) and not any(k in n for k in ex)

mismatch_files = [r for r in records if is_mismatch(r)]

# =====================================================================
#  CSS（浅色主题，对齐参考文件）
# =====================================================================
CSS = """
  :root{
    --bg:#ffffff; --fg:#1f2a37; --muted:#5b6675; --line:#e3e8ef; --soft:#f6f8fb;
    --brand:#16407a; --brand2:#0b6e4f; --accent:#b4231f; --chip:#eef3fb;
    --l4:#16407a; --l5:#0b6e4f; --m:#9a4b00;
  }
  *{box-sizing:border-box}
  body{margin:0;font-family:"Segoe UI","Microsoft YaHei","PingFang SC",system-ui,sans-serif;
       color:var(--fg);background:var(--bg);line-height:1.75;font-size:15px}
  .wrap{max-width:1180px;margin:0 auto;padding:32px 28px 80px}
  header.top{border-bottom:3px solid var(--brand);padding-bottom:18px;margin-bottom:8px}
  header.top h1{font-size:27px;margin:0 0 6px;color:var(--brand);letter-spacing:.5px}
  header.top .sub{color:var(--muted);font-size:14px}
  .meta{margin-top:10px;font-size:13px;color:var(--muted)}
  nav.toc{position:sticky;top:0;background:rgba(255,255,255,.96);backdrop-filter:blur(4px);
          border:1px solid var(--line);border-radius:10px;padding:12px 16px;margin:18px 0 28px;z-index:5}
  nav.toc b{color:var(--brand)}
  nav.toc a{color:var(--fg);text-decoration:none;margin:0 10px 4px 0;display:inline-block;font-size:13.5px}
  nav.toc a:hover{color:var(--brand);text-decoration:underline}
  h2{font-size:22px;color:var(--brand);border-left:6px solid var(--brand);padding-left:12px;margin:38px 0 14px}
  h3{font-size:18px;color:var(--brand2);margin:26px 0 10px}
  h4{font-size:15.5px;color:var(--accent);margin:18px 0 8px}
  p{margin:8px 0}
  .note{background:var(--soft);border:1px solid var(--line);border-left:4px solid var(--brand);
        border-radius:8px;padding:12px 16px;margin:14px 0}
  .warn{background:#fff6f5;border:1px solid #f3c9c5;border-left:4px solid var(--accent);border-radius:8px;padding:12px 16px;margin:14px 0}
  .layer-tag{display:inline-block;font-size:12px;font-weight:700;color:#fff;border-radius:5px;padding:1px 8px;margin-right:6px;vertical-align:middle}
  .l4{background:var(--l4)} .l5{background:var(--l5)} .lm{background:var(--m)}
  table{border-collapse:collapse;width:100%;margin:12px 0 18px;font-size:13.3px}
  th,td{border:1px solid var(--line);padding:7px 9px;vertical-align:top;text-align:left}
  th{background:var(--chip);color:var(--brand);font-weight:700;position:sticky}
  tr:nth-child(even) td{background:#fafcff}
  code{background:#eef2f7;padding:1px 5px;border-radius:4px;font-family:"Consolas","Courier New",monospace;font-size:12.6px;color:#0a3a66}
  .formula{background:#f3f7fb;border:1px dashed #b9cbe6;border-radius:8px;padding:10px 14px;margin:8px 0;font-family:"Consolas",monospace;font-size:13px;color:#0a3a66;overflow-x:auto;white-space:pre-wrap}
  ul,ol{margin:8px 0 8px 22px} li{margin:3px 0}
  .grid{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin:16px 0}
  .card{border:1px solid var(--line);border-radius:10px;padding:14px 16px;background:var(--soft)}
  .card h4{margin-top:0}
  footer{margin-top:50px;border-top:1px solid var(--line);padding-top:14px;color:var(--muted);font-size:12.5px}
  .pill{display:inline-block;background:var(--chip);border:1px solid var(--line);border-radius:20px;padding:2px 10px;font-size:12px;margin:2px 4px 2px 0;color:var(--brand)}
  .muted{color:var(--muted)}
"""

# =====================================================================
#  章节内容
# =====================================================================
layer_counts = Counter(r.get("layer", "?") for r in records)

# --- 〇、使用说明与数据质量 ---
s0 = f"""
<h2 id="s0">〇、使用说明与数据质量说明</h2>
<p>本文档对 <b>L4 风险应对层</b>、<b>L5 认知行为层</b>、<b>M 方法论与识别检验</b> 三个层级文件夹内的学术文献逐篇抽取并汇总了变量指标体系，严格按「自变量 / 因变量 / 数据来源 / 描述性统计 / 计算公式」五大维度归类。所有变量均标注了所属层级（{layer_tag('L4')}{layer_tag('L5')}{layer_tag('M')}）与出处文献文件名。</p>
<div class="warn">
  <b>⚠ 数据质量提示（重要）</b>：在 PDF 解析 / 文本抽取过程中，发现部分文件存在以下问题，相关变量的可靠性需在正式写作前复核原文：
  <ul>
    <li><b>① 文件名与正文内容错配（非对应主题，已按真实内容提取并标注）</b>：共 {len(mismatch_files)} 篇，均位于 L5 第 10–18 篇组：
      <ul>
        {"".join(f"<li><code>{esc(m.get('file',''))}</code> —— 实为：{esc((m.get('notes','') or '').replace('【文件名与内容严重不符】','').split('。')[0])}</li>" for m in mismatch_files)}
      </ul>
    </li>
    <li><b>② OCR 扫描质量较差（公式/数值残缺，已按可读片段整理）</b>：个别中文论文（如 L5 中部分羊群/处置效应文献、苏艳丽等《中国证券投资基金羊群行为和正反馈行为研究》等）原文扫描模糊，变量定义完整、公式按可读字符片段还原，文中 notes 已注明。</li>
    <li><b>③ 综述类文献（无实证变量）</b>：少数文献为理论/文献综述（如 M 中部分方法评述、L5 中《羊群效应理论及其对中国股市的现实意义》《证券投资基金羊群行为的研究趋向》等），变量字段留空或仅列理论机制，已在对应条目标注。</li>
  </ul>
  建议：正式引用前，对带「（推测）」「据原文/可读片段」标注的条目，务必回到原文核对变量定义、符号与统计数值；错配文件的真正主题文献请按 notes 中标注的真实作者/标题检索。
</div>
"""

# --- 一、变量指标总览（按层） ---
OVERVIEW = {
    "L4": ("风险应对层", "刻画基金经理在<b>排名竞争、锦标赛激励与风险约束</b>下的应对行为，是画像的「压力响应」维度。",
           ["锦标赛激励", "排名压力", "风格漂移", "风险调整", "冒险行为", "隐性交易", "社会网络", "业绩拉升"]),
    "L5": ("认知行为层", "刻画基金经理的<b>认知偏差与群体行为</b>（羊群、处置效应、过度自信、前景理论），是画像的「行为心理」维度。",
           ["羊群行为", "处置效应", "过度自信", "前景理论", "性别差异", "机器学习", "文本情绪", "基金抱团"]),
    "M": ("方法论与识别检验", "提供<b>计量识别与方法工具</b>（Fama-MacBeth、因子模型、分位数回归、遗漏变量敏感性），是变量度量的「方法底座」维度。",
          ["Fama-MacBeth", "动量因子", "Carhart四因子", "分位数回归", "遗漏变量敏感性", "聚类稳健", "PSM-DID"]),
}
s1_cards = []
for ly in ["L4", "L5", "M"]:
    desc, pills = OVERVIEW[ly][1], OVERVIEW[ly][2]
    pill_html = "".join(f'<span class="pill">{p}</span>' for p in pills)
    s1_cards.append(f"""
    <div class="card">
      <h4>{layer_tag(ly)}{LAYER_NAME[ly]}</h4>
      <p>{desc}</p>
      {pill_html}
    </div>""")
s1 = f"""
<h2 id="s1">一、变量指标总览（按层）</h2>
<div class="grid">{"".join(s1_cards)}</div>
<p>三层级变量构成完整的「属性—结构—行为—方法」画像链条：L4 解释「压力下如何调整」，L5 捕捉「认知与群体行为如何偏差」，M 提供「如何科学识别与度量」的方法论支撑，共同服务于基金经理投资行为画像的学术框架。</p>
"""

# --- 二、自变量明细（逐篇，按层） ---
def section_vars(kind):  # kind: 'iv' or 'dv'
    out = []
    for ly in ["L4", "L5", "M"]:
        papers = [r for r in records if r.get("layer") == ly]
        out.append(f'<h3>{layer_tag(ly)}{LAYER_NAME[ly]} — {"自变量" if kind=="iv" else "因变量"}</h3>')
        col = "变量（中/英） | 定义与度量方式 | 计算公式 / 取值 | " + ("数据来源" if kind=="iv" else "代表文献")
        for r in papers:
            ay = esc(r.get("authors_year", ""))
            title = esc(r.get("title", ""))
            fname = esc(r.get("file", ""))
            vars_ = r.get("independent_variables" if kind=="iv" else "dependent_variables")
            head = "数据来源" if kind=="iv" else "代表文献"
            rows = var_rows(vars_, kind)
            rep = title if kind=="dv" else ""
            # DV 表最后一列用代表文献；IV 用数据来源（已在行内）
            out.append(f"""
            <h4>{layer_tag(ly)}{ay} — {title}</h4>
            <p class="muted" style="font-size:12.5px;margin:2px 0 6px">文件：<code>{fname}</code></p>
            <table>
            <thead><tr><th>变量（中/英）</th><th>定义与度量方式</th><th>计算公式 / 取值</th><th>{head}</th></tr></thead>
            <tbody>{rows}</tbody>
            </table>""")
    return "".join(out)

s2 = f'<h2 id="s2">二、自变量明细（解释变量 X，逐篇）</h2><p>以下按层级、逐篇列出各文献的核心自变量。同一变量被多篇使用，此处保留各文献的原始定义与度量，便于溯源。</p>' + section_vars("iv")
s3 = f'<h2 id="s3">三、因变量明细（被解释变量 Y，逐篇）</h2><p>以下按层级、逐篇列出各文献的核心因变量，最后一列标注该变量的出处文献。</p>' + section_vars("dv")

# --- 四、数据来源汇总（聚合） ---
def categorize_source(src):
    s = (src or "")
    overseas = ["CRSP", "Thomson", "IBES", "Compustat", "Ken French", "Morningstar", "WRDS", "NBER", "SEC", "S&P", "Russell", "Wilshire", "Census", "NYSE", "NASDAQ"]
    domestic = ["Wind", "CSMAR", "RESSET", "锐思", "聚源", "天相", "国泰君安", "CCER", "巨潮", "金融界", "中国基金网", "好买", "同花顺", "国泰安"]
    sl = s.lower()
    if any(k.lower() in sl for k in overseas):
        return "海外"
    if any(k in s for k in domestic):
        return "国内"
    return "其他"

src_counter = Counter()
src_papers = defaultdict(list)
for r in records:
    ds = r.get("data_source") or {}
    src = ds.get("source", "") if isinstance(ds, dict) else ""
    if not src:
        continue
    # 可能有多个来源用顿号/、/；拆分
    for piece in str(src).replace("；", "；").split("；"):
        piece = piece.strip()
        if not piece:
            continue
        src_counter[piece] += 1
        src_papers[piece].append(esc(r.get("file", "")))

ov_rows, dom_rows, oth_rows = [], [], []
for src, cnt in src_counter.most_common():
    cat = categorize_source(src)
    ex = "、".join(sorted(set(src_papers[src]))[:3])
    row = f"<tr><td>{esc(src)}</td><td>{cnt}</td><td>{ex}{' 等' if len(set(src_papers[src]))>3 else ''}</td></tr>"
    if cat == "海外": ov_rows.append(row)
    elif cat == "国内": dom_rows.append(row)
    else: oth_rows.append(row)

s4 = f"""
<h2 id="s4">四、数据来源汇总</h2>
<p>各文献的数据底座高度集中，可归纳为「海外库」「国内库」与「方法/实验」三大类（按出现频次降序列出）：</p>
<h3>① 海外数据库（主要支撑 M 方法论文及部分国际文献）</h3>
<table><thead><tr><th>数据库 / 来源</th><th>出现频次</th><th>典型使用文献（文件）</th></tr></thead><tbody>{''.join(ov_rows)}</tbody></table>
<h3>② 国内数据库（主要支撑 L4/L5 中国文献）</h3>
<table><thead><tr><th>数据库 / 来源</th><th>出现频次</th><th>典型使用文献（文件）</th></tr></thead><tbody>{''.join(dom_rows)}</tbody></table>
<h3>③ 方法 / 实验 / 手工整理</h3>
<table><thead><tr><th>来源</th><th>出现频次</th><th>典型使用文献（文件）</th></tr></thead><tbody>{''.join(oth_rows)}</tbody></table>
<div class="note"><b>样本区间与频率共性</b>：海外文献多取 1980s–2000s、半年度/季度持仓 + 日/月收益；国内文献多取 2003–2020s、开放式偏股/股票型主动基金，频率多为季度/半年度或年度。国内文献普遍对连续变量做 1% 或 0.5% 缩尾（Winsorize）。</div>
"""

# --- 五、描述性统计汇总（逐篇，仅列有内容者） ---
desc_blocks = []
for r in records:
    d = r.get("descriptive_stats") or ""
    if not d or not str(d).strip():
        continue
    ly = r.get("layer", "")
    desc_blocks.append(f"""
    <h4>{layer_tag(ly)}{esc(r.get('authors_year',''))} — {esc(r.get('title',''))}</h4>
    <p>{esc(d)}</p>""")
s5 = f"""
<h2 id="s5">五、描述性统计汇总</h2>
<p>以下为各文献在文中报告的描述性统计（已尽量原文照录；未报告或 OCR 残缺者未列入，详见各篇 notes）。</p>
{''.join(desc_blocks)}
<div class="note">说明：受 PDF 抽取限制，部分文献未给出集中的均值/标准差描述性统计表，或数值未能完整识别，已在对应条目标注。建议引用前回原文核对具体数值。</div>
"""

# --- 六、关键计算公式汇编（逐篇，按层） ---
formula_blocks = []
for ly in ["L4", "L5", "M"]:
    items = []
    for r in records:
        if r.get("layer") != ly:
            continue
        kf = r.get("key_formulas") or ""
        if not kf or not str(kf).strip():
            continue
        items.append(f'<div class="formula">{esc(kf)}\n　—— {esc(r.get("authors_year",""))} 《{esc(r.get("title",""))}》</div>')
    if items:
        formula_blocks.append(f'<h3>{layer_tag(ly)}{LAYER_NAME[ly]} — 核心公式</h3>' + "".join(items))
s6 = f"""
<h2 id="s6">六、关键计算公式汇编</h2>
<p>按层级集中列出各文献报告的核心变量计算公式与度量方法，便于直接引用与横向比较。</p>
{''.join(formula_blocks)}
"""

# --- 七、附录：文献清单与可用性 ---
app_rows = []
for r in records:
    ly = r.get("layer", "")
    fname = esc(r.get("file", ""))
    if is_mismatch(r):
        avail = '<span style="color:#b4231f">⚠ 文件名与内容错配，已按真实内容提取</span>'
    elif (r.get("notes") or "").find("OCR") >= 0 or (r.get("notes") or "").find("扫描") >= 0 or (r.get("notes") or "").find("乱码") >= 0:
        avail = "扫描/OCR 损坏，公式按可读片段整理"
    elif (r.get("notes") or "").find("综述") >= 0 or (r.get("notes") or "").find("无实证") >= 0:
        avail = "综述类，无实证变量"
    else:
        avail = "✅ 可用"
    app_rows.append(f"<tr><td>{layer_tag(ly)}{ly}</td><td><code>{fname}</code></td><td>{avail}</td></tr>")
s7 = f"""
<h2 id="s7">七、附录：文献清单与可用性</h2>
<p>下表列出 L4/L5/M 三层全部 {len(records)} 篇文献及其文本抽取可用性，便于追溯与复核。</p>
<table><thead><tr><th>层级</th><th>文献（文件名）</th><th>可用性</th></tr></thead><tbody>{''.join(app_rows)}</tbody></table>
"""

# =====================================================================
#  组装 HTML
# =====================================================================
TOC = """
<nav class="toc">
  <b>目录</b><br>
  <a href="#s0">〇、使用说明与数据质量</a>
  <a href="#s1">一、变量指标总览（按层）</a>
  <a href="#s2">二、自变量明细</a>
  <a href="#s3">三、因变量明细</a>
  <a href="#s4">四、数据来源汇总</a>
  <a href="#s5">五、描述性统计汇总</a>
  <a href="#s6">六、关键计算公式汇编</a>
  <a href="#s7">七、附录：文献清单与可用性</a>
</nav>
"""

html_doc = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>基金经理投资行为画像 — 变量指标体系汇总（L4 / L5 / M）</title>
<style>{CSS}</style>
</head>
<body>
<div class="wrap">

<header class="top">
  <h1>基金经理投资行为画像 — 变量指标体系汇总</h1>
  <div class="sub">基于 L4 风险应对层 · L5 认知行为层 · M 方法论与识别检验 三层级文献的系统梳理</div>
  <div class="meta">编制日期：2026-08-11 ｜ 文献覆盖：L4 风险应对层 {layer_counts.get('L4',0)} 篇、L5 认知行为层 {layer_counts.get('L5',0)} 篇、M 方法论与识别检验 {layer_counts.get('M',0)} 篇（合计 {len(records)} 篇）<br>
  内容维度：① 变量指标总览 ② 自变量明细 ③ 因变量明细 ④ 数据来源 ⑤ 描述性统计 ⑥ 计算公式</div>
</header>

{TOC}
{s0}
{s1}
{s2}
{s3}
{s4}
{s5}
{s6}
{s7}

<footer>
本报告由文献文本抽取 + 多智能体变量抽取 + 人工汇总而成，变量定义、公式与统计数值尽量忠实原文；凡带「推测 / 据原文 / 可读片段」标注者，正式引用前请回原文核对。
生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')} ｜ 文件：文献变量提取汇总_L4_L5_M_报告版.html
</footer>

</div>
</body>
</html>"""

out_path = os.path.join(BASE, "文献变量提取汇总_L4_L5_M_报告版.html")
with open(out_path, "w", encoding="utf-8") as fh:
    fh.write(html_doc)
print("HTML 已生成:", out_path, "大小:", os.path.getsize(out_path), "bytes")
