# -*- coding: utf-8 -*-
"""
生成《实证总结报告：文献综述 · 回归解读 · SDI 诊断》
数据来源（全部为项目已验证数字）：
  - _v4_benchmark.json（M4 双向聚类 v4 基准）
  - L3_L1_regression_HONEST_TOWind_2026-08-15.json（H1–H5 稀疏规格）
  - merged_manuscript.html（§4.2/§4.3/§4.4 截面/前向/组内/牛熊/中介/FM）
  - 实证结论_证据强度总览_2026-08-16.html（A/C 分级）
  - 主分析面板_重建_含TOwind.csv（2026-08-19 实测覆盖率/均值/SDI 逐年）
输出：实证总结报告_文献综述回归解读与SDI诊断_2026-08-19.html（自包含，无外部依赖）
"""
import math

OUT = "实证总结报告_文献综述回归解读与SDI诊断_2026-08-19.html"

# ============================================================ #
#  数据块                                                       #
# ============================================================ #

# M4 v4 基准（双向聚类 t2w）： (变量, 层, beta, se, t, p, 星号)
M4 = [
    ("risk_asym",        "L5",  0.07311, 0.02049,  3.57, 0.0004, "***"),
    ("ICI",              "L2",  0.01804, 0.00482,  3.74, 0.0002, "***"),
    ("ARG",              "L4",  0.01625, 0.00545,  2.98, 0.0029, "***"),
    ("AS_improved",      "L2", -0.02982, 0.01059, -2.81, 0.0049, "***"),
    ("de",               "L5", -0.00606, 0.00203, -2.99, 0.0028, "***"),
    ("log_fund_age",     "L1", -0.00417, 0.00165, -2.53, 0.0114, "**"),
    ("return_volatility","L4",  0.02379, 0.02919,  0.81, 0.4152, ""),
    ("lsv",              "L5",  0.01548, 0.02010,  0.77, 0.4411, ""),
    ("industry_hhi",     "L2",  0.00865, 0.04650,  0.19, 0.8524, ""),
    ("log_aum",          "控制", 0.00069, 0.00066, 1.05, 0.2955, ""),
    ("mgr_total_tenure_v2","L1", 7.007e-07, 6.883e-07, 1.02, 0.3088, ""),
    ("TO_wind",          "L3",  4.529e-06, 4.250e-06, 1.07, 0.2868, ""),
    ("SDI",              "L3", -2.289e-06, 1.348e-03, -0.00, 0.9986, ""),
]
M4_SE = {  # 精确 se（用于注释）
    "TO_wind": 4.25e-06, "SDI": 1.35e-3, "mgr_total_tenure_v2": 6.88e-07,
}
FF5 = [
    ("ff5_HML",         0.05166, 0.01802,  2.87, 0.0042, "***"),
    ("ff5_RMW",        -0.04971, 0.02407, -2.07, 0.0390, "**"),
    ("ff5_CMA",        -0.10853, 0.03818, -2.84, 0.0045, "***"),
    ("ff5_MKT_excess", -0.03396, 0.01799, -1.89, 0.0592, "*"),
    ("ff5_SMB",         0.01123, 0.00661,  1.70, 0.0894, "*"),
]

# L5 三重识别 + 稳健性（t 值；ns 留空星号）
L5X = {
    "risk_asym": dict(cross="+0.205 (4.55)***", fwd4="+0.313 (10.51)***", fwd1="−0.064 (−1.14) ns",
                      fe="−0.076 (−1.29) ns", m4="+0.0731 (3.57)***", wcb="0.000 ***", perm="0.020 *", fm="+0.0549 (2.18)**"),
    "de":        dict(cross="−0.057 (−3.28)***", fwd4="−0.056 (−7.11)***", fwd1="−0.071 (−4.81)***",
                      fe="−0.041 (−3.64)***", m4="−0.0061 (−2.99)***", wcb="0.014 **", perm="0.047 *", fm="−0.0049 (−1.57) ns"),
    "lsv":       dict(cross="+0.004 (0.06) ns", fwd4="+0.057 (1.81) ns", fwd1="+0.110 (1.61) ns",
                      fe="−0.005 (−0.15) ns", m4="+0.0155 (0.77) ns", wcb="0.229 ns", perm="0.507 ns", fm="+0.0043 (0.27) ns"),
}

# SDI 三规格
SDI_SPEC = [
    ("M4 全控制", "DV=FF5 alpha（ff5_adj_return）· 混合OLS+年份FE · 无基金FE", "β=−0.000002", "t=−0.00", "n.s.", 0.0, "N=2,264 / 348基金"),
    ("H1 稀疏规格", "DV=季度原始收益（quarter_return）· 基金FE+年份哑变量", "β=+0.1028", "t=+2.46", "**", 2.46, "N=6,337 / 366基金"),
    ("H4 联合规格", "DV=季度原始收益 · 基金FE · SDI+TO+OCI 同时进入", "β=+0.0198", "t=+3.09", "***", 3.09, "N=1,192 / 200基金"),
]

# SDI 逐年（实测）
SDI_YEAR = [(2017, 47, 0.0), (2018, 142, 0.0), (2019, 199, 0.0), (2020, 222, 0.0), (2021, 236, 0.0),
            (2022, 873, 0.2516), (2023, 1192, 0.2333), (2024, 1317, 0.1941), (2025, 1406, 0.3219), (2026, 728, 0.4320)]

# 牛熊（MKT_excess 符号分组）
BULLBEAR = [
    ("RiskAsym", 0.0651, "4.08", "***", 0.1034, "3.74", "***"),
    ("LSV",      0.0014, "0.10", "",    0.0424, "2.32", "**"),
    ("DE",      -0.0066, "−2.36", "**", -0.0049, "−1.11", ""),
]

# 覆盖率（2026-08-19 实测，主分析面板_重建_含TOwind.csv，N=9,974）
COV = [
    ("log_fund_age 基金年龄", 100.0, "L1"), ("education 学历", 99.1, "L1"),
    ("mgr_tenure 任期", 99.1, "L1"), ("gender/CFA", 98.2, "L1"),
    ("ff5_adj_return 因变量", 97.2, "DV"), ("ARG 主动风险增益", 96.7, "L4"),
    ("AS_improved 主动份额", 94.4, "L2"), ("ICI 行业偏离", 94.3, "L2"),
    ("industry_hhi 行业HHI", 94.3, "L2"), ("lsv 羊群效应", 92.1, "L5"),
    ("return_volatility 波动率", 92.0, "L4"), ("TO_wind 换手率", 86.6, "L3"),
    ("risk_asym 风险不对称", 72.0, "L5"), ("SDI 风格漂移", 63.8, "L3"),
    ("de 处置效应", 46.6, "L5"),
]

# 递进回归
PROG = [("M0", 0.0154, 9255, "控制+FF5"), ("M1", 0.0431, 9167, "+L1 背景"),
        ("M2", 0.0873, 8668, "+L2 持仓"), ("M3", 0.0938, 4881, "+L3/L4 交易与风险"),
        ("M4", 0.1290, 2264, "+L5 认知偏差")]

# 证据分级（实证结论_证据强度总览_2026-08-16）
GRADE = [
    ("L2", "行业偏离 ICI", "+0.01804", "+3.74", "A", "行业集中下注带来超额收益，稳健；净效应取决于选股能力"),
    ("L2", "主动份额 AS", "−0.02982", "−2.81", "A", "高主动份额伴随更低 alpha；与 ICI 构成\"方向>量\""),
    ("L4", "主动风险增益 ARG", "+0.01625", "+2.98", "A", "主动风险调整正向关联业绩；截面+组内双证据"),
    ("L5", "风险不对称 RA", "+0.07311", "+3.57", "A", "双向聚类***+WCB***+置换*；截面/前向/M4 全显著"),
    ("L5", "处置效应 DE", "−0.00606", "−2.99", "A", "双向聚类***+WCB**+置换*；组内FE t=−3.64 最接近因果；外推限 46.6% 子群"),
    ("L1", "基金年龄 log_fund_age", "−0.00417", "−2.53", "A", "老基金 alpha 更低，稳健结构性控制"),
    ("L3", "风格漂移 SDI", "≈0", "−0.00", "C", "M4 全控制下不显著（DV=alpha 剥离风格收益+被 L2/L4 吸收）；稀疏 H1/H4 显著"),
    ("L3", "换手率 TO_wind", "≈0", "+1.07", "C", "M4 不显著；稀疏 t=+1.78*；成本侵蚀弱且中介 b 路径不显著"),
    ("L5", "羊群效应 LSV", "+0.01548", "+0.77", "C", "被同层 de/RA 掩盖+时期依存+仅熊市显著+选择敏感"),
    ("L2", "行业 HHI", "+0.00865", "+0.19", "C", "与 ICI 共线（相关 0.84），方向信息被吸收"),
    ("L4", "收益波动率 RV", "+0.02379", "+0.81", "C", "直接预测无信息；作为中介渠道显著（通道非信号）"),
    ("L1", "经理任期 tenure", "≈0", "+1.02", "C", "任期长度与业绩无稳定截面关联"),
]

