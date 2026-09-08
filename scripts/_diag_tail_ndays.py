# -*- coding: utf-8 -*-
"""确认污染范围：n_days覆盖 + 各季度收益分布 + 污染季识别。"""
import numpy as np
import pandas as pd

f = '指标计算流水线/data/L4_风险应对层/基金季度收益.csv'
raw = pd.read_csv(f, encoding='utf-8-sig')
raw['report_date'] = pd.to_datetime(raw['report_date'])
raw['year'] = raw['report_date'].dt.year
raw['q'] = raw['report_date'].dt.quarter

print('== n_days 按季度（近12个季度）==')
recent = raw[(raw.year >= 2023)]
g = recent.groupby(['year', 'q'])['n_days'].agg(['count', 'min', 'median', 'max'])
print(g.to_string())

print('\n== 完整季度交易日应为 ~61-63 天 ==')
print('n_days<50 的行数=%d，其年季分布:' % (raw.n_days < 50).sum())
print(raw[raw.n_days < 50].groupby(['year', 'q']).size().to_string())

print('\n== 全样本季度收益分布（近12季）==')
gg = recent.groupby(['year', 'q'])['quarter_return'].agg(
    ['count', 'mean', 'std', 'median',
     lambda s: s.quantile(.05), lambda s: s.quantile(.95)])
gg.columns = ['count', 'mean', 'std', 'median', 'p05', 'p95']
print(gg.round(4).to_string())

# 更早历史对照
old = raw[(raw.year >= 2019) & (raw.year <= 2022)]
go = old.groupby(['year', 'q'])['quarter_return'].agg(['mean', 'std'])
print('\n2019-2022 对照均值=%.4f std=%.4f' % (go['mean'].mean(), go['std'].mean()))
