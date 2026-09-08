# -*- coding: utf-8 -*-
"""导师汇报 PPT 生成（2026-08-22）：基于 导师汇报_研究进展_2026-08-22.html。
python-pptx 原生构建，中文学术风，深墨/青金配色，10 页。
"""
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
from pptx.chart.data import CategoryChartData
from pptx.enum.chart import XL_CHART_TYPE, XL_LABEL_POSITION
from pptx.oxml.ns import qn
import copy

INK   = RGBColor(0x0E, 0x2A, 0x35)   # 深墨（封面/结尾底色）
TEAL  = RGBColor(0x13, 0x80, 0x89)   # 主色
TEALD = RGBColor(0x0F, 0x5F, 0x66)
GOLD  = RGBColor(0xC9, 0xA2, 0x27)   # 强调
LIGHT = RGBColor(0xEE, 0xF4, 0xF5)   # 卡片底
TXT   = RGBColor(0x1A, 0x2B, 0x33)
MUT   = RGBColor(0x5C, 0x70, 0x79)
GREEN = RGBColor(0x1E, 0x7A, 0x34)
GRAY  = RGBColor(0x8A, 0x9A, 0xA3)
RED   = RGBColor(0xB3, 0x26, 0x1E)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
FONT = "Microsoft YaHei"

prs = Presentation()
prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
BLANK = prs.slide_layouts[6]

def _set_ea(run, name=FONT):
    rPr = run._r.get_or_add_rPr()
    ea = rPr.find(qn('a:ea'))
    if ea is None:
        ea = rPr.makeelement(qn('a:ea'), {}); rPr.append(ea)
    ea.set('typeface', name)

def txt(s, x, y, w, h, text, size=14, color=TXT, bold=False, align=PP_ALIGN.LEFT,
        anchor=MSO_ANCHOR.TOP, spacing=1.0, wrap=True):
    tb = s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame; tf.word_wrap = wrap; tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    lines = text.split("\n")
    for i, line in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align; p.line_spacing = spacing
        r = p.add_run(); r.text = line
        r.font.name = FONT; r.font.size = Pt(size); r.font.color.rgb = color; r.font.bold = bold
        _set_ea(r)
    return tb

def card(s, x, y, w, h, fill=LIGHT, radius=0.08, shadow=False, line=None):
    sp = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    try: sp.adjustments[0] = radius
    except Exception: pass
    sp.fill.solid(); sp.fill.fore_color.rgb = fill
    if line: sp.line.color.rgb = line; sp.line.width = Pt(1)
    else: sp.line.fill.background()
    sp.shadow.inherit = False
    return sp

def circle(s, x, y, d, fill, label, size=16, color=WHITE, bold=True):
    c = s.shapes.add_shape(MSO_SHAPE.OVAL, Inches(x), Inches(y), Inches(d), Inches(d))
    c.fill.solid(); c.fill.fore_color.rgb = fill; c.line.fill.background(); c.shadow.inherit = False
    tf = c.text_frame; tf.word_wrap = False
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    p = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER
    r = p.add_run(); r.text = label
    r.font.name = FONT; r.font.size = Pt(size); r.font.color.rgb = color; r.font.bold = bold
    _set_ea(r)
    return c

def header(s, num, title):
    circle(s, 0.55, 0.42, 0.52, TEAL, num, size=18)
    txt(s, 1.25, 0.42, 11.5, 0.55, title, size=26, color=INK, bold=True, anchor=MSO_ANCHOR.MIDDLE)

def badge(s, x, y, w, label, fill, color=WHITE, size=11):
    b = card(s, x, y, w, 0.3, fill=fill, radius=0.5)
    tf = b.text_frame; tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    p = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER
    r = p.add_run(); r.text = label
    r.font.name = FONT; r.font.size = Pt(size); r.font.color.rgb = color; r.font.bold = True
    _set_ea(r)