# 国内评级机构对照
RATERS = [
    ("晨星中国（持牌）", "基金", "风险调整收益 MRAR（期望效用理论，侧重下行风险）", "类内百分位：前10%五星 / 22.5%四星 / 35%三星 / 22.5%二星 / 10%一星", "星级；3/5/10 年期；季度更新"),
    ("招商证券（持牌）", "基金", "收益 / 风险 / 流动性（CAPM+单指数模型基础）", "类内排序同上五星分布；36/60/120 个月窗口", "星级；季度更新"),
    ("海通证券（持牌）", "基金", "夏普 / 特雷诺 / 信息比率 + 持股调整收益（重仓股品质）", "多指标综合打分", "10 分制"),
    ("银河证券（持牌）", "基金", "三级分类体系（2006 年起）下的类内业绩比较", "类内排序", "星级"),
    ("上海证券（持牌）", "基金", "三能力：风险管理（夏普）/ 选证能力 / 择时能力", "能力驱动综合评级", "星级"),
    ("济安金信（持牌）", "基金/公司", "盈利 / 抗风险 / 选股择时 / 契约履行（定性：合同偏离、分红履约，违规不予评价）", "分形市场理论+多目标规划，类内多因素", "星级；季度"),
    ("金牛奖（中证报+5家协办）", "基金/公司", "收益 / 风险 / 稳定性 / 合规（70% 定量+30% 定性；五机构独立计算互核）", "评奖制；存续 3 年以上", "年度奖项（\"基金业奥斯卡\"）"),
    ("天天基金（非持牌，C端流量最大）", "基金经理", "经验值 / 收益率 / 抗风险 / 稳定性 / 择时能力", "五维打分加权（权重保密）；经理业绩由所管基金代理", "百分制综合分"),
]

# ============================================================ #
#  CSS                                                          #
# ============================================================ #
CSS = """
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:system-ui,-apple-system,'Segoe UI','Microsoft YaHei',sans-serif;background:#f1f5f9;color:#1f2937;line-height:1.75;font-size:15px}
.wrap{max-width:1000px;margin:0 auto;padding:28px 20px 60px}
header{background:linear-gradient(135deg,#0f2557 0%,#1e3a8a 60%,#3730a3 100%);color:#fff;border-radius:14px;padding:34px 38px;margin-bottom:22px}
header h1{font-size:26px;letter-spacing:.5px;margin-bottom:10px}
header .meta{font-size:13px;opacity:.85;line-height:1.9}
h2{font-size:21px;margin:40px 0 14px;padding:8px 0 8px 14px;border-left:5px solid #1d4ed8;background:#eef2ff;border-radius:0 8px 8px 0}
h3{font-size:17px;margin:26px 0 10px;color:#1e3a8a}
h4{font-size:15px;margin:18px 0 8px;color:#334155}
p{margin:10px 0}
.lead{color:#374151}
.muted{color:#6b7280;font-size:13px}
.box{background:#fff;border:1px solid #e5e7eb;border-radius:12px;padding:18px 22px;margin:14px 0;box-shadow:0 1px 4px rgba(15,23,42,.05)}
.box.key{border-left:5px solid #b45309;background:#fffbeb}
.box.warn{border-left:5px solid #b91c1c;background:#fef2f2}
.box.info{border-left:5px solid #1d4ed8;background:#eff6ff}
.box.ok{border-left:5px solid #15803d;background:#f0fdf4}
table{border-collapse:collapse;width:100%;margin:12px 0;background:#fff;font-size:13.5px}
th{background:#1e3a8a;color:#fff;padding:8px 10px;text-align:left;font-weight:600}
td{padding:7px 10px;border-bottom:1px solid #e5e7eb;vertical-align:top}
tr:nth-child(even) td{background:#f8fafc}
.num{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
.sig{font-weight:700}
.pos{color:#b91c1c}.neg{color:#15803d}.ns{color:#9ca3af}
.cellA{background:#dcfce7!important;font-weight:700;color:#14532d}
.cellC{background:#fee2e2!important;font-weight:700;color:#7f1d1d}
.toc{background:#fff;border:1px solid #e5e7eb;border-radius:12px;padding:16px 24px;margin:0 0 8px;columns:2;column-gap:30px;font-size:13.5px}
.toc a{color:#1d4ed8;text-decoration:none;display:block;padding:3px 0}
.toc a:hover{text-decoration:underline}
.fig{background:#fff;border:1px solid #e5e7eb;border-radius:12px;padding:14px 10px 8px;margin:16px 0;text-align:center}
.fig .cap{font-size:12.5px;color:#6b7280;margin:6px 8px 4px;text-align:left;line-height:1.6}
.svgbox{width:100%;overflow-x:auto}
.legend{display:flex;flex-wrap:wrap;gap:6px 18px;justify-content:center;font-size:12.5px;color:#475569;margin:2px 0 6px}
.legend .sw{display:inline-block;width:11px;height:11px;border-radius:3px;margin-right:5px;vertical-align:-1px}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:14px}
@media(max-width:760px){.grid2{grid-template-columns:1fr}.toc{columns:1}}
.kpi{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px;margin:14px 0}
.kpi .card{background:#fff;border:1px solid #e5e7eb;border-radius:10px;padding:12px 14px}
.kpi .v{font-size:20px;font-weight:800;color:#1e3a8a}
.kpi .l{font-size:12px;color:#6b7280;margin-top:2px}
code{background:#eef2ff;color:#3730a3;padding:1px 6px;border-radius:4px;font-size:.92em}
.footnote{font-size:12.5px;color:#6b7280;border-top:1px dashed #d1d5db;padding-top:8px;margin-top:10px}
"""

# ============================================================ #
#  SVG 组件                                                      #
# ============================================================ #

def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def star_color(t, stars):
    if not stars:
        return "#9ca3af"
    return "#b91c1c" if t > 0 else "#15803d"

def svg_forest(rows, title, xlo, xhi, width=940, rowh=27, note=""):
    n = len(rows)
    h = 64 + n * rowh + 34
    plotx0, plotx1 = 250, 660
    tx0, tx1 = 690, 920
    def X(v):
        return plotx0 + (v - xlo) / (xhi - xlo) * (plotx1 - plotx0)
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {h}" font-family="system-ui,Segoe UI,Microsoft YaHei">']
    s.append(f'<text x="{width/2}" y="24" font-size="15" font-weight="700" fill="#111827" text-anchor="middle">{esc(title)}</text>')
    # 零线
    if xlo < 0 < xhi:
        s.append(f'<line x1="{X(0)}" y1="40" x2="{X(0)}" y2="{48+n*rowh}" stroke="#334155" stroke-width="1.6" stroke-dasharray="5,4"/>')
        s.append(f'<text x="{X(0)}" y="{48+n*rowh+16}" font-size="11" fill="#334155" text-anchor="middle">0</text>')
    # 网格
    import numpy as _np
    ticks = _np.linspace(xlo, xhi, 5)
    for tv in ticks:
        xx = X(tv)
        s.append(f'<line x1="{xx:.1f}" y1="40" x2="{xx:.1f}" y2="{48+n*rowh}" stroke="#e5e7eb" stroke-width="1"/>')
        s.append(f'<text x="{xx:.1f}" y="{48+n*rowh+16}" font-size="11" fill="#9ca3af" text-anchor="middle">{tv:+.3f}</text>')
    for i, row in enumerate(rows):
        if len(row) == 7:
            name, layer, beta, se, t, p, stars = row
        else:
            name, beta, se, t, p, stars = row
            layer = "FF5"
        y = 56 + i * rowh
        lo, hi = beta - 1.96 * se, beta + 1.96 * se
        col = star_color(t, stars)
        filled = bool(stars)
        s.append(f'<text x="238" y="{y+4}" font-size="12.5" fill="#1f2937" text-anchor="end">{esc(name)} <tspan fill="#94a3b8" font-size="10.5">[{layer}]</tspan></text>')
        s.append(f'<line x1="{X(lo):.1f}" y1="{y}" x2="{X(hi):.1f}" y2="{y}" stroke="{col}" stroke-width="{2.2 if filled else 1.4}" stroke-opacity="{1 if filled else .65}"/>')
        if hi - lo > (xhi - xlo) * 0.004:
            s.append(f'<line x1="{X(lo):.1f}" y1="{y-4}" x2="{X(lo):.1f}" y2="{y+4}" stroke="{col}" stroke-width="1.6"/>')
            s.append(f'<line x1="{X(hi):.1f}" y1="{y-4}" x2="{X(hi):.1f}" y2="{y+4}" stroke="{col}" stroke-width="1.6"/>')
        r = 5 if filled else 4.2
        s.append(f'<circle cx="{X(beta):.1f}" cy="{y}" r="{r}" fill="{col if filled else "#fff"}" stroke="{col}" stroke-width="1.8"/>')
        sst = f" t={t:+.2f}{'('+stars+')' if stars else ' n.s.'}"
        s.append(f'<text x="{tx0}" y="{y+4}" font-size="12" fill="{col}" font-weight="{700 if filled else 400}">{esc(sst)}</text>')
        beta_s = f"{beta:+.2e}" if (beta != 0 and abs(beta) < 1e-4) else f"{beta:+.4f}"
        s.append(f'<text x="{tx1}" y="{y+4}" font-size="11" fill="#6b7280" text-anchor="end">β={beta_s}</text>')
    s.append('</svg>')
    cap = note or f'95% CI = β ± 1.96·SE（双向聚类 t2w 口径）。实心点=显著（红=正向，绿=负向），空心点=不显著。'
    return '<div class="fig"><div class="svgbox">' + "".join(s) + '</div><div class="cap">' + cap + '</div></div>'

