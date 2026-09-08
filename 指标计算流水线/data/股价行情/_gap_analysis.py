# -*- coding: utf-8 -*-
"""对照持仓 v3 与月收益率，找出真正缺失月收益的 A 股持仓股票。
区分：基金代码(006/009/100/110/113/...等) vs A股(000-003/300/301/600-605/688/920/8xx北交)。
"""
import os, re
import pandas as pd

BASE = r"d:\Desktop\基金经理行为分析研究\指标计算流水线\data"
HOLD = os.path.join(BASE, "L2_持仓偏离层", "基金持仓明细_全量修正版_v3.csv")
MRET = os.path.join(BASE, "股价行情", "个股月收益率_全量.csv")

h = pd.read_csv(HOLD, encoding="utf-8-sig", dtype={"stock_code": str})
h["stock_code"] = h["stock_code"].str.zfill(6)
hold_codes = set(h["stock_code"].dropna())
print("持仓v3 股票数:", len(hold_codes))

m = pd.read_csv(MRET, encoding="utf-8-sig", dtype={"stock_code": str})
m["stock_code"] = m["stock_code"].str.zfill(6)
have_codes = set(m["stock_code"].dropna())
print("月收益已有股票数:", len(have_codes))

missing = hold_codes - have_codes
print("持仓中缺月收益的股票数:", len(missing))

# A股合法前缀
VALID_PFX = ('000','001','002','003','300','301','400','420','430',
             '600','601','603','605','688','689',
             '830','831','832','833','834','835','836','837','838','839',
             '870','871','872','873','920')
def is_a(c):
    return c.startswith(VALID_PFX)

a_missing = sorted([c for c in missing if is_a(c)])
non_a = sorted([c for c in missing if not is_a(c)])
print("缺月收益的 A股/北交 股票数:", len(a_missing))
print("缺月收益的非A股(基金/其他)代码数:", len(non_a))

with open(os.path.join(BASE, "股价行情", "_missing_a_stocks.txt"), "w", encoding="utf-8") as f:
    f.write("\n".join(a_missing))
with open(os.path.join(BASE, "股价行情", "_missing_nonA_codes.txt"), "w", encoding="utf-8") as f:
    f.write("\n".join(non_a))

# 打印缺失A股清单
print("\n=== 缺失 A股 清单 ===")
print(" ".join(a_missing))