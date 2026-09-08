"""Task A：向权威面板新增 RG_v2 列（Return Gap，重算版）。
- 数据源：基金持仓明细_全量修正版_v2.csv（canonical）
- fund_code 对齐：面板'11' ↔ 持仓'000011' → 统一 int 化
- 无前视权重：仅用 ≤ 目标季的过去快照；仅当目标日在两过去快照之间才插值（仅 Q1 生效），否则退回最近过去快照
- 保留原 RG 列不动；备份面板后写回
"""
import os, shutil, numpy as np, pandas as pd
ROOT="D:/Desktop/基金经理行为分析研究"
PANEL=f"{ROOT}/指标计算流水线/output/主分析面板_重建_含TOwind.csv"
HOLD=f"{ROOT}/指标计算流水线/data/L2_持仓偏离层/基金持仓明细_全量修正版_v2.csv"
STK=f"{ROOT}/指标计算流水线/data/股价行情/个股月收益率_全量.csv"
BACKUP=f"{ROOT}/指标计算流水线/output/主分析面板_重建_含TOwind_backup_20260821.csv"
def nf(s): return str(int(float(s)))

# 备份
shutil.copyfile(PANEL, BACKUP)
print(f"[备份] {BACKUP}")

# 个股季度收益
sm=pd.read_csv(STK,encoding="utf-8-sig"); sm["stock_code"]=sm["stock_code"].astype(str).str.zfill(6)
sm["date"]=pd.to_datetime(sm["date"]); sm["yrq"]=sm["date"].dt.to_period("Q"); sm["r"]=pd.to_numeric(sm["monthly_return"],errors="coerce")
g=sm.groupby(["stock_code","yrq"])["r"].apply(lambda x:np.prod(1+x.dropna())-1)
stock_q={(str(k[0]).zfill(6),int(k[1].year),int(k[1].quarter)):float(v) for k,v in g.items()}
print(f"  个股季度收益键数: {len(stock_q)}")

# 持仓快照
h=pd.read_csv(HOLD,encoding="utf-8-sig",low_memory=False)
h["fund_code"]=h["fund_code"].apply(nf); h["stock_code"]=h["stock_code"].astype(str).str.zfill(6)
h["w"]=pd.to_numeric(h["hold_ratio"],errors="coerce").fillna(0)/100.0
h["rd"]=pd.to_datetime(h["report_date"]); h["q"]=h["rd"].dt.to_period("Q")
snaps={}
for fc,fdf in h.groupby("fund_code"):
    fdf=fdf.sort_values("rd")
    snaps[fc]=list(zip(fdf["q"],fdf["rd"],[dict(zip(gg["stock_code"],gg["w"])) for _,gg in fdf.groupby("q")]))

# 面板基金季度
pan=pd.read_csv(PANEL,dtype={"fund_code":str}); pan["fund_code"]=pan["fund_code"].apply(nf)
pan["rd"]=pd.to_datetime(pan["report_date"]); pan["q"]=pan["rd"].dt.to_period("Q"); pan["qr"]=pd.to_numeric(pan["quarter_return"],errors="coerce")

rows=[]
for _,r in pan[["fund_code","report_date","rd","q","qr"]].iterrows():
    fc=r["fund_code"];q=r["q"];tgt=r["rd"];qr=r["qr"];rd=r["report_date"]
    if pd.isna(qr): rows.append((fc,rd,np.nan)); continue
    sp=snaps.get(fc)
    if not sp: rows.append((fc,rd,np.nan)); continue
    past=[(s[0],s[1],s[2]) for s in sp if s[1]<=tgt]
    if not past: rows.append((fc,rd,np.nan)); continue
    ps=sorted(past,key=lambda x:x[1]); p1=ps[-1]; p0=ps[-2] if len(ps)>=2 else None
    if p0 is not None and p0[1]<tgt<p1[1]:
        span=(p1[1]-p0[1]).days; f=(tgt-p0[1]).days/span if span>0 else 0.0
        wmap={}
        for stk in set(p0[2])|set(p1[2]): wmap[stk]=p0[2].get(stk,0)*(1-f)+p1[2].get(stk,0)*f
    else:
        wmap=p1[2]
    y,qn=int(q.year),int(q.quarter); port=0.0; ws=0.0
    for stk,w in wmap.items():
        sr=stock_q.get((stk,y,qn))
        if sr is not None and not pd.isna(sr): port+=w*sr; ws+=w
    if ws>0 and not pd.isna(port): rows.append((fc,rd,(qr-port)/ws))
    else: rows.append((fc,rd,np.nan))

RG=pd.DataFrame(rows,columns=["fund_code","report_date","RG_v2"])
n_old=len(pan); cov=RG["RG_v2"].notna().sum()
pan2=pan.merge(RG,on=["fund_code","report_date"],how="left")
assert len(pan2)==n_old, f"行数变化! {n_old}->{len(pan2)}"
assert "RG" in pan2.columns, "原 RG 列丢失"
# 写回（保持列顺序，RG_v2 接在 RG 后）
cols=list(pan.columns); cols.append("RG_v2")
pan2=pan2[cols]
pan2.to_csv(PANEL,index=False,encoding="utf-8-sig")
print(f"[完成] RG_v2 非空 {cov}/{n_old} ({cov/n_old*100:.1f}%)，已写回权威面板（原 RG 列保留）。")
