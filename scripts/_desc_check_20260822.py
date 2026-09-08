# -*- coding: utf-8 -*-
"""重算表4-2描述性统计：分别给出原始与1%/99%缩尾两种口径，判定稿件数字属于哪一种。"""
import io, json
import numpy as np
import pandas as pd

CSV = r"d:\Desktop\基金经理行为分析研究\指标计算流水线\output\主分析面板_重建_含TOwind.csv"
df = pd.read_csv(CSV)
if "log_aum" not in df.columns:
    df["log_aum"] = np.log(df["avg_aum"].clip(lower=1e-9))

VARS = ["ff5_adj_return", "mgr_total_tenure_v2", "log_fund_age", "AS_improved", "ICI",
        "industry_hhi", "SDI", "TO_wind", "OCI_two_sided", "ARG", "return_volatility",
        "de", "lsv", "risk_asym", "log_aum"]

N = len(df)
rows = []
for v in VARS:
    if v not in df.columns:
        rows.append({"var": v, "note": "MISSING"})
        continue
    s = pd.to_numeric(df[v], errors="coerce")
    nn = int(s.notna().sum())
    lo, hi = s.quantile(0.01), s.quantile(0.99)
    w = s.clip(lo, hi)
    rows.append({
        "var": v, "n": nn, "cov_pct": round(100.0 * nn / N, 2),
        "raw":  [round(float(s.mean()), 4), round(float(s.std()), 4), round(float(s.min()), 4),
                 round(float(s.median()), 4), round(float(s.max()), 4)],
        "wins": [round(float(w.mean()), 4), round(float(w.std()), 4), round(float(w.min()), 4),
                 round(float(w.median()), 4), round(float(w.max()), 4)],
    })

print("面板 shape =", df.shape, " 总观测 =", N)
print("基金数 =", df["fund_code"].nunique() if "fund_code" in df.columns else "?")
print()
hdr = "%-22s %6s %7s | %-42s | %-42s" % ("变量", "N", "覆盖%", "原始 mean/sd/min/med/max", "缩尾 mean/sd/min/med/max")
print(hdr)
print("-" * len(hdr))
for r in rows:
    if r.get("note") == "MISSING":
        print("%-22s  MISSING" % r["var"]); continue
    f = lambda a: "/".join("%.4f" % x for x in a)
    print("%-22s %6d %7.2f | %-42s | %-42s" % (r["var"], r["n"], r["cov_pct"], f(r["raw"]), f(r["wins"])))

# L5 完整观测数
l5 = df[["de", "lsv", "risk_asym"]].apply(pd.to_numeric, errors="coerce")
print("\nL5三指标同时非缺失观测数 =", int(l5.dropna().shape[0]))
print("变量列数 =", df.shape[1])
io.open(r"d:\Desktop\基金经理行为分析研究\_desc_check_20260822.json", "w", encoding="utf-8").write(
    json.dumps({"n_obs": N, "n_cols": int(df.shape[1]), "rows": rows}, ensure_ascii=False, indent=1))
