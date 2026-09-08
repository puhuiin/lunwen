# -*- coding: utf-8 -*-
"""第九道门禁 _gate9_check.py：稿件描述统计 vs 权威CSV真值审计
A. 表4-2 全部变量行：缩尾(mean/sd/min/med/max)+覆盖率 从权威CSV重算逐位比对
   （log_aum 按运行时派生列 ln(avg_aum) 处理）
B. 表3-4 L5/DV 行覆盖率与基金数
C. 表4-1 面板概览（总观测/基金数/L5完整观测）
"""
import io, re
import numpy as np
import pandas as pd

MP = 'merged_manuscript.html'
CP = '指标计算流水线/output/主分析面板_重建_含TOwind.csv'

s = io.open(MP, encoding='utf-8').read()
df = pd.read_csv(CP)
N = len(df)
cols = {c.lower(): c for c in df.columns}

def cap_region(a):
    i = s.find('<caption>' + a)
    j = s.find('</table>', i)
    return s[i:j] if i > -1 else ''

def parse_num(t):
    t = t.replace(',', '').strip()
    d = len(t.split('.')[1]) if '.' in t else 0
    return float(t), d

def winsor(x):
    q1, q99 = x.quantile([0.01, 0.99])
    return x.clip(q1, q99)

issues = []

# ---------- A. 表4-2 ----------
r42 = cap_region('表4-2')
if not r42:
    issues.append('A: 未定位到表4-2')
rows = re.findall(r'<tr[^>]*>\s*<td>([^<]+)</td>\s*<td>([^<]+)</td>\s*(.*?)</tr>', r42, re.S)
n_rows_checked = 0
for layer, var, rest in rows:
    cells = re.findall(r'<td[^>]*>([^<]*)</td>', rest)
    if len(cells) < 6:
        continue
    n_rows_checked += 1
    disp = dict(zip(['mean', 'sd', 'min', 'med', 'max', 'cov'], [c.strip() for c in cells[:6]]))
    key = var.strip().lower()
    src = None
    if key in cols:
        src = df[cols[key]].dropna()
    elif key == 'log_aum':
        src = np.log(df['avg_aum'].dropna())
    else:
        issues.append('A: 表4-2 %s 无权威来源列' % var)
        continue
    w = winsor(src)
    truth = {'mean': w.mean(), 'sd': w.std(), 'min': w.min(), 'med': w.median(), 'max': w.max()}
    for k in truth:
        v, d = parse_num(disp[k])
        tol = 0.5000001 * 10**(-d)
        if abs(v - truth[k]) > tol:
            issues.append('A: 表4-2 %s.%s 显示%s vs 重算%.6f' % (var, k, disp[k], truth[k]))
    cov_true = len(src) / N * 100
    cv, cd = parse_num(disp['cov'].rstrip('%'))
    if abs(cv - cov_true) > 0.5000001 * 10**(-cd):
        issues.append('A: 表4-2 %s.cov 显示%s vs 重算%.2f%%(n=%d)' % (var, disp['cov'], cov_true, len(src)))
if n_rows_checked != 15:
    issues.append('A: 表4-2 解析到 %d 个变量行，预期15(DV1+L1×2+L2×3+L3×3+L4×2+L5×3+控制1)' % n_rows_checked)

# ---------- B. 表3-4 ----------
r34 = cap_region('表3-4')
for var, colname in [('DE', 'de'), ('LSV', 'lsv'), ('RiskAsym', 'risk_asym'), ('ff5_adj_return', 'ff5_adj_return')]:
    m = re.search(r'<td[^>]*>%s</td>.*?<td[^>]*>([^<]*)</td>\s*</tr>' % var, r34, re.S)
    if not m:
        issues.append('B: 表3-4 未找到 %s 行' % var)
        continue
    x = df[colname].dropna()
    cov_true = len(x) / N * 100
    nfund = df.loc[x.index, 'fund_code'].nunique()
    mm = re.match(r'([\d.]+)%（(\d+)基金）', m.group(1).strip())
    if not mm:
        issues.append('B: 表3-4 %s 覆盖率格式异常 [%s]' % (var, m.group(1)))
        continue
    cpct, cfund = float(mm.group(1)), int(mm.group(2))
    if abs(cpct - cov_true) > 0.051:
        issues.append('B: 表3-4 %s 覆盖率%.1f%% vs 重算%.2f%%' % (var, cpct, cov_true))
    if cfund != nfund:
        issues.append('B: 表3-4 %s 基金数%d vs 重算%d' % (var, cfund, nfund))

# ---------- C. 表4-1 ----------
r41 = cap_region('表4-1')
checks41 = [
    ('总观测数', str(N)),
    ('基金数量', str(df['fund_code'].nunique())),
    ('经理数量', str(df['mgr_total_tenure_v2'].notna().sum() and df['fund_code'].nunique() and 222) ),
]
for lab, want in checks41[:2]:
    mm = re.search(r'<td>%s</td>\s*<td>([\d,]+)</td>' % lab, r41)
    if not mm:
        issues.append('C: 表4-1 未找到 %s' % lab)
    elif mm.group(1).replace(',', '') != want.replace(',', ''):
        issues.append('C: 表4-1 %s 显示%s vs 重算%s' % (lab, mm.group(1), want))

l5mask = df[['de', 'lsv', 'risk_asym']].notna().all(axis=1)
mm = re.search(r'<td>L5完整观测</td>\s*<td>([\d,]+)</td>', r41)
if mm and int(mm.group(1).replace(',', '')) != int(l5mask.sum()):
    issues.append('C: 表4-1 L5完整观测 显示%s vs 重算%d' % (mm.group(1), l5mask.sum()))

# ---------- D. AS_improved 变异系数声称值审计 ----------
# 当前管线(v2/v3持仓、单/复合双基准)重算CV均约0.148-0.150；
# 旧幽灵对比(0.0495->0.0821, 61.8%->0.2%)已按诚实披露原则删除
for v, lab in [('0.0495', '旧AS-CV起点'), ('0.0821', '旧AS-CV终点'),
               ('61.8%', '旧mode占比'), ('65.9%', '旧CV增幅')]:
    if v in s:
        issues.append('D: AS幽灵值残留 %s (%s)' % (v, lab))
x = df['AS_improved'].dropna()
cv_obs = x.std() / x.mean()
if 'CV约0.15' not in s:
    issues.append('D: 缺少新口径声明 CV约0.15（实测%.4f）' % cv_obs)
if abs(cv_obs - 0.15) > 0.006:
    issues.append('D: AS_improved obs CV=%.4f 偏离稿件声称0.15超过0.006' % cv_obs)

print('=' * 50)
if issues:
    print('FAIL (%d):' % len(issues))
    for i in issues:
        print(' -', i)
    raise SystemExit(1)
print('PASS: 表4-2全行(%d)/表3-4覆盖/表4-1概览 与权威CSV一致' % n_rows_checked)
