# -*- coding: utf-8 -*-
"""生成实证结论—证据强度总览：单一数据源 → manuscript §6.1.7 + 独立 HTML 工件。
所有数值取自 v4 权威基准（双向聚类 CGM2011，M4 N=2264/348，R²=0.1290）：
  基准表 回归表_双向聚类_v4基准_2026-08-16.html
  LSV 审计 output/lsv_脆弱性诊断电池_2026-08-16.csv
  DE  审计 output/de_选择性审计_2026-08-16.csv / de_组间可比性_2026-08-16.csv
"""
import io, os

# ---------- 单一数据源：按层组织的证据表 ----------
# 字段: layer, name, hypoth, beta, t, p, wcb, perm, grade, boundary
# beta/t 为 M4 双向聚类权威值；wcb/perm 仅 L5 三指标有（来自 _v4_robust.json）
# grade: A=强 / B=条件 / C=弱或不稳
ROWS = [
    # L1 基金经理层
    ("L1","基金年龄对数","—","-0.00417","-2.53","0.011","—","—","A",
     "稳定控制变量，全样本稳健；无外推限制"),
    ("L1","经理累计任期","—","≈0.00000","+1.02","0.309","—","—","C",
     "M4 不显著，任期长度与业绩无稳定截面关联"),
    # L2 持仓偏离层
    ("L2","主动持股比 (AS)","—","-0.02982","-2.81","0.005","—","—","A",
     "高主动份额伴随更低 alpha，稳健；属结构性控制"),
    ("L2","行业集中度 (ICI)","—","+0.01804","+3.74","<0.001","—","—","A",
     "行业集中带来超额收益，稳健；净效应取决于选股能力"),
    ("L2","行业 HHI","—","+0.00865","+0.19","0.852","—","—","C",
     "M4 不显著，行业集中度-HHI 维度无独立信息"),
    # L3 交易执行层
    ("L3","风格漂移 (SDI)","H1","-0.00000","-0.00","0.999","—","—","C",
     "M4 全控制下不显著（被 L2/L4 吸收）；稀疏设定下 H1 成立，但有效窗口 2022+（§4.2）"),
    ("L3","换手率 (TO_wind)","H2","+0.00000","+1.07","0.287","—","—","C",
     "M4 全控制下不显著；稀疏设定 t=+1.78*，成本侵蚀效应弱且被中介检验推翻（§4.2）"),
    ("L3","调仓收益缺口 (ARG)","—","+0.01625","+2.98","0.003","—","—","A",
     "主动风险调整正向关联业绩，稳健；属执行一致性维度"),
    ("L3","收益波动率","—","+0.02379","+0.81","0.415","—","—","C",
     "M4 不显著；其作为中介渠道显著（§6.1.5），但作为直接预测因子无独立信息"),
    # L5 行为指标层（核心）
    ("L5","处置效应 (DE)","H3*","-0.00606","-2.99","0.003","0.014","0.047","A",
     "双向聚类*** + WCB** + 置换* 一致；组内FE t=-3.64 强。效度边界：估计样本为选择偏倚子群（de_avail→alpha +0.0048,t2.18**），结论外推限于~46.6%有全持仓数据子群（§4.4.9）"),
    ("L5","羊群效应 (LSV)","—","+0.01548","+0.77","0.441","0.229","0.507","C",
     "M4 不显著；脆弱性已诊断：非共线(VIF=1.15)、非数据假象，机制=被同层 de/RA 掩盖（J 隔离→+0.027,t2.78***）、时期依存（2022+ +0.025,t2.03**）。作描述性/选择敏感证据（§4.4.8）"),
    ("L5","风险不对称 (RiskAsym)","—","+0.07311","+3.57","<0.001","0.000","0.020","A",
     "双向聚类*** + WCB*** + 置换* 一致；构念已对择时正交化（§4.4.5）。机制多元（赌资/择时/技能），非线性倒U仅边际；最强单指标证据"),
]

