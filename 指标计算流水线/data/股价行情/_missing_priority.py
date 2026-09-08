# -*- coding: utf-8 -*-
"""分析缺失月收益的持仓股票：权重覆盖、频次、时间范围，判断下载优先级。"""
import os, re
import pandas as pd

BASE = r"d:\Desktop\基金经理行为分析研究\指标计算流水线\data"
HOLD = os.path.join(BASE, "L2_持仓偏离层", "基金持仓明细_全量修正版_v3.csv")

h = pd.read_csv(HOLD, encoding="utf-8-sig", dtype={"stock_code": str}, low_memory=False)
h["stock_code"] = h["stock_code"].str.zfill(6)
h["hold_ratio"] = pd.to_numeric(h["hold_ratio"], errors="coerce")
h["report_date"] = pd.to_datetime(h["report_date"], errors="coerce")

missing = set()
with open(os.path.join(BASE, "股价行情", "_missing_a_stocks.txt"), encoding="utf-8") as f:
    missing = {ln.strip() for ln in f if ln.strip()}

sub = h[h["stock_code"].isin(missing)]
print("缺失股票在持仓中的行数:", len(sub))
print("缺失股票数:", sub["stock_code"].nunique())
print("涉及基金数:", sub["fund_code"].nunique())
print("时间范围:", sub["report_date"].min(), "->", sub["report_date"].max())

# 按出现频次(报告期数)排序，前60只最有价值
freq = sub.groupby("stock_code")["report_date"].nunique().sort_values(ascending=False)
print("\n=== 出现报告期数最高 的 60 只 ===")
print(" ".join(freq.head(60).index.tolist()))

# 各年缺失行数分布
h["year"] = h["report_date"].dt.year
# 按持仓权重总量
w = sub.groupby("stock_code")["hold_ratio"].sum().sort_values(ascending=False)
print("\n=== 持仓权重累计最高 的 60 只 ===")
print(" ".join(w.head(60).index.tolist()))

# 缺失股票平均权重
print("\n缺失股票平均权重:", round(sub["hold_ratio"].mean(), 4))