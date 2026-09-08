# -*- coding: utf-8 -*-
"""直查基金末段的季度收益原始数据，定位RA边缘跳变的根因。"""
import numpy as np
import pandas as pd

f = '指标计算流水线/data/L4_风险应对层/基金季度收益.csv'
raw = pd.read_csv(f, encoding='utf-8-sig')
print('总行数=%d 列=%s' % (len(raw), list(raw.columns)))
dup = raw.groupby(['fund_code', 'report_date']).size()
print('重复(fund,report_date)对数=%d, 最大重复=%d' % ((dup > 1).sum(), dup.max()))

raw['report_date'] = pd.to_datetime(raw['report_date'])
raw = raw.sort_values(['fund_code', 'report_date'])

# 抽样5只存续到末端 + 2只中途清盘的基金，打印最后10个季度的收益
last_q = raw.groupby('fund_code')['report_date'].max()
gmax = last_q.max()
print('\n全局最晚report_date=%s' % gmax.date())

surv = last_q[last_q >= gmax - pd.Timedelta(days=45)].index[:5]
liq = last_q[(last_q < gmax - pd.Timedelta(days=2000))].index[:2]
show = list(surv) + list(liq)
for fc in show:
    g = raw[raw.fund_code == fc].tail(10)
    print('\n-- fund %s (末次=%s) --' % (fc, last_q[fc].date()))
    print(g[['report_date', 'quarter_return']].to_string(index=False))

# 全市场：末三行 vs 其余行的收益分布
raw['rank_from_end'] = raw.groupby('fund_code').cumcount(ascending=False)
edge = raw[raw['rank_from_end'] < 3]
rest = raw[raw['rank_from_end'] >= 3]
print('\n== 末3行 vs 其余：quarter_return 分布 ==')
print(pd.DataFrame({
    'edge_n': [len(edge)], 'edge_mean': [edge.quarter_return.mean()],
    'edge_std': [edge.quarter_return.std()],
    'rest_n': [len(rest)], 'rest_mean': [rest.quarter_return.mean()],
    'rest_std': [rest.quarter_return.std()]}).round(4).to_string(index=False))
print('\n末3行的分位数:')
print(edge['quarter_return'].describe(percentiles=[.01, .05, .25, .5, .75, .95, .99]).round(4).to_string())
print('\n其余行的分位数:')
print(rest['quarter_return'].describe(percentiles=[.01, .05, .25, .5, .75, .95, .99]).round(4).to_string())
