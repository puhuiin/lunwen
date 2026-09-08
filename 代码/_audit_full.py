# -*- coding: utf-8 -*-
"""全流程数据严谨性审计：重点验证无 2026Q3 未来泄漏 + 各项完整性。"""
import os, numpy as np, pandas as pd

BASE = "D:/Desktop/基金经理行为分析研究/指标计算流水线"
PANEL = os.path.join(BASE, "output/主分析面板_重建.csv")
TOFILE = os.path.join(BASE, "data/L3_交易行为层/基金换手率_双边_含卖出.csv")
NAV   = os.path.join(BASE, "data/L4_风险应对层/基金净值历史_全量.csv")
HOLD  = os.path.join(BASE, "data/L2_持仓偏离层/基金持仓明细_全量修正版.csv")

print("="*70)
print("A. 面板基础")
df = pd.read_csv(PANEL, dtype={"fund_code": str})
df["report_date"] = pd.to_datetime(df["report_date"], errors="coerce")
df["ym"] = df["report_date"].dt.month
print(f"  shape={df.shape}  funds={df['fund_code'].nunique()}")
print(f"  report_date: {df['report_date'].min()} -> {df['report_date'].max()}")
print(f"  year range: {df['year'].min()} -> {df['year'].max()}  quarter: {sorted(df['quarter'].unique())}")

print("\nB. 未来泄漏检查（核心）")
print(f"  面板最大 (year,quarter) = {(int(df['year'].max()), int(df['quarter'].max()))}")
has_2026q3 = ((df['year']==2026)&(df['quarter']==3)).sum()
print(f"  含 2026Q3 行数 = {has_2026q3}  (必须为 0)")
# future_return 应等于同基金下一季 quarter_return
df = df.sort_values(["fund_code","year","quarter"]).reset_index(drop=True)
g = df.groupby("fund_code")
qret_next = g["quarter_return"].shift(-1)
mism = (df["future_return"].notna() & qret_next.notna() &
        (np.abs(df["future_return"] - qret_next) > 1e-9)).sum()
print(f"  future_return 与下一季 quarter_return 不一致数 = {mism}  (应为 0)")
# 末季 future_return 必为 NaN
last_mask = g.cumcount(ascending=False) == 0  # 每只基金最后一行
last_with_fut = df.loc[last_mask, "future_return"].notna().sum()
print(f"  各基金最后一季仍含 future_return 的行数 = {last_with_fut}  (应为 0)")
# future_return 非空的 (year,quarter) 最大
fut_ok = df[df["future_return"].notna()]
mx = fut_ok[["year","quarter"]].drop_duplicates().sort_values(["year","quarter"]).tail(1)
print(f"  future_return 非空最大 (year,quarter) 对 = {tuple(int(x) for x in mx.iloc[0])}  (应<=(2026,1))")

print("\nC. FF 因子外推检查")
for c in ["MKT_excess","ff5_MKT_excess","rf","ff5_RF"]:
    sub = df[df[c].notna()]
    if len(sub):
        mx = sub[["year","quarter"]].drop_duplicates().sort_values(["year","quarter"]).tail(1)
        print(f"  {c:16s} 非空最大 (y,q)={tuple(int(x) for x in mx.iloc[0])}  n={len(sub)}")
    else:
        print(f"  {c:16s} 全空")
# excess_return 2026Q2 应缺失（因子止于2026Q1）
ex26q2 = df[(df['year']==2026)&(df['quarter']==2)]["excess_return"].notna().sum()
print(f"  2026Q2 的 excess_return 非空数 = {ex26q2}  (因子止于2026Q1，应为 0)")

print("\nD. 主键与异常值")
dup = df.duplicated(subset=["fund_code","report_date"]).sum()
print(f"  重复主键 (fund_code,report_date) = {dup}  (应为 0)")
print(f"  mgr_total_tenure_v2 < 0 行数 = {(df['mgr_total_tenure_v2']<0).sum()}  (应为 0)")
print(f"  avg_aum <= 0 行数 = {(df['avg_aum']<=0).sum()}  (应为 0，已修复为 NaN)")
print(f"  log_fund_age 非有限数 = {(~np.isfinite(df['log_fund_age'].astype(float))).sum()}  (应为 0)")
print(f"  存在 (2026,3) 或 (2026,4) 行数 = {((df['year']==2026)&(df['quarter'].isin([3,4]))).sum()}  (应为 0)")

print("\nE. de 仅 6/12 月快照检查")
# report_date = 季末+1天: Q2(06-30)->07-01(month7); Q4(12-31)->01-01(month1)
de_nonnull = df[df["de"].notna()]
bad_month = de_nonnull[~de_nonnull["ym"].isin([1,7])]
print(f"  de 非空行数 = {len(de_nonnull)}; 其中 report_date 月份不在 {{1,7}} 的行 = {len(bad_month)}  (应为 0)")

print("\nF. avg_aum 全样本检查（非 200 基金版）")
print(f"  avg_aum 非空行 = {df['avg_aum'].notna().sum()} ({df['avg_aum'].notna().mean()*100:.1f}%)  基金数 = {df.loc[df['avg_aum'].notna(),'fund_code'].nunique()}")

print("\nG. TO 基座完整性（(buy+sell)/(2*aum) 校验）")
tof = pd.read_csv(TOFILE, encoding="utf-8-sig")
tof["fund_code"] = tof["fund_code"].astype(str)
recompute = (tof["total_buy"]+tof["total_sell"])/(2*tof["avg_aum"])
ratio = (tof["TO_two_sided"]/recompute).replace([np.inf,-np.inf],np.nan).dropna()
print(f"  TO 文件行数 = {len(tof)}  基金数 = {tof['fund_code'].nunique()}")
print(f"  TO_two_sided / 重算 比值 中位数 = {ratio.median():.4f}  在[0.99,1.01]占比 = {((ratio>0.99)&(ratio<1.01)).mean()*100:.1f}%")
print(f"  total_buy/total_sell 任一为 NaN 行数 = {tof[['total_buy','total_sell']].isna().any(axis=1).sum()}  (应为 0，曾被破坏)")

print("\nH. 持仓 stock_code 格式（连接键）")
hold = pd.read_csv(HOLD, encoding="utf-8-sig", nrows=200000)
leadzero = hold["stock_code"].astype(str).str.startswith("0").sum()
print(f"  持仓样本 stock_code 带前导零行数 = {leadzero}  (应为 0，否则连接失效)")

print("\nI. 覆盖速览（关键列）")
for c in ["quarter_return","future_return","excess_return","ff5_adj_return","avg_aum",
          "risk_asym","lsv","de","return_volatility","RG","ARG","ICI","industry_hhi","SDI","TO_two_sided","school"]:
    print(f"  {c:16s} {df[c].notna().mean()*100:5.1f}%  funds={df.loc[df[c].notna(),'fund_code'].nunique()}")

print("\n" + "="*70)
print("审计完成。")
