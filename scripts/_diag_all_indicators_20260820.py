# -*- coding: utf-8 -*-
"""_diag_all_indicators_20260820.py
全指标复核：M4 双向聚类 β/t + 组内 FE β/t + VIF + L5 隔离检验
输出 output/全指标复核_2026-08-20.csv + JSON 摘要
"""
import os, json, numpy as np, pandas as pd, warnings
import statsmodels.api as sm
import statsmodels.formula.api as smf
warnings.filterwarnings("ignore")

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PANEL = os.path.join(HERE, "指标计算流水线", "output", "主分析面板_重建_含TOwind.csv")
OUT = os.path.join(HERE, "output")
os.makedirs(OUT, exist_ok=True)

df = pd.read_csv(PANEL, dtype={"fund_code": str})
df["log_aum"] = np.log(df["avg_aum"].clip(lower=1e-9))
df["ff5_adj_return"] = pd.to_numeric(df["ff5_adj_return"], errors="coerce")
df["quarter"] = pd.to_numeric(df["quarter"], errors="coerce")

FF5  = ["ff5_MKT_excess","ff5_SMB","ff5_HML","ff5_RMW","ff5_CMA"]
CONT = ["log_aum"]
L1   = ["log_fund_age","mgr_total_tenure_v2"]
L2   = ["AS_improved","ICI","industry_hhi"]
L3   = ["SDI","TO_wind"]
L4   = ["ARG","return_volatility"]
L5   = ["de","lsv","risk_asym"]
BEHAV = L1 + L2 + L3 + L4 + L5   # 12 个行为指标（不含 CONT/FF5）
ALLRHS = CONT + FF5 + BEHAV

def winsor(s):
    s = s.astype(float); lo, hi = s.quantile(0.01), s.quantile(0.99)
    return s.clip(lo, hi)
for v in ALLRHS + ["ff5_adj_return"]:
    df[v+"_w"] = winsor(df[v])

rhs_w = [r+"_w" for r in ALLRHS]
d = df.dropna(subset=rhs_w + ["ff5_adj_return_w","fund_code","quarter"]).copy()
print(f"样本 N={len(d)} funds={d['fund_code'].nunique()}")

# ---------- 1. 加载 M4 双向聚类结果（v4 基准） ----------
bench = json.load(open(os.path.join(HERE, "_v4_benchmark.json"), encoding="utf-8"))
m4 = {v: bench["coefs"][v] for v in BEHAV}

# ---------- 2. 组内 FE（demean by fund，fund-clustered SE） ----------
# 对每个变量做 fund-demean，然后 OLS + fund cluster
d_fe = d.copy()
for v in rhs_w + ["ff5_adj_return_w"]:
    gm = d_fe.groupby("fund_code")[v].transform("mean")
    d_fe[v+"_dm"] = d_fe[v] - gm

rhs_dm = [r+"_w_dm" for r in ALLRHS]
X_fe = d_fe[rhs_dm].values
y_fe = d_fe["ff5_adj_return_w_dm"].values
X_fe = sm.add_constant(X_fe)
# fund cluster
fe_model = sm.OLS(y_fe, X_fe).fit(cov_type="cluster",
                                   cov_kwds={"groups": d_fe["fund_code"].values})
fe_coefs = {}
for j, name in enumerate(["const"] + ALLRHS):
    if name in BEHAV:
        idx = 1 + ALLRHS.index(name)
        fe_coefs[name] = {"beta": float(fe_model.params[idx]),
                          "t": float(fe_model.tvalues[idx]),
                          "p": float(fe_model.pvalues[idx])}

# ---------- 3. VIF（从已有 CSV 加载） ----------
vif_df = pd.read_csv(os.path.join(OUT, "M4_多重共线性_VIF_2026-08-16.csv"), encoding="utf-8-sig")
vif_map = {r["variable"]: r["VIF"] for _, r in vif_df.iterrows()}

