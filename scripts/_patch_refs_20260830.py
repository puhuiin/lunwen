# -*- coding: utf-8 -*-
"""C1 参考文献体系修复（2026-08-30）

问题（比"编号乱序"更严重，是双向不匹配）：
  1. 正文用「作者-年份」制（如 Kahneman & Tversky, 1979），文献表却用 [n] 编号制，
     两套体系完全脱节，读者无法对应。
  2. 正文引用了 Greenwood & Shleifer (2014)、Barber & Odean (2008)，文献表中没有。
  3. 文献表有 Gervais & Odean (2001)、Treynor & Mazuy (1966)、Cremers & Petajisto (2009)
     三条正文从未引用。

处理：统一改为顺序编码制（GB/T 7714），按正文首现顺序编号 [1]–[25]；
      补入 2 条缺失文献（底库未收录，手工构造）；补引 3 条未引文献。

每处替换强制精确命中一次，未命中即中止（防误伤）。
"""
import io
import json
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, 'output')
REFJSON = os.path.join(OUT, '参考文献_定稿_2026-08-26.json')
DOCXPY = os.path.join(BASE, 'scripts', '_draft_docx_20260826.py')
NL = chr(10)


def rd(p):
    with io.open(p, encoding='utf-8') as f:
        return f.read()


def wr(p, s):
    with io.open(p, 'w', encoding='utf-8') as f:
        f.write(s)


# ---------------------------------------------------------------- Step 1 补文献
NEW_REFS = {
    '63': ('GREENWOOD R, SHLEIFER A. Expectations and returns[J]. '
           'The Review of Financial Studies, 2014, 27(3): 714-746.'),
    '64': ('BARBER B M, ODEAN T. All that glitters: the effect of attention and news '
           'on the buying behavior of individual and institutional investors[J]. '
           'The Review of Financial Studies, 2008, 21(2): 785-818.'),
}


def step1():
    d = json.loads(rd(REFJSON))
    added = []
    for k, v in NEW_REFS.items():
        if k not in d:
            d[k] = v
            added.append(k)
    if added:
        wr(REFJSON + '.bak_20260830', rd(REFJSON))
        wr(REFJSON, json.dumps(d, ensure_ascii=False, indent=1))
        print('[Step1] 已补入文献 key=%s；原文件备份 .bak_20260830' % ','.join(added))
    else:
        print('[Step1] 两条文献已存在，跳过')


# ---------------------------------------------------------------- Step 2 改脚本
# 顺序编码制映射：新编号 -> 底库 key（按正文首现顺序）
REF_ORDER = ['1', '15', '16', '59', '30', '60', '45', '54', '53', '52', '26', '62',
             '55', '39', '58', '57', '34', '31', '23', '43', '63', '64', '13',
             '61', '28']

