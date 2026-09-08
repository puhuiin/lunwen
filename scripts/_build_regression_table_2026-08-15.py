# -*- coding: utf-8 -*-
"""#171 生成升级版回归表 HTML：双向聚类 SE(fund×year) + 边界披露。
读取 L3_L1_regression_HONEST_TOWind_2026-08-15.json，输出
回归表_双向聚类_2026-08-15.html。模型为列、变量为行，含 t2w(主)/t1w(对照)。"""
import os, json

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JSON = os.path.join(HERE, "L3_L1_regression_HONEST_TOWind_2026-08-15.json")
OUT = os.path.join(HERE, "回归表_双向聚类_2026-08-15.html")

with open(JSON, encoding="utf-8") as f:
    blob = json.load(f)
H = blob["honest"]

ORDER = ["H1 SDI(真算风格漂移)", "H2 TO_wind(Wind集成换手率)",
         "H2b TO_two_sided(旧双边,稳健性)", "H3 OCI_two_sided(真算)",
         "H4 SDI+TO_wind+OCI(联合)", "H5 SDI+控制(不含TO,大样本)"]
SHORT = {"H1 SDI(真算风格漂移)": "H1\nSDI",
         "H2 TO_wind(Wind集成换手率)": "H2\nTO_wind",
         "H2b TO_two_sided(旧双边,稳健性)": "H2b\nTO_2side",
         "H3 OCI_two_sided(真算)": "H3\nOCI",
         "H4 SDI+TO_wind+OCI(联合)": "H4\n联合",
         "H5 SDI+控制(不含TO,大样本)": "H5\nSDI大样本"}
# 列分组（基金总体）
POP = {"H1 SDI(真算风格漂移)": "366只·SDI样本",
       "H2 TO_wind(Wind集成换手率)": "394只·TO_wind",
       "H2b TO_two_sided(旧双边,稳健性)": "200只·双边子集",
       "H3 OCI_two_sided(真算)": "200只·双边子集",
       "H4 SDI+TO_wind+OCI(联合)": "200只·双边子集",
       "H5 SDI+控制(不含TO,大样本)": "366只·SDI样本"}

# 变量显示顺序（头条行为变量 + 两个主控制）
VAR_ORDER = ["SDI", "TO_wind", "TO_two_sided", "OCI_two_sided", "log_aum", "log_fund_age"]
VAR_LBL = {"SDI": "SDI (风格漂移·真算)", "TO_wind": "TO_wind (Wind单边换手·集成)",
           "TO_two_sided": "TO_two_sided (旧双边·稳健性)", "OCI_two_sided": "OCI_two_sided (真算)",
           "log_aum": "log_aum (规模)", "log_fund_age": "log_fund_age (基金年龄)"}

def cell(spec, var):
    r = next((x for x in H[spec]["rows"] if x["v"] == var), None)
    if r is None:
        return "—"
    b = r["b"]; t2 = r["t"]; t1 = r["t1"]; s = r["s"]
    # beta 格式：行为变量保留5位，控制变量保留4位
    if var in ("SDI", "TO_wind", "TO_two_sided", "OCI_two_sided"):
        bs = f"{b:+.5f}"
    else:
        bs = f"{b:+.4f}"
    return f'<div class="b">{bs}{s}</div><div class="t2">t2w={t2:+.2f}</div><div class="t1">t1w={t1:+.2f}</div>'

# 表头列
cols = "".join(
    f'<th class="model"><div class="ms">{SHORT[k].replace(chr(10),"<br>")}</div>'
    f'<div class="pop">{POP[k]}</div></th>' for k in ORDER)

# 变量行
rows_html = ""
for v in VAR_ORDER:
    cells = "".join(f'<td class="{"hl" if v in ("SDI","TO_wind") else ""}">{cell(k, v)}</td>' for k in ORDER)
    rows_html += f'<tr><td class="vname">{VAR_LBL[v]}</td>{cells}</tr>'

# N / funds 行
n_row = "<tr class='meta'><td class='vname'>观测数 N</td>" + "".join(
    f'<td>{H[k]["N"]:,}</td>' for k in ORDER) + "</tr>"
