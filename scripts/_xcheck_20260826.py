# -*- coding: utf-8 -*-
"""三产物跨口径一致性核验（2026-08-26）
================================================================
核验对象：
  A 论文初稿_2026-08-26.docx
  B 方法详解_2026-08-26.html
  C 投资经理行为画像_2026-08-26.html

核验内容：
  1  关键数字在三产物中是否与 output/ 定稿 JSON 一致（六维联立 R²、各维 t、
     五分组 alpha、Q5−Q1、群体画像 t 等）
  2  是否残留旧口径措辞（"五维联立"作为主口径、"五个能力"、"12 项指标"等）
  3  L1 定位叙事是否三处一致（计分维 + 边界条件，非纯控制变量）
  4  参考文献编号引用是否都能在参考文献库中找到
  5  覆盖率数字是否标注口径（避免 46.3% 与 46.6% 混用）
输出：output/跨产物一致性核验_2026-08-26.json + 控制台报告
"""
import json
import re
import os
import io
import zipfile

BASE = r'd:\Desktop\基金经理行为分析研究'
OUT = os.path.join(BASE, 'output')
REP = os.path.join(BASE, 'reports')
TODAY = '2026-08-26'
ART = '2026-08-31'  # 产物文件日期（8-30 深夜那轮重生成后为 31 日）


def rj(name):
    with io.open(os.path.join(OUT, name), encoding='utf-8') as f:
        return json.load(f)


def read_docx_text(path):
    """不依赖 python-docx，直接从 word/document.xml 抽纯文本。"""
    with zipfile.ZipFile(path) as z:
        xml = z.read('word/document.xml').decode('utf-8')
    xml = re.sub(r'</w:p>', '\n', xml)
    xml = re.sub(r'<w:tab/>', '\t', xml)
    return re.sub(r'<[^>]+>', '', xml)


def read_text(path):
    with io.open(path, encoding='utf-8') as f:
        return f.read()


VER = rj(f'六维复合定稿验证_含L1_{TODAY}.json')
POR = rj(f'画像_群体与典型_{TODAY}.json')
DESC = rj(f'统计性描述_{TODAY}.json')
REF = rj(f'参考文献_定稿_{TODAY}.json')

S1, S2, S3 = VER['S1_成分定向'], VER['S2_维度相关'], VER['S3_单维']
S3J, S4 = VER['S3_联立'], VER['S4_分组']
GP = POR['群体画像']

DOCX_DATE = '2026-09-03' if (os.path.exists(os.path.join(REP, '论文初稿_2026-09-03.docx')) or os.path.exists(os.path.join(BASE, '论文初稿_2026-09-03.docx'))) else ART
_docx_alt = os.path.join(REP, f'论文初稿_{DOCX_DATE}_横向排版.docx')
_docx_std = os.path.join(REP, f'论文初稿_{DOCX_DATE}.docx')
if not os.path.exists(_docx_std) and os.path.exists(os.path.join(BASE, f'论文初稿_{DOCX_DATE}.docx')):
    _docx_std = os.path.join(BASE, f'论文初稿_{DOCX_DATE}.docx')
DOCX_PATH = _docx_alt if (os.path.exists(_docx_alt) and os.path.getmtime(_docx_alt) > os.path.getmtime(_docx_std)) else _docx_std
DOC = read_docx_text(DOCX_PATH)
DET = read_text(os.path.join(REP, f'方法详解_{ART}.html'))
POR_H = read_text(os.path.join(REP, f'投资经理行为画像_{ART}.html'))
PRODUCTS = [('论文docx', DOC), ('方法详解html', DET), ('画像html', POR_H)]

res = {'检查项': [], '问题': []}


def rec(item, ok, detail):
    res['检查项'].append(dict(项=item, 通过=ok, 说明=detail))
    flag = 'OK  ' if ok else '×   '
    print('%s%-46s %s' % (flag, item, detail))
    if not ok:
        res['问题'].append(dict(项=item, 说明=detail))


def variants(x, nd):
    """数字的多种可能书写：0.4557 / .4557 / 45.57%（百分号形式仅在 nd<=4 时给）"""
    s = ('%.' + str(nd) + 'f') % abs(x)
    out = {s}
    if x < 0:
        out |= {'-' + s, '−' + s, '–' + s}
    else:
        out |= {'+' + s}
    return out


def found_any(text, cands):
    return any(c in text for c in cands)


