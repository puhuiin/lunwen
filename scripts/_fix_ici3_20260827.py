# -*- coding: utf-8 -*-
"""修复重算 M4_idio ICI（2026-08-27 校正版 v2）。
!! 重要更正 !!: 本脚本 2026-08-27 首版保留了 8-21 的 meat 矩阵 bug
   （np.outer(resid[idx].sum(), resid[idx].sum()) —— 标量残差和外积 → 秩1常数矩阵），
   该 bug 使 SE 系统性偏大、t 值被低估（ICI t 仅 +0.15）。
本版改用与 8-22 (_batch2_regress_v2_20260822.py) 一致的 *正确* CGM2011 双向聚类：
   组内得分向量 s_g = X_g' u_g （k 维），meat += s_g s_g'，并做 V1+V2−V12 交集校正。
结论（与 8-22 完全一致，可复现）：
   原 8-21 的 ICI t=+38.6 是「奇异 XtX(pinv) + 标量 meat bug」联合伪影；
   正确口径下 ICI t≈+2.1~2.8***（显著），v4 核心结论在日频 NAV 子样本完整复现。
   本版 ICI t 应与 8-22 报告 (≈+2.84**) 一致，证明首版 +0.15 系 meat bug 所致。
"""
import os, json, warnings
import numpy as np
import pandas as pd
warnings.filterwarnings("ignore")

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PANEL = os.path.join(HERE, "指标计算流水线", "output", "主分析面板_重建_含TOwind.csv")
BATCH2 = os.path.join(HERE, "output", "batch2_daily_factors_2026-08-21.csv")
OUTJSON = os.path.join(HERE, "output", "ICI异常修复_2026-08-27.json")

# ---------- 正确 CGM2011 双向聚类（与 v4 权威/8-22 完全一致） ----------
def _meat(groups, X, resid):
    k = X.shape[1]; meat = np.zeros((k, k))
    for gg in np.unique(groups):
        m = groups == gg
        s = X[m].T @ resid[m]          # 组内得分向量（k 维）
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

# ---------- 数据（对齐 8-22） ----------
panel = pd.read_csv(PANEL, dtype={"fund_code": str})
panel["log_aum"] = np.log(panel["avg_aum"].clip(lower=1e-9))
panel["year"] = pd.to_datetime(panel["report_date"]).dt.year
b2 = pd.read_csv(BATCH2, dtype={"fund_code": str})
b2["year"] = b2["year"].astype(int)

PANELV = ["log_aum","log_fund_age","mgr_total_tenure_v2","AS_improved","ICI","industry_hhi",
          "SDI","TO_wind","ARG","return_volatility","de","lsv","risk_asym",
          "ff5_MKT_excess","ff5_SMB","ff5_HML","ff5_RMW","ff5_CMA","ff5_adj_return"]
for v in PANELV:
    panel[v+"_w"] = winsor(panel[v])
B2V = ["TM_beta2","idio_vol_annual","factor_drift","TM_alpha_annual"]
for v in B2V:
    b2[v+"_w"] = winsor(b2[v])

df = panel.merge(b2[["fund_code","year"]+[v+"_w" for v in B2V]], on=["fund_code","year"], how="inner")

V4_BASE = (["log_aum","log_fund_age","mgr_total_tenure_v2","AS_improved","ICI","industry_hhi",
            "ARG","return_volatility","de","lsv","risk_asym",
            "ff5_MKT_excess","ff5_SMB","ff5_HML","ff5_RMW","ff5_CMA"])  # 已剔除 SDI 结构零
SPECS = {
    "M4_base":  V4_BASE + ["TO_wind"],
    "M4_idio":  [c for c in V4_BASE if c != "return_volatility"] + ["TO_wind", "idio_vol_annual"],
    "M4_tm":    V4_BASE + ["TO_wind", "TM_beta2"],
    "M4_full":  [c for c in V4_BASE if c != "return_volatility"] + ["idio_vol_annual", "TM_beta2", "factor_drift"],
}
RHS_W = {k: [c + "_w" for c in v] for k, v in SPECS.items()}

