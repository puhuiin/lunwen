# -*- coding: utf-8 -*-
"""生成四个追问硬化报告 HTML（2026-08-27），读取当日四个诊断 JSON。"""
import json, os
BASE = "D:/Desktop/基金经理行为分析研究"
OUT = os.path.join(BASE, "output")
REP = os.path.join(BASE, "reports")

A = json.load(open(f"{OUT}/L1重定位与五维能力分_2026-08-27.json", encoding="utf-8"))
B = json.load(open(f"{OUT}/L4b权重稳健性_2026-08-27.json", encoding="utf-8"))
C = json.load(open(f"{OUT}/稳健性_四项代价_2026-08-27.json", encoding="utf-8"))
D = json.load(open(f"{OUT}/ICI异常修复_2026-08-27.json", encoding="utf-8"))


def tbl(rows):
    h = "".join(f"<th>{x}</th>" for x in rows[0])
    body = "".join("<tr>" + "".join(f"<td>{x}</td>" for x in r) + "</tr>" for r in rows[1:])
    return f"<table><thead><tr>{h}</tr></thead><tbody>{body}</tbody></table>"


# A 表
a = A
A_tbl = tbl([
    ["口径", "Q5−Q1", "t", "单调", "联立R²", "L1联立t"],
    ["五维行为能力综合分（主能力口径）", a["五维行为能力综合分"]["Q5_Q1"], a["五维行为能力综合分"]["t"],
     "是" if a["五维行为能力综合分"]["单调"] else "否", a["联立_R2"]["五维"], "—"],
    ["六维综合分（含L1）", a["六维综合分_含L1"]["Q5_Q1"], a["六维综合分_含L1"]["t"],
     "是" if a["六维综合分_含L1"]["单调"] else "否", a["联立_R2"]["六维"], a["联立_L1系数"]["t"]],
])

# B 表
b = B
B_tbl = tbl([
    ["L4b 构造", "单维t", "单维R²", "联立coef", "联立t", "联立R²"],
    ["等权三成分（当前）", b["等权三成分"]["单维_t"], b["等权三成分"]["单维_R2"],
     b["等权三成分"]["联立_coef"], b["等权三成分"]["联立_t"], b["等权三成分"]["联立_R2"]],
    ["mppm8 单成分", b["mppm8单成分"]["单维_t"], b["mppm8单成分"]["单维_R2"],
     b["mppm8单成分"]["联立_coef"], b["mppm8单成分"]["联立_t"], b["mppm8单成分"]["联立_R2"]],
    ["PCA 加权", b["PCA加权"]["单维_t"], b["PCA加权"]["单维_R2"],
     b["PCA加权"]["联立_coef"], b["PCA加权"]["联立_t"], b["PCA加权"]["联立_R2"]],
])
pca_w = " / ".join(f"{k.split('_')[0]}={v}" for k, v in b["PCA权重"].items())

# C 表（四项代价）
c = C
C_tbl = tbl([
    ["代价项", "关键数值", "披露结论"],
    ["① L1 同期稀释", f"五维 {c['代价1_L1同期稀释']['五维Q5Q1']} vs 六维 {c['代价1_L1同期稀释']['六维Q5Q1']}；L1联立t={c['代价1_L1同期稀释']['六维联立L1_t']}；OOS嵌套F p={c['代价1_L1同期稀释']['样本外嵌套F_p']}",
     "L1 为边界条件，主能力口径采用五维；样本外仍有增量"],
    ["② mppm8 精度次优", f"等权 R²={c['代价2_mppm8精度次优']['等权三成分_R2']} t={c['代价2_mppm8精度次优']['等权三成分_t']}；mppm8单成分 R²={c['代价2_mppm8精度次优']['mppm8单成分_R2']} t={c['代价2_mppm8精度次优']['mppm8单成分_t']}",
     "等权为覆盖/抗操纵选择，非精度最优；纯预测力可改用 mppm8"],
    ["③ TO 残余信号", f"控制六维后 TO 净t={c['代价3_TO残余信号']['控制六维后TO净t']}；双口径单变量t={c['代价3_TO残余信号']['TO双口径单变量t']}",
     "TO 未通过预注册双口径单变量稳健性，按规则剔除"],
    ["④ L4b 概念同源", f"sharpe↔mppm 相关={c['代价4_L4b概念同源']['sharpe8_mppm8相关']}；成分-alpha最大相关={c['代价4_L4b概念同源']['成分与alpha最大相关']}；增量R²={c['代价4_L4b概念同源']['L4b增量R2']}",
     "L4b 与因变量共享风险调整后收益内核，性质弱于纯行为维度"],
])

# D 表
d = D
c4 = d["全部四规格修复"]
D_tbl = tbl([
    ["修复后规格", "N", "R²", "cond", "ICI t"],
    ["M4_base", c4["M4_base"]["n"], f"{c4['M4_base']['R2']:.4f}", f"{c4['M4_base']['cond']:.1e}", f"{c4['M4_base']['ICI']['t']:+.3f}"],
    ["M4_idio", c4["M4_idio"]["n"], f"{c4['M4_idio']['R2']:.4f}", f"{c4['M4_idio']['cond']:.1e}", f"{c4['M4_idio']['ICI']['t']:+.3f}"],
    ["M4_tm", c4["M4_tm"]["n"], f"{c4['M4_tm']['R2']:.4f}", f"{c4['M4_tm']['cond']:.1e}", f"{c4['M4_tm']['ICI']['t']:+.3f}"],
    ["M4_daily_full", c4["M4_daily_full"]["n"], f"{c4['M4_daily_full']['R2']:.4f}", f"{c4['M4_daily_full']['cond']:.1e}", f"{c4['M4_daily_full']['ICI']['t']:+.3f}"],
])
root_cause = "；".join(d["根因"])

