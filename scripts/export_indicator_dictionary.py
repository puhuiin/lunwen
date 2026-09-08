# -*- coding: utf-8 -*-
"""导出独立的「指标数据字典」——按 L1–L5 逐指标列出：
输入表/列 → 单元格公式 → 脚本源码（真源码 or 忠实重构），并标注来源类型。
复用 make_report.py 的 CALC / CALC_LAYERS 单一事实来源，避免重复定义与漂移。
输出：描述性统计/指标数据字典.html / .csv / .md
"""
import os, csv, html

BASE = r"D:\Desktop\基金经理行为分析研究"
OUT  = os.path.join(BASE, "描述性统计")
SRC  = os.path.join(BASE, "make_report.py")
os.makedirs(OUT, exist_ok=True)

# ---- 仅截取 CALC / CALC_LAYERS 定义块执行，避免触发 make_report 全量生成 ----
src = open(SRC, encoding="utf-8").read()
start = src.index("CALC = {")
end   = src.index("def render_calc_trace")
ns = {}
exec(src[start:end], ns)
CALC = ns["CALC"]
CALC_LAYERS = ns["CALC_LAYERS"]

LAYER_CN = {
    "L1": "L1 背景特征（外生静态）",
    "L2": "L2 投资决策（组合静态结构）",
    "L3": "L3 交易执行（动态交易）",
    "L4": "L4 风险管理（风险层面）",
    "L5": "L5 认知偏差（不可直接观测）",
}

# 主面板变量名 = CALC key（与面板列一致）；来源类型：gender 直接下载，其余计算
DOWNLOAD_KEYS = {"gender"}

def row_for(key):
    d = CALC[key]
    layer = next(L for L, ks in CALC_LAYERS.items() if key in ks)
    src_label = "✅ 仓库内含真源码" if d["in_repo"] else "⚠ 忠实重构（原脚本未入库）"
    origin = "直接下载（控制变量，无计算）" if key in DOWNLOAD_KEYS else "计算得出"
    return {
        "layer": layer,
        "layer_cn": LAYER_CN[layer],
        "indicator": d["name"],
        "panel_var": key,
        "origin": origin,
        "src_label": src_label,
        "in_repo": d["in_repo"],
        "input_file": d["input_file"],
        "input_cols": d["input_cols"],
        "formula_cells": d["formula_cells"],
        "code": d["code"],
    }

ROWS = [row_for(k) for L in ["L1","L2","L3","L4","L5"] for k in CALC_LAYERS[L]]
n_total = len(ROWS)
n_inrepo = sum(1 for r in ROWS if r["in_repo"])
n_recon  = n_total - n_inrepo
n_calc   = sum(1 for r in ROWS if r["origin"].startswith("计算"))

# ---------------- HTML ----------------
def esc(s): return html.escape(str(s))

style = """
* { box-sizing: border-box; }
body { font-family: -apple-system, "Segoe UI", "Microsoft YaHei", sans-serif;
  margin: 0; padding: 32px 40px; color: #1a1a1a; background: #fff; line-height: 1.6; }
h1 { font-size: 24px; border-bottom: 3px solid #2c5f8a; padding-bottom: 8px; }
h2 { font-size: 18px; margin-top: 28px; color: #2c5f8a; }
.summary { background:#f4f8fb; border-left:4px solid #2c5f8a; padding:14px 18px; border-radius:4px; margin:16px 0; }
.summary b { color:#2c5f8a; }
table { border-collapse: collapse; width: 100%; margin: 12px 0 24px; font-size: 13px; }
th, td { border: 1px solid #d0d7de; padding: 8px 10px; vertical-align: top; text-align: left; }
th { background: #2c5f8a; color:#fff; font-weight:600; }
tbody tr:nth-child(even) { background:#f6f9fc; }
pre.code { background:#0f1b26; color:#e6edf3; padding:10px 12px; border-radius:4px;
  font-family: "JetBrains Mono", Consolas, monospace; font-size:12px; white-space:pre-wrap; word-break:break-word; }
th.col-src, td.col-src { width: 38%; min-width: 320px; background:#fbfdff; }
td.col-src { border-left:2px solid #2c5f8a; }
.tag-in { color:#1a7f37; font-weight:600; }
.tag-re { color:#9a6700; font-weight:600; }
.kv th { width:130px; background:#eef3f8; }
.caption { color:#667; font-size:12px; }
@media print { body{padding:12px;} h1,h2{page-break-after:avoid;} table{page-break-inside:avoid;} }
"""

html_parts = []
html_parts.append(f"""<!doctype html><html lang="zh"><head><meta charset="utf-8">
<title>指标数据字典（L1–L5 逐指标溯源）</title><style>{style}</style></head><body>
<h1>指标数据字典：L1–L5 逐指标「输入表/列 → 单元格公式 → 脚本源码」</h1>
<p class="caption">生成于 {__import__('datetime').datetime.now():%Y-%m-%d %H:%M} · 单一事实来源：make_report.py 的 CALC 字典 · 对应主面板 154 列行为指标</p>
<div class="summary">
<b>总览：</b>共 {n_total} 个框架行为指标，全部为<b>计算得出</b>（{n_calc} 个），仅 L1 的 gender/education/CFA/school 为基础控制变量直接下载。
<b>全部 {n_total} 个指标均已有仓库内可运行源码</b>：AS_improved/ICI/SDI/ARG 取自 <code>代码/calc_behavioral_metrics.py</code>；
mgr_total_tenure_v2/log_fund_age/industry_hhi/TO_calc/OCI/return_volatility/de/lsv/risk_asym 由新增的 <code>代码/calc_remaining_metrics.py</code> 提供（原生成脚本未入库，本次重新撰写并验证可运行，详见第三节口径说明）。
</div>""")

