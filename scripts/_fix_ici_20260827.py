# -*- coding: utf-8 -*-
"""诊断并修复 M4_idio 下 ICI t=+38.6 异常（2026-08-27 复算）"""
import json, numpy as np, pandas as pd
from numpy.linalg import lstsq, inv, pinv, cond

PROJ = "D:/Desktop/基金经理行为分析研究"
panel = pd.read_csv(f"{PROJ}/指标计算流水线/output/主分析面板_重建_含TOwind.csv")
batch2 = pd.read_csv(f"{PROJ}/output/batch2_daily_factors_2026-08-21.csv")

panel["log_aum"] = np.log(panel["avg_aum"].astype(float))
batch2["year"] = batch2["year"].astype(int)
panel["year"] = panel["year"].astype(int)
panel["fund_code"] = panel["fund_code"].astype(str)
batch2["fund_code"] = batch2["fund_code"].astype(str)
df_all = panel.merge(batch2[["fund_code","year","TM_beta2","idio_vol_annual",
                              "factor_drift","TM_alpha_annual"]],
                     on=["fund_code","year"], how="left")
df_nav = df_all[df_all["TM_beta2"].notna()].copy()
df_nav["SDI"] = df_nav["SDI"].fillna(0)
df_nav["TO_wind"] = df_nav["TO_wind"].fillna(df_nav["TO_wind"].median())
for c in ["ff5_MKT_excess","ff5_SMB","ff5_HML","ff5_RMW","ff5_CMA"]:
    df_nav[c] = df_nav[c].fillna(0)

V4_BASE = ["log_aum","log_fund_age","mgr_total_tenure_v2","AS_improved","ICI","industry_hhi",
           "SDI","TO_wind","ARG","return_volatility","de","lsv","risk_asym",
           "ff5_MKT_excess","ff5_SMB","ff5_HML","ff5_RMW","ff5_CMA"]

def fit_ici(df, rhs, label):
    s = df[rhs+["ff5_adj_return","fund_code","year"]].dropna()
    n=len(s); X=np.column_stack([np.ones(n), s[rhs].values]); y=s["ff5_adj_return"].values
    b,*_=lstsq(X,y,rcond=None); resid=y-X@b
    # 简易双聚类 SE（fund×year）
    u=resid; meat=np.zeros((X.shape[1],X.shape[1]))
    for key,col in [("f",s["fund_code"].values),("y",s["year"].values)]:
        for g in np.unique(col):
            idx=np.where(col==g)[0]; meat+=np.outer(u[idx].sum(),u[idx].sum())
    XtXinv=inv(X.T@X); cov=XtXinv@meat@XtXinv
    se=np.sqrt(np.maximum(np.diag(cov)*n/(n-X.shape[1]),0))
    t=b/se
    print(f"\n[{label}] N={n}  条件数={cond(X):.1f}")
    for i,name in enumerate(["_c"]+rhs):
        if name in ("ICI",):
            print(f"   ICI  β={b[i]:+.5f}  se={se[i]:.6f}  t={t[i]:+.3f}")
    # ICI 与其他 RHS 的相关
    sub=s[rhs].dropna()
    print("   ICI 与 idio_vol 相关 =", round(float(sub[["ICI","idio_vol_annual"]].corr().iloc[0,1]),3) if "idio_vol_annual" in sub else "NA")
    print("   ICI std =", round(float(s["ICI"].std()),4), " ICI nunique =", int(s["ICI"].nunique()))
    return dict(n=n, ici_beta=float(b[rhs.index("ICI")+1]), ici_se=float(se[rhs.index("ICI")+1]), ici_t=float(t[rhs.index("ICI")+1]))

print("=== M4_base (NAV子集, 含 return_vol) ===")
r_base = fit_ici(df_nav, V4_BASE, "M4_base")
print("\n=== M4_idio (idio 替 return_vol) ===")
rhs2=[c for c in V4_BASE if c!="return_volatility"]+["idio_vol_annual"]
r_idio = fit_ici(df_nav, rhs2, "M4_idio")

# 关键检查：df_nav 是否有重复 (fund_code,year) 导致 X 行重复
dup = df_nav.duplicated(subset=["fund_code","year"]).sum()
print(f"\n[检查] df_nav 重复(fund_code,year)行数 = {dup}")
# ICI 在 NAV 子集是否近常量 / 含异常值
print("ICI describe:\n", df_nav["ICI"].describe())
print("\nidio_vol_annual describe:\n", df_nav["idio_vol_annual"].describe())

# 修复候选：用稳健缩尾 + 检查缺失
df_nav_w = df_nav.copy()
for c in rhs2:
    if c in df_nav_w: df_nav_w[c]=df_nav_w[c].clip(df_nav_w[c].quantile(.01),df_nav_w[c].quantile(.99))
print("\n=== M4_idio (idio 替 return_vol, 1%/99%缩尾) ===")
r_idio_w = fit_ici(df_nav_w, rhs2, "M4_idio_winsor")

out=dict(M4_base=r_base, M4_idio_raw=r_idio, M4_idio_winsor=r_idio_w,
         df_nav_dup_rows=int(dup),
         ICI_nunique=int(df_nav["ICI"].nunique()),
         idio_nunique=int(df_nav["idio_vol_annual"].nunique()))
with open(f"{PROJ}/output/ICI异常诊断_2026-08-27.json","w",encoding="utf-8") as f:
    json.dump(out,f,ensure_ascii=False,indent=2)
print("\n[out] output/ICI异常诊断_2026-08-27.json")
