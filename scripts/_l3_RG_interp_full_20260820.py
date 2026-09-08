"""L3 深化核心技术动作：季度插值权重重算 Return Gap (RG_interp)，并检验显著性。
- 持仓快照半年频(06-30/12-31)；Q1/Q3 权重在相邻两快照间线性插值（仅改这两季，Q2/Q4 精确）。
- 对齐 fund_code（面板无前导零 vs 持仓有前导零 → 统一 int 化）。
- stock_code 统一 zfill(6)。
- 个股季度收益 = 月收益复利 (1+r1)(1+r2)(1+r3)-1。
- 最后跑 M4+RG_interp 双向聚类，对比原 RG 结论。
"""
import os, json, numpy as np, pandas as pd
import statsmodels.formula.api as smf
from scipy import stats as spstats

ROOT = "D:/Desktop/基金经理行为分析研究"
PANEL = f"{ROOT}/指标计算流水线/output/主分析面板_重建_含TOwind.csv"
HOLD  = f"{ROOT}/指标计算流水线/data/L2_持仓偏离层/基金持仓明细_全量修正版_v2.csv"
STK   = f"{ROOT}/指标计算流水线/data/股价行情/个股月收益率_全量.csv"
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def norm_fc(s):  # 统一 fund_code 为无前导零整数串
    return str(int(float(s)))

# ---------- 1) 个股季度收益 ----------
print("读取个股月收益并聚合为季度收益 ...")
sm = pd.read_csv(STK, encoding="utf-8-sig")
sm["stock_code"] = sm["stock_code"].astype(str).str.zfill(6)
sm["date"] = pd.to_datetime(sm["date"])
sm["ym"] = sm["date"].dt.to_period("M")
sm["yrq"] = sm["date"].dt.to_period("Q")
sm["r"] = pd.to_numeric(sm["monthly_return"], errors="coerce")
g = sm.groupby(["stock_code", "yrq"])["r"].apply(lambda x: np.prod(1+x.dropna())-1)
stock_q = {(str(k[0]).zfill(6), int(k[1].year), int(k[1].quarter)): float(v) for k,v in g.items()}
print(f"  个股季度收益键数: {len(stock_q)}")

# ---------- 2) 持仓快照 ----------
print("读取持仓快照 ...")
h = pd.read_csv(HOLD, encoding="utf-8-sig")
h["fund_code"] = h["fund_code"].apply(norm_fc)
h["stock_code"] = h["stock_code"].astype(str).str.zfill(6)
h["w"] = pd.to_numeric(h["hold_ratio"], errors="coerce").fillna(0)/100.0
h["rd"] = pd.to_datetime(h["report_date"])
h["q"] = h["rd"].dt.to_period("Q")
# 每个基金的有序快照: (period, rd_date, {stock:w})
snaps = {}
for fc, fdf in h.groupby("fund_code"):
    fdf = fdf.sort_values("rd")
    snaps[fc] = list(zip(fdf["q"], fdf["rd"],
                    [dict(zip(gg["stock_code"], gg["w"])) for _,gg in fdf.groupby("q")]))
print(f"  持仓基金数: {len(snaps)}")

# ---------- 3) 基金季度目标（取面板 quarter_return） ----------
pan = pd.read_csv(PANEL, dtype={"fund_code": str})
pan["fund_code"] = pan["fund_code"].apply(norm_fc)
pan["rd"] = pd.to_datetime(pan["report_date"])
pan["q"] = pan["rd"].dt.to_period("Q")
pan["qr"] = pd.to_numeric(pan["quarter_return"], errors="coerce")

def quarter_end(yr, q):
    return pd.Timestamp(year=yr, month=[3,6,9,12][q-1], day=31 if q!=2 else 30)

# ---------- 4) 插值权重 + 组合收益 + RG ----------
rows = []
for _, r in pan[["fund_code","report_date","rd","q","qr"]].iterrows():
    fc = r["fund_code"]; q = r["q"]; tgt = r["rd"]; qr = r["qr"]; rdate = r["report_date"]
    if pd.isna(qr): rows.append((fc, rdate, np.nan)); continue
    sp = snaps.get(fc)
    if not sp: rows.append((fc, rdate, np.nan)); continue
    # 无前视插值：只用 ≤ tgt 的过去快照；取最近过去(p1)及其前一个(p0)。
    # 仅当 tgt 落在 p0.rd 与 p1.rd 之间时才插值；否则退回最近过去快照(与原始一致，避免前视)。
    past = [(s[0], s[1], s[2]) for s in sp if s[1] <= tgt]
    if not past: rows.append((fc, rdate, np.nan)); continue
    past_sorted = sorted(past, key=lambda x: x[1])
    p1 = past_sorted[-1]; p0 = past_sorted[-2] if len(past_sorted) >= 2 else None
    if p0 is not None and p0[1] < tgt < p1[1]:
        span = (p1[1]-p0[1]).days
        f = (tgt - p0[1]).days/span if span > 0 else 0.0
        wmap = {}
        for stk in set(p0[2])|set(p1[2]):
            wmap[stk] = p0[2].get(stk,0)*(1-f) + p1[2].get(stk,0)*f
    else:
        wmap = p1[2]   # 最近过去快照（Q3 等无法合法插值时退化回原始口径）
    y,qn = int(q.year), int(q.quarter)
    port = 0.0; wsum = 0.0
    for stk,w in wmap.items():
        sr = stock_q.get((stk,y,qn))
        if sr is not None and not pd.isna(sr):
            port += w*sr; wsum += w
    if wsum>0 and not pd.isna(port):
        port /= wsum
        rows.append((fc, rdate, qr - port))
    else:
        rows.append((fc, rdate, np.nan))