# ---------- 4. L5 隔离检验：每个 L5 指标单独放入（去掉同层兄弟） ----------
# 规格：CONT + FF5 + L1 + L2 + L3 + L4 + [单个 L5] + C(year)
iso_results = {}
base_rhs = [r for r in ALLRHS if r not in L5]  # 去掉全部 L5
for v in L5:
    spec_rhs = base_rhs + [v]
    spec_w = [r+"_w" for r in spec_rhs]
    dd = d.dropna(subset=spec_w + ["ff5_adj_return_w","fund_code","quarter"]).copy()
    X = dd[spec_w].values
    X = sm.add_constant(X)
    # year dummies
    yr_dum = pd.get_dummies(dd["quarter"].astype(int), prefix="q", drop_first=True)
    X = np.column_stack([X, yr_dum.values])
    y = dd["ff5_adj_return_w"].values
    # two-way cluster
    groups = dd["fund_code"].astype(str).values + "_" + dd["quarter"].astype(str).values
    m = sm.OLS(y, X).fit(cov_type="cluster", cov_kwds={"groups": groups})
    idx = 1 + spec_rhs.index(v)
    iso_results[v] = {"beta": float(m.params[idx]), "t": float(m.tvalues[idx]),
                      "p": float(m.pvalues[idx]),
                      "N": len(dd), "funds": dd["fund_code"].nunique()}

# ---------- 5. 汇总表 ----------
rows = []
LAYER_MAP = {**{v:"L1" for v in L1}, **{v:"L2" for v in L2},
             **{v:"L3" for v in L3}, **{v:"L4" for v in L4}, **{v:"L5" for v in L5}}
CN_MAP = {"log_fund_age":"基金年龄","mgr_total_tenure_v2":"从业年限",
          "AS_improved":"改进主动份额","ICI":"行业偏离","industry_hhi":"行业集中度",
          "SDI":"风格漂移","TO_wind":"换手率",
          "ARG":"主动增益","return_volatility":"收益波动率",
          "de":"处置效应","lsv":"羊群效应","risk_asym":"风险不对称"}

def stars(p):
    if p is None or np.isnan(p): return ""
    if p < 0.01: return "***"
    if p < 0.05: return "**"
    if p < 0.10: return "*"
    return "n.s."

for v in BEHAV:
    m4c = m4[v]
    fec = fe_coefs[v]
    iso = iso_results.get(v, {})
    rows.append({
        "layer": LAYER_MAP[v], "var": v, "cn": CN_MAP.get(v, v),
        "M4_beta": round(m4c["beta"], 5), "M4_t2w": round(m4c["t2w"], 2),
        "M4_sig": stars(m4c["p2w"]),
        "FE_beta": round(fec["beta"], 5), "FE_t": round(fec["t"], 2),
        "FE_sig": stars(fec["p"]),
        "VIF": round(vif_map.get(v, float("nan")), 3),
        "iso_beta": round(iso.get("beta", float("nan")), 5) if iso else None,
        "iso_t": round(iso.get("t", float("nan")), 2) if iso else None,
        "iso_sig": stars(iso.get("p")) if iso else "",
        "iso_N": iso.get("N"), "iso_funds": iso.get("funds"),
        "sign_consistent": ("✓" if np.sign(m4c["beta"]) == np.sign(fec["beta"]) else "✗ 翻转") if fec["beta"] != 0 else "?",
    })

res = pd.DataFrame(rows)
res.to_csv(os.path.join(OUT, "全指标复核_2026-08-20.csv"), index=False, encoding="utf-8-sig")
print("\n=== 全指标复核表 ===")
print(res[["layer","var","cn","M4_beta","M4_t2w","M4_sig","FE_beta","FE_t","FE_sig","VIF","sign_consistent"]].to_string(index=False))

print("\n=== L5 隔离检验（去掉同层兄弟，单独放） ===")
for v in L5:
    r = iso_results[v]
    print(f"  {v:12s} β={r['beta']:.5f} t={r['t']:.2f} {stars(r['p'])}  N={r['N']} funds={r['funds']}")

# 摘要
summary = {
    "N": len(d), "funds": int(d["fund_code"].nunique()),
    "VIF_max_behavioral": round(max(vif_map[v] for v in BEHAV), 3),
    "VIF_max_var": max(BEHAV, key=lambda v: vif_map[v]),
    "sign_flips_M4_to_FE": [r["var"] for r in rows if r["sign_consistent"] == "✗ 翻转"],
    "M4_significant": [r["var"] for r in rows if r["M4_sig"] not in ("", "n.s.")],
    "FE_significant": [r["var"] for r in rows if r["FE_sig"] not in ("", "n.s.")],
    "both_significant": [r["var"] for r in rows if r["M4_sig"] not in ("","n.s.") and r["FE_sig"] not in ("","n.s.")],
    "lsv_iso": iso_results["lsv"],
    "de_iso": iso_results["de"],
    "ra_iso": iso_results["risk_asym"],
}
json.dump(summary, open(os.path.join(OUT, "全指标复核_摘要_2026-08-20.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)
print("\n=== 摘要 ===")
print(json.dumps(summary, ensure_ascii=False, indent=2))
