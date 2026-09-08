# -*- coding: utf-8 -*-
"""修正：股价行情(真实列为 date/stock_code)、FF合并版(year/quarter)、宏观中文日期年份范围。"""
import pandas as pd, numpy as np, os, json, re

BASE = r"D:\Desktop\基金经理行为分析研究\数据"
OUT  = r"D:\Desktop\基金经理行为分析研究\描述性统计"

# ---- 股价行情 ----
sp = os.path.join(BASE,"股价行情","个股日行情_全量.csv")
uniq=set(); dmin=None; dmax=None; nrows=0
for ch in pd.read_csv(sp, usecols=["date","stock_code"], chunksize=1000000):
    nrows += len(ch)
    uniq.update(ch["stock_code"].dropna().unique())
    dd = pd.to_datetime(ch["date"], errors="coerce")
    cmin,cmax = dd.min(), dd.max()
    dmin = cmin if dmin is None else min(dmin,cmin)
    dmax = cmax if dmax is None else max(dmax,cmax)
stock = {"n_rows":nrows,"n_stocks":len(uniq),
         "date_min":str(dmin.date()) if pd.notna(dmin) else None,
         "date_max":str(dmax.date()) if pd.notna(dmax) else None}
spm = os.path.join(BASE,"股价行情","个股月收益率_全量.csv")
sm = pd.read_csv(spm)
stock["monthly_n_rows"]=len(sm)
stock["monthly_n_stocks"]=int(sm["stock_code"].nunique())
stock["monthly_date_min"]=str(pd.to_datetime(sm["date"],errors="coerce").min().date())
stock["monthly_date_max"]=str(pd.to_datetime(sm["date"],errors="coerce").max().date())
print("STOCK:",stock)

# ---- FF合并完整版(year/quarter) ----
ffp = os.path.join(BASE,"FF因子","FF因子_合并完整版.csv")
fd = pd.read_csv(ffp)
ff_merge = {"n_rows":len(fd),
            "year_min":int(fd["year"].min()),"year_max":int(fd["year"].max()),
            "quarter_min":int(fd["quarter"].min()),"quarter_max":int(fd["quarter"].max()),
            "cols":list(fd.columns)}
print("FF_MERGE:",ff_merge)

# ---- 宏观中文日期：提取年份范围 ----
mp = os.path.join(BASE,"宏观数据")
macro={}
for f in sorted(os.listdir(mp)):
    if not f.endswith(".csv"): continue
    d = pd.read_csv(os.path.join(mp,f), nrows=20000)
    rec={"n_cols":len(d.columns),"cols":list(d.columns)[:6],"n_periods":int(len(d))}
    years=[]
    for c in d.columns:
        if c in ("月份","季度","日期","TRADE_DATE","时间"):
            for v in d[c].dropna().astype(str):
                m=re.search(r"(19|20)\d{2}", v)
                if m: years.append(int(m.group()))
            break
    if years:
        rec["year_min"]=min(years); rec["year_max"]=max(years)
    if "日期" in d.columns:
        dd=pd.to_datetime(d["日期"],errors="coerce")
        if dd.notna().any():
            rec["date_min"]=str(dd.min().date()); rec["date_max"]=str(dd.max().date())
    macro[f]=rec
print("MACRO:")
for k,v in macro.items(): print("  ",k,v)

# ---- 更新 JSON ----
s=json.load(open(os.path.join(OUT,"descriptive_stats.json"),encoding="utf-8"))
s["stock_prices"]=stock
s["ff_factors"]["FF因子_合并完整版.csv"]=ff_merge
s["macro"]=macro
json.dump(s,open(os.path.join(OUT,"descriptive_stats.json"),"w",encoding="utf-8"),ensure_ascii=False,indent=2)
print(">> updated descriptive_stats.json")
