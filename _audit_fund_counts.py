import pandas as pd, numpy as np

p = pd.read_csv("指标计算流水线/output/主分析面板_重建_含TOwind.csv")
p["qidx"] = p["year"] * 4 + p["quarter"]

# 每只基金首次出现的季度
first = p.groupby("fund_code")["qidx"].min().reset_index(name="first_q")
first["first_year"] = first["first_q"] // 4
first["first_q_num"] = first["first_q"] % 4

print("=== 各年首次出现（进入样本）的基金数 ===")
vc = first["first_year"].value_counts().sort_index()
print(vc.to_string())

print("\n=== 累计首次出现（截至各年）===")
cum = vc.cumsum()
print(cum.to_string())

print("\n=== 各年存续基金数（该年有观测即为存续）===")
for y in range(2018, 2023):
    n = p[p["year"] == y]["fund_code"].nunique()
    print(f"  {y}: {n}")

# 仅看可进入横截面回归的 362 只
nu = p.groupby("fund_code")["ff5_adj_return"].nunique()
valid = set(nu[nu == 1].index)
pv = p[p["fund_code"].isin(valid)]
print("\n=== 仅 362 只有效基金：各年存续数 ===")
for y in [2018, 2019, 2020, 2021]:
    n = pv[pv["year"] == y]["fund_code"].nunique()
    print(f"  {y}: {n}")

print("\n=== 仅 362 只：各年首次出现数 ===")
fv = pv.groupby("fund_code")["qidx"].min().reset_index(name="first_q")
fv["fy"] = fv["first_q"] // 4
print(fv["fy"].value_counts().sort_index().to_string())

print("\n=== 论文口径候选对照 ===")
print("2019 存续(全样本):", p[p["year"]==2019]["fund_code"].nunique())
print("2020 存续(全样本):", p[p["year"]==2020]["fund_code"].nunique())
print("2020 首次出现(全样本):", (first["first_year"]==2020).sum())
print("2020 累计首次出现(全样本):", (first["first_year"]<=2020).sum())
