# -*- coding: utf-8 -*-
"""13_分层回归.py —— 按 L1-L5 分层，每层变量对基金业绩（截面，基金层均值）的专项回归。
镜像 R1 口径：DV = 基金层均值 ff5_adj_return（FF5 alpha）/ excess_return；控制 log_aum + log_fund_age；
OLS + HC1 稳健标准误。输出 output/分层回归结果.csv 并打印可读表。
目的：补齐全论文回归清单中「每个 L 层自身变量 → 业绩」的专项回归（用户指出此前遗漏）。
"""
import pandas as pd, numpy as np, statsmodels.api as sm, os

PANEL = "指标计算流水线/output/主分析面板_重建.csv"
OUT = "指标计算流水线/output/分层回归结果.csv"
os.makedirs("指标计算流水线/output", exist_ok=True)

df = pd.read_csv(PANEL)
# 派生 log_aum
df["log_aum"] = np.log(df["avg_aum"].clip(lower=1.0))
# gender 哑变量（兼容 男/女 / M/F / Male/Female）
g = df["gender"].astype(str).str.strip()
if g.str.contains("男|女").any():
    df["gender_m"] = (g == "男").astype(float)
elif g.str.contains("M|F", case=False, regex=True).any():
    df["gender_m"] = g.str.upper().eq("M").astype(float)
else:
    df["gender_m"] = np.nan
# CFA 哑变量（兼容 是/否、True/False、1/0）
_cfa = df["CFA"].astype(str).str.strip()
df["cfa_d"] = np.where(_cfa.isin(["是", "True", "true", "1", "Y", "y"]), 1.0,
                np.where(_cfa.isin(["否", "False", "false", "0", "N", "n"]), 0.0, np.nan))

# 基金层均值（截面口径，同 R1）
id_cols = ["fund_code"]
group = df.groupby("fund_code")
mean_cols = ["ff5_adj_return", "excess_return", "log_aum", "log_fund_age",
             "mgr_total_tenure_v2", "gender_m", "cfa_d", "school",
             "AS_improved", "ICI", "industry_hhi", "TO_two_sided", "SDI",
             "return_volatility", "ARG", "RG", "risk_asym", "lsv", "de", "pgr", "plr"]
fm = group[mean_cols].mean(numeric_only=True)
fm = fm.reset_index()

def ols_report(data, dv, ivs, label):
    sub = data[[dv] + ivs].dropna()
    if len(sub) < len(ivs) + 5:
        return []
    X = sm.add_constant(sub[ivs])
    m = sm.OLS(sub[dv], X).fit(cov_type="HC1")
    rows = []
    for v in ivs:
        rows.append({"layer": label, "DV": dv, "N": int(len(sub)), "R2": round(m.rsquared, 4),
                     "var": v, "coef": round(m.params[v], 5), "t": round(m.tvalues[v], 3),
                     "sig": "***" if abs(m.tvalues[v]) > 2.58 else ("**" if abs(m.tvalues[v]) > 1.96 else "")})
    return rows

results = []
controls = ["log_aum", "log_fund_age"]

# ---------- L1 背景特征层 ----------
# L1a 连续特質：任期
results += ols_report(fm, "ff5_adj_return", ["mgr_total_tenure_v2"] + controls, "L1-任期")
results += ols_report(fm, "excess_return", ["mgr_total_tenure_v2"] + controls, "L1-任期")
# L1b 性别
results += ols_report(fm, "ff5_adj_return", ["gender_m"] + controls, "L1-性别")
# L1c CFA
results += ols_report(fm, "ff5_adj_return", ["cfa_d"] + controls, "L1-CFA")

# ---------- L2 持仓偏离层 ----------
results += ols_report(fm, "ff5_adj_return", ["AS_improved", "ICI", "industry_hhi"] + controls, "L2-持仓")
results += ols_report(fm, "excess_return", ["AS_improved", "ICI", "industry_hhi"] + controls, "L2-持仓")

# ---------- L3 交易执行层 ----------
results += ols_report(fm, "ff5_adj_return", ["TO_two_sided", "SDI"] + controls, "L3-交易")
results += ols_report(fm, "excess_return", ["TO_two_sided", "SDI"] + controls, "L3-交易")

# ---------- L4 风险应对层 ----------
results += ols_report(fm, "ff5_adj_return", ["ARG", "RG", "return_volatility"] + controls, "L4-风险")
results += ols_report(fm, "excess_return", ["ARG", "RG", "return_volatility"] + controls, "L4-风险")

# ---------- L5 认知偏差层（与 R1 一致，复核） ----------
results += ols_report(fm, "ff5_adj_return", ["risk_asym", "lsv", "de"] + controls, "L5-认知")

res = pd.DataFrame([r for r in results if r])
res.to_csv(OUT, index=False, encoding="utf-8-sig")

# 打印可读表
for layer in ["L1-任期", "L1-性别", "L1-CFA", "L2-持仓", "L3-交易", "L4-风险", "L5-认知"]:
    sub = res[res.layer == layer]
    if sub.empty:
        print(f"\n[{layer}] 无结果（样本不足）"); continue
    dv = sub.DV.iloc[0]; N = int(sub.N.iloc[0]); R2 = sub.R2.iloc[0]
    print(f"\n[{layer}]  DV={dv}  N={N}  R2={R2}")
    for _, row in sub.iterrows():
        print(f"   {row['var']:18s} β={row['coef']:+.5f}  t={row['t']:+.2f} {row['sig']}")
print("\n已写出:", OUT)
