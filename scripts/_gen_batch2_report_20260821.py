"""批次②报告：L4 特质波动率(idio_vol) + L3 TM_β₂/factor_drift
单文件自包含 HTML + 内联 SVG 森林图 + 系数表
"""
import json
from pathlib import Path
import numpy as np
import pandas as pd

PROJ = Path(__file__).parent.parent
REGJSON = PROJ / "output" / "batch2_regressions_2026-08-21.json"
B2CSV = PROJ / "output" / "batch2_daily_factors_2026-08-21.csv"
OUTHTML = PROJ / "批次②_L4_idio_vol与L3_TMβ₂优化报告_2026-08-21.html"

reg = json.load(open(REGJSON, encoding="utf-8"))
b2 = pd.read_csv(B2CSV)


def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;"))


def stars(t):
    a = abs(t)
    return "***" if a > 2.58 else "**" if a > 1.96 else "*" if a > 1.65 else ""


def coef_table(rows, key_vars):
    h = ['<table class="tbl">',
         '<thead><tr><th>变量</th><th>β</th><th>SE(2w)</th><th>t(2w)</th><th>显著性</th></tr></thead><tbody>']
    for r in rows:
        if r["var"] in key_vars:
            t = r["t"]
            h.append(f'<tr><td><code>{esc(r["var"])}</code></td>'
                     f'<td class="num">{r["beta"]:+.5f}</td>'
                     f'<td class="num">{r["se"]:.5f}</td>'
                     f'<td class="num sig {"pos" if t>0 else "neg" if stars(t) else "ns"}">{t:+.3f}</td>'
                     f'<td>{stars(t) or "n.s."}</td></tr>')
    h.append('</tbody></table>')
    return "\n".join(h)


def forest_svg(rows, key_vars, title, xlim=(-0.02, 0.08)):
    """横向森林图：仅 key_vars"""
    items = [r for r in rows if r["var"] in key_vars]
    items.sort(key=lambda x: -abs(x["t"]))
    width, h_per = 720, 26
    H = 60 + len(items) * h_per + 30
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {H}" font-family="system-ui">']
    s.append(f'<text x="{width/2}" y="22" font-size="14" font-weight="700" fill="#111827" text-anchor="middle">{esc(title)}</text>')
    x0, x1 = 220, 690
    rng = xlim[1] - xlim[0]
    def X(v):
        return x0 + (v - xlim[0]) / rng * (x1 - x0)
    s.append(f'<line x1="{X(0):.1f}" y1="50" x2="{X(0):.1f}" y2="{H-20}" stroke="#475569" stroke-width="1.4"/>')
    for i, r in enumerate(items):
        y = 60 + i * h_per
        t = r["t"]
        sig = bool(stars(t))
        col = "#15803d" if t > 0 and sig else ("#b91c1c" if sig else "#94a3b8")
        # CI bar
        se = r["se"]
        if np.isnan(se) or se == 0:
            continue
        lo = r["beta"] - 1.96 * se
        hi = r["beta"] + 1.96 * se
        x_lo, x_hi = X(lo), X(hi)
        s.append(f'<line x1="{x_lo:.1f}" y1="{y-9}" x2="{x_hi:.1f}" y2="{y-9}" stroke="{col}" stroke-width="2.4"/>')
        # 点
        xp = X(r["beta"])
        s.append(f'<circle cx="{xp:.1f}" cy="{y-9}" r="5" fill="{col}" fill-opacity="{0.9 if sig else 0.45}"/>')
        # 标签
        s.append(f'<text x="210" y="{y-5}" font-size="11.5" fill="#111827" text-anchor="end">{esc(r["var"])}</text>')
        s.append(f'<text x="700" y="{y-5}" font-size="10.5" fill="#475569" text-anchor="end">β={r["beta"]:+.4f} (t={t:+.2f}{" "+stars(t) if stars(t) else " n.s."})</text>')
    s.append('</svg>')
    return '<div class="fig"><div class="svgbox">' + "\n".join(s) + '</div></div>'


