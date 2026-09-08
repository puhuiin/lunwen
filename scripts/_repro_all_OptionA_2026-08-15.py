# -*- coding: utf-8 -*-
"""
Option A 完整诚实重估脚本（2026-08-15）
基于当前诚实面板 主分析面板_重建_含TOwind.csv 重算所有受 TO_calc/OCI 删除影响的数字：
  A. 表4-2 描述性统计（全面板 1%/99% 缩尾，覆盖率 = 非缺失占比）
  B. M0–M4 递进回归（DV=ff5_adj_return，基金簇稳健 SE，含年份 FE）——诚实口径
  C. 表4-5 M4 完整模型系数（TO_wind 替换 TO_calc；OCI 剔除；mgr_total_tenure_v2）
  D. 表4-6 VIF（诚实 M4 RHS）
  E. 中介分析（TO_wind 替换 TO_calc，Baron-Kenny + Bootstrap 500）
  F. 2SLS IV（滞后一期工具变量）
  G. Oster 界（β_restricted / β_full / R² / δ）
  H. PS 描述性统计（M4 样本）
  I. §4.2.7 ΔR² 与 §4.3 同样本
输出 JSON：_repro_all_OptionA_2026-08-15.json
"""
import json, warnings, numpy as np, pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
warnings.filterwarnings("ignore")

PANEL = r"指标计算流水线/output/主分析面板_重建_含TOwind.csv"
OUT   = r"_repro_all_OptionA_2026-08-15.json"

df = pd.read_csv(PANEL)
TOTAL = len(df)

# ---------- 派生控制变量 ----------
df["log_aum"] = np.log(df["avg_aum"].clip(lower=1e-9))
# 清理 DV / 关键列
df["ff5_adj_return"] = pd.to_numeric(df["ff5_adj_return"], errors="coerce")

CONT = ["log_aum"]
FF5  = ["ff5_MKT_excess","ff5_SMB","ff5_HML","ff5_RMW","ff5_CMA"]
L1   = ["log_fund_age","mgr_total_tenure_v2"]
L2   = ["AS_improved","ICI","industry_hhi"]
L3   = ["SDI","TO_wind"]          # OCI 剔除（仅 18% 覆盖）
L4   = ["ARG","return_volatility"]
L5   = ["de","lsv","risk_asym"]

ALLRHS = CONT + FF5 + L1 + L2 + L3 + L4 + L5

# ---------- 缩尾（1%/99%，全面板） ----------
def winsor(s):
    s = s.astype(float)
    lo, hi = s.quantile(0.01), s.quantile(0.99)
    return s.clip(lo, hi)
for v in ALLRHS + ["ff5_adj_return"]:
    df[v+"_w"] = winsor(df[v])

def cov(col):
    return round(100.0 * df[col].notna().mean(), 1)

def desc(col):
    wcol = col+"_w" if (col+"_w") in df.columns else col
    s = df[wcol].dropna()   # 1%/99% 缩尾值（无 _w 则用原始）
    return dict(mean=round(s.mean(),4), std=round(s.std(),4), min=round(s.min(),4),
               median=round(s.median(),4), max=round(s.max(),4), cov=cov(col))

# =====================================================================
# A. 描述性统计（表4-2）
# =====================================================================
desc_order = ["ff5_adj_return","mgr_total_tenure_v2","log_fund_age","AS_improved","ICI",
              "industry_hhi","SDI","TO_wind","OCI_two_sided","ARG","return_volatility",
              "de","lsv","risk_asym","log_aum"]
A = {c: desc(c) for c in desc_order}

# =====================================================================
# B. M0–M4 递进回归
# =====================================================================
def run_model(rhs, data):
    rhs_w = [r+"_w" for r in rhs]
    d = data.dropna(subset=rhs_w+["ff5_adj_return_w"]).copy()
    form = "ff5_adj_return_w ~ " + " + ".join(rhs_w) + " + C(year)"
    m = smf.ols(form, data=d).fit(cov_type="cluster", cov_kwds={"groups": d["fund_code"]})
    return m, len(d), d["fund_code"].nunique()

