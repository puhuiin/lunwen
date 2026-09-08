import pandas as pd, os, numpy as np
DATA = r"D:\Desktop\基金经理行为分析研究\数据"
def tryp(path, **kw):
    for e in ("utf-8-sig","utf-8","gbk"):
        try: return pd.read_csv(path, encoding=e, **kw)
        except: pass
    return pd.read_csv(path, **kw)

# 〔2026-08-14 治理〕主分析面板_修正版.csv（模拟占位）已删除，改读真实重建面板做对照。
_pan_src = os.path.join(DATA,"L4_风险应对层","主分析面板_修正版.csv")
_REB = os.path.join(os.path.dirname(DATA), "指标计算流水线", "output", "主分析面板_重建.csv")
if os.path.exists(_pan_src):
    pan = tryp(_pan_src, low_memory=False)
else:
    pan = tryp(_REB, low_memory=False)
print("面板全部列(含日期类):")
datecols=[c for c in pan.columns if any(k in c.lower() for k in ["date","period","year","quarter","time","ym","月","期"])]
print(datecols)
# 看这些列的样例
for c in datecols[:6]:
    print(f"  {c} 样例:", pan[c].dropna().unique()[:6])

de = tryp(os.path.join(DATA,"L5_认知行为层","处置效应DE指标_修正版.csv"), low_memory=False)
# 构造 half key
de["half"] = np.where(de["report_date"].astype(str).str[5:7]=="06","H1","H2")
de["yh"] = de["report_date"].astype(str).str[:4] + de["half"]

# 面板：找 year/quarter 列
yc = [c for c in pan.columns if c.lower() in ("year","quarter") or "year" in c.lower() or "quarter" in c.lower()]
print("\n面板 year/quarter 列:", yc)
if len(yc)>=2:
    ycol,qcol = yc[0], yc[1]
    # quarter 可能是 2018Q2 或 1-4
    qv = pan[qcol].astype(str).str.replace("Q","",case=False)
    pan["half"] = np.where(qv.isin(["2","Q2","2.0"]),"H1", np.where(qv.isin(["4","Q4","4.0"]),"H2", "X"))
    pan["yh"] = pan[ycol].astype(str)+pan["half"]
    sub = pan[pan["half"].isin(["H1","H2"])].copy()
    m = sub.merge(de[["fund_code","yh","de","pgr","plr"]], on=["fund_code","yh"], how="left", suffixes=("_pan","_de"))
    print("\n对齐后可比样本:", len(m), " 其中匹配到DE:", m["de_de"].notna().sum())
    both = m.dropna(subset=["de_de"])
    print("面板de vs l5_de 相关性:", both["de_pan"].corr(both["de_de"]))
    print("面板pgr vs l5_de pgr 相关性:", both["pgr_pan"].corr(both["pgr_de"]))
    print("\n差异均值(面板-修正): de=", (both["de_pan"]-both["de_de"]).mean(),
          " pgr=", (both["pgr_pan"]-both["pgr_de"]).mean(),
          " plr=", (both["plr_pan"]-both["plr_de"]).mean())
    print("样本面板de均值=", both["de_pan"].mean(), " 修正de均值=", both["de_de"].mean())
    print("样本面板pgr均值=", both["pgr_pan"].mean(), " 修正pgr均值=", both["pgr_de"].mean())
else:
    print("未找到 year/quarter 列，无法对齐。面板列总数:", len(pan.columns))
