import pandas as pd, json

p = pd.read_csv("指标计算流水线/output/主分析面板_重建_含TOwind.csv")

print("=== 2019–2021 逐季基金数 ===")
g = p.groupby(["year", "quarter"])["fund_code"].nunique()
for (y, q), n in g.items():
    if 2019 <= y <= 2021:
        print(f"  {y}Q{q}: {n}")

print("\n=== 2020 年口径对照 ===")
q3 = g.get((2020, 3), None)
q4 = g.get((2020, 4), None)
year_n = p[p["year"] == 2020]["fund_code"].nunique()
print(f"  2020Q3 基金数 = {q3}")
print(f"  2020Q4 基金数 = {q4}")
print(f"  2020 全年(存续并集) = {year_n}")

print("\n=== 统计性描述 JSON 中的 2020 ===")
try:
    j = json.load(open("output/统计性描述_2026-08-26.json", encoding="utf-8"))
    for k in j:
        if isinstance(j[k], dict) and any(str(y) in str(k) for y in ["2019", "2020"]):
            print(f"  {k}: {j[k]}")
except Exception as e:
    print("  err:", e)

print("\n=== 结论：论文/结论源用的 279 对应哪个口径 ===")
print(f"  279 == 2020Q3 ? {q3 == 279}")
print(f"  279 == 2020全年 ? {year_n == 279}")