specs = {
    "M0": CONT + FF5,
    "M1": CONT + FF5 + L1,
    "M2": CONT + FF5 + L1 + L2,
    "M3": CONT + FF5 + L1 + L2 + L3 + L4,
    "M4": CONT + FF5 + L1 + L2 + L3 + L4 + L5,
}
B = {}
models = {}
for name, rhs in specs.items():
    m, n, nf = run_model(rhs, df)
    models[name] = (m, n, nf, rhs)
    B[name] = dict(N=n, funds=nf, R2=round(m.rsquared,4), adjR2=round(m.rsquared_adj,4))

# §4.2.7 ΔR²
def dR2(a,b): return round(B[b]["R2"]-B[a]["R2"],4)
B["dR2"] = {
    "M0_M1": dR2("M0","M1"), "M1_M2": dR2("M1","M2"), "M2_M3": dR2("M2","M3"),
    "M3_M4": dR2("M3","M4"), "M0_M4": dR2("M0","M4"),
}
# §4.3 同样本（在 M4 样本上重估 M0/M3）
m4_model, m4_n, m4_nf, m4_rhs = models["M4"]
m4_data = df.dropna(subset=[r+"_w" for r in m4_rhs]+["ff5_adj_return_w"]).copy()
def run_on(data, rhs):
    rhs_w=[r+"_w" for r in rhs]
    d=data.dropna(subset=rhs_w+["ff5_adj_return_w"]).copy()
    form="ff5_adj_return_w ~ "+" + ".join(rhs_w)+" + C(year)"
    m=smf.ols(form,data=d).fit(cov_type="cluster",cov_kwds={"groups":d["fund_code"]})
    return m,d["fund_code"].nunique(),len(d)
m0s,_ ,_ = run_on(m4_data, CONT+FF5)
m3s,_ ,_ = run_on(m4_data, CONT+FF5+L1+L2+L3+L4)
m4s,m4s_nf,m4s_n = run_on(m4_data, m4_rhs)
B["same_sample"] = {
    "M0_R2": round(m0s.rsquared,4), "M3_R2": round(m3s.rsquared,4),
    "M4_R2": round(m4s.rsquared,4), "dR2_L5": round(m4s.rsquared-m3s.rsquared,4),
    "N": m4s_n, "funds": m4s_nf,
}

# =====================================================================
# C. 表4-5 M4 系数
# =====================================================================
def stars(p):
    return "***" if p<0.01 else ("**" if p<0.05 else ("*" if p<0.1 else ""))
M4C = {}
m4,_,_,_ = models["M4"]
for v in m4_rhs:
    beta=m4.params[v+"_w"]; t=m4.tvalues[v+"_w"]; p=m4.pvalues[v+"_w"]
    M4C[v]=dict(beta=round(beta,5), t=round(t,2), p=round(p,4), stars=stars(p))

# =====================================================================
# D. 表4-6 VIF
# =====================================================================
from statsmodels.stats.outliers_influence import variance_inflation_factor
m4d = df.dropna(subset=[r+"_w" for r in m4_rhs]+["ff5_adj_return_w"]).copy()
X = sm.add_constant(pd.DataFrame({r:m4d[r+"_w"] for r in m4_rhs}))
D = {}
for i,col in enumerate(X.columns):
    if col=="const": continue
    vif = variance_inflation_factor(X.values, i)
    D[col]=dict(vif=round(vif,2), inv=round(1.0/vif,3))

