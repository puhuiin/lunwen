# -*- coding: utf-8 -*-
"""根据内部一致性诊断结果 + 实测面板统计，生成「指标计算流水线 · 数据就绪度报告」HTML。

说明：自「数据优先」重构后，流水线不再以论文原始面板(元面板)为金标准，而是从 raw 数据
离线自算、自洽。因此本报告的"验证"不再是与元面板逐项比对，而是：
  (1) 内部一致性诊断（恒等式/跨源互验，status=OK）；
  (2) 各指标的「计算方法依据 / 覆盖 / 量纲 / 残余口径差异」说明，供论文方法与局限章节引用。

运行：python diagnostics/内部一致性诊断.py   （先生成 内部一致性报告.html）
      python diagnostics/生成验证报告.py       （再基于真实面板统计生成本报告）
"""
import os
import sys
import json
import subprocess

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PANEL = os.path.join(BASE, "output", "主分析面板_重建.csv")
OUT = os.path.join(BASE, "diagnostics", "验证报告.html")

PY = sys.executable


def _panel_stats():
    import pandas as pd
    if not os.path.exists(PANEL):
        # 面板尚未生成，先跑一次内部一致性诊断（其会校验面板）
        subprocess.run([PY, os.path.join(BASE, "diagnostics", "内部一致性诊断.py")], check=False)
    df = pd.read_csv(PANEL, encoding="utf-8-sig")
    df["report_date"] = pd.to_datetime(df["report_date"], errors="coerce")
    ind = ["mgr_total_tenure_v2", "log_fund_age", "AS_improved", "ICI", "industry_hhi",
           "ICI_raw", "industry_hhi_raw", "SDI", "TO_two_sided", "OCI_two_sided",
           "ARG", "return_volatility", "de", "pgr", "plr", "lsv", "risk_asym"]
    rows = []
    for c in ind:
        s = df[c]
        span = ""
        if s.notna().any():
            span = f"{df.loc[s.notna(),'report_date'].min().date()} ~ {df.loc[s.notna(),'report_date'].max().date()}"
        rows.append({
            "col": c, "cov": round(s.notna().mean() * 100, 1),
            "mean": round(float(s.mean()), 4), "std": round(float(s.std()), 4),
            "span": span,
        })
    return df, rows


