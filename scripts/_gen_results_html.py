# -*- coding: utf-8 -*-
"""生成《回归结果展示与解读说明》独立 HTML。
数据源：v4 双向聚类基准（merged_manuscript / 回归表_双向聚类_v4基准_2026-08-16.html /
实证结论_证据强度总览_2026-08-16.html / M4_FamaMacBeth复核_2026-08-16.md）。
所有数字为权威口径，禁止编造；缺失口径标注"未提供"。
"""
import datetime

# ---------- 权威数据（v4 双向聚类 CGM2011，N=2264/348，R²=0.1290） ----------
# (层, 变量, beta, t_two_way, sig, WCB_p, perm_p, FM_sparse_t, grade, 方向说明)
ROWS = [
    ("L1", "基金年龄对数",      -0.00417, -2.53, "**",  None,   None,   None, "A", "越老越弱"),
    ("L1", "经理累计任期",       0.00000,  1.02, "",    None,   None,   None, "C", "无关联"),
    ("L2", "主动持股比 AS",     -0.02982, -2.81, "***", None,   None,   None, "A", "拖累"),
    ("L2", "行业集中度 ICI",     0.01804,  3.74, "***", None,   None,   None, "A", "提升"),
    ("L2", "行业 HHI",           0.00865,  0.19, "",    None,   None,   None, "C", "无信息"),
    ("L3", "风格漂移 SDI",      -0.00000, -0.00, "",    None,   None,   None, "C", "被吸收"),
    ("L3", "换手率 TO_wind",     0.00000,  1.07, "",    None,   None,   None, "C", "弱"),
    ("L3", "调仓收益缺口 ARG",   0.01625,  2.98, "***", None,   None,   None, "A", "提升"),
    ("L4", "收益波动率",         0.02379,  0.81, "",    None,   None,   None, "C", "仅中介"),
    ("L5", "处置效应 DE",       -0.00606, -2.99, "***", 0.014,  0.047, -1.57, "A", "拖累(外推限46.6%)"),
    ("L5", "羊群效应 LSV",       0.01548,  0.77, "",    0.229,  0.507,  0.27, "C", "设定依赖"),
    ("L5", "风险不对称 RA",      0.07311,  3.57, "***", 0.000,  0.020,  2.18, "A", "提升(最强)"),
]

# 增量 R²
DR2_FULL = 0.0352   # 全样本口径
DR2_SUB  = 0.0224   # 同样本口径

# ---------- 颜色约定（与画像文档一致：结论导向） ----------
# 红 = β>0 提升业绩；绿 = β<0 拖累业绩；灰 = 不显著(方向仍标，但降透明度)
RED   = "#cf1322"   # β>0
GREEN = "#08976b"   # β<0
GRAY  = "#9aa0a6"   # 不显著
def color_of(beta, sig):
    base = RED if beta > 0 else GREEN
    return base if sig else GRAY

# ===================== 森林图 SVG =====================
FW, FH = 920, 470
LEFT = 230          # 标签区
PLOT_L, PLOT_R = LEFT, 860
CTRL = (PLOT_L + PLOT_R) / 2.0      # t=0
T_MAX = 4.2
SCALE = (PLOT_R - PLOT_L) / (2 * T_MAX)
def CTRL_Z(t): return CTRL + t * SCALE

row_h = 33
y0 = 56
svg = []
svg.append(f'<svg viewBox="0 0 {FW} {FH}" width="100%" style="max-width:920px;display:block;margin:0 auto" font-family="-apple-system,Segoe UI,Microsoft YaHei,sans-serif">')
# threshold bands ±1.96
x_n = CTRL_Z(-1.96); x_p = CTRL_Z(1.96)
svg.append(f'<rect x="{x_n:.1f}" y="{y0-18}" width="{x_p-x_n:.1f}" height="{FH-y0-14}" fill="#fdecea" opacity="0.55"/>')
# zero line + threshold lines
svg.append(f'<line x1="{CTRL:.1f}" y1="{y0-18}" x2="{CTRL:.1f}" y2="{FH-14}" stroke="#444" stroke-width="1.2"/>')
for xn, lab in [(x_n,"-1.96"),(x_p,"+1.96")]:
    svg.append(f'<line x1="{xn:.1f}" y1="{y0-18}" x2="{xn:.1f}" y2="{FH-14}" stroke="#cf1322" stroke-width="1" stroke-dasharray="4 3" opacity="0.7"/>')
    svg.append(f'<text x="{xn:.1f}" y="{y0-22}" fill="#cf1322" font-size="10" text-anchor="middle">{lab}</text>')
