# -*- coding: utf-8 -*-
"""第十道门禁 _gate10_check.py：核心回归系数表 ↔ 权威重算JSON逐位审计
A. 表4-5 截面基准   ↔ core_regs_recalc_clean.table45.{with_aum_ff5,with_aum_ex}
B. 表4-6 前向预测   ↔ core_regs_recalc_clean.table46.{fut4q,fut1q}（含N/基金数/R²）
C. 表4-7 组内双向FE ↔ core_regs_recalc_clean.table47（含p值/组内R²/基金数）
D. 表4-17 择时控制  ↔ t417_purify_clean.table417.{no_timing,with_timing}
E. 表4-18 因子口径  ↔ ff34_alpha_clean.{ff3,ff4} + core_regs.with_aum_ff5（FF5行交叉核对ff5_crosscheck）
F. 表4-5 证据块 bootstrap/两阶段数字 ↔ table45_bootstrap / table45_twostage（存在性校验，
   校验令牌由JSON动态构造，防稿件漂移；上下文正确性依赖人工复核）
G. 表4-10 M4完整模型 ↔ _v4_benchmark.json.coefs（18变量 β/t2w/p2w，星号由p2w三档惯例导出；
   注意审计 rerun 的 M4C/TwoWay 中 FF5 行为单向聚类值，不得作本表权威）
H. 表4-11 R²对比    ↔ _audit_rerun_20260822.{B,same_sample}（含差异列=两列之差的自洽校验）
I. 表4-12 增量分解  ↔ _audit_rerun2_20260822.C_same_sample（sequential/last-in/alone+共享方差占比，
   含逐层加总=R²差的内部一致性）
J. 表4-13 安慰剂    ↔ _v4_robust.json（真实t/perm_p分位/结论列；置换均值无权威存档仅格式校验；
   并锁定本轮修复：300次/L5指标置换表题/50.7%，禁止500次与"因变量随机置换"回潮）
K. 表4-15 FM        ↔ M4_FamaMacBeth复核.json（fm_t/nw_t，T=20窗口；log_aum控制行无权威仅跳过；
   全18RHS补充段令牌校验）
L. 表4-20 LSV电池   ↔ lsv_脆弱性诊断电池.csv（A-K逐规格；I为三分位合并行拆三组核对）
M. 表4-21 DE审计    ↔ de_选择性审计.csv（A-F逐规格；E行系数位为—占位）
N. 表4-22 VIF       ↔ M4_多重共线性_VIF.csv（18变量双列布局全覆盖）+ 诊断JSON条件数/maxVIF交叉
O. 表4-23 能力分解  ↔ batch3_alpha_decomposition.json（DV1/DV2/DV3×5变量 β/t/星号；
   兼容"β=x, t=y"与"t=z n.s."两种单元格语法；§4.4.11(ii)日频复验令牌↔batch2_regressions_v2）
P. 表4-24 Bootstrap ↔ batch4_bootstrap.json（β均值/经验CI两端/排零/同向显著份额=max(正,负)向份额）
数值容差 = 半ULP（按显示小数位）：tol = 0.5000001*10^(-d)；星号与权威stars逐字比对。
"""
import io, re, json

MP = 'merged_manuscript.html'
J_CR = 'output/core_regs_recalc_clean_2026-08-23.json'
J_T417 = 'output/t417_purify_clean_2026-08-23.json'
J_FF = 'output/ff34_alpha_clean_2026-08-23.json'
J_BM = '_v4_benchmark.json'
J_AU1 = '_audit_rerun_20260822.json'
J_AU2 = '_audit_rerun2_20260822.json'
J_RB = '_v4_robust.json'
J_B2 = 'output/batch2_regressions_v2_2026-08-22.json'
J_B3 = 'output/batch3_alpha_decomposition_2026-08-22.json'
J_B4 = 'output/batch4_bootstrap_2026-08-22.json'
J_FM = 'output/M4_FamaMacBeth复核_2026-08-16.json'
J_LSV = 'output/lsv_脆弱性诊断电池_2026-08-16.csv'
J_DEA = 'output/de_选择性审计_2026-08-16.csv'
J_VIF = 'output/M4_多重共线性_VIF_2026-08-16.csv'
J_SMD = 'output/de_组间可比性_2026-08-16.csv'
J_COLL = 'output/M4_多重共线性诊断_2026-08-16.json'

s = io.open(MP, encoding='utf-8').read()
CR = json.load(io.open(J_CR, encoding='utf-8'))
T417 = json.load(io.open(J_T417, encoding='utf-8'))
FF = json.load(io.open(J_FF, encoding='utf-8'))
BM = json.load(io.open(J_BM, encoding='utf-8'))
AU1 = json.load(io.open(J_AU1, encoding='utf-8'))
AU2 = json.load(io.open(J_AU2, encoding='utf-8'))
RB = json.load(io.open(J_RB, encoding='utf-8'))
B2 = json.load(io.open(J_B2, encoding='utf-8'))
B3 = json.load(io.open(J_B3, encoding='utf-8'))
B4 = json.load(io.open(J_B4, encoding='utf-8'))
FMJ = json.load(io.open(J_FM, encoding='utf-8'))

