# -*- coding: utf-8 -*-
"""路径B（行为 Bootstrap，2026-08-22）：DE/RA 驱动的 alpha 差异是"实力"还是"运气"（截面运气检验）？

设计：基金层整簇 pairs bootstrap（CGM 口径下的标准做法）——
  以 v4 M4 全样本（N=2,264/348 基金）为基础，有放回重抽 348 个基金簇，
  每次在重抽面板上重估 M4（缩尾 + C(year) FE），记录 RA/DE/ICI/ARG/AS 的 β 与单维基金聚类 t。
  1,000 次重复 → 经验分布、95% CI、同号且显著的比例。
判读：CI 不含 0 且"同号显著"比例高 → 系数非少数基金（截面运气）驱动，是横截面上的稳定关系。
（组内/时序维度的运气已由 v4 的 WCB 与置换检验覆盖，本检验补截面维度。）
"""
import os, json, warnings, time
import numpy as np
import pandas as pd
import patsy
warnings.filterwarnings("ignore")

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PANEL = os.path.join(HERE, "指标计算流水线", "output", "主分析面板_重建_含TOwind.csv")
OUTJSON = os.path.join(HERE, "output", "batch4_bootstrap_2026-08-22.json")

RHS = ["log_aum","log_fund_age","mgr_total_tenure_v2","AS_improved","ICI","industry_hhi",
       "SDI","TO_wind","ARG","return_volatility","de","lsv","risk_asym",
       "ff5_MKT_excess","ff5_SMB","ff5_HML","ff5_RMW","ff5_CMA"]
KEY = ["risk_asym","de","ICI","ARG","AS_improved","lsv"]

panel = pd.read_csv(PANEL, dtype={"fund_code": str})
panel["log_aum"] = np.log(panel["avg_aum"].clip(lower=1e-9))
panel["year"] = pd.to_datetime(panel["report_date"]).dt.year
def winsor(s, lo=0.01, hi=0.99):
    s = s.astype(float); a, b = s.quantile(lo), s.quantile(hi)
    return s.clip(a, b)
for v in RHS + ["ff5_adj_return"]:
    panel[v+"_w"] = winsor(panel[v])

d = panel.dropna(subset=[c+"_w" for c in RHS] + ["ff5_adj_return_w"]).copy()
y_all, X_all = patsy.dmatrices("ff5_adj_return_w ~ " + " + ".join(c+"_w" for c in RHS) + " + C(year)",
                               data=d, return_type="dataframe")
Xn = np.asarray(X_all); yn = np.asarray(y_all).ravel()
names = list(X_all.columns)
key_idx = {k: names.index(k+"_w") for k in KEY}
funds = d["fund_code"].values
fund_codes, fund_inv = np.unique(funds, return_inverse=True)
G = len(fund_codes)
row_by_fund = [np.where(fund_inv == g)[0] for g in range(G)]
print(f"全样本 N={len(d)} 基金 {G}")

def cluster_t(Xs, ys, keyname):
    beta, *_ = np.linalg.lstsq(Xs, ys, rcond=None)
    resid = ys - Xs @ beta
    k = Xs.shape[1]
    XtX_inv = np.linalg.inv(Xs.T @ Xs)
    gs = np.unique(fund_inv_s)
    meat = np.zeros((k, k))
    for g in gs:
        m = fund_inv_s == g
        s = Xs[m].T @ resid[m]
        meat += np.outer(s, s)
    V = XtX_inv @ meat @ XtX_inv
    se = np.sqrt(max(V[key_idx[keyname], key_idx[keyname]], 0))
    return beta[key_idx[keyname]], (beta[key_idx[keyname]] / se if se > 0 else np.nan)

rng = np.random.default_rng(20260822)
B = 1000
boot = {k: {"beta": [], "t": []} for k in KEY}
t0 = time.time()
for b in range(B):
    gsample = rng.integers(0, G, size=G)
    rows = np.concatenate([row_by_fund[g] for g in gsample])
    Xs, ys = Xn[rows], yn[rows]
    fund_inv_s = fund_inv[rows]
    for k in KEY:
        try:
            bb, tt = cluster_t(Xs, ys, k)
            boot[k]["beta"].append(bb); boot[k]["t"].append(tt)
        except Exception:
            pass
    if (b + 1) % 200 == 0:
        print(f"  rep {b+1}/{B}  elapsed {time.time()-t0:.0f}s")

results = {"design": dict(B=B, G=G, N=int(len(d)), method="fund-cluster pairs bootstrap, v4 M4 spec (winsor + C(year) FE), seed 20260822")}
for k in KEY:
    b_ = np.array(boot[k]["beta"]); t_ = np.array(boot[k]["t"])
    same_sign_sig = np.mean(np.sign(t_) == np.sign(np.nanmean(b_)) ) # placeholder replaced below
    pos_sig = np.mean((t_ > 1.96)); neg_sig = np.mean((t_ < -1.96))
    results[k] = dict(
        beta_mean=float(np.mean(b_)), beta_p2p5=float(np.percentile(b_, 2.5)),
        beta_p97p5=float(np.percentile(b_, 97.5)), ci_excludes_zero=bool(np.percentile(b_, 2.5) * np.percentile(b_, 97.5) > 0),
        t_mean=float(np.nanmean(t_)), t_p2p5=float(np.nanpercentile(t_, 2.5)), t_p97p5=float(np.nanpercentile(t_, 97.5)),
        share_t_pos_sig=float(pos_sig), share_t_neg_sig=float(neg_sig))
    print(f"{k:12s} β_mean={np.mean(b_):+.5f}  CI95[{np.percentile(b_,2.5):+.5f}, {np.percentile(b_,97.5):+.5f}]  "
          f"CI排零={results[k]['ci_excludes_zero']}  t95[{np.nanpercentile(t_,2.5):+.2f},{np.nanpercentile(t_,97.5):+.2f}]  同向显著比例={max(pos_sig,neg_sig):.1%}")

with open(OUTJSON, "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)
print(f"[out] {OUTJSON}  total {time.time()-t0:.0f}s")