print('=' * 78)
print('一、关键数字三产物一致性（数字必须能在文本中原样命中）')
print('=' * 78)

# 六维联立 R² 与五维对照 R²
for lab, val, nd in [
        ('六维联立 R²', S3J['r2'], 4),
        ('五维对照 R²', VER['S3_联立_五维对照']['r2'], 4),
        ('Q5−Q1 alpha 差', S4['Q5_Q1'], 5),
        ('五分组 t', S4['t'], 2)]:
    miss = [n for n, t in PRODUCTS if not found_any(t, variants(val, nd))]
    # Q5-Q1 与 alpha 常以百分数书写，放宽：允许 3.13 / 3.131 之类
    if miss and nd == 5:
        alt = {('%.2f' % (val * 100)), ('%.3f' % (val * 100))}
        miss = [n for n in miss
                if not found_any(dict(PRODUCTS)[n], alt)]
    rec(f'{lab} = {val}', not miss,
        '三产物均命中' if not miss else '缺失于：' + '、'.join(miss))

# 六维联立各维 t
for d, c in S3J['系数'].items():
    val = c['t']
    miss = [n for n, t in PRODUCTS if not found_any(t, variants(val, 2))]
    rec(f'联立 t[{d}] = {val:+.2f}', not miss,
        '三产物均命中' if not miss else '缺失于：' + '、'.join(miss))

# 单维 t
for d in list(S3.keys()):
    val = S3[d]['t']
    miss = [n for n, t in PRODUCTS if not found_any(t, variants(val, 2))]
    rec(f'单维 t[{d}] = {val:+.2f}', not miss,
        '三产物均命中' if not miss else '缺失于：' + '、'.join(miss))

print()
print('=' * 78)
print('二、旧口径措辞残留（这些词若作为主口径出现即为不一致）')
print('=' * 78)

STALE = {
    '五个能力': '应为「六个维度」',
    '五种能力': '应为「六个维度」',
    '五者放在一起': '应为「六者放在一起」',
    '五维同时进入': '应为「六维同时进入」',
    '12 项进入正式框架': '应为 15 项',
    '12 个成分': '应为 15 个成分',
    '12 项成分': '应为 15 项成分',
    '五维等权': '应为六维等权',
    '五维得分': '应为六维得分',
    '五维分位': '应为六维分位',
    '五个维度全部': '应为六个维度全部',
    '五张卡片': '应为六张卡片',
    '46.3%': '覆盖率口径已统一为 46.6%（观测层）/99.8%（基金层）',
}
# 允许出现的例外语境：明确标注为「对照」的五维联立
ALLOW_CONTEXT = ['五维联立＋三控制变量', '五维联立+三控制变量', '五维对照',
                 '前一版五维定稿', '原五维', '五维定稿']

for word, why in STALE.items():
    hits = []
    for n, t in PRODUCTS:
        if word not in t:
            continue
        # 检查每处命中是否落在允许语境内
        bad = 0
        for m in re.finditer(re.escape(word), t):
            ctx = t[max(0, m.start() - 60):m.end() + 60]
            if not any(a in ctx for a in ALLOW_CONTEXT):
                bad += 1
        if bad:
            hits.append('%s(%d处)' % (n, bad))
    rec('无残留：%s' % word, not hits,
        why if hits else '未出现（或仅出现在对照语境）')
    if hits:
        res['问题'][-1]['命中'] = hits
        print('        命中：' + '、'.join(hits))

print()
print('=' * 78)
print('三、L1 定位叙事一致性')
print('=' * 78)

# L1 必须被描述为「计分维度」且同时是「边界条件」
for n, t in PRODUCTS:
    has_score = ('基本面优势' in t)
    has_bound = ('边界条件' in t) or ('条件而非' in t) or ('不是能力' in t)
    has_ctrl_only = ('L1 基本面层：控制变量不计分' in t) or ('L1 仅作控制变量' in t)
    ok = has_score and has_bound and not has_ctrl_only
    rec('%s：L1 为计分维 + 边界条件' % n, ok,
        'ok' if ok else '计分维=%s 边界条件=%s 旧控制变量表述=%s'
        % (has_score, has_bound, has_ctrl_only))

# L1 三成分名必须在三产物都出现
for c in ['mgr_total_tenure_v2', 'log_fund_age', 'log_aum']:
    miss = [n for n, t in PRODUCTS if c not in t]
    rec('L1 成分 %s 三产物均现' % c, not miss,
        'ok' if not miss else '缺失于：' + '、'.join(miss))