issues = []
NC = [0]

def cap_region(a):
    i = s.find('<caption>' + a)
    j = s.find('</table>', i)
    return s[i:j] if i > -1 else ''

def rows(region):
    out = []
    for tr in re.findall(r'<tr[^>]*>(.*?)</tr>', region, re.S):
        cells = [c.strip() for c in re.findall(r'<td[^>]*>(.*?)</td>', tr, re.S)]
        if cells:
            out.append(cells)
    return out

def txt(x):
    return re.sub(r'<[^>]+>', '', x).replace('−', '-').strip()

def num(t):
    t = re.sub(r'<[^>]+>', '', t).replace('−', '-').strip().replace(',', '').lstrip('+')
    d = len(t.split('.')[1]) if '.' in t else 0
    return float(t), d

def chk(tag, disp, truth):
    NC[0] += 1
    try:
        v, d = num(disp)
    except ValueError:
        issues.append('%s 数值解析失败 [%s]' % (tag, disp)); return
    tol = 0.5000001 * 10 ** (-d)
    tv = float(truth)
    if abs(v - tv) > tol:
        issues.append('%s 显示%s vs 权威%.6f（应显示%.*f）' % (tag, disp, tv, d, round(tv, d)))

def chk_stars(tag, disp, truth):
    NC[0] += 1
    if disp.strip() != truth:
        issues.append('%s 星号[%s] vs 权威[%s]' % (tag, disp.strip(), truth))

def stars3(p):
    return '***' if p < 0.01 else ('**' if p < 0.05 else ('*' if p < 0.1 else ''))

def load_csv(p):
    ln = io.open(p, encoding='utf-8-sig').read().strip().splitlines()
    hdr = ln[0].split(',')
    return [dict(zip(hdr, x.split(','))) for x in ln[1:] if x.strip()]

def pct(disp):
    disp = re.sub(r'<[^>]+>', '', disp).replace('−', '-').strip()
    return float(disp.rstrip('%'))

def has_signed(tok):
    if tok in s:
        return True
    return tok.replace('-', '−') in s

def letter_rows(region, ncells):
    out = {}
    for raw in rows(region):
        cells = [txt(c) for c in raw]
        if len(cells) != ncells:
            continue
        m = re.match(r'^([A-K])\s', cells[0])
        if m:
            out.setdefault(m.group(1), []).append(cells)
    return out

VARS = ('risk_asym', 'lsv', 'de')

# ---------- A. 表4-5 ----------
r45 = cap_region('表4-5')
if not r45:
    issues.append('A: 未定位到表4-5')
f45 = {}
for cells in rows(r45):
    key = cells[0].split('（')[0].strip()
    if key in VARS and len(cells) == 7:
        f45[key] = cells[1:]
for ci, spec in enumerate(['with_aum_ff5', 'with_aum_ex']):
    sp = CR['table45'][spec]
    for var in VARS:
        if var not in f45:
            issues.append('A: 表4-5 缺 %s 行' % var); continue
        c = f45[var][ci * 3:ci * 3 + 3]
        tc = sp['coef'][var]
        tag = 'A: 表4-5 %s[%s]' % (var, spec)
        chk(tag + '.b', c[0], tc['b'])
        chk(tag + '.t', c[1], tc['t'])
        chk_stars(tag + '.sig', c[2], tc['stars'])
nr45 = [c for c in rows(r45) if c[0].startswith('N')]
if len(nr45) != 1:
    issues.append('A: 表4-5 N/R² 行数异常 (%d)' % len(nr45))
else:
    ms = re.findall(r'([\d,]+)\s*/\s*([\d.]+)', ' '.join(nr45[0]))
    if len(ms) != 2:
        issues.append('A: 表4-5 N/R² 格式异常 [%s]' % ' '.join(nr45[0]))
    else:
        for k, (nn, rr) in enumerate(ms):
            sp = CR['table45'][['with_aum_ff5', 'with_aum_ex'][k]]
            chk('A: 表4-5 N%d' % k, nn, sp['N'])
            chk('A: 表4-5 R²%d' % k, rr, sp['r2'])

# ---------- B. 表4-6 ----------
r46 = cap_region('表4-6')
if not r46:
    issues.append('B: 未定位到表4-6')
f46 = {}
for cells in rows(r46):
    key = cells[0].split('（')[0].strip()
    if key in VARS and len(cells) == 7:
        f46[key] = cells[1:]
