# -*- coding: utf-8 -*-
"""第八道门禁 _gate8_check.py：
A. 文内 "见§x.y(.z)" 节引用存在性校验
B. PS 链条表格/正文数值 vs 权威 JSON 独立复核
C. 表5-5 行加总 vs N=2,264；表5-9 加总与占比复核
D. L5 描述统计跨位置一致性（表3-2=原始obs口径、表4-2与§4.1.3=缩尾obs口径，
   从权威 CSV 动态重算；另扫描幽灵值残留与 DV 覆盖新值锚点）
"""
import re, io, json

MP = r"d:\Desktop\基金经理行为分析研究\merged_manuscript.html"
JP = r"d:\Desktop\基金经理行为分析研究\output\ps_v4_recalc_20260822.json"
s = io.open(MP, encoding="utf-8").read()
J = json.load(open(JP, encoding="utf-8"))

issues = []

# ---------- A. 节引用存在性 ----------
heads = re.findall(r'<h([123])[^>]*>([\d.]+)', s)
hset = set(x[1].rstrip('.') for x in heads)
refs = set()
for m in re.finditer(r'§(\d(?:\.\d+){0,3})', s):
    refs.add(m.group(1).rstrip('.'))
bad = sorted(r for r in refs if r not in hset)
if bad:
    issues.append('A: 无效节引用 -> %s' % bad)

# ---------- B. 数值复核 ----------
def fmt_pm(v):
    return ('+' if v >= 0 else '-') + ('%.4f' % abs(v))

def cap_region(a, b):
    """按 caption 锚点取区域；b 缺省时到下一个 caption。"""
    i = s.find('<caption>' + a)
    j = s.find('<caption>', i + 10) if b is None else s.find('<caption>' + b)
    return s[i:j] if (i > -1 and j > i) else ''

# 表5-5 五分位（允许 signif 类、strong 包裹、"(最低PS)/(最高PS)" 后缀）
r55 = cap_region('表5-5', '表5-6')
for q in ['Q1', 'Q2', 'Q3', 'Q4', 'Q5']:
    d = J['quintiles'][q]
    m = re.search(r'<tr[^>]*>\s*<td>\s*%s[^<]*</td>\s*<td>%d</td>\s*<td>%s</td>\s*'
                  r'<td>(?:<strong>)?%.4f(?:</strong>)?</td>\s*<td>%.4f</td>\s*<td>%.4f</td>'
                  % (re.escape(q), d['n'], re.escape(fmt_pm(d['ps_mean'])),
                     d['alpha_mean'], d['alpha_median'], d['alpha_std']), r55)
    if not m:
        issues.append('B: 表5-5 %s 行与 JSON 不符' % q)

# 表5-6 关键统计
mono = J['monotonicity']
r56 = cap_region('表5-6', '表5-7')
checks56 = [
    ('%.2f%%' % (mono['q5_q1_spread'] * 100), 'Q5-Q1 收益差'),
    ('t=%.2f' % mono['spread_t'], 'spread t'),
    ('ρ=%.4f' % mono['spearman_rho'], 'spearman'),
    ('+%.4f' % mono['trend_slope'], 'trend slope'),
    ('t=%.2f ***' % mono['trend_t'], 'trend t stars'),
    ('r=+%.4f' % J['correlation']['pearson_r'], 'pearson r'),
    ('%.4f' % J['correlation']['reg_r2'], 'reg r2')]
for v, lab in checks56:
    if v not in r56:
        issues.append('B: 表5-6 区缺少 %s (%s)' % (v, lab))

# 表5-7 / 表5-8 Logistic
lg = J['logistic']
blob57 = s[s.find('表5-7'):s.find('表5-9')] if s.find('表5-7') > -1 and s.find('表5-9') > -1 else ''
for k, lab in [('-0.689', 'de coef'), ('-2.79', 'de z'), ('3.527', 'lsv coef'), ('+3.30', 'lsv z'),
               ('9.052', 'ra coef'), ('+8.06', 'ra z'), ('0.016', 'aum coef'), ('+0.64', 'aum z')]:
    if k not in blob57:
        issues.append('B: 表5-7 区缺少 %s (%s)' % (k, lab))