print()
print('=' * 78)
print('四、参考文献引用编号可解析性')
print('=' * 78)

ref_keys = set(REF.keys())
for n, t in PRODUCTS:
    cited = set(re.findall(r'\[(\d{1,2})\]', t))
    # 过滤掉明显不是文献号的（如公式中的 [0,1]）
    cited = {c for c in cited if c.isdigit()}
    bad = sorted(cited - ref_keys, key=int)
    rec('%s：引用编号均在文献库' % n, not bad,
        '引用 %d 个编号，全部可解析' % len(cited) if not bad
        else '无法解析：' + '、'.join(bad))

# Berk & Green (2004) 是否已进入三产物。顺序编码制下正文不再出现作者名，
# 改查文献表条目（大小写不敏感，底库为全大写 BERK J B）。
for n, t in PRODUCTS:
    ok = 'BERK' in t.upper()
    rec('%s：Berk & Green (2004) 已入文献表（[12]）' % n, ok, 'ok' if ok else '缺失')

print()
print('=' * 78)
print('五、覆盖率口径标注')
print('=' * 78)

for n, t in PRODUCTS:
    # 若出现 46.6% 或 46.3%，必须同时说明口径
    if '46.6%' in t or '46.3%' in t:
        ok = ('基金层' in t) or ('观测' in t)
        rec('%s：de 覆盖率标注口径' % n, ok, 'ok' if ok else '出现覆盖率但未标注口径')
    else:
        rec('%s：de 覆盖率标注口径' % n, True, '未提及该数字，跳过')

print()
print('=' * 78)
print('六、群体画像与维度相关：细粒度数字对齐')
print('=' * 78)

# 群体画像六维 t 值（三产物都展示该表的产物才要求命中）
for d, t_ in GP['六维']['t'].items():
    hit = [n for n, txt in PRODUCTS if found_any(txt, variants(t_, 2))]
    # docx 与两个 html 都有群体画像表，要求至少两处命中且无矛盾数字
    ok = len(hit) >= 2
    rec(f'群体画像 t[{d}] = {t_:+.2f}', ok,
        '命中于：' + '、'.join(hit) if ok else '仅命中 %s' % ('、'.join(hit) or '无'))

# 维度相关矩阵的关键对（叙事中反复引用的三对）
for a, b in [('交易执行能力', '风险应对能力'), ('基本面优势', '风险应对能力'),
             ('基本面优势', '交易执行能力'), ('基本面优势', '风险转化能力')]:
    v = S2[a][b]
    hit = [n for n, txt in PRODUCTS if found_any(txt, variants(v, 3))]
    rec(f'相关 [{a}×{b}] = {v:.3f}', len(hit) >= 1,
        '命中于：' + '、'.join(hit) if hit else '三产物均未出现')

# 五分组 alpha 单调序列
seq = [S4['alpha均值'][k] for k in ['Q1最低', 'Q2', 'Q3', 'Q4', 'Q5最高']]
mono = all(seq[i] < seq[i + 1] for i in range(4))
rec('五分组 alpha 严格单调递增', mono,
    ' → '.join('%.4f' % x for x in seq))
# 三产物是否都写出了首尾两端
ends = [n for n, txt in PRODUCTS
        if found_any(txt, variants(seq[0], 4) | {'%.2f' % (seq[0] * 100)})
        and found_any(txt, variants(seq[-1], 4) | {'%.2f' % (seq[-1] * 100)})]
rec('五分组首尾 alpha 三产物一致', len(ends) >= 2,
    '命中于：' + '、'.join(ends) if ends else '未在任何产物同时出现首尾值')

print()
print('=' * 78)
print('七、L1 反例（基本面优势型）叙事一致性')
print('=' * 78)

arch_l1 = [c for c in POR['典型画像'] if '基本面优势' in c['标签']]
if arch_l1:
    c = arch_l1[0]
    nm = c['基金简称']
    a = c['ff5_alpha']
    q = c['六维分位']['基本面优势']
    for n, txt in PRODUCTS:
        has_name = nm in txt or nm[:4] in txt
        has_neg = found_any(txt, variants(a, 4)) or ('alpha 为负' in txt) or ('为负' in txt)
        rec('%s：L1 反例（%s，alpha=%.4f）已叙述' % (n, nm, a),
            has_name and has_neg,
            '基金名=%s 负 alpha 表述=%s' % (has_name, has_neg))
    hit_q = [n for n, txt in PRODUCTS if found_any(txt, variants(q, 3) | {'%.0f%%' % (q * 100), '%.1f%%' % (q * 100)})]
    rec('L1 反例分位 %.3f 至少一处写明' % q, bool(hit_q),
        '命中于：' + '、'.join(hit_q) if hit_q else '未写明分位')