def svg_cov():
    width, rowh = 940, 24
    n = len(COV)
    h = 56 + n * rowh + 10
    laycol = {"L1": "#64748b", "L2": "#1d4ed8", "L3": "#0f766e", "L4": "#b45309", "L5": "#b91c1c", "DV": "#7c3aed"}
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {h}" font-family="system-ui,Segoe UI,Microsoft YaHei">']
    s.append(f'<text x="{width/2}" y="22" font-size="15" font-weight="700" fill="#111827" text-anchor="middle">变量覆盖率（2026-08-19 面板实测，N=9,974）</text>')
    x0, x1 = 235, 830
    for gv in (0, 25, 50, 75, 100):
        xx = x0 + gv / 100 * (x1 - x0)
        s.append(f'<line x1="{xx}" y1="34" x2="{xx}" y2="{44+n*rowh}" stroke="#e5e7eb"/>')
        s.append(f'<text x="{xx}" y="{44+n*rowh+0}" font-size="10.5" fill="#9ca3af" text-anchor="middle">{gv}%</text>')
    for i, (name, cov, layer) in enumerate(COV):
        y = 50 + i * rowh
        c = laycol[layer]
        w = cov / 100 * (x1 - x0)
        s.append(f'<text x="225" y="{y+4}" font-size="12" fill="#1f2937" text-anchor="end">{esc(name)}</text>')
        s.append(f'<rect x="{x0}" y="{y-8}" width="{x1-x0}" height="15" rx="3" fill="#f1f5f9"/>')
        s.append(f'<rect x="{x0}" y="{y-8}" width="{w:.1f}" height="15" rx="3" fill="{c}"/>')
        s.append(f'<text x="{x1+6}" y="{y+4}" font-size="11.5" fill="#374151">{cov:.1f}%</text>')
    s.append('</svg>')
    lg = '<div class="legend">' + "".join(
        f'<span><span class="sw" style="background:{laycol[k]}"></span>{k}</span>' for k in ["L1", "L2", "L3", "L4", "L5", "DV"]) + '</div>'
    cap = ('M4 完整观测要求全部变量非缺失，交集 N=2,264（22.7%）——约束主要来自 de（46.6%）∩ risk_asym（72.0%）∩ TO_wind（86.6%）。'
           'SDI 的 63.8% 中 2017–2021 为结构零（详见 §6）。')
    return '<div class="fig">' + lg + '<div class="svgbox">' + "".join(s) + '</div><div class="cap">' + cap + '</div></div>'

def svg_r2():
    width, h = 940, 345
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {h}" font-family="system-ui,Segoe UI,Microsoft YaHei">']
    s.append(f'<text x="{width/2}" y="24" font-size="15" font-weight="700" fill="#111827" text-anchor="middle">M0→M4 递进回归：R² 阶梯与 L5 增量</text>')
    x0, x1 = 70, 890
    base, bh = 250, 26
    step = (x1 - x0 - 40) / 5
    for i, (m, r2, n, note) in enumerate(PROG):
        cx = x0 + 20 + i * step
        hh = r2 / 0.14 * 165
        col = "#1e3a8a" if m != "M4" else "#b45309"
        s.append(f'<rect x="{cx}" y="{base-hh}" width="72" height="{hh}" rx="5" fill="{col}"/>')
        s.append(f'<text x="{cx+36}" y="{base-hh-10}" font-size="13.5" font-weight="700" fill="{col}" text-anchor="middle">{r2:.4f}</text>')
        s.append(f'<text x="{cx+36}" y="{base+20}" font-size="13" font-weight="700" fill="#111827" text-anchor="middle">{m}</text>')
        s.append(f'<text x="{cx+36}" y="{base+37}" font-size="10.5" fill="#6b7280" text-anchor="middle">{esc(note)}</text>')
        s.append(f'<text x="{cx+36}" y="{base+52}" font-size="10.5" fill="#9ca3af" text-anchor="middle">N={n:,}</text>')
    # 增量标注
    xm3 = x0 + 20 + 3 * step + 36
    xm4 = x0 + 20 + 4 * step + 36
    s.append('<defs><marker id="arr" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto"><path d="M0,0 L6,3 L0,6 z" fill="#b45309"/></marker></defs>')
    s.append(f'<path d="M {xm3} 96 H {xm4-56}" stroke="#b45309" stroke-width="1.6" stroke-dasharray="4,3" marker-end="url(#arr)"/>')
    s.append(f'<text x="{(xm3+xm4)/2-20}" y="78" font-size="12" fill="#b45309" text-anchor="middle" font-weight="700">ΔR²(L5)</text>')
    s.append(f'<text x="{(xm3+xm4)/2-20}" y="62" font-size="11" fill="#b45309" text-anchor="middle">全样本 0.035 / 同样本 0.022</text>')
    s.append(f'<text x="{width/2}" y="{h-10}" font-size="11.5" fill="#6b7280" text-anchor="middle">注意：M3（N=4,881）与 M4（N=2,264）样本不同；同样本口径下 M3 R²=0.1066 → ΔR²=0.0221（§4.3 排除样本选择偏差）</text>')
    s.append('</svg>')
    return '<div class="fig"><div class="svgbox">' + "".join(s) + '</div><div class="cap">五层递进设计：控制+FF5 → +L1 背景 → +L2 持仓 → +L3/L4 交易与风险 → +L5 认知偏差。L5 在控制全部可观测行为后仍贡献同样本 ΔR²≈0.022（占 M4 总 R² 的 17%）。</div></div>'

def svg_sdi_year():
    width, h = 940, 300
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {h}" font-family="system-ui,Segoe UI,Microsoft YaHei">']
    s.append(f'<text x="{width/2}" y="22" font-size="15" font-weight="700" fill="#111827" text-anchor="middle">SDI 逐年均值与观测数：2017–2021 恒为结构零，有效变异自 2022 起</text>')
    x0, x1, base = 70, 900, 235
    step = (x1 - x0) / len(SDI_YEAR)
    for gy in (0.0, 0.15, 0.30, 0.45):
        yy = base - gy / 0.5 * 165
        s.append(f'<line x1="{x0}" y1="{yy}" x2="{x1}" y2="{yy}" stroke="#e5e7eb"/>')
        s.append(f'<text x="{x0-8}" y="{yy+4}" font-size="10.5" fill="#9ca3af" text-anchor="end">{gy:.2f}</text>')
    for i, (yr, n, m) in enumerate(SDI_YEAR):
        cx = x0 + step * (i + 0.5)
        hh = m / 0.5 * 165
        real = yr >= 2022
        col = "#0f766e" if real else "#cbd5e1"
        s.append(f'<rect x="{cx-26}" y="{base-hh}" width="52" height="{max(hh,2)}" rx="4" fill="{col}"/>')
        s.append(f'<text x="{cx}" y="{base-hh-8 if real else base-12}" font-size="11" fill="{("#0f766e" if real else "#94a3b8")}" text-anchor="middle" font-weight="{700 if real else 400}">{m:.2f}</text>')
        s.append(f'<text x="{cx}" y="{base+18}" font-size="12" fill="#374151" text-anchor="middle" font-weight="600">{yr}</text>')
        s.append(f'<text x="{cx}" y="{base+32}" font-size="10" fill="#9ca3af" text-anchor="middle">n={n}</text>')
    s.append(f'<text x="{width/2}" y="{h-12}" font-size="11.5" fill="#6b7280" text-anchor="middle">灰=结构零（滚动窗口未成熟，非"无漂移"的测量）；青=真实变异。2026 为不完整年度。</text>')
    s.append('</svg>')
    return '<div class="fig"><div class="svgbox">' + "".join(s) + '</div><div class="cap">SDI 由 8 季滚动 OLS（基金季收益对 4 风格指数）反推风格权重后取相邻期曼哈顿距离：风格指数数据起点+窗口预热导致 2017–2021 全部为零。这批"伪零"在 M4 中占 SDI 非缺失观测的约 25%，构成经典测量误差→衰减偏误。</div></div>'