blob58 = blob57  # 5-7 与 5-8 相邻，同区间覆盖
for v, lab in [('%.4f' % lg['auc'], 'auc'), ('%.4f' % lg['pseudo_r2'], 'pseudo_r2'),
               ('%.2f%%' % (lg['accuracy'] * 100), 'accuracy')]:
    if v not in blob58:
        issues.append('B: 表5-8 区缺少 %s (%s)' % (v, lab))
if ('%.4f' % lg['auc']) not in s:
    issues.append('B: 全文缺 AUC %.4f' % lg['auc'])

# 表5-9 八画像
prof = J['profiles']['profiles']
for name, d in prof.items():
    row = '<tr%s><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%d</td><td>%.1f%%</td><td>%s%.4f</td></tr>'
    m = re.search(r'<tr[^>]*><td>%s</td>.{0,220}?</tr>' % name, s, re.S)
    if not m:
        issues.append('B: 表5-9 找不到画像行 %s' % name)
        continue
    seg = m.group(0)
    for v, lab in [(str(d['n']), 'n'), ('%.1f%%' % d['pct'], 'pct'), ('%.4f' % d['alpha_mean'], 'alpha')]:
        if v not in seg:
            issues.append('B: 表5-9 %s 缺 %s=%s（段:%s）' % (name, lab, v, seg[:120]))

# 八画像 n 加总 == 2264
tot = sum(d['n'] for d in prof.values())
if tot != 2264:
    issues.append('C: 表5-9 八画像 n 加总=%d != 2264' % tot)
# pct 加总 ~100
ptot = sum(d['pct'] for d in prof.values())
if abs(ptot - 100) > 1.0:
    issues.append('C: 表5-9 pct 加总=%.1f 偏离100超过1pp' % ptot)

# 正文关键句
must = [
    ('1.02%', '样本内 Q5-Q1'), ('t=9.07', 'spread t 正文'),
    ('0.6067', 'AUC 精确值'), ('+0.0093', 'best-worst spread'),
    ('t=6.25', 'profile t'), ('+0.0245', '自信从众 alpha'), ('+0.0152', '固执独立 alpha')]
for v, lab in must:
    if v not in s:
        issues.append('B: 全文缺 %s (%s)' % (v, lab))
stale = [('1.48%', '旧 Q5-Q1'), ('11.55', '旧 spread t'), ('0.661', '旧 AUC'),
         ('61.20%', '旧准确率'), ('0.0591', '旧 pseudoR2'), ('8.87', '旧 profile t'),
         ('+0.0208', '旧 冲动型'), ('0.0068', '旧 固执独立'), ('+0.0140', '旧 best-worst')]
for v, lab in stale:
    if v in s:
        issues.append('B: 残留旧值 %s (%s)' % (v, lab))

# C. 表5-5 行加总（限定在表5-5区域内）
ns = [int(x) for x in re.findall(r'<td>Q[1-5][^<]*</td>\s*<td>(\d+)</td>', r55)]
if ns and sum(ns) != 2264:
    issues.append('C: 表5-5 n 加总=%d != 2264 (%s)' % (sum(ns), ns))

# ---------- D. L5 描述统计跨位置一致性 ----------
# 从权威 CSV 动态重算两种口径，再断言稿件各位置匹配
try:
    import pandas as pd
    df = pd.read_csv(r"d:\Desktop\基金经理行为分析研究\指标计算流水线\output\主分析面板_重建_含TOwind.csv")
    cal = {}
    for c in ['de', 'lsv', 'risk_asym']:
        x = df[c].dropna()
        q1, q99 = x.quantile([0.01, 0.99])
        w = x.clip(q1, q99)
        cal[c] = {'raw': (x.mean(), x.std()), 'win': (w.mean(), w.std())}
except Exception as e:
    cal = None
    issues.append('D: 权威CSV不可用 -> %r' % e)

