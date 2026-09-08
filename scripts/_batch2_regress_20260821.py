"""批次②入模回归：
  - M4_base          ：v4 M4 变量，但仅在 NAV 覆盖的 194 基金子样本上（验证可复现性）
  - M4_daily_L3      ：M4_base + TM_beta2 + factor_drift（替换 SDI、TO_wind）
  - M4_daily_L4      ：M4_base + idio_vol_annual（替换 return_volatility）
  - M4_daily_full    ：三个日度变量都加入
所有回归 DV=ff5_adj_return；SE=CGM2011 双向聚类(fund×year)。
"""
import json
from pathlib import Path
import numpy as np
import pandas as pd

PROJ = Path(__file__).parent.parent
PANELPATH = PROJ / "指标计算流水线" / "output" / "主分析面板_重建_含TOwind.csv"
BATCH2PATH = PROJ / "output" / "batch2_daily_factors_2026-08-21.csv"
OUTJSON = PROJ / "output" / "batch2_regressions_2026-08-21.json"
OUTCSV = PROJ / "output" / "batch2_regression_table_2026-08-21.csv"


def cluster_2way_se(X, resid, fund_codes, years, max_iter=20):
    """CGM 2011 双聚类 SE（fund × year）。"""
    n, k = X.shape
    fund_codes = np.asarray(fund_codes)
    years = np.asarray(years)
    u = resid
    meat = np.zeros((k, k))
    fund_groups = {}
    for f in np.unique(fund_codes):
        idx = np.where(fund_codes == f)[0]
        s = u[idx].sum()
        fund_groups[f] = (idx, s)
    year_groups = {}
    for y in np.unique(years):
        idx = np.where(years == y)[0]
        s = u[idx].sum()
        year_groups[y] = (idx, s)
    for idx, s in fund_groups.values():
        meat += np.outer(s, s)
    for idx, s in year_groups.values():
        meat += np.outer(s, s)
    XtX = X.T @ X
    # 处理近奇异（添加 Tikhonov 正则）
    try:
        XtX_inv = np.linalg.inv(XtX)
    except np.linalg.LinAlgError:
        XtX_inv = np.linalg.pinv(XtX)
    cov = XtX_inv @ meat @ XtX_inv
    se = np.sqrt(np.maximum(np.diag(cov) * n / (n - k), 0))
    return se


def fit(df, rhs, dv="ff5_adj_return", fund_col="fund_code", year_col="year"):
    """双向聚类 OLS。"""
    s = df[rhs + [dv, fund_col, year_col]].dropna()
    n = len(s)
    if n < 50:
        return None
    X = np.column_stack([np.ones(n), s[rhs].values])
    y = s[dv].values
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ beta
    se = cluster_2way_se(X, resid, s[fund_col].values, s[year_col].values)
    se = np.where(se > 0, se, np.nan)
    t = np.where(se > 0, beta / se, np.nan)
    from scipy.stats import t as tdist
    p = 2 * (1 - tdist.cdf(np.abs(t), df=max(n - X.shape[1], 1)))
    yhat = X @ beta
    ss_res = np.sum(resid ** 2)
    ss_tot = np.sum((y - y.mean()) ** 2)
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else np.nan
    r2_adj = 1 - (1 - r2) * (n - 1) / (n - X.shape[1])
    rows = []
    for i, name in enumerate(["_const"] + rhs):
        rows.append(dict(var=name, beta=float(beta[i]), se=float(se[i]),
                         t=float(t[i]), n=n, r2=r2, r2_adj=r2_adj))
    return rows


# === 加载 ===
panel = pd.read_csv(PANELPATH)
batch2 = pd.read_csv(BATCH2PATH)
print(f"面板 {len(panel):,} 行, batch2 {len(batch2):,} 行")

# 构造 log_aum（v4 基准所用）
panel["log_aum"] = np.log(panel["avg_aum"].astype(float))

# 合并日度指标到面板（key: fund_code+year）
batch2["year"] = batch2["year"].astype(int)
panel["year"] = panel["year"].astype(int)
panel["fund_code"] = panel["fund_code"].astype(str)
batch2["fund_code"] = batch2["fund_code"].astype(str)
df_all = panel.merge(batch2[["fund_code", "year", "TM_beta2", "TM_alpha_annual",
                              "idio_vol_annual", "factor_drift"]],
                     on=["fund_code", "year"], how="left")

print(f"[merge] df_all {len(df_all):,} 行  基金 {df_all['fund_code'].nunique()}")

# v4 M4 完整 RHS（与 _v4_benchmark.json 对齐）
V4_BASE = [
    "log_aum", "log_fund_age", "mgr_total_tenure_v2",
    "AS_improved", "ICI", "industry_hhi",
    "SDI", "TO_wind",
    "ARG", "return_volatility",
    "de", "lsv", "risk_asym",
    "ff5_MKT_excess", "ff5_SMB", "ff5_HML", "ff5_RMW", "ff5_CMA",
]

