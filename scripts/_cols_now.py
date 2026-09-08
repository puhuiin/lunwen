# -*- coding: utf-8 -*-
import pandas as pd
p = pd.read_csv(r'd:\Desktop\基金经理行为分析研究\指标计算流水线\output\主分析面板_重建_含TOwind.csv', nrows=5)
for c in p.columns:
    print(c)
