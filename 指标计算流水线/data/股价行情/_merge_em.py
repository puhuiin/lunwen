# -*- coding: utf-8 -*-
"""把 em_parsed 下已下载的 q1~q4 月收盘价合并进主表 个股月收益率_全量.csv。
格式转换: 年-月 -> 月末日期; 收盘价序列 -> pct_change 月收益。
upsert: 按 stock_code+date 覆盖已有、追加新行。输出覆盖统计与剩余缺口。
"""
import os, glob, calendar
import pandas as pd

EM = r"d:\Desktop\基金经理行为分析研究\指标计算流水线\data\股价行情\em_parsed"
BASE = r"d:\Desktop\基金经理行为分析研究\指标计算流水线\data\股价行情"
MRET = os.path.join(BASE, "个股月收益率_全量.csv")

def ym_to_monthend(ym):
    y, m = int(ym[:4]), int(ym[5:7])
    return f"{ym}-{calendar.monthrange(y, m)[1]:02d}"

# 1) 读取所有 q1~q4 批次 CSV
frames = []
for f in glob.glob(os.path.join(EM, "q?_b*.csv")):
    try:
        df = pd.read_csv(f, names=["code", "ym", "close"], dtype={"code": str})
        df["close"] = pd.to_numeric(df["close"], errors="coerce")
        df = df.dropna(subset=["close"])
        df["src"] = os.path.basename(f)
        frames.append(df)
    except Exception as e:
        print("skip", f, e)
if not frames:
    print("无数据"); raise SystemExit
allc = pd.concat(frames, ignore_index=True)
allc["code"] = allc["code"].str.zfill(6)
print("解析CSV总行数:", len(allc), "涉及股票数:", allc["code"].nunique())

# 2) 每只股票: 按年-月排序(去重), 计算月收益
allc = allc.sort_values(["code", "ym"]).drop_duplicates(["code", "ym"], keep="last")
allc["date"] = allc["ym"].map(ym_to_monthend)
allc["ret"] = allc.groupby("code")["close"].pct_change()
out = allc[["code", "date", "ret"]].dropna(subset=["ret"]).copy()
out.columns = ["stock_code", "date", "monthly_return"]
print("合并后月收益行数:", len(out), "股票数:", out["stock_code"].nunique())

# 3) 读主表
mast = pd.read_csv(MRET, encoding="utf-8-sig", dtype={"stock_code": str})
mast = mast.copy()
mast["stock_code"] = mast["stock_code"].astype(str).str.zfill(6)
print("主表原有行数:", len(mast), "股票数:", mast["stock_code"].nunique())

# 4) upsert 合并
mast_idx = set(zip(mast["stock_code"], mast["date"]))
new_rows = out[~out.apply(lambda r: (r["stock_code"], r["date"]) in mast_idx, axis=1)]
print("将新增行数:", len(new_rows), "将覆盖行数:", len(out) - len(new_rows))
merged = pd.concat([mast, new_rows], ignore_index=True)
merged = merged.sort_values(["stock_code", "date"]).drop_duplicates(
    ["stock_code", "date"], keep="last")
merged.to_csv(MRET, index=False, encoding="utf-8-sig")
print("写出主表完成, 新主表行数:", len(merged), "股票数:", merged["stock_code"].nunique())

# 5) 覆盖率 vs 持仓v3
HOLD = os.path.join(BASE, "..", "L2_持仓偏离层", "基金持仓明细_全量修正版_v3.csv")
h = pd.read_csv(HOLD, encoding="utf-8-sig", dtype={"stock_code": str})
h["stock_code"] = h["stock_code"].str.zfill(6)
hold_codes = set(h["stock_code"].dropna())
have = set(merged["stock_code"].dropna())
missing = hold_codes - have
VALID = ('000','001','002','003','300','301','400','420','430',
         '600','601','603','605','688','689',
         '830','831','832','833','834','835','836','837','838','839',
         '870','871','872','873','920')
a_missing = sorted(c for c in missing if c.startswith(VALID))
print("\n持仓v3股票数:", len(hold_codes))
print("主表已有股票数:", len(have))
print("仍缺月收益股票数:", len(missing), "其中A股/北交:", len(a_missing))
open(os.path.join(BASE, "_missing_a_stocks.txt"), "w", encoding="utf-8").write("\n".join(a_missing))
print("剩余缺失A股清单已写 _missing_a_stocks.txt:", len(a_missing))