def style_table(tb, header_fill=INK, size=12, header_size=12):
    for ri, row in enumerate(tb.rows):
        for cell in row.cells:
            cell.margin_left = cell.margin_right = Inches(0.06)
            cell.margin_top = cell.margin_bottom = Inches(0.02)
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            if ri == 0:
                cell.fill.solid(); cell.fill.fore_color.rgb = header_fill
            for p in cell.text_frame.paragraphs:
                for r in p.runs:
                    r.font.name = FONT; r.font.size = Pt(header_size if ri == 0 else size)
                    r.font.color.rgb = WHITE if ri == 0 else TXT
                    r.font.bold = (ri == 0)
                    _set_ea(r)

# ============ S1 封面 ============
s = prs.slides.add_slide(BLANK)
s.background.fill.solid(); s.background.fill.fore_color.rgb = INK
card(s, 0, 7.0, 13.333, 0.5, fill=TEALD, radius=0)
txt(s, 1.0, 1.55, 11.3, 1.0, "基金经理投资行为画像", size=44, color=WHITE, bold=True, align=PP_ALIGN.CENTER)
txt(s, 1.0, 2.55, 11.3, 0.6, "基于五层行为分解框架的实证研究 · 阶段进展汇报", size=22, color=GOLD, align=PP_ALIGN.CENTER)
layers = [("L1", "谁在管"), ("L2", "持什么"), ("L3", "怎么交易"), ("L4", "怎么控风险"), ("L5", "为何决策")]
for i, (code, q) in enumerate(layers):
    x = 2.27 + i * 1.85
    card(s, x, 3.7, 1.6, 0.95, fill=RGBColor(0x14, 0x3A, 0x47), radius=0.15, line=TEAL)
    txt(s, x, 3.82, 1.6, 0.35, code, size=15, color=GOLD, bold=True, align=PP_ALIGN.CENTER)
    txt(s, x, 4.18, 1.6, 0.35, q, size=12, color=WHITE, align=PP_ALIGN.CENTER)
    if i < 4:
        txt(s, x + 1.6, 3.95, 0.25, 0.4, "→", size=16, color=TEAL, bold=True, align=PP_ALIGN.CENTER)
txt(s, 1.0, 5.3, 11.3, 0.4, "2006–2026 · 400 只主动偏股混合基金 · 9,974 基金-季度 · 222 位经理", size=14, color=RGBColor(0xAF, 0xC5, 0xCC), align=PP_ALIGN.CENTER)
txt(s, 1.0, 6.3, 11.3, 0.4, "2026 年 8 月 22 日", size=13, color=MUT, align=PP_ALIGN.CENTER)

# ============ S2 研究问题 ============
s = prs.slides.add_slide(BLANK)
header(s, "1", "我们在研究什么")
card(s, 0.55, 1.25, 12.2, 1.35, fill=LIGHT, radius=0.1)
txt(s, 0.9, 1.42, 11.5, 1.0,
    "核心问题：在控制“谁在管理、持有什么、怎么交易、怎么控风险”等全部可观测行为后，\n认知偏差（处置效应 DE · 羊群 LSV · 风险不对称 RA）是否仍独立预测基金超额业绩？",
    size=17, color=INK, bold=True, spacing=1.25)
ids = [("截面基准", "基金之间谁 alpha 更高", "回答“高低”"), ("前向预测", "本季行为 → 未来业绩", "回答“时序”"), ("组内识别", "同一基金内时序变异", "最接近因果")]
for i, (t, d1, d2) in enumerate(ids):
    x = 0.55 + i * 4.15
    card(s, x, 2.95, 3.9, 1.75, fill=WHITE, radius=0.1, line=RGBColor(0xD4, 0xE2, 0xE5))
    circle(s, x + 0.25, 3.2, 0.45, TEAL, str(i + 1), size=15)
    txt(s, x + 0.85, 3.22, 2.9, 0.4, t, size=16, bold=True, color=INK)
    txt(s, x + 0.25, 3.85, 3.4, 0.4, d1, size=13, color=TXT)
    txt(s, x + 0.25, 4.25, 3.4, 0.4, d2, size=12, color=MUT)