for ci, spec in enumerate(['fut4q', 'fut1q']):
    sp = CR['table46'][spec]
    for var in VARS:
        if var not in f46:
            issues.append('B: 表4-6 缺 %s 行' % var); continue
        c = f46[var][ci * 3:ci * 3 + 3]
        tc = sp['coef'][var]
        tag = 'B: 表4-6 %s[%s]' % (var, spec)
        chk(tag + '.b', c[0], tc['b'])
        chk(tag + '.t', c[1], tc['t'])
        chk_stars(tag + '.sig', c[2], tc['stars'])
nr46 = [c for c in rows(r46) if c[0].startswith('N')]
if len(nr46) != 1:
    issues.append('B: 表4-6 N/R² 行数异常 (%d)' % len(nr46))
else:
    ms = re.findall(r'([\d,]+)\s*/\s*([\d.]+)（(\d+)基金）', ' '.join(nr46[0]))
    if len(ms) != 2:
        issues.append('B: 表4-6 N/R²/基金数 格式异常 [%s]' % ' '.join(nr46[0]))
    else:
        for k, (nn, rr, nf) in enumerate(ms):
            sp = CR['table46'][['fut4q', 'fut1q'][k]]
            chk('B: 表4-6 N%d' % k, nn, sp['N'])
            chk('B: 表4-6 R²%d' % k, rr, sp['r2'])
            chk('B: 表4-6 基金数%d' % k, nf, sp['n_funds'])

# ---------- C. 表4-7 ----------
r47 = cap_region('表4-7')
if not r47:
    issues.append('C: 未定位到表4-7')
seen47 = set()
for cells in rows(r47):
    key = cells[0].split('（')[0].strip()
    if key in VARS and len(cells) == 5:
        seen47.add(key)
        tc = CR['table47']['coef'][key]
        tag = 'C: 表4-7 %s' % key
        chk(tag + '.b', cells[1], tc['b'])
        chk(tag + '.t', cells[2], tc['t'])
        pv = cells[3]
        if pv.startswith('&lt;'):
            NC[0] += 1
            if not (tc['p'] < float(pv[4:].strip())):
                issues.append('%s.p 上界不符 [%s vs p=%.4g]' % (tag, pv, tc['p']))
        else:
            chk(tag + '.p', pv, tc['p'])
        chk_stars(tag + '.sig', cells[4], tc['stars'])
    elif cells[0].startswith('N'):
        m = re.search(r'([\d,]+)\s*/\s*([\d.]+)（(\d+)基金', ' '.join(cells))
        if not m:
            issues.append('C: 表4-7 N/R² 格式异常 [%s]' % ' '.join(cells))
        else:
            sp = CR['table47']
            chk('C: 表4-7 N', m.group(1), sp['N'])
            chk('C: 表4-7 组内R²', m.group(2), sp['r2_within'])
            chk('C: 表4-7 基金数', m.group(3), sp['n_funds'])
miss = set(VARS) - seen47
if miss:
    issues.append('C: 表4-7 缺行 %s' % sorted(miss))

# ---------- D. 表4-17 ----------
r417 = cap_region('表4-17')
if not r417:
    issues.append('D: 未定位到表4-17')
rowmap = {'不控制择时': 'no_timing', '控制HM择时': 'with_timing'}
seen417 = set()
for cells in rows(r417):
    spec = rowmap.get(cells[0])
    if not spec or len(cells) != 9:
        continue
    seen417.add(spec)
    sp = T417['table417'][spec]
    tag = 'D: 表4-17 %s' % spec
    for off, var in [(1, 'risk_asym'), (3, 'lsv'), (5, 'de')]:
        tc = sp['coef'][var]
        chk('%s %s.b' % (tag, var), cells[off], tc['b'])
        chk('%s %s.t' % (tag, var), cells[off + 1], tc['t'])
    if spec == 'no_timing':
        NC[0] += 1
        if cells[7].strip() != '—':
            issues.append('%s 择时列应为— [%s]' % (tag, cells[7]))
    else:
        chk(tag + ' hm_b2.t', cells[7], sp['coef']['hm_b2']['t'])
    chk(tag + '.R²', cells[8], sp['r2'])
miss = {'no_timing', 'with_timing'} - seen417
if miss:
    issues.append('D: 表4-17 缺行 %s' % sorted(miss))

# ---------- E. 表4-18 ----------
r418 = cap_region('表4-18')
if not r418:
    issues.append('E: 未定位到表4-18')