svg.append(f'<text x="{CTRL:.1f}" y="{FH-2}" fill="#444" font-size="10" text-anchor="middle">t = 0（无影响）</text>')
# axis title
svg.append(f'<text x="{(PLOT_L+PLOT_R)/2:.1f}" y="{y0-34}" fill="#666" font-size="11" text-anchor="middle">横轴 = 双向聚类 t 统计量（符号=系数方向，超出红虚线≈显著）</text>')

for i, (layer, name, beta, t, sig, wcb, perm, fmt, grade, note) in enumerate(ROWS):
    y = y0 + i * row_h
    c = color_of(beta, sig)
    op = "1" if sig else "0.45"
    # bar from center to dot
    xdot = CTRL_Z(t)
    if xdot >= CTRL:
        svg.append(f'<rect x="{CTRL:.1f}" y="{y-7}" width="{xdot-CTRL:.1f}" height="14" rx="3" fill="{c}" opacity="{op}"/>')
    else:
        svg.append(f'<rect x="{xdot:.1f}" y="{y-7}" width="{CTRL-xdot:.1f}" height="14" rx="3" fill="{c}" opacity="{op}"/>')
    # dot
    svg.append(f'<circle cx="{xdot:.1f}" cy="{y}" r="5.5" fill="{c}" opacity="{op}" stroke="#fff" stroke-width="1.2"/>')
    # label
    svg.append(f'<text x="{LEFT-12}" y="{y+4}" fill="#222" font-size="12.5" text-anchor="end">{name} <tspan fill="#888" font-size="10.5">[{layer}]</tspan></text>')
    # value + stars
    star = sig if sig else ""
    star = {"***":"***","**":"**","*":"*","" :""}.get(sig,"")
    svg.append(f'<text x="{xdot+10:.1f}" y="{y+4}" fill="{c if sig else "#666"}" font-size="11" font-weight="600">β={beta:+.5f} {star}</text>')
    # grade pill
    svg.append(f'<text x="{PLOT_R+8:.1f}" y="{y+4}" fill="#666" font-size="10.5">{grade}</text>')

svg.append('</svg>')
FOREST = "\n".join(svg)

# ===================== 三指标 × 四口径 交叉验证网格 =====================
# DE / LSV / RA across: M4双向聚类, WCB, 置换, FM稀疏
cross = [
    ("处置效应 DE", "负向", [
        ("M4 双向聚类", True,  "t=-2.99***"),
        ("WCB 自助",   True,  "p=0.014**"),
        ("置换检验",   True,  "p=0.047*"),
        ("FM 稀疏",    False, "t=-1.57"),
    ]),
    ("羊群效应 LSV", "正向", [
        ("M4 双向聚类", False, "t=+0.77"),
        ("WCB 自助",   False, "p=0.229"),
        ("置换检验",   False, "p=0.507"),
        ("FM 稀疏",    False, "t=+0.27"),
    ]),
    ("风险不对称 RA", "正向", [
        ("M4 双向聚类", True,  "t=+3.57***"),
        ("WCB 自助",   True,  "p=0.000***"),
        ("置换检验",   True,  "p=0.020*"),
        ("FM 稀疏",   True,  "t=+2.18**"),
    ]),
]
cells = []
for ri, (ind, direction, methods) in enumerate(cross):
    for ci, (mname, sig, val) in enumerate(methods):
        fill = "#e6f4ea" if sig else "#fdecea"
        txt  = "#1e7a34" if sig else "#b3261e"
        mark = "✓" if sig else "✗"
        cells.append(f'<div class="cv-cell" style="background:{fill};color:{txt}"><span class="cv-mark">{mark}</span><span class="cv-val">{val}</span></div>')