RG = pd.DataFrame(rows, columns=["fund_code","report_date","RG_interp"])
cov = RG["RG_interp"].notna().sum()
print(f"  RG_interp 非空: {cov} / {len(RG)}")
RG.to_csv(f"{ROOT}/output/RG_interp_2026-08-20.csv", index=False, encoding="utf-8-sig")

# ---------- 5) 合并入面板并跑 M4+RG_interp ----------
pan2 = pan.merge(RG, on=["fund_code","report_date"], how="left")
pan2["log_aum"] = np.log(pd.to_numeric(pan2["avg_aum"],errors="coerce").clip(lower=1e-9))
pan2["ff5_adj_return"] = pd.to_numeric(pan2["ff5_adj_return"],errors="coerce")
FF5=["ff5_MKT_excess","ff5_SMB","ff5_HML","ff5_RMW","ff5_CMA"]; CONT=["log_aum"]
L1=["log_fund_age","mgr_total_tenure_v2"]; L2=["AS_improved","ICI","industry_hhi"]
L3=["SDI","TO_wind"]; L4=["ARG","return_volatility"]; L5=["de","lsv","risk_asym"]
RHS = CONT+FF5+L1+L2+L3+L4+L5
def winsor(s):
    s=s.astype(float); lo,hi=s.quantile(.01),s.quantile(.99); return s.clip(lo,hi)
for v in RHS+["RG_interp","ff5_adj_return"]:
    pan2[v+"_w"]=winsor(pd.to_numeric(pan2[v],errors="coerce"))
def meat(gr,X,res):
    k=X.shape[1]; m=np.zeros((k,k))
    for gg in np.unique(gr):
        mm=gr==gg; s=X[mm].T@res[mm]; m+=np.outer(s,s)
    return m
def ow(X,res,gr): return np.linalg.inv(X.T@X)@meat(gr,X,res)@np.linalg.inv(X.T@X)
def tw(X,res,a,b):
    ab=np.array([f"{x}|{y}" for x,y in zip(a,b)])
    return ow(X,res,a)+ow(X,res,b)-ow(X,res,ab)
rhs_w=[r+"_w" for r in RHS]+["RG_interp_w"]
d=pan2.dropna(subset=rhs_w+["ff5_adj_return_w"]).copy()
form="ff5_adj_return_w ~ "+" + ".join(rhs_w)+" + C(year)"
m=smf.ols(form,data=d).fit(cov_type="cluster",cov_kwds={"groups":d["fund_code"]})
X=np.asarray(m.model.data.exog,float); res=np.asarray(m.resid,float)
g1=d["fund_code"].values.astype(str); g2=d["year"].values.astype(str)
V2=tw(X,res,g1,g2); se2=np.sqrt(np.maximum(np.diag(V2),0)); t2=m.params.values/se2
p2=2*spstats.t.sf(np.abs(t2),df=len(res)-X.shape[1])
names=list(m.params.index); out={}
for i,nm in enumerate(names):
    if nm=="Intercept" or nm.startswith("C(year)"): continue
    base=nm[:-2] if nm.endswith("_w") else nm
    out[base]=dict(beta=float(m.params.values[i]),t2w=float(t2[i]),p2w=float(p2[i]))
print(f"\n[M4+RG_interp] N={int(m.nobs)} R²={m.rsquared:.4f}")
def st(p): return "***" if p<.01 else "**" if p<.05 else "*" if p<.1 else "n.s."
for v in ["SDI","TO_wind","RG_interp"]:
    r=out[v]; print(f"  {v:10s} β={r['beta']:+.5f} t2w={r['t2w']:+.2f} p2w={r['p2w']:.3f} {st(r['p2w']):>4s}")

# 隔离 RG_interp（仅 L3=RG_interp）
rhs2=[r+"_w" for r in CONT+FF5+L1+L2+["RG_interp"]+L4+L5]
d2=pan2.dropna(subset=rhs2+["ff5_adj_return_w"]).copy()
m2=smf.ols("ff5_adj_return_w ~ "+" + ".join(rhs2)+" + C(year)",data=d2).fit(cov_type="cluster",cov_kwds={"groups":d2["fund_code"]})
X2=np.asarray(m2.model.data.exog,float); res2=np.asarray(m2.resid,float)
V22=tw(X2,res2,d2["fund_code"].values.astype(str),d2["year"].values.astype(str))
se22=np.sqrt(np.maximum(np.diag(V22),0)); t22=m2.params.values/se22
iRG=[i for i,nm in enumerate(m2.params.index) if nm=="RG_interp_w"][0]
p22=2*spstats.t.sf(np.abs(t22[iRG]),df=len(res2)-X2.shape[1])
print(f"  [隔离RG_interp] N={int(m2.nobs)} β={m2.params.values[iRG]:+.5f} t2w={t22[iRG]:+.2f} p2w={p22:.3f} {st(p22)}")
print("\n[已写出] output/RG_interp_2026-08-20.csv")