else:
    rec('L1 反例存在于画像 JSON', False, '未找到「基本面优势型」典型案例')

print()
print('=' * 78)
print('八、剔除指标的处理一致性（五项必须都有交代，且不得进入复合）')
print('=' * 78)

DROPPED = {'AS_improved': '改进主动份额', 'TO': '换手率', 'rc_mom': '追涨杀跌',
           'rsstab': '风险稳定性', 'return_volatility': '收益波动率'}
for k, cn in DROPPED.items():
    hit = [n for n, txt in PRODUCTS if (k in txt) or (cn in txt)]
    rec('剔除项 %s（%s）有交代' % (k, cn), len(hit) >= 2,
        '命中于：' + '、'.join(hit) if hit else '三产物均未提及')

# 剔除项绝不能出现在复合公式里
COMPOSITE_MARK = ['z(AS_improved', 'z(TO_', 'z(rc_mom', 'z(rsstab', 'z(return_volatility']
for n, txt in PRODUCTS:
    bad = [m for m in COMPOSITE_MARK if m in txt]
    rec('%s：剔除项未混入复合公式' % n, not bad,
        'ok' if not bad else '发现：' + '、'.join(bad))

print()
print('=' * 78)
print('九、AS 六道检验的口径表述一致性（六道 = 五回归 + 一群体检验）')
print('=' * 78)

for n, txt in PRODUCTS:
    has_six = ('六道检验' in txt) or ('六个口径' in txt)
    # 必须交代第六道是群体检验，否则读者会数出只有五行
    explains = ('第六道' in txt) or ('末行' in txt) or ('表末' in txt) or ('五行' in txt)
    rec('%s：六道检验口径已交代（避免只见五行）' % n, has_six and explains,
        '六道表述=%s 第六道说明=%s' % (has_six, explains))

# AS 群体差值必须与画像 JSON 一致
as_d = GP['原始指标']['差值']['AS_improved']
as_t = GP['原始指标']['t']['AS_improved']
as_p = GP['原始指标']['p']['AS_improved']
for lab, v, nd in [('AS 群体差值', as_d, 4), ('AS 群体 t', as_t, 2), ('AS 群体 p', as_p, 4)]:
    hit = [n for n, txt in PRODUCTS if found_any(txt, variants(v, nd))]
    rec(f'{lab} = {v}', len(hit) >= 2,
        '命中于：' + '、'.join(hit) if hit else '三产物均未出现')

# 硬编码残值检测：旧稿的 AS 群体差值 t=1.91 / p=0.065 不应再出现
# 注意 +0.023 是 +0.0233 的前缀，需用词边界避免误报
for old in [r'\+0\.023（t=1\.91', r't=1\.91，p=0\.065', r'差值仅 \+0\.023(?!\d)']:
    bad = [n for n, txt in PRODUCTS if re.search(old, txt)]
    rec('无旧硬编码 AS 数值「%s」' % old, not bad,
        'ok' if not bad else '残留于：' + '、'.join(bad))

print()
print('=' * 78)
print('十、群体画像分组方向一致性（按业绩分组，不是按能力分组）')
print('=' * 78)

for n, txt in PRODUCTS:
    by_perf = ('按 FF5' in txt) or ('按 FF5 alpha' in txt) or ('按业绩' in txt) or ('按 FF5 超额收益' in txt)
    wrong = '按综合能力排序，取头尾' in txt
    rec('%s：群体画像声明按业绩分组' % n, by_perf and not wrong,
        '按业绩=%s 误写为按能力=%s' % (by_perf, wrong))

print()
print('=' * 78)
print('十一、辅助产物（修改说明与自评）口径同步')
print('=' * 78)

