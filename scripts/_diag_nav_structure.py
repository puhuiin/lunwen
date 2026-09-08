# -*- coding: utf-8 -*-
"""决定性检验：2025Q3/2026Q2 内部的日度收益结构——重置伪影 vs 真实行情。"""
import numpy as np
import pandas as pd

nav = pd.read_csv('指标计算流水线/data/L4_风险应对层/基金净值历史_全量.csv',
                  encoding='utf-8-sig')
nav['date'] = pd.to_datetime(nav['date'])

for lab, lo, hi in [('2025Q3', '2025-07-01', '2025-09-30'),
                    ('2026Q2', '2026-04-01', '2026-06-30'),
                    ('对照2025Q2', '2025-04-01', '2025-06-30')]:
    seg = nav[(nav.date >= lo) & (nav.date <= hi)]
    dr = seg['daily_return']
    print('\n== %s 日度收益结构 == (%d行)' % (lab, len(seg)))
    print('mean=%.5f median=%.5f std=%.5f  |r|>5%%占比=%.3f' % (
        dr.mean(), dr.median(), dr.std(), (dr.abs() > .05).mean()))
    # 单日截面中位数最大的日期Top5
    cm = seg.groupby('date')['daily_return'].median()
    print('截面单日中位数最高的5天:')
    print(cm.nlargest(5).round(4).to_string())
    # 净值水平本身是否平滑增长（复权重置特征：每日近似等比）
    piv = seg.pivot_table(index='date', values='nav',
                          aggfunc='median') if False else seg.groupby('date')['nav'].median()
    if len(piv) > 10:
        ratio = piv.pct_change().dropna()
        print('净值水平(中位)首=%s 末=%s 区间累计=%.3f' % (
            piv.iloc[0], piv.iloc[-1], piv.iloc[-1] / piv.iloc[0] - 1))