txt(s, 0.55, 5.05, 12.2, 0.4, "三重识别策略：严格区分“预测关联”与“因果证据”", size=15, bold=True, color=TEALD)
txt(s, 0.55, 5.5, 12.2, 0.8,
    "推断口径：基金×年份双向聚类（CGM 2011）为主，Wild Cluster Bootstrap、置换检验交叉验证；\n全部变量 1%/99% 缩尾；证据实行 A / B / C 三级分级并逐项标注效度边界。",
    size=13, color=MUT, spacing=1.3)

# ============ S3 五层框架 ============
s = prs.slides.add_slide(BLANK)
header(s, "2", "五层行为分解框架：哪几层有信号")
rows = [
    ("L1", "经理背景", "任期 · 基金年龄 · 学历/CFA", "基金年龄 −2.53**；其余 n.s.", GRAY, "微弱"),
    ("L2", "持仓决策", "主动份额 AS · 行业偏离 ICI · HHI", "AS −2.81*** · ICI +3.74***", GREEN, "强"),
    ("L3", "交易执行", "风格漂移 SDI · 换手 TO · Return Gap", "全部不显著（RG 仲裁为零结果）", GRAY, "零/负结果"),
    ("L4", "风险应对", "ARG · 收益波动率 · idio_vol · TMβ₂", "ARG +2.98***；其余 n.s.", GREEN, "中强"),
    ("L5", "认知偏差", "DE · LSV · RA（理论核心层）", "RA +3.57*** · DE −2.99*** · LSV n.s.", GREEN, "最强"),
]
for i, (code, name, ind, sig, col, lab) in enumerate(rows):
    y = 1.3 + i * 1.08
    card(s, 0.55, y, 12.2, 0.92, fill=(LIGHT if i != 4 else RGBColor(0xE6, 0xF3, 0xEC)), radius=0.12)
    txt(s, 0.75, y + 0.24, 0.7, 0.45, code, size=18, bold=True, color=TEAL)
    txt(s, 1.55, y + 0.1, 1.8, 0.4, name, size=15, bold=True, color=INK)
    txt(s, 1.55, y + 0.48, 4.6, 0.35, ind, size=11.5, color=MUT)
    txt(s, 6.4, y + 0.28, 4.7, 0.4, sig, size=13.5, color=(GREEN if "n.s." not in sig.split("；")[0] else TXT), bold=True)
    badge(s, 11.4, y + 0.29, 1.1, lab, col)
txt(s, 0.55, 6.85, 12.2, 0.4,
    "显著信号集中于“决策内容（L2）— 风险应对（L4）— 认知偏差（L5）”；L1/L3 的不显著是框架的发现：为配置指明“不该看什么”。",
    size=13, color=MUT)

# ============ S4 核心结果 ============
s = prs.slides.add_slide(BLANK)
header(s, "3", "核心结果（v4 权威基准 M4：N=2,264 / 348 只 / R²=0.129）")
data = [
    ["指标", "系数 β", "t（双向聚类）", "分级"],
    ["风险不对称 RA（L5）", "+0.0731", "+3.57 ***", "A"],
    ["行业偏离 ICI（L2）", "+0.0180", "+3.74 ***", "A"],
    ["处置效应 DE（L5）", "−0.0061", "−2.99 ***", "A（限组内）"],
    ["主动份额 AS（L2）", "−0.0298", "−2.81 ***", "A"],
    ["主动风险 ARG（L4）", "+0.0162", "+2.98 ***", "A"],
    ["羊群 LSV（L5）", "+0.0155", "+0.77 n.s.", "C"],
]
tb = s.shapes.add_table(len(data), 4, Inches(0.55), Inches(1.3), Inches(6.4), Inches(3.4)).table
for c, w in enumerate([2.6, 1.2, 1.6, 1.0]): tb.columns[c].width = Inches(w)
for ri, row in enumerate(data):
    for ci, v in enumerate(row):
        tb.cell(ri, ci).text = v