def svg_sdi_spec():
    width, h = 940, 340
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {h}" font-family="system-ui,Segoe UI,Microsoft YaHei">']
    s.append(f'<text x="{width/2}" y="22" font-size="15" font-weight="700" fill="#111827" text-anchor="middle">SDI 系数的三规格对比：同一指标、三种设计、三种答案</text>')
    x0, x1 = 240, 560
    base = 218
    def X(t):
        return x0 + (t + 0.6) / 4.2 * (x1 - x0)
    for tv in (0, 1.96, 2.58):
        xx = X(tv)
        s.append(f'<line x1="{xx}" y1="52" x2="{xx}" y2="{base}" stroke="{"#94a3b8" if tv==0 else "#d97706"}" stroke-width="{"1.6" if tv==0 else "1.2"}" stroke-dasharray="4,3"/>')
        lab = "t=0" if tv == 0 else ("1.96 (5%)" if tv == 1.96 else "2.58 (1%)")
        s.append(f'<text x="{xx}" y="{base+18}" font-size="11" fill="{"#6b7280" if tv==0 else "#b45309"}" text-anchor="middle">{lab}</text>')
    for i, (name, spec, beta, tlab, stars, t, n) in enumerate(SDI_SPEC):
        y = 84 + i * 46
        sig = bool(stars)
        col = "#b91c1c" if (t > 0 and sig) else ("#15803d" if sig else "#9ca3af")
        s.append(f'<text x="228" y="{y+4}" font-size="13.5" font-weight="700" fill="#111827" text-anchor="end">{esc(name)}</text>')
        s.append(f'<rect x="{min(X(0), X(t)):.1f}" y="{y-9}" width="{max(abs(X(t)-X(0)),3):.1f}" height="18" rx="3" fill="{col}" fill-opacity="{0.9 if sig else 0.45}"/>')
        s.append(f'<text x="{X(t):.1f}" y="{y-15}" font-size="12.5" font-weight="700" fill="{col}" text-anchor="middle">{esc(tlab)}{(" "+stars) if stars else " n.s."}</text>')
        s.append(f'<text x="930" y="{y-2}" font-size="11.5" fill="#374151" text-anchor="end">{esc(beta)}</text>')
        s.append(f'<text x="930" y="{y+16}" font-size="10.5" fill="#6b7280" text-anchor="end">{esc(n)}</text>')
        s.append(f'<text x="228" y="{y+21}" font-size="10" fill="#9ca3af" text-anchor="end">{esc(spec)}</text>')
    s.append(f'<text x="{width/2}" y="{h-12}" font-size="12" fill="#6b7280" text-anchor="middle">横轴为 t 统计量（双向聚类）；关键差异：M4 的因变量是 FF5 alpha（风格中性收益），H1/H4 是原始季度收益</text>')
    s.append('</svg>')
    return '<div class="fig"><div class="svgbox">' + "".join(s) + '</div><div class="cap">SDI 并非"无信息"：在以原始收益为因变量、含基金固定效应的规格中稳定显著（t=2.46**/3.09***）；它失效的恰好是"以 alpha 为因变量+全控制"的 M4——这是构念与因变量正交的表现，详见 §6.3 机制①。</div></div>'

def svg_bullbear():
    width, h = 940, 300
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {h}" font-family="system-ui,Segoe UI,Microsoft YaHei">']
    s.append(f'<text x="{width/2}" y="24" font-size="15" font-weight="700" fill="#111827" text-anchor="middle">L5 三指标的牛熊市分化（MKT_excess 符号分组，M4 口径）</text>')
    x0, x1 = 250, 720
    base = 240
    def X(v):
        return x0 + (v + 0.02) / 0.14 * (x1 - x0)
    s.append(f'<line x1="{X(0)}" y1="48" x2="{X(0)}" y2="{base}" stroke="#334155" stroke-width="1.6" stroke-dasharray="5,4"/>')
    s.append(f'<text x="{X(0)}" y="{base+16}" font-size="11" fill="#334155" text-anchor="middle">0</text>')
    for gv in (0.05, 0.10):
        s.append(f'<line x1="{X(gv)}" y1="48" x2="{X(gv)}" y2="{base}" stroke="#e5e7eb"/>')
        s.append(f'<text x="{X(gv)}" y="{base+16}" font-size="10.5" fill="#9ca3af" text-anchor="middle">+{gv:.2f}</text>')
    for i, (name, b, bt, bs, e, et, es) in enumerate(BULLBEAR):
        cy = 86 + i * 58
        s.append(f'<text x="236" y="{cy+4}" font-size="13.5" font-weight="700" fill="#111827" text-anchor="end">{esc(name)}</text>')
        # 连接线
        s.append(f'<line x1="{X(min(b,e)):.1f}" y1="{cy}" x2="{X(max(b,e)):.1f}" y2="{cy}" stroke="#cbd5e1" stroke-width="3"/>')
        # 牛市点（上标签）
        sig_b = bool(bs)
        cb = "#b91c1c" if sig_b else "#fca5a5"
        s.append(f'<circle cx="{X(b):.1f}" cy="{cy}" r="7" fill="{cb}" stroke="#fff" stroke-width="1.6"/>')
        s.append(f'<text x="{X(b):.1f}" y="{cy-14}" font-size="11.5" fill="{"#b91c1c" if sig_b else "#9ca3af"}" text-anchor="middle" font-weight="{700 if sig_b else 400}">牛市 {b:+.4f} (t={bt}){(" "+bs) if bs else " n.s."}</text>')
        # 熊市点（下标签）
        sig_e = bool(es)
        ce = "#7c2d12" if sig_e else "#fed7aa"
        s.append(f'<circle cx="{X(e):.1f}" cy="{cy}" r="7" fill="{ce}" stroke="#fff" stroke-width="1.6"/>')
        s.append(f'<text x="{X(e):.1f}" y="{cy+24}" font-size="11.5" fill="{"#7c2d12" if sig_e else "#9ca3af"}" text-anchor="middle" font-weight="{700 if sig_e else 400}">熊市 {e:+.4f} (t={et}){(" "+es) if es else " n.s."}</text>')
    s.append(f'<text x="{width/2}" y="{h-10}" font-size="12" fill="#6b7280" text-anchor="middle">牛市≈1,680 obs（74%）/ 熊市≈584 obs（26%）；红点=牛市系数，棕点=熊市系数，灰线=两点跨度</text>')
    s.append('</svg>')
    return '<div class="fig"><div class="svgbox">' + "".join(s) + '</div><div class="cap">RiskAsym 牛熊均***（熊市更强 +0.103 vs +0.065）；LSV 仅熊市显著（+0.042, t=2.32）——协同交易的压力期信号；DE 仅牛市显著（−0.0066, t=−2.36）——果断止损的收益集中在上行期。</div></div>'

# ============================================================ #
#  HTML 表格组件                                                 #
# ============================================================ #

def cell_class(txt):
    if "***" in txt:
        return "pos" if txt.startswith("+") or txt.startswith("0.0") else "neg"
    if "**" in txt:
        return "pos" if txt.startswith("+") else "neg"
    return "ns"

def l5_matrix_table():
    cols = [("cross", "截面 N=200"), ("fwd4", "前向 4 季"), ("fwd1", "前向 1 季"), ("fe", "组内 FE"), ("m4", "面板 M4"), ("wcb", "WCB-S p"), ("perm", "置换 p"), ("fm", "FM 稀疏")]
    h = ['<table><tr><th>指标</th>'] + [f'<th>{c[1]}</th>' for c in cols] + ['</tr>']
    names = {"risk_asym": "RiskAsym 风险不对称", "de": "DE 处置效应", "lsv": "LSV 羊群效应"}
    for k in ["risk_asym", "de", "lsv"]:
        h.append(f'<tr><td><b>{names[k]}</b></td>')
        for cid, _ in cols:
            v = L5X[k][cid]
            cl = cell_class(v) if "n.s." not in v and "ns" not in v else "ns"
            h.append(f'<td class="num sig {cl}">{esc(v)}</td>')
        h.append('</tr>')
    h.append('</table>')
    return "".join(h)

def m4_table():
    h = ['<table><tr><th>变量</th><th>层</th><th class="num">系数 β</th><th class="num">SE(t2w)</th><th class="num">t(t2w)</th><th class="num">p</th><th class="num">t(t1w)</th><th>判定</th></tr>']
    t1w = {"risk_asym": 4.53, "ICI": 3.65, "ARG": 2.65, "AS_improved": -2.90, "de": -2.50, "log_fund_age": -2.56,
           "return_volatility": 1.07, "lsv": 1.23, "industry_hhi": 0.19, "log_aum": 1.21, "mgr_total_tenure_v2": 1.00, "TO_wind": 0.96, "SDI": -0.00}
    for name, layer, beta, se, t, p, stars in M4:
        se_disp = M4_SE.get(name, se)
        cls = ("pos" if t > 0 else "neg") if stars else "ns"
        judg = {"risk_asym": "显著正（A级）", "ICI": "显著正（A级）", "ARG": "显著正（A级）", "AS_improved": "显著负（A级）",
                "de": "显著负（A级）", "log_fund_age": "显著负（A级）"}.get(name, "不显著（C级）")
        beta_s = f"{beta:+.2e}" if (beta != 0 and abs(beta) < 1e-4) else f"{beta:+.5f}"
        se_s = f"{se_disp:.2e}" if (se_disp != 0 and abs(se_disp) < 1e-4) else f"{se_disp:.6f}"
        h.append(f'<tr><td><code>{esc(name)}</code></td><td>{layer}</td><td class="num">{beta_s}</td><td class="num">{se_s}</td>'
                 f'<td class="num sig {cls}">{t:+.2f}{"("+stars+")" if stars else " n.s."}</td><td class="num">{p:.3f}</td><td class="num muted">{t1w[name]:+.2f}</td><td>{judg}</td></tr>')
    for name, beta, se, t, p, stars in FF5:
        cls = ("pos" if t > 0 else "neg") if stars else "ns"
        h.append(f'<tr><td><code>{esc(name)}</code></td><td>FF5</td><td class="num">{beta:+.5f}</td><td class="num">{se:.6f}</td>'
                 f'<td class="num sig {cls}">{t:+.2f}{"("+stars+")" if stars else " n.s."}</td><td class="num">{p:.3f}</td><td class="num muted">—</td><td>因子载荷</td></tr>')
    h.append('</table>')
    return "".join(h)

