# -*- coding: utf-8 -*-
"""按论文解读说明.html 的 L1-L5 框架，从主分析面板提取各层指标的描述统计。"""
import pandas as pd, numpy as np, json, os
from datetime import datetime

BASE = r"D:\Desktop\基金经理行为分析研究"
OUT  = os.path.join(BASE, "描述性统计")
# 真实主分析面板（真算口径，已剔除模拟占位列 SDI_hc/OCI_hc/TO_calc/SDI_original）
# 注意：此前指向 数据/L4_风险应对层/主分析面板_修正版.csv，但该文件是用户要求"模拟对齐字段"的
# 占位面板（=mvp_panel_v22），其 SDI/OCI/TO_calc 为高覆盖模拟值，已于 2026-08-14 审计确认并剔除。
PANEL = os.path.join(BASE, "指标计算流水线", "output", "主分析面板_重建_含TOwind.csv")

df = pd.read_csv(PANEL)
N = len(df)

def stats(s):
    s = pd.to_numeric(s, errors="coerce")
    n = int(s.notna().sum())
    if n == 0:
        return None
    return {
        "n": n,
        "missing_pct": round(100*(1-n/len(s)), 2),
        "mean": round(float(s.mean()), 6),
        "std": round(float(s.std()), 6),
        "min": round(float(s.min()), 6),
        "p25": round(float(s.quantile(.25)), 6),
        "median": round(float(s.median()), 6),
        "p75": round(float(s.quantile(.75)), 6),
        "max": round(float(s.max()), 6),
    }

def cat_info(s):
    s = s.dropna()
    n = int(s.notna().sum())
    vc = s.astype(str).value_counts().head(6).to_dict()
    return {"n": n, "missing_pct": round(100*(1-n/len(s)), 2), "top": {k:int(v) for k,v in vc.items()}}

# 框架指标定义（变量名严格对应主面板列）
FRAMEWORK = {
 "L1": {
   "title":"L1 经理背景层","sub":"谁在管理",
   "numeric":["mgr_total_tenure_v2","log_fund_age","manager_tenure","fund_age","family_size","log_aum"],
   "cat":["gender","education","CFA","school","major"],
 },
 "L2": {
   "title":"L2 投资决策层","sub":"如何配置",
   "numeric":["AS_improved","AS","AS_original","ICI","ICI_original","industry_hhi"],
   "cat":[],
 },
 "L3": {
   "title":"L3 交易执行层","sub":"如何执行",
   "numeric":["SDI","TO_wind","TO_two_sided","OCI_two_sided"],
   "cat":[],
 },
 "L4": {
   "title":"L4 风险管理层","sub":"如何控险",
   "numeric":["ARG","return_volatility"],
   "cat":[],
 },
 "L5": {
   "title":"L5 认知偏差层","sub":"为何如此决策",
   "numeric":["de","pgr","plr","lsv","risk_asym"],
   "cat":[],
 },
}

layers = {}
for L, info in FRAMEWORK.items():
    recs = []
    for v in info["numeric"]:
        if v in df.columns:
            recs.append({"variable":v, "type":"num", **(stats(df[v]) or {})})
    for v in info["cat"]:
        if v in df.columns:
            recs.append({"variable":v, "type":"cat", **cat_info(df[v])})
    layers[L] = recs

# 因变量 / 控制变量（非层，实证所用）
DEP = ["ff5_adj_return","ff3_adj_return","ff4_adj_return","future_return","quarter_return","excess_return","log_aum"]
dep = []
for v in DEP:
    if v in df.columns:
        dep.append({"variable":v, **(stats(df[v]) or {})})

# 面板总体信息
_dcol = "report_date" if "report_date" in df.columns else ("date" if "date" in df.columns else None)
date_min = str(df[_dcol].min())[:10] if _dcol else "-"
date_max = str(df[_dcol].max())[:10] if _dcol else "-"
n_funds = int(df["fund_code"].nunique()) if "fund_code" in df.columns else "-"
# 季度数
if "year" in df.columns and "quarter" in df.columns:
    yq = df["year"].astype(str)+"Q"+df["quarter"].astype(str)
    n_quarters = int(yq.nunique())

panel_info = {"n_obs":N, "n_vars":df.shape[1], "n_funds":n_funds,
              "date_min":date_min, "date_max":date_max, "n_quarters":n_quarters}

out = {"panel":panel_info, "layers":layers, "dependent":dep,
       "generated":datetime.now().strftime("%Y-%m-%d %H:%M")}
with open(os.path.join(OUT,"framework_stats.json"),"w",encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)

# 控制台摘要
print("面板:", panel_info)
for L, recs in layers.items():
    print(f"\n=== {FRAMEWORK[L]['title']} ({FRAMEWORK[L]['sub']}) ===")
    for r in recs:
        if r["type"]=="num":
            print(f"  {r['variable']:18s} n={r['n']:5d} miss={r['missing_pct']:5.1f}% mean={r['mean']:.4f} std={r['std']:.4f} med={r['median']:.4f}")
        else:
            top=", ".join(f"{k}:{v}" for k,v in list(r.get('top',{}).items())[:4])
            print(f"  {r['variable']:18s} [分类] n={r['n']} 主要取值: {top}")
print("\n=== 因变量/控制 ===")
for r in dep:
    print(f"  {r['variable']:18s} n={r['n']:5d} miss={r['missing_pct']:5.1f}% mean={r['mean']:.4f} std={r['std']:.4f}")
print("\n>> framework_stats.json 已生成")