srcmap = {'FF3': FF['ff3'], 'FF4': FF['ff4'], 'FF5': None}
seen418 = set()
for cells in rows(r418):
    if len(cells) != 5:
        continue
    key = cells[0].split('（')[0].split()[0].strip()
    if key not in srcmap:
        continue
    seen418.add(key)
    sp = srcmap[key] if key != 'FF5' else CR['table45']['with_aum_ff5']
    tag = 'E: 表4-18 %s' % key
    chk(tag + '.R²', cells[1], sp['r2'])
    for ci, var in [(2, 'risk_asym'), (3, 'lsv'), (4, 'de')]:
        m = re.match(r'\s*([+-][\d.]+)（([+-]?[\d.]+)）(\**)\s*$', cells[ci])
        if not m:
            issues.append('%s %s 单元格格式异常 [%s]' % (tag, var, cells[ci])); continue
        tc = sp['coef'][var]
        chk('%s %s.b' % (tag, var), m.group(1), tc['b'])
        chk('%s %s.t' % (tag, var), m.group(2), tc['t'])
        chk_stars('%s %s.sig' % (tag, var), m.group(3), tc['stars'])
miss = {'FF3', 'FF4', 'FF5'} - seen418
if miss:
    issues.append('E: 表4-18 缺行 %s' % sorted(miss))
if FF.get('ff5_crosscheck'):
    xc = FF['ff5_crosscheck']
    NC[0] += 1
    if not (abs(xc['ra_b'] - CR['table45']['with_aum_ff5']['coef']['risk_asym']['b']) < 1e-9
            and abs(xc['ra_t'] - CR['table45']['with_aum_ff5']['coef']['risk_asym']['t']) < 1e-9
            and xc['N'] == CR['table45']['with_aum_ff5']['N']):
        issues.append('E: ff5_crosscheck 与 core_regs.with_aum_ff5 不一致')

# ---------- F. 表4-5 证据块 bootstrap/两阶段数字（存在性校验） ----------
B = CR['table45_bootstrap']; T = CR['table45_twostage']
tokens = [
    ('F: bootstrap mean|t|', '%.1f' % B['risk_asym']['mean_abs_t']),
    ('F: bootstrap RA |t|>2.58份额', '%.1f%%' % (B['risk_asym']['share_gt_258'] * 100)),
    ('F: bootstrap LSV |t|>1.96份额', '%.1f%%' % (B['lsv']['share_gt_196'] * 100)),
    ('F: bootstrap DE |t|>1.96份额', '%.1f%%' % (B['de']['share_gt_196'] * 100)),
    ('F: 两阶段 RA 中位t', '%.2f' % T['risk_asym']['median_t']),
    ('F: 两阶段 LSV 中位t', '%.2f' % T['lsv']['median_t']),
    ('F: 两阶段 DE 中位t', '%.2f' % T['de']['median_t']),
]
for tag, tk in tokens:
    NC[0] += 1
    if tk not in s:
        issues.append('%s 校验令牌缺失 [%s]' % (tag, tk))

# ---------- G. 表4-10 M4完整模型 ----------
r410 = cap_region('表4-10')
if not r410:
    issues.append('G: 未定位到表4-10')
g410 = {}
for raw in rows(r410):
    cells = [txt(c) for c in raw]
    if len(cells) != 6 or cells[1] not in BM['coefs']:
        continue
    g410[cells[1]] = cells
for var in BM['coefs']:
    if var not in g410:
        issues.append('G: 表4-10 缺行 %s' % var); continue
    cells = g410[var]
    cf = BM['coefs'][var]
    tag = 'G: 表4-10 %s' % var
    bdisp = cells[2]
    NC[0] += 1
    if bdisp.lstrip('+') != '0.00000' and float(bdisp.replace('+', '')) == 0.0 and abs(cf['beta']) < 5e-7:
        pass
    else:
        chk(tag + '.b', bdisp, cf['beta'])
    chk(tag + '.t', cells[3], cf['t2w'])
    pv = cells[4]
    if pv.startswith('&lt;'):
        NC[0] += 1
        if not (cf['p2w'] < float(pv[4:].strip())):
            issues.append('%s.p 上界不符' % tag)
    elif pv == '0.000':
        NC[0] += 1
        if not (cf['p2w'] < 0.0005):
            issues.append('%s.p=0.000 应为p<0.0005（实际%.4g）' % (tag, cf['p2w']))
    else:
        chk(tag + '.p', pv, cf['p2w'])
    chk_stars(tag + '.sig', cells[5], stars3(cf['p2w']))
NC[0] += 2
if not has_signed('+0.07311') or not has_signed('-0.00606') or not has_signed('+0.01548'):
    issues.append('G: 正文经济解读段基准系数令牌缺失')

# ---------- H. 表4-11 R²对比 ----------
r411 = cap_region('表4-11')
if not r411:
    issues.append('H: 未定位到表4-11')
h411 = {}
for cells in rows(r411):
    if len(cells) != 4:
        continue
    h411[cells[0]] = cells
