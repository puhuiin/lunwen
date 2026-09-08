# -*- coding: utf-8 -*-
"""终极确认：季度边界单日跳变特征 + 全历史污染季扫描。"""
import numpy as np
import pandas as pd

nav = pd.read_csv('指标计算流水线/data/L4_风险应对层/基金净值历史_全量.csv',
                  encoding='utf-8-sig')
nav['date'] = pd.to_datetime(nav['date'])
print('NAV行数=%d 基金数=%d 日期范围=%s~%s' % (
    len(nav), nav.fund_code.nunique(), nav.date.min().date(), nav.date.max().date()))

# 季度边界跳变：每个季度首日的daily_return分布（相对该基金自身波动）
nav['is_qstart'] = nav.groupby(['fund_code', nav.date.dt.year, nav.date.dt.quarter])[
    'date'].transform('min') == nav['date']
qs = nav[nav.is_qstart]
big = qs[qs['daily_return'].abs() > 0.15]
print('\n季度首日|单日收益|>15%%的行数=%d，涉及日期:' % len(big))
print(big.groupby(big.date.dt.to_period('Q')).size().sort_values(
    ascending=False).head(10).to_string())

# 全历史截面扫描：每季中位数/MAD/离群占比
qret = pd.read_csv('指标计算流水线/data/L4_风险应对层/基金季度收益.csv',
                   encoding='utf-8-sig')
qret['report_date'] = pd.to_datetime(qret['report_date'])
qret['pq'] = qret.report_date.dt.to_period('Q')


def mad(s):
    m = s.median()
    return np.median(np.abs(s - m))


scan = qret.groupby('pq')['quarter_return'].agg(
    n='count', med='median', mad=mad,
    p05=lambda s: s.quantile(.05), p95=lambda s: s.quantile(.95),
    beyond=lambda s: (s.abs() > .30).mean())
sus = scan[(scan['mad'] > .10) | (scan.beyond > .10)]
print('\n== 可疑季度（MAD>0.10 或 |r|>30%%占比>10%%）==')
print(sus.round(4).to_string())
print('\n== 近8季对照 ==')
print(scan.tail(8).round(4).to_string())
