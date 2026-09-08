# -*- coding: utf-8 -*-
"""
直接抓取【全 A 股个股月收益率】的等价实现（绕过 akshare 客户端，直连东方财富 kline）。
与 fetch_stock_monthly_returns_akshare.py 产出完全相同的文件与 schema，用于救 ARG 的 108 只股票覆盖限制。

为什么不用 akshare：
  本沙箱环境 akshare 的 requests 会话会被远端中断（RemoteDisconnected），但东方财富
  push2his.eastmoney.com 的 kline 接口在带 UA/Referer 时可直接访问。故这里直接用 urllib 拉，
  结果一致。

口径：
  - klt=103 月度；fqt=1 前复权（收益计算的标准选择，避免除权跳空）。
  - monthly_return = 复权收盘 的逐月环比涨跌幅；首月无前置价，丢弃。
  - 默认只抓【持仓里出现过的股票】（直接服务于 ARG），数量约 4500+，远小于全市场。
  - 运行前务必清除代理：env -u HTTP_PROXY -u HTTPS_PROXY -u http_proxy -u https_proxy python ...

用法：
  python fetch_stock_monthly_returns_em.py            # 全量（持仓股）
  python fetch_stock_monthly_returns_em.py 50         # 仅前 50 只（冒烟测试）

输出：数据/L4_风险应对层/个股月收益率_全量_v2.csv
      列：stock_code, date, monthly_return  （与 lib_metrics.calc_arg 读取 schema 一致）
"""
import os
import sys
import time
import json
import urllib.request
import pandas as pd

OUT = r"D:\Desktop\基金经理行为分析研究\数据\L4_风险应对层\个股月收益率_全量_v2.csv"
HOLDINGS = r"D:\Desktop\基金经理行为分析研究\数据\L2_持仓偏离层\基金持仓明细_全量修正版.csv"
BEG, END = "20060101", "20261231"


def get_codes():
    h = pd.read_csv(HOLDINGS, encoding="utf-8-sig", usecols=["stock_code"])
    return sorted(set(h["stock_code"].astype(str).str.zfill(6)))


def secid(code):
    # 6 开头为上交所(market=1)，其余(0/3 开头)为深交所(market=0)
    return ("1." if code.startswith("6") else "0.") + code


def fetch_one(code):
    url = ("https://push2his.eastmoney.com/api/qt/stock/kline/get?"
           "fields1=f1,f2,f3,f4,f5,f6&fields2=f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61"
           f"&klt=103&fqt=1&secid={secid(code)}&beg={BEG}&end={END}")
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0", "Referer": "https://quote.eastmoney.com/"})
    with urllib.request.urlopen(req, timeout=10) as r:
        js = json.loads(r.read().decode("utf-8", "ignore"))
    d = js.get("data")
    if not d or not d.get("klines"):
        return None
    rows, prev = [], None
    for kl in d["klines"]:
        p = kl.split(",")
        close = float(p[2])
        if prev is not None and prev > 0:
            rows.append((code, p[0], close / prev - 1.0))
        prev = close
    return rows


def main():
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else None
    codes = get_codes()
    if limit:
        codes = codes[:limit]
    print("待抓取持仓股票数:", len(codes))
    allrows, fail = [], 0
    for i, code in enumerate(codes):
        ok = False
        for attempt in range(8):
            try:
                rows = fetch_one(code)
                if rows:
                    allrows.extend(rows)
                    ok = True
                break
            except Exception:
                time.sleep(0.5 * (attempt + 1))
        if not ok:
            fail += 1
        else:
            time.sleep(0.05)  # 轻微限速，降低瞬时断连
        if (i + 1) % 200 == 0:
            print(f"  进度 {i+1}/{len(codes)} 已得 {len(allrows)} 行, 失败 {fail}")
            # 检查点落盘，避免长任务中断丢数据（仅每 200 只写一次）
            pd.DataFrame(allrows, columns=["stock_code", "date", "monthly_return"]).to_csv(
                OUT, index=False, encoding="utf-8-sig")
    out = pd.DataFrame(allrows, columns=["stock_code", "date", "monthly_return"])
    out.to_csv(OUT, index=False, encoding="utf-8-sig")
    print("写出:", OUT, out.shape, " 覆盖股票:", out["stock_code"].nunique(), " 失败:", fail)


if __name__ == "__main__":
    main()
