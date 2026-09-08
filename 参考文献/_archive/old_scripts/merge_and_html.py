# -*- coding: utf-8 -*-
"""
合并 L4 + M_方法论 文献变量提取 JSON，生成结构化 HTML 报告。
"""
import json, html, os, glob
from datetime import datetime

BASE = r"D:/Desktop/基金经理行为分析研究/参考文献"
files = [
    # L4 风险应对层 (23)
    "extracted_variables_L4_1_6.json",
    "extracted_variables_L4_7_12.json",
    "extracted_variables_L4_13_18.json",
    "extracted_variables_L4_19_23.json",
    # M 方法论与识别检验 (11)
    "extracted_variables_M_1_6.json",
    "extracted_variables_M_7_11.json",
    # L5 认知行为层 (82) - 9 组
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
    p = os.path.join(BASE, f)
    with open(p, encoding="utf-8") as fh:
        data = json.load(fh)
    records.extend(data)

# 按 layer 分组，组内按文件名排序
records.sort(key=lambda r: (r.get("layer", ""), r.get("file", "")))
print(f"合并总记录数: {len(records)}")

# 统计
from collections import Counter
layer_count = Counter(r.get("layer", "?") for r in records)

def esc(x):
    if x is None:
        return ""
    return html.escape(str(x))

def render_var_list(varlist, empty_text="—"):
    if not varlist:
        return f'<span class="muted">{empty_text}</span>'
    # 兼容：部分记录将变量存为纯字符串
    if isinstance(varlist, str):
        return f'<div class="vitem"><div class="vdef">{esc(varlist)}</div></div>'
    out = []
    for v in varlist:
        if not isinstance(v, dict):
            out.append(f'<div class="vitem"><div class="vdef">{esc(v)}</div></div>')
            continue
        name = esc(v.get("name", ""))
        definition = esc(v.get("definition", ""))
        formula = esc(v.get("formula", ""))
        ds = esc(v.get("data_source", ""))
        parts = [f'<div class="vname">{name}</div>']
        if definition:
            parts.append(f'<div class="vdef">{definition}</div>')
        if formula:
            parts.append(f'<div class="vformula"><code>{formula}</code></div>')
        if ds:
            parts.append(f'<div class="vds">数据来源：{ds}</div>')
        out.append('<div class="vitem">' + "".join(parts) + '</div>')
    return "".join(out)

def render_kv(label, value):
    if not value:
        return ""
    return f'<div class="kv"><span class="k">{esc(label)}</span><span class="v">{esc(value)}</span></div>'

cards = []
for i, r in enumerate(records, 1):
    layer = esc(r.get("layer", "?"))
    file = esc(r.get("file", ""))
    title = esc(r.get("title", ""))
    ay = esc(r.get("authors_year", ""))
    topic = esc(r.get("topic", ""))
    iv = render_var_list(r.get("independent_variables"))
    dv = render_var_list(r.get("dependent_variables"))
    cv = esc(r.get("control_variables", ""))
    ds = r.get("data_source", {}) or {}
    ds_str = ""
    if isinstance(ds, dict):
        ds_str = render_kv("样本期", ds.get("sample_period", "")) + \
                 render_kv("数据来源", ds.get("source", "")) + \
                 render_kv("样本量", ds.get("sample_size", ""))
    else:
        ds_str = f'<div class="vdef">{esc(ds)}</div>'
    desc = esc(r.get("descriptive_stats", ""))
    kf = esc(r.get("key_formulas", ""))
    notes = esc(r.get("notes", ""))
    # 文件名与内容不符警示（仅匹配明确“不符”措辞，排除“内容一致”误触发）
    _notes_raw = r.get("notes", "") or ""
    mismatch_kw = ["文件名与内容严重不符", "文件名与内容不符", "文件名与真实内容", "文件名与 PDF 真实内容"]
    exclude_kw = ["文件名与内容一致", "与文件名一致", "与内容一致"]
    is_mismatch = (any(k in _notes_raw for k in mismatch_kw)
                   and not any(k in _notes_raw for k in exclude_kw))
    warn_html = '<div class="warn">⚠ 文件名与 PDF 实际内容不符，已按真实内容提取，请核对文件命名。</div>' if is_mismatch else ""

    card = f'''
    <div class="card" data-layer="{layer}" data-search="{(file+' '+title+' '+topic+' '+ay).lower()}">
      <div class="card-head">
        <div class="card-meta"><span class="badge badge-{layer}">{layer}</span><span class="idx">#{i}</span></div>
        <h3 class="card-title">{title}</h3>
        <div class="card-sub">{ay} · <span class="fname">{file}</span></div>
        <div class="card-topic">{topic}</div>
      </div>
      <div class="card-body">
        <div class="section">
          <div class="sec-label">自变量 (Independent Variables)</div>
          <div class="vlist">{iv}</div>
        </div>
        <div class="section">
          <div class="sec-label">因变量 (Dependent Variables)</div>
          <div class="vlist">{dv}</div>
        </div>
        <div class="section">
          <div class="sec-label">控制变量</div>
          <div class="vdef">{cv if cv else '<span class="muted">—</span>'}</div>
        </div>
        <div class="section">
          <div class="sec-label">数据来源</div>
          <div class="kv-wrap">{ds_str}</div>
        </div>
        <div class="section two-col">
          <div>
            <div class="sec-label">描述性统计</div>
            <div class="vdef">{desc if desc else '<span class="muted">—</span>'}</div>
          </div>
          <div>
            <div class="sec-label">核心公式</div>
            <div class="vdef"><code>{kf if kf else '—'}</code></div>
          </div>
        </div>
        <div class="section">
          <div class="sec-label">备注</div>
          <div class="vdef">{notes if notes else '<span class="muted">—</span>'}</div>
          {warn_html}
        </div>
      </div>
    </div>'''
    cards.append(card)

stat_html = "".join(
    f'<div class="stat"><div class="stat-num">{c}</div><div class="stat-label">{k} 层</div></div>'
    for k, c in sorted(layer_count.items())
)

html_doc = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>基金经理行为分析 · 文献变量提取汇总（L4 + L5 + M）</title>
<style>
  :root {{
    --bg: #0f1115; --panel: #181b22; --panel2: #1f232c; --border: #2a2f3a;
    --text: #e6e8ec; --muted: #8b93a1; --accent: #4f9dff; --accent2: #ffb454;
    --L4: #5eb3ff; --M: #ffb454;
  }}
  * {{ box-sizing: border-box; }}
  body {{ margin:0; background:var(--bg); color:var(--text);
    font-family: -apple-system, "Segoe UI", "Microsoft YaHei", Roboto, sans-serif;
    line-height: 1.6; }}
  .wrap {{ max-width: 1180px; margin: 0 auto; padding: 32px 24px 80px; }}
  header h1 {{ font-size: 26px; margin: 0 0 8px; }}
  header p {{ color: var(--muted); margin: 4px 0; }}
  .stats {{ display:flex; gap:16px; flex-wrap:wrap; margin: 24px 0; }}
  .stat {{ background: var(--panel); border:1px solid var(--border); border-radius:12px;
    padding: 16px 24px; min-width: 120px; }}
  .stat-num {{ font-size: 30px; font-weight: 700; color: var(--accent); }}
  .stat-label {{ color: var(--muted); font-size: 13px; }}
  .toolbar {{ display:flex; gap:12px; margin: 20px 0; flex-wrap:wrap; align-items:center; }}
  .toolbar input, .toolbar select {{ background: var(--panel2); border:1px solid var(--border);
    color: var(--text); padding: 8px 12px; border-radius: 8px; font-size: 14px; }}
  .toolbar input {{ flex: 1; min-width: 220px; }}
  .card {{ background: var(--panel); border:1px solid var(--border); border-radius:14px;
    margin-bottom: 18px; overflow:hidden; }}
  .card-head {{ padding: 18px 20px 12px; border-bottom:1px solid var(--border);
    background: linear-gradient(180deg, var(--panel2), var(--panel)); }}
  .card-meta {{ display:flex; align-items:center; gap:10px; margin-bottom:6px; }}
  .badge {{ font-size:12px; font-weight:600; padding:2px 10px; border-radius:20px; }}
  .badge-L4 {{ background: rgba(94,179,255,.15); color: var(--L4); border:1px solid rgba(94,179,255,.3); }}
  .badge-L5 {{ background: rgba(126,231,135,.15); color: #7ee787; border:1px solid rgba(126,231,135,.3); }}
  .badge-M {{ background: rgba(255,180,84,.15); color: var(--M); border:1px solid rgba(255,180,84,.3); }}
  .idx {{ color: var(--muted); font-size:13px; }}
  .card-title {{ font-size: 18px; margin: 2px 0 4px; }}
  .card-sub {{ color: var(--muted); font-size: 13px; }}
  .fname {{ font-family: Consolas, monospace; font-size:12px; color:#9fb0c8; word-break:break-all; }}
  .card-topic {{ color: var(--accent2); font-size: 13px; margin-top:6px; }}
  .card-body {{ padding: 16px 20px 20px; }}
  .section {{ margin-bottom: 14px; }}
  .sec-label {{ font-size: 13px; font-weight:600; color: var(--accent);
    text-transform: uppercase; letter-spacing:.5px; margin-bottom:8px; }}
  .vlist {{ display:flex; flex-direction:column; gap:8px; }}
  .vitem {{ background: var(--panel2); border:1px solid var(--border); border-radius:8px; padding:10px 12px; }}
  .vname {{ font-weight:600; color: #fff; }}
  .vdef {{ color: var(--muted); font-size:14px; }}
  .warn {{ color:#ff6b6b; font-size:12px; margin-top:4px; }}
  .vformula code, .card-body code {{ background:#0c0e12; color:#9fe6a0; padding:2px 6px;
    border-radius:5px; font-family: Consolas, monospace; font-size:13px; }}
  .vds {{ color:#7fa8d6; font-size:12px; margin-top:2px; }}
  .kv-wrap {{ display:flex; flex-direction:column; gap:6px; }}
  .kv {{ display:flex; gap:12px; }}
  .kv .k {{ color: var(--muted); min-width:80px; font-size:13px; }}
  .kv .v {{ color: var(--text); }}
  .two-col {{ display:grid; grid-template-columns:1fr 1fr; gap:18px; }}
  @media (max-width:700px) {{ .two-col {{ grid-template-columns:1fr; }} }}
  .muted {{ color: var(--muted); }}
  footer {{ margin-top:40px; color: var(--muted); font-size:13px; text-align:center; }}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <h1>基金经理行为分析 · 文献变量提取汇总</h1>
    <p>层级范围：<strong>L4 风险应对层</strong> + <strong>L5 认知行为层</strong> + <strong>M 方法论与识别检验</strong></p>
    <p>生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')} ｜ 共 {len(records)} 篇文献</p>
  </header>
  <div class="stats">{stat_html}
    <div class="stat"><div class="stat-num">{len(records)}</div><div class="stat-label">合计</div></div>
  </div>
  <div class="toolbar">
    <input id="search" type="text" placeholder="搜索文件名 / 标题 / 主题 / 作者…">
    <select id="filter">
      <option value="">全部层级</option>
      <option value="L4">L4 风险应对层</option>
      <option value="L5">L5 认知行为层</option>
      <option value="M">M 方法论与识别检验</option>
    </select>
  </div>
  <div id="results">{''.join(cards)}</div>
  <footer>数据来源于各文献正文提取，公式与数据来源以原文为准。本表用于研究变量梳理，不构成投资建议。</footer>
</div>
<script>
  const search = document.getElementById('search');
  const filter = document.getElementById('filter');
  const cards = Array.from(document.querySelectorAll('.card'));
  function apply() {{
    const q = search.value.trim().toLowerCase();
    const f = filter.value;
    let shown = 0;
    cards.forEach(c => {{
      const layer = c.getAttribute('data-layer');
      const hay = c.getAttribute('data-search') || '';
      const okLayer = !f || layer === f;
      const okQ = !q || hay.includes(q);
      const vis = okLayer && okQ;
      c.style.display = vis ? '' : 'none';
      if (vis) shown++;
    }});
  }}
  search.addEventListener('input', apply);
  filter.addEventListener('change', apply);
</script>
</body>
</html>'''

out_path = os.path.join(BASE, "文献变量提取汇总_L4_L5_M.html")
with open(out_path, "w", encoding="utf-8") as fh:
    fh.write(html_doc)
print("HTML 已生成:", out_path)
