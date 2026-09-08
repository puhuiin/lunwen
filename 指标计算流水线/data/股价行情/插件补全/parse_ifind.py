# -*- coding: utf-8 -*-
"""解析 iFinD get_stock_performance 导出的月涨跌幅 CSV，转为标准 monthly_return 格式。
ifind 的月涨跌幅会在当月每个交易日广播同一值，故按 (证券代码, 年月) 去重取月末。
"""
import os, sys, glob
import pandas as pd

RAW_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "task1_raw")
OUT_CSV = os.path.join(os.path.dirname(os.path.abspath(__file__)), "task1_monthly.csv")

def parse_one(path):
    try:
        df = pd.read_csv(path, encoding="utf-8-sig", dtype={"证券代码": str})
    except Exception:
        return None
    if df is None or df.empty:
        return None
    # 列名统一
    df.columns = [c.strip() for c in df.columns]
    code_col = "证券代码" if "证券代码" in df.columns else df.columns[0]
    date_col = "日期" if "日期" in df.columns else "date"
    val_col = None
    for c in df.columns:
        if "月涨跌幅" in c or "涨跌幅" in c or "收益率" in c:
            val_col = c
            break
    if val_col is None:
        return None
    df = df[[code_col, date_col, val_col]].copy()
    df.columns = ["stock_code", "date", "monthly_return"]
    # 去空值(\t / 空串)
    df["monthly_return"] = pd.to_numeric(df["monthly_return"], errors="coerce")
    df = df.dropna(subset=["monthly_return"])
    df = df[df["monthly_return"] != 0.0]  # 0.0 常为停牌占位，剔除避免污染
    if df.empty:
        return None
    # 标准化代码
    df["stock_code"] = df["stock_code"].str.extract(r"(\d{6})")[0]
    # 日期转标准
    df["date"] = pd.to_datetime(df["date"].astype(str), format="%Y%m%d", errors="coerce")
    df = df.dropna(subset=["date"])
    df["ym"] = df["date"].dt.strftime("%Y-%m")
    # 每 (stock, ym) 取月末最后一值
    out = df.sort_values("date").groupby(["stock_code", "ym"], as_index=False).tail(1)
    out = out[["stock_code", "ym", "monthly_return"]].copy()
    out.columns = ["stock_code", "date", "monthly_return"]
    out["date"] = pd.to_datetime(out["date"]).dt.strftime("%Y-%m-%d")
    # 转小数(ifind 为 %)
    out["monthly_return"] = out["monthly_return"] / 100.0
    return out

def main():
    files = sorted(glob.glob(os.path.join(RAW_DIR, "*.csv")))
    if not files:
        print("no raw csv found in", RAW_DIR)
        return
    frames = []
    for p in files:
        code = os.path.basename(p).replace(".csv", "")
        d = parse_one(p)
        if d is not None:
            frames.append(d)
        else:
            print("parse fail:", code)
    if frames:
        all_df = pd.concat(frames, ignore_index=True)
        all_df = all_df.drop_duplicates(subset=["stock_code", "date"], keep="last")
        all_df.to_csv(OUT_CSV, index=False, encoding="utf-8-sig")
        print(f"saved {len(all_df)} rows -> {OUT_CSV}")
        print("stocks covered:", all_df["stock_code"].nunique())
        # 缺失月份统计
        ymd = all_df.loc[all_df["stock_code"].eq("000004"), "date"].tolist() if "000004" in set(all_df["stock_code"]) else []
        print("sample 000004 rows:", len(ymd))
    else:
        print("no parsed data")

if __name__ == "__main__":
    main()