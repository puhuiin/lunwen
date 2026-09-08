# -*- coding: utf-8 -*-
"""定位 NAV 子集 RHS 的奇异性来源，并给出稳健修复后的 ICI t。"""
import json, numpy as np, pandas as pd

PROJ = "D:/Desktop/基金经理行为分析研究"
panel = pd.read_csv(f"{PROJ}/指标计算流水线/output/主分析面板_重建_含TOwind.csv")
batch2 = pd.read_csv(f"{PROJ}/output/batch2_daily_factors_2026-08-21.csv")
panel["log_aum"] = np.log(panel["avg_aum"].astype(float))
batch2["year"] = batch2["year"].astype(int); panel["year"] = panel["year"].astype(int)
panel["fund_code"] = panel["fund_code"].astype(str); batch2["fund_code"] = batch2["fund_code"].astype(str)
df_all = panel.merge(batch2[["fund_code","year","TM_beta2","idio_vol_annual","factor_drift"]],
                     on=["fund_code","year"], how="left")
df_nav = df_all[df_all["TM_beta2"].notna()].copy()
df_nav["SDI"] = df_nav["SDI"].fillna(0)
df_nav["TO_wind"] = df_nav["TO_wind"].fillna(df_nav["TO_wind"].median())
for c in ["ff5_MKT_excess","ff5_SMB","ff5_HML","ff5_RMW","ff5_CMA"]:
    df_nav[c] = df_nav[c].fillna(0)

V4 = ["log_aum","log_fund_age","mgr_total_tenure_v2","AS_improved","ICI","industry_hhi",
      "SDI","TO_wind","ARG","return_volatility","de","lsv","risk_asym",
      "ff5_MKT_excess","ff5_SMB","ff5_HML","ff5_RMW","ff5_CMA"]

s = df_nav[V4+["ff5_adj_return"]].dropna()
print("NAV 有效观测 N =", len(s))
# 1) 零方差列
zero_var = [c for c in V4 if s[c].std() < 1e-12]
print("零方差(常量)列:", zero_var)
# 2) 高相关对
C = s[V4].corr().abs()
pairs = []
for i in range(len(V4)):
    for j in range(i+1, len(V4)):
        if C.iloc[i,j] > 0.95:
            pairs.append((V4[i], V4[j], round(float(C.iloc[i,j]),3)))
print("高相关对(|r|>0.95):", pairs)
# 3) 条件数随逐步剔除
print("满阵条件数:", round(float(np.linalg.cond(s[V4].values)),1))

# 4) 稳健拟合（仅保留非奇异子集）：用 np.linalg.lstsq 自带 rank 报告
X = s[V4].values; y = s["ff5_adj_return"].values
b, *_ = np.linalg.lstsq(X, y, rcond=None)
rank = np.linalg.matrix_rank(X)
print("X 秩 =", rank, " / 列数 =", X.shape[1])

# 5) 构建满秩 RHS：剔除零方差 + 用 QR 剔除共线列
keep = [c for c in V4 if c not in zero_var]
Xk = s[keep].values
# 逐步用条件数剔除使条件数<1e6
import itertools
def cond_ok(cols):
    return np.linalg.cond(s[cols].values) < 1e6
final = list(keep)
changed = True
while changed:
    changed = False
    for c in list(final):
        trial=[x for x in final if x!=c]
        if trial and cond_ok(trial) and np.linalg.matrix_rank(s[trial].values)==len(trial):
            final=trial; changed=True; break
print("剔除后满秩 RHS (", len(final), "列):", final)

# 6) 在该满秩集上重跑 M4_idio 与 M4_base 的 ICI
def fit_robust(df, rhs, label):
    ss = df[rhs+["ff5_adj_return","fund_code","year"]].dropna()
    n=len(ss); Xm=np.column_stack([np.ones(n), ss[rhs].values]); Y=ss["ff5_adj_return"].values
    bb,*_=np.linalg.lstsq(Xm,Y,rcond=None); resid=Y-Xm@bb
    meat=np.zeros((Xm.shape[1],Xm.shape[1]))
    for col in [ss["fund_code"].values, ss["year"].values]:
        for g in np.unique(col):
            idx=np.where(col==g)[0]; meat+=np.outer(resid[idx].sum(),resid[idx].sum())
    XtXinv=np.linalg.pinv(Xm.T@Xm); cov=XtXinv@meat@XtXinv
    se=np.sqrt(np.maximum(np.diag(cov)*n/(n-Xm.shape[1]),0))
    t=bb/se
    i=rhs.index("ICI")+1
    print(f"  [{label}] N={n}  ICI β={bb[i]:+.5f} se={se[i]:.5f} t={t[i]:+.3f}")
    return dict(n=n, ici_beta=float(bb[i]), ici_se=float(se[i]), ici_t=float(t[i]))

print("\n--- M4_base (NAV, 满秩集) ---")
rb = fit_robust(s, final, "base")
rhs2_idio = [c for c in final if c!="return_volatility"] + (["idio_vol_annual"] if "idio_vol_annual" in V4 else [])
# 注意 idio 不在 V4 内，单独处理
rhs2_idio = [c for c in final if c!="return_volatility"] + ["idio_vol_annual"]
# 确保 idio 在 s 中
s2 = df_nav[final+["idio_vol_annual","ff5_adj_return","fund_code","year"]].dropna()
print("--- M4_idio (idio 替 return_vol, 满秩集) ---")
ri = fit_robust(s2, rhs2_idio, "idio")

out=dict(nav_N=int(len(s)), zero_var=zero_var, high_corr_pairs=pairs, X_rank=int(rank),
         full_rank_rhs=final, M4_base_ICI=rb, M4_idio_ICI=ri)
with open(f"{PROJ}/output/ICI异常诊断_2026-08-27.json","w",encoding="utf-8") as f:
    json.dump(out,f,ensure_ascii=False,indent=2)
print("\n[out] output/ICI异常诊断_2026-08-27.json")