def grade_table():
    h = ['<table><tr><th>层</th><th>指标</th><th class="num">M4 β</th><th class="num">t</th><th>分级</th><th>要点</th></tr>']
    for layer, name, b, t, g, note in GRADE:
        cl = "cellA" if g == "A" else "cellC"
        h.append(f'<tr><td>{layer}</td><td><b>{esc(name)}</b></td><td class="num">{b}</td><td class="num">{t}</td>'
                 f'<td class="{cl}" style="text-align:center">{g}</td><td>{esc(note)}</td></tr>')
    h.append('</table>')
    return "".join(h)

def raters_table():
    h = ['<table><tr><th>机构</th><th>评价对象</th><th>核心维度</th><th>方法</th><th>输出 / 频率</th></tr>']
    for r in RATERS:
        h.append('<tr>' + "".join(f'<td>{esc(x)}</td>' for x in r) + '</tr>')
    h.append('</table>')
    return "".join(h)

# ============================================================ #
#  组装                                                         #
# ============================================================ #

html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>实证总结报告 · 文献综述 · 回归解读 · SDI 诊断（2026-08-19）</title>
<style>{CSS}</style>
</head>
<body>
<div class="wrap">

<header>
<h1>实证总结报告：文献综述 · 回归解读 · SDI 诊断</h1>
<div class="meta">
基金经理行为分析研究（五层递进框架 L1–L5）· 总结性报告<br>
数据：400 只主动偏股混合基金 / 222 位经理 / 9,974 基金-季度观测 / 2006–2026（80 个季度）<br>
权威数值源：<code>_v4_benchmark.json</code>（M4 双向聚类 v4 基准）· <code>L3_L1_regression_HONEST_TOWind_2026-08-15.json</code>（H1–H5）· 主文稿 §4.2–§4.4 · 面板实测（2026-08-19）<br>
生成日期：2026-08-19 · 由 <code>_gen_summary_report_2026-08-19.py</code> 可复现生成
</div>
</header>

<div class="toc">
<a href="#s0">§0 摘要：一页看懂全部结论</a>
<a href="#s1">§1 研究问题、数据与覆盖率</a>
<a href="#s2">§2 文献综述：从前景理论到中国证据</a>
<a href="#s3">§3 回归方法：两套规格与三重识别</a>
<a href="#s4">§4 主结果：M4 全系数与递进解释力</a>
<a href="#s5">§5 稳健性：多估计量交叉验证</a>
<a href="#s6">§6 专题：SDI 为什么在 M4 中不显著</a>
<a href="#s7">§7 其他不显著指标的系统性原因</a>
<a href="#s8">§8 证据强度分级（A/C）</a>
<a href="#s9">§9 六维能力排序的客观性与国内评级机构对照</a>
<a href="#s10">§10 总结与边界</a>
</div>

<h2 id="s0">§0 摘要：一页看懂全部结论</h2>
<div class="box key">
<p><b>研究问题：</b>在控制经理背景（L1）、持仓决策（L2）、交易执行（L3）、风险管理（L4）等全部可观测行为后，认知偏差（L5：处置效应 DE / 羊群 LSV / 风险不对称 RA）是否仍独立解释基金业绩？</p>
</div>
<div class="kpi">
<div class="card"><div class="v">RA +0.0731</div><div class="l">t=+3.57***（M4 双向聚类）· A 级最强信号</div></div>
<div class="card"><div class="v">DE −0.0061</div><div class="l">t=−2.99*** · 组内 FE t=−3.64 最接近因果</div></div>
<div class="card"><div class="v">LSV +0.015</div><div class="l">t=+0.77 n.s. · C 级（被同层掩盖+时期依存）</div></div>
<div class="card"><div class="v">ΔR²(L5)=0.022</div><div class="l">同样本口径 · 占 M4 总 R² 的 17%</div></div>
<div class="card"><div class="v">SDI t=−0.00</div><div class="l">M4 完全平坦 · 但 H1/H4 下 t=2.46**/3.09***（§6）</div></div>
</div>
<div class="box">
<p><b>五句话结论：</b></p>
<p>① <b>认知偏差有独立信息，但量级有限</b>——控制全部可观测行为后 L5 仍显著（RA***、DE***），同样本增量 R²≈2.2 个百分点；它不是可观测行为的冗余代理，但也远非业绩的主导因素。</p>
<p>② <b>三重识别给出三种证据性质</b>：截面（基金间排序）RA 强；前向预测（排反向因果）RA t=10.51***、DE t=−7.11***；组内 FE（最接近因果）只有 DE 稳健（t=−3.64***）——RA/LSV 是"分型变量"（哪些基金好），DE 是"行为效应"（改行为→改业绩）。</p>
<p>③ <b>中国语境的两条独立发现</b>：主动份额 AS 显著负而行业偏离 ICI 显著正——"主动的方向说了算，主动的量反而拖累"（与美股 Active Share 溢价相反）；机构呈<b>反向处置</b>（PGR 0.659 &lt; PLR 0.785，de=−0.126：更倾向卖亏持赢的反面——果断止损）。</p>
<p>④ <b>不显著 ≠ 无信息</b>：SDI/TO/HHI/RV/LSV 的不显著各有明确机制（构念正交、共线吸收、覆盖率、通道 vs 信号），其中 SDI 的"失效"恰好证明 FF5 调整剥离了风格择时收益（§6 专题）。</p>
<p>⑤ <b>诚实边界</b>：Oster δ 全负（遗漏变量稳健性不成立）；IV 在诚实面板不可复现（作废）；LSV 选择敏感；DE 效度边界=46.6% 有全持仓数据的子群。全部推断为预测关联而非因果。</p>
</div>

<h2 id="s1">§1 研究问题、数据与覆盖率</h2>
<p class="lead">面板由 <code>run_full.py</code> 一键重建（10 步数据处理 + 回归），无未来泄漏：所有行为指标只用截至当季可得的持仓/净值/交易数据。样本为<b>全部混合型主动基金</b>（偏股 307 / 灵活 92 / 平衡 1），无货币、债券、指数与 FOF——这是"主动股基画像"研究口径。</p>
{svg_cov()}
<div class="box info">
<p><b>覆盖率三梯队：</b>① L1/L4/因变量 ≈92–100%（净值与管理人数据完备）；② L2 持仓类与 LSV ≈92–94%（持仓明细快照 + 交易方向数据）；③ 约束项——TO_wind 86.6%、RA 72.0%、SDI 63.8%、DE 46.6%。M4 要求全变量交集，N=2,264（22.7%），这一样本收缩本身构成 DE 的选择性审计议题（§7）。</p>
</div>

<h2 id="s2">§2 文献综述：从前景理论到中国证据</h2>

<h3>2.1 理论基础：前景理论 → 三个认知偏差</h3>
<p>Kahneman &amp; Tversky 前景理论的三个特征各自对应 L5 的一个指标，构成统一理论骨架：</p>
<table>
<tr><th>前景理论特征</th><th>行为含义</th><th>对应指标</th><th>文献源头</th></tr>
<tr><td>参考点依赖</td><td>盈亏状态影响卖出决策</td><td>处置效应 DE</td><td>Shefrin &amp; Statman (1985)；Frazzini (2006) 应用于基金</td></tr>
<tr><td>损失规避</td><td>盈亏两侧风险承担不对称</td><td>风险不对称 RA</td><td>Brown, Harlow &amp; Starks (1996) 锦标赛理论</td></tr>
<tr><td>决策从众（信息瀑布）</td><td>基金集体趋同交易</td><td>羊群效应 LSV</td><td>Lakonishok, Shleifer &amp; Vishny (1992)；Wermers (1999)</td></tr>
</table>

<h3>2.2 国际文献的五条主线</h3>
<table>
<tr><th>主线</th><th>代表文献</th><th>核心发现</th><th>本文对应层</th></tr>
<tr><td>因子模型与业绩评价</td><td>CAPM → Fama-French (1993) → Carhart (1997) → FF5 (2015)</td><td>为"业绩"提供风险调整基准（本文因变量=FF5 alpha）</td><td>DV</td></tr>
<tr><td>经理特征</td><td>Gottesman &amp; Morey (2006)；CFA 持证研究</td><td>顶尖商学院/CFA 与业绩关联证据不一致</td><td>L1</td></tr>
<tr><td>可观测行为指标</td><td>Cremers &amp; Petajisto (2009) Active Share；Carhart (1997) 换手率；Chan, Chen &amp; Lakonishok (2002) 风格漂移</td><td>美股：高 Active Share 溢价；高换手损害业绩；风格漂移者风险调整后不占优</td><td>L2/L3</td></tr>
<tr><td>认知偏差</td><td>Frazzini (2006) 处置；LSV (1992)/Wermers (1999) 羊群；Gervais &amp; Odean (2001) 过度自信</td><td>处置折价、羊群的信息效率两面性</td><td>L5</td></tr>
<tr><td>风险承担与锦标赛</td><td>Brown et al. (1996)</td><td>年中输家下半年加大风险（"输家冒险"）</td><td>L4/L5(RA)</td></tr>
</table>

