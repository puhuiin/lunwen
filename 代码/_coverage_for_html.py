# -*- coding: utf-8 -*-
"""一次性覆盖快照：为主分析面板_重建.csv 生成 HTML 回归文档所需的真实数字。"""
import numpy as np
import pandas as pd

PANEL = "D:/Desktop/基金经理行为分析研究/指标计算流水线/output/主分析面板_重建.csv"
df = pd.read_csv(PANEL, dtype={"fund_code": str})
df["log_aum"] = np.log(df["avg_aum"].clip(lower=1.0))
df["report_date"] = pd.to_datetime(df["report_date"], errors="coerce")

print("==== SHAPE ====")
print("rows, cols:", df.shape)
print("funds:", df["fund_code"].nunique())
print("report_date range:", df["report_date"].min(), "->", df["report_date"].max())
print("year span:", int(df["year"].min()), "->", int(df["year"].max()))

print("\n==== COVERAGE (non-null % / distinct funds) ====")
key_cols = ["mgr_total_tenure_v2","log_fund_age","gender","education","CFA","school",
            "AS_improved","ICI","industry_hhi","SDI","TO_two_sided","OCI_two_sided",
            "avg_aum","ARG","return_volatility","de","pgr","plr","lsv","risk_asym",
            "quarter_return","future_return","excess_return","RG","abs_return",
            "ff3_adj_return","ff4_adj_return","ff5_adj_return"]
for c in key_cols:
    nn = df[c].notna().sum()
    nf = df.loc[df[c].notna(), "fund_code"].nunique()
    print(f"  {c:18s} {nn:5d} ({nn/len(df)*100:5.1f}%)  funds={nf}")

print("\n==== L5 COMPLETE (lsv & de & risk_asym non-null) ====")
l5 = df[["lsv","de","risk_asym"]].notna().all(axis=1)
print("L5_complete obs:", int(l5.sum()), "funds:", int(df.loc[l5,"fund_code"].nunique()))

print("\n==== CROSS-SECTIONAL N (fund-level mean complete) ====")
g = df.groupby("fund_code")
fund = pd.DataFrame({
    "alpha5": g["ff5_adj_return"].first(),
    "excess_mean": g["excess_return"].mean(),
    "risk_asym": g["risk_asym"].mean(),
    "lsv": g["lsv"].mean(),
    "de": g["de"].mean(),
    "log_aum": g["avg_aum"].apply(lambda s: np.log(s.dropna().mean()) if s.dropna().mean()>0 else np.nan),
    "log_fund_age": g["log_fund_age"].first(),
})
cs_with = fund.dropna(subset=["alpha5","risk_asym","lsv","de","log_aum","log_fund_age"])
cs_without = fund.dropna(subset=["alpha5","risk_asym","lsv","de","log_fund_age"])
print("CS with aum   N funds:", len(cs_with))
print("CS no   aum   N funds:", len(cs_without))

print("\n==== FORWARD N (panel, with vs without aum) ====")
d = df.sort_values(["fund_code","year","quarter"]).copy()
def roll4(s): return s.shift(-1).rolling(4, min_periods=4).mean()
d["fut1q"] = d.groupby("fund_code")["excess_return"].shift(-1)
d["fut4q"] = d.groupby("fund_code")["excess_return"].transform(roll4)
fw_with = d.dropna(subset=["risk_asym","lsv","de","log_aum","log_fund_age","fut4q"]).copy()
fw_without = d.dropna(subset=["risk_asym","lsv","de","log_fund_age","fut4q"]).copy()
print("FWD 4Q with aum   N obs / funds:", len(fw_with), fw_with["fund_code"].nunique())
print("FWD 4Q no  aum   N obs / funds:", len(fw_without), fw_without["fund_code"].nunique())

print("\n==== EGARCH sample (needs risk_asym + future_return + return_volatility + egarch_gamma) ====")
print("(egarch_gamma from output/EGARCH_基金层不对称.csv)")
