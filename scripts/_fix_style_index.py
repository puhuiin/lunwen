# -*- coding: utf-8 -*-
"""修正风格指数CSV：将错误的399374（中盘成长）替换为399372（大盘成长）。
步骤：
  1) 用 akshare 下载399372日线，计算季度收益
  2) 备份原CSV为 风格指数季度收益.csv.bak_wrong_399374
  3) 用399372_q_return替换399374_q_return列，列顺序改为 399372/399373/399376/399377
     （即标准四宫格：大盘成长、大盘价值、小盘成长、小盘价值）
  4) 输出到原CSV路径
"""
import os, shutil
import pandas as pd
import numpy as np

CSV_PATH = r'd:\Desktop\基金经理行为分析研究\指标计算流水线\data\L2_持仓偏离层\风格指数季度收益.csv'
BAK_PATH = CSV_PATH + '.bak_wrong_399374'

# ---- 1. 读旧CSV ----
old = pd.read_csv(CSV_PATH, encoding='utf-8-sig')
print('旧CSV列：', list(old.columns))
print('旧CSV行数：', len(old))

# ---- 2. 下载399372日线 ----
import akshare as ak
print('正在下载399372（巨潮大盘成长）日线...')
# akshare的指数日线接口：stock_zh_index_daily 用 symbol="sz399372"
try:
    df_idx = ak.stock_zh_index_daily(symbol="sz399372")
except Exception as e:
    print('ak.stock_zh_index_daily 失败:', e)
    # 备用：用 index_zh_a_hist
    df_idx = ak.index_zh_a_hist(symbol="399372", period="daily", start_date="20100101", end_date="20261231")
    print('备用接口返回列:', list(df_idx.columns))
    print(df_idx.head(2))

print('下载行数：', len(df_idx))
print('列名：', list(df_idx.columns))
print(df_idx.head(3))
print(df_idx.tail(3))
