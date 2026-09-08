# -*- coding: utf-8 -*-
"""正式执行替换：399374(中盘成长) → 399372(大盘成长)，标准四宫格。"""
import os, shutil
import pandas as pd
import numpy as np
import akshare as ak

CSV_PATH = r'd:\Desktop\基金经理行为分析研究\指标计算流水线\data\L2_持仓偏离层\风格指数季度收益.csv'
BAK_PATH = CSV_PATH + '.bak_wrong_399374'

# ---- 1. 备份 ----
if not os.path.exists(BAK_PATH):
    shutil.copy2(CSV_PATH, BAK_PATH)
    print('已备份到', BAK_PATH)
else:
    print('备份已存在，跳过')

old = pd.read_csv(CSV_PATH, encoding='utf-8-sig')

# ---- 2. 下载399372日线并算季度收益 ----
df_idx = ak.stock_zh_index_daily(symbol="sz399372")
df_idx['date'] = pd.to_datetime(df_idx['date'])
df_idx = df_idx.sort_values('date').reset_index(drop=True)
# 季末收盘
df_idx['year'] = df_idx['date'].dt.year
df_idx['quarter'] = df_idx['date'].dt.quarter
# 每季度取最后一个交易日的close
qclose = df_idx.groupby(['year','quarter'])['close'].last().reset_index()
# 上季末收盘
qclose = qclose.sort_values(['year','quarter']).reset_index(drop=True)
qclose['prev_close'] = qclose['close'].shift(1)
qclose['399372_q_return'] = qclose['close']/qclose['prev_close'] - 1
print('399372季度收益:')
print(qclose[['year','quarter','399372_q_return']].to_string(index=False))

# ---- 3. 合并替换 ----
new = old.merge(qclose[['year','quarter','399372_q_return']], on=['year','quarter'], how='left')
# 删掉399374，加入399372
new = new.drop(columns=['399374_q_return'])
# 列顺序：大盘成长、大盘价值、小盘成长、小盘价值
new = new[['year','quarter','399372_q_return','399373_q_return','399376_q_return','399377_q_return']]
new.to_csv(CSV_PATH, index=False, encoding='utf-8-sig')
print('\n新CSV列：', list(new.columns))
print('行数：', len(new))
print('\n前10行：')
print(new.head(10).to_string(index=False))
print('\n末10行：')
print(new.tail(10).to_string(index=False))

# ---- 4. 四列覆盖率对比 ----
for c in ['399372_q_return','399373_q_return','399376_q_return','399377_q_return']:
    n = new[c].notna().sum()
    first = new.loc[new[c].notna(), ['year','quarter']].iloc[0]
    last  = new.loc[new[c].notna(), ['year','quarter']].iloc[-1]
    print(f'{c}: {n}季 有数据, {first["year"]}Q{first["quarter"]} ~ {last["year"]}Q{last["quarter"]}')