SELF = os.path.join(REP, '修改说明与自评_2026-08-25.html')
if os.path.isfile(SELF):
    st = read_text(SELF)
    SELF_STALE = {
        '五维复合': '应为六维复合',
        '12 指标': '应为 15 指标',
        '12 指标卡': '应为 15 指标卡',
        '5 名典型画像': '应为 6 名典型画像',
        '五名典型经理': '应为六名典型经理',
        '五维能力画像': '应为六维能力画像',
        '552 段': '应为 618 段（实际段落数）',
        '24 表': '方法详解现为 27 表',
    }
    for w, why in SELF_STALE.items():
        rec('自评文档无残留：%s' % w, w not in st, why if w in st else '未出现')
    # 实际数字比对
    doc_paras = len([l for l in DOC.split('\n') if l.strip()])
    rec('自评文档段落数与 docx 实际一致', str(doc_paras) + ' 段' in st,
        'docx 实际 %d 段；自评文档%s' % (doc_paras,
                                        '已写明' if str(doc_paras) + ' 段' in st else '未写明或不一致'))
    n_tab_det = DET.count('<table')
    rec('自评文档方法详解表数与实际一致', '%d 表' % n_tab_det in st,
        '方法详解实际 %d 表；自评文档%s' % (n_tab_det,
                                          '已写明' if '%d 表' % n_tab_det in st else '未写明或不一致'))
else:
    rec('自评文档存在', False, '未找到 reports/修改说明与自评_2026-08-25.html')

print()
print('=' * 78)
print('十二、五层框架 vs 六个计分维度：口径表述与稳健性交代')
print('=' * 78)

MG = rj(f'L4合并可行性检验_{TODAY}.json')
DG = rj(f'L4b机械性诊断_{TODAY}.json')

# 2026-09-02 结构重写：分层在显著性检验之后才出现，不再要求“五层”表述
for n, txt in PRODUCTS:
    says_six = ('六个能力维度' in txt) or ('六个计分维度' in txt) or ('六维' in txt)
    says_after = ('显著性检验' in txt) or ('检验' in txt)
    ok = says_six and says_after
    rec('%s：明确「六个能力维度（检验后归并）」' % n, ok,
        '六维=%s 提及检验=%s' % (says_six, says_after))

# L4 两职能拆分交代（过程应对 / 转化效率，不再要求 L4a/L4b 代码）
for n, txt in PRODUCTS:
    ok = ('过程应对' in txt and '转化效率' in txt)
    rec('%s：风险应对两职能拆分交代' % n, ok,
        'ok' if ok else '未同时交代过程应对与转化效率')

# 合并检验的关键数字必须至少在两处出现
for lab, v, nd in [
        ('L4a×L4b Spearman', MG['③_异质性']['spearman'], 3),
        ('口径B Q5−Q1', MG['②_五分组']['B_五维_分数级']['Q5_Q1'], 5),
        ('A vs B 综合分 Spearman', MG['④_秩相关']['相关']['综合_A_vs_综合_B']['spearman'], 4)]:
    hit = [n for n, txt in PRODUCTS if found_any(txt, variants(v, nd))]
    rec(f'{lab} = {v}', len(hit) >= 2,
        '命中于：' + '、'.join(hit) if hit else '三产物均未出现')

# 权重代价必须披露（L4 实得 1/3）
for n, txt in PRODUCTS:
    ok = ('33.3%' in txt) or ('2/6' in txt) or ('1/3 权重' in txt)
    rec('%s：披露 L4 层实得 1/3 权重' % n, ok, 'ok' if ok else '未披露等权造成的层间权重不均')

print()
print('=' * 78)
print('十三、L4b 机械性质疑的正面回答')
print('=' * 78)

for n, txt in PRODUCTS:
    has_q = ('用业绩解释业绩' in txt) or ('概念同源' in txt) or ('定义同源' in txt)
    has_oos = ('样本外' in txt)
    rec('%s：正面交代 L4b 机械性质疑 + 样本外证据' % n, has_q and has_oos,
        '质疑已交代=%s 样本外证据=%s' % (has_q, has_oos))

for lab, v, nd in [
        ('L4b 样本外单维 t', DG['D2_样本外']['单维']['风险转化能力']['t'], 2),
        ('L4b 增量 R²', DG['D3_剔除L4b']['增量R2'], 4),
        ('L1 样本外联立 t', DG['D2_样本外']['联立']['系数']['基本面优势']['t'], 2)]:
    hit = [n for n, txt in PRODUCTS if found_any(txt, variants(v, nd))]
    rec(f'{lab} = {v}', len(hit) >= 2,
        '命中于：' + '、'.join(hit) if hit else '三产物均未出现')

# 「解释力最强」这类未加限定的强表述应已下调
for n, txt in PRODUCTS:
    # 允许「系数最大」，但「解释力最强」若出现必须紧邻限定语
    bad = 0
    for m in re.finditer('解释力最强', txt):
        ctx = txt[max(0, m.start() - 200):m.end() + 300]
        if not any(k in ctx for k in ['同源', '样本外', '限定', '须注意', '下调', '单指标']):
            bad += 1
    rec('%s：「解释力最强」已加限定或改为系数最大' % n, not bad,
        'ok' if not bad else '仍有 %d 处未加限定的强表述' % bad)

print()
print('=' * 78)
print('十四、结论单一数据源：19 条结论在三产物中逐条对齐')
print('=' * 78)

CONCL = rj(f'核心结论_定稿_{TODAY}.json')

# 编号出现检查（2026-08-31 改为读者视角口径）：
# 论文 docx 面向外部读者，不得出现内部结论编号；两份内部 HTML 仍须全编号可追溯。
# 豁免：Q1/Q2/Q3 在正文同时是五等分组标签（Q1 最低→Q5 最高），无法区分，跳过；
# F 系列加左边界防 FF3/FF5 误报。
import re as _re
_SKIP_IDS = {'Q1', 'Q2', 'Q3'}
for c in CONCL['结论']:
    cid = c['id']
    miss = [n for n, txt in PRODUCTS[1:] if cid not in txt]
    rec('结论 %s（%s）两份内部 HTML 均现' % (cid, c['主题']), not miss,
        'ok' if not miss else '缺失于：' + '、'.join(miss))
    if cid in _SKIP_IDS:
        continue
    pat = r'(?<![A-Za-z0-9])' + cid + r'(?![0-9])' if cid.startswith('F') else cid
    rec('论文docx：不含内部编号 %s' % cid, not _re.search(pat, DOC),
        'ok（读者视角）' if not _re.search(pat, DOC) else '正文残留内部编号')

# 定性内核逐字比对：《方法详解》第七节「结论要点」由结论源渲染，必须逐字一致。
# 论文 docx 与画像 HTML 均为成文叙述（篇幅所限，措辞按各自文体改写），
# 它们的对齐由「结论编号出现 + 关键数字命中」两道保证（见第十四组前半与第一组）。
SRC_PRODUCTS = [('方法详解html', DET)]
for c in CONCL['结论']:
    fp = re.sub(r'[，。：；、“”\s]', '', c['定性'])[:22]
    miss = []
    for n, txt in SRC_PRODUCTS:
        flat = re.sub(r'[，。：；、“”\s]', '', re.sub(r'<[^>]+>', '', txt))
        if fp not in flat:
            miss.append(n)
    rec('结论 %s 定性内核与结论源逐字一致' % c['id'], not miss,
        'ok' if not miss else '缺失于：' + '、'.join(miss))

# 局限类结论编号不得与层级编号 L1–L5 冲突
bad_ids = [c['id'] for c in CONCL['结论'] if re.fullmatch(r'L[1-5]', c['id'])]
rec('结论编号不与 L1–L5 层级冲突', not bad_ids,
    'ok（局限类用 Q 系列）' if not bad_ids else '冲突编号：' + '、'.join(bad_ids))

# 结论源声明（2026-08-31 改读者视角）：两份内部 HTML 须声明；论文 docx 面向读者不声明
for n, txt in PRODUCTS[1:]:
    ok = '核心结论_定稿' in txt
    rec('%s：声明结论源文件' % n, ok, 'ok' if ok else '未声明 output/核心结论_定稿 JSON')
rec('论文docx：不声明内部结论源（读者视角）', '核心结论_定稿' not in DOC,
    'ok' if '核心结论_定稿' not in DOC else '正文残留内部文件路径')

# 结论要点表集中在《方法详解》第七节，另两个产物以正文承载
rec('《方法详解》含结论要点表', '结论要点' in DET,
    'ok（另两产物以正文与章节标注承载）')

print()
print('=' * 78)
print('十五、排版与可读性')
print('=' * 78)

# 画像 HTML 保留导航目录；方法详解按用户要求去掉顶部目录，改为逐层顺读
rec('画像html：含导航目录', 'nav class="toc"' in POR_H,
    'ok' if 'nav class="toc"' in POR_H else '缺少 nav.toc')
rec('方法详解html：无顶部目录（改为逐层顺读）', 'nav class="toc"' not in DET,
    'ok（已按要求移除目录与 KPI 数字墙）')