GRID = "".join(cells)
CVHEAD = "".join(f'<div class="cv-head">{m}</div>' for m in ["M4 双向聚类","WCB 自助","置换检验","FM 稀疏"])

# ===================== A/B/C 分级堆叠 =====================
grades = [r[8] for r in ROWS]
na = grades.count("A"); nb = grades.count("B"); nc = grades.count("C")
total = len(grades)
def pct(n): return f"{n/total*100:.0f}%"
# 分层分布
layer_grade = {}
for layer, name, beta, t, sig, wcb, perm, fmt, grade, note in ROWS:
    layer_grade.setdefault(layer, []).append(grade)
BAR_SVG = f'''
<svg viewBox="0 0 520 120" width="100%" style="max-width:520px;display:block;margin:0 auto" font-family="-apple-system,Segoe UI,Microsoft YaHei,sans-serif">
  <rect x="10" y="40" width="{520-20}" height="34" rx="6" fill="#eee"/>
  <rect x="10" y="40" width="{(520-20)*na/total:.1f}" height="34" fill="#1e7a34"/>
  <rect x="{10+(520-20)*na/total:.1f}" y="40" width="{(520-20)*nb/total:.1f}" height="34" fill="#b26a00"/>
  <rect x="{10+(520-20)*(na+nb)/total:.1f}" y="40" width="{(520-20)*nc/total:.1f}" height="34" fill="#b3261e"/>
  <text x="{10+(520-20)*na/total/2:.1f}" y="62" fill="#fff" font-size="13" font-weight="700" text-anchor="middle">A {na}</text>
  <text x="{10+(520-20)*(na+nb)/total + (520-20)*nb/total/2:.1f}" y="62" fill="#fff" font-size="13" font-weight="700" text-anchor="middle">B {nb}</text>
  <text x="{10+(520-20)*(na+nb)/total + (520-20)*nc/total/2:.1f}" y="62" fill="#fff" font-size="13" font-weight="700" text-anchor="middle">C {nc}</text>
  <text x="10" y="95" fill="#1e7a34" font-size="11">A 强证据 {pct(na)}</text>
  <text x="180" y="95" fill="#b26a00" font-size="11">B 条件 {pct(nb)}</text>
  <text x="320" y="95" fill="#b3261e" font-size="11">C 弱/不稳 {pct(nc)}</text>
</svg>'''