style_table(tb)
for ri in range(1, len(data)):
    cell = tb.cell(ri, 3)
    for p in cell.text_frame.paragraphs:
        for r in p.runs:
            r.font.color.rgb = GREEN if "A" in r.text and ri != 6 else (GRAY if ri == 6 else GREEN)
cd = CategoryChartData()
cd.categories = ["LSV", "ARG", "AS", "DE", "RA", "ICI"]
cd.add_series("t 值（双向聚类）", (0.77, 2.98, -2.81, -2.99, 3.57, 3.74))
gf = s.shapes.add_chart(XL_CHART_TYPE.BAR_CLUSTERED, Inches(7.3), Inches(1.25), Inches(5.5), Inches(3.6), cd)
ch = gf.chart; ch.has_legend = False; ch.has_title = False
ser = ch.series[0]; ser.format.fill.solid(); ser.format.fill.fore_color.rgb = TEAL
for ax in (ch.category_axis, ch.value_axis):
    ax.tick_labels.font.size = Pt(11); ax.tick_labels.font.name = FONT
ch.value_axis.has_major_gridlines = True
txt(s, 0.55, 4.95, 6.4, 1.6,
    "一句话结论：控制 L1–L4 全部可观测行为后，认知偏差层仍有增量解释力\n（ΔR²=0.022，占 M4 总 R² 的 17%）；RA 是全文最稳健的发现，DE 在组内维度稳健，\nLSV 不显著（C 级，机制已诊断：被同层掩盖 + 时期依存）。",
    size=13.5, color=INK, spacing=1.35)
txt(s, 7.3, 5.05, 5.5, 1.4,
    "定位：预测关联，不主张因果量级\n（Oster δ≤0、IV 路线不可复现，均已诚实披露并收缩结论）。",
    size=12.5, color=MUT, spacing=1.3)

# ============ S5 结论与边界 ============
s = prs.slides.add_slide(BLANK)
header(s, "4", "结论与效度边界（如实报告）")
card(s, 0.55, 1.3, 12.2, 1.15, fill=RGBColor(0xE6, 0xF3, 0xEC), radius=0.1)
txt(s, 0.9, 1.5, 11.6, 0.8,
    "基金业绩的稳定可预测来源在“持仓决策 — 风险应对 — 认知偏差”，而非经理背景与交易频率；\n认知偏差的预测力经截面 / 前向 / 组内三重识别与十余项稳健性检验界定。",
    size=16, color=INK, bold=True, spacing=1.3)