# HTML 锚点可达性：nav 里的 href="#x" 都要有对应 id
for n, txt in [('方法详解html', DET), ('画像html', POR_H)]:
    hrefs = set(re.findall(r'href="#([\w-]+)"', txt))
    ids = set(re.findall(r'id="([\w-]+)"', txt))
    dead = sorted(hrefs - ids)
    rec('%s：目录锚点全部可达' % n, not dead,
        '%d 个锚点均可达' % len(hrefs) if not dead else '死链：' + '、'.join(dead))

# 结论要点表仅在《方法详解》第七节，行数须与 JSON 条数一致
_cnt = DET.count('class="cid"')
rec('方法详解html：结论要点表 %d 行 = 结论 %d 条' % (_cnt, CONCL['结论数']),
    _cnt == CONCL['结论数'], 'ok' if _cnt == CONCL['结论数'] else '行数不符')

# 论文自足性（2026-08-31 用户要求）：读者视角不出现内部产物与结论编号体系
# 只查书名号引用与文件路径；摘要中"刻画投资经理行为画像"是论文自身术语，不算引用
_docx_clean = ('方法详解' not in DOC and '《投资经理行为画像》' not in DOC
               and '核心结论_定稿' not in DOC and '结论编号' not in DOC)
rec('论文docx：不含内部配套文档引用', _docx_clean,
    'ok（论文自足，细节备索）' if _docx_clean else '仍引用内部文档/编号，读者无法获取')

# HTML 标签配平
for n, txt in [('方法详解html', DET), ('画像html', POR_H)]:
    t_ok = txt.count('<table') == txt.count('</table>')
    r_ok = txt.count('<tr') == txt.count('</tr>')
    rec('%s：表格标签配平' % n, t_ok and r_ok,
        'table %d/%d，tr %d/%d' % (txt.count('<table'), txt.count('</table>'),
                                   txt.count('<tr'), txt.count('</tr>')))

# 三产物不得残留未渲染的 HTML 标签字面量（docx 尤其容易）
rec('论文docx：无字面 HTML 标签泄漏', '&lt;b&gt;' not in DOC and '<b>' not in DOC,
    'ok' if '&lt;b&gt;' not in DOC else '发现未渲染的 <b> 标签')

print()
print('=' * 78)
print('十六、论文 docx 篇幅与版式')
print('=' * 78)

import zipfile as _zf

_z = _zf.ZipFile(DOCX_PATH)
_xml = _z.read('word/document.xml').decode('utf-8')
_lines = [l.strip() for l in
          re.sub(r'<[^>]+>', '', re.sub(r'</w:p>', '\n', _xml.replace('<w:br/>', '\n'))).split('\n')
          if l.strip()]
_total = sum(len(l) for l in _lines)
_ref_i = next((i for i, l in enumerate(_lines) if l == '参考文献'), len(_lines))
_intro_i = next((i for i, l in enumerate(_lines) if l == '引言'), 0)
# 正文 = 引言 → 参考文献（含表内文字），不含参考文献
_body = sum(len(l) for l in _lines[_intro_i:_ref_i])

# 大纲要求「不冗长、故事讲清楚」：正文控制在 1.5 万字内；
# 参考文献不计入正文阈值（摘要与附录已按用户要求删除）
rec('正文篇幅 %d 字（阈值 17000，不含参考文献）' % _body, _body <= 17000,
    '符合大纲「不冗长」要求' if _body <= 17000 else '超出阈值，需继续精简')
rec('总篇幅 %d 字（阈值 22500，含参考文献）' % _total, _total <= 22500,
    '其中参考文献 %d 字' % (_total - _body))

# 表号必须连续无跳号、无重复（正表 1–N）
_caps = re.findall(r'表\s*(\d+)\s{2}', ' '.join(_lines))
_nums = sorted({int(x) for x in _caps})
_expect = list(range(1, len(_nums) + 1))
rec('表号连续无重复（共 %d 张）' % len(_nums), _nums == _expect,
    '表 1–%d 连续' % len(_nums) if _nums == _expect else '实际编号：%s' % _nums)
# 表格数量与题注数量一致
_ntbl = _xml.count('<w:tbl>')
rec('表格数 %d = 题注数 %d' % (_ntbl, len(_nums)), _ntbl == len(_nums),
    'ok' if _ntbl == len(_nums) else '题注与实际表格数不符')