# ---------- 组装 HTML ----------
today = datetime.date(2026, 8, 17).strftime("%Y-%m-%d")
html = f'''<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>回归结果展示与解读 · 基金经理行为指标研究（v4）</title>
<style>
*{{box-sizing:border-box;}}
body{{font-family:-apple-system,"Segoe UI","Microsoft YaHei",sans-serif;margin:0;background:#f4f6f9;color:#1a1f29;line-height:1.7;}}
.wrap{{max-width:1080px;margin:0 auto;padding:32px 24px 80px;}}
header.hero{{background:linear-gradient(135deg,#1f3b57,#2c5f8a);color:#fff;border-radius:14px;padding:30px 34px;box-shadow:0 6px 24px rgba(31,59,87,.25);}}
header.hero h1{{margin:0 0 8px;font-size:25px;letter-spacing:.5px;}}
header.hero p{{margin:4px 0;font-size:13.5px;opacity:.92;}}
.kpis{{display:flex;flex-wrap:wrap;gap:14px;margin-top:18px;}}
.kpi{{background:rgba(255,255,255,.14);border:1px solid rgba(255,255,255,.25);border-radius:10px;padding:12px 16px;min-width:120px;}}
.kpi b{{display:block;font-size:21px;line-height:1.2;}}
.kpi span{{font-size:11.5px;opacity:.85;}}
section{{background:#fff;border-radius:12px;padding:26px 30px;margin:22px 0;box-shadow:0 2px 10px rgba(0,0,0,.05);}}
section h2{{font-size:19px;color:#1f3b57;margin:0 0 6px;border-left:5px solid #2c5f8a;padding-left:12px;}}
section h3{{font-size:15px;color:#2c5f8a;margin:22px 0 8px;}}
.lead{{color:#555;font-size:13.5px;margin:0 0 14px;}}
.legend{{display:flex;gap:18px;flex-wrap:wrap;font-size:12.5px;margin:8px 0 4px;color:#444;}}
.legend i{{display:inline-block;width:12px;height:12px;border-radius:3px;margin-right:6px;vertical-align:-1px;}}
.box{{border-radius:10px;padding:14px 18px;margin:14px 0;font-size:13.5px;}}
.box.note{{background:#eef6ff;border-left:4px solid #2b7de9;}}
.box.key{{background:#eafaf1;border-left:4px solid #1e7a34;}}
.box.warn{{background:#fff7e6;border-left:4px solid #fa8c16;}}
.box.danger{{background:#fff1f0;border-left:4px solid #cf1322;}}
.box b{{color:#233;}}
table.tbl{{border-collapse:collapse;width:100%;font-size:13px;margin:10px 0;}}
table.tbl th,table.tbl td{{border:1px solid #e2e6ec;padding:8px 10px;text-align:center;}}
table.tbl th{{background:#2c5f8a;color:#fff;font-weight:600;}}
table.tbl td:first-child,table.tbl th:first-child{{text-align:left;}}
.gA{{background:#e6f4ea;color:#1e7a34;font-weight:700;}}
.gB{{background:#fff4e5;color:#b26a00;font-weight:700;}}
.gC{{background:#fdecea;color:#b3261e;font-weight:700;}}
.cv-grid{{display:grid;grid-template-columns:140px repeat(4,1fr);gap:6px;align-items:center;margin-top:10px;}}
.cv-head{{background:#2c5f8a;color:#fff;text-align:center;font-size:12.5px;padding:8px 4px;border-radius:6px;font-weight:600;}}
.cv-row-lab{{font-size:13px;font-weight:600;color:#233;}}
.cv-cell{{border-radius:8px;padding:10px 6px;text-align:center;font-size:12px;}}
.cv-mark{{display:block;font-size:18px;font-weight:800;}}
.cv-val{{display:block;font-size:11px;margin-top:2px;opacity:.9;}}
.flow{{display:flex;flex-wrap:wrap;gap:10px;margin:6px 0 14px;}}
.step{{flex:1;min-width:150px;background:#f7f9fc;border:1px solid #e2e8f0;border-radius:10px;padding:12px 14px;}}
.step .st{{font-size:11px;color:#2c5f8a;font-weight:700;letter-spacing:.5px;}}
.step .sd{{font-size:13px;margin-top:3px;}}
.step.done{{background:#eafaf1;border-color:#bfe6cc;}}
.step.doing{{background:#fff7e6;border-color:#ffe0a3;}}
.step.todo{{background:#f4f6f9;border-style:dashed;opacity:.85;}}
.pill{{display:inline-block;padding:1px 8px;border-radius:20px;font-size:11px;font-weight:700;}}
.pill.red{{background:#fdecea;color:#cf1322;}}
.pill.green{{background:#e6f7f0;color:#08976b;}}
.pill.gray{{background:#eef0f2;color:#6b7280;}}
footer{{color:#889;font-size:12px;text-align:center;margin-top:30px;}}
ul.tight{{margin:8px 0;padding-left:20px;}} li{{margin:5px 0;font-size:13.5px;}}
code{{background:#eef1f5;padding:1px 6px;border-radius:4px;font-size:12px;color:#1f3b57;}}
</style></head>
<body>
<div class="wrap">

<header class="hero">
  <h1>基金经理行为指标 · 回归结果展示与解读</h1>
  <p>五层行为框架（L1–L5）· v4 诚实面板 · 基金×年份双向聚类（CGM 2011）权威口径</p>
  <p>生成日期 {today} · 单一真相源：<code>回归表_双向聚类_v4基准_2026-08-16.html</code> · 与 <code>merged_manuscript.html</code> / <code>实证结论_证据强度总览_2026-08-16.html</code> 完全一致</p>
  <div class="kpis">
    <div class="kpi"><b>2,264</b><span>回归观测（诚实面板）</span></div>
    <div class="kpi"><b>348</b><span>基金（去重）</span></div>
    <div class="kpi"><b>0.1290</b><span>M4 拟合 R²</span></div>
    <div class="kpi"><b>3</b><span>估算量交叉验证</span></div>
    <div class="kpi"><b>A×6 / C×6</b><span>证据强度分布</span></div>
  </div>
</header>

<!-- ===== 研究进度状态 ===== -->
<section>
  <h2>一、研究推进到哪一步了</h2>
  <p class="lead">实证核心已"诚实化锁定"，文稿主体已完成 v4 口径刷新，当前处于"讨论/机制深化 + 投稿打磨"阶段。</p>
  <div class="flow">
    <div class="step done"><div class="st">✓ 已完成</div><div class="sd"><b>指标计算流水线</b><br>10 步数据处理 + L3/L1 回归，输出含TOwind面板（9,974观测/400只/51列）</div></div>
    <div class="step done"><div class="st">✓ 已完成</div><div class="sd"><b>描述性统计</b><br>报告+数据字典刷新至最新口径（TO_wind 86.6% 等）</div></div>
    <div class="step done"><div class="st">✓ 已完成</div><div class="sd"><b>主回归 M4</b><br>v4 双向聚类锁定，全程 1%/99% 缩尾，无未来泄漏</div></div>
    <div class="step done"><div class="st">✓ 已完成</div><div class="sd"><b>稳健性诊断</b><br>WCB / 置换 / FM / LSV脆弱性 / DE选择性 / 增量R²</div></div>
    <div class="step doing"><div class="st">● 进行中</div><div class="sd"><b>机制与讨论</b><br>AS↔ICI 反向、LSV 截面/组内反转等机制解读落地</div></div>
    <div class="step todo"><div class="st">○ 待办</div><div class="sd"><b>投稿打磨</b><br>英文 abstract、reviewer 应答、敏感性补充</div></div>
  </div>
  <div class="box note">
    <b>当前最可靠的结论（一句话）：</b>在控制 FF5 因子与全层变量后——
    <span class="pill green">风险不对称 RA（提升业绩，A级）</span> 与
    <span class="pill green">处置效应 DE（拖累业绩，A级·外推限46.6%子群）</span>
    是唯一跨"渐近 / 自助 / 置换"三口径一致显著的行为指标；
    <span class="pill gray">羊群效应 LSV 在所有口径下均不显著（C级）</span>，
    其早期"显著"为小样本+同层掩盖的假象，已诊断剔除。
  </div>
</section>

<!-- ===== M4 主回归森林图 ===== -->
<section>
  <h2>二、M4 主回归：行为指标如何影响基金业绩</h2>
  <p class="lead">因变量 = FF5 五因子模型残差 alpha（已缩尾）；横轴为 <b>双向聚类 t 统计量</b>，符号表示系数方向。
  超出红色虚线（|t|&gt;1.96）即统计显著。颜色遵循本文统一约定。</p>
  <div class="legend">
    <span><i style="background:{RED}"></i>β&gt;0 提升业绩（红）</span>
    <span><i style="background:{GREEN}"></i>β&lt;0 拖累业绩（绿）</span>
    <span><i style="background:{GRAY}"></i>不显著（灰，方向仍标）</span>
  </div>
  {FOREST}
  <div class="box key">
    <b>读图要点：</b>
    <ul class="tight">
      <li><b>L5 行为层（核心）</b>：RA（t=+3.57***）与 DE（t=−2.99***）显著且方向相反——<b>敢于不对称承担风险者业绩更好，而"卖盈持亏"的处置倾向显著侵蚀 alpha</b>；LSV（t=+0.77）落在灰色区，不显著。</li>
      <li><b>L2 持仓偏离</b>：ICI（行业集中度，t=+3.74***）正向、AS（主动份额，t=−2.81***）负向——"行业信念被奖励、总主动份额被惩罚"，二者符号相反的机制见第四节。</li>
      <li><b>L3 交易层</b>：ARG（调仓收益缺口，t=+2.98***）正向显著；SDI 与 TO_wind 在全控制下被吸收为不显著（C级），其对应 H1/H2 仅在稀疏设定成立。</li>
    </ul>
  </div>
</section>

<!-- ===== 三指标 × 四口径 交叉验证 ===== -->
<section>
  <h2>三、L5 三指标 × 四估算量 交叉验证</h2>
  <p class="lead">同一组行为指标，在四种推断框架下是否都给出一致方向/显著性？这是结论稳健性的"压力测试"。</p>
  <div class="cv-grid">
    <div class="cv-head">指标（方向）</div>{CVHEAD}
    <div class="cv-row-lab">处置效应 DE<br><span style="color:#08976b;font-size:11px">预期负向</span></div>{GRID[0:4]}
    <div class="cv-row-lab">羊群效应 LSV<br><span style="color:#cf1322;font-size:11px">预期正向</span></div>{GRID[4:8]}
    <div class="cv-row-lab">风险不对称 RA<br><span style="color:#cf1322;font-size:11px">预期正向</span></div>{GRID[8:12]}
  </div>
  <div class="box key">
    <b>结论：</b>
    <span class="pill green">RA 4/4 全中</span>——M4(WCB/置换/FM) 无一例外正向显著，是<b>最强单指标证据</b>；
    <span class="pill green">DE 3/4 中</span>——仅 FM 稀疏设定边际（t=−1.57），其余三口径一致负向显著，且组内FE强（t=−3.64），属 A 级但<b>外推限于约46.6%有全持仓数据子群</b>；
    <span class="pill gray">LSV 0/4 全空</span>——任何口径都不显著，C 级，早期"显著"结论已作废（见 §4.4.8 脆弱性诊断）。
  </div>
</section>

<!-- ===== 证据强度总览 ===== -->
<section>
  <h2>四、证据强度总览（A / B / C 分级）</h2>
  <p class="lead">A=强（多口径一致显著）· B=条件（部分口径/子样本显著）· C=弱或不稳（M4 不显著或方向样本敏感）。</p>
  {BAR_SVG}
  <table class="tbl">
    <thead><tr><th>层</th><th>指标</th><th>M4 β<br>(双向聚类)</th><th>t</th><th>显著性</th><th>WCB p</th><th>置换 p</th><th>分级</th><th>效度边界 / 稳健性索引</th></tr></thead>
    <tbody>
'''
for layer, name, beta, t, sig, wcb, perm, fmt, grade, note in ROWS:
    gpill = f'<span class="g{grade}">{grade}</span>'
    wcb_s = f"{wcb}" if wcb is not None else "—"
    perm_s = f"{perm}" if perm is not None else "—"
    star = sig if sig else ""
    html += (f'<tr><td>{layer}</td><td style="text-align:left">{name}</td>'
             f'<td>{beta:+.5f}</td><td>{t:+.2f}</td><td>{star if star else "n.s."}</td>'
             f'<td>{wcb_s}</td><td>{perm_s}</td><td>{gpill}</td>'
             f'<td style="text-align:left;font-size:12px;color:#555">{note}</td></tr>\n')

