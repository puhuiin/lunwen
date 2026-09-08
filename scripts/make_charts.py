# -*- coding: utf-8 -*-
"""生成汇总图 + HTML 描述性统计报告。"""
import json, os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import numpy as np

# 中文字体
for fp in [r"C:\Windows\Fonts\simhei.ttf", r"C:\Windows\Fonts\msyh.ttc"]:
    if os.path.exists(fp):
        fm.fontManager.addfont(fp)
plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.dpi"] = 130

BASE = r"D:\Desktop\基金经理行为分析研究"
OUT  = os.path.join(BASE, "描述性统计")
FIG  = os.path.join(OUT, "figures")
os.makedirs(FIG, exist_ok=True)

S = json.load(open(os.path.join(OUT,"descriptive_stats.json"),encoding="utf-8"))
INV = json.load(open(os.path.join(BASE,"data_inventory.json"),encoding="utf-8"))

ACCENT="#2E5A87"; ACCENT2="#C0504D"; GREY="#9AA5B1"; GREEN="#4F8A5B"

# ============ 图1：各数据层文件数量与体积 ============
layers_order = ["FF因子","L1_背景特征层","L2_持仓偏离层","L3_交易行为层","L4_风险应对层",
                "L5_认知行为层","基金基础信息","外部数据","宏观数据","文档与元数据","股价行情","补充数据源"]
labels=[]; nf=[]; sz=[]
for L in layers_order:
    if L in INV["layers"]:
        labels.append(L.replace("_","\n")); nf.append(INV["layers"][L]["n_files"])
        sz.append(INV["layers"][L]["total_kb"]/1024.0)  # MB
fig,ax=plt.subplots(figsize=(11,5.2))
x=np.arange(len(labels))
b1=ax.bar(x-0.2,nf,0.4,label="文件数",color=ACCENT)
ax2=ax.twinx()
b2=ax2.bar(x+0.2,sz,0.4,label="体积(MB)",color=ACCENT2,alpha=0.8)
ax.set_xticks(x); ax.set_xticklabels(labels,fontsize=8.5)
ax.set_ylabel("文件数",color=ACCENT); ax2.set_ylabel("体积 (MB)",color=ACCENT2)
ax.set_title("各数据层文件数量与体积（活跃分析层，不含'无用数据'）",fontsize=12,fontweight="bold")
for i,v in enumerate(nf): ax.text(i-0.2,v+0.3,str(v),ha="center",fontsize=8,color=ACCENT)
lines=[b1,b2]
ax.legend(lines,[l.get_label() for l in lines],loc="upper right",fontsize=9)
plt.tight_layout(); plt.savefig(os.path.join(FIG,"fig1_layers.png")); plt.close()

# ============ 图2：主分析面板季度观测覆盖 ============
panel=S["main_panel"]
oq=panel["obs_per_quarter"]
xs=list(oq.keys()); ys=[oq[k] for k in xs]
fig,ax=plt.subplots(figsize=(11,4.6))
ax.bar(range(len(xs)),ys,color=ACCENT,alpha=0.85)
ax.set_xticks(range(len(xs))); ax.set_xticklabels(xs,rotation=90,fontsize=6.5)
ax.set_ylabel("基金-季度观测数")
ax.set_title(f"主分析面板时间覆盖：{panel['n_obs']:,} 观测 · {panel['n_funds']} 只基金 · {panel['date_min']} ~ {panel['date_max']}",
             fontsize=12,fontweight="bold")
ax.axhline(np.mean(ys),color=ACCENT2,ls="--",lw=1,label=f"均值 {np.mean(ys):.0f}")
ax.legend(fontsize=9)
plt.tight_layout(); plt.savefig(os.path.join(FIG,"fig2_panel_coverage.png")); plt.close()

# ============ 图3：L5 三指标分布 ============
l5=S["L5"]
fig,axes=plt.subplots(1,3,figsize=(13,4))
specs=[("DE","de","处置效应 DE = PGR−PLR"),
       ("LSV","lsv","羊群行为 LSV"),
       ("RA","risk_asym","风险偏好不对称 RiskAsym")]
for ax,(tag,var,title) in zip(axes,specs):
    fn={"DE":"L5_认知行为层/处置效应DE指标_修正版.csv","LSV":"L5_认知行为层/羊群行为LSV指标.csv","RA":"L5_认知行为层/风险偏好不对称RA指标.csv"}[tag]
    import pandas as pd
    d=pd.read_csv(os.path.join(BASE,"数据",fn))
    v=pd.to_numeric(d[var],errors="coerce").dropna()
    ax.hist(v,bins=40,color=ACCENT,alpha=0.85,edgecolor="white",linewidth=0.3)
    ax.axvline(v.mean(),color=ACCENT2,lw=1.6,label=f"均值 {v.mean():.3f}")
    ax.axvline(0,color=GREY,lw=1,ls=":")
    ax.set_title(title,fontsize=11,fontweight="bold")
    ax.set_xlabel(var); ax.set_ylabel("频数")
    ax.legend(fontsize=8)
plt.tight_layout(); plt.savefig(os.path.join(FIG,"fig3_l5_dist.png")); plt.close()

# ============ 图4：基金池类型分布 ============
fund=S["fund_universe"]
bt=fund["by_type"]
items=sorted(bt.items(),key=lambda x:-x[1])
lab=[k for k,_ in items]; val=[v for _,v in items]
fig,ax=plt.subplots(figsize=(10,4.6))
ax.barh(range(len(lab)),val,color=ACCENT,alpha=0.85)
ax.set_yticks(range(len(lab))); ax.set_yticklabels(lab,fontsize=9)
ax.invert_yaxis()
ax.set_xlabel("基金数量")
ax.set_title(f"基金池类型分布（全样本 {fund['n_total']:,} 只，含清盘）",fontsize=12,fontweight="bold")
for i,v in enumerate(val): ax.text(v+50,i,str(v),va="center",fontsize=8)
plt.tight_layout(); plt.savefig(os.path.join(FIG,"fig4_fund_types.png")); plt.close()

# ============ 图5：宏观与FF数据时间跨度 ============
macro=S["macro"]; ff=S["ff_factors"]
rows=[]
for k,v in macro.items():
    if v.get("year_min") is not None:
        rows.append((k.replace("宏观_","").replace(".csv",""), v["year_min"], v["year_max"], v.get("n_periods",0)))
rows.append(("FF5月度因子",2002,2026,ff["FF5月度因子.csv"]["n_rows"]))
rows.append(("FF5日度因子",1995,2026,ff["FF5日度因子.csv"]["n_rows"]))
rows.append(("国债收益率(日)",1990,2026,macro["国债收益率.csv"]["n_periods"]))
rows.sort(key=lambda x:x[1])
fig,ax=plt.subplots(figsize=(10,5))
for i,(name,y0,y1,n) in enumerate(rows):
    ax.barh(i, y1-y0, left=y0, height=0.6, color=ACCENT if "FF" in name or "国债" in name else GREEN, alpha=0.85)
    ax.text(y1+0.2,i,f"{y0}–{y1} (n={n:,})",va="center",fontsize=7.5)
ax.set_yticks(range(len(rows))); ax.set_yticklabels([r[0] for r in rows],fontsize=8.5)
ax.set_xlabel("年份")
ax.set_title("宏观与定价因子数据时间跨度",fontsize=12,fontweight="bold")
ax.set_xlim(1990, 2030)
plt.tight_layout(); plt.savefig(os.path.join(FIG,"fig5_macro_span.png")); plt.close()

print(">> 5 张图已生成:", os.listdir(FIG))
