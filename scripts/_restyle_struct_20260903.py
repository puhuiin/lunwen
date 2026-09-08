# -*- coding: utf-8 -*-
"""风格改版·结构层（2026-09-03）：对齐《你是什么样的投资者0903.docx》样本。
① 标题体系改口语化 ② 表 1 层级列改三层 ③ 编号引用改作者-年份 ④ 参考文献表改附注
全部为唯一性断言的精确替换。
"""
import io, os, re

P = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                 'scripts', '_draft_docx_20260826.py')
src = io.open(P, encoding='utf-8').read()

def rep(old, new, cnt=1):
    global src
    n = src.count(old)
    assert n == cnt, f'count={n}(want {cnt}): {old[:40]!r}'
    src = src.replace(old, new)

# ---------- ① 标题体系 ----------
rep("heading(doc, '一、理论研究', 1)",
    "heading(doc, '一、“行为”拆成三层：底色、认知、应对', 1)")
rep("heading(doc, '二、实证检验', 1)",
    "heading(doc, '二、实证检验：行为指标的业绩解释力', 1)")
rep("heading(doc, '（一）数据来源说明', 2)",
    "heading(doc, '（一）样本与指标设计', 2)")
rep("heading(doc, '（三）显著指标的维度归并', 2)",
    "heading(doc, '（三）维度复合与业绩预测', 2)")
rep("heading(doc, '三、投资经理画像', 1)",
    "heading(doc, '三、投资经理画像——好经理和差经理，差在哪？', 1)")
rep("heading(doc, '（一）群体画像', 2)",
    "heading(doc, '（一）群体画像：绩优与绩差经理的维度差异', 2)")
rep("heading(doc, '（二）典型画像', 2)",
    "heading(doc, '（二）典型案例：六种行为切面', 2)")
rep("heading(doc, '（三）结论', 2)",
    "heading(doc, '四、结论与启示', 1)")

# ---------- ② 表 1 层级列：五层命名 → 三层（与叙事一致）----------
rep("""LAYER_OF = {
    'tenure': '背景特征', 'log_age': '背景特征', 'log_aum': '背景特征', 'male': '背景特征',
    'has_CFA': '背景特征', 'master_up': '背景特征', 'top_school': '背景特征',
    'risk_asym': '认知与行为', 'de': '认知与行为', 'oc_conf': '认知与行为',
    'rc_mom': '认知与行为', 'anchor_high': '认知与行为', 'cgo': '认知与行为',
    'house_money': '认知与行为', 'bhm_shm': '认知与行为',
    'ICI': '配置选择', 'ISDI': '配置选择', 'AS_improved': '配置选择',
    'ARG': '风险应对', 'timing': '风险应对', 'return_volatility': '风险应对',
    'rsstab': '风险应对', 'sharpe8': '风险应对', 'sortino8': '风险应对', 'mppm8': '风险应对',
    'SDI': '交易执行', 'lsv': '交易执行', 'TO': '交易执行',
}""",
    """LAYER_OF = {
    'tenure': '风格底色', 'log_age': '风格底色', 'log_aum': '风格底色', 'male': '风格底色',
    'has_CFA': '风格底色', 'master_up': '风格底色', 'top_school': '风格底色',
    'risk_asym': '认知偏差', 'de': '认知偏差', 'oc_conf': '认知偏差',
    'rc_mom': '认知偏差', 'anchor_high': '认知偏差', 'cgo': '认知偏差',
    'house_money': '认知偏差', 'bhm_shm': '认知偏差',
    'ICI': '风格底色', 'ISDI': '风格底色', 'AS_improved': '风格底色',
    'ARG': '风险应对', 'timing': '风险应对', 'return_volatility': '风险应对',
    'rsstab': '风险应对', 'sharpe8': '风险应对', 'sortino8': '风险应对', 'mppm8': '风险应对',
    'SDI': '风险应对', 'lsv': '风险应对', 'TO': '风险应对',
}""")
rep("caption(doc, '表 1  候选指标的行为层级、理论依据与计算方式')",
    "caption(doc, '表 1  三层递进行为框架与候选指标体系')")

# ---------- ③ 正文编号引用 → 作者-年份 ----------
rep("'主口径 FF5 alpha[19]——'\n          '其中国市场适用性经文献[20]检验支持。')",
    "'主口径 FF5 alpha，'\n          '其在中国市场的适用性已有实证支持（李志冰等, 2017）。')")
rep("'其余落选候选：趋势外推偏差[21]与有限关注度[22]方向检验未通过'",
    "'其余落选候选各有各的原因：趋势外推偏差（Greenwood & Shleifer, 2014）与有限关注度（Barber & Odean, 2008）方向检验未通过'")
rep("。三证俱在，剔除之，与文献[13]一致'\n          '（文献[25]持相反意见）。')",
    "。三证俱在，剔除之——与 Frazzini 等（2016）“去激活主动份额”的结论一致'\n          '（Cremers & Petajisto, 2009 持相反意见）。')")

# ---------- ④ 参考文献表 → 附注：方法说明 ----------
rep("""# ---------------------------------------------------------------- 参考文献
heading(doc, '参考文献', 1)
# 顺序编码制（GB/T 7714）：按正文首次引用顺序编号 [1]–[25]，不再使用底库散乱 id
ref_ids = ['1', '15', '16', '59', '30', '60', '45', '54', '53', '52', '26', '62', '55', '39', '58', '57', '34', '31', '23', '43', '63', '64', '13', '61', '28',
           '70', '71', '33', '14']
for _n, i in enumerate(ref_ids, 1):
    p = doc.add_paragraph()
    r = p.add_run(f'[{_n}] {REF[i]}')
    set_run(r, size=9)
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.line_spacing = 1.15""",
    """# ---------------------------------------------------------------- 附注：方法说明
# 样本式文献处理：正文作者-年份制，文末附注列举主要来源（完整列表联系作者）
p = doc.add_paragraph()
r = p.add_run('附注：方法说明')
set_run(r, size=10.5, bold=True, cn='黑体')
p.paragraph_format.space_before = Pt(14)
p.paragraph_format.space_after = Pt(4)
para(doc, '指标均经 1%/99% 缩尾与 z 标准化，并按理论定向取号；维度内成分等权、'
          '六维再等权复合为综合能力分。因变量为 FF5 五因子模型调整后的超额收益'
          '（alpha，Fama & French, 2015），中国市场适用性见李志冰等（2017）。'
          '本文为工作稿，完整文献列表（29 条，GB/T 7714）联系作者索取；'
          '主要理论来源包括：Kahneman & Tversky (1979)、Shefrin & Statman (1985)、'
          'Odean (1998)、Chevalier & Ellison (1999)、Kacperczyk, Sialm & Zheng (2005, 2008)、'
          'Henriksson & Merton (1981)、Cremers & Petajisto (2009)、Frazzini et al. (2016)、'
          'Berk & Green (2004)、Greenwood & Shleifer (2014)、Barber & Odean (2008) 等。')""")

# ---------- ⑤ 表 1 来源列去编号（theory_rows 内的 [n]）----------
_i = src.find('theory_rows = [')
_j = src.find(']', src.find("'值越大表示交易越频繁", _i))
_seg = src[_i:_j]
_seg2 = re.sub(r'\[\d+\]', '', _seg)
rep(_seg, _seg2)

io.open(P, 'w', encoding='utf-8').write(src)
print('结构层改版完成')
