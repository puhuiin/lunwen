# -*- coding: utf-8 -*-
"""故事线逻辑审计（2026-08-30）

核心质疑：论文结论第四点用「综合能力五等分 → FF5 alpha 从 Q1 0.64% 单调升至 Q5 3.77%」
证明能力得分可用于筛选。但综合得分的六个维度里：
  - L4b 转化效率 = sharpe8 / sortino8 / mppm8，本身即风险调整后业绩指标；
  - L4a 过程应对含 timing = −γ，由同一段收益序列估计。
若区分度主要由这两维贡献，则「行为画像 → 预测业绩」的故事存在定义同源的循环成分。

本脚本拆解：剔除不同维度后，五等分 Q5−Q1 的 alpha 区分度还剩多少。
"""
import os

import numpy as np
import pandas as pd

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV = os.path.join(BASE, 'output', '画像_全样本能力表_2026-08-26.csv')

L1, L2, L3, L4a, L4b, L5 = ('基本面优势', '认知能力', '配置选择能力',
                            '风险应对能力', '风险转化能力', '交易执行能力')
DIM = [L1, L2, L3, L4a, L4b, L5]

df = pd.read_csv(CSV, encoding='utf-8-sig')
y = df['ff5_alpha']

print('=== 1. 六维相关矩阵 ===')
print(df[DIM].corr().round(3).to_string())

print()
print('=== 2. 各维与 ff5_alpha 的相关 ===')
for k, v in df[DIM].corrwith(y).round(3).items():
    print('  %-8s %.3f' % (k, v))


def quint(score, label):
    g = pd.qcut(score.rank(method='first'), 5, labels=False)
    a1, a5 = y[g == 0], y[g == 4]
    d = a5.mean() - a1.mean()
    se = np.sqrt(a1.var(ddof=1) / len(a1) + a5.var(ddof=1) / len(a5))
    t = d / se
    print('  %-24s Q1=%7.4f Q5=%7.4f  差=%7.4f  t=%5.2f' % (label, a1.mean(), a5.mean(), d, t))
    return {'Q1': float(a1.mean()), 'Q5': float(a5.mean()), '差': float(d), 't': float(t)}


print()
print('=== 3. 五等分 Q5−Q1 区分度：逐步剥离 L4 ===')
combos = [
    ('全六维', DIM),
    ('剔除L4b', [L1, L2, L3, L4a, L5]),
    ('剔除L4整层', [L1, L2, L3, L5]),
    ('纯行为L2L3L5', [L2, L3, L5]),
    ('仅L4b', [L4b]),
    ('仅L4a', [L4a]),
    ('仅L2', [L2]),
]
res = {}
for key, cols in combos:
    res[key] = quint(df[cols].mean(axis=1), key)

print()
print('=== 4. 同源程度量化 ===')
rest = df[[L1, L2, L3, L4a, L5]].mean(axis=1)
print('  corr(L4b, alpha)           = %.3f' % df[L4b].corr(y))
print('  corr(其余五维合成, alpha)   = %.3f' % rest.corr(y))
print('  corr(L4b, 其余五维合成)     = %.3f' % df[L4b].corr(rest))
print('  corr(L4b, L4a)             = %.3f' % df[L4b].corr(df[L4a]))
print('  corr(L1, L5)               = %.3f' % df[L1].corr(df[L5]))

print()
print('=== 5. 关键比值 ===')
full = res['全六维']['差']
pure = res['纯行为L2L3L5']['差']
no4b = res['剔除L4b']['差']
print('  纯行为三维 / 全六维      = %.1f%%' % (100 * pure / full))
print('  剔除 L4b 后 / 全六维     = %.1f%%' % (100 * no4b / full))
print('  L4b 单独 / 全六维        = %.1f%%' % (100 * res['仅L4b']['差'] / full))

# 落盘供论文脚本动态引用，避免正文硬编码（本项目约定：数字一律走 JSON 数据源）
import io as _io
import json as _json

_out = {
    '样本N': int(len(df)),
    '组合': res,
    '关键比值': {
        '纯行为三维占全六维': pure / full,
        '剔除L4b占全六维': no4b / full,
        'L4b单独占全六维': res['仅L4b']['差'] / full,
    },
    '相关': {
        '各维与alpha': {k: float(v) for k, v in df[DIM].corrwith(y).items()},
        'L4b与其余五维合成': float(df[L4b].corr(rest)),
        'L4b与L4a': float(df[L4b].corr(df[L4a])),
        'L1与L5': float(df[L1].corr(df[L5])),
    },
    '六维相关矩阵': {a: {b: float(df[a].corr(df[b])) for b in DIM} for a in DIM},
}
with _io.open(os.path.join(BASE, 'output', '逻辑审查_区分度拆解_2026-08-30.json'),
              'w', encoding='utf-8') as f:
    _json.dump(_out, f, ensure_ascii=False, indent=1)
print()
print('[DONE] 已落盘 output/逻辑审查_区分度拆解_2026-08-30.json')