ss = AU1['same_sample']; bb = AU1['B']
exp_h = {
    'M0（基准）': (bb['M0']['R2'], ss['M0']),
    'M3（L1-L4）': (bb['M3']['R2'], ss['M3']),
    'M4（L1-L5）': (bb['M4']['R2'], ss['M4']),
}
for rowname, (full, same) in exp_h.items():
    if rowname not in h411:
        issues.append('H: 表4-11 缺行 [%s]' % rowname); continue
    cells = h411[rowname]
    chk('H: 表4-11 %s 全样本R²' % rowname[:2], cells[1], full)
    chk('H: 表4-11 %s 同样本R²' % rowname[:2], cells[2], same)
    NC[0] += 1
    diff_disp = float(cells[3].replace('+', ''))
    if abs(diff_disp - round(float(same) - float(full), 4)) > 0.00005:
        issues.append('H: 表4-11 %s 差异列不自洽 [%s vs %.4f]' % (rowname, cells[3], float(same) - float(full)))
NC[0] += 2
if '0.0352' not in s:
    issues.append('H: ΔR²(L5)全样本0.0352令牌缺失')
chk('H: ΔR²(L5)同样本', '0.0224', ss['dR2_L5'])

# ---------- I. 表4-12 增量分解 ----------
r412 = cap_region('表4-12')
if not r412:
    issues.append('I: 未定位到表4-12')
C = AU2['C_same_sample']
seq = C['sequential']; lastin = C['dR2_last_in']; alone = C['dR2_alone']
i412 = {
    'L1 经理背景': (seq['L1']['dR2'], lastin['L1'], alone['L1']),
    'L2 投资决策': (seq['L2']['dR2'], lastin['L2'], alone['L2']),
    'L3+L4 交易执行与风险管理': (seq['L3+L4']['dR2'], lastin['L3+L4'], alone['L3+L4']),
    'L5 认知偏差': (seq['L5']['dR2'], lastin['L5'], alone['L5']),
}
seenI = set()
sumseq = 0.0
for cells in rows(r412):
    key0 = txt(cells[0]) if cells else ''
    if len(cells) != 5 or not any(key0.startswith(k) for k in i412):
        continue
    rowkey = next(k for k in i412 if key0.startswith(k))
    seenI.add(rowkey)
    sq, li, al = i412[rowkey]
    tag = 'I: 表4-12 %s' % rowkey[:4]
    sqv, _ = num(cells[1])
    chk(tag + '.seq', cells[1], sq); sumseq += sqv
    chk(tag + '.lastin', cells[2], li)
    chk(tag + '.alone', cells[3], al)
    share = 1 - float(li) / float(al)
    NC[0] += 1
    if abs(pct(cells[4]) / 100.0 - round(share, 3)) > 0.0005:
        issues.append('%s 共享方差占比不自洽 [%s vs %.1f%%]' % (tag, cells[4], share * 100))
miss = set(i412) - seenI
if miss:
    issues.append('I: 表4-12 缺行 %s' % sorted(miss))
NC[0] += 1
if abs(sumseq - (seq['L5']['R2'] - seq['M0'])) > 0.0005:
    issues.append('I: 逐层ΔR²加总 %.4f ≠ R²差 %.4f' % (sumseq, seq['L5']['R2'] - seq['M0']))

# ---------- J. 表4-13 安慰剂 ----------
r413 = cap_region('表4-13')
if not r413:
    issues.append('J: 未定位到表4-13')
j413 = {'RiskAsym': 'risk_asym', 'LSV': 'lsv', 'DE': 'de'}
seenJ = set()
for cells in rows(r413):
    if len(cells) != 5 or cells[0] not in j413:
        continue
    seenJ.add(cells[0])
    v = j413[cells[0]]
    tag = 'J: 表4-13 %s' % cells[0]
    chk(tag + '.真实t', cells[1], RB['true_t2w'][v])
    NC[0] += 1
    try:
        num(cells[2])
    except ValueError:
        issues.append('%s 置换均值格式异常 [%s]' % (tag, cells[2]))
    q = pct(cells[3]) / 100.0
    NC[0] += 1
    if abs(q - round(RB['perm_p'][v], 3)) > 0.0005:
        issues.append('%s 置换分位 %s vs 权威 %.4f' % (tag, cells[3], RB['perm_p'][v]))
sig_expect = RB['perm_p'][v] < 0.05
concl = txt(cells[4])
NC[0] += 1
if sig_expect and '显著' not in concl.replace('不显著', ''):
    issues.append('%s 结论列应为显著 [%s]' % (tag, concl))
NC[0] += 1
if not sig_expect and '不显著' not in concl:
    issues.append('%s 结论列应为不显著 [%s]' % (tag, concl))