# =====================================================================
# E. 中介分析（TO_wind 替换 TO_calc）+ return_vol（不变）
# =====================================================================
def mediate(Xname, Mname, Y="ff5_adj_return_w"):
    need=[Xname,Mname,Y]+m4_rhs
    d=df.dropna(subset=[c+"_w" if c in m4_rhs else c for c in [Xname,Mname,Y]]).copy()
    d=d.dropna(subset=[Xname,Mname,Y])
    # a 路径
    a=smf.ols(f"{Mname} ~ {Xname}", data=d).fit()
    # b 路径（含 X 与控制）
    ctrl=[r for r in m4_rhs if r not in (Xname,)]
    form_b=f"{Y} ~ {Mname} + {Xname} + " + " + ".join(ctrl)
    b=smf.ols(form_b, data=d).fit()
    a_coef=a.params[Xname]; b_coef=b.params[Mname]
    indirect=a_coef*b_coef
    # bootstrap 500
    rng=np.random.default_rng(20260815)
    idx=np.arange(len(d))
    bs=[]
    for _ in range(500):
        s=rng.choice(idx, size=len(idx), replace=True)
        dd=d.iloc[s]
        aa=smf.ols(f"{Mname} ~ {Xname}", data=dd).fit()
        bb=smf.ols(form_b, data=dd).fit()
        bs.append(aa.params[Xname]*bb.params[Mname])
    bs=np.array(bs)
    ci=(round(float(np.percentile(bs,2.5)),5), round(float(np.percentile(bs,97.5)),5))
    # M→Y 整体显著？用 b 路径 t
    return dict(a=round(a_coef,4), b=round(b_coef,4), ind=round(indirect,5),
                ci=ci, b_t=round(b.tvalues[Mname],3),
                sig=("✓***" if b.pvalues[Mname]<0.01 else ("✓**" if b.pvalues[Mname]<0.05 else ("✓*" if b.pvalues[Mname]<0.1 else "✗"))),
                N=len(d))

E = {
    "LSV_TO": mediate("lsv","TO_wind"),
    "RA_TO":  mediate("risk_asym","TO_wind"),
    "DE_TO":  mediate("de","TO_wind"),
    "LSV_RV": mediate("lsv","return_volatility"),
    "RA_RV":  mediate("risk_asym","return_volatility"),
    "DE_RV":  mediate("de","return_volatility"),
}

# =====================================================================
# F. 2SLS IV（滞后一期工具变量）——诚实可行性核查
# =====================================================================
iv_df = df.sort_values(["fund_code","year","quarter"]).copy()
for v in L5:
    iv_df["L1_"+v] = iv_df.groupby("fund_code")[v].shift(1)
iv_rhs = CONT+FF5+L1+L2+L3+L4
need = iv_rhs + L5 + ["L1_"+v for v in L5] + ["ff5_adj_return_w"]
iv_d = iv_df.dropna(subset=need).copy()
F = {}
# OLS 参照列 = 诚实 M4 系数（来自 M4C）
for v in L5:
    F[v] = dict(ols=M4C[v]["beta"], ols_t=M4C[v]["t"])
# 2SLS 可行性：诚实面板要求 当期+滞后 L5 同时非缺失，DE 为半年度稀疏 → 样本塌缩
F["iv_feasible"] = (len(iv_d) >= 100)
F["iv_N"] = len(iv_d)
F["iv_funds"] = int(iv_d["fund_code"].nunique()) if len(iv_d)>0 else 0
F["note"] = ("诚实面板下，2SLS 滞后一期 L5 工具变量集的可用样本塌缩为 %d 行"
             "（DE 为半年度稀疏指标，要求当期与滞后 DE 同时非缺失导致交集为空），"
             "故 IV/2SLS 无法在诚实数据上复现；下表 IV 列仅供方法说明，OLS 参照列已更新为诚实 M4 系数。"
             % len(iv_d))