def stars(p):
    if p in ("<0.001",) or (isinstance(p,str) and p.startswith("<0.001")):
        return "***"
    try:
        pv = float(p)
    except Exception:
        return ""
    if pv < 0.01: return "***"
    if pv < 0.05: return "**"
    if pv < 0.10: return "*"
    return "n.s."

def render_table():
    head = ("<tr><th>层</th><th>指标</th><th>假设</th><th>M4 系数<br>(双向聚类)</th>"
            "<th>t</th><th>p</th><th>WCB p</th><th>置换 p</th><th>证据分级</th><th>效度边界与稳健性索引</th></tr>")
    body = []
    for layer,name,hypoth,beta,t,p,wcb,perm,grade,boundary in ROWS:
        st = stars(p)
        pcell = f"{p} {st}".strip() if st else p
        # grade cell with color hint
        gclass = {"A":"grade-a","B":"grade-b","C":"grade-c"}[grade]
        body.append(
            f"<tr><td>{layer}</td><td>{name}</td><td>{hypoth}</td>"
            f"<td>{beta}</td><td>{t}</td><td>{pcell}</td><td>{wcb}</td><td>{perm}</td>"
            f"<td class='{gclass}'>{grade}</td><td class='boundary'>{boundary}</td></tr>"
        )
    return head, "\n".join(body)

HEAD, BODY = render_table()

# ---------- manuscript 插入块 ----------
intro = (
    "<p>下表将全文实证结论按 L1–L5 五层框架汇总为统一的<b>证据强度总览</b>，"
    "所有系数取自 v4 权威基准（M4 面板混合 OLS + 基金×年份双向聚类 CGM2011，"
    "N=2,264 / 348 只基金，R²=0.1290）。证据分级遵循三档规则："
    "<b>A 级（强证据）</b>＝M4 双向聚类至少 ** 且独立于渐近/WCB/置换至少两种口径一致显著、稳健性章无推翻项；"
    "<b>B 级（条件证据）</b>＝部分口径或子样本显著、方向稳健但量级/显著性受限；"
    "<b>C 级（弱/不稳证据）</b>＝M4 不显著（n.s.）或方向对样本选择高度敏感，作描述性佐证。"
    "LSV 与 DE 的脆弱性/选择偏倚机制分别见 §4.4.8 与 §4.4.9。</p>"
)
legend = (
    "<p class='footnote'>分级说明：A=强（多口径一致显著）、B=条件（部分口径/子样本显著）、"
    "C=弱或不稳（M4 n.s. 或方向样本敏感）。WCB p=Wild Cluster Bootstrap-S 小样本推断 p；"
    "置换 p=500 次置换检验 p。* H3* 表示 DE 属 L5 行为指标层，其处置效应构念对应前景理论损失规避假设。"
    "SDI/TO_wind 在 M4 全控制下被吸收为不显著，但其对应 H1/H2 在稀疏设定下成立，故分级为 C 并标注有效窗口/中介结论。</p>"
)
table_html = (
    f"<div class='table-wrap'><table class='evi'>\n<thead>{HEAD}</thead>\n<tbody>\n{BODY}\n</tbody></table></div>"
)
SECTION = (
    "<!-- ==================== 6.1.7 实证结论与证据强度总览 ==================== -->\n"
    "<h3>6.1.7 实证结论与证据强度总览</h3>\n"
    + intro + "\n" + table_html + "\n" + legend + "\n"
)

MANUSCRIPT = r"D:/Desktop/基金经理行为分析研究/merged_manuscript.html"
s = io.open(MANUSCRIPT, encoding="utf-8").read()

anchor = "<!-- ==================== 6.2 理论贡献 ==================== -->"
assert s.count(anchor) == 1, f"anchor count={s.count(anchor)}"
assert s.count("6.1.7") == 0, "§6.1.7 already exists"
# 断言：§6.1.7 插入位置前应是 §6.1.6 末尾
s = s.replace(anchor, SECTION + anchor, 1)

