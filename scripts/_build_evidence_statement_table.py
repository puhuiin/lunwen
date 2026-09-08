# -*- coding: utf-8 -*-
"""生成投稿版《实证结论证据声明表》(Evidence Statement Table) 独立 HTML 工件。
所有系数/t/p 取自 v4 权威基准 _v4_benchmark.json（与 §6.1.7 同源，已通过一致性审计），
A/B/C 分级与效度边界为人工裁定。输出 实证结论_证据声明表_2026-08-16.html。"""
import os, json

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
B = json.load(open(os.path.join(HERE, "_v4_benchmark.json"), encoding="utf-8"))
C = B["coefs"]

ROWS = [
    ("log_fund_age",      "L1", "基金年龄对数",        "—",   "A", "稳定控制变量，全样本稳健；无外推限制"),
    ("mgr_total_tenure_v2","L1","经理累计任期",        "—",   "C", "M4 不显著，任期长度与业绩无稳定截面关联"),
    ("AS_improved",       "L2", "主动持股比 (AS)",     "—",   "A", "高主动份额伴随更低 alpha，稳健；属结构性控制"),
    ("ICI",               "L2", "行业集中度 (ICI)",    "—",   "A", "行业集中带来超额收益，稳健；净效应取决于选股能力"),
    ("industry_hhi",      "L2", "行业 HHI",            "—",   "C", "M4 不显著，行业集中度-HHI 维度无独立信息"),
    ("SDI",               "L3", "风格漂移 (SDI)",      "H1",  "C", "M4 全控制下不显著（被 L2/L4 吸收）；稀疏设定下 H1 成立，但有效窗口 2022+（§4.2）"),
    ("TO_wind",           "L3", "换手率 (TO_wind)",    "H2",  "C", "M4 全控制下不显著；稀疏设定 t=+1.78*，成本侵蚀效应弱且被中介检验推翻（§4.2）"),
    ("ARG",               "L3", "调仓收益缺口 (ARG)",  "—",   "A", "主动风险调整正向关联业绩，稳健；属执行一致性维度"),
    ("return_volatility", "L3", "收益波动率",          "—",   "C", "M4 不显著；其作为中介渠道显著（§6.1.5），但作为直接预测因子无独立信息"),
    ("de",                "L5", "处置效应 (DE)",       "H3*", "A", "双向聚类*** + WCB** + 置换* 一致；组内FE t=-3.64 强。效度边界：估计样本为选择偏倚子群（de_avail→alpha +0.0048,t2.18**），结论外推限于~46.6%有全持仓数据子群（§4.4.9）"),
    ("lsv",               "L5", "羊群效应 (LSV)",      "—",   "C", "M4 不显著；脆弱性已诊断：非共线(VIF=1.15)、非数据假象，机制=被同层 de/RA 掩盖（J 隔离→+0.027,t2.78***）、时期依存（2022+ +0.025,t2.03**）。作描述性/选择敏感证据（§4.4.8）"),
    ("risk_asym",         "L5", "风险不对称 (RiskAsym)","—",  "A", "双向聚类*** + WCB*** + 置换* 一致；构念已对择时正交化（§4.4.5）。机制多元（赌资/择时/技能），非线性倒U仅边际；最强单指标证据"),
]

def fmt_p(p):
    if p is None: return "—"
    if p < 0.001: return "&lt;0.001 ***"
    if p < 0.01:  return f"{p:.3f} ***"
    if p < 0.05:  return f"{p:.3f} **"
    if p < 0.10:  return f"{p:.3f} *"
    return f"{p:.3f} n.s."

GRADE_COLOR = {"A": "#1e7a34", "B": "#b26a00", "C": "#b3261e"}

def row_html(r):
    var, layer, name, hyp, grade, note = r
    c = C[var]
    beta = f"{c['beta']:+.5f}"
    t = f"{c['t2w']:+.2f}"
    p = fmt_p(c['p2w'])
    wcb = fmt_p(c.get('wcb_p'))
    perm = fmt_p(c.get('perm_p'))
    gc = GRADE_COLOR[grade]
    return (f"<tr><td>{layer}</td><td>{name}</td><td>{hyp}</td>"
            f"<td class='num'>{beta}</td><td class='num'>{t}</td><td class='num'>{p}</td>"
            f"<td class='num'>{wcb}</td><td class='num'>{perm}</td>"
            f"<td class='grade' style='color:{gc};border-color:{gc}'>{grade}</td>"
            f"<td class='note'>{note}</td></tr>")

rows_html = "\n".join(row_html(r) for r in ROWS)
nA = sum(1 for r in ROWS if r[4] == "A")
nB = sum(1 for r in ROWS if r[4] == "B")
nC = sum(1 for r in ROWS if r[4] == "C")

html = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<title>实证结论证据声明表 (Evidence Statement Table)</title>
<style>
* {{ box-sizing: border-box; }}
body {{ font-family: -apple-system,"Segoe UI","Microsoft YaHei",sans-serif; color:#1a1a1a; margin:32px auto; max-width:1100px; line-height:1.55; }}
h1 {{ font-size:22px; border-bottom:3px solid #2563eb; padding-bottom:8px; }}
h2 {{ font-size:15px; margin-top:26px; color:#2563eb; }}
.meta {{ font-size:12.5px; color:#555; background:#f5f7fb; border-left:4px solid #2563eb; padding:10px 14px; margin:14px 0; }}
table {{ border-collapse:collapse; width:100%; font-size:12.5px; margin:12px 0; }}
th,td {{ border:1px solid #cbd5e1; padding:7px 9px; vertical-align:top; text-align:left; }}
th {{ background:#eef2f9; font-weight:700; }}
td.num {{ text-align:right; font-variant-numeric:tabular-nums; white-space:nowrap; }}
td.grade {{ text-align:center; font-weight:800; border:2px solid; border-radius:4px; }}
td.note {{ font-size:11.5px; color:#444; }}
.legend {{ display:flex; gap:18px; font-size:13px; margin:10px 0; flex-wrap:wrap; }}
.legend span {{ padding:4px 12px; border-radius:5px; font-weight:700; }}
.legend .A {{ background:#e6f4ea; color:#1e7a34; }}
.legend .B {{ background:#fff4e5; color:#b26a00; }}
.legend .C {{ background:#fdecea; color:#b3261e; }}
.foot {{ font-size:11.5px; color:#666; margin-top:18px; border-top:1px solid #e2e8f0; padding-top:10px; }}
@media print {{ body {{ margin:14mm; }} h1 {{ color:#000; }} }}
</style></head>
<body>
<h1>实证结论证据声明表 (Evidence Statement Table)</h1>
<div class="meta">
<b>数据来源</b>：v4 权威基准（主模型 M4）— 面板混合 OLS，因变量 ff5_adj_return，右侧 18 个 RHS（含 FF5 五因子）+
C(year)；基金×年份双向聚类标准误（CGM 2011）；全部连续变量 1%/99% 缩尾。
样本 N = {B['n_obs']:,} 观测 / {B['n_fund']} 只基金，R² = {B['r2']:.4f}。
系数、t、p 与 WCB/置换 p 均由 <code>_v4_benchmark.json</code> 程序化提取，与稿件 §6.1.7 同源且经一致性审计逐字段核对。
</div>

<h2>证据分级规则</h2>
<div class="legend">
  <span class="A">A 级 · 强证据</span>
  <span class="B">B 级 · 条件证据</span>
  <span class="C">C 级 · 弱 / 不稳证据</span>
</div>
<p style="font-size:12.5px"><b>A 级</b>：M4 双向聚类至少 ** 且渐近 / WCB / 置换至少两种口径一致显著，稳健性章无推翻项。
<b>B 级</b>：部分口径或子样本显著、方向稳健但量级 / 显著性受限。
<b>C 级</b>：M4 不显著（n.s.）或方向对样本选择高度敏感，作描述性佐证。
（本案暂无任何指标落入 B 级。）</p>

<h2>证据声明总表（L1–L5 五层框架）</h2>
<table>
<thead><tr><th>层</th><th>指标</th><th>假设</th><th>M4 系数<br>(双向聚类)</th><th>t</th><th>p</th>
<th>WCB p</th><th>置换 p</th><th>分级</th><th>效度边界与稳健性索引</th></tr></thead>
<tbody>
{rows_html}
</tbody></table>

<div class="meta" style="border-color:#1e7a34">
<b>分级统计</b>：A 级 {nA} 项（{', '.join(r[2] for r in ROWS if r[4]=='A')}）；
C 级 {nC} 项（{', '.join(r[2] for r in ROWS if r[4]=='C')}）；
B 级 {nB} 项。
<strong>最强证据</strong>：RiskAsym（A，前向+组内多口径显著）、DE（A，组内准因果但外推限于 ~46.6% 子群）、
以及结构性控制 AS / ICI / ARG。
<strong>最弱证据</strong>：LSV（C，方向样本敏感、被同层掩盖，作描述性）。
</div>

<div class="foot">
<p>WCB p = Wild Cluster Bootstrap-S 小样本推断 p 值；置换 p = 500 次置换检验 p 值。
* H3* 表示 DE 属 L5 行为指标层，其处置效应构念对应前景理论损失规避假设。</p>
<p>诊断索引：LSV 脆弱性机制见 §4.4.8；DE 选择性缺失与效度边界见 §4.4.9；
全 RHS 多重共线性（VIF）诊断见 §4.4.10（headline 系数 VIF 均 &lt; 2）。
完整证据分级与引用见稿件 §6.1.7。本表为投稿配套的独立声明文件，可单独提交或作为在线附录。</p>
<p>生成时间：2026-08-16 · 由 <code>_build_evidence_statement_table.py</code> 自 v4 权威基准程序化生成。</p>
</div>
</body></html>"""

out = os.path.join(HERE, "实证结论_证据声明表_2026-08-16.html")
with open(out, "w", encoding="utf-8") as f:
    f.write(html)
print(f"已生成 {out}")
print(f"分级统计：A={nA} B={nB} C={nC}")
print("行数：", len(ROWS))
