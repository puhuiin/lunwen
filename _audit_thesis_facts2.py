import pandas as pd, numpy as np

p = pd.read_csv("指标计算流水线/output/主分析面板_重建_含TOwind.csv")

q = p.groupby(["year","quarter"]).size().reset_index(name="n")
q = q.sort_values(["year","quarter"])
print("=== 唯一季度数 ===", len(q))
print("首季:", tuple(q.iloc[0][["year","quarter"]]), " 末季:", tuple(q.iloc[-1][["year","quarter"]]))
print("\n=== 前 6 季 ===")
print(q.head(6).to_string(index=False))
print("\n=== 末 6 季 ===")
print(q.tail(6).to_string(index=False))

print("\n=== 各年基金数（2018-2021）===")
for y in [2018,2019,2020,2021]:
    sub = p[p["year"]==y]
    print(f"  {y}: 基金 {sub['fund_code'].nunique()}  观测 {len(sub)}")

print("\n=== 论文区间口径核对 ===")
# 论文称 2006-10 至 2026-07，80 季
print("论文称 80 个季度；实际唯一季度数 =", len(q))
print("论文称起点 2006-10(即 2006Q4 起)；实际首季 =", tuple(q.iloc[0][["year","quarter"]]))
print("论文称终点 2026-07(即 2026Q3)；实际末季 =", tuple(q.iloc[-1][["year","quarter"]]))

print("\n=== SDI 零值（观测层 vs 基金层）===")
s = p["SDI"].dropna()
print("观测层: n=%d, zero share=%.3f" % (len(s), (s==0).mean()))
fm = p.groupby("fund_code")["SDI"].mean().dropna()
print("基金层: n=%d, zero share=%.3f, q25=%.4f, mean=%.4f" % (len(fm), (fm==0).mean(), fm.quantile(0.25), fm.mean()))

print("\n=== ff5_adj_return 覆盖 ===")
nu = p.groupby("fund_code")["ff5_adj_return"].nunique()
print("有 alpha 的基金数(唯一值=1):", (nu==1).sum(), " 全缺失:", (nu==0).sum(), " 总基金:", len(nu))
