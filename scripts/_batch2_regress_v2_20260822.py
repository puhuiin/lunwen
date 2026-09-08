# -*- coding: utf-8 -*-
"""批次②回归修正版（2026-08-22）：
修复 8-21 版 _batch2_regress_20260821.py 的三处方法学缺陷：
  (1) 双向聚类 meat 用了"组内残差和(标量)外积"，应为组内得分向量 X_g'u_g —— 旧版全部 t 值作废
      （典型症状：M4_idio_substitute 中 ICI t=+38.6）
  (2) 未做 CGM2011 交集校正（V1+V2-V12）
  (3) 未缩尾、未剔除零方差列（NAV 子样本 SDI 为结构零 std=0）
本版完全对齐 v4 权威口径（_repro_M4_authoritative_v4_2026-08-16.py）：
  全变量 1%/99% 缩尾（界取自全样本） + C(year) FE + CGM2011 双向聚类(fund×year)。
规格：
  M4_base   : v4 18 RHS − SDI（结构零剔除，披露）
  M4_idio   : return_volatility → idio_vol_annual
  M4_tm     : + TM_beta2（SDI 槽位）
  M4_full   : idio_vol_annual + TM_beta2 + factor_drift 同时入模（− return_volatility/SDI/TO_wind）
附加：corr(TM_β₂,RA)、corr(idio_vol,return_volatility)、corr(factor_drift,SDI)（全样本可变部分）。
"""
import os, json, warnings
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from scipy import stats as spstats
warnings.filterwarnings("ignore")

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PANEL = os.path.join(HERE, "指标计算流水线", "output", "主分析面板_重建_含TOwind.csv")
BATCH2 = os.path.join(HERE, "output", "batch2_daily_factors_2026-08-21.csv")
OUTJSON = os.path.join(HERE, "output", "batch2_regressions_v2_2026-08-22.json")
OUTCSV = os.path.join(HERE, "output", "batch2_regression_table_v2_2026-08-22.csv")

# ---------- CGM2011 双向聚类（与 v4 权威/批次① 完全一致） ----------
def _meat(groups, X, resid):
    k = X.shape[1]; meat = np.zeros((k, k))
    for gg in np.unique(groups):
        m = groups == gg
        s = X[m].T @ resid[m]          # 组内得分向量（k 维），旧版误用标量残差和
        meat += np.outer(s, s)
    return meat

def _oneway_V(X, resid, groups):
    XtX_inv = np.linalg.inv(X.T @ X)
    return XtX_inv @ _meat(groups, X, resid) @ XtX_inv

def two_way_V(X, resid, g1, g2):
    g12 = np.array([f"{a}|{b}" for a, b in zip(g1, g2)])
    return _oneway_V(X, resid, g1) + _oneway_V(X, resid, g2) - _oneway_V(X, resid, g12)

def winsor(s, lo=0.01, hi=0.99):
    s = s.astype(float); a, b = s.quantile(lo), s.quantile(hi)
    return s.clip(a, b)

# ---------- 数据 ----------
panel = pd.read_csv(PANEL, dtype={"fund_code": str})
panel["log_aum"] = np.log(panel["avg_aum"].clip(lower=1e-9))
panel["year"] = pd.to_datetime(panel["report_date"]).dt.year

b2 = pd.read_csv(BATCH2, dtype={"fund_code": str})
b2["year"] = b2["year"].astype(int)

# 缩尾界取自各自全样本（panel 9,974 行；batch2 1,182 基金-年），与 v4 口径一致
PANELV = ["log_aum","log_fund_age","mgr_total_tenure_v2","AS_improved","ICI","industry_hhi",
          "SDI","TO_wind","ARG","return_volatility","de","lsv","risk_asym",
          "ff5_MKT_excess","ff5_SMB","ff5_HML","ff5_RMW","ff5_CMA","ff5_adj_return"]
for v in PANELV:
    panel[v+"_w"] = winsor(panel[v])
B2V = ["TM_beta2","idio_vol_annual","factor_drift","TM_alpha_annual"]
for v in B2V:
    b2[v+"_w"] = winsor(b2[v])

df = panel.merge(b2[["fund_code","year"]+[v+"_w" for v in B2V]], on=["fund_code","year"], how="inner")
print(f"merge 后 fund-year 行 {len(df):,} / {df['fund_code'].nunique()} 基金")

# NAV 子样本内 SDI 结构零核查（披露依据）
sdi_sub = df["SDI_w"]
print(f"SDI_w 子样本非缺失 {sdi_sub.notna().sum()}，std={sdi_sub.std():.3g} → 结构零，全规格剔除")

V4_BASE = (["log_aum","log_fund_age","mgr_total_tenure_v2",
            "AS_improved","ICI","industry_hhi",
            "ARG","return_volatility",
            "de","lsv","risk_asym",
            "ff5_MKT_excess","ff5_SMB","ff5_HML","ff5_RMW","ff5_CMA"])  # 已剔除 SDI、TO_wind 留给 full 规格替换