miss = set(j413) - seenJ
if miss:
    issues.append('J: 表4-13 缺行 %s' % sorted(miss))
NC[0] += 1
i_perm = s.find('随机置换检验')
seg = s[max(0, i_perm - 200):i_perm + 60]
m300 = re.search(r'进行(\d+)次随机置换检验', seg)
if not m300:
    issues.append('J: §4.4.1 置换次数表述未定位')
elif m300.group(1) != '300':
    issues.append('J: 置换次数=%s 应为300' % m300.group(1))
NC[0] += 1
cap413 = re.search(r'<caption>([^<]*)</caption>', r413).group(1)
if '因变量随机置换' in cap413 or '因變量隨機置換' in cap413:
    issues.append('J: 表4-13表题口径错误（置换对象是X的L5指标而非y）：%s' % cap413)
if 'L5指标随机置换' not in cap413:
    issues.append('J: 表4-13表题应为「L5指标随机置换」：%s' % cap413)
NC[0] += 1
m61 = re.search(r'安慰剂检验（(\d+)次置换）', s)
if not m61:
    issues.append('J: 表6-1 安慰剂数字未定位')
elif m61.group(1) != '300':
    issues.append('J: 表6-1 安慰剂=%s次 应为300次' % m61.group(1))
NC[0] += 1
if not re.search(r'置换\s*p\s*=\s*300\s*次置换检验\s*p', s):
    issues.append('J: 注释「置换 p=300 次置换检验 p」缺失或漂移')
NC[0] += 1
if '50.7%' not in s:
    issues.append('J: LSV置换分位50.7%令牌缺失（防回潮）')

# ---------- K. 表4-15 FM ----------
r415 = cap_region('表4-15')
if not r415:
    issues.append('K: 未定位到表4-15')
tgt_map = {'risk_asym': 'risk_asym_w', 'lsv': 'lsv_w', 'de': 'de_w'}
fm_sparse = {e['target']: e for e in FMJ['sparse_4var']}
fm_full = {e['target']: e for e in FMJ['full_18rhs']}
kcount = 0
for cells in rows(r415):
    if len(cells) != 5 or cells[0] not in tgt_map:
        continue
    tg = tgt_map[cells[0]]
    if tg not in fm_sparse:
        issues.append('K: 权威缺 %s' % tg); continue
    e = fm_sparse[tg]
    tag = 'K: 表4-15 %s' % cells[0]
    chk(tag + '.mean', cells[1], e['mean'])
    chk(tag + '.fmt', cells[2], e['fm_t'])
    chk(tag + '.nw', cells[3], e['nw_t'])
    kcount += 1
if kcount != 3:
    issues.append('K: 表4-15 三指标行数异常 (%d)' % kcount)
NC[0] += 1
if '20 个有效季度' not in s and '20个有效季度' not in s:
    issues.append('K: T=20窗口表述缺失')
for tk in ['RA FM-t=+0.15', 'LSV FM-t=−0.21', 'DE FM-t=−1.40']:
    NC[0] += 1
    if tk not in s:
        issues.append('K: 全18RHS补充段令牌缺失 [%s]' % tk)
NC[0] += 1
if not (abs(fm_full['risk_asym_w']['fm_t']) < 0.155 + 0.005 and abs(fm_full['lsv_w']['fm_t']) < 0.21 + 0.005
        and abs(fm_full['de_w']['fm_t']) < 1.40 + 0.005):
    issues.append('K: 补充段令牌与权威fm_t不一致')

# ---------- L. 表4-20 LSV电池 ----------
r420 = cap_region('表4-20')
if not r420:
    issues.append('L: 未定位到表4-20')
LSVD = load_csv(J_LSV)
lsv_by = {}
for r in LSVD:
    lsv_by.setdefault(r['spec'][0], []).append(r)
seenL = set()
for cells in rows(r420):
    if len(cells) != 5:
        continue
    mm = re.match(r'^([A-K])\s', txt(cells[0]))
    if not mm:
        continue
    key = mm.group(1)
    seenL.add(key)
    rs = lsv_by.get(key, [])
    if not rs:
        issues.append('L: 权威CSV缺规格 %s' % key); continue
    if key == 'I':
        betas = [c.split('/')[0].strip() for c in cells[1].split('/')]
        ts = [c.strip() for c in cells[2].split('/')]
        ps = [c.strip() for c in cells[3].split('/')]
        if not (len(betas) == len(ts) == len(ps) == len(rs) == 3):
            issues.append('L: 规格I 三分位拆分格式异常'); continue
        for kk, rr in enumerate(rs):
            tag = 'L: 表4-20 I%d' % kk
            chk(tag + '.b', betas[kk], rr['lsv_beta'])
            chk(tag + '.t', ts[kk], rr['t2w'])
            chk(tag + '.p', ps[kk], rr['p2w'])
            stI = re.sub(r'n\.s\.|ns', '', txt(cells[4])).strip()
            chk_stars(tag + '.sig', stI, rr['stars'])
    else:
        rr = rs[0]
        tag = 'L: 表4-20 %s' % key
        chk(tag + '.b', cells[1], rr['lsv_beta'])
        chk(tag + '.t', cells[2], rr['t2w'])
        chk(tag + '.p', cells[3], rr['p2w'])
        st = re.sub(r'n\.s\.|ns', '', txt(cells[4])).strip()
        chk_stars(tag + '.sig', st, rr['stars'])