REPS = [
    # ---- 引言段（L331-339）----
    ('R01', "'风险态度的损益不对称（Kahneman & Tversky, 1979），处置效应刻画“售盈持亏”'",
     "'风险态度的损益不对称[1]，处置效应刻画“售盈持亏”'", 1),
    ('R02', "'（Shefrin & Statman, 1985；Odean, 1998），业绩反馈引发的过度自信导致换手放大'",
     "'[2,3]，业绩反馈引发的过度自信导致换手放大'", 1),
    ('R03', "'（Puetz & Ruenzi, 2011），行业集中度体现配置的信息优势'",
     "'[4,23]，行业集中度体现配置的信息优势'", 1),
    ('R04', "'（Kacperczyk, Sialm & Zheng, 2005），持仓之外的主动行为可由调仓幅度捕捉'",
     "'[5]，持仓之外的主动行为可由调仓幅度捕捉'", 1),
    ('R05', "'（同前, 2008），择时能力可用分段回归检验（Henriksson & Merton, 1981），'",
     "'[6]，择时能力可用分段回归检验[7,24]，'", 1),
    ('R06', "'（Sharpe, 1966；Sortino & Price, 1994；Goetzmann et al., 2007）；'",
     "'[8,9,10]；'", 1),
    ('R07', "'经理与组织层面则有职业顾虑（Chevalier & Ellison, 1999）与规模不经济'",
     "'经理与组织层面则有职业顾虑[11]与规模不经济'", 1),
    ('R08', "'（Berk & Green, 2004）。这些结论在成熟市场已获验证，但在中国市场是否同样成立，'",
     "'[12]。这些结论在成熟市场已获验证，但在中国市场是否同样成立，'", 1),

    # ---- 主要发现（L354-355）----
    ('R09', "'其三，改进主动份额在六道检验中符号翻转，与 Frazzini, Friedman & Pomorski (2016) '",
     "'其三，改进主动份额在六道检验中符号翻转，与文献[13]的批评一致，剔除出画像。'", 1),
    ('R10', "'的批评一致，剔除出画像。最后刻画了业绩最好与最差 5% 的群体画像，'",
     "'最后刻画了业绩最好与最差 5% 的群体画像，'", 1),

    # ---- 表 1 文献依据列（L369-398）----
    ('R11', "'Chevalier & Ellison (1999)；Berk & Green (2004)'", "'[11]；[12]'", 1),
    ('R12', "'Ang, Chen & Xing (2006)；Shefrin & Statman (1985)；Odean (1998)；Puetz & Ruenzi (2011)'",
     "'[14]；[2]；[3]；[4]'", 1),
    ('R13', "'Kacperczyk, Sialm & Zheng (2005)；Chen & Wei (2025)'", "'[5]；[15]'", 1),
    ('R14', "'Kacperczyk, Sialm & Zheng (2008)；Henriksson & Merton (1981)'", "'[6]；[7]'", 1),
    ('R15', "'Sharpe (1966)；Sortino & Price (1994)；Goetzmann et al. (2007)'",
     "'[8]；[9]；[10]'", 1),
    ('R16', "'Wermers (2012)；Lakonishok, Shleifer & Vishny (1992)；Wermers (1999)'",
     "'[16]；[17]；[18]'", 1),

    # ---- 变量说明（L418-419）----
    ('R17', "'行业分类采用申万一级（31 行业，个股匹配率 99.2%）。因变量为 Fama & French (2015) '",
     "'行业分类采用申万一级（31 行业，个股匹配率 99.2%）。因变量为 Fama & French[19] '", 1),
    ('R18', "'五因子模型调整后的超额收益（alpha），其中国市场适用性经李志冰等 (2017) 检验支持。'",
     "'五因子模型调整后的超额收益（alpha），其中国市场适用性经文献[20]检验支持。'", 1),

    # ---- AS 裁决段（L582）补引 [25] Cremers & Petajisto ----
    ('R19', "'这与 Frazzini, Friedman & Pomorski (2016) 一致：控制基准后主动份额不具预测力。'",
     "'这与文献[13]一致：控制基准后主动份额不具预测力，文献[25]则持相反意见。'", 1),

    # ---- L2 扩展候选（L586-587）----
    ('R20', "'趋势外推偏差（持仓加权个股 12 月动量，Greenwood & Shleifer 2014）与有限关注度'",
     "'趋势外推偏差（持仓加权个股 12 月动量）[21]与有限关注度'", 1),
    ('R21', "'（持仓加权个股上月｜收益｜，Barber & Odean 2008）。二者基金层覆盖率均达 100%，'",
     "'（持仓加权个股上月｜收益｜）[22]。二者基金层覆盖率均达 100%，'", 1),

    # ---- 文献表：乱序 id -> 顺序编码 [1]-[25] ----
    ('R22',
     NL.join([
         "ref_ids = ['1', '15', '16', '59', '13', '30', '58', '57', '60', '45', '61',",
         "           '52', '53', '54', '34', '31', '55', '28', '23', '43', '26', '62',",
         "           '39']",
         "for i in ref_ids:",
         "    p = doc.add_paragraph()",
         "    r = p.add_run(f'[{i}] {REF[i]}')",
     ]),
     NL.join([
         "# 顺序编码制（GB/T 7714）：按正文首次引用顺序编号 [1]–[25]，不再使用底库散乱 id",
         "ref_ids = %r" % (REF_ORDER,),
         "for _n, i in enumerate(ref_ids, 1):",
         "    p = doc.add_paragraph()",
         "    r = p.add_run(f'[{_n}] {REF[i]}')",
     ]).replace('[', '[').replace("'", "'"), 1),
]


def step2():
    s = rd(DOCXPY)
    orig = s
    for cid, old, new, want in REPS:
        got = s.count(old)
        if got != want:
            print('[FAIL] %s 命中 %d 次（期望 %d），已中止，未写入任何改动' % (cid, got, want))
            print('       old = %r' % old[:80])
            return 2
        s = s.replace(old, new)
        print('[OK] %-4s %+d 字符' % (cid, len(new) - len(old)))
    if s == orig:
        print('[Step2] 无改动')
        return 0
    bak = DOCXPY + '.bak_refs_20260830'
    if not os.path.exists(bak):
        wr(bak, orig)
    wr(DOCXPY, s)
    print('[Step2] 已写入；备份 %s' % os.path.basename(bak))
    return 0


if __name__ == '__main__':
    step1()
    sys.exit(step2())
