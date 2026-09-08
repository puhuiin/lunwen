import pandas as pd, numpy as np

PROJ = "D:/Desktop/基金经理行为分析研究"
panel = pd.read_csv(f"{PROJ}/指标计算流水线/output/主分析面板_重建_含TOwind.csv")
batch2 = pd.read_csv(f"{PROJ}/output/batch2_daily_factors_2026-08-21.csv")
panel["fund_code"] = panel["fund_code"].astype(str)
batch2["fund_code"] = batch2["fund_code"].astype(str)
panel["year"] = panel["year"].astype(int)
batch2["year"] = batch2["year"].astype(int)
df = panel.merge(batch2[["fund_code","year","TM_beta2","idio_vol_annual"]], on=["fund_code","year"], how="left")
df_nav = df[df["TM_beta2"].notna()].copy()

print("=== df_nav 基本信息 ===")
print("行数:", len(df_nav), " 基金:", df_nav["fund_code"].nunique())

print("\n=== ICI 在 df_nav 的描述统计 ===")
print(df_nav["ICI"].describe())
print("ICI 非缺失:", df_nav["ICI"].notna().sum(), " 缺失:", df_nav["ICI"].isna().sum())
print("ICI 唯一值数:", df_nav["ICI"].nunique())

print("\n=== idio_vol_annual 描述 ===")
print(df_nav["idio_vol_annual"].describe())

print("\n=== ICI 与 idio_vol_annual 相关 ===")
sub = df_nav[["ICI","idio_vol_annual"]].dropna()
print("corr =", sub.corr().iloc[0,1])
X = np.column_stack([np.ones(len(sub)), sub["idio_vol_annual"].values])
y = sub["ICI"].values
b, *_ = np.linalg.lstsq(X, y, rcond=None)
print("ICI ~ idio 斜率/截距:", b)

print("\n=== 对照：M4_base 口径（无 idio）ICI ===")
V4 = ["log_aum","log_fund_age","mgr_total_tenure_v2","AS_improved","ICI","industry_hhi",
      "SDI","TO_wind","ARG","return_volatility","de","lsv","risk_asym",
      "ff5_MKT_excess","ff5_SMB","ff5_HML","ff5_RMW","ff5_CMA"]
Xb = df_nav[V4].fillna(0)
print("V4 (含 return_vol) 条件数:", float(np.linalg.cond(Xb.values)))
print("ICI 列 std:", float(Xb["ICI"].std()))

print("\n=== M4_idio 口径（idio 替 return_vol）ICI ===")
V4i = [c for c in V4 if c!="return_volatility"] + ["idio_vol_annual"]
Xi = df_nav[V4i].fillna(0)
print("V4i (含 idio) 条件数:", float(np.linalg.cond(Xi.values)))
print("idio 列 std:", float(Xi["idio_vol_annual"].std()))

print("\n=== 每个 RHS 列 std 对比 ===")
for c in V4i:
    print(f"  {c:20s} std={Xb[c].std() if c in Xb else 'NA':.6f}" if c in Xb else "")