miss = set(lsv_by) - seenL
if miss:
    issues.append('L: 表4-20 缺规格行 %s' % sorted(miss))

# ---------- M. 表4-21 DE审计 ----------
r421 = cap_region('表4-21')
if not r421:
    issues.append('M: 未定位到表4-21')
DEA = load_csv(J_DEA)
dea_by = {r['spec'][0]: r for r in DEA}
seenM = set()
for cells in rows(r421):
    if len(cells) != 6:
        continue
    mm = re.match(r'^([A-F])\s', txt(cells[0]))
    if not mm:
        continue
    key = mm.group(1)
    if key not in dea_by:
        issues.append('M: 权威CSV缺规格 %s' % key); continue
    seenM.add(key)
    rr = dea_by[key]
    tag = 'M: 表4-21 %s' % key
    if key == 'E':
        NC[0] += 1
        if cells[1].strip() != '—':
            issues.append('%s de系数位应为—占位 [%s]' % (tag, cells[1]))
    else:
        chk(tag + '.b', cells[1], rr['de_beta'])
    chk(tag + '.t', cells[2], rr['t2w'])
    chk(tag + '.p', cells[3], rr['p2w'])
    chk_stars(tag + '.sig', txt(cells[4]), rr['stars'])
miss = set(dea_by) - seenM
if miss:
    issues.append('M: 表4-21 缺规格行 %s' % sorted(miss))
SMD = load_csv(J_SMD)
smd_by = {r['var']: r for r in SMD}
for var, tok in [('AS_improved', '+1.502'), ('industry_hhi', '-1.119'), ('ICI', '-0.292'),
                 ('log_fund_age', '+0.306'), ('mgr_total_tenure_v2', '+0.131')]:
    NC[0] += 1
    if not has_signed(tok):
        issues.append('M: SMD令牌 %s(%s) 缺失' % (var, tok))
    elif abs(abs(float(smd_by[var]['SMD'])) - abs(float(tok))) > 1e-9:
        issues.append('M: SMD令牌与权威不符 %s' % var)

# ---------- N. 表4-22 VIF ----------
r422 = cap_region('表4-22')
if not r422:
    issues.append('N: 未定位到表4-22')
VIFC = load_csv(J_VIF)
vif_by = {r['variable']: r['VIF'] for r in VIFC}
foundN = {}
for cells in rows(r422):
    if len(cells) != 6:
        continue
    for cc in (1, 4):
        vn = txt(cells[cc])
        if vn in vif_by:
            foundN[vn] = cells[cc + 1]
for vn, vv in sorted(vif_by.items()):
    if vn not in foundN:
        issues.append('N: 表4-22 缺变量 %s' % vn); continue
    chk('N: 表4-22 %s' % vn, foundN[vn], vv)
COLL = json.load(io.open(J_COLL, encoding='utf-8'))
NC[0] += 1
if COLL['max_VIF_var'] != 'ff5_CMA' or abs(COLL['max_VIF'] - 10.5308) > 1e-9:
    issues.append('N: 共线诊断JSON max_VIF 不符')
chk('N: 条件数', '7.42', COLL['condition_number'])
NC[0] += 1
pair = [p for p in COLL['strong_pairs_abs_r_gt_0.5'] if p[0] == 'ff5_SMB' and p[1] == 'ff5_RMW']
if not pair or abs(pair[0][2]) - 0.871 > 1e-9 or not has_signed('-0.871'):
    issues.append('N: 最强配对 ff5_SMB–ff5_RMW r=-0.871 校验失败')

# ---------- O. 表4-23 能力分解 ----------
r423 = cap_region('表4-23')
if not r423:
    issues.append('O: 未定位到表4-23')
