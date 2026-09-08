import pandas as pd

p = pd.read_csv("指标计算流水线/output/主分析面板_重建_含TOwind.csv")
p["report_date"] = pd.to_datetime(p["report_date"])

print("=== 面板 report_date 极值 ===")
print("min:", p["report_date"].min())
print("max:", p["report_date"].max())

print("\n=== 首尾各 5 个不同 report_date ===")
u = sorted(p["report_date"].unique())
print("最早 5:", [str(x)[:10] for x in u[:5]])
print("最晚 5:", [str(x)[:10] for x in u[-5:]])

print("\n=== 唯一 report_date 个数 ===")
print(len(u), "（论文称 80 个季度）")

print("\n=== 各 report_date 的月份分布 ===")
print(pd.Series([str(x)[5:7] for x in u]).value_counts().sort_index().to_string())

print("\n=== 对照：JSON 存的是 2006-10-01 / 2026-07-01 ===")
print("真实首季末日期:", p["report_date"].min().date(), " -> [:7] =", str(p["report_date"].min())[:7])
print("真实末季末日期:", p["report_date"].max().date(), " -> [:7] =", str(p["report_date"].max())[:7])