html += f'''    </tbody>
  </table>
  <div class="box warn"><b>增量 R²（L5 三指标整体贡献）：</b>全样本口径 ΔR² = <b>{DR2_FULL}</b>（M4 R² 0.1290 − 剔除L5后 0.0938）；
  同样本口径（M3↔M4 可比子集）ΔR² = <b>{DR2_SUB}</b>（≈2.2%）。两口径定义不同、并存；均远小于原稿误报的 0.0728（34.9%，已作废）。
  L5 行为指标对 alpha 的解释力虽非压倒性，但<b>方向与显著性稳健</b>，属"小而真实"的效应。</div>
</section>

<!-- ===== 机制解读 ===== -->
<section>
  <h2>五、关键机制解读（为什么结论长这样）</h2>

  <h3>5.1 主动份额 AS 为负、行业集中度 ICI 为正——为什么符号相反？</h3>
  <div class="box">
    Active Share 可分解为「行业配置偏离（≈ICI 渠道）+ 行业内个股选择偏离」。二者相关系数仅 <b>+0.045</b>（几乎正交），因此方向相反是<b>各自独立的真实现象，而非共线假象</b>。
    <ul class="tight">
      <li><b>ICI（+，t≈3.7）</b>：相对基准做对行业超配/低配（行业择时/配置诀窍）被市场奖励——最"干净"的技能信号。</li>
      <li><b>AS（−，t≈−2.8）</b>：在行业渠道被控制后，剩余的"行业内广撒网式个股偏离"平均不创造价值、反因交易成本与特质风险侵蚀 alpha（对应 Cremers &amp; Petajisto 2009：集中式主动份额才预测业绩）。</li>
      <li>旁证：行业 HHI 在联合方程中从单变量 +（t+0.19）翻为不显著——驱动 alpha 的是<b>相对基准的配置偏离（conviction）</b>，不是笼统的绝对集中度。</li>
    </ul>
  </div>

  <h3>5.2 LSV：截面 +0.10(不显著) vs 组内FE −0.19(***)——为什么反转？</h3>
  <div class="box">
    <ul class="tight">
      <li><b>截面（between-fund）</b>比的是"高注意力基金 vs 低注意力基金"的平均 alpha，被基金层面时不变特质（经理能力、风格、规模）混淆——平均注意力集中的基金多为成长/赛道型，因风格溢价看似不差（β正但不显著）。</li>
      <li><b>组内FE（within-fund）</b>清除这些混淆后，<b>同一只基金内部</b>抱团/追热点上升反而侵蚀 alpha（负向显著）。<b>符号反转(+→−)正是"截面受时不变遗漏变量干扰"的典型信号</b>。</li>
      <li>可靠结论取<b>组内FE（负向显著）</b>；截面仅作参照。与 §4.4.8 诊断（去掉同层 de/RA 后 lsv 单独显著、2022+ 子样本显著）口径一致——LSV 是"时期依存 + 被同层强信号掩盖"的指标，非失败变量，但降级为 C 级。</li>
    </ul>
  </div>

  <h3>5.3 DE 与 RA：双显著，但效度边界不同</h3>
  <div class="box">
    <ul class="tight">
      <li><b>RA（A级·最强）</b>：双向聚类*** + WCB*** + 置换* + FM** 全中；构念已对择时正交化，机制多元（赌资/择时/技能），是最稳健的"行为→业绩"证据。</li>
      <li><b>DE（A级·有外推边界）</b>：覆盖仅 46.6%（结构性缺失），估计样本被"是否有全持仓数据"选择；审计显示 de_avail 独立预测 alpha（+0.0048, t=2.18**）→ <b>存在正向选择偏倚</b>。结论<b>外推限于约46.6%有全持仓数据子群</b>，不可泛化全样本。</li>
    </ul>
  </div>

  <h3>5.4 文章主线结论（可直引）</h3>
  <div class="box key">
    在 2006Q2–2026Q2 中国主动偏股基金样本中，<b>基金经理的风险承担不对称（RiskAsym）显著正向预测风险调整后的基金业绩，而处置效应（DE）显著负向预测业绩</b>；
    行业层面的主动配置（ICI）被奖励、泛化的主动份额（AS）反被惩罚；
    传统"羊群/抱团"（LSV）在控制了同层强信号后不再显著。
    研究提示：<b>真正创造价值的不是"交易得多"或"跟得紧"，而是"不对称地承担经过判断的风险"与"克服处置倾向"</b>。
  </div>
</section>

<footer>
  数据源：指标计算流水线/output/主分析面板_重建_含TOwind.csv（v4 可复现）· 重算脚本 _v4_benchmark_table.py / _recompute_robustness_v4_2026-08-16.py / _diag_fama_macbeth_v4.py<br>
  推断口径：基金×年份双向聚类（CGM 2011）为主，单维基金聚类为对照；WCB / 500次置换 / Fama-MacBeth(T=20) 作交叉验证。本文颜色约定为结论导向（红=提升业绩/绿=拖累业绩），与股票涨跌配色无关。
</footer>

</div>
</body></html>'''

out = "回归结果展示与解读_v4_2026-08-17.html"
with open(out, "w", encoding="utf-8") as f:
    f.write(html)
print("WROTE", out, "| bytes:", len(html))
print("A/B/C:", na, nb, nc, "| total graded:", total)
