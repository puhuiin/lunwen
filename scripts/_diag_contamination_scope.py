# -*- coding: utf-8 -*-
"""污染范围判定：面板DV vs RA原始输入，两条数据链是否都被污染。"""
import numpy as np
import pandas as pd

panel = pd.read_csv('指标计算流水线/output/主分析面板_重建_含TOwind.csv')
print('面板列(部分):', [c for c in panel.columns if 'return' in c or c in
      ('year', 'quarter', 'quarter_return', 'risk_asym')])
g = panel.groupby(['year', 'quarter']).agg(
    n=('excess_return', 'count'), ex_mean=('excess_return', 'mean'),
    ex_std=('excess_return', 'std'),
    qr_mean=('quarter_return', 'mean') if 'quarter_return' in panel.columns else ('excess_return', 'count'))
print('\n== 面板 excess_return 按季度（近12季）==')
print(g.tail(14).round(4).to_string())

print('\n== 面板 ff5_adj_return 按季度 ==')
if 'ff5_adj_return' in panel.columns:
    g2 = panel.groupby(['year', 'quarter'])['ff5_adj_return'].agg(['count', 'mean', 'std'])
    print(g2.tail(14).round(4).to_string())

print('\n== 面板 risk_asym 按季度（近12季）==')
g3 = panel.groupby(['year', 'quarter'])['risk_asym'].agg(['count', 'mean', 'std'])
print(g3.tail(14).round(4).to_string())

print('\n== 对照：净值历史全量 在 2025Q3/2026Q2 的隐含季收益 ==')
nav = pd.read_csv('指标计算流水线/data/L4_风险应对层/基金净值历史_全量.csv',
                  encoding='utf-8-sig', nrows=200000)
print('净值文件列:', list(nav.columns))