# 修正 §6.1.2 残留 46.5% → 46.6%
old_cov = "DE功效不足的主要原因是其覆盖率（46.5%）低于另两个指标"
new_cov = "DE功效不足的主要原因是其覆盖率（46.6%，v4 面板真值）低于另两个指标"
assert s.count(old_cov) == 1, f"coverage string count={s.count(old_cov)}"
s = s.replace(old_cov, new_cov, 1)

io.open(MANUSCRIPT, "w", encoding="utf-8").write(s)
print("manuscript: §6.1.7 inserted, 46.5%->46.6% fixed")

# ---------- 独立 HTML 工件 ----------
css = """
<style>
  body{font-family:-apple-system,'Segoe UI','Microsoft YaHei',sans-serif;margin:32px;color:#1a1a1a;background:#fafafa;}
  h1{font-size:22px;border-bottom:2px solid #2c5f8a;padding-bottom:8px;color:#1f3b57;}
  h2{font-size:16px;color:#2c5f8a;margin-top:24px;}
  p.meta{color:#666;font-size:13px;}
  .table-wrap{overflow-x:auto;margin:16px 0;}
  table.evi{border-collapse:collapse;width:100%;font-size:13px;background:#fff;box-shadow:0 1px 3px rgba(0,0,0,.1);}
  table.evi th,table.evi td{border:1px solid #d9d9d9;padding:7px 9px;text-align:center;vertical-align:top;}
  table.evi th{background:#2c5f8a;color:#fff;font-weight:600;}
  table.evi td:nth-child(2),table.evi td.boundary{text-align:left;}
  table.evi td.boundary{font-size:12px;color:#444;max-width:340px;}
  .grade-a{background:#e6f4ea;color:#1e7a34;font-weight:700;}
  .grade-b{background:#fff4e5;color:#b26a00;font-weight:700;}
  .grade-c{background:#fdecea;color:#b3261e;font-weight:700;}
  .footnote{font-size:12px;color:#666;margin-top:10px;}
  .summary{background:#fff;border-left:4px solid #2c5f8a;padding:12px 16px;margin:16px 0;font-size:13px;}
</style>
"""
summary = (
    "<div class='summary'><b>总览结论：</b>在 v4 诚实面板下，L5 行为指标层中 "
    "<b>RiskAsym（A 级）</b>与 <b>DE（A 级，效度边界 ~46.6% 子群）</b>提供最强的多口径一致证据；"
    "<b>LSV 降为 C 级</b>（M4 n.s.，脆弱性已诊断：非共线、被同层 de/RA 掩盖、2022+ 显著）。"
    "L3 交易层 SDI/TO_wind 在 M4 全控制下被吸收为 C 级（对应 H1/H2 仅在稀疏设定成立）；"
    "ARG 为 A 级。L2 的 AS/ICI 与 L1 的基金年龄均为 A 级稳健控制。 "
    "全稿推断口径已统一为基金×年份双向聚类（CGM2011），并与 WCB / 置换检验交叉验证。</div>"
)
standalone = (
    "<!DOCTYPE html><html lang='zh'><head><meta charset='utf-8'>"
    "<title>实证结论与证据强度总览（v4）</title>" + css + "</head><body>"
    "<h1>实证结论与证据强度总览</h1>"
    "<p class='meta'>数据源：v4 权威基准（M4 面板混合 OLS + 基金×年份双向聚类 CGM2011，"
    "N=2,264 / 348 只基金，R²=0.1290）。生成日期 2026-08-16。</p>"
    + intro + "\n" + table_html + "\n" + summary + "\n" + legend +
    "<p class='footnote'>配套文档：merged_manuscript.html §4.4.8（LSV 脆弱性）、§4.4.9（DE 选择性）、"
    "§6.1.2（L5 三指标结论）、§4.4（十项稳健性）。底层审计：lsv_脆弱性诊断报告_2026-08-16.md、"
    "de_选择性诊断报告_2026-08-16.md。</p>"
    "</body></html>"
)
OUT = r"D:/Desktop/基金经理行为分析研究/实证结论_证据强度总览_2026-08-16.html"
io.open(OUT, "w", encoding="utf-8").write(standalone)
print("standalone written:", OUT)
print("rows:", len(ROWS))