f_row = "<tr class='meta'><td class='vname'>基金数</td>" + "".join(
    f'<td>{H[k]["funds"]}</td>' for k in ORDER) + "</tr>"

HTML = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>基金经理行为回归表 · 双向聚类升级版</title>
<style>
  :root{{--bg:#fbfcfe;--card:#fff;--ink:#1a2233;--mut:#5b6678;--line:#e3e8f0;
         --accent:#1f5fb0;--hl:#fff7e6;--hlb:#f0a93b;--ok:#1a7a3c;--warn:#b54708;}}
  *{{box-sizing:border-box}}
  body{{margin:0;background:var(--bg);color:var(--ink);
        font-family:-apple-system,"Segoe UI","Microsoft YaHei",sans-serif;line-height:1.55;padding:32px}}
  .wrap{{max-width:1080px;margin:0 auto}}
  h1{{font-size:23px;margin:0 0 4px}}
  .sub{{color:var(--mut);font-size:13.5px;margin:0 0 22px}}
  .card{{background:var(--card);border:1px solid var(--line);border-radius:12px;
         padding:20px 22px;margin:0 0 20px;box-shadow:0 1px 3px rgba(20,40,80,.04)}}
  .card h2{{font-size:15.5px;margin:0 0 10px;color:var(--accent);
            border-left:3px solid var(--accent);padding-left:9px}}
  table{{width:100%;border-collapse:collapse;font-size:13px}}
  th,td{{border:1px solid var(--line);padding:7px 8px;text-align:center;vertical-align:middle}}
  th.model{{background:#eef3fb}}
  .ms{{font-weight:700;font-size:13.5px}}
  .pop{{font-size:11px;color:var(--mut);font-weight:400;margin-top:2px}}
  td.vname{{text-align:left;font-weight:600;background:#f7f9fc;white-space:nowrap}}
  td.hl{{background:var(--hl)}}
  .b{{font-weight:700}}
  .t2{{font-size:11.5px;color:var(--ink)}}
  .t1{{font-size:10.5px;color:var(--mut)}}
  tr.meta td{{background:#f3f6fa;font-weight:600}}
  .callout{{border:1px solid #cfe3f5;background:#f1f7fd;border-radius:10px;padding:14px 16px;margin:0 0 18px}}
  .callout b{{color:var(--accent)}}
  .disc{{border-left:4px solid var(--hlb);background:#fffaf0;
         border-radius:0 10px 10px 0;padding:14px 18px}}
  .disc h2{{border:none;padding:0;color:var(--warn)}}
  .disc ul{{margin:8px 0 0;padding-left:20px}}
  .disc li{{margin:6px 0;font-size:13px}}
  .tag{{display:inline-block;background:var(--accent);color:#fff;font-size:11px;
        border-radius:5px;padding:1px 7px;margin-right:6px;vertical-align:middle}}
  .foot{{color:var(--mut);font-size:12px;margin-top:8px}}
  code{{background:#eef1f6;padding:1px 5px;border-radius:4px;font-size:12px}}
</style></head>
<body><div class="wrap">

<h1>基金经理行为回归表 · 双向聚类升级版</h1>
<p class="sub">DV = <code>quarter_return</code>（基金季度收益，同期） · 方法学：双向 demeaning(fund+year) + 双向聚类稳健 SE(fund×year, Cameron–Gelbach–Miller 2011)
 · 全样本 9,974 观测 / 400 只 · 连续变量 1%/99% winsorize · 2026-08-15</p>

<div class="callout">
<b>核心诚实结论（at-a-glance）：</b><br>
• <b>SDI（H1）</b> β=+0.103，<b>t2w=+2.46**</b>（5% 显著，仍为正）；对照单维基金聚类 t1w=+12.41***。
  年份共同冲击被 year 聚类吸收后显著性由 1% 收敛至 5%（Petersen 2009 规范做法）。<br>
• <b>TO_wind（H2）</b> β=+0.00003，t2w=+1.78（p=0.075，10% 边际）；换手率与收益关联弱。<br>
• <b>H4 联合</b> SDI β=+0.020，<b>t2w=+3.09***</b>——但在受限 200 基金子集，样本总体与 H1 不同。
</div>

<div class="card">
<h2>回归结果（模型为列 · 变量为行）</h2>
<table>
<thead><tr><th class="vname">变量</th>{cols}</tr></thead>
<tbody>
{rows_html}
{n_row}
{f_row}
</tbody>
</table>
<p class="foot">单元格：<span class="b">β（显著性）</span> / <span class="t2">t2w=双向聚类 t</span> / <span class="t1">t1w=单维基金聚类 t（对照）</span>。
显著性：* p&lt;0.10，** p&lt;0.05，*** p&lt;0.01。其余控制变量（mgr_total_tenure_v2 / gender_m / cfa_d / edu_postgrad）已纳入各模型但未列示，详见 JSON。
<b>颜色高亮</b>：SDI、TO_wind 为头条行为变量。</p>
</div>

<div class="disc">
<h2>⚠ 边界与披露（Boundary A 及方法学）</h2>
<ul>
<li><span class="tag">窗口</span><b>SDI 有效识别窗口 = 2022+。</b> SDI 采用 window=8 滚动 OLS，首个有效 SDI 约 2022Q2；
   实证有效样本期为 2022Q2–2026Q2。更早季度 SDI 因暖机不足为空，不可外推至 2022 年前。</li>
<li><span class="tag">对齐</span><b>SDI(t) 与 quarter_return(t) 同期同位置对齐、无前视偏差。</b>
   经独立复算核验（与 lib_metrics 输出 diff=0）：SDI(t) 完全由截至 <code>t−1</code> 季度的收益估计，
   未使用 t 季或未来任何收益；在面板中按 <code>report_date</code> 与 quarter_return(t) 对齐。
   故 H1/H2 应表述为「同期关联」而非「预测」。</li>
<li><span class="tag">总体</span><b>H1/H5（366 只）与 H4（200 只）是不同基金总体。</b>
   H4 因纳入 OCI_two_sided（仅 18% 覆盖）被限制在 200 只双边换手子集，其 SDI 系数（β=+0.020）
   与 H1（β=+0.103）不可直接比较——样本选择不同，非同一总体。</li>
<li><span class="tag">覆盖</span><b>换手率覆盖差异：</b>TO_wind 86.6%（394 只，半年度，单边口径）；
   TO_two_sided / OCI_two_sided 仅 18%（200 只，半年度）。低覆盖变量构成 H2b/H3/H4 的样本约束。</li>
<li><span class="tag">SE</span><b>双向聚类已交叉验证。</b>自实现 CGM(fund×year) 与 linearmodels 双向 FE+双向聚类
   的 β 完全一致（0.09911）、t 仅差 ~3%（小样本校正差异），实现正确。t1w 列保留供对照。</li>
<li><span class="tag">异常</span><b>H4 受限样本个别控制 SE 不稳定：</b>如 gender_m 在 H4 中 t=14.4（H1/H5 仅 0.75），
   系 200 基金/1,192 观测下少簇导致，不影响 SDI 头条结论（t=3.09***）。H4 以 SDI 为准。</li>
</ul>
</div>

<div class="foot">生成：_build_regression_table_2026-08-15.py（读 L3_L1_regression_HONEST_TOWind_2026-08-15.json）。
可复现：重跑 L3_L1_regressions_HONEST_2026-08-14.py 即重建 JSON 与本表。</div>

</div></body></html>"""

with open(OUT, "w", encoding="utf-8") as f:
    f.write(HTML)
print("写出", OUT, "大小", len(HTML), "字符")
print("H1 SDI t2w=%.2f t1w=%.2f | H2 TO_wind t2w=%.2f | H4 SDI t2w=%.2f"
      % (H[ORDER[0]]["rows"][0]["t"], H[ORDER[0]]["rows"][0]["t1"],
         H[ORDER[1]]["rows"][0]["t"], H[ORDER[4]]["rows"][0]["t"]))
