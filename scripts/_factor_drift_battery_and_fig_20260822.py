# -*- coding: utf-8 -*-
"""factor_drift 稳健性电池 + 能力分解四设计系数图（2026-08-22）。
A) factor_drift 在 M4_full 中 t=+1.88*（边际）。跑多规格：单独+控制、稀疏、
   不同控制集、分时段——判断"边际信号"是稳健还是设定依赖。
B) 生成 §4.4.11 配图：RA/DE 在四种设计（截面/组内 × TM/HM）× 两能力维度的 t 值条形图。
"""
import os, json, warnings
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from scipy import stats as spstats
warnings.filterwarnings("ignore")
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import rcParams
rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Noto Sans CJK SC"]
rcParams["axes.unicode_minus"] = False

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PANEL = os.path.join(HERE, "指标计算流水线", "output", "主分析面板_重建_含TOwind.csv")
B2 = os.path.join(HERE, "output", "batch2_daily_factors_2026-08-21.csv")
OUTJ = os.path.join(HERE, "output", "factor_drift_battery_2026-08-22.json")
OUTFIG = os.path.join(HERE, "figures", "能力分解_四设计系数图_2026-08-22.png")

def winsor(s, lo=0.01, hi=0.99):
    s = s.astype(float); a, b = s.quantile(lo), s.quantile(hi)
    return s.clip(a, b)
def _meat(groups, X, resid):
    k = X.shape[1]; meat = np.zeros((k, k))
    for gg in np.unique(groups):
        m = groups == gg
        s = X[m].T @ resid[m]; meat += np.outer(s, s)
    return meat
def two_way_V(X, resid, g1, g2):
    def one(g):
        XtX_inv = np.linalg.inv(X.T @ X)
        return XtX_inv @ _meat(g, X, resid) @ XtX_inv
    g12 = np.array([f"{a}|{b}" for a, b in zip(g1, g2)])
    return one(g1) + one(g2) - one(g12)

panel = pd.read_csv(PANEL, dtype={"fund_code": str})
panel["fund_code"] = panel["fund_code"].str.strip()
panel["year"] = pd.to_datetime(panel["report_date"]).dt.year
panel["log_aum"] = np.log(panel["avg_aum"].clip(lower=1e-9))
b2 = pd.read_csv(B2); b2["fund_code"] = b2["fund_code"].astype(int).astype(str); b2["year"] = b2["year"].astype(int)
for c in ["TM_beta2", "idio_vol_annual", "factor_drift"]:
    b2[c+"_w"] = winsor(b2[c])
PANELV = ["log_aum","log_fund_age","mgr_total_tenure_v2","AS_improved","ICI","industry_hhi",
          "TO_wind","ARG","return_volatility","de","lsv","risk_asym",
          "ff5_MKT_excess","ff5_SMB","ff5_HML","ff5_RMW","ff5_CMA","ff5_adj_return"]
for v in PANELV:
    panel[v+"_w"] = winsor(panel[v])
df = panel.merge(b2[["fund_code","year","TM_beta2_w","idio_vol_annual_w","factor_drift_w"]],
                 on=["fund_code","year"], how="inner")
sub = df[df["factor_drift_w"].notna()].copy()
print(f"factor_drift 可用样本 {len(sub)} / {sub['fund_code'].nunique()} 基金")

def fit(d, rhs):
    d2 = d.dropna(subset=rhs + ["ff5_adj_return_w"]).copy()
    keep = [c for c in rhs if d2[c].std() > 1e-12]
    m = smf.ols("ff5_adj_return_w ~ " + " + ".join(keep) + " + C(year)", data=d2).fit()
    X = np.asarray(m.model.data.exog, float); resid = np.asarray(m.resid, float)
    V = two_way_V(X, resid, d2["fund_code"].values.astype(str), d2["year"].values.astype(str))
    se = np.sqrt(np.maximum(np.diag(V), 0)); t2 = m.params.values / se
    names = list(m.params.index)
    i = names.index("factor_drift_w")
    p = 2.0 * spstats.t.sf(abs(t2[i]), df=len(resid) - X.shape[1])
    return dict(beta=float(m.params.values[i]), t=float(t2[i]), p=float(p), N=int(m.nobs),
                stars="" if p > .10 else "*" if p > .05 else "**" if p > .01 else "***")

base = [c+"_w" for c in ["log_aum","log_fund_age","mgr_total_tenure_v2","AS_improved","ICI",
                          "industry_hhi","ARG","return_volatility","de","lsv","risk_asym",
                          "ff5_MKT_excess","ff5_SMB","ff5_HML","ff5_RMW","ff5_CMA"]]
