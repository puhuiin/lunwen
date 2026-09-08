import pandas as pd, numpy as np

p = pd.read_csv("指标计算流水线/output/主分析面板_重建_含TOwind.csv")

comps = ["risk_asym","de","oc_conf","ICI","ISDI","ARG","timing",
         "mppm8_lag","sortino8_lag","sharpe8_lag","SDI","lsv"]

print("=== 各成分：观测层 vs 基金层(时序均值) 的零值/缺失比例 ===")
print(f"{'指标':14s} {'观测n':>7s} {'零%':>7s} {'基金n':>6s} {'基金层零%':>9s} {'基金层缺失%':>10s}")
for c in comps:
    if c not in p.columns:
        print(f"{c:14s} (列不存在)")
        continue
    s = p[c].dropna()
    fm = p.groupby("fund_code")[c].mean()
    fm_nonnull = fm.dropna()
    z_obs = (s == 0).mean() * 100 if len(s) else np.nan
    z_fund = (fm_nonnull == 0).mean() * 100 if len(fm_nonnull) else np.nan
    miss_fund = fm.isna().mean() * 100
    print(f"{c:14s} {len(s):7d} {z_obs:7.2f} {len(fm_nonnull):6d} {z_fund:9.2f} {miss_fund:10.2f}")

print("\n=== 基金层零值比例 >20% 的指标（复合得分受影响）===")
for c in comps:
    if c not in p.columns:
        continue
    fm = p.groupby("fund_code")[c].mean().dropna()
    if len(fm) == 0:
        continue
    z = (fm == 0).mean()
    if z > 0.20:
        print(f"  {c}: 零值 {z*100:.1f}%  (n={len(fm)})")

print("\n=== oc_conf 构造核查（指示函数是否造成零堆积）===")
if "oc_conf" in p.columns:
    s = p["oc_conf"].dropna()
    print("  观测层: n=%d, 零=%.1f%%, 中位数=%.4f" % (len(s), (s==0).mean()*100, s.median()))
    print("  范围: %.2f ~ %.2f, 均值 %.4f, sd %.4f" % (s.min(), s.max(), s.mean(), s.std()))

print("\n=== 缩尾后(1%/99%) 基金层 SDI 描述 ===")
if "SDI" in p.columns:
    fm = p.groupby("fund_code")["SDI"].mean().dropna()
    lo, hi = fm.quantile([0.01, 0.99])
    fw = fm.clip(lo, hi)
    print("  基金层 SDI: n=%d mean=%.4f sd=%.4f 零值=%.1f%%" % (len(fw), fw.mean(), fw.std(), (fw==0).mean()*100))
