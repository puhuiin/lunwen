import pandas as pd, numpy as np

p = pd.read_csv("指标计算流水线/output/主分析面板_重建_含TOwind.csv")
print("=== 面板规模 ===")
print("rows:", len(p), " funds:", p["fund_code"].nunique())

dcols = [c for c in p.columns if c.lower() in ("year","quarter","季度","报告期","date","end_date")]
print("\n=== 日期相关列 ===", dcols)

print("\n=== year 范围 ===")
print("year:", p["year"].min(), "->", p["year"].max())

if "quarter" in p.columns:
    print("\n=== quarter 取值分布（末 12 项）===")
    print(p["quarter"].value_counts().sort_index().tail(12))
    print("\n=== 逐季观测数（末 8 季）===")
    g = p.groupby(["year","quarter"]).size()
    print(g.tail(8))

print("\n=== SDI 零值堆积 ===")
s = p["SDI"].dropna()
print("SDI n:", len(s), " zero share: %.3f" % (s==0).mean(), " q25:", round(s.quantile(0.25),4))

print("\n=== 各年观测数（首末各 5 年）===")
gy = p.groupby("year").size()
print(gy.head(5))
print(gy.tail(5))

print("\n=== ff5_adj_return 基金内唯一值数分布 ===")
if "ff5_adj_return" in p.columns:
    nu = p.groupby("fund_code")["ff5_adj_return"].nunique()
    print("基金数:", len(nu), " 唯一值=1 的基金数:", (nu==1).sum(), " 唯一值>1:", (nu>1).sum())
