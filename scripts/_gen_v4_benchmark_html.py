# -*- coding: utf-8 -*-
"""生成 v4 基准回归表 HTML：M4 全 18 RHS 双向聚类权威系数 + 单维基金聚类对照 + L5 置换/WCB p + 增量 R^2。
数据来自 _v4_benchmark.json（_v4_benchmark_table.py 导出）。本文件为全工作区单一真相源，与 merged_manuscript.html / 5层架构完整研究方案.html 口径一致。"""
import os, json

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = json.load(open(os.path.join(HERE, "_v4_benchmark.json"), encoding="utf-8"))
coefs = D["coefs"]
perm_p = D["perm_p"]; wcb_p = D["wcb_p"]
FF5 = D["ff5"]

LABEL = {
    "log_aum": "规模对数 (log AUM)",
    "ff5_MKT_excess": "FF5 市场超额 (MKT)",
    "ff5_SMB": "FF5 规模 (SMB)",
    "ff5_HML": "FF5 价值 (HML)",
    "ff5_RMW": "FF5 盈利 (RMW)",
    "ff5_CMA": "FF5 投资 (CMA)",
    "log_fund_age": "基金年龄对数",
    "mgr_total_tenure_v2": "经理累计任期",
    "AS_improved": "主动持股比 (AS)",
    "ICI": "行业集中度 (ICI)",
    "industry_hhi": "行业 HHI",
    "SDI": "风格漂移 (SDI)",
    "TO_wind": "换手率 (TO_wind)",
    "ARG": "调仓收益缺口 (ARG)",
    "return_volatility": "收益波动率",
    "de": "处置效应 (DE)",
    "lsv": "羊群效应 (LSV)",
    "risk_asym": "风险不对称 (RiskAsym)",
}
GROUP = [
    ("控制变量", ["log_aum"]),
    ("FF5 因子", FF5),
    ("L1 基金经理层", ["log_fund_age", "mgr_total_tenure_v2"]),
    ("L2 持仓偏离层", ["AS_improved", "ICI", "industry_hhi"]),
    ("L3 交易行为层", ["SDI", "TO_wind"]),
    ("L4 收益特征层", ["ARG", "return_volatility"]),
    ("L5 行为指标层（核心）", ["de", "lsv", "risk_asym"]),
]

def star(p):
    if p > 0.10: return ""
    if p > 0.05: return "*"
    if p > 0.01: return "**"
    return "***"

def fmt_p(p):
    if p < 0.001: return "&lt;0.001"
    return "%.3f" % p

# 按 rhs_order 保证顺序
order = D["rhs_order"]
# 重排 group 内部按 order
pos = {v: i for i, v in enumerate(order)}

rows_html = []
for gname, gvars in GROUP:
    rows_html.append('<tr class="group-row"><td colspan="9">%s</td></tr>' % gname)
    for v in sorted(gvars, key=lambda x: pos.get(x, 99)):
        c = coefs[v]
        st = star(c["p2w"])
        cls = ' class="signif"' if st and v in ("de", "lsv", "risk_asym") else ""
        # L5 额外列
        if v in perm_p:
            extra = '<td>%.3f</td><td>%.3f</td>' % (perm_p[v], wcb_p[v])
            extra_h = '<th>置换 p</th><th>WCB p</th>'
        else:
            extra = '<td>—</td><td>—</td>'
            extra_h = '<th>置换 p</th><th>WCB p</th>'
        rows_html.append(
            '<tr%s><td>%s</td><td>%+.5f</td><td>%.5f</td><td>%+.2f</td><td>%s</td>'
            '<td>%s</td><td>%.5f</td><td>%+.2f</td><td>%s</td>%s</tr>'
            % (cls, LABEL.get(v, v), c["beta"], c["se2w"], c["t2w"], fmt_p(c["p2w"]), st,
               c["se1w"], c["t1w"], fmt_p(c["p1w"]), extra)
        )
# 注：置换/WCB 列头需补到 thead。这里在 thead 动态加。

thead = ('<tr><th>变量</th><th>β</th><th>SE(双向)</th><th>t(双向)</th><th>p(双向)</th>'
         '<th>显著性</th><th>SE(单维)</th><th>t(单维)</th><th>p(单维)</th>'
         '<th>置换 p</th><th>WCB p</th></tr>')