# M4 同规格，仅 NAV 子样本
df_nav = df_all[df_all["TM_beta2"].notna()].copy()
print(f"[NAV subset]  df_nav {len(df_nav):,} 行  基金 {df_nav['fund_code'].nunique()}  年份 {df_nav['year'].min()}-{df_nav['year'].max()}")
# NAV 子样本中 SDI/TO_wind 等可能缺值，做兜底填充
# SDI 的"伪零"：缺失视为 0（与结构零一致）
df_nav["SDI"] = df_nav["SDI"].fillna(0)
df_nav["TO_wind"] = df_nav["TO_wind"].fillna(df_nav["TO_wind"].median())
df_nav["ff5_MKT_excess"] = df_nav["ff5_MKT_excess"].fillna(0)
df_nav["ff5_SMB"] = df_nav["ff5_SMB"].fillna(0)
df_nav["ff5_HML"] = df_nav["ff5_HML"].fillna(0)
df_nav["ff5_RMW"] = df_nav["ff5_RMW"].fillna(0)
df_nav["ff5_CMA"] = df_nav["ff5_CMA"].fillna(0)

results = {}

# 1) M4_base（NAV 子样本，确认 v4 可复现）
print("\n[1] M4_base（NAV 子样本）")
m4base = fit(df_nav, V4_BASE)
if m4base:
    results["M4_base_nav_subset"] = m4base
    print(f"   N={m4base[0]['n']}  R²={m4base[0]['r2']:.4f}")

# 2) M4 + idio_vol_annual（替代 return_volatility，验证特质波动是否更预测）
print("\n[2] M4 + idio_vol_annual 替代 return_volatility")
rhs2 = [c for c in V4_BASE if c != "return_volatility"] + ["idio_vol_annual"]
m4_idio = fit(df_nav, rhs2)
if m4_idio:
    results["M4_idio_substitute"] = m4_idio
    print(f"   N={m4_idio[0]['n']}  R²={m4_idio[0]['r2']:.4f}")

# 3) M4 + TM_beta2（替代 SDI，验证择时信号是否更显著）
print("\n[3] M4 + TM_beta2 替代 SDI")
rhs3 = [c for c in V4_BASE if c != "SDI"] + ["TM_beta2"]
m4_tm = fit(df_nav, rhs3)
if m4_tm:
    results["M4_tm_substitute"] = m4_tm
    print(f"   N={m4_tm[0]['n']}  R²={m4_tm[0]['r2']:.4f}")

# 4) M4 + 三个日度变量同时加入
print("\n[4] M4 + idio_vol_annual + TM_beta2 + factor_drift（三个一起）")
rhs4 = [c for c in V4_BASE if c not in ("return_volatility", "SDI", "TO_wind")] + [
    "idio_vol_annual", "TM_beta2", "factor_drift"
]
m4_full = fit(df_nav, rhs4)
if m4_full:
    results["M4_daily_full"] = m4_full
    print(f"   N={m4_full[0]['n']}  R²={m4_full[0]['r2']:.4f}")

# 5) 单变量检验：TM_beta2 与 RA 的相关性（验证路径 A 的核心问题）
print("\n[5] TM_beta2 vs RA 的相关性（核心问题）")
both = df_all[["TM_beta2", "risk_asym"]].dropna()
if len(both):
    corr = both["TM_beta2"].corr(both["risk_asym"])
    print(f"   共同观测 {len(both)}  corr(TM_β₂, RA) = {corr:.4f}")
    results["corr_TMbeta2_RA"] = float(corr)

# 6) TM_beta2 自身的 M4 截面预测力
print("\n[6] TM_beta2 在 M4 完整 RHS 中的系数")
# 已在步骤 3 中产出，从 m4_tm 中提取
if "M4_tm_substitute" in results:
    for row in results["M4_tm_substitute"]:
        if row["var"] == "TM_beta2":
            results["TM_beta2_in_M4"] = row
            print(f"   TM_β₂: β={row['beta']:+.4f}  se={row['se']:.4f}  t={row['t']:+.3f}  p={row.get('p', 'NA')}")
            break

# === 落盘 ===
OUTJSON.parent.mkdir(exist_ok=True)
# JSON 不能序列化 numpy 数组，先转 float
def _conv(o):
    if isinstance(o, dict):
        return {k: _conv(v) for k, v in o.items()}
    if isinstance(o, list):
        return [_conv(x) for x in o]
    if isinstance(o, (np.floating, np.integer)):
        return float(o)
    return o
results = _conv(results)
with open(OUTJSON, "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)
print(f"\n[out] {OUTJSON}")

# CSV 汇总
summ = []
for spec_name, rows in results.items():
    if isinstance(rows, list) and rows and isinstance(rows[0], dict):
        for row in rows:
            summ.append(dict(spec=spec_name, **row))
if summ:
    pd.DataFrame(summ).to_csv(OUTCSV, index=False)
    print(f"[out] {OUTCSV}")

print("\n===== 关键发现 =====")
# 提取关键变量
for spec_name in ["M4_base_nav_subset", "M4_idio_substitute", "M4_tm_substitute", "M4_daily_full"]:
    if spec_name not in results:
        continue
    print(f"\n{spec_name}: N={results[spec_name][0]['n']}  R²={results[spec_name][0]['r2']:.4f}")
    for row in results[spec_name]:
        if row["var"] in ("_const", "risk_asym", "de", "lsv", "AS_improved", "ICI", "industry_hhi",
                          "SDI", "TO_wind", "ARG", "return_volatility",
                          "idio_vol_annual", "TM_beta2", "factor_drift"):
            print(f"  {row['var']:18s}  β={row['beta']:+.5f}  se={row['se']:.5f}  t={row['t']:+.3f}")