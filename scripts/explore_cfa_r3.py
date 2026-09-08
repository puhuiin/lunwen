import pandas as pd, numpy as np, os, glob

base = "D:/Desktop/基金经理行为分析研究/"
panel_p = base + "指标计算流水线/output/主分析面板_重建.csv"
panel_eg = base + "指标计算流水线/output/主分析面板_含EGARCH.csv"

# 1) 主面板列 + CFA 分布
df = pd.read_csv(panel_p)
print("=== 主面板_重建 列 ===")
print(list(df.columns))
print("shape", df.shape)
for c in df.columns:
    if "cfa" in c.lower() or "cert" in c.lower() or "证书" in c:
        print("\n--- CFA-like col:", c, "---")
        print("non-null:", df[c].notna().sum(), "/", len(df))
        print(df[c].value_counts(dropna=False).head(10))

# 2) EGARCH 面板 gamma 列
if os.path.exists(panel_eg):
    dfe = pd.read_csv(panel_eg)
    print("\n=== 含EGARCH 面板 列(含gamma) ===")
    gc = [c for c in dfe.columns if "gamma" in c.lower() or "egarch" in c.lower() or "asym" in c.lower()]
    print(gc)
    for c in gc:
        s = dfe[c].dropna()
        print(f"{c}: n={len(s)} min={s.min():.3f} max={s.max():.3f} mean={s.mean():.4f} "
              f"neg_frac={(s<0).mean():.3f} |g|>10={(s.abs()>10).sum()}")

# 3) 前向相关列
print("\n=== 前向/预测相关列 ===")
fc = [c for c in df.columns if "fut" in c.lower() or "future" in c.lower() or "forward" in c.lower()
      or "risk_asym" in c.lower() or "lsv" in c.lower() or "de" in c.lower() and "de_" in c.lower()]
print(fc)
for c in ["risk_asym","lsv","de","de_improved"]:
    if c in df.columns:
        s=df[c].dropna()
        print(c, "n", len(s), "mean", round(s.mean(),4), "nonnull_funds", df.loc[df[c].notna(),"fund_code"].nunique())

# 查找 fut 列名
fut_cols=[c for c in df.columns if c.lower().startswith("fut")]
print("fut cols:", fut_cols)