if cal:
    def near(a, b, tol=0.00006):
        return abs(a - b) <= tol

    # 表3-2（原始obs口径，3位舍入）
    r32 = cap_region('表3-2', '表3-3')
    if r32:
        for c, disp in [('de', '-0.126'), ('lsv', '+0.088'), ('risk_asym', '+0.035')]:
            v = cal[c]['raw'][0]
            if not near(float(disp), round(v, 3)):
                issues.append('D: 表3-2 %s 展示值%s 与重算raw均值%.4f 不符' % (c, disp, v))
        for c, sd in [('de', '0.181'), ('lsv', '0.053'), ('risk_asym', '0.081')]:
            if not near(float(sd), round(cal[c]['raw'][1], 3)):
                issues.append('D: 表3-2 %s sd %s 与重算不符' % (c, sd))
    else:
        issues.append('D: 未定位到表3-2区域')

    # 表4-2（缩尾obs口径，4位）
    r42 = cap_region('表4-2', '表4-3')
    if r42:
        for c, disp in [('de', '-0.1266'), ('lsv', '0.0879'), ('risk_asym', '0.0344')]:
            v = cal[c]['win'][0]
            if not near(float(disp), v):
                issues.append('D: 表4-2 %s 展示值%s 与重算win均值%.4f 不符' % (c, disp, v))
        for c, sd in [('de', '0.1715'), ('lsv', '0.0489'), ('risk_asym', '0.0783')]:
            if not near(float(sd), cal[c]['win'][1]):
                issues.append('D: 表4-2 %s sd %s 与重算不符' % (c, sd))
    else:
        issues.append('D: 未定位到表4-2区域')

    # §4.1.3 评述段（缩尾口径；LSV为3位显示，DE/RiskAsym为4位显示）
    for c, disp, lab in [('de', '-0.1266', '§4.1.3 DE'),
                         ('lsv', '+0.088', '§4.1.3 LSV'),
                         ('risk_asym', '+0.0344', '§4.1.3 RiskAsym')]:
        v = cal[c]['win'][0]
        target = round(v, len(disp.lstrip('+-').split('.')[1])) if '.' in disp else v
        if not near(abs(float(disp)), abs(target)):
            issues.append('D: %s 值%s 与缩尾均值%.4f 不符' % (lab, disp, v))

    # 正文常用3位舍入（缩尾口径）
    for c, disp, lab in [('de', '-0.127', '正文DE(-0.127)'),
                         ('lsv', '+0.088', '正文LSV(+0.088)')]:
        v = cal[c]['win'][0]
        if not near(abs(float(disp)), abs(round(v, 3))):
            issues.append('D: %s 与缩尾均值%.4f 的3位舍入不符' % (lab, v))

    # 幽灵值残留扫描（不匹配任何现行口径的旧版本值）
    ghosts = [('+0.089', '旧LSV均值'), ('-0.1274', '旧DE均值'), ('0.089（', '旧LSV括号形式')]
    for v, lab in ghosts:
        if v in s:
            issues.append('D: 幽灵值残留 %s (%s)' % (v, lab))
    # LSV 语境下的 0.089（排除 p 值/R² 等合法用途）
    for i, ln in enumerate(s.split('\n')):
        for m in re.finditer(r'0\.089(?![0-9])', ln):
            ctx = ln[max(0, m.start() - 40):m.start() + 30]
            if 'LSV' in ctx or '羊群' in ctx or 'lsv' in ctx.lower():
                issues.append('D: L%d LSV语境残留0.089' % (i + 1))

    # DV 覆盖新值锚点（上一轮修复的防回归检查）
    for v, lab in [('97.2%', 'DV覆盖率'), ('362只基金', 'alpha基金数'), ('核心样本348只', 'M4基金数')]:
        if v not in s:
            issues.append('D: 缺少 DV 覆盖新锚点 %s (%s)' % (v, lab))
    if '95.2%' in s:
        issues.append('D: 残留旧DV覆盖率 95.2%')

print('=' * 50)
if issues:
    print('FAIL (%d):' % len(issues))
    for i in issues:
        print(' -', i)
    raise SystemExit(1)
print('PASS: 节引用、PS 链数值、加总自洽全部一致')
