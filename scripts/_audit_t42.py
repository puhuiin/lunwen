# -*- coding: utf-8 -*-
"""表4-2全行缩尾描述统计审计 + 表3-4覆盖率基金数 + 表4-1面板概览"""
import io, re
import pandas as pd

s = io.open('merged_manuscript.html', encoding='utf-8').read()

def cap_region(a):
    i = s.find('<caption>' + a)
    j = s.find('</table>', i)
    return s[i:j] if i > -1 else ''

df = pd.read_csv('指标计算流水线/output/主分析面板_重建_含TOwind.csv')
print('列数:', len(df.columns))
print('列清单:', list(df.columns))
cols = {c.lower(): c for c in df.columns}
N = len(df)

def parse_num(t):
    t = t.replace(',', '').strip()
    d = len(t.split('.')[1]) if '.' in t else 0
    return float(t), d

issues = []

# ---------- 表4-2 ----------
r42 = cap_region('表4-2')
rows = re.findall(r'<tr[^>]*>\s*<td>([^<]+)</td>\s*<td>([^<]+)</td>\s*(.*?)</tr>', r42, re.S)
for layer, var, rest in rows:
    cells = re.findall(r'<td[^>]*>([^<]*)</td>', rest)
    if len(cells) < 6:
        continue
    disp = dict(zip(['mean', 'sd', 'min', 'med', 'max', 'cov'], [c.strip() for c in cells[:6]]))
    key = var.strip().lower()
    if key not in cols:
        cand = [c for c in df.columns if key[:4].replace('_','') in c.lower().replace('_','')]
        issues.append('表4-2 %s: CSV无此列 (近似候选: %s)' % (var, cand[:5]))
        continue
    x = df[cols[key]].dropna()
    q1, q99 = x.quantile([0.01, 0.99])
    w = x.clip(q1, q99)
    truth = {'mean': w.mean(), 'sd': w.std(), 'min': w.min(), 'med': w.median(), 'max': w.max()}
    for k in truth:
        v, d = parse_num(disp[k])
        tol = 0.5000001 * 10**(-d)
        if abs(v - truth[k]) > tol:
            issues.append('表4-2 %s.%s: 显示%s vs 重算%.6f' % (var, k, disp[k], truth[k]))
    cov_true = len(x) / N * 100
    cv, cd = parse_num(disp['cov'].rstrip('%'))
    if abs(cv - cov_true) > 0.5000001 * 10**(-cd):
        issues.append('表4-2 %s.cov: 显示%s vs 重算%.2f%%(n=%d)' % (var, disp['cov'], cov_true, len(x)))

# ---------- 表3-4 基金数与覆盖率 ----------
r34 = cap_region('表3-4')
for var, colname in [('DE', 'de'), ('LSV', 'lsv'), ('RiskAsym', 'risk_asym'), ('ff5_adj_return', 'ff5_adj_return')]:
    m = re.search(r'<td[^>]*>%s</td>.*?<td[^>]*>([^<]*)</td>\s*</tr>' % var, r34, re.S)
    if not m:
        issues.append('表3-4: 未找到 %s 行' % var)
        continue
    disp_cov = m.group(1).strip()
    x = df[colname].dropna()
    cov_true = len(x) / N * 100
    nfund = df.loc[x.index, 'fund_code'].nunique() if 'fund_code' in df.columns else None
    mm = re.match(r'([\d.]+)%（(\d+)基金）', disp_cov)
    if not mm:
        issues.append('表3-4 %s: 覆盖率格式异常 [%s]' % (var, disp_cov))
        continue
    cpct, cfund = float(mm.group(1)), int(mm.group(2))
    if abs(cpct - cov_true) > 0.051:
        issues.append('表3-4 %s: 覆盖率%.1f%% vs 重算%.2f%%' % (var, cpct, cov_true))
    if nfund is not None and cfund != nfund:
        issues.append('表3-4 %s: 基金数%d vs 重算%d' % (var, cfund, nfund))

# ---------- 表4-1 面板概览 ----------
r41 = cap_region('表4-1')
checks41 = [
    ('总观测数', str(N), None),
    ('基金数量', str(df['fund_code'].nunique()) if 'fund_code' in df.columns else '?', None),
]
for lab, want, _ in checks41:
    mm = re.search(r'<td>%s</td>\s*<td>([\d,]+)</td>' % lab, r41)
    if not mm:
        issues.append('表4-1: 未找到 %s' % lab)
    elif mm.group(1).replace(',', '') != want.replace(',', ''):
        issues.append('表4-1 %s: 显示%s vs 重算%s' % (lab, mm.group(1), want))

if 'fund_code' in df.columns and 'year' in df.columns and 'quarter' in df.columns:
    l5mask = df[['de', 'lsv', 'risk_asym']].notna().all(axis=1)
    n_l5 = int(l5mask.sum())
    mm = re.search(r'<td>L5完整观测</td>\s*<td>([\d,]+)</td>', r41)
    if mm and int(mm.group(1).replace(',', '')) != n_l5:
        issues.append('表4-1 L5完整观测: 显示%s vs 重算%d' % (mm.group(1), n_l5))
    nq = df[['year', 'quarter']].drop_duplicates().shape[0]
    print('季度数:', nq, '| L5完整观测:', n_l5, '| L5完整基金:', df.loc[l5mask, 'fund_code'].nunique())

print('=' * 50)
if issues:
    print('FAIL (%d):' % len(issues))
    for i in issues:
        print(' -', i)
else:
    print('PASS: 表4-2全部行/表3-4覆盖/表4-1概览与权威CSV一致')
