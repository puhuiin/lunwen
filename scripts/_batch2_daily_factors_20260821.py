"""批次②：L4 特质波动率(idio_vol) + L3 TM_β₂ + factor_drift
共享管道：日频 NAV(200基金) + FF5 日度因子(1995-2026)。
约束：仅新增列、不动现有 v4 基准、不破坏 run_all。

输出：
  output/batch2_daily_factors_2026-08-21.csv
    列：fund_code, year, TM_beta2, TM_alpha, idio_vol, factor_drift,
        n_days, n_days_used
"""
from pathlib import Path
import numpy as np
import pandas as pd

PROJ = Path(__file__).parent.parent
NAVPATH = PROJ / "归档" / "旧版数据" / "fund_nav_new200.csv"
FF5PATH = PROJ / "指标计算流水线" / "data" / "FF因子" / "FF5日度因子.csv"
PANELPATH = PROJ / "指标计算流水线" / "output" / "主分析面板_重建_含TOwind.csv"
OUTPATH = PROJ / "output" / "batch2_daily_factors_2026-08-21.csv"

# === 1. 加载 + 清洗 ===
nav = pd.read_csv(NAVPATH, parse_dates=["date"])
ff5 = pd.read_csv(FF5PATH, parse_dates=["date"])
panel = pd.read_csv(PANELPATH)
panel_funds = set(panel["fund_code"].unique())
years = sorted(panel["year"].unique().tolist())

# NAV 百分比 → 小数；清洗 inf/nan；去 0 方差日
nav = nav[nav["fund_code"].isin(panel_funds)].copy()
nav["daily_return"] = nav["daily_return"].astype(float)
# 极端值截尾：|daily_return| > 50% 视为数据错误
nav["daily_return"] = nav["daily_return"].where(nav["daily_return"].abs() <= 50, np.nan)
nav["daily_return"] = nav["daily_return"].replace([np.inf, -np.inf], np.nan)
nav = nav.dropna(subset=["daily_return"]).copy()
nav["year"] = nav["date"].dt.year
nav["daily_return"] = nav["daily_return"] / 100.0  # 百分比 → 小数

ff5 = ff5.sort_values("date").reset_index(drop=True)
ff5["MKT_excess"] = ff5["MKT"]  # FF5日度已是超额形式
# 平方项供 TM
ff5["MKT_excess2"] = ff5["MKT_excess"] ** 2

print(f"[1] NAV 清洗后 {len(nav):,} 行  基金 {nav['fund_code'].nunique()}  区间 {nav['date'].min().date()}–{nav['date'].max().date()}")
print(f"    FF5 {len(ff5):,} 行  区间 {ff5['date'].min().date()}–{ff5['date'].max().date()}")


# === 2. 合并 NAV×FF5 ===
merged = nav.merge(
    ff5[["date", "MKT_excess", "MKT_excess2", "SMB", "HML", "RMW", "CMA", "RF"]],
    on="date", how="inner"
)
merged["excess"] = merged["daily_return"] - merged["RF"]
merged = merged.dropna(subset=["excess", "MKT_excess", "MKT_excess2", "SMB", "HML", "RMW", "CMA"]).copy()
print(f"[2] 合并后 {len(merged):,} 行")


# === 3. 按 (fund, year) 滚动窗口回归 ===
def regress_one(g):
    """对单个基金-年的日度序列跑 TM 与 FF5 回归"""
    y_excess = g["excess"].values
    x_tm = g[["MKT_excess", "MKT_excess2"]].values
    x_ff5 = g[["MKT_excess", "SMB", "HML", "RMW", "CMA"]].values

    n = len(y_excess)
    out = dict(n_days=n, n_days_used=n, TM_beta2=np.nan, TM_alpha=np.nan,
               idio_vol=np.nan, sys_vol=np.nan, factor_drift=np.nan)

    if n < 200:
        return pd.Series(out)

    # TM: r_p − r_f = β·MKT_excess + β₂·MKT_excess² + α + ε
    try:
        X_tm = np.column_stack([np.ones(n), x_tm])
        beta_tm, *_ = np.linalg.lstsq(X_tm, y_excess, rcond=None)
        resid_tm = y_excess - X_tm @ beta_tm
        out["TM_beta2"] = beta_tm[2]
        out["TM_alpha"] = beta_tm[0]  # 截距即选股α(日度)
    except Exception:
        pass

    # FF5: r_p − r_f = β·MKT + s·SMB + h·HML + r·RMW + c·CMA + ε
    try:
        X_ff5 = np.column_stack([np.ones(n), x_ff5])
        beta_ff5, *_ = np.linalg.lstsq(X_ff5, y_excess, rcond=None)
        resid_ff5 = y_excess - X_ff5 @ beta_ff5
        # idio_vol = 残差标准差 (日度)
        out["idio_vol"] = float(np.nanstd(resid_ff5, ddof=len(beta_ff5)))
        out["sys_vol"] = float(np.nanstd(X_ff5 @ beta_ff5, ddof=0))
    except Exception:
        pass

    # factor_drift = 因子载荷的时间变异（这里用当前年度残差std/因子解释比例近似）
    # 严格定义需多年滚动，本批次用 idio_vol/(idio_vol+sys_vol) 作为特质占比
    if out["idio_vol"] is not np.nan and out["sys_vol"] is not np.nan and (out["idio_vol"] + out["sys_vol"]) > 0:
        out["factor_drift"] = out["idio_vol"] / (out["idio_vol"] + out["sys_vol"])

    return pd.Series(out)


# 改用滚动 1.5 年窗口 (本年 + 前半年)，让 β₂ 更稳定
print("[3] 滚动窗口回归（当年 + 前 1 年日度数据，最少 200 天）...")
rows = []
for fund, g_fund in merged.groupby("fund_code"):
    g_fund = g_fund.sort_values("date")
    for yr in years:
        # 窗口：前 1 年到当年末
        start = pd.Timestamp(f"{yr - 1}-01-01")
        end = pd.Timestamp(f"{yr}-12-31")
        g_win = g_fund[(g_fund["date"] >= start) & (g_fund["date"] <= end)]
        if len(g_win) < 200:
            continue
        r = regress_one(g_win)
        r["fund_code"] = fund
        r["year"] = yr
        rows.append(r)

df = pd.DataFrame(rows)
# 年化处理：日度 TM_α × 252, 日度 idio_vol × sqrt(252)
df["TM_alpha_annual"] = df["TM_alpha"] * 252
df["idio_vol_annual"] = df["idio_vol"] * np.sqrt(252)
# 截尾极端值
for c in ["TM_beta2", "TM_alpha_annual", "idio_vol_annual", "factor_drift"]:
    if c in df.columns:
        lo, hi = df[c].quantile([0.005, 0.995])
        df[c] = df[c].clip(lo, hi)

print(f"[3] 完成 {len(df):,} 个基金-年观测  基金 {df['fund_code'].nunique()}  年 {df['year'].min()}–{df['year'].max()}")

# === 4. 落盘 ===
OUTPATH.parent.mkdir(exist_ok=True)
df.to_csv(OUTPATH, index=False)
print(f"[4] 落盘 {OUTPATH}  ({OUTPATH.stat().st_size:,} 字节)")

# 描述统计
print()
print("===== 描述统计 =====")
for c in ["TM_beta2", "TM_alpha_annual", "idio_vol_annual", "factor_drift", "n_days_used"]:
    s = df[c]
    print(f"{c:18s} n={len(s):5d}  mean={s.mean():.4f}  std={s.std():.4f}  min={s.min():.4f}  median={s.median():.4f}  max={s.max():.4f}")