<h3>2.3 中国市场的证据与差异</h3>
<p>国内研究已形成较丰富的证据链：基金业绩持续性弱；羊群交易显著存在；<b>反向处置</b>（机构 PGR&lt;PLR，与散户相反）；锦标赛/排名压力驱动风险调整与风格漂移加剧（期中排名靠后→下半年漂移加剧、熊市更甚），但冒险不改善业绩。</p>
<div class="box">
<p><b>本文的两条中国语境贡献：</b></p>
<p>① <b>AS 折价 vs ICI 溢价</b>：主动份额 AS 在 M4 中 β=−0.030（t=−2.81***）而行业偏离 ICI β=+0.018（t=+3.74***）——与美股"Active Share 溢价"（Cremers &amp; Petajisto 2009）方向相反，说明在中国主动股基中"有观点的行业下注"创造 alpha、"为偏离而偏离"只是噪声，L2 由此拆成"方向"与"量"两个独立信号。</p>
<p>② <b>RA 的方向</b>：中国经理盈利期风险承担不对称（均值 +0.035）与锦标赛"输家冒险"（预测亏损侧加风险）方向不同，且是三者中预测力最强者——为风险承担文献提供新经验证据。</p>
</div>

<h3>2.4 四大文献缺口与本文回应</h3>
<table>
<tr><th>缺口</th><th>文献现状</th><th>本文回应</th></tr>
<tr><td>① 可观测行为与认知偏差割裂</td><td>两类研究互不控制对方变量</td><td>M0→M4 递进：控制全部 L1–L4 后检验 L5 增量</td></tr>
<tr><td>② 单一指标缺乏系统性</td><td>一次只研究一个行为</td><td>五层 18 变量同框竞争</td></tr>
<tr><td>③ 中国认知偏差证据不足</td><td>样本期短、指标零散</td><td>2006–2026 长面板 + 真算指标</td></tr>
<tr><td>④ 递进框架缺失</td><td>无"背景→持仓→交易→风险→偏差"逻辑链</td><td>五层递进设计 + 增量 R² 分解</td></tr>
</table>

<h2 id="s3">§3 回归方法：两套规格与三重识别</h2>

<h3>3.1 因变量：两种口径回答不同问题</h3>
<div class="grid2">
<div class="box info">
<p><b>M4（v4 基准）：</b>DV = <code>ff5_adj_return</code>——第一阶段对每只基金做 FF5 时序回归取截距（Jensen's α）。回答"<b>风格中性的选股能力</b>由什么决定"。混合 OLS + 年份哑变量 C(year)，<b>无基金 FE</b>。</p>
</div>
<div class="box info">
<p><b>H1–H5（HONEST 稀疏规格）：</b>DV = <code>quarter_return</code>（原始季收益）。基金 FE demeaning + 年份哑变量。回答"<b>原始收益</b>（含风格暴露回报）由什么决定"，为 L3 层指标（SDI/TO）设计。</p>
</div>
</div>
<div class="box warn">
<p><b>口径纪律（必须遵守）：</b>两套规格研究问题不同、结论同时成立、<b>严禁混用或合并</b>。M4 中 SDI 近零（t≈−0.00）、TO_wind 不显著（t≈1.07）；H1–H5 中 SDI 显著（t≈2.46）、TO_wind 边际（t≈1.78）——这不是矛盾，而是"风格漂移的收益回报是因子层面的，不是 alpha 层面的"（§6 详解）。</p>
</div>

<h3>3.2 三重识别策略（L5 专设）</h3>
<table>
<tr><th>策略</th><th>识别逻辑</th><th>排除的干扰</th><th>样本</th></tr>
<tr><td>截面回归</td><td>基金层均值横比</td><td>—（基础关联）</td><td>N=200（控制规模）/ 362</td></tr>
<tr><td>前向预测</td><td>当期行为 → 未来 4/1 季收益</td><td>同期反向因果</td><td>N=1,355</td></tr>
<tr><td>组内双向 FE</td><td>同一基金偏离自身均值时业绩是否变化</td><td>所有不随时间变的基金特征（最接近因果）</td><td>N=1,642 / 302 基金</td></tr>
</table>

<h3>3.3 M4 技术细节（可复现性锚点）</h3>
<div class="box">
<p>① 全变量（含 FF5 五因子与被解释变量）1%/99% 缩尾；② 标准误采用<b>基金×年份双向聚类</b>（Cameron-Gelbach-Miller 2011，手写实现已与 linearmodels 金标准交叉验证：同方差口径 SE/t 差异 0.00%）；③ 年份哑变量吸收宏观冲击；④ N=2,264 / 348 基金 / R²=0.1290 / Adj.R²=0.1189；⑤ v4 基准 JSON 二次重跑逐字段差=0.0（完全可复现）。</p>
</div>

<h2 id="s4">§4 主结果：M4 全系数与递进解释力</h2>

<h3>4.1 M4 森林图（18 变量一览）</h3>
{svg_forest(M4, "M4 全系数森林图：L1–L5 行为与控制变量（双向聚类 t2w）", -0.06, 0.12)}
{svg_forest(FF5, "M4 森林图（续）：FF5 因子载荷", -0.20, 0.10, note="FF5 因子载荷刻画样本基金整体的风格暴露结构（HML 正、CMA/RMW 负：偏向价值与高投资风格），系控制变量而非行为发现。")}

<h3>4.2 M4 完整系数表</h3>
{m4_table()}
<p class="muted">注：t2w=基金×年份双向聚类（主口径）；t1w=单维基金聚类（对照列）。TO_wind/SDI/tenure 的 β 与 SE 量级为 10⁻³–10⁻⁶ 级，表内以 6 位小数显示。*** p&lt;0.01, ** p&lt;0.05, * p&lt;0.1。</p>

<h3>4.3 怎么读这张表：显著与不显著的分野</h3>
<div class="box ok">
<p><b>显著组（6 个 A 级）：</b>ICI +（行业下注有观点）、ARG +（主动风险管理）、RA +（风险不对称溢价）、AS −（主动份额折价）、DE −（果断止损溢价）、log_fund_age −（老基金 alpha 衰减）。</p>
</div>
<div class="box warn">
<p><b>不显著组（6 个 C 级）：</b>SDI（§6 专题）、TO_wind（换手成本侵蚀弱）、industry_hhi（与 ICI 共线被吸收）、return_volatility（通道非信号）、LSV（被同层掩盖+时期依存）、tenure（任期无关）。<b>每一个"不显著"都有可诊断的机制，不是随机噪声</b>（§7）。</p>
</div>

<h3>4.4 递进解释力：五层各贡献多少</h3>
{svg_r2()}
<div class="box">
<p><b>递进读法：</b>控制+FF5 仅解释 1.5%；加 L1 背景到 4.3%；加 L2 持仓跳到 8.7%（<b>单层增量最大</b>——持仓结构是最强信息层）；加 L3/L4 到 9.4%；加 L5 认知偏差到 12.9%。同样本口径下 L5 增量 ΔR²=0.0221（若直接比较 M3→M4 全样本为 0.0352，但两者样本不同须用同样本校正）。<b>L2 与 L5 是"方向感"的两级：先有持仓观点（ICI），后有行为纪律（DE/RA）。</b></p>
</div>

<h3>4.5 L5 三指标的三重识别结果</h3>
<table>
<tr><th>指标</th><th>截面（N=200）</th><th>前向 4 季（N=1,355）</th><th>前向 1 季</th><th>组内 FE（N=1,642）</th></tr>
<tr><td><b>RiskAsym</b></td><td class="num sig pos">+0.205 (4.55)***</td><td class="num sig pos">+0.313 (10.51)***</td><td class="num ns">−0.064 (−1.14) n.s.</td><td class="num ns">−0.076 (−1.29) n.s.</td></tr>
<tr><td><b>DE</b></td><td class="num sig neg">−0.057 (−3.28)***</td><td class="num sig neg">−0.056 (−7.11)***</td><td class="num sig neg">−0.071 (−4.81)***</td><td class="num sig neg">−0.041 (−3.64)***</td></tr>
<tr><td><b>LSV</b></td><td class="num ns">+0.004 (0.06) n.s.</td><td class="num ns">+0.057 (1.81) n.s.</td><td class="num ns">+0.110 (1.61) n.s.</td><td class="num ns">−0.005 (−0.15) n.s.</td></tr>
</table>
<p class="muted">注：截面为基金层均值回归（控制规模，HC1）；前向含年份 FE 与控制变量、基金层聚类；组内为基金+年份双向 FE。</p>
<div class="box key">
<p><b>证据性质的分化（本研究最重要的方法论发现之一）：</b></p>
<p>① <b>DE 是唯一的全维度显著者</b>——截面***、前向***、组内***。同一基金在更果断止损的季度业绩更高，这是最接近"行为→业绩"因果链的证据。</p>
<p>② <b>RA 是最强的分型预测因子</b>——截面/前向极强（t=10.51），但组内 FE 不显著：它的预测力来自<b>基金之间稳定的特征差异</b>（RA 高的基金是"另一类基金"），而非基金内实时波动。应理解为"持续性特征的前瞻排序能力"。</p>
<p>③ <b>LSV 全面不显著</b>——但其不显著有明确结构（§7.1）：被同层强信号掩盖 + 时期依存 + 样本选择敏感。</p>
</div>

<h2 id="s5">§5 稳健性：多估计量交叉验证</h2>

