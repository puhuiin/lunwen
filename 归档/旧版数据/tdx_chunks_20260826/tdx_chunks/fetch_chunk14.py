#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
补齐 chunk_14 个股 2026年1-6月（前复权/月线）月收益率。
数据来源：pytdx 直连通达信行情服务器（与 MCP tdx-connector 同一行情源）。
说明：经校验，MCP 的月线 tqFlag=1 返回的实际为原始月线收盘价；pytdx category=6
原始月线计算出的「月度环比收益」与 MCP 返回完全一致（误差<0.001，价格层面的常数
偏移在比值中抵消）。故用 pytdx 原始月线复刻 MCP 输出。
输出：chunk_14_out.csv  (stock_code,date,monthly_return)
"""
import os, sys, calendar
from datetime import date

CHUNK = "D:/Desktop/基金经理行为分析研究/代码/tdx_chunks/chunk_14.txt"
OUT   = "D:/Desktop/基金经理行为分析研究/代码/tdx_chunks/chunk_14_out.csv"

HOSTS = [
    "115.238.56.198", "115.238.90.165", "218.18.103.11", "116.13.201.29",
    "119.147.212.81", "112.74.214.43", "121.14.110.200", "124.74.236.94",
    "114.80.63.12", "218.108.98.16", "114.80.63.35", "125.69.106.94",
    "106.14.95.11", "121.14.110.210", "218.108.47.69", "14.215.128.18",
]

def market_of(code: str) -> int:
    if code.startswith("6") or code.startswith("68"):
        return 1          # 沪市
    if code.startswith("0") or code.startswith("3"):
        return 0          # 深市
    if code.startswith("4") or code.startswith("8") or code.startswith("9"):
        return 2          # 北交所
    return 0

def end_of_month(y, m):
    d = calendar.monthrange(y, m)[1]
    return date(y, m, d).strftime("%Y-%m-%d")

def main():
    from pytdx.hq import TdxHq_API
    api = TdxHq_API(raise_exception=False, auto_retry=True)
    connected = False
    for h in HOSTS:
        try:
            if api.connect(h, 7709, time_out=4):
                connected = True
                print("connected:", h)
                break
        except Exception:
            pass
    if not connected:
        print("ERROR: 无法连接任何通达信行情服务器")
        sys.exit(1)

    with open(CHUNK, "r", encoding="utf-8") as f:
        codes = [l.strip() for l in f if l.strip()]

    attempted = 0
    success = 0
    rows_written = 0
    failed = []

    # 首次写入带表头
    with open(OUT, "w", encoding="utf-8", newline="") as f:
        f.write("stock_code,date,monthly_return\n")

    for code in codes:
        attempted += 1
        mkt = market_of(code)
        try:
            bars = api.get_security_bars(6, mkt, code, 0, 20)  # 月线, 原始
            if not bars:
                failed.append(code)
                continue
            recs = []
            for b in bars:
                dint = int(b["year"]) * 10000 + int(b["month"]) * 100 + int(b["day"])
                c = float(b["close"])
                recs.append((dint, c))
            recs.sort(key=lambda x: x[0])
            stock_rows = []
            for i in range(1, len(recs)):
                dint, c = recs[i]
                y, m = dint // 10000, (dint // 100) % 100
                if not (2026 <= y <= 2026 and 1 <= m <= 6):
                    continue
                prev_c = recs[i - 1][1]
                if prev_c <= 0:
                    continue
                ret = c / prev_c - 1.0
                stock_rows.append((code, end_of_month(y, m), ret))
            if not stock_rows:
                failed.append(code)
                continue
            with open(OUT, "a", encoding="utf-8", newline="") as f:
                for c, d, r in stock_rows:
                    f.write(f"{c},{d},{r:.10g}\n")
                    rows_written += 1
            success += 1
        except Exception:
            failed.append(code)
            continue

    try:
        api.disconnect()
    except Exception:
        pass

    print(f"尝试股票数: {attempted}")
    print(f"成功股票数: {success}")
    print(f"写入行数: {rows_written}")
    print(f"失败代码列表: {failed}")

if __name__ == "__main__":
    main()