specs = {
    "S1 单独+规模": ["log_aum_w", "factor_drift_w"],
    "S2 稀疏(行为4)": ["log_aum_w","risk_asym_w","de_w","lsv_w","factor_drift_w"],
    "S3 M4_base+fd": base + ["factor_drift_w"],
    "S4 M4_full复刻": [c for c in base if c != "return_volatility_w"] + ["idio_vol_annual_w","TM_beta2_w","factor_drift_w"],
    "S5 full+return_vol": base + ["idio_vol_annual_w","TM_beta2_w","factor_drift_w"],
    "S6 2017-2021": None, "S7 2022-2025": None,
}
results = {}
for name, rhs in specs.items():
    if rhs is None:
        yr0, yr1 = (2017, 2021) if "2017" in name else (2022, 2025)
        results[name] = fit(sub[(sub["year"] >= yr0) & (sub["year"] <= yr1)], specs["S4 M4_full复刻"])
    else:
        results[name] = fit(sub, rhs)
    r = results[name]
    print(f"  {name:16s} β={r['beta']:+.4f}  t={r['t']:+.2f}  {r['stars']}  N={r['N']}")
with open(OUTJ, "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)
print(f"[out] {OUTJ}")

# ============ B) 四设计系数图 ============
w = json.load(open(os.path.join(HERE, "output", "batch3_within_decomposition_2026-08-22.json"), encoding="utf-8"))
c = json.load(open(os.path.join(HERE, "output", "batch3_alpha_decomposition_2026-08-22.json"), encoding="utf-8"))
hj = json.load(open(os.path.join(HERE, "output", "batch3_hm_decomposition_2026-08-22.json"), encoding="utf-8"))
def T(blob, key, var): return blob[key]["coefs"][var]["t"]
bars = {
    "RiskAsym": {"选股α": [T(c,"DV1_选股α","risk_asym"), T(hj,"DV1_HM选股α","risk_asym"),
                            T(w,"组内 DV1_TM选股α","risk_asym_w"), T(w,"组内 DV2_HM选股α","risk_asym_w")],
                 "择时贡献": [T(c,"DV2_择时贡献","risk_asym"), T(hj,"DV2_HM择时贡献","risk_asym"),
                              T(w,"组内 DV3_TM择时","risk_asym_w"), T(w,"组内 DV4_HM择时","risk_asym_w")]},
    "DE": {"选股α": [T(c,"DV1_选股α","de"), T(hj,"DV1_HM选股α","de"),
                      T(w,"组内 DV1_TM选股α","de_w"), T(w,"组内 DV2_HM选股α","de_w")],
           "择时贡献": [T(c,"DV2_择时贡献","de"), T(hj,"DV2_HM择时贡献","de"),
                        T(w,"组内 DV3_TM择时","de_w"), T(w,"组内 DV4_HM择时","de_w")]},
}
fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.6), sharey=True)
labels = ["截面 TM", "截面 HM", "组内 TM", "组内 HM"]; x = np.arange(4)
cols = {"选股α": "#138089", "择时贡献": "#C9A227"}
for ax, name in zip(axes, ["RiskAsym", "DE"]):
    for i, (dim, vals) in enumerate(bars[name].items()):
        off = (i - 0.5) * 0.36
        b = ax.bar(x + off, vals, width=0.34, color=cols[dim], label=dim)
        for xi, v in zip(x + off, vals):
            ax.text(xi, v + (0.25 if v >= 0 else -0.55), f"{v:+.2f}", ha="center", fontsize=8.5)
    ax.axhline(0, color="#444", lw=0.8)
    ax.axhline(1.96, color="#999", lw=0.7, ls="--"); ax.axhline(-1.96, color="#999", lw=0.7, ls="--")
    ax.set_xticks(x); ax.set_xticklabels(labels, fontsize=10)
    ax.set_title(f"{name}：预测力的能力维度", fontsize=13, fontweight="bold")
    ax.spines[["top", "right"]].set_visible(False)
axes[0].set_ylabel("t 值（虚线=±1.96）", fontsize=10.5)
axes[0].legend(frameon=False, fontsize=10, loc="upper right")
fig.suptitle("能力分解：RA 与 DE 的预测力集中于选股α（四种设计一致）", fontsize=14, fontweight="bold", y=1.00)
fig.text(0.99, 0.01, "截面 N=1,351/170；组内（基金+年份双FE）N=828/174；CGM/基金聚类 t", ha="right", fontsize=8, color="#666")
fig.tight_layout(rect=(0, 0.03, 1, 0.96))
os.makedirs(os.path.dirname(OUTFIG), exist_ok=True)
fig.savefig(OUTFIG, dpi=160, bbox_inches="tight")
print(f"[out] {OUTFIG}")
