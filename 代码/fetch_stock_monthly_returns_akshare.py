# -*- coding: utf-8 -*-
"""
免费修复脚本（重写版）：用 akshare 的【新浪源】拉取个股月收益率，扩展 ARG/DE 的收益覆盖。

为什么重写：
  原脚本用 ak.stock_zh_a_hist（东方财富源），在本环境被网络封锁（RemoteDisconnected）。
  改用 ak.stock_zh_a_daily（新浪源，已验证可用，~0.9s/只），同样免费、无需 token。

输出落点（关键）：
  直接写流水线 calc_arg / calc_de 真正读取的文件：
    指标计算流水线/data/股价行情/个股月收益率_全量.csv
  （calc_arg 内 D("股价行情","个股月收益率_全量.csv") 指向此路径，旧版仅 76 只）。
  同时同步一份到 数据/股价行情/ 副本，保持一致。

口径：
  - adjust='qfq' 前复权，月收益 = 月内最后交易日收盘价 / 上月最后交易日收盘价 − 1。
  - 区间 2016-01 → 2026-01（覆盖 ARG 窗口 2018Q1–2025Q4 并留足 base month）。
  - 只拉持仓里出现过的股票（FILTER_TO_HOLDINGS），约 4500+ 只，足够覆盖 ARG。

健壮性：
  - 断点续传：已写入的股票记录在 *.done.txt，重启自动跳过。
  - 每 25 只检查点落盘，长任务中断不丢已完成数据。
  - 单只失败（如港股/北交所等新浪无覆盖）记录到 *.failed.txt 并跳过，不中断整体。

用法（需联网 + 安装 akshare；务必清除代理以避免代理掐断新浪）：
  pip install akshare
  env -u HTTP_PROXY -u HTTPS_PROXY -u http_proxy -u https_proxy python fetch_stock_monthly_returns_akshare.py
"""
import os
import time
import akshare as ak
import pandas as pd

HOLDINGS = r"D:\Desktop\基金经理行为分析研究\数据\L2_持仓偏离层\基金持仓明细_全量修正版.csv"
# 流水线 calc_arg/calc_de 实际读取的 canonical 路径
OUT = r"D:\Desktop\基金经理行为分析研究\指标计算流水线\data\股价行情\个股月收益率_全量.csv"
# 同步副本
OUT2 = r"D:\Desktop\基金经理行为分析研究\数据\股价行情\个股月收益率_全量.csv"
DONE = OUT + ".done.txt"
FAILED = OUT + ".failed.txt"
START, END = "20160101", "20260101"
CHK = 25


def get_codes():
    h = pd.read_csv(HOLDINGS, encoding="utf-8-sig", usecols=["stock_code"])
    return sorted(set(h["stock_code"].astype(str).str.zfill(6)))


def fetch_one(code):
    sym = ("sh" if code.startswith("6") else "sz") + code
    df = ak.stock_zh_a_daily(symbol=sym, start_date=START, end_date=END, adjust="qfq")
    if df is None or df.empty:
        return []
    df = df[["date", "close"]].copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna().sort_values("date")
    df["month"] = df["date"].dt.to_period("M")
    me = df.groupby("month")["close"].last()          # 每月最后交易日收盘价
    ret = me.pct_change().dropna()                     # 月收益 = 本月/上月 − 1
    rows = []
    for p, r in ret.items():
        if not pd.isna(r):
            # 用月末日期（calc_arg 只取 month，具体日不重要）
            rows.append((code, p.to_timestamp(how="end").strftime("%Y-%m-%d"), float(r)))
    return rows


def main():
    # 首次运行备份原文件
    if not os.path.exists(DONE) and os.path.exists(OUT):
        try:
            os.replace(OUT, OUT + ".bak")
            print("已备份原文件 ->", OUT + ".bak")
        except Exception:
            pass

    attempted = set()
    for pf in (DONE, FAILED):
        if os.path.exists(pf):
            with open(pf, encoding="utf-8") as f:
                attempted |= {l.strip() for l in f if l.strip()}

    # 已落盘的股票也算 attempted（restart 安全）
    base_rows = []
    if os.path.exists(OUT):
        b = pd.read_csv(OUT, encoding="utf-8-sig")
        b["stock_code"] = b["stock_code"].astype(str).str.zfill(6)
        attempted |= set(b["stock_code"].tolist())
        base_rows = list(zip(b["stock_code"].astype(str),
                             b["date"].astype(str),
                             b["monthly_return"].astype(float)))

    codes = [c for c in get_codes() if c not in attempted]
    print(f"持仓股总数去重: {len(get_codes())}  待抓取: {len(codes)}  已完成: {len(attempted)}")

    new_rows, fail = [], []
    dfp_done = open(DONE, "a", encoding="utf-8")
    dfp_fail = open(FAILED, "a", encoding="utf-8")

    for i, code in enumerate(codes):
        ok = False
        for attempt in range(4):
            try:
                rows = fetch_one(code)
                if rows:
                    new_rows.extend(rows)
                ok = True
                break
            except Exception:
                time.sleep(0.4 * (attempt + 1))
        if ok:
            dfp_done.write(code + "\n"); dfp_done.flush()
        else:
            fail.append(code); dfp_fail.write(code + "\n"); dfp_fail.flush()
        if (i + 1) % CHK == 0:
            out = pd.DataFrame(base_rows + new_rows,
                               columns=["stock_code", "date", "monthly_return"])
            out.to_csv(OUT, index=False, encoding="utf-8-sig")
            print(f"  进度 {i+1}/{len(codes)} 累计行 {len(out)} "
                  f"覆盖股 {out['stock_code'].nunique()} 失败 {len(fail)}")

    # 末次写出
    out = pd.DataFrame(base_rows + new_rows,
                       columns=["stock_code", "date", "monthly_return"])
    out.to_csv(OUT, index=False, encoding="utf-8-sig")
    # 同步副本
    try:
        out.to_csv(OUT2, index=False, encoding="utf-8-sig")
    except Exception:
        pass
    dfp_done.close(); dfp_fail.close()

    print("写出:", OUT, out.shape)
    print("覆盖股票数:", out["stock_code"].nunique(),
          " 时间范围:", out["date"].min(), "→", out["date"].max())
    print("本次失败(多为港股/北交所等新浪无覆盖):", len(fail))


if __name__ == "__main__":
    main()