<h3>5.1 L5 三指标 × 七种估计量矩阵</h3>
{l5_matrix_table()}
<p class="muted">行=指标，列=估计量（截面/前向/组内/M4 面板/WCB-S 野生聚类自助/500 次置换/Fama-MacBeth 稀疏 4 变量、20 季）。红=正向显著，绿=负向显著，灰=不显著。</p>
{svg_bullbear()}

<h3>5.2 其余稳健性证据摘要</h3>
<table>
<tr><th>检验</th><th>设计</th><th>RiskAsym</th><th>DE</th><th>LSV</th></tr>
<tr><td>野生聚类自助 WCB-S</td><td>聚类 348、Rademacher 权重、修正 H₀</td><td class="num sig pos">p=0.000 ***</td><td class="num sig neg">p=0.014 **</td><td class="num ns">p=0.229 n.s.</td></tr>
<tr><td>置换检验</td><td>500 次、two-way t</td><td class="num sig pos">p=0.020 *</td><td class="num sig neg">p=0.047 *</td><td class="num ns">p=0.507 n.s.</td></tr>
<tr><td>Fama-MacBeth（稀疏）</td><td>20 季截面（2016Q4–2026Q2）</td><td class="num sig pos">+0.0549 (2.18)**</td><td class="num ns">−0.0049 (−1.57) n.s.</td><td class="num ns">+0.0043 (0.27) n.s.</td></tr>
<tr><td>规范曲线（60 设定）</td><td>控制/FE/DV 组合</td><td class="num">43/60 显著</td><td class="num">52/60 显著</td><td class="num">34/60 显著</td></tr>
<tr><td>中介：TO_wind 渠道</td><td>Baron-Kenny + Bootstrap 500</td><td colspan="3" class="ns">三路径 b 系数均不显著（t=−0.70）——<b>换手率不是传导中介</b></td></tr>
<tr><td>中介：收益波动率渠道</td><td>同上</td><td colspan="3">RA、DE 两路径显著（5%）；LSV 路径不显著（p=0.16）——<b>波动率是传导中介</b></td></tr>
<tr><td>Oster δ（遗漏变量界）</td><td>敏感性分析</td><td class="num ns">−1.65</td><td class="num ns">−2.87</td><td class="num ns">−2.66</td></tr>
<tr><td>RESET / 非线性</td><td>二次项与函数形式</td><td colspan="3">RESET F=1.79 (p=0.168) 不拒线性；RA 倒 U 型仅边际（拐点 0.164）</td></tr>
</table>
<div class="box warn">
<p><b>诚实披露（三条）：</b>① Oster δ 全负——"对不可观测遗漏变量稳健"的更强声称<b>不成立</b>，关联部分由可观测行为中介；② IV/2SLS 在诚实面板下工具变量交集塌缩（iv_N=0），全部 IV 数值<b>作废不得引用</b>；③ FM 全 18 控制口径下三指标均不显著（逐季 18 维控制致截面功效不足），RA 的 A 级以 M4 双向聚类为准。</p>
</div>

<h2 id="s6">§6 专题：SDI 为什么在 M4 中不显著</h2>

<h3>6.1 SDI 的构造与数据真相</h3>
<div class="box">
<p><b>定义：</b>风格漂移指数 SDI = 对基金季收益做 8 季滚动 OLS（对 4 个风格指数）得到风格权重向量的<b>相邻期曼哈顿距离</b>：SDI<sub>t</sub> = Σ<sub>k=1..4</sub> |ŵ<sub>k,t</sub> − ŵ<sub>k,t−1</sub>|。它度量"组合风格暴露随时间变动的幅度"，属 L3 交易执行层（与 ARG 的区分：SDI 变的是"持有什么风格"，ARG 变的是"承担多少风险"，二者相关仅 +0.06、近似正交）。</p>
</div>
{svg_sdi_year()}
<p><b>关键数据事实：</b>面板实测显示 SDI 在 2017–2021 恒为 0（结构零），真实变异仅存在于 2022 年起（均值 0.19–0.43）。成因：风格指数数据起点 + 8 季窗口预热的机械结果——这些零<b>不是"无漂移"的测量，而是"未测量"</b>。</p>

<h3>6.2 三规格实证全景</h3>
{svg_sdi_spec()}

<h3>6.3 五个机制：为什么恰好是 M4 归零</h3>
<div class="box key">
<p><b>机制①（最核心）：因变量口径的"构念正交"——FF5 调整恰好剥离 SDI 的收益通道。</b></p>
<p>推理链：SDI 度量的是组合<b>风格暴露的变化</b>；而风格暴露变化的收益体现为 FF5 因子载荷的变化——大盘/小盘、价值/成长之间切换赚到的钱是<b>因子层面的钱</b>。M4 的因变量 ff5_adj_return 是第一阶段 FF5 时序回归的<b>截距 α</b>：因子层面的收益已被载荷吸收，α 只保留风格中性的选股能力。于是"漂移多"与"α 高"在构造上近乎正交。反证完美自洽：把因变量换成原始季收益（H1/H4），SDI 立刻显著（t=2.46**/3.09***）。<b>一句话：SDI 的信息是"风格择时能力"，而 α 只度量"选股能力"——前者被因变量设计过滤掉了。</b></p>
</div>
<div class="box">
<p><b>机制②：全控制集吸收漂移的实现路径。</b>风格漂移的实现手段就是调仓（换手）与改变风险暴露（ARG/RV）、并伴随持仓结构变化（AS/ICI）。M4 同时控制 L2+L4 共 6 个行为变量后，SDI 的"残余独立信号"所剩无几。证据分级表对此的判词即"被 L2/L4 吸收"。注意 SDI 与 ARG 相关仅 +0.06（非简单共线），吸收是广义的信息重叠而非 VIF 意义上的共线。</p>
<p><b>机制③：结构零膨胀 → 衰减偏误。</b>M4 样本内 2017–2021 的观测（约 14%）携带 SDI=0 的"伪零"：把"未测量"当"零漂移"引入经典测量误差，系数向零收缩。对照 H1（基金 FE）的识别同样只来自 2022+ 的组内变异，但 H1 没有全控制集稀释，信号得以显现。</p>
<p><b>机制④：组内 vs 组间变异的识别差异。</b>H1 含基金 FE demeaning，识别来自"同一基金漂移加大的季度收益是否更高"（组内时序）；M4 无基金 FE，系数主要靠基金间断面变异。SDI 的经济含义偏向组内（经理自己的择时时点），组间断面排名意义弱。</p>
<p><b>机制⑤：测量噪声。</b>风格权重是 8 季滚动回归的<b>估计量</b>（非观测值），估计噪声 + 季度频 SDI 与半年频持仓快照的频率错配，进一步压低信噪比。</p>
</div>

<h3>6.4 与文献对照：不矛盾，而是互补</h3>
<p>Chan, Chen &amp; Lakonishok (2002) 在美股发现风格漂移者风险调整后业绩不占优（跟踪误差成本）；本文 H1 中 SDI 对原始收益显著为<b>正</b>（中国市场风格轮动快，适度漂移是适应性行为）；M4 中对 α 归零。三个结论各答一问：美股问"漂移者的风格中性业绩"，H1 问"漂移期内的总收益"，M4 问"漂移的选股 α 增量"——<b>中国经理的风格漂移赚的是"风格的钱"，不是"选股的钱"</b>，这与 Chan et al. 的"漂移无 alpha 增量"精神实质一致。</p>
<div class="box ok">
<p><b>SDI 专题结论：</b>SDI 在 M4 中的 t=−0.00 不是"风格漂移不重要"，而是"风格漂移的业绩含义恰好落在 FF5 调整所删除的成分里"。正确表述应为：<b>SDI 是风格择时能力的信号（对原始收益有效），不是选股 alpha 能力的信号（对 alpha 无增量）</b>。任何以 alpha 为因变量的全控制回归都会重现这一结果——它是测量设计的必然，不是样本运气。</p>
</div>

<h2 id="s7">§7 其他不显著指标的系统性原因</h2>
<table>
<tr><th>指标</th><th>M4 t</th><th>不显著的机制</th><th>关键证据</th></tr>
<tr><td><b>LSV 羊群效应</b></td><td class="num ns">+0.77</td><td>被同层强信号掩盖 + 时期依存 + 样本选择敏感</td><td>从 L5 去掉 de/RA 单独放 lsv → +0.027 (t=2.78***)；2022+ 子样本 +0.025 (t=2.03**)、2022 前不显著；仅熊市显著（+0.042, t=2.32）；存活样本偏倚（清盘基金 LSV 高且业绩差）</td></tr>
<tr><td><b>industry_hhi</b></td><td class="num ns">+0.19</td><td>与 ICI 共线，"方向"信息吸收"集中度"信息</td><td>ICI–HHI 相关 +0.84（基金层）/ +0.70（面板），VIF 1.9–3.4；纳入 ICI 后 HHI 归零——"方向 &gt; 集中度"</td></tr>
<tr><td><b>TO_wind 换手率</b></td><td class="num ns">+1.07</td><td>量级极小 + 中介路径不显著 + 频率错配</td><td>β=4.5×10⁻⁶（经济量级可忽略）；中介 b 路径 t=−0.70；半年频对季度 DV；单边口径低估（约双边一半）；稀疏 H2 下 t=+1.78* 仅边际</td></tr>
<tr><td><b>return_volatility</b></td><td class="num ns">+0.81</td><td>通道而非信号</td><td>直接预测无信息，但作为中介渠道显著（b=0.028, t=2.42）：RA/DE 经波动率传导</td></tr>
<tr><td><b>mgr_tenure 任期</b></td><td class="num ns">+1.02</td><td>与文献一致：任期长度无稳定业绩关联</td><td>H1 中亦仅 −2.17**（微弱负向）；经理特征研究证据本就不一致</td></tr>
<tr><td><b>log_aum 规模</b></td><td class="num ns">+1.05</td><td>口径依赖</td><td>M4 不显著但 H1 中 +2.71***：规模效应对"原始收益"存在、对"alpha"被控制集吸收</td></tr>
</table>
<div class="box info">
<p><b>不显著的四类通用机制（写作与审稿答辩可用）：</b>① <b>共线吸收</b>（HHI←ICI）；② <b>构念与因变量正交</b>（SDI 的风格收益被 α 剥离）；③ <b>测量与覆盖</b>（SDI 结构零、DE 46.6%、频率错配→衰减）；④ <b>条件依存</b>（LSV 的时期/市场状态/同层掩蔽）。<b>区分"真无效"与"被设计过滤"是不显著指标解读的核心纪律。</b></p>
</div>

