import pandas as pd
df = pd.read_csv("D:/Desktop/基金经理行为分析研究/指标计算流水线/output/主分析面板_重建_含TOwind.csv", nrows=0)
for c in df.columns:
    print(c)