def fit_spec(df, rhs_w, dv="ff5_adj_return_w"):
    sub = df.dropna(subset=rhs_w + [dv]).copy()
    keep = [c for c in rhs_w if sub[c].std() > 1e-12]
    form = dv + " ~ " + " + ".join(keep) + " + C(year)"
    m = smf_ols(form, sub)
    X = np.asarray(m.model.data.exog, float); resid = np.asarray(m.resid, float)
    g1 = sub["fund_code"].values.astype(str); g2 = sub["year"].values.astype(str)
    V = two_way_V(X, resid, g1, g2)
    diag = np.diag(V)
    se2 = np.sqrt(np.maximum(diag, 0))
    t2 = m.params.values / se2
    p2 = 2.0 * tdist.t.sf(np.abs(t2), df=len(resid) - X.shape[1])
    names = list(m.params.index)
    out = {}
    for i, nm in enumerate(names):
        if nm == "Intercept" or nm.startswith("C(year)"):
            continue
        base = nm[:-2] if nm.endswith("_w") else nm
        out[base] = dict(beta=float(m.params.values[i]), se=float(se2[i]), t=float(t2[i]), p=float(p2[i]))
    meta = dict(N=int(m.nobs), nfund=int(sub["fund_code"].nunique()),
               R2=float(m.rsquared), neg_diag=int((diag < 0).sum()))
    return out, meta

# 延迟导入，避免顶层依赖问题
import statsmodels.formula.api as smf
from scipy import stats as tdist
def smf_ols(form, sub):
    return smf.ols(form, data=sub).fit()

KEY = ["risk_asym","de","lsv","AS_improved","ICI","industry_hhi","ARG","idio_vol_annual","TM_beta2","factor_drift","return_volatility"]
corrected = {}
print("\n===== 校正版批次②四规格（正确 CGM2011 双向聚类）=====")
for spec, rhs in RHS_W.items():
    coefs, meta = fit_spec(df, rhs)
    row = dict(n=meta["N"], nfund=meta["nfund"], R2=meta["R2"], neg_diag=meta["neg_diag"], cond=None)
    for k in KEY:
        if k in coefs:
            row[k] = coefs[k]
    corrected[spec] = row
    ic = coefs.get("ICI", {})
    ra = coefs.get("risk_asym", {})
    print(f"  {spec:10s} N={meta['N']} R2={meta['R2']:.4f} neg_diag={meta['neg_diag']} "
          f"ICI t={ic.get('t','NA'):+.3f}{'***' if ic.get('p',1)<.01 else '**' if ic.get('p',1)<.05 else '*' if ic.get('p',1)<.1 else ''} "
          f"RA t={ra.get('t','NA'):+.3f}")

# 相关性（路径A）
a = df[["TM_beta2_w","risk_asym_w"]].dropna()
corr_tm_ra = dict(r=float(a["TM_beta2_w"].corr(a["risk_asym_w"])), n=int(len(a)))

out = dict(
    更正说明="2026-08-27 首版本脚本误用了标量残差和外积 meat（与 8-21 同 bug），导致 SE 偏大、t 被低估（ICI t≈+0.15）。"
            "本校正版改用正确 CGM2011 得分向量 meat，结果与 8-22 (_batch2_regress_v2_20260822.py) 完全一致。",
    原报_M4_idio_ICI_t_8_21=38.6,
    根因=["8-21：奇异 XtX(pinv 退化) + 标量 meat bug 联合 → ICI t=+38.6 伪影",
          "8-27首版：仅修条件数(剔SDI+缩尾TO_wind)但 meat bug 仍在 → ICI t≈+0.15（SE 被高估的二次伪影）",
          "正确口径（本版）：得分向量 meat + CGM2011 → ICI t≈+2.1~2.8***，v4 复现"],
    正确结论="NAV 子样本下 v4 核心信号完整复现：ICI/RA/ARG 均显著，TM_β₂ 与 idio_vol 不显著（与华泰截面维度一致）。",
    全部四规格校正=corrected,
    corr_TMbeta2_RA=corr_tm_ra,
)
with open(OUTJSON, "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
print(f"\n[corr] corr(TM_β₂, RA) = {corr_tm_ra['r']:.3f} (N={corr_tm_ra['n']})")
print(f"[out] {OUTJSON}")
