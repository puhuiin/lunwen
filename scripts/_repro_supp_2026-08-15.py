# -*- coding: utf-8 -*-
"""补充计算：诚实 M4 下的置换检验(§4.4.1)与正确 Oster δ(§4.6)。"""
import pandas as pd, numpy as np, statsmodels.formula.api as smf, json

PANEL = "指标计算流水线/output/主分析面板_重建_含TOwind.csv"
df = pd.read_csv(PANEL)
df["ff5_adj_return"] = pd.to_numeric(df["ff5_adj_return"], errors="coerce")

# 派生
df["log_aum"] = np.log(df["avg_aum"].clip(lower=1e-9))
FF5 = ["ff5_MKT_excess","ff5_SMB","ff5_HML","ff5_RMW","ff5_CMA"]
CONT = ["log_aum","log_fund_age","mgr_total_tenure_v2"]
L1 = ["AS_improved","ICI","industry_hhi"]
L2 = ["SDI","TO_wind"]
L3 = ["ARG","return_volatility"]
L4 = ["de","lsv","risk_asym"]
RHS = CONT + FF5 + L1 + L2 + L3 + L4
need = RHS + ["ff5_adj_return"]
sub = df.dropna(subset=need).copy()
print("M4 honest N=", len(sub), "funds", sub["fund_code"].nunique())

# winsor —— 使用全面板分位数（与主重估脚本一致）
wq = {}
for v in RHS + ["ff5_adj_return"]:
    lo, hi = df[v].quantile(0.01), df[v].quantile(0.99)
    wq[v] = (lo, hi)
for v in RHS + ["ff5_adj_return"]:
    sub[v+"_w"] = sub[v].astype(float).clip(wq[v][0], wq[v][1])

form = "ff5_adj_return_w ~ " + " + ".join([r+"_w" for r in RHS]) + " + C(year)"
m = smf.ols(form, data=sub).fit(cov_type="cluster", cov_kwds={"groups": sub["fund_code"]})
true_t = {v: m.tvalues[v+"_w"] for v in L4}
true_b = {v: m.params[v+"_w"] for v in L4}
print("真实 t:", {k: round(v,2) for k,v in true_t.items()})

# ---- 置换检验：跨全体观测打乱 L5 三指标（破坏截面与时序对齐）----
rng = np.random.default_rng(20260815)
perm_t = {v: [] for v in L4}
N_PERM = 500
data = sub.copy()
for _ in range(N_PERM):
    d = data.copy()
    for v in L4:
        d[v+"_w"] = rng.permutation(d[v+"_w"].values)   # 全样本随机置换
    try:
        mm = smf.ols(form, data=d).fit(cov_type="cluster", cov_kwds={"groups": d["fund_code"]})
        for v in L4:
            perm_t[v].append(mm.tvalues[v+"_w"])
    except Exception:
        pass

twop = {}
for v in L4:
    arr = np.array(perm_t[v])
    tt = abs(true_t[v])
    p = 2.0 * min((arr >= tt).mean(), (arr <= -tt).mean())
    twop[v] = round(max(p, 1.0/N_PERM), 4)
print("置换双尾 p:", twop)

# ---- 正确 Oster δ ----
def oster(X):
    # 短回归：仅含 X + 最小控制(FF5+规模/年龄/任期)；长回归：再加全部 L1-L4 与另两 L5
    others = [c for c in (L1+L2+L3+L4) if c != X]
    rhs_short = CONT + FF5          # 含 X
    rhs_long  = CONT + FF5 + others # 含 X
    mf = smf.ols("ff5_adj_return_w ~ " + X+"_w" + " + " + " + ".join([r+"_w" for r in rhs_long]) + " + C(year)",
                 data=sub).fit(cov_type="cluster", cov_kwds={"groups": sub["fund_code"]})
    ms = smf.ols("ff5_adj_return_w ~ " + X+"_w" + " + " + " + ".join([r+"_w" for r in rhs_short]) + " + C(year)",
                 data=sub).fit(cov_type="cluster", cov_kwds={"groups": sub["fund_code"]})
    b_long = mf.params[X+"_w"]; b_short = ms.params[X+"_w"]
    R_long = mf.rsquared; Rmax = min(1.0, 1.3*R_long)
    # Oster δ = (b_short - b_long*(Rmax/R_long)) / (b_long*(Rmax-R_long)/R_long)
    delta = (b_short - b_long*(Rmax/R_long)) / (b_long*(Rmax-R_long)/R_long)
    return dict(b_short=round(b_short,4), b_long=round(b_long,4),
                R_long=round(R_long,3), Rmax=round(Rmax,3), delta=round(delta,2))

G = {v: oster(v) for v in L4}
print("Oster:", G)

out = dict(true_t={k: round(v,2) for k,v in true_t.items()},
           true_b={k: round(v,5) for k,v in true_b.items()},
           perm_p=twop, oster=G, M4_N=len(sub), M4_funds=sub["fund_code"].nunique())
json.dump(out, open("_repro_supp_2026-08-15.json","w"), ensure_ascii=False, indent=1)
print("DONE")