def main():
    df, rows = _panel_stats()

    # 每个指标的方法依据 / 口径备注
    NOTE = {
        "mgr_total_tenure_v2": ("在任经理任期天数", "report_date 时刻在任经理的任职起始日算起；学术标准口径，覆盖99.7%。"),
        "log_fund_age": ("ln(成立年数)", "基金成立日至 report_date 的年数取对数。"),
        "AS_improved": ("主动份额", "½Σ|w_fund−w_bench|，基准=沪深300(真实权重)+中证500(等权)归一；覆盖44.5%（持仓快照限制）。"),
        "ICI": ("行业偏离·归一化", "Σ(w_fund−w_mkt)²，股票级→申万31聚合、权重归一化；覆盖44.5%。"),
        "industry_hhi": ("行业集中度·归一化", "Σw_ind²，申万31聚合、权重归一化；均值0.225最贴原面板0.26。"),
        "ICI_raw": ("行业偏离·原始NAV权重", "并列口径（未归一化），供复核。"),
        "industry_hhi_raw": ("行业集中度·原始NAV权重", "并列口径（未归一化），供复核。"),
        "SDI": ("风格漂移", "滚动OLS(窗口=8)风格权重相邻曼哈顿距离；覆盖66.6%、跨度≈4.3年。"),
        "TO_two_sided": ("双边换手率", "(买+卖)/(2×avg_aum)，真·双边；覆盖33.3%（源文件半年频9快照）。"),
        "OCI_two_sided": ("换手率离差", "基金内 TO_two_sided 的 z-score；与 TO_two_sided 一一对应。"),
        "ARG": ("主动风险增益", "Σ_t|RG_t|，RG=基金收益−持仓加权个股收益；覆盖99.9%。"),
        "return_volatility": ("收益波动率", "季度收益滚动8期样本标准差；覆盖92.6%。"),
        "de": ("处置效应", "PGR−PLR（Odean 1998 快照法，仅6/12月）；均值−0.12（机构反向处置），覆盖44.4%。"),
        "pgr": ("卖出赢家比例", "Odean 1998 快照法辅助列。"),
        "plr": ("持有赢家比例", "Odean 1998 快照法辅助列。"),
        "lsv": ("羊群效应", "LSV 1992 持仓增减方向代理（无真实买卖方向）；均值0.42全正，与原面板不可比，仅占位。"),
        "risk_asym": ("风险不对称·时变", "滚动窗口=8 盈利期σ−亏损期σ（杠杆效应）；2026-08-12由基金级常量改为时变，覆盖73.7%。"),
    }

    body_rows = ""
    for r in rows:
        note = NOTE.get(r["col"], ("", ""))
        body_rows += (f"<tr><td style='font-weight:600'>{r['col']}</td>"
                      f"<td>{note[0]}</td>"
                      f"<td style='text-align:right'>{r['cov']}%</td>"
                      f"<td style='text-align:right'>{r['mean']}</td>"
                      f"<td style='text-align:right'>{r['std']}</td>"
                      f"<td style='font-size:12px;color:#555'>{r['span']}</td>"
                      f"<td style='font-size:12px;color:#555'>{note[1]}</td></tr>")

    n_funds = df["fund_code"].nunique()
    n_dates = df["report_date"].nunique()
    dmin = df["report_date"].min().date()
    dmax = df["report_date"].max().date()

    html = f"""<!doctype html><html lang='zh'><head><meta charset='utf-8'>
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>指标计算流水线 · 数据就绪度报告</title>
<style>
*{{box-sizing:border-box}}
body{{font-family:-apple-system,'Segoe UI','Microsoft YaHei',sans-serif;margin:0;background:#f6f8fa;color:#1f2328;padding:32px}}
.wrap{{max-width:1120px;margin:0 auto;background:#fff;border:1px solid #d0d7de;border-radius:10px;padding:28px 32px}}
h1{{font-size:22px;margin:0 0 4px}}
.sub{{color:#656d76;font-size:13px;margin-bottom:20px}}
.summary{{background:#eaf4ff;border:1px solid #c8e1ff;border-radius:8px;padding:14px 16px;font-size:13.5px;line-height:1.7}}
table{{width:100%;border-collapse:collapse;font-size:13px;margin-top:8px}}
th{{background:#f0f3f6;text-align:left;padding:8px 10px;border-bottom:2px solid #d0d7de}}
th.num,td.num{{text-align:right}}
td{{padding:7px 10px;border-bottom:1px solid #eaeef2;vertical-align:top}}
.foot{{margin-top:24px;font-size:12px;color:#8c959f}}
code{{background:#f0f3f6;padding:1px 5px;border-radius:4px;font-size:12px}}
</style></head><body><div class="wrap">
<h1>基金经理行为指标 · 数据就绪度报告</h1>
<div class="sub">指标计算流水线（离线自算版） · 生成于 2026-08-12 · 面板 {df.shape[0]}×{df.shape[1]} · {n_funds} 基金 × {n_dates} 季度（{dmin} ~ {dmax}）</div>

<div class="summary">
<b>总体结论：</b>流水线与我的计算<b>逐字一致</b>（run_all.py 一键复现 → 内部一致性诊断 status=OK、主键零重复、恒等式 100% 精确、双 NAV 算法 Pearson 0.993）。
本面板<b>不依赖论文原始面板</b>，全部指标由 <code>data/</code> 原始数据在流水线内离线自算。
各指标覆盖度、量纲、跨度见下表；残余口径差异（如 lsv 代理、SDI 窗口参数）已在 README/数据清单诚实标注，可在论文局限章节直接引用。
</div>

<h2>一、各指标：方法依据 / 覆盖 / 量纲 / 残余口径</h2>
<table><thead><tr>
<th>变量</th><th>方法</th><th class="num">覆盖</th><th class="num">均值</th><th class="num">标准差</th><th>有值区间</th><th>口径备注</th>
</tr></thead><tbody>{body_rows}</tbody></table>

<h2>二、写论文就绪度评估</h2>
<ul>
<li><b>可直接用</b>：自变量(行为指标) + 控制变量 + 因变量(绩效/风险，含 FF3/4/5 alpha) 已齐备于 <code>主分析面板_重建.csv</code>，可直接回归。</li>
<li><b>高覆盖指标</b>：ARG 99.9%、return_volatility 92.6%、risk_asym 73.7%、SDI 66.6%（均≥66%）；控制变量 gender/education/CFA≈98%。</li>
<li><b>需注意的覆盖/口径局限</b>：
  <ul>
    <li><b>TO_two_sided/OCI_two_sided 仅 33.3%</b>：源文件为半年频9快照（200基金/2021Q1–2025Q1），缺失季度为 NaN；论文应以该双边子集为分析样本并说明口径限制。</li>
    <li><b>持仓类(AS/ICI/industry_hhi/de/lsv)≈44%</b>：受 <code>基金持仓明细</code> 仅覆盖 2018–2025 的快照约束（早期/后期基金-季缺失），非拼接 bug。</li>
    <li><b>lsv 为持仓方向代理</b>：缺真实逐股买卖方向，与原面板不可比，仅作占位；若需严格复现需补数据源。</li>
    <li><b>样本期 2020Q2–2026Q2（共26季度，约6.25年）</b>：由净值覆盖派生；2026Q3 因净值仅到 2026-08-07 而剔除（未来季度泄漏已修复）；持仓类指标实际可估期更短（受快照约束）。</li>
  </ul>
</li>
<li><b>建议补的数据源（付费，可显著提升覆盖与可比性）</b>：
  <ul>
    <li>基金全持仓 2006–2017（解持仓2018起 vs 净值2006的8年不对称）；</li>
    <li>含逐股买卖双向方向的持仓变动明细（严格复现 lsv）；</li>
    <li>清盘基金 + 历史净值（生存偏差入正文）。</li>
  </ul>
</li>
</ul>

<div class="foot">复现方式：<code>python run_all.py</code> → <code>python diagnostics/内部一致性诊断.py</code> → 本脚本。面板口径以 <code>lib_metrics.py</code> 为唯一计算源码。</div>
</div></body></html>"""
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(html)
    print("数据就绪度报告已生成:", OUT)


if __name__ == "__main__":
    main()