bounds = [
    ("DV 口径边界", "法定基准收益作因变量时 L5 三指标全不显著、RA 方向反转 —— 结论限于 FF5-alpha 口径（8/21 Brinson 批次发现，已入稿）"),
    ("PS 综合分样本外", "严格协议样本外验证 Q5−Q1=4.1–5.6%/季（置换 p<0.0005），但初期口径仅 1.28% 且覆盖单一牛熊窗 —— 定位为方向性证据"),
    ("覆盖率边界", "DE 仅 46.6% 观测可用（需全持仓），估计样本为正向选择子群 —— A 级限定于组内维度；LSV 92%、RA 72%"),
    ("因果边界", "Oster 遗漏变量界 δ 均 ≤0、IV 路线 iv_N=0 不可复现 —— 不作任何因果量级声称"),
]
for i, (t, d) in enumerate(bounds):
    x = 0.55 + (i % 2) * 6.25; y = 2.75 + (i // 2) * 1.75
    card(s, x, y, 5.95, 1.55, fill=WHITE, radius=0.1, line=RGBColor(0xE4, 0xD6, 0xB4))
    circle(s, x + 0.22, y + 0.22, 0.4, GOLD, "!", size=15)
    txt(s, x + 0.78, y + 0.22, 5.0, 0.4, t, size=15, bold=True, color=INK)
    txt(s, x + 0.25, y + 0.68, 5.5, 0.8, d, size=11.5, color=MUT, spacing=1.2)

# ============ S6 深化① 能力分解 ============
s = prs.slides.add_slide(BLANK)
header(s, "5", "本周发现①（论文级）：偏差影响的是选股能力，不是择时能力")
txt(s, 0.55, 1.18, 12.2, 0.45,
    "日频 NAV 对每个基金-年做 TM / HM 择时模型，把业绩分解为“选股α”与“择时贡献”，分别作因变量：", size=14, color=TXT)
data = [
    ["变量", "选股α 截面 TM", "选股α 截面 HM", "选股α 组内 TM", "选股α 组内 HM", "择时贡献（四口径）"],
    ["风险不对称 RA", "+5.12 ***", "+3.45 ***", "+6.88 ***", "+5.16 ***", "n.s.（−0.3~−0.9）"],
    ["处置效应 DE", "−3.03 ***", "−3.42 ***", "−2.68 ***", "−2.66 ***", "n.s.（+0.2~+1.9）"],
    ["行业偏离 ICI（对照）", "n.s.", "−1.93 *", "−2.76 ***", "−2.41 **", "+2.5~2.8 ***（仅择时）"],
    ["换手率 TO（对照）", "n.s.", "+2.20 **", "n.s.", "+2.28 **", "−2.1~−3.0 **（仅择时）"],
]
tb = s.shapes.add_table(len(data), 6, Inches(0.55), Inches(1.75), Inches(12.2), Inches(2.7)).table
widths = [2.5, 1.9, 1.9, 1.9, 1.9, 2.1]
for c, w in enumerate(widths): tb.columns[c].width = Inches(w)
for ri, row in enumerate(data):
    for ci, v in enumerate(row): tb.cell(ri, ci).text = v
style_table(tb, size=12)
card(s, 0.55, 4.75, 12.2, 1.0, fill=RGBColor(0xE6, 0xF3, 0xEC), radius=0.1)
txt(s, 0.85, 4.92, 11.7, 0.7,
    "双分离在「截面 TM / 截面 HM / 组内 TM / 组内 HM」四种设计下完全复现；DE 的 A 级证据本以组内为最强维度，\n组内复验确认其承接维度正是选股α —— “处置效应损害选股能力”从截面关联升级为组内（准因果方向）证据。",
    size=13.5, color=INK, bold=True, spacing=1.3)
txt(s, 0.55, 5.95, 12.2, 0.4, "附：corr(TMβ₂, RA)=0.28 —— RA 独立于统计择时，是对传统择时模型的增量维度", size=12, color=MUT)

# ============ S7 深化② 运气与复验 ============
s = prs.slides.add_slide(BLANK)
header(s, "6", "本周发现②③：RA 免疫截面运气 · 日频独立子样本复现")
cd = CategoryChartData()
cd.categories = ["LSV", "DE", "ARG", "AS", "ICI", "RA"]
cd.add_series("同向显著比例", (0.068, 0.42, 0.567, 0.598, 0.84, 0.976))
gf = s.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(0.55), Inches(1.35), Inches(6.1), Inches(3.7), cd)
ch = gf.chart; ch.has_legend = False; ch.has_title = False
ser = ch.series[0]; ser.format.fill.solid(); ser.format.fill.fore_color.rgb = TEAL
pt = ser.points[5]; pt.format.fill.solid(); pt.format.fill.fore_color.rgb = GOLD
for ax in (ch.category_axis, ch.value_axis):
    ax.tick_labels.font.size = Pt(11); ax.tick_labels.font.name = FONT
txt(s, 0.55, 1.28, 6.1, 0.35, "基金层 Bootstrap 1,000 次重抽样：同向显著比例", size=13, bold=True, color=INK)
txt(s, 0.55, 5.2, 6.1, 1.0,
    "RA 在 97.6% 的重抽样中同向显著（经验 CI [+0.041, +0.099] 排零）——\n基本免疫“少数明星基金驱动”的截面运气质疑；LSV CI 含零，确认零结果。",
    size=12.5, color=TXT, spacing=1.3)