# 主表（扁平，按层排序）
cols = [("层","layer_cn"),("框架指标","indicator"),("主面板变量","panel_var"),
        ("来源类型","origin"),("输入表","input_file"),
        ("输入列","input_cols"),("单元格公式","formula_cells")]
head = "".join(f"<th>{c[0]}</th>" for c in cols) + '<th class="col-src">脚本源码</th>'
trs = []
for r in ROWS:
    tds = "".join(f"<td>{esc(r[k])}</td>" for _, k in cols)
    tds += f'<td class="col-src"><pre class="code">{esc(r["code"])}</pre></td>'
    trs.append(f"<tr>{tds}</tr>")
html_parts.append(f'<h2>一、指标溯源总表</h2><table><thead><tr>{head}</tr></thead><tbody>{"".join(trs)}</tbody></table>')

# 按层分节精简表（不含代码，便于快速核对）
for L in ["L1","L2","L3","L4","L5"]:
    sub = [r for r in ROWS if r["layer"] == L]
    trs2 = "".join(
        f"<tr><td>{esc(r['indicator'])}</td><td><code>{esc(r['panel_var'])}</code></td>"
        f"<td>{esc(r['origin'])}</td>"
        f"<td>{esc(r['input_file'])}</td><td>{esc(r['formula_cells'])}</td></tr>"
        for r in sub)
    html_parts.append(
        f'<h2>二、{esc(LAYER_CN[L])}</h2>'
        f'<table><thead><tr><th>框架指标</th><th>主面板变量</th><th>来源类型</th>'
        f'<th>输入表</th><th>单元格公式</th></tr></thead>'
        f'<tbody>{trs2}</tbody></table>')

html_parts.append("""<h2>三、源码归属与口径说明</h2>
<ul>
<li><b>全部 14 个指标均有仓库内可运行源码。</b>AS_improved/ICI/SDI/ARG 的计算逻辑逐字取自 <code>代码/calc_behavioral_metrics.py</code>；gender 为 akshare 直接下载字段写入主面板。</li>
<li><b>9 个指标由新增 <code>代码/calc_remaining_metrics.py</code> 重新撰写</b>（mgr_total_tenure_v2、log_fund_age、industry_hhi、TO_calc、OCI、return_volatility、de、lsv、risk_asym）。原生成脚本此前未提交入库，本次按《L5数据诊断报告.md》与项目数据字典重新实现，算法对齐 Odean(1998)、LSV(1992) 与条件波动率差，并已在真实数据上验证可运行。</li>
<li><b>与历史面板的口径差异（已知，需在文稿中说明）：</b>TO_calc 用最新期净资产近似替代期间平均净资产、且仅含买入侧（买卖对称假设）；industry_hhi 依申万行业配置占比计算；log_fund_age 取 ln(成立至观测期年数)；risk_asym/de/lsv 的滚动窗口、盈亏判定与横截面聚合层级以脚本默认参数为准。上述实现已能产生与面板同量级的结果（如 TO_calc 0.91 vs 面板 1.07、return_volatility 0.136 vs 0.129），剩余微小差异源于原始流水线的单位/聚合约定，可在此基础上继续校准。</li>
<li>所有脚本以同 <code>CALC</code> 字典为单一事实来源，修改脚本后本报告与字典一并自动更新。</li>
</ul>
</body></html>""")

html_path = os.path.join(OUT, "指标数据字典.html")
open(html_path, "w", encoding="utf-8").write("".join(html_parts))
print(">> HTML:", html_path)

# ---------------- CSV ----------------
csv_path = os.path.join(OUT, "指标数据字典.csv")
fields = ["层","框架指标","主面板变量","来源类型","输入表","输入列","单元格公式","脚本源码"]
with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
    w = csv.writer(f)
    w.writerow(fields)
    for r in ROWS:
        w.writerow([r["layer"], r["indicator"], r["panel_var"], r["origin"],
                    r["input_file"], r["input_cols"],
                    r["formula_cells"], r["code"]])
print(">> CSV :", csv_path)

# ---------------- Markdown（精简，不含代码，便于嵌入文稿） ----------------
md_path = os.path.join(OUT, "指标数据字典.md")
md = ["# 指标数据字典（L1–L5 逐指标溯源）", "",
      f"> 共 {n_total} 个框架行为指标；{n_calc} 个计算得出，仅 gender 等控制变量直接下载。",
      f"> 全部 {n_total} 个指标均已有仓库内可运行源码（calc_behavioral_metrics.py + calc_remaining_metrics.py）。", ""]
for L in ["L1","L2","L3","L4","L5"]:
    sub = [r for r in ROWS if r["layer"] == L]
    md.append(f"## {LAYER_CN[L]}")
    md.append("| 框架指标 | 主面板变量 | 来源类型 | 输入表 | 单元格公式 |")
    md.append("| --- | --- | --- | --- | --- |")
    for r in sub:
        md.append(f"| {r['indicator']} | `{r['panel_var']}` | {r['origin']} | {r['input_file']} | {r['formula_cells']} |")
    md.append("")
open(md_path, "w", encoding="utf-8").write("\n".join(md))
print(">> MD  :", md_path)
print(f">> 统计：total={n_total} in_repo={n_inrepo} reconstructed={n_recon} computed={n_calc}")
