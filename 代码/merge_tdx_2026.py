# -*- coding: utf-8 -*-
"""
合并 16 个子代理经 tdx 月线补抓的 2026 月收益分块 CSV，追加到两份个股月收益主文件。

输入：代码/tdx_chunks/chunk_XX_out.csv  （列：stock_code,date,monthly_return；date=实际月末 YYYY-MM-DD）
输出（仅追加、不改动既有行）：
  数据/股价行情/个股月收益率_全量.csv
  指标计算流水线/data/股价行情/个股月收益率_全量.csv

安全规则（防未来泄漏 + 防重复）：
  - 仅接受 date ∈ [2026-01-31, 2026-06-30] 的行（上游子代理已过滤，这里再卡一道）。
  - 按 (stock_code, date) 去重；若主文件已有该 (code,date) 则跳过（幂等，可重复运行）。
  - 绝对不写入 2026-07 及以后任何月份。
"""
import os
import glob
import pandas as pd

BASE = r"D:\Desktop\基金经理行为分析研究"
CHUNK_DIR = os.path.join(BASE, "代码", "tdx_chunks")
OUT1 = os.path.join(BASE, "数据", "股价行情", "个股月收益率_全量.csv")
OUT2 = os.path.join(BASE, "指标计算流水线", "data", "股价行情", "个股月收益率_全量.csv")
LO = pd.Timestamp("2026-01-31")
HI = pd.Timestamp("2026-06-30")


def main():
    files = sorted(glob.glob(os.path.join(CHUNK_DIR, "chunk_*_out*.csv")))
    print("分块文件数:", len(files))
    parts = []
    for f in files:
        if os.path.getsize(f) == 0:
            continue
        df = pd.read_csv(f, encoding="utf-8-sig")
        if "stock_code" not in df.columns:
            continue
        parts.append(df)
    if not parts:
        print("没有可用分块数据，退出。"); return
    new = pd.concat(parts, ignore_index=True)
    new["stock_code"] = new["stock_code"].astype(str).str.zfill(6)
    new["date"] = pd.to_datetime(new["date"], errors="coerce")
    new = new.dropna(subset=["date"])
    # 严格窗口卡控
    new = new[(new["date"] >= LO) & (new["date"] <= HI)]
    new["date"] = new["date"].dt.strftime("%Y-%m-%d")
    new = new[["stock_code", "date", "monthly_return"]].drop_duplicates(
        subset=["stock_code", "date"]).sort_values(["stock_code", "date"])
    print("待追加 2026 月收益行数:", len(new),
          " 覆盖股票:", new["stock_code"].nunique(),
          " 月份:", sorted(new["date"].unique()))

    for out in (OUT1, OUT2):
        base = pd.read_csv(out, encoding="utf-8-sig")
        base["stock_code"] = base["stock_code"].astype(str).str.zfill(6)
        base["date"] = base["date"].astype(str)
        have = set(zip(base["stock_code"], base["date"]))
        add = new[~new.apply(lambda r: (r["stock_code"], r["date"]) in have, axis=1)]
        merged = pd.concat([base, add], ignore_index=True)
        merged.to_csv(out, index=False, encoding="utf-8-sig")
        print(f"写出 {out}  原 {len(base)} 行 + 新增 {len(add)} = {len(merged)} 行")
    print("完成。")


if __name__ == "__main__":
    main()