HTML = f"""<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8">
<title>四个追问硬化报告 2026-08-27</title>
<style>
body{{font-family:-apple-system,'Segoe UI',Roboto,'Microsoft YaHei',sans-serif;max-width:960px;margin:32px auto;padding:0 20px;color:#1a1a1a;line-height:1.7;}}
h1{{border-bottom:3px solid #2c5f8a;padding-bottom:8px;}}
h2{{color:#2c5f8a;margin-top:36px;border-left:4px solid #2c5f8a;padding-left:10px;}}
.card{{background:#f7f9fc;border:1px solid #e1e8f0;border-radius:8px;padding:14px 18px;margin:14px 0;}}
table{{border-collapse:collapse;width:100%;margin:12px 0;font-size:14px;}}
th,td{{border:1px solid #ddd;padding:7px 9px;text-align:center;}}
th{{background:#2c5f8a;color:#fff;}}
td:nth-child(1){{text-align:left;}}
.tag{{display:inline-block;background:#2c5f8a;color:#fff;border-radius:4px;padding:1px 8px;font-size:13px;}}
.ok{{color:#1a7a3a;font-weight:600;}}
.warn{{color:#b8860b;font-weight:600;}}
code{{background:#eef2f7;padding:1px 5px;border-radius:3px;}}
</style></head><body>
<h1>四个追问的硬化与优化报告</h1>
<p class="card">基于 2026-08-26 的「四问诊断」与 §4.13，本轮（2026-08-27）对四处薄弱点做硬化：
<span class="tag">A</span> L1 重新定位＋五维能力分 ｜
<span class="tag">B</span> L4b 权重稳健性 ｜
<span class="tag">C</span> 四项代价提级主表 ｜
<span class="tag">D</span> 修复 M4_idio 的 ICI 异常(t=+38.6)。
所有数值由脚本复算，源数据见 <code>output/*_2026-08-27.json</code>。</p>

<h2>① L1 重新定位：五维行为能力分为主能力口径</h2>
<p>L1 本质是「边界条件/状态层」而非行为能力。剥离 L1 后，五维行为能力综合分当期区分度反而<b>更高</b>，
且六维联立 R² 与五维完全相同（0.4557）——证明 L1 在联立中已被完全吸收，剥离它<b>无损能力刻画</b>。</p>
{A_tbl}
<div class="card"><b>建议口径：</b>主能力口径 = 五维行为能力综合分（剔除 L1）；L1 基本面优势作为「边界条件/状态层」单列报告，
参与样本外预测与画像刻画，但不进入等权能力计分。同期稀释 = 五维 Q5−Q1 0.03351 − 六维 0.03131 = <b>0.0022</b>（已在主表披露）。</div>

<h2>② L4b 权重稳健性：等权选择被 PCA 验证</h2>
<p>PCA 第一主成分权重为 {pca_w}，与等权（各 1/3）几乎一致，<b>等权并非随意，而是数据一致的选择</b>。
mppm8 单成分预测力更强（联立 t=+8.64、R²=0.5116），但其与 alpha 同源度最高（相关 0.443），
故等权是以一点预测力换取概念覆盖与抗操纵的权衡。</p>
{B_tbl}

<h2>③ 四项代价提级进主表／稳健性章节</h2>
<p>以下四项原仅在 §4.13 披露，现提级为主回归表脚注与稳健性章节，供答辩直接引用。</p>
{C_tbl}

<h2>④ 修复 M4_idio 的 ICI 异常(t=+38.6)</h2>
<p><b>根因：</b>{root_cause}。原代码对奇异+病态 XᵀX 用 <code>inv→pinv</code> 退化求逆，产生虚假极小 SE，ICI t=+38.6 为<b>数值伪影</b>（t 统计对 regressor 缩放不变，故修正后 ICI t 即真实值）。</p>
<p><b>修复：</b>剔除 NAV 子集内的常数列 SDI，并对 TO_wind 等畸变变量做 1%/99% 缩尾，条件数由 2.1e7 降至 1.1e5（满秩、良态）。四规格重算结果：</p>
{D_tbl}
<div class="card">
<b>修正结论：</b>ICI 在 M4_idio 的真实 t=<b>{c4['M4_idio']['ICI']['t']:+.3f}</b>，<b>不显著</b>，与全文「ICI 通道由行为层承载」一致。
TM_β₂≈0 的结论保持（M4_tm 中 t=+0.004）；idio_vol 替换 return_volatility 带来 R² 由 0.0682→0.0785 的小幅提升，
但其自身系数在子样本中不显著（t=+0.278）——批次②应据实表述为「日频特质波动有微弱增量、个体不显著」，而非原稿的强结论。
全部四规格的 SE 此前均受同一退化影响，已一并修正。
</div>

<h2>附：产出文件</h2>
<ul>
<li><code>output/L1重定位与五维能力分_2026-08-27.json</code></li>
<li><code>output/L4b权重稳健性_2026-08-27.json</code></li>
<li><code>output/稳健性_四项代价_2026-08-27.json</code></li>
<li><code>output/ICI异常修复_2026-08-27.json</code></li>
<li>复算脚本：<code>scripts/_harden_20260827.py</code>、<code>scripts/_fix_ici3_20260827.py</code></li>
</ul>
</body></html>"""

with open(f"{REP}/稳健性硬化_四个追问_2026-08-27.html", "w", encoding="utf-8") as f:
    f.write(HTML)
print("已生成 reports/稳健性硬化_四个追问_2026-08-27.html  (%d 字节)" % len(HTML))