SPECS = {
    "M4_base":  V4_BASE + ["TO_wind"],
    "M4_idio":  [c for c in V4_BASE if c != "return_volatility"] + ["TO_wind", "idio_vol_annual"],
    "M4_tm":    V4_BASE + ["TO_wind", "TM_beta2"],
    "M4_full":  [c for c in V4_BASE if c != "return_volatility"] + ["idio_vol_annual", "TM_beta2", "factor_drift"],
}
RHS_W = {k: [c + "_w" for c in v] for k, v in SPECS.items()}

def fit_spec(df, rhs_w, dv="ff5_adj_return_w"):
    sub = df.dropna(subset=rhs_w + [dv]).copy()
    # 防御性剔除零方差列
    keep = [c for c in rhs_w if sub[c].std() > 1e-12]
    dropped = [c for c in rhs_w if c not in keep]
    form = dv + " ~ " + " + ".join(keep) + " + C(year)"
    m = smf.ols(form, data=sub).fit()
    X = np.asarray(m.model.data.exog, float); resid = np.asarray(m.resid, float)
    g1 = sub["fund_code"].values.astype(str); g2 = sub["year"].values.astype(str)
    V = two_way_V(X, resid, g1, g2)
    diag = np.diag(V)
    se2 = np.sqrt(np.maximum(diag, 0))
    t2 = m.params.values / se2
    p2 = 2.0 * spstats.t.sf(np.abs(t2), df=len(resid) - X.shape[1])
    names = list(m.params.index)
    rows = []
    for i, nm in enumerate(names):
        if nm == "Intercept" or nm.startswith("C(year)"):
            continue
        base = nm[:-2] if nm.endswith("_w") else nm
        rows.append(dict(var=base, beta=float(m.params.values[i]), se2w=float(se2[i]),
                         t2w=float(t2[i]), p2w=float(p2[i]),
                         stars=("" if p2[i] > .10 else "*" if p2[i] > .05 else "**" if p2[i] > .01 else "***")))
    meta = dict(N=int(m.nobs), nfund=int(sub["fund_code"].nunique()),
                r2=float(m.rsquared), r2_adj=float(m.rsquared_adj),
                n_neg_diag=int((diag < 0).sum()), dropped_cols=dropped)
    return rows, meta

results = {}
for spec, rhs in RHS_W.items():
    rows, meta = fit_spec(df, rhs)
    results[spec] = dict(meta=meta, coefs=rows)
    print(f"\n[{spec}]  N={meta['N']}  funds={meta['nfund']}  R²={meta['r2']:.4f}  neg_diag={meta['n_neg_diag']}  dropped={meta['dropped_cols']}")
    for r in rows:
        if r["var"] in ("AS_improved","ICI","industry_hhi","TO_wind","ARG","return_volatility",
                        "de","lsv","risk_asym","idio_vol_annual","TM_beta2","factor_drift"):
            print(f"   {r['var']:18s} β={r['beta']:+.5f}  se={r['se2w']:.5f}  t2w={r['t2w']:+.2f}  {r['stars']}")

# ---------- 相关性（路径A + 口径互证） ----------
corr_out = {}
a = df[["TM_beta2_w","risk_asym_w"]].dropna()
corr_out["corr_TMbeta2_RA"] = dict(r=float(a["TM_beta2_w"].corr(a["risk_asym_w"])), n=int(len(a)))
b_ = df[["idio_vol_annual_w","return_volatility_w"]].dropna()
corr_out["corr_idio_vol_retvol"] = dict(r=float(b_["idio_vol_annual_w"].corr(b_["return_volatility_w"])), n=int(len(b_)))
c_ = df[["factor_drift_w","SDI_w"]].dropna()
corr_out["corr_factor_drift_SDI_navsubset"] = dict(r=(float(c_["factor_drift_w"].corr(c_["SDI_w"])) if len(c_) > 2 and c_["SDI_w"].std() > 0 else None), n=int(len(c_)))
# factor_drift vs SDI 需在 SDI 有变异的更大样本上做：用全 panel 的 SDI（不限 NAV）按 fund-year 聚合后对齐
panel_fy = panel.groupby(["fund_code","year"]).agg(SDI_fy=("SDI","mean")).reset_index()
b2_fy = b2[["fund_code","year","factor_drift_w"]]
xz = panel_fy.merge(b2_fy, on=["fund_code","year"], how="inner").dropna()
if len(xz) > 2 and xz["SDI_fy"].std() > 0:
    corr_out["corr_factor_drift_SDI_fullsample"] = dict(r=float(xz["factor_drift_w"].corr(xz["SDI_fy"])), n=int(len(xz)))
else:
    corr_out["corr_factor_drift_SDI_fullsample"] = dict(r=None, n=int(len(xz)))
results["correlations"] = corr_out
print("\n=== 相关性 ===")
for k, v in corr_out.items():
    print(f"  {k}: {v}")

with open(OUTJSON, "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)
rows_out = []
for spec, blob in results.items():
    if spec == "correlations":
        continue
    for r in blob["coefs"]:
        rows_out.append(dict(spec=spec, **r, **blob["meta"]))
pd.DataFrame(rows_out).to_csv(OUTCSV, index=False, encoding="utf-8-sig")
print(f"\n[out] {OUTJSON}\n[out] {OUTCSV}")
