# -*- coding: utf-8 -*-
"""描述性统计 + 汇总图生成。
核心数据集：主分析面板(含L5三指标)、L5三文件、基金池、股价行情、宏观、FF因子、持仓。
"""
import pandas as pd, numpy as np, os, json
from pathlib import Path

BASE = r"D:\Desktop\基金经理行为分析研究\数据"
OUT  = r"D:\Desktop\基金经理行为分析研究\描述性统计"
os.makedirs(OUT, exist_ok=True)
stats = {}

def col_summary(s, name):
    s = pd.to_numeric(s, errors="coerce")
    return {
        "variable": name,
        "n": int(s.notna().sum()),
        "missing_pct": round(100 * s.isna().mean(), 2),
        "mean": round(float(s.mean()), 5) if s.notna().any() else None,
        "std": round(float(s.std()), 5) if s.notna().any() else None,
        "min": round(float(s.min()), 5) if s.notna().any() else None,
        "p25": round(float(s.quantile(.25)), 5) if s.notna().any() else None,
        "median": round(float(s.median()), 5) if s.notna().any() else None,
        "p75": round(float(s.quantile(.75)), 5) if s.notna().any() else None,
        "max": round(float(s.max()), 5) if s.notna().any() else None,
    }

# ---------- 1. 主分析面板 ----------
print(">> 主分析面板")
# 真实主分析面板（真算口径）。注意：此前读 数据/L4_风险应对层/主分析面板_修正版.csv，
# 该文件是用户要求"模拟对齐字段"的占位面板（=mvp_panel_v22），其 SDI/OCI/TO_calc 为模拟值，
# 已于 2026-08-14 审计确认并剔除模拟列，故改读经管线真算重建的最终面板。
p = os.path.join(os.path.dirname(BASE), "指标计算流水线", "output", "主分析面板_重建_含TOwind.csv")
df = pd.read_csv(p)
panel = {}
panel["n_obs"] = len(df)
panel["n_funds"] = int(df["fund_code"].nunique())
panel["date_min"] = str(df["report_date"].min())
panel["date_max"] = str(df["report_date"].max())
panel["n_years"] = int(df["year"].nunique())
panel["n_quarters"] = int(df.groupby(["year","quarter"]).ngroups)
# 按季度观测数（用于时间覆盖图）
df["yq"] = df["year"].astype(str) + "Q" + df["quarter"].astype(str)
qcount = df.groupby("yq").size()
panel["obs_per_quarter"] = {k: int(v) for k, v in qcount.items()}
panel["key_vars"] = []
for v in ["de","pgr","plr","lsv","risk_asym",
          "future_return","excess_return","quarter_return","ff5_adj_return",
          "log_aum","fund_age","manager_tenure","return_volatility","TO_two_sided",
          "family_size","industry_hhi","RG","AS","delta_AS"]:
    if v in df.columns:
        panel["key_vars"].append(col_summary(df[v], v))
stats["main_panel"] = panel
print("   观测=%d 基金=%d 时间=%s~%s" % (panel["n_obs"], panel["n_funds"], panel["date_min"], panel["date_max"]))

# ---------- 2. L5 三指标文件 ----------
print(">> L5 三指标")
l5 = {}
for tag, fn, var in [("DE","处置效应DE指标_修正版.csv","de"),
                     ("LSV","羊群行为LSV指标.csv","lsv"),
                     ("RA","风险偏好不对称RA指标.csv","risk_asym")]:
    fp = os.path.join(BASE,"L5_认知行为层",fn)
    d = pd.read_csv(fp)
    l5[tag] = {
        "file": fn, "n_rows": len(d), "n_funds": int(d["fund_code"].nunique()),
        "date_min": str(d["report_date"].min()), "date_max": str(d["report_date"].max()),
        "var_stats": col_summary(d[var], var),
    }
    if "pgr" in d.columns:
        l5[tag]["pgr"] = col_summary(d["pgr"],"pgr")
    if "plr" in d.columns:
        l5[tag]["plr"] = col_summary(d["plr"],"plr")
stats["L5"] = l5
print("   DE:%d行 LSV:%d行 RA:%d行" % (l5["DE"]["n_rows"], l5["LSV"]["n_rows"], l5["RA"]["n_rows"]))

# ---------- 3. 基金池 ----------
print(">> 基金池")
fp = os.path.join(BASE,"基金基础信息","全部基金列表_含清盘.csv")
fd = pd.read_csv(fp)
fund = {"n_total": len(fd), "by_type": {str(k): int(v) for k,v in fd["基金类型"].value_counts().items()}}
stats["fund_universe"] = fund
print("   总基金数=%d" % fund["n_total"])

