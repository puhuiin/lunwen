# -*- coding: utf-8 -*-
"""生成英文版《Evidence Statement Table》独立 HTML 工件（国际投稿配套）。
数值同源 _v4_benchmark.json，与 §6.1.7 及中文证据声明表逐字段一致。
输出 Evidence_Statement_Table_2026-08-16.html。"""
import os, json

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
B = json.load(open(os.path.join(HERE, "_v4_benchmark.json"), encoding="utf-8"))
C = B["coefs"]

# (var, layer, name_en, hypothesis, grade, validity_note_en)
ROWS = [
    ("log_fund_age",       "L1", "Fund age (log)",            "—",   "A",
     "Stable control; robust across full sample; no external-validity restriction"),
    ("mgr_total_tenure_v2","L1", "Manager cumulative tenure", "—",   "C",
     "Insignificant in M4; tenure length shows no stable cross-sectional association with performance"),
    ("AS_improved",        "L2", "Active Share (AS)",         "—",   "A",
     "Higher active share associated with lower alpha; robust; structural control"),
    ("ICI",                "L2", "Industry Concentration (ICI)","—", "A",
     "Industry concentration yields excess return; robust; net effect depends on stock-selection skill"),
    ("industry_hhi",       "L2", "Industry HHI",              "—",   "C",
     "Insignificant in M4; HHI dimension of concentration carries no independent information"),
    ("SDI",                "L3", "Style Drift (SDI)",         "H1",  "C",
     "Absorbed (insignificant) under full M4 controls (by L2/L4); H1 holds under sparse specification but effective window is 2022+ (§4.2)"),
    ("TO_wind",            "L3", "Turnover (TO_wind)",        "H2",  "C",
     "Insignificant under full M4 controls; sparse-spec t=+1.78*; weak cost-erosion effect, overturned by mediation test (§4.2)"),
    ("ARG",                "L3", "Active Return Gap (ARG)",   "—",   "A",
     "Active risk-adjusted return positively associated with performance; robust; execution-consistency dimension"),
    ("return_volatility",  "L3", "Return volatility",         "—",   "C",
     "Insignificant in M4; significant as a mediation channel (§6.1.5) but no independent information as direct predictor"),
    ("de",                 "L5", "Disposition Effect (DE)",   "H3*", "A",
     "Two-way clustered *** + WCB ** + permutation * all aligned; within-fund FE t=-3.64 strong. Validity boundary: estimate sample is a selection-biased subsample (de_avail -> alpha +0.0048, t=2.18**); external validity limited to ~46.6% of funds with full-holding data (§4.4.9)"),
    ("lsv",                "L5", "Herd Behavior (LSV)",       "—",   "C",
     "Insignificant in M4; fragility diagnosed: not collinear (VIF=1.15), not data artifact; mechanism = masked by same-layer de/RA (J-isolation -> +0.027, t=2.78***), period-dependent (2022+ +0.025, t=2.03**). Descriptive/selection-sensitive evidence only (§4.4.8)"),
    ("risk_asym",          "L5", "Risk-taking Asymmetry (RiskAsym)","—","A",
     "Two-way clustered *** + WCB *** + permutation * all aligned; construct orthogonalized to market timing (§4.4.5). Multiple mechanisms (house-money/timing/skill); inverse-U only marginal; strongest single-indicator evidence"),
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
<html lang="en"><head><meta charset="utf-8">
<title>Evidence Statement Table</title>
<style>
* {{ box-sizing: border-box; }}
body {{ font-family: -apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif; color:#1a1a1a; margin:32px auto; max-width:1150px; line-height:1.5; }}
h1 {{ font-size:22px; border-bottom:3px solid #2563eb; padding-bottom:8px; }}
h2 {{ font-size:15px; margin-top:26px; color:#2563eb; }}
.meta {{ font-size:12.5px; color:#555; background:#f5f7fb; border-left:4px solid #2563eb; padding:10px 14px; margin:14px 0; }}
table {{ border-collapse:collapse; width:100%; font-size:12px; margin:12px 0; }}
th,td {{ border:1px solid #cbd5e1; padding:7px 9px; vertical-align:top; text-align:left; }}
th {{ background:#eef2f9; font-weight:700; }}
td.num {{ text-align:right; font-variant-numeric:tabular-nums; white-space:nowrap; }}
td.grade {{ text-align:center; font-weight:800; border:2px solid; border-radius:4px; }}
td.note {{ font-size:11px; color:#444; }}
.legend {{ display:flex; gap:18px; font-size:13px; margin:10px 0; flex-wrap:wrap; }}
.legend span {{ padding:4px 12px; border-radius:5px; font-weight:700; }}
.legend .A {{ background:#e6f4ea; color:#1e7a34; }}
.legend .B {{ background:#fff4e5; color:#b26a00; }}
.legend .C {{ background:#fdecea; color:#b3261e; }}
.foot {{ font-size:11px; color:#666; margin-top:18px; border-top:1px solid #e2e8f0; padding-top:10px; }}
@media print {{ body {{ margin:14mm; }} h1 {{ color:#000; }} }}
</style></head>
<body>
<h1>Evidence Statement Table</h1>
<div class="meta">
<b>Source</b>: v4 authoritative benchmark (main model M4) &mdash; panel mixed OLS, dependent variable
<i>ff5_adj_return</i>; 18 right-hand-side regressors (including the FF5 five factors) + C(year);
fund&times;year two-way clustered standard errors (CGM 2011); all continuous variables winsorized at 1%/99%.
Sample N = {B['n_obs']:,} fund-quarter observations / {B['n_fund']} funds, R&sup2; = {B['r2']:.4f}.
Coefficients, t, p, and WCB / permutation p are programmatically extracted from
<code>_v4_benchmark.json</code>, sharing the same source as manuscript &sect;6.1.7 and verified field-by-field by a consistency audit.
</div>

<h2>Evidence-grading rules</h2>
<div class="legend">
  <span class="A">A &middot; Strong</span>
  <span class="B">B &middot; Conditional</span>
  <span class="C">C &middot; Weak / Unstable</span>
</div>
<p style="font-size:12.5px"><b>A (Strong)</b>: M4 two-way clustered at least ** and consistent significance across &ge;2 of
asymptotic / WCB / permutation inference; no overturning item in the robustness chapter.
<b>B (Conditional)</b>: significant in some specification or subsample, directionally stable but magnitude / significance limited.
<b>C (Weak / Unstable)</b>: M4 insignificant (n.s.) or direction highly sensitive to sample selection; descriptive support only.
(No indicator falls into B in this study.)</p>

<h2>Evidence statement &mdash; full table (L1&ndash;L5 framework)</h2>
<table>
<thead><tr><th>Layer</th><th>Indicator</th><th>Hyp.</th><th>M4 coef.<br>(2-way clust.)</th><th>t</th><th>p</th>
<th>WCB p</th><th>Perm. p</th><th>Grade</th><th>Validity boundary &amp; robustness index</th></tr></thead>
<tbody>
{rows_html}
</tbody></table>

<div class="meta" style="border-color:#1e7a34">
<b>Grade tally</b>: A = {nA} ({{ {', '.join(r[2] for r in ROWS if r[4]=='A')} }});
C = {nC} ({{ {', '.join(r[2] for r in ROWS if r[4]=='C')} }}); B = {nB}.
<strong>Strongest evidence</strong>: RiskAsym (A, significant in forward + within-fund dimensions), DE (A, within-fund quasi-causal but external validity limited to ~46.6% subsample),
and structural controls AS / ICI / ARG.
<strong>Weakest evidence</strong>: LSV (C, direction sample-sensitive, masked by same-layer indicators; descriptive only).
</div>

<div class="foot">
<p>WCB p = Wild Cluster Bootstrap-S small-sample inference p-value; Perm. p = 500-draw permutation-test p-value.
* H3* marks DE as an L5 behavioral indicator whose disposition-effect construct corresponds to the prospect-theory loss-aversion hypothesis.</p>
<p>Diagnostic index: LSV fragility mechanism &sect;4.4.8; DE selection bias &amp; validity boundary &sect;4.4.9;
full-RHS multicollinearity (VIF) diagnostic &sect;4.4.10 (all headline coefficients VIF &lt; 2).
Full grading and citations in manuscript &sect;6.1.7. This table is a stand-alone submission companion and may be submitted separately or as an online appendix.</p>
<p>Generated 2026-08-16 &middot; programmatically built from the v4 authoritative benchmark by <code>_build_evidence_statement_table_en.py</code>.</p>
</div>
</body></html>"""

out = os.path.join(HERE, "Evidence_Statement_Table_2026-08-16.html")
with open(out, "w", encoding="utf-8") as f:
    f.write(html)
print(f"Generated {out}")
print(f"Grade tally: A={nA} B={nB} C={nC}; rows={len(ROWS)}")
