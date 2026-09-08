# -*- coding: utf-8 -*-
import numpy as np, pandas as pd
PANEL = "D:/Desktop/基金经理行为分析研究/指标计算流水线/output/主分析面板_重建.csv"
SCALE = "D:/Desktop/基金经理行为分析研究/指标计算流水线/data/L1_背景特征层/基金规模历史_批量.csv"

df = pd.read_csv(PANEL, dtype={"fund_code": str})
print("=== log_fund_age 诊断 ===")
print("  dtype:", df['log_fund_age'].dtype)
s = df['log_fund_age']
print("  describe:\n", s.describe())
print("  isnan:", s.isna().sum(), " isinf:", np.isinf(s.astype(float)).sum() if s.dtype!=object else 'n/a')
print("  min/max:", s.min(), s.max())
print("  非有限(正确算法):", (~np.isfinite(s.astype(float))).sum())
print("  样例非有限:", s[~np.isfinite(s.astype(float))].head(5).tolist())
# 反查来源：基金详细信息_最终版.csv 成立日
det = pd.read_csv("D:/Desktop/基金经理行为分析研究/指标计算流水线/data/L1_背景特征层/基金详细信息_最终版.csv", encoding="utf-8-sig", nrows=5)
print("  基金详细信息列:", list(det.columns)[:15])

print("\n=== avg_aum <=0 诊断 ===")
bad = df[df['avg_aum']<=0]
print("  行数:", len(bad))
print("  avg_aum 值分布(<=0):", bad['avg_aum'].value_counts().head())
print("  这些行的 year/quarter/fund 样例:")
print(bad[['fund_code','year','quarter','avg_aum']].head(10).to_string(index=False))
# 查规模源文件
sc = pd.read_csv(SCALE, encoding="utf-8-sig")
sc['net_asset'] = pd.to_numeric(sc['net_asset'], errors='coerce')
print("\n  规模源 net_asset: 行数=%d, <=0 行数=%d, 最小值=%.4f, 中位数=%.2f" % (len(sc), (sc['net_asset']<=0).sum(), sc['net_asset'].min(), sc['net_asset'].median()))
print("  规模源 net_asset<=0 样例:")
print(sc[sc['net_asset']<=0][['fund_code','year','quarter','net_asset']].head(10).to_string(index=False))
