import pandas as pd, numpy as np, glob, os, json

PYTHON = "C:/Users/26955/.workbuddy/binaries/python/envs/default/Scripts/python.exe"
PANEL = "指标计算流水线/output/主分析面板_重建.csv"

df = pd.read_csv(PANEL, encoding="utf-8-sig", low_memory=False)
df["report_date"] = pd.to_datetime(df["report_date"], errors="coerce")
df["year"] = df["report_date"].dt.year
df["q"] = df["report_date"].dt.quarter

print("="*70)
print("A. 面板规模与结构")
print("="*70)
print(f"rows={len(df)}  cols={df.shape[1]}")
print(f"fund_code nunique={df['fund_code'].nunique()}")
print(f"report_date range: {df['report_date'].min().date()} -> {df['report_date'].max().date()}")
print(f"year range: {df['year'].min()} -> {df['year'].max()}")

# duplicate (fund, report_date) keys
dup = df.duplicated(subset=["fund_code","report_date"]).sum()
print(f"DUPLICATE (fund_code, report_date) keys: {dup}")

# balance check
cnt = df.groupby("fund_code")["report_date"].count()
print(f"obs per fund: min={cnt.min()} median={int(cnt.median())} max={cnt.max()} mean={cnt.mean():.1f}")
print(f"funds with full 20yr(80q) coverage: {(cnt>=80).sum()}")
print(f"funds >=40q: {(cnt>=40).sum()}")

print("\n" + "="*70)
print("B. 分年观测数 & 关键指标覆盖率")
print("="*70)
key_cols = ["RG","future_return","quarter_return","excess_return","return_volatility",
            "ARG","de","pgr","plr","lsv","risk_asym","n_gain","n_loss",
            "TO_two_sided","avg_aum","AS_improved","ICI","industry_hhi","SDI",
            "mgr_total_tenure_v2","log_fund_age","ff3_adj_return","ff5_adj_return"]
hdr = "year  obs  " + " ".join(f"{c[:6]:>7}" for c in key_cols)
print(hdr)
for y in range(int(df['year'].min()), int(df['year'].max())+1):
    sub = df[df['year']==y]
    if len(sub)==0: continue
    row = f"{y} {len(sub):4d} "
    for c in key_cols:
        rate = sub[c].notna().mean()*100 if c in sub else float('nan')
        row += f"{rate:6.1f} "
    print(row)

print("\n" + "="*70)
print("C. 未来日期泄漏专项审计")
print("="*70)
NAV_MAX = pd.Timestamp("2026-08-07")
# 1) report_date beyond nav max
print(f"report_date > NAV_MAX({NAV_MAX.date()}): {(df['report_date']>NAV_MAX).sum()}")
# 2) any true fund-quarter 2026Q3+ (report_date >= 2026-10-01)
leak_q3 = (df['report_date']>=pd.Timestamp("2026-10-01")).sum()
print(f"report_date >= 2026-10-01 (true 2026Q3+): {leak_q3}")
# 3) future_return non-NaN on last available quarter (2026Q2) => leak
last_q = df[df['report_date']==df['report_date'].max()]
print(f"last report_date={df['report_date'].max().date()} obs={len(last_q)} future_return_nonNaN={(last_q['future_return'].notna()).sum()}")
# 4) any date-like field beyond nav max (scan numeric extreme in returns not a date but sanity)
# 5) quarterly_return using months beyond 2026-06 in stock master
sm = pd.read_csv("数据/股价行情/个股月收益率_全量.csv", encoding="utf-8-sig")
sm["date"]=pd.to_datetime(sm["date"],errors="coerce")
print(f"stock monthly master max date={sm['date'].max().date()} (2026-07 present={ (sm['date']>=pd.Timestamp('2026-07-01')).sum() } rows)")
print(f"  -> 2026-07 rows exist but quarterly_return must use <= q_end. Check RG at 2026Q2 uses only <=2026-06.")
# 6) RG at 2026Q1/Q2 non-NaN (should be filled, not leaked)
for rd in [pd.Timestamp("2026-04-01"), pd.Timestamp("2026-07-01")]:
    s = df[df['report_date']==rd]
    print(f"  {rd.date()}: RG_nonNaN={s['RG'].notna().sum()}/{len(s)}  future_return_nonNaN={s['future_return'].notna().sum()}/{len(s)}")

print("\n" + "="*70)
print("D. 数值质量：inf / 极端值 / 缺失集中")
print("="*70)
num_cols = df.select_dtypes(include=[np.number]).columns
for c in num_cols:
    s = df[c]
    n_inf = np.isinf(s).sum()
    n_nan = s.isna().sum()
    if n_inf>0 or n_nan>0:
        pass
# extreme return checks
for c in ["RG","quarter_return","future_return","excess_return","ff3_adj_return"]:
    s = df[c].dropna()
    if len(s):
        print(f"{c:16s} min={s.min():.3f} max={s.max():.3f} |inf|={np.isinf(s).sum()} p1={s.quantile(.01):.3f} p99={s.quantile(.99):.3f}")
# ARG / de / lsv plausibility
for c in ["ARG","de","pgr","plr","lsv","return_volatility"]:
    s = df[c].dropna()
    if len(s):
        print(f"{c:16s} n={len(s)} min={s.min():.4f} max={s.max():.4f} mean={s.mean():.4f}")

print("\n" + "="*70)
print("E. 持仓支撑窗口（解释 RG/de/lsv 覆盖率断点）")
print("="*70)
# find holding snapshot files
hold_files = sorted(glob.glob("数据/**/*持仓*.csv", recursive=True)) + sorted(glob.glob("指标计算流水线/data/**/*持仓*.csv", recursive=True))
print("holding-related files found:")
for h in hold_files[:20]:
    print("  ", h)
# snapshot coverage by counting distinct quarter-end dates in a representative holding file
# try to locate the canonical holding snapshot store
import subprocess
EOF