html = """<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>M4 基准回归表（v4 双向聚类）· 2026-08-16</title>
<style>
* {{ box-sizing: border-box; }}
body {{ font-family: -apple-system, "Segoe UI", "Microsoft YaHei", sans-serif; margin: 0; padding: 32px; color: #1a1a1a; background: #fafafa; line-height: 1.65; }}
h1 {{ font-size: 22px; margin: 0 0 6px; }}
.sub {{ color: #666; font-size: 13px; margin-bottom: 18px; }}
.callout {{ background: #eef6ff; border-left: 4px solid #2b7de9; padding: 12px 16px; border-radius: 6px; margin: 16px 0; font-size: 13.5px; }}
.callout.warn {{ background: #fff7e6; border-color: #fa8c16; }}
.callout.danger {{ background: #fff1f0; border-color: #cf1322; }}
table {{ border-collapse: collapse; width: 100%%; background: #fff; font-size: 13px; box-shadow: 0 1px 3px rgba(0,0,0,.08); }}
th, td {{ border: 1px solid #e4e4e4; padding: 7px 9px; text-align: right; }}
th:first-child, td:first-child {{ text-align: left; }}
thead th {{ background: #2b3a4a; color: #fff; position: sticky; top: 0; }}
.group-row td {{ background: #f0f3f7; font-weight: 600; text-align: left; color: #2b3a4a; }}
tr.signif td {{ background: #f6fff8; }}
.stars {{ color: #cf1322; font-weight: 700; }}
.footnote {{ color: #777; font-size: 12px; margin-top: 12px; }}
.bad {{ color: #cf1322; }}
code {{ background: #f0f0f0; padding: 1px 5px; border-radius: 4px; font-size: 12px; }}
</style></head><body>
<h1>M4 基准回归表 · v4 双向聚类（CGM 2011）权威值</h1>
<div class="sub">单一真相源 · 生成于 2026-08-16 · 与 <code>merged_manuscript.html</code> / <code>5层架构完整研究方案.html</code> 口径完全一致</div>

<div class="callout">
<strong>模型规格</strong>：因变量 <code>ff5_adj_return_w</code>（FF5 五因子模型残差，已缩尾）；
RHS = 18 个解释变量（规模控制 + FF5 五因子 + L1 经理层 + L2 持仓偏离层 + L3 交易行为层 + L4 收益特征层 + L5 行为指标层）；
全部变量经 <strong>1%%/99%% 双向缩尾</strong>；含年份固定效应 <code>C(year)</code>。
样本 N = <strong>%d</strong> 观测 / <strong>%d</strong> 只基金；R² = %.4f，Adj.R² = %.4f。
标准误采用 <strong>基金×年份双向聚类（Cameron–Gelbach–Miller 2011）</strong>为主口径，单维基金聚类为对照列（两口径均与 linearmodels 金标准交叉验证一致）。
</div>

<div class="table-wrap"><table>
<thead>%s</thead>
<tbody>
%s
</tbody></table></div>

<div class="callout warn">
<strong>L5 行为指标层（核心结论）</strong>：在双向聚类口径下，
<strong>RiskAsym β=+0.07311（t=+3.57, p&lt;0.001***）</strong> 与
<strong>DE β=−0.00606（t=−2.99, p=0.003***）</strong> 均稳健显著；
<strong>LSV β=+0.01548（t=+0.77, p=0.441, n.s.）</strong> 不显著。
三指标推断结论在 <strong>渐近（双向聚类）/ Wild Cluster Bootstrap / 置换检验</strong> 三种口径下高度一致：
RiskAsym 与 DE 均显著（置换 p：RA 0.02 / DE 0.047；WCB p：RA 0.000 / DE 0.014**），仅 LSV 不显著（置换 p 0.51 / WCB p 0.229）。
</div>

<div class="callout">
<strong>L5 增量 R²（全样本口径）</strong> = 完整 M4 R² (%.4f) − 剔除 (de, lsv, risk_asym) 三列后 R² (%.4f) = <strong>%.4f</strong>。
（口径：同一 M4 样本 N=2,264，仅移除 L5 三列；原稿误报的 0.0728 已作废。）
另有<strong>同样本口径</strong>（主文稿 §4.3，M3 与 M4 在可比子集上比较）ΔR²=0.0224（≈2.2%%），与全样本口径定义不同、两者并存；均远小于原稿误报的 0.0728（34.9%%）。
</div>

<p class="footnote">
脚注：(1) <strong>缩尾</strong>：依稿件声明"所有变量经 1%%/99%% 缩尾处理"，FF5 因子与控制变量同样缩尾（全面板缩尾），这是 v4 相对早期未缩尾 FF5 规格的关键修正。(2)
<strong>双向聚类</strong>：V = V_fund + V_year − V_fund∩year（CGM 2011）；t 与 p 基于双向聚类 SE。(3)
<strong>FF5 组内退化</strong>：ff5_adj_return 为 FF5 模型残差，故组内固定效应下 α 截距退化为 0，组内 FE 须改用 quarter_return / excess_return，本表为面板混合 OLS + 双向聚类口径。(4)
<strong>数据缺口披露</strong>：TO_wind 覆盖 86.6%%、全持仓 v2 覆盖 446 只、2016+ 个股月收益已齐；P1 学历(school)仅 45.9%% 有值（需 Wind 经理档案补）；DE/LSV 为半年频全持仓快照（结构性覆盖约 46%%），其关联推断受持仓源限制，须视为方法局限而非缺陷。(5)
<strong>SDI 有效窗口</strong>：SDI（风格漂移）的有效识别窗口为 2022 年之后（window=8 滚动），此前窗口信号不足，相关结论须在此窗口内解读。(6)
<strong>缺失值过滤</strong>：任一 RHS 或 DV 缺失即整行删除，最终 N=2,264；无未来季度泄漏（面板终点 2026Q2）。
</p>
<p class="footnote">数据来源：<code>指标计算流水线/output/主分析面板_重建_含TOwind.csv</code>（MD5 f79b4900，可复现）。
重算脚本：<code>_v4_benchmark_table.py</code>（双向聚类代数与 <code>_verify_two_way_cluster.py</code> 金标准一致）；置换/WCB p 来自 <code>_v4_robust.json</code>（<code>_recompute_robustness_v4_2026-08-16.py</code>）。
</p>
</body></html>
""" % (D["n_obs"], D["n_fund"], D["r2"], D["adj_r2"], thead, "\n".join(rows_html),
       D["r2"], D["r2_without_L5"], D["delta_r2_L5"])

out_path = os.path.join(HERE, "回归表_双向聚类_v4基准_2026-08-16.html")
with open(out_path, "w", encoding="utf-8") as f:
    f.write(html)
print("written:", out_path, "rows:", len(rows_html))
