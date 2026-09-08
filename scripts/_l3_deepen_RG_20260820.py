"""L3 深化：Return Gap(RG) 纳入 M4 扩展回归。
严格复用 _v4_benchmark_table.py 的规格与 CGM2011 双向聚类口径。
- DV = ff5_adj_return_w （1%/99% 缩尾）
- 基准 RHS = CONT+FF5+L1+L2+L3[SDI,TO_wind]+L4+L5
- 扩展 L3' = [SDI, TO_wind, RG]
- 另跑隔离模型：L3_only=[RG]，看 RG 独立信号
- 输出：RG 的 β/t2w/p2w/t1w，增量 R²，N，与 TO_wind/SDI 同模型对比
"""
import os, json, numpy as np, pandas as pd
import statsmodels.formula.api as smf
from scipy import stats as spstats

PANEL = "D:/Desktop/基金经理行为分析研究/指标计算流水线/output/主分析面板_重建_含TOwind.csv"
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
df = pd.read_csv(PANEL, dtype={"fund_code": str})
df["log_aum"] = np.log(df["avg_aum"].clip(lower=1e-9))
df["ff5_adj_return"] = pd.to_numeric(df["ff5_adj_return"], errors="coerce")

FF5  = ["ff5_MKT_excess","ff5_SMB","ff5_HML","ff5_RMW","ff5_CMA"]
CONT = ["log_aum"]
L1   = ["log_fund_age","mgr_total_tenure_v2"]
L2   = ["AS_improved","ICI","industry_hhi"]
L3   = ["SDI","TO_wind"]
L4   = ["ARG","return_volatility"]
L5   = ["de","lsv","risk_asym"]
ALLRHS = CONT + FF5 + L1 + L2 + L3 + L4 + L5

def winsor(s):
    s = s.astype(float); lo, hi = s.quantile(0.01), s.quantile(0.99)
    return s.clip(lo, hi)

for v in ALLRHS + ["RG"] + ["ff5_adj_return"]:
    if v in df.columns:
        df[v+"_w"] = winsor(pd.to_numeric(df[v], errors="coerce"))

# CGM2011 双向聚类
def _meat(groups, X, resid):
    k = X.shape[1]; meat = np.zeros((k, k))
    for gg in np.unique(groups):
        m = groups == gg; s = X[m].T @ resid[m]; meat += np.outer(s, s)
    return meat
def _oneway_V(X, resid, groups):
    XtX_inv = np.linalg.inv(X.T @ X)
    return XtX_inv @ _meat(groups, X, resid) @ XtX_inv
def two_way_V(X, resid, g1, g2):
    g12 = np.array([f"{a}|{b}" for a, b in zip(g1, g2)])
    return _oneway_V(X, resid, g1) + _oneway_V(X, resid, g2) - _oneway_V(X, resid, g12)

def fit(rhs_list):
    rhs_w = [r+"_w" for r in rhs_list]
    d = df.dropna(subset=rhs_w + ["ff5_adj_return_w"]).copy()
    form = "ff5_adj_return_w ~ " + " + ".join(rhs_w) + " + C(year)"
    m = smf.ols(form, data=d).fit(cov_type="cluster", cov_kwds={"groups": d["fund_code"]})
    X = np.asarray(m.model.data.exog, float); resid = np.asarray(m.resid, float)
    g1 = d["fund_code"].values.astype(str); g2 = d["year"].values.astype(str)
    V2 = two_way_V(X, resid, g1, g2)
    se2 = np.sqrt(np.maximum(np.diag(V2), 0)); t2 = m.params.values / se2
    p2 = 2.0 * spstats.t.sf(np.abs(t2), df=len(resid)-X.shape[1])
    se1 = np.asarray(m.bse.values, float); t1 = m.tvalues.values; p1 = m.pvalues.values
    names = list(m.params.index)
    out = {}
    for i, nm in enumerate(names):
        if nm == "Intercept" or nm.startswith("C(year)"): continue
        base = nm[:-2] if nm.endswith("_w") else nm
        out[base] = dict(beta=float(m.params.values[i]), se2w=float(se2[i]), t2w=float(t2[i]),
                         p2w=float(p2[i]), se1w=float(se1[i]), t1w=float(t1[i]), p1w=float(p1[i]))
    return m, d, out

def stars(p):
    return "***" if p<0.01 else "**" if p<0.05 else "*" if p<0.10 else "n.s."

# 1) 基准 M4（无 RG）
m0, d0, o0 = fit(ALLRHS)
# 2) 扩展 M4+RG
m1, d1, o1 = fit(ALLRHS + ["RG"])
# 3) 隔离模型 L3_only = [RG]
m2, d2, o2 = fit(CONT + FF5 + L1 + L2 + ["RG"] + L4 + L5)

print("="*78)
print("L3 深化 — Return Gap(RG) 扩展回归结果")
print("="*78)
print(f"\n[N] 基准M4 N={int(m0.nobs)} | M4+RG N={int(m1.nobs)} | 隔离RG N={int(m2.nobs)}")
print(f"[R²] 基准M4={m0.rsquared:.4f} | M4+RG={m1.rsquared:.4f} | 隔离RG={m2.rsquared:.4f}")
print(f"[ΔR² from adding RG] {m1.rsquared - m0.rsquared:+.4f}")

print("\n--- 扩展 M4+RG：L3 三指标同模型对比 ---")
for v in ["SDI","TO_wind","RG"]:
    r = o1[v]
    print(f"  {v:10s} β={r['beta']:+.5f}  t2w={r['t2w']:+.2f}  p2w={r['p2w']:.3f} {stars(r['p2w']):>4s}  | t1w={r['t1w']:+.2f}")

print("\n--- 隔离模型（L3 仅 RG，其余层全保留）---")
r = o2["RG"]
print(f"  RG  β={r['beta']:+.5f}  t2w={r['t2w']:+.2f}  p2w={r['p2w']:.3f} {stars(r['p2w']):>4s}  | t1w={r['t1w']:+.2f}")

print("\n--- 基准 M4 的 TO_wind/SDI（对照，无 RG）---")
for v in ["SDI","TO_wind"]:
    r = o0[v]
    print(f"  {v:10s} β={r['beta']:+.5f}  t2w={r['t2w']:+.2f}  p2w={r['p2w']:.3f} {stars(r['p2w']):>4s}")

# 输出 JSON 供后续写入报告
res = dict(
    n_base=int(m0.nobs), n_ext=int(m1.nobs), n_iso=int(m2.nobs),
    r2_base=float(m0.rsquared), r2_ext=float(m1.rsquared), r2_iso=float(m2.rsquared),
    delta_r2=float(m1.rsquared - m0.rsquared),
    ext=o1, iso=o2, base=o0,
)
with open(os.path.join(HERE, "output/L3_RG扩展回归_2026-08-20.json"), "w", encoding="utf-8") as f:
    json.dump(res, f, ensure_ascii=False, indent=2)
print("\n[已写出] output/L3_RG扩展回归_2026-08-20.json")