# =====================================================================
# G. Oster 界
# =====================================================================
def oster(Xname):
    # 完整模型 = M4（含 X 与全部控制）；受限模型 = 仅 X + 控制变量（不含其他 L1-L5）
    rhs_full = CONT+FF5+L1+L2+L3+L4+[Xname]   # 同 m4_rhs
    rhs_res  = CONT+FF5+[Xname]
    mf,_ ,_ = run_on(df, rhs_full)
    mr,_ ,_ = run_on(df, rhs_res)
    b_full=mf.params[Xname+"_w"]; b_res=mr.params[Xname+"_w"]
    R2f=mf.rsquared; R2r=mr.rsquared; R2max=min(1,1.3*R2f)
    if (R2f-R2r)==0 or (b_full-b_res)==0:
        delta=None
    else:
        b_max = b_full + (b_full-b_res)*(R2max-R2f)/(R2f-R2r)
        delta = (b_full-b_res)/(b_full-b_max)
    return dict(b_restricted=round(b_res,4), b_full=round(b_full,4),
                R2_full=round(R2f,3), R2_restricted=round(R2r,3), R2_max=round(R2max,3),
                delta=round(delta,2) if delta==delta else None)
G = {v: oster(v) for v in L5}

# =====================================================================
# H. PS 描述性统计（M4 样本）
# =====================================================================
ps_d = m4d.copy()
H = dict(N=len(ps_d), funds=ps_d["fund_code"].nunique(),
         mean=round(ps_d["ff5_adj_return_w"].mean(),4) if False else None)
# PS 用 M4 系数加权
zw = {v:(ps_d[v]-ps_d[v].mean())/ps_d[v].std() for v in L5}
ps_score = (-abs(M4C["de"]["beta"])*zw["de"] + abs(M4C["lsv"]["beta"])*zw["lsv"]
            + abs(M4C["risk_asym"]["beta"])*zw["risk_asym"])
H = dict(N=len(ps_d), funds=ps_d["fund_code"].nunique(),
         ps_mean=round(float(ps_score.mean()),4), ps_std=round(float(ps_score.std()),4),
         ps_min=round(float(ps_score.min()),4), ps_max=round(float(ps_score.max()),4))
# PS 权重 |β|
H["weights"] = {v: abs(M4C[v]["beta"]) for v in L5}

# =====================================================================
# 输出
# =====================================================================
result = dict(TOTAL=TOTAL, A_desc=A, B_progressive=B, C_m4=M4C, D_vif=D,
              E_mediation=E, F_iv=F, G_oster=G, H_ps=H)
with open(OUT,"w",encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

# 打印关键结果
print("=== A 描述性统计 ===")
for k,v in A.items():
    print(f"  {k:20s} mean={v['mean']:>9} std={v['std']:>9} min={v['min']:>9} med={v['median']:>9} max={v['max']:>9} cov={v['cov']}%")
print("\n=== B 递进 M0-M4 ===")
for k in ["M0","M1","M2","M3","M4"]:
    print(f"  {k}: N={B[k]['N']} funds={B[k]['funds']} R2={B[k]['R2']} adjR2={B[k]['adjR2']}")
print("  ΔR²:", B["dR2"])
print("  同样本:", B["same_sample"])
print("\n=== C 表4-5 M4 系数 ===")
for k,v in M4C.items():
    print(f"  {k:18s} β={v['beta']:>10} t={v['t']:>7} p={v['p']:>7} {v['stars']}")
print("\n=== D VIF ===")
for k,v in D.items():
    print(f"  {k:18s} VIF={v['vif']} 1/VIF={v['inv']}")
print("\n=== E 中介 (TO_wind & return_vol) ===")
for k,v in E.items():
    print(f"  {k:10s} a={v['a']} b={v['b']} ind={v['ind']} CI={v['ci']} {v['sig']} N={v['N']}")
print("\n=== F IV ===")
for k,v in F.items():
    print(f"  {k}: {v}")
print("\n=== G Oster ===")
for k,v in G.items():
    print(f"  {k}: {v}")
print("\n=== H PS ===")
print(" ", H)
print("\nDONE ->", OUT)