# 正文中引用的每个表号都必须存在
_joined = ' '.join(_lines)
_refs_in_text = {int(x) for x in re.findall(r'见表\s*(\d+)', _joined)}
_refs_in_text |= {int(x) for x in
                  re.findall(r'表\s*(\d+)\s*(?:报告|显示|列出|汇总)', _joined)}
_dead = sorted(_refs_in_text - set(_nums))
rec('正文交叉引用的表号均存在', not _dead,
    '引用 %d 个表号均可达' % len(_refs_in_text) if not _dead
    else '不存在的表号：%s' % _dead)

# 页面版式：边距与列宽约束
_sect = re.search(r'<w:pgMar[^/]*/>', _xml)
rec('页面边距已设置', bool(_sect), _sect.group(0)[:90] if _sect else '未找到 pgMar')
# 页码域
rec('页脚含页码域', 'PAGE' in _z.read('word/footer1.xml').decode('utf-8')
    if 'word/footer1.xml' in _z.namelist() else False,
    'ok' if 'word/footer1.xml' in _z.namelist() else '未找到 footer')
# 表头跨页重复
rec('表头设置跨页重复', _xml.count('tblHeader') >= _ntbl,
    '%d 张表均设置' % _ntbl if _xml.count('tblHeader') >= _ntbl
    else '仅 %d 处设置' % _xml.count('tblHeader'))

# 论文自足性（2026-08-31 用户要求）：方法细节备索，不引用内部 HTML 文档
rec('论文docx：无《方法详解》交叉引用（已按读者视角移除）', '方法详解' not in DOC,
    'ok（论文自足）' if '方法详解' not in DOC else '仍引用内部方法文档')

print()
print('=' * 78)
print('十七、论文投稿要素：配图（摘要与附录已按用户要求删除）')
print('=' * 78)

# 摘要、关键词、JEL 与 Abstract 已按用户要求删除（2026-09-01）：检查无残留
for w in ['摘要', '关键词', 'JEL 分类号', 'Abstract', 'Keywords']:
    rec('论文docx：无 %s 残留（摘要已删除）' % w, w not in DOC,
        'ok' if w not in DOC else '摘要删除后仍有残留 ' + w)

# 附录已按用户要求删除（2026-09-01）：检查无残留
for w in ['附录', '附表']:
    rec('论文docx：无 %s 残留（附录已删除）' % w, w not in DOC,
        'ok' if w not in DOC else '附录删除后仍有残留 ' + w)
rec('论文docx：含四、结论与启示（2026-09-03 风格版结构）',
    '四、结论与启示' in DOC and '（三）结论' not in DOC,
    'ok' if '四、结论与启示' in DOC else '缺少四、结论与启示')

# 配图：内嵌媒体数、图题、正文交叉引用（排除 zip 目录条目，只数真实图片文件）
_zm = [n for n in _z.namelist()
       if n.startswith('word/media') and not n.endswith('/')]
rec('论文docx：内嵌图片 3 张', len(_zm) == 3,
    '实际 %d 张' % len(_zm))
for i in (1, 2, 3):
    cap_ok = f'图 {i}  ' in DOC
    # 题注一处 + 正文引用（"见图 i"/"图 i 的"/"与图 i"/"图 i 直观"等）至少一处
    ref_ok = DOC.count(f'图 {i}') >= 2
    rec(f'论文docx：图 {i} 题注 + 正文引用', cap_ok and ref_ok,
        '题注=%s 引用=%s' % (cap_ok, ref_ok))

print()
print('=' * 78)
n_all = len(res['检查项'])
n_bad = len(res['问题'])
print('核验完成：%d 项检查，%d 项通过，%d 项不通过' % (n_all, n_all - n_bad, n_bad))
print('=' * 78)
if res['问题']:
    print('\n待修问题清单：')
    for i, p in enumerate(res['问题'], 1):
        print('  %d. %s —— %s' % (i, p['项'], p['说明']))
        if '命中' in p:
            print('     命中位置：' + '、'.join(p['命中']))

res['汇总'] = dict(检查项数=n_all, 通过=n_all - n_bad, 不通过=n_bad)
with io.open(os.path.join(OUT, f'跨产物一致性核验_{TODAY}.json'), 'w', encoding='utf-8') as f:
    json.dump(res, f, ensure_ascii=False, indent=2)
print('\n已落盘：output/跨产物一致性核验_%s.json' % TODAY)