<h2 id="s8">§8 证据强度分级（A/C）</h2>
{grade_table()}
<p class="muted">分级口径：A=双向聚类***且跨估计量方向稳健；C=M4 不显著或推断脆弱（详细稳健性索引见《实证结论_证据强度总览_2026-08-16》，本表为单一数据源忠实转引）。无 B 级：指标呈两极分化——要么全口径稳健，要么 M4 归零。</p>

<h2 id="s9">§9 六维能力排序的客观性与国内评级机构对照</h2>

<h3>9.1 "巴菲特 27 &gt; 张坤 24 &gt; 朱少醒 22 &gt; 葛兰 19 &gt; 林奇 18 &gt; 蔡嵩松 15"是怎么算出来的</h3>
<p>六维能力雷达的每一维都锚定一条显著回归证据（高=好）：行业配置力（ICI +0.044***）/ 风险应对力（RA +0.113***)/ 主动收益力（ARG 双证据***)/ 投资纪律性（−de −0.070***)/ 风险转化力（RV 双证据***)/ 成本控制力（−TO 概念）。六位经理在每维上的 1–5 序数由<b>公开披露的持仓/换手/风格事实定性映射</b>（如张坤重注消费白酒→行业配置力 5；蔡嵩松高换手→成本控制力 1），综合得分=六维等权求和（满分 30）。</p>

<h3>9.2 这个排序客观吗——一半客观，一半示意</h3>
<div class="grid2">
<div class="box ok">
<p><b>客观成分（可核验）：</b></p>
<p>① 六维的方向（高=好）由回归系数符号锚定，非拍脑袋选维；</p>
<p>② 序数定位的输入是公开事实（持仓集中度、换手高低、任职时长），文献综述文档已附逐条来源链接；</p>
<p>③ "面积=能力"的逻辑成立前提（每维有据）已被 v4 回归验证。</p>
</div>
<div class="box warn">
<p><b>主观边界（必须声明）：</b></p>
<p>① 序数 1–5 是<b>定性映射</b>，换评分者可能差 ±1 级，排序对边界敏感（24 vs 22 的差距在测量误差之内）；</p>
<p>② 六维<b>等权求和</b>无最优性论证（权重任意）；</p>
<p>③ <b>样本内仅 1/6</b>：蔡嵩松的基金（6025，26 季）在面板内，其余五位（含巴菲特/林奇两位美股经理）<b>不在 400 只样本内</b>——跨市场、跨时代、跨基准的序数不可直接比较；</p>
<p>④ <b>存活偏差</b>：六位皆为事后成功者，"选案例"这一步本身看结果；</p>
<p>⑤ 业绩未直接入维：排序 ≠ 业绩排序（葛兰 2019–2021 业绩顶尖但行为短板多、综合分仅 19）。</p>
</div>
</div>
<div class="box key">
<p><b>定性结论：</b>该排序是<b>"证据锚定的示意性排序"（evidence-anchored illustrative ranking）</b>——维度与方向客观、序数与合成主观。它的正确用途是展示"什么样的行为组合对应什么样的能力结构"（教学与直觉锚定），<b>不可作为投资排序或统计推断</b>。若需严格排名，应回到全样本面板按 A 级指标（ICI/ARG/RA/DE）分位数打分。</p>
</div>

<h3>9.3 国内有没有类似机构？他们怎么给基金经理打分排序</h3>
<p>有，且体系成熟。证监会 2010 年《证券投资基金评价业务管理暂行办法》划定持牌评价机构（晨星中国、银河、海通、招商、上海证券、济安金信、天相等），加上中证报牵头的金牛奖与东方财富旗下天天基金（非持牌但 C 端流量最大），构成国内基金评价的主流格局：</p>
{raters_table()}
<div class="box info">
<p><b>他们与我们的一致与差异：</b></p>
<p>① <b>一致</b>：都认同"多维度"、都用风险调整思想、都做类内比较（他们按基金类型分池，我们按行为分层）。</p>
<p>② <b>根本差异——后视镜 vs 望远镜</b>：国内评级全部以<b>历史净值业绩</b>为核心输入（MRAR/夏普/信息比率+类内百分位），是"用结果评价结果"；我们的六维以<b>行为面板</b>为输入（持仓/交易/风险行为→回归证据），是"用过程解释结果"。前者回答"这只基金过去排第几"，后者回答"什么样的经理行为创造 alpha"。</p>
<p>③ <b>评价对象</b>：持牌机构几乎全部评<b>基金</b>（经理层面仅天天基金等少数，且其经理评分由所管基金业绩代理，存在多经理归因不分、一拖多类型混杂的已知问题）；我们直接以<b>经理行为</b>为单位。</p>
<p>④ <b>输出哲学</b>：星级/评分是面向投资者的<b>筛选工具</b>（监管要求可复现、定期更新）；我们的证据分级（A/C）是面向研究的<b>诚实声明</b>（明确标注哪里不显著、哪里不可外推）。二者互补：评级告诉你"买谁"，行为画像告诉你"为什么"。</p>
</div>

<h2 id="s10">§10 总结与边界</h2>
<div class="box ok">
<p><b>三条可稳妥写进结论的话：</b></p>
<p>① 控制全部可观测行为后，认知偏差仍有独立增量信息（同样本 ΔR²≈0.022，占 M4 R² 的 17%）：RA 是最强的截面/前向分型预测因子（A 级），DE 提供最接近因果的组内证据（A 级，效度边界 46.6% 子群）。</p>
<p>② 中国主动股基的行为结构：行业方向（ICI+）而非偏离总量（AS−）创造 alpha；机构反向处置（PGR&lt;PLR）且果断止损有溢价；风格漂移赚"风格的钱"而非"选股的钱"。</p>
<p>③ 不显著指标均有可诊断机制：SDI 的归零是 FF5 调整的必然（风格择时 vs 选股 alpha 的正交），LSV 是时期依存+同层掩蔽，HHI 被 ICI 吸收——"为什么无效"与"什么有效"同样是本研究的知识产出。</p>
</div>
<div class="box warn">
<p><b>边界（诚实清单）：</b>全部结论为预测关联而非因果（IV 不可复现、Oster δ 全负）；DE 外推限有全持仓数据的 ~46.6% 子群；LSV 为选择敏感的描述性证据；SDI 有效变异仅 2022+（4 年窗口）；案例排序为示意性锚定非统计排名；面板为主动混合型基金，不含指数/债券/清盘基金的全样本外推须谨慎。</p>
</div>

<p class="footnote">报告数字与以下权威源逐字一致：M4=_v4_benchmark.json（v4 双向聚类基准，2026-08-16）；H1–H5=L3_L1_regression_HONEST_TOWind_2026-08-15.json；截面/前向/组内/牛熊/中介/FM=merged_manuscript.html §4.2–§4.4（v4 刷新版）；覆盖率/SDI 逐年=主分析面板_重建_含TOwind.csv（2026-08-19 实测）；证据分级=实证结论_证据强度总览_2026-08-16.html。由 _gen_summary_report_2026-08-19.py 生成，可复现。</p>

</div>
</body>
</html>
"""

with open(OUT, "w", encoding="utf-8") as f:
    f.write(html)

# ---------- 校验 ----------
import re
src = open(OUT, encoding="utf-8").read()
VOID = {"meta", "link", "br", "hr", "img", "input", "source", "area", "base", "col", "embed", "param", "track", "wbr"}
tok = re.findall(r"<(/?)([a-zA-Z][a-zA-Z0-9]*)([^>]*?)(/?)>", src)
stack, errs, counts = [], [], {}
for closing, name, attrs, selfclose in tok:
    n = name.lower()
    counts[n] = counts.get(n, 0) + 1
    if n in VOID or selfclose == "/":
        continue
    if closing == "":
        stack.append(n)
    else:
        if stack and stack[-1] == n:
            stack.pop()
        else:
            errs.append(f"mismatch </{n}> stack_top={stack[-1] if stack else None}")
print("标签计数:", {k: v for k, v in sorted(counts.items())})
print("栈剩余:", stack if stack else "空 OK")
print("错误:", errs[:10] if errs else "无 OK")
print("文件:", OUT, len(src), "字符")
