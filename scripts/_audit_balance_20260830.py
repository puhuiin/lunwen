# -*- coding: utf-8 -*-
"""画像结论检验：「能力的均衡性而非单点突出」是否成立（2026-08-30）

论文 §4.2 用六个**刻意挑选的极值案例**（各维度最高/最低者）推出结论：
"能力的均衡性而非单点突出，才是持续超额收益的行为特征"。
极值案例属事后挑选，不能用来论证总体规律。本脚本用全样本直接检验该命题：
以六维分位的离散度衡量"不均衡度"，看它是否与 alpha 负相关。
"""
import os

import numpy as np
import pandas as pd

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
df = pd.read_csv(os.path.join(BASE, 'output', '画像_全样本能力表_2026-08-26.csv'), encoding='utf-8-sig')
DIM = ['基本面优势', '认知能力', '配置选择能力', '风险应对能力', '风险转化能力', '交易执行能力']
y = df['ff5_alpha']
comp = df['综合能力']
pct = df[DIM].rank(pct=True)
bal = pct.std(axis=1)
mx = pct.max(axis=1)

print('=== 均衡性 vs alpha（全样本 N=%d）===' % len(df))
print('  corr(不均衡度, alpha)      = %+.3f' % bal.corr(y))
print('  corr(不均衡度, 综合能力)   = %+.3f' % bal.corr(comp))
print('  corr(最强单点分位, alpha)  = %+.3f' % mx.corr(y))

X = np.c_[np.ones(len(df)), comp]


def resid(v):
    return v - X @ np.linalg.lstsq(X, v, rcond=None)[0]


print('  偏相关(控制综合能力后)     = %+.3f' % np.corrcoef(resid(y), resid(bal))[0, 1])

g = pd.qcut(bal.rank(method='first'), 5, labels=False)
quint_alpha = {}
print('  按不均衡度五等分（Q1 最均衡 → Q5 最不均衡）：')
for i in range(5):
    a = y[g == i].mean()
    quint_alpha['Q%d' % (i + 1)] = float(a)
    print('    Q%d  不均衡度 %.3f   alpha %+.4f' % (i + 1, bal[g == i].mean(), a))

# 落盘供论文脚本动态引用，避免正文硬编码
import io as _io
import json as _json

with _io.open(os.path.join(BASE, 'output', '逻辑审查_均衡性检验_2026-08-30.json'),
              'w', encoding='utf-8') as f:
    _json.dump({
        '样本N': int(len(df)),
        '相关': {
            '不均衡度与alpha': float(bal.corr(y)),
            '偏相关_控制综合能力': float(np.corrcoef(resid(y), resid(bal))[0, 1]),
            '最强单点分位与alpha': float(mx.corr(y)),
            '不均衡度与综合能力': float(bal.corr(comp)),
        },
        '按不均衡度五等分_alpha': quint_alpha,
    }, f, ensure_ascii=False, indent=1)
print()
print('[DONE] 已落盘 output/逻辑审查_均衡性检验_2026-08-30.json')
