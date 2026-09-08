# -*- coding: utf-8 -*-
"""核验 §4.1.4 VIF 表与 max|r| 口径（M4 同样本、1%/99% 全样本缩尾）"""
import json
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

CSV = r"d:\Desktop\基金经理行为分析研究\指标计算流水线\output\主分析面板_重建_含TOwind.csv"
DV = "ff5_adj_return"
CONT = ["log_aum"]
FF5 = ["ff5_MKT_excess", "ff5_SMB", "ff5_HML", "ff5_RMW", "ff5_CMA"]
L1 = ["log_fund_age", "mgr_total_tenure_v2"]
L2 = ["AS_improved", "ICI", "industry_hhi"]
L3 = ["SDI", "TO_wind"]
L4 = ["ARG", "return_volatility"]
L5 = ["de", "lsv", "risk_asym"]
RHS = CONT + FF5 + L1 + L2 + L3 + L4 + L5

df = pd.read_csv(CSV)
if "log_aum" not in df.columns:
    df["log_aum"] = np.log(df["avg_aum"].clip(lower=1e-9))
for v in RHS + [DV]:
    df[v] = pd.to_numeric(df[v], errors="coerce")
    lo, hi = df[v].quantile(0.01), df[v].quantile(0.99)
    df[v + "_w"] = df[v].clip(lo, hi)

d4 = df.dropna(subset=[x + "_w" for x in RHS] + [DV + "_w"]).copy()
print("M4 sample:", len(d4), d4["fund_code"].nunique())

vif = {}
for v in RHS:
    others = [x + "_w" for x in RHS if x != v]
    r2 = smf.ols(v + "_w ~ " + " + ".join(others), data=d4).fit().rsquared
    vif[v] = round(1.0 / (1.0 - r2), 3)

print("\n-- VIF 降序 --")
for k, x in sorted(vif.items(), key=lambda t: -t[1]):
    print("%-24s %7.3f  1/VIF=%.3f" % (k, x, 1.0 / x))

nonfactor = {k: v for k, v in vif.items() if not k.startswith("ff5_")}
print("\n最大非FF5变量VIF:", max(nonfactor.items(), key=lambda t: t[1]))

C = d4[[v + "_w" for v in L5]].corr()
pairs = [(L5[i], L5[j], round(C.iloc[i, j], 4)) for i in range(3) for j in range(i + 1, 3)]
print("\nL5 两两相关（M4缩尾样本 N=%d）:" % len(d4), pairs)
print("max|r| =", max(abs(p[2]) for p in pairs))

X = d4[[v + "_w" for v in RHS]].to_numpy(float)
X = np.column_stack([np.ones(len(X)), X])
print("\n条件数 =", round(float(np.linalg.cond(X, 2) ** 0 * np.linalg.cond(X)), 4))
sv = np.linalg.svd(X / np.linalg.norm(X, axis=0), compute_uv=False)
print("标准化设计阵条件数 =", round(float(sv[0] / sv[-1]), 2))

json.dump({"n": len(d4), "funds": int(d4["fund_code"].nunique()), "vif": vif,
           "l5_pairs": pairs, "cond": round(float(sv[0] / sv[-1]), 2)},
          open(r"d:\Desktop\基金经理行为分析研究\_vif_check_20260822.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
