# -*- coding: utf-8 -*-
"""验证东财推导出的月收益 vs 现有库中同一只股票的已有月收益。"""
import pandas as pd

BASE = r"d:\Desktop\基金经理行为分析研究\指标计算流水线\data"
em = pd.read_csv(r"d:\Desktop\基金经理行为分析研究\指标计算流水线\data\股价行情\_em_test_out.csv", dtype={"stock_code": str})
full = pd.read_csv(BASE + r"\股价行情\个股月收益率_全量.csv", dtype={"stock_code": str})

# 取共同股票+月份
codes = set(em["stock_code"]) & set(full["stock_code"])
print("共同股票:", sorted(codes)[:5], "...", len(codes))

em2 = em.copy(); em2["ym"] = em2["date"].str[:7]
f2 = full.copy(); f2["ym"] = f2["date"].str[:7]
mg = em2.merge(f2, on=["stock_code", "ym"], suffixes=("_em", "_orig"))
print("共同月-股票记录数:", len(mg))

mg["diff"] = (mg["monthly_return_em"] - mg["monthly_return_orig"]).abs()
print("diff stats:")
print(mg["diff"].describe())
print("差>0.01的比例:", (mg["diff"] > 0.01).mean())

# 大偏差样本
big = mg[mg["diff"] > 0.05].head(10)
print("\n偏差 >5% 的样本:")
print(big[["stock_code","ym","monthly_return_em","monthly_return_orig","diff"]].to_string())