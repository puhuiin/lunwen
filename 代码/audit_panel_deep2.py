import pandas as pd, numpy as np, glob, os

PYTHON = "C:/Users/26955/.workbuddy/binaries/python/envs/default/Scripts/python.exe"
PANEL = "指标计算流水线/output/主分析面板_重建.csv"
df = pd.read_csv(PANEL, encoding="utf-8-sig", low_memory=False)
df["report_date"] = pd.to_datetime(df["report_date"], errors="coerce")
df["year"] = df["report_date"].dt.year

print("="*70)
print("F. 2026 report_date 分布 & future_return 一致性")
print("="*70)
y26 = df[df["year"]==2026]
print("2026 obs:", len(y26))
print(y26["report_date"].value_counts().sort_index())
print("\nfuture_return by 2026 report_date:")
for rd, g in y26.groupby("report_date"):
    print(f"  {rd.date()}: n={len(g)} future_nonNaN={g['future_return'].notna().sum()} RG_nonNaN={g['RG'].notna().sum()}")
# global future_return non-NaN by year (should be 100% except last avail quarter)
print("\nfuture_return rate by year (expect 100% except 2026):")
print(df.groupby("year")["future_return"].apply(lambda s: round(s.notna().mean()*100,1)).to_string())

print("\n" + "="*70)
print("G. 有效「行为样本」窗口（RG 非 NaN 的 fund-quarter）")
print("="*70)
print("year   obs   RG_nonNaN   RG_rate%   funds_with_RG")
for y in range(2006,2027):
    sub = df[df["year"]==y]
    rg = sub["RG"].notna()
    if len(sub)==0: continue
    print(f"{y}  {len(sub):5d}  {rg.sum():5d}      {rg.mean()*100:6.1f}     {sub.loc[rg,'fund_code'].nunique()}")

print("\n" + "="*70)
print("H. LSV 真实性核验（是否仍占位/常数）")
print("="*70)
lsv = df["lsv"].dropna()
print(f"n={len(lsv)} unique={lsv.nunique()} std={lsv.std():.4f} min={lsv.min():.4f} max={lsv.max():.4f}")
print("by year non-NaN count & mean:")
for y in range(2006,2027):
    s = df[df["year"]==y]["lsv"].dropna()
    if len(s): print(f"  {y}: n={len(s)} mean={s.mean():.4f} std={s.std():.4f}")

print("\n" + "="*70)
print("I. 持仓快照覆盖（解释 2018 断点）")
print("="*70)
# scan the canonical holding snapshot store for distinct quarter-ends
cand = ["数据/L2_持仓偏离层/基金持仓明细_全量修正版.csv",
        "指标计算流水线/data/L2_持仓偏离层/基金持仓明细_全量修正版.csv"]
for f in cand:
    if os.path.exists(f):
        h = pd.read_csv(f, encoding="utf-8-sig", low_memory=False)
        print(f"\n{f}\n  shape={h.shape} cols={list(h.columns)[:12]}")
        # find a date-like column
        for c in h.columns:
            if "date" in c.lower() or "季度" in c or "报告期" in c or "时间" in c:
                print(f"  date-col '{c}': sample={h[c].dropna().unique()[:6]}")
                break

# snapshot count by scanning L4 holding files dates
print("\nL4 持仓文件按报告期覆盖（粗略）：")
import re
for f in sorted(glob.glob("数据/L4_风险应对层/*.csv")):
    h = pd.read_csv(f, encoding="utf-8-sig", low_memory=False)
    dtcols=[c for c in h.columns if any(k in c.lower() for k in ["date","季度","报告期","时间","period"])]
    info = ""
    if dtcols:
        col=dtcols[0]
        u = pd.to_datetime(h[col], errors="coerce").dropna()
        if len(u): info=f"  [{col}] {u.min().date()}..{u.max().date()} n={len(u)}"
    print(f"  {os.path.basename(f)}: shape={h.shape}{info}")

print("\n" + "="*70)
print("J. 早期年份观测极少（存活/成立偏差）")
print("="*70)
for y in [2006,2007,2008,2009,2010,2011,2012,2013,2014,2015,2016,2017]:
    sub=df[df["year"]==y]
    print(f"  {y}: obs={len(sub)} funds={sub['fund_code'].nunique()}")