card(s, 7.0, 1.35, 5.75, 4.5, fill=LIGHT, radius=0.1)
txt(s, 7.3, 1.55, 5.2, 0.4, "日频 NAV 独立子样本复验（N=1,336/159）", size=15, bold=True, color=INK)
repl = [("RA", "+3.22 ***"), ("ICI", "+2.84 ***"), ("ARG", "+2.27 **"), ("TO_wind", "+1.72 *")]
for i, (n, v) in enumerate(repl):
    x = 7.3 + i * 1.32
    txt(s, x, 2.15, 1.25, 0.35, n, size=12, color=MUT, align=PP_ALIGN.CENTER)
    txt(s, x, 2.5, 1.25, 0.45, v, size=14, color=GREEN, bold=True, align=PP_ALIGN.CENTER)
txt(s, 7.3, 3.15, 5.2, 1.5,
    "194 只基金的子样本，数据源与构造逻辑均不同于主面板，\n却完整复现了 v4 核心信号（全样本 RA +3.57 / ICI +3.74 / ARG +2.98）。\nAS 未复现（t=−0.38）、DE 方向一致但 n.s. —— 均已如实披露。",
    size=12.5, color=TXT, spacing=1.35)
txt(s, 7.3, 4.85, 5.2, 0.8,
    "注：该结论来自 8/22 对批次②标准误实现的勘误修正；\n修正前的“子样本不显著”系计算错误造成的伪影。",
    size=11, color=MUT, spacing=1.25)

# ============ S8 诚信自查 ============
s = prs.slides.add_slide(BLANK)
header(s, "7", "研究诚信自查：主动发现并撤回自己的虚假显著")
items = [
    ("v20 → v3", "推翻初版“三指标全显著”结论：LSV 显著性为小样本窗口产物，降为 C 级"),
    ("中介分析", "修复间接效应计算 bug，修正后 LSV→波动率路径不再显著"),
    ("Return Gap", "8/20 曾现 t=−7.68“强显著”，8/21 仲裁查明系持仓污染伪信号，正式撤回为零结果"),
    ("IV / 2SLS", "工具变量样本交集塌缩（iv_N=0），全部 IV 系数作废，不主张因果量级"),
    ("PS 综合分", "样本外验证失败后主动降级为方向性证据，不外推可交易性"),
    ("批次② SE（8/22）", "发现聚类标准误实现错误，当日全部 t 值作废并修正重跑"),
]
for i, (t, d) in enumerate(items):
    x = 0.55 + (i % 2) * 6.25; y = 1.35 + (i // 2) * 1.62
    card(s, x, y, 5.95, 1.42, fill=WHITE, radius=0.1, line=RGBColor(0xD4, 0xE2, 0xE5))
    circle(s, x + 0.22, y + 0.2, 0.42, TEAL, "✓", size=15)
    txt(s, x + 0.8, y + 0.18, 5.0, 0.4, t, size=14.5, bold=True, color=INK)
    txt(s, x + 0.8, y + 0.62, 4.95, 0.75, d, size=11.5, color=MUT, spacing=1.2)
card(s, 0.55, 6.35, 12.2, 0.75, fill=INK, radius=0.1)
txt(s, 0.9, 6.5, 11.6, 0.45, "全部结果 A/C 两级分级 + 效度边界逐项标注 —— “诚实重估”流程本身是本研究的方法论贡献", size=14, color=WHITE, bold=True)

# ============ S9 数据与可复现 ============
s = prs.slides.add_slide(BLANK)
header(s, "8", "数据与可复现性")
stats = [("400", "主动偏股混合基金"), ("9,974", "基金-季度观测"), ("2006–2026", "非平衡面板区间"), ("222", "基金经理")]
for i, (v, l) in enumerate(stats):
    x = 0.55 + i * 3.15
    card(s, x, 1.35, 2.9, 1.5, fill=LIGHT, radius=0.12)
    txt(s, x, 1.55, 2.9, 0.6, v, size=30, bold=True, color=TEALD, align=PP_ALIGN.CENTER)
    txt(s, x, 2.3, 2.9, 0.4, l, size=12.5, color=MUT, align=PP_ALIGN.CENTER)
stats2 = [("MD5 一致", "run_all.py 两次复跑"), ("逐字段差=0", "出稿终值验证"), ("28.4 万行", "日频 NAV + FF5 因子"), ("302 篇", "文献库（核心 252）")]
for i, (v, l) in enumerate(stats2):
    x = 0.55 + i * 3.15
    card(s, x, 3.1, 2.9, 1.5, fill=WHITE, radius=0.12, line=RGBColor(0xD4, 0xE2, 0xE5))
    txt(s, x, 3.3, 2.9, 0.6, v, size=22, bold=True, color=GOLD, align=PP_ALIGN.CENTER)
    txt(s, x, 4.0, 2.9, 0.4, l, size=12, color=MUT, align=PP_ALIGN.CENTER)
txt(s, 0.55, 4.85, 12.2, 0.4, "数据来源", size=15, bold=True, color=INK)
txt(s, 0.55, 5.3, 12.2, 0.9,
    "Wind（换手率、经理信息）· AKShare/新浪（2006–2017 全持仓、个股月收益约 4,185 只）· 东财全持仓 v2 ·\niFinD（27 只清盘基金净值，生存偏差修正）· FF5 因子（本地/日度）· 覆盖率边界：AS/ICI 94%、LSV 92%、RA 72%、DE 46.6%",
    size=12, color=MUT, spacing=1.3)
txt(s, 0.55, 6.5, 12.2, 0.4, "覆盖边界如实披露：DE/LSV 受全持仓披露约束；school 字段 45.9% 待补（Wind 配额）", size=11.5, color=RED)

# ============ S10 下一步 ============
s = prs.slides.add_slide(BLANK)
s.background.fill.solid(); s.background.fill.fore_color.rgb = INK
txt(s, 1.0, 0.7, 11.3, 0.6, "下一步", size=34, color=WHITE, bold=True)
nxt = [
    ("数据补强", "CSMAR 付费源补 2006–2017 全持仓（提升 DE 覆盖率 46.6%→更高）；Wind 经理档案补 school 字段 —— 等配额"),
    ("写作收尾", "稿件 19 项一致性问题已全部修复（8/22 清零）；剩余为 Word 转换与参考文献格式终排"),
    ("可选延伸", "Chang-Lewellan 第三分解口径（边际）；factor_drift 边际信号更大样本复验"),
]
for i, (t, d) in enumerate(nxt):
    y = 1.75 + i * 1.25
    circle(s, 1.0, y, 0.5, GOLD, str(i + 1), size=16, color=INK)
    txt(s, 1.75, y + 0.02, 3.0, 0.45, t, size=18, bold=True, color=WHITE)
    txt(s, 1.75, y + 0.52, 10.5, 0.55, d, size=13, color=RGBColor(0xAF, 0xC5, 0xCC))
card(s, 1.0, 5.8, 11.3, 0.9, fill=RGBColor(0x14, 0x3A, 0x47), radius=0.12, line=TEAL)
txt(s, 1.35, 6.0, 10.6, 0.5,
    "一句话：我们找到了“哪些行为预测业绩”（RA/DE/ICI/AS/ARG），本周进一步找到了“预测哪种能力”（选股α）。",
    size=15, color=GOLD, bold=True)

OUT = "D:/Desktop/基金经理行为分析研究/导师汇报_研究进展_2026-08-22.pptx"
prs.save(OUT)
print("saved:", OUT, "slides:", len(prs.slides.__iter__.__self__._sldIdLst))