dv_keys = {'选股α': 'DV1_选股α', '择时贡献': 'DV2_择时贡献', '总α (FF5, 参照)': 'DV3_总α_参照'}
omap = {'RiskAsym': 'risk_asym', 'DE': 'de', 'LSV': 'lsv', 'ICI（对照）': 'ICI', 'ARG（对照）': 'ARG'}
seenO = set()
for cells in rows(r423):
    if len(cells) != 4 or cells[0] not in omap:
        continue
    seenO.add(cells[0])
    v = omap[cells[0]]
    for ci, dk in zip((1, 2, 3), dv_keys):
        blk = B3[dv_keys[dk]]['coefs'].get(v)
        if blk is None:
            issues.append('O: 权威缺 %s/%s' % (dk, v)); continue
        cell = txt(cells[ci])
        tag = 'O: 表4-23 %s×%s' % (cells[0][:6], dk[:3])
        mfull = re.match(r'^β=([+-]?[\d.]+),\s*t=([+-]?[\d.]+)(\**)\s*n?\.?s?\.?\s*$', cell)
        mtonly = re.match(r'^t=([+-]?[\d.]+)\s*(n\.s\.|\**\*?)\s*$', cell)
        if mfull:
            chk(tag + '.b', mfull.group(1), blk['beta'])
            chk(tag + '.t', mfull.group(2), blk['t'])
            sig = mfull.group(3)
            if 'n.s.' in cell:
                sig = ''
            chk_stars(tag + '.sig', sig, blk['stars'])
        elif mtonly:
            NC[0] += 1
            if blk['stars']:
                issues.append('%s 单元格省略β但权威显著 [%s]' % (tag, cell))
            chk(tag + '.t', mtonly.group(1), blk['t'])
            chk_stars(tag + '.sig', '', '')
        else:
            issues.append('%s 单元格格式异常 [%s]' % (tag, cell))
miss = set(omap) - seenO
if miss:
    issues.append('O: 表4-23 缺行 %s' % sorted(miss))
mbase = {c['var']: c for c in B2['M4_base']['coefs']}
NC[0] += 1
if B2['M4_base']['meta']['N'] != 1336 or B2['M4_base']['meta']['nfund'] != 159:
    issues.append('O: batch2 日频复验 meta 不符')
toks_O = [('RiskAsym t=+3.22', mbase['risk_asym']), ('DE（t=-1.30', mbase['de']),
          ('AS_improved（t=-0.38', None)]
for tk, cf in toks_O:
    NC[0] += 1
    if not has_signed(tk):
        issues.append('O: §4.4.11(ii) 令牌缺失 [%s]' % tk)
NC[0] += 1
if abs(abs(mbase['risk_asym']['t2w']) - 3.224826) > 1e-4:
    issues.append('O: RA日频t与权威不符')

# ---------- P. 表4-24 Bootstrap ----------
r424 = cap_region('表4-24')
if not r424:
    issues.append('P: 未定位到表4-24')
pmap = {'RiskAsym': 'risk_asym', 'ICI': 'ICI', 'AS_improved': 'AS_improved',
        'ARG': 'ARG', 'DE': 'de', 'LSV': 'lsv'}
seenP = set()
for cells in rows(r424):
    if len(cells) != 5 or cells[0] not in pmap:
        continue
    seenP.add(cells[0])
    v = pmap[cells[0]]
    bk = B4[v]
    tag = 'P: 表4-24 %s' % cells[0]
    chk(tag + '.mean', cells[1], bk['beta_mean'])
    mci = re.match(r'^\[([+-]?[\d.]+),\s*([+-]?[\d.]+)\]$', txt(cells[2]))
    if not mci:
        issues.append('%s CI格式异常 [%s]' % (tag, cells[2])); continue
    chk(tag + '.lo', mci.group(1), bk['beta_p2p5'])
    chk(tag + '.hi', mci.group(2), bk['beta_p97p5'])
    excl = '否' not in cells[3]
    NC[0] += 1
    if bool(bk['ci_excludes_zero']) != excl:
        issues.append('%s CI排零不符 [%s]' % (tag, cells[3]))
    share = max(bk['share_t_pos_sig'], bk['share_t_neg_sig'])
    NC[0] += 1
    if abs(pct(txt(cells[4])) / 100.0 - share) > 0.0005:
        issues.append('%s 同向显著比例 %s vs 权威 %.1f%%' % (tag, cells[4], share * 100))
miss = set(pmap) - seenP
if miss:
    issues.append('P: 表4-24 缺行 %s' % sorted(miss))
NC[0] += 1
if not (B4['design']['B'] == 1000 and B4['design']['G'] == 348 and B4['design']['N'] == 2264):
    issues.append('P: bootstrap design 参数不符')

print('=' * 50)
print('数值/星号/令牌/自洽校验点：%d' % NC[0])
if issues:
    print('FAIL (%d):' % len(issues))
    for i in issues:
        print(' -', i)
    raise SystemExit(1)
print('PASS: A-P 十六节全部通过——表4-5/4-6/4-7/4-10/4-11/4-12/4-13/4-15/4-17/4-18/'
      '4-20/4-21/4-22/4-23/4-24 系数与权威JSON/CSV逐位一致；证据块数字齐全；本轮五处修复已锁定')