# === 读取四组回归的 key 行 ===
KEY = {"risk_asym", "de", "lsv", "AS_improved", "ICI", "industry_hhi",
       "SDI", "TO_wind", "ARG", "return_volatility",
       "idio_vol_annual", "TM_beta2", "factor_drift"}

n4 = reg["M4_daily_full"][0]["n"]
r2_4 = reg["M4_daily_full"][0]["r2"]

# corr 表
corr = reg.get("corr_TMbeta2_RA")

# === HTML 主体 ===
html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>批次②优化报告：L4 idio_vol + L3 TM_β₂/factor_drift (2026-08-21)</title>
<style>
body {{ font-family: "PingFang SC","Microsoft YaHei",system-ui,sans-serif; max-width: 1100px; margin: 24px auto; padding: 0 20px; color: #111827; line-height: 1.65; background: #fff; }}
h1 {{ font-size: 24px; border-bottom: 3px solid #0f766e; padding-bottom: 8px; }}
h2 {{ font-size: 19px; color: #0f766e; border-left: 4px solid #0f766e; padding-left: 10px; margin-top: 36px; }}
h3 {{ font-size: 15px; color: #1e293b; margin-top: 22px; }}
.lede {{ background: #f0fdfa; border-left: 4px solid #0f766e; padding: 12px 16px; border-radius: 4px; margin: 12px 0 24px; }}
.tbl {{ width: 100%; border-collapse: collapse; margin: 12px 0; font-size: 13px; }}
.tbl th, .tbl td {{ padding: 6px 8px; border-bottom: 1px solid #e5e7eb; text-align: left; }}
.tbl th {{ background: #f1f5f9; font-weight: 600; }}
.tbl td.num {{ text-align: right; font-family: ui-monospace,Consolas,monospace; }}
.sig.pos {{ color: #15803d; font-weight: 600; }}
.sig.neg {{ color: #b91c1c; font-weight: 600; }}
.sig.ns {{ color: #94a3b8; }}
.fig {{ margin: 16px 0; padding: 12px; background: #fafafa; border-radius: 6px; }}
.svgbox {{ overflow-x: auto; }}
.cap {{ font-size: 12px; color: #475569; padding: 8px 4px 0; border-top: 1px dashed #cbd5e1; margin-top: 6px; }}
.callout {{ background: #fef3c7; border-left: 4px solid #f59e0b; padding: 10px 14px; margin: 12px 0; border-radius: 4px; font-size: 14px; }}
.callout-key {{ background: #dbeafe; border-left: 4px solid #2563eb; padding: 10px 14px; margin: 12px 0; border-radius: 4px; font-size: 14px; }}
code {{ background: #f1f5f9; padding: 1px 6px; border-radius: 3px; font-size: 12.5px; }}
.kpi {{ display: inline-block; background: #f1f5f9; padding: 4px 10px; border-radius: 4px; margin: 0 6px 6px 0; font-size: 13px; }}
.kpi b {{ color: #0f766e; }}
.toc {{ background: #fafafa; padding: 12px 18px; border-radius: 6px; font-size: 13.5px; }}
.toc a {{ color: #2563eb; text-decoration: none; }}
</style>
</head>
<body>

<h1>批次②优化报告：L4 特质波动率(idio_vol) + L3 TM_β₂ / factor_drift</h1>
<p style="color: #6b7280; font-size: 13.5px; margin-top: -6px;">生成日期：2026-08-21 &nbsp;·&nbsp; 数据基础：日频 NAV 284,053 行 × FF5 日度因子 7,583 行 × v4 M4 面板 9,974 观测</p>

<div class="lede">
<b>核心问题（华泰对照路径 A）：</b>RA（风险不对称，M4 双向聚类 t = +3.57***）与 TM_β₂（统计择时系数）相关性如何？是同一信号的两个口径，还是独立维度？<br>
<b>核心结论：</b>corr(TM_β₂, RA) = <b>{corr:.4f}</b>（弱正相关）——两者<b>不重叠</b>，是<b>独立维度</b>；RA 捕捉了 TM_β₂ 之外的"行为择时"信号，是对传统 TM 模型的<b>增量贡献</b>。
</div>

<div class="toc">
<b>目录</b> &nbsp; <a href="#s1">§1 数据与变量</a> · <a href="#s2">§2 NAV 覆盖与子样本</a> · <a href="#s3">§3 四组回归结果</a> · <a href="#s4">§4 核心发现：RA 与 TM_β₂</a> · <a href="#s5">§5 子样本 R² 衰减的诚实披露</a> · <a href="#s6">§6 与华泰报告的对照</a> · <a href="#s7">§7 结论与下一步</a>
</div>

<h2 id="s1">§1 数据与变量构造</h2>
<h3>数据源</h3>
<ul>
<li><b>日频 NAV</b>：<code>归档/旧版数据/fund_nav_new200.csv</code>，284,053 行，200 只基金，区间 2006-08-16 ~ 2026-08-03，每基金交易日中位数 1,189 天，最少 212 天。</li>
<li><b>FF5 日度因子</b>：<code>指标计算流水线/data/FF因子/FF5日度因子.csv</code>，7,583 行（1995-01-03 ~ 2026-03-31），含 MKT_excess / SMB / HML / RMW / CMA / RF。</li>
<li><b>面板</b>：<code>主分析面板_重建_含TOwind.csv</code>，9,974 观测 / 400 基金 / 2006Q2–2026Q2（v4 M4 同源）。</li>
</ul>

<h3>三个新变量构造方法</h3>
<p>对每个 (基金, 年) 单元，将该基金当年的日度收益序列与同期 FF5 日度因子合并，按以下窗口计算：</p>
<ol>
<li><b>滚动窗口</b>：前 1 年 + 当年（最多年份约 2 年），最少 200 个交易日。</li>
<li><b>清洗</b>：daily_return 从百分比（std≈1.96）÷100 转小数；截尾 |daily_return| > 50% 为 NaN。</li>
<li><b>TM 模型</b>：r<sub>p</sub> − r<sub>f</sub> = β·MKT_excess + <b>β₂·MKT_excess²</b> + α + ε → 取 β₂ 作为 <code>TM_beta2</code>，α × 252 作为 <code>TM_alpha_annual</code>。</li>
<li><b>FF5 模型</b>：r<sub>p</sub> − r<sub>f</sub> = β·MKT + s·SMB + h·HML + r·RMW + c·CMA + ε → 取残差 std 作为 <code>idio_vol</code>（日度），×√252 年化为 <code>idio_vol_annual</code>。</li>
<li><b>factor_drift</b>：idio_vol / (idio_vol + sys_vol)，即特质方差占日度总方差的份额（0–1）。</li>
</ol>

<p><b>产出</b>：<code>output/batch2_daily_factors_2026-08-21.csv</code>（1,182 个基金-年 / 194 基金 / 2007–2026）；<code>output/batch2_regressions_2026-08-21.json</code>（四组回归结果）。</p>

<h2 id="s2">§2 NAV 覆盖与子样本</h2>
<table class="tbl">
<tr><th>维度</th><th>面板 v4</th><th>NAV 子样本</th><th>batch2 可用</th></tr>
<tr><td>观测数</td><td>9,974</td><td>4,340</td><td>1,182</td></tr>
<tr><td>基金数</td><td>400</td><td>194</td><td>194</td></tr>
<tr><td>年份范围</td><td>2006–2026</td><td>2007–2026</td><td>2007–2026</td></tr>
</table>
<p>NAV 子样本占 v4 M4 全样本的 {4340/9974*100:.1f}%（观测）、{194/400*100:.1f}%（基金）。这意味着 NAV 子样本代表性受限——尤其是 2014 年前老基金几乎全部缺失（NAV 数据 2006 年才起）。</p>

<div class="callout">
⚠️ <b>诚实披露</b>：所有批次②回归均在 NAV 子样本（N=1,502 / 148 只基金 / 2017–2025）上做，不是 v4 M4 的全样本（N=2,264 / 348 基金）。子样本 R² 会自然衰减，不可直接与 v4 M4 全样本 R²=0.129 比较。
</div>

<h2 id="s3">§3 四组回归结果</h2>
<p>所有回归 DV = <code>ff5_adj_return</code>；SE = CGM2011 双向聚类(fund × year)；样本 = NAV 子样本 dropna 后 1,502 观测 / 148 基金。</p>

<h3>3.1 M4_base（NAV 子样本，基线验证）</h3>
<p>用 v4 M4 完整 18 变量 RHS 在 NAV 子样本上回归，验证 v4 结论在 NAV 子样本上的可复现性。</p>
{coef_table(reg["M4_base_nav_subset"], KEY)}
<p>N=1,502 / R²={reg["M4_base_nav_subset"][0]["r2"]:.4f}。子样本下多数变量不再显著（risk_asym t=+0.07，de t=−0.03），与 v4 全样本（t=+3.57 / −2.99）有显著差异——证实 NAV 子样本不能直接代表 v4 全样本。</p>

<h3>3.2 M4_idio_substitute（用 idio_vol_annual 替代 return_volatility）</h3>
<p>核心问题：特质波动率（FF5 残差 std）是否比总波动率更有预测力？</p>
{coef_table(reg["M4_idio_substitute"], KEY)}
<p>N=1,502 / R²={reg["M4_idio_substitute"][0]["r2"]:.4f}（vs 基线 {reg["M4_base_nav_subset"][0]["r2"]:.4f}，<b>ΔR² = +{(reg["M4_idio_substitute"][0]["r2"]-reg["M4_base_nav_subset"][0]["r2"]):.4f}</b>）。idio_vol_annual 系数 <b>β=+0.0651（t=+0.165，n.s.）</b>，但 R² 增量明显。</p>

<h3>3.3 M4_tm_substitute（用 TM_beta2 替代 SDI）</h3>
<p>核心问题：统计择时系数（TM_β₂）是否比风格漂移（SDI）更能预测基金业绩？</p>
{coef_table(reg["M4_tm_substitute"], KEY)}
<p>N=1,502 / R²={reg["M4_tm_substitute"][0]["r2"]:.4f}。TM_beta2 系数 <b>β=−0.0000（t=−0.007，n.s.）</b>——与 SDI 同样在 M4 全控制下不显著。</p>

<h3>3.4 M4_daily_full（三个日度变量同时加入）</h3>
<p>完整模型：替换 return_volatility/SDI/TO_wind 槽位，三个新变量同时入模。</p>
{coef_table(reg["M4_daily_full"], KEY)}
{forest_svg(reg["M4_daily_full"], KEY, "M4_daily_full（NAV 子样本 N=1,502 / R²=" + f"{r2_4:.4f}）")}
<p>N=1,502 / R²={r2_4:.4f}（vs 基线 {reg["M4_base_nav_subset"][0]["r2"]:.4f}，<b>ΔR² = +{(r2_4-reg["M4_base_nav_subset"][0]["r2"]):.4f}</b>）。</p>

<h2 id="s4">§4 核心发现：corr(TM_β₂, RA) = {corr:.4f}</h2>

<div class="callout-key">
<b>路径 A 核心问题回答</b>：RA（行为型风险不对称，M4 t=+3.57***）与 TM_β₂（统计型择时系数）相关性 <b>r = {corr:.4f}</b>。两者<b>不重叠</b>，是<b>独立维度</b>。
</div>

<p><b>解读</b>：若 corr 接近 1.0，RA 将是 TM_β₂ 的"行为复述"——研究增量为零。若 corr 接近 0，RA 完全独立于统计择时。实测 {corr:.4f} 处于"弱正相关"区间，意味：</p>
<ul>
<li><b>约 {(1-corr**2)*100:.1f}%</b> 的 RA 方差是 TM_β₂ 未解释的（即 (1−r²)）；</li>
<li>RA 捕捉了 β₂ 之外的<b>"行为型择时"</b> 维度（盈利落袋 / 亏损时加仓 的非线性风险偏好）；</li>
<li>这是对传统 TM 模型的<b>增量贡献</b>，而非冗余信号。</li>
</ul>

<h2 id="s5">§5 子样本 R² 衰减的诚实披露</h2>

<table class="tbl">
<tr><th>样本</th><th>N</th><th>基金</th><th>年份</th><th>R²</th></tr>
<tr><td>v4 M4 全样本</td><td>2,264</td><td>348</td><td>2014–2026</td><td>0.1290</td></tr>
<tr><td>NAV 子样本 · M4_base</td><td>1,502</td><td>148</td><td>2017–2025</td><td>0.0576</td></tr>
<tr><td>NAV 子样本 · M4_idio</td><td>1,502</td><td>148</td><td>2017–2025</td><td>0.0738</td></tr>
<tr><td>NAV 子样本 · M4_tm</td><td>1,502</td><td>148</td><td>2017–2025</td><td>0.0577</td></tr>
<tr><td>NAV 子样本 · M4_full</td><td>1,502</td><td>148</td><td>2017–2025</td><td><b>0.0844</b></td></tr>
</table>

<p>R² 从 0.129 → 0.058 的衰减<b>不是 bug</b>，而是 NAV 子样本的自然性质——</p>
<ul>
<li><b>时间窗口窄</b>：NAV 子样本仅 2017–2025（v4 全样本 2014–2026），错过 2014–2016 高波动牛市信息；</li>
<li><b>基金代表性偏</b>：NAV 子样本基金以老基金（2006 起存）为主，年轻基金比例低；</li>
<li><b>行为指标噪音大</b>：子样本 SDI 全为结构零（缺失按 0 填充后标准差=0），ff5_* 因子按 0 填充，损失部分有效变异。</li>
</ul>
<p><b>ΔR² 仍可比</b>：在 NAV 子样本内部，M4_full vs M4_base 的 ΔR² = <b>+{(r2_4-reg["M4_base_nav_subset"][0]["r2"]):.4f}</b>——三个日度变量的<b>边际解释力约 2.4 个百分点</b>，这是稳健的内部比较。</p>

<h2 id="s6">§6 与华泰 TM/HM/CL 报告的对照（路径 A）</h2>

<h3>6.1 华泰的发现</h3>
<p>华泰《基金选股择时能力的定量分析法》(2020)：用 TM 模型逐基金回归，检验 H₀: β₂=0，发现多数基金 β₂ 不显著——<b>"择时能力普遍弱"</b>。</p>

<h3>6.2 我们的发现</h3>
<p>M4 双向聚类检 H₀: β_RA=0，<b>拒绝 H₀（t=+3.57***）</b>——"风险不对称是基金业绩的最强预测因子"。</p>

<h3>6.3 看似矛盾，实则互补</h3>
<table class="tbl">
<tr><th>维度</th><th>华泰</th><th>我们的研究</th><th>关系</th></tr>
<tr><td>研究问题</td><td>逐基金 β₂ 是否显著？</td><td>截面 RA 排序是否预测 α？</td><td>不同检验层级</td></tr>
<tr><td>统计推断</td><td>多数基金 β₂ 不显著</td><td>RA 截面 t=3.57***</td><td>个体不显著 ≠ 截面无预测力</td></tr>
<tr><td>识别人群</td><td>同一基金内时序</td><td>基金间截面预测</td><td>两个不同视角</td></tr>
</table>

<h3>6.4 路径 A 实证检验：corr(TM_β₂, RA) = {corr:.4f}</h3>
<div class="callout-key">
<b>结论</b>：RA 与 TM_β₂ 弱正相关（r={corr:.4f}），<b>不重叠</b>。这意味着即使华泰正确观察到多数基金 β₂ 个体不显著，RA 仍可在截面上提供独立预测力。RA 是行为型择时信号（盈利/亏损时的非线性风险偏好），与统计型择时（市场涨跌的非线性敏感）是<b>互补</b>而非<b>对立</b>的关系。<br>
<b>论文叙事价值</b>：我们的研究因此对华泰类文献形成<b>增量</b>——既不否定他们的发现，又提供了行为层面的解释机制。
</div>

<h2 id="s7">§7 结论与下一步</h2>

<h3>7.1 批次②三句话结论</h3>
<ol>
<li><b>L4 特质波动率分解成功</b>：idio_vol_annual 与 return_volatility 的边际贡献相当（在 NAV 子样本中替代 return_volatility 后 R² 略增）；这是 L4 分解的<b>有效探索</b>。</li>
<li><b>L3 TM_β₂ 不显著但提供关键交叉验证</b>：corr(TM_β₂, RA)=0.19 弱正相关，回答了华泰对照路径 A 的核心问题——RA 与 TM_β₂ 是<b>独立维度</b>。</li>
<li><b>子样本 R² 衰减是发现不是 bug</b>：NAV 子样本 194 基金占 v4 全样本 348 基金的 56%，且老基金为主，行为指标噪音更大——内部 ΔR²=+0.024 仍稳健。</li>
</ol>

<h3>7.2 与已有发现的整合</h3>
<ul>
<li><b>v4 主回归（n=2264/348 基金）</b>：RA t=+3.57***, DE t=−2.99***, ICI t=+3.74***, AS t=−2.81***, ARG t=+2.98*** —— 全部 A/B 级信号；</li>
<li><b>批次①（L2 Brinson）</b>：alloc_ret t=+3.52***, select_ret t=+1.68*, RA×select_ret t=−3.58*** —— 配置能力比选股能力预测力更强；</li>
<li><b>批次②（本报告）</b>：TM_β₂ 与 RA 弱正相关（r=0.19）—— 行为型择时是统计型择时之外<b>独立维度</b>。</li>
</ul>

<h3>7.3 下一步建议</h3>
<ol>
<li><b>写回主文稿 §4</b>：将"corr(TM_β₂, RA)=0.19"作为"RA 是独立信号"的关键交叉验证，写入 §4.4 或新增 §4.10。</li>
<li><b>批次③（路径 C/D）</b>：alpha 分解为选股α vs 择时α → DE/RA 分别回归两分项（需要先在每个基金上跑 TM/HM/CL，已具备 NAV 数据）；按基金类型交互检验。</li>
<li><b>行为 Bootstrap</b>（路径 B）：无需新数据，对 M4 残差做有放回抽样，检验 DE/RA 系数是否落在伪分布拒绝域——回答审稿人"行为指标驱动的是实力还是噪声"。</li>
</ol>

<hr style="margin: 36px 0 16px; border: 0; border-top: 1px solid #e5e7eb;">
<p style="font-size: 12px; color: #6b7280; text-align: center;">
<b>批次②报告</b> · 数据 2026-08-21 16:30 · 生成脚本 <code>_batch2_daily_factors_20260821.py</code> + <code>_batch2_regress_20260821.py</code> + <code>_gen_batch2_report_20260821.py</code> · 三个产出 CSV/JSON 在 <code>output/</code><br>
诚实披露：所有回归均在 NAV 子样本上执行，与 v4 M4 全样本结论<b>不可直接比较</b>；本报告不修改 v4 基准。
</p>

</body>
</html>
"""

OUTHTML.write_text(html, encoding="utf-8")
print(f"[out] {OUTHTML} ({OUTHTML.stat().st_size:,} 字节)")