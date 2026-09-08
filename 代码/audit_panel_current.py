# -*- coding: utf-8 -*-
"""Fresh coverage + leakage audit of the re-run master panel."""
import pandas as pd
import numpy as np
import os

PANEL = r"D:/Desktop/基金经理行为分析研究/指标计算流水线/output/主分析面板_重建.csv"
df = pd.read_csv(PANEL, encoding="utf-8-sig")
n_obs, n_funds = len(df), df["fund_code"].nunique()
print("="*70)
print(f"主分析面板_重建.csv  |  obs={n_obs}  funds={n_funds}  cols={df.shape[1]}")
print("="*70)

# date range
rd = pd.to_datetime(df["report_date"], errors="coerce")
print(f"report_date range: {rd.min().date()}  ->  {rd.max().date()}")

# dup keys
key = ["fund_code", "report_date"]
dups = df.duplicated(subset=key).sum()
print(f"duplicate (fund_code,report_date) keys: {dups}")

# coverage per metric
metrics = ["avg_aum","TO_two_sided","OCI_two_sided","total_buy","total_sell",
           "de","ICI","industry_hhi","SDI","school","return_volatility",
           "RG","quarter_return","future_return","LSV","AS_improved"]
print("\n--- coverage (non-null %) ---")
for m in metrics:
    if m in df.columns:
        cov = df[m].notna().mean()*100
        nf = df.loc[df[m].notna(), "fund_code"].nunique()
        print(f"  {m:18s} {cov:6.2f}%   funds_with_data={nf}")
    else:
        print(f"  {m:18s} [COLUMN MISSING]")

# TO funds distinct
if "TO_two_sided" in df.columns:
    print(f"\nTO_two_sided distinct funds: {df.loc[df['TO_two_sided'].notna(),'fund_code'].nunique()}")

# leakage audit: future_return / q_end
print("\n--- leakage audit ---")
if "q_end" in df.columns:
    qe = pd.to_datetime(df["q_end"], errors="coerce")
    print(f"q_end max: {qe.max().date()}  (2026Q3 q_end would be 2026-09-30)")
    leak = (qe > pd.Timestamp("2026-09-30")).sum()
    print(f"rows with q_end > 2026-09-30 (future quarter leak): {leak}")
# max obs date overall (any date-like col near 2026Q3+)
for c in ["nav_date","date","future_return"]:
    pass
# check any column containing 2026-10 onward? future_return is shift(-1) of quarter_return
fr = df["future_return"].notna().sum()
print(f"future_return non-null: {fr}  (last panel quarter 2026Q2 -> should be NaN there)")

# column list
print("\n--- all columns ---")
print(", ".join(df.columns.tolist()))