# ---------- 4. 股价行情（大文件，仅读必要列） ----------
print(">> 股价行情")
sp = os.path.join(BASE,"股价行情","个股日行情_全量.csv")
n_stk=0; dmin=None; dmax=None; nrows=0
for chunk in pd.read_csv(sp, usecols=["ts_code","trade_date"], chunksize=500000):
    nrows += len(chunk)
    n_stk = chunk["ts_code"].nunique() if n_stk==0 else n_stk  # placeholder
    d = pd.to_datetime(chunk["trade_date"], format="%Y%m%d", errors="coerce")
    cmin, cmax = d.min(), d.max()
    dmin = cmin if dmin is None else min(dmin, cmin)
    dmax = cmax if dmax is None else max(dmax, cmax)
# 准确 unique 计数需全量去重
uniq = set()
for chunk in pd.read_csv(sp, usecols=["ts_code"], chunksize=1000000):
    uniq.update(chunk["ts_code"].dropna().unique())
stock = {"n_rows": nrows, "n_stocks": len(uniq),
         "date_min": str(dmin.date()), "date_max": str(dmax.date())}
spm = os.path.join(BASE,"股价行情","个股月收益率_全量.csv")
sm = pd.read_csv(spm)
stock["monthly_n_rows"]=len(sm); stock["monthly_n_stocks"]=int(sm["stock_code"].nunique())
stats["stock_prices"] = stock
print("   个股日行情:%d行 %d只 %s~%s" % (stock["n_rows"], stock["n_stocks"], stock["date_min"], stock["date_max"]))

# ---------- 5. 宏观数据 ----------
print(">> 宏观数据")
macro = {}
mp = os.path.join(BASE,"宏观数据")
for f in sorted(os.listdir(mp)):
    if not f.endswith(".csv"): continue
    d = pd.read_csv(os.path.join(mp,f), nrows=10000)
    # 找日期列
    datecol = None
    for c in d.columns:
        if "季度" in c or "日期" in c or "时间" in c or c.lower() in ("date","year","月份"):
            datecol=c; break
    rec = {"n_cols": len(d.columns), "cols": list(d.columns)[:6]}
    if datecol:
        try:
            dd = pd.to_datetime(d[datecol], errors="coerce")
            rec["date_min"]=str(dd.min()); rec["date_max"]=str(dd.max())
            rec["n_periods"]=int(d[datecol].notna().sum())
        except Exception:
            pass
    macro[f]=rec
stats["macro"] = macro

# ---------- 6. FF因子 ----------
print(">> FF因子")
ffp = os.path.join(BASE,"FF因子")
ff = {}
for f in ["FF5日度因子.csv","FF5月度因子.csv","FF因子_合并完整版.csv"]:
    d = pd.read_csv(os.path.join(ffp,f))
    datecol = "date" if "date" in d.columns else d.columns[0]
    try:
        dd = pd.to_datetime(d[datecol], errors="coerce")
        ff[f]={"n_rows":len(d),"date_min":str(dd.min().date()),"date_max":str(dd.max().date()),"cols":list(d.columns)}
    except Exception as e:
        ff[f]={"n_rows":len(d),"err":str(e)}
stats["ff_factors"] = ff

# ---------- 7. 持仓数据 ----------
print(">> 持仓")
hp = os.path.join(BASE,"L2_持仓偏离层","基金持仓明细_全量修正版.csv")
hd = pd.read_csv(hp)
hold = {"n_rows":len(hd),"n_funds":int(hd["fund_code"].nunique()),
        "n_stocks":int(hd["stock_code"].nunique()),
        "date_min":str(hd["report_date"].min()),"date_max":str(hd["report_date"].max())}
hc = os.path.join(BASE,"L3_交易行为层","基金持仓变动_批量.csv")
hcd = pd.read_csv(hc)
hold["change_n_rows"]=len(hcd)
stats["holdings"] = hold
print("   持仓明细:%d行 %d基金 %d股票" % (hold["n_rows"],hold["n_funds"],hold["n_stocks"]))

# 保存 JSON
with open(os.path.join(OUT,"descriptive_stats.json"),"w",encoding="utf-8") as f:
    json.dump(stats,f,ensure_ascii=False,indent=2)
print("\n>> 已保存 descriptive_stats.json")

# 供绘图脚本使用
import pickle
with open(os.path.join(OUT,"_stats.pkl"),"wb") as f:
    pickle.dump({"panel":panel,"l5":l5,"fund":fund,"stock":stock,"macro":macro,"ff":ff,"hold":hold},f)
print(">> 统计计算完成")
