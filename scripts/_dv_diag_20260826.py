# -*- coding: utf-8 -*-
"""DV 结构诊断：检查 ff5_adj_return 是否存在基金内常数化"""
import numpy as np
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
d = pd.read_csv(ROOT / '指标计算流水线' / 'output' / '主分析面板_重建_含TOwind.csv')

for c in ['ff5_adj_return', 'ff3_adj_return', 'excess_return', 'quarter_return',
          'abs_return', 'RG', 'ARG']:
    g = d.groupby('fund_code')[c]
    sd = g.std()
    n = d.dropna(subset=[c])['fund_code'].nunique()
    print(f'{c:18s} nonnull={d[c].notna().sum():5d} funds={n:4d} '
          f'within_std_mean={float(np.nanmean(sd)):.6f} '
          f'zero_within_funds={int((sd < 1e-12).sum())}')

print()
sub = d.dropna(subset=['ff5_adj_return'])
cnt = sub.groupby('fund_code')['ff5_adj_return'].nunique()
print('每基金 ff5_adj_return 不同取值数分布:')
print(cnt.value_counts().head(10).to_string())
print('\n样本期:', d['report_date'].min(), '~', d['report_date'].max())
print('季度数:', d['report_date'].nunique())
print('\n每年基金数:')
print(d.groupby('year')['fund_code'].nunique().to_string())
