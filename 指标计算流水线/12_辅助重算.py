# -*- coding: utf-8 -*-
"""
12_辅助重算.py
为手稿 Option A 清理提供真实重算数字：
 (1) 截面 alpha-with-aum 回归的 bootstrap boot_t（RA/LSV/DE）；
 (2) §3.3 的 ICI↔HHI、SDI↔ARG 基金层相关性（诚实截面）；
 (3) §4.4.6 FF因子稳健性表（FF3/FF4/FF5 alpha 作 DV，修正后非负 LSV）。
所有数字直接来自当前面板 主分析面板_重建.csv。
"""
import pandas as pd, numpy as np, statsmodels.api as sm

PANEL = "指标计算流水线/output/主分析面板_重建.csv"
df = pd.read_csv(PANEL)
df["log_aum"] = np.log(df["avg_aum"].clip(lower=1))

# ---------- 基金层均值（截面口径，含规模 N=200）----------
g = df.groupby("fund_code")
fund = pd.DataFrame({
    "alpha5": g["ff5_adj_return"].first(),
    "alpha3": g["ff3_adj_return"].first(),
    "alpha4": g["ff4_adj_return"].first(),
    "excess_mean": g["excess_return"].mean(),
    "risk_asym": g["risk_asym"].mean(),
    "lsv": g["lsv"].mean(),
    "de": g["de"].mean(),
    "log_aum": g["avg_aum"].apply(lambda s: np.log(s.dropna().mean()) if s.dropna().mean() > 0 else np.nan),
    "log_fund_age": g["log_fund_age"].first(),
    "ICI": g["ICI"].mean(),
    "industry_hhi": g["industry_hhi"].mean(),
    "SDI": g["SDI"].mean(),
    "ARG": g["ARG"].mean(),
}).dropna(subset=["alpha5","risk_asym","lsv","de","log_aum","log_fund_age"])

ivs = ["risk_asym","lsv","de","log_aum","log_fund_age"]

def ols(data, dv):
    X = sm.add_constant(data[ivs]); m = sm.OLS(data[dv], X).fit(cov_type="HC1")
    return m

m0 = ols(fund, "alpha5")
print("==== 截面 alpha5-with-aum (N=%d) 点估计 ====" % len(fund))
for iv in ivs:
    print(f"  {iv:14s} coef={m0.params[iv]:+.4f}  t={m0.tvalues[iv]:+.2f}")

# ---------- (1) Bootstrap boot_t ----------
rng = np.random.default_rng(20260813)
B = 2000
boots = {iv: [] for iv in ivs}
idx = fund.index.values
for b in range(B):
    samp = rng.choice(idx, size=len(idx), replace=True)
    d = fund.loc[samp]
    if d[ivs+["alpha5"]].isna().any().any():
        continue
    try:
        mb = ols(d, "alpha5")
    except Exception:
        continue
    for iv in ivs:
        boots[iv].append(mb.tvalues[iv])
print("\n==== Bootstrap (B=%d) boot_t = mean|t| 与 显著占比 ====" % B)
for iv in ivs:
    arr = np.array(boots[iv])
    print(f"  {iv:14s} mean|t|={np.mean(np.abs(arr)):.2f}  frac|t|>1.96={np.mean(np.abs(arr)>1.96):.3f}  frac|t|>2.58={np.mean(np.abs(arr)>2.58):.3f}")

# ---------- (2) §3.3 相关性 ----------
sub = fund.dropna(subset=["ICI","industry_hhi","SDI","ARG"])
r_ici = sub["ICI"].corr(sub["industry_hhi"])
r_sdi = sub["SDI"].corr(sub["ARG"])
print("\n==== §3.3 基金层相关性 (N=%d) ====" % len(sub))
print(f"  ICI↔HHI  r = {r_ici:+.3f}")
print(f"  SDI↔ARG  r = {r_sdi:+.3f}")

# ---------- (3) FF 因子稳健性表 ----------
print("\n==== §4.4.6 FF因子稳健性表（N=%d，含规模）====" % len(fund))
for name, dv in [("FF3","alpha3"),("FF4","alpha4"),("FF5","alpha5")]:
    m = ols(fund, dv)
    print(f"  {name}: R2={m.rsquared:.3f} | RA coef={m.params['risk_asym']:+.4f}(t={m.tvalues['risk_asym']:+.2f}) "
          f"LSV coef={m.params['lsv']:+.4f}(t={m.tvalues['lsv']:+.2f}) DE coef={m.params['de']:+.4f}(t={m.tvalues['de']:+.2f})")
