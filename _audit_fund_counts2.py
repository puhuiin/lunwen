import pandas as pd

p = pd.read_csv("指标计算流水线/output/主分析面板_重建_含TOwind.csv")

# 修正：直接按 (year, quarter) 排序取首次出现，避免 qidx//4 的 Q4 取整 bug
first = (p.sort_values(["year", "quarter"])
          .groupby("fund_code")[["year", "quarter"]]
          .first()
          .reset_index())
first = first.rename(columns={"year": "first_year", "quarter": "first_q"})

print("=== 每只基金首次出现的真实 (年,季) 频次（前 10）===")
print(first.groupby(["first_year", "first_q"]).size().head(10).to_string())

print("\n=== 各年首次出现基金数（非累计，已修正 Q4 bug）===")
vc = first["first_year"].value_counts().sort_index()
print(vc.to_string())

print("\n=== 累计首次出现（截至各年末）===")
cum = vc.cumsum()
print(cum.to_string())

print("\n=== 各年存续基金数（该年有观测）===")
surv = p.groupby("year")["fund_code"].nunique()
print(surv.loc[[y for y in [2018, 2019, 2020, 2021, 2022] if y in surv.index]].to_string())

print("\n=== 关键对照 ===")
for y in [2019, 2020]:
    c = int(cum.get(y, 0))
    s = int(surv.get(y, 0))
    print(f"  {y}: 累计首次出现={c}   当年存续={s}   差={s-c}")

print("\n=== 论文/结论源称：2019=61, 2020=279 ===")
print("2019 存续 =", int(surv.get(2019, 0)), " 累计 =", int(cum.get(2019, 0)))
print("2020 存续 =", int(surv.get(2020, 0)), " 累计 =", int(cum.get(2020, 0)))

# 检查 2020Q4 新进入的基金数（此前被误归到 2021）
n20q4 = int(((first["first_year"] == 2020) & (first["first_q"] == 4)).sum())
print("\n2020Q4 首次进入的基金数 =", n20q4, "（这些是此前 qidx//4 bug 误归到 2021 的部分）")
