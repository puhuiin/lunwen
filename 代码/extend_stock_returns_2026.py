# -*- coding: utf-8 -*-
"""
靶向补抓 2026 年个股月收益率（仅补 2026-01 ~ 2026-06），用于补齐面板 2026Q1/Q2 的
RG 收益覆盖（原 个股月收益率_全量.csv 仅到 2025-12-31，导致 2026 年 RG 为 NaN）。

为什么重写（2026-08-13）：
  上一版用 akshare 新浪源 ak.stock_zh_a_daily，在本环境返回空数据（fetch 不抛异常、
  只返回空列表），9 分钟空转、0 条有效数据。本版改用 ak.stock_zh_a_hist（东方财富日线，
  实测可用），取日线 → 重采样到月末收盘 → close-to-close 环比，与现有 个股月收益率_全量.csv
  口径（monthly_return = 月末收盘环比；date = 月末 YYYY-MM-DD）一致。

口径与边界（严格防未来泄漏）：
  - 仅抓取「最新可用持仓快照（= 2025-12-31）里出现的股票」——这些才是 RG 在 2026Q1/Q2
    实际用到的权重股票（2026 快照缺失，最近快照即 2025Q4），避免无谓全市场抓取。
  - 日线窗口 START=2025-12-01 ~ END=2026-07-01：含 2025-12 收盘做基准，截到 2026-06 收盘。
  - 仅追加 date ∈ [2026-01-31, 2026-06-30] 的行；绝不写入 2026-07 及以后（未来）。
  - 个股季度收益在 06_因变量.py 由月收益 (1+r) 连乘得到，故月收益口径必须一致。

做法：
  - 读现有 个股月收益率_全量.csv，记录已存在的 (stock_code, date) 防重复。
  - 断点续传：已成功补到 2026 月的股票记入 .done2026.txt，重启跳过（启动前若发现旧标记
    对应 0 条 2026 数据，应手动删掉该文件再跑）。
  - 同步写流水线 data/ 与 数据/ 两份副本。

用法（需联网、清除代理）：
  env -u HTTP_PROXY -u HTTPS_PROXY -u http_proxy -u https_proxy \\
      python extend_stock_returns_2026.py
"""
import os
import time
import akshare as ak
import pandas as pd

HOLDINGS = r"D:\Desktop\基金经理行为分析研究\数据\L2_持仓偏离层\基金持仓明细_全量修正版.csv"
OUT = r"D:\Desktop\基金经理行为分析研究\指标计算流水线\data\股价行情\个股月收益率_全量.csv"
OUT2 = r"D:\Desktop\基金经理行为分析研究\数据\股价行情\个股月收益率_全量.csv"
DONE = OUT + ".done2026.txt"
START, END = "20251201", "20260701"   # 日线窗口：含2025-12做基准，截到2026-06收盘
CHK = 50
# 仅补 2026-01 ~ 2026-06（严格上限，未来季度绝不写入）
APPEND_FROM = pd.Timestamp("2026-01-01")
APPEND_THRU = pd.Timestamp("2026-06-30")


def get_codes():
    """最新可用持仓快照（最大 report_date）里出现的股票（RG 在 2026 实际用到的权重股）。"""
    h = pd.read_csv(HOLDINGS, encoding="utf-8-sig", low_memory=False)
    h["report_date"] = pd.to_datetime(h["report_date"], errors="coerce")
    mx = h["report_date"].max()
    last = h[h["report_date"] == mx]
    return sorted(set(last["stock_code"].astype(str).str.zfill(6)))


def fetch_2026(code):
    """取日线 → 月末收盘 → close-to-close 环比；仅返回 2026-01..06 的 (code, month_end, ret)。"""
    df = ak.stock_zh_a_hist(symbol=code, period="daily",
                            start_date=START, end_date=END, adjust="qfq")
    if df is None or df.empty:
        return []
    df["日期"] = pd.to_datetime(df["日期"], errors="coerce")
    df = df.dropna(subset=["日期"]).sort_values("日期")
    if df.empty:
        return []
    df["month"] = df["日期"].dt.to_period("M")
    me = df.groupby("month")["收盘"].last()        # 月末收盘
    ret = me.pct_change().dropna()
    rows = []
    for p, r in ret.items():
        d = p.to_timestamp(how="end")
        if APPEND_FROM <= d <= APPEND_THRU and not pd.isna(r):
            rows.append((code, d.strftime("%Y-%m-%d"), float(r)))
    return rows


def main():
    if os.path.exists(DONE):
        done = {l.strip() for l in open(DONE, encoding="utf-8") if l.strip()}
    else:
        done = set()

    base = pd.read_csv(OUT, encoding="utf-8-sig")
    base["stock_code"] = base["stock_code"].astype(str).str.zfill(6)
    base["date"] = base["date"].astype(str)
    have = set(zip(base["stock_code"], base["date"]))   # 已存在行，防止重复

    codes = [c for c in get_codes() if c not in done]
    print(f"目标快照股票总数: {len(get_codes())}  待补2026: {len(codes)}  已完成: {len(done)}")

    new_rows = []
    dfp = open(DONE, "a", encoding="utf-8")
    fail = 0
    for i, code in enumerate(codes):
        ok = False
        rows = None
        for attempt in range(4):
            try:
                rows = fetch_2026(code)
                ok = True
                break
            except Exception:
                time.sleep(0.4 * (attempt + 1))
        if ok:
            for r in rows:
                if r not in have:
                    new_rows.append(r)
                    have.add(r)
            dfp.write(code + "\n")
            dfp.flush()
        else:
            fail += 1
        if (i + 1) % CHK == 0:
            out = pd.concat([base, pd.DataFrame(new_rows, columns=["stock_code", "date", "monthly_return"])],
                            ignore_index=True)
            out.to_csv(OUT, index=False, encoding="utf-8-sig")
            print(f"  进度 {i+1}/{len(codes)} 累计新增 {len(new_rows)} 行 失败 {fail}")
    out = pd.concat([base, pd.DataFrame(new_rows, columns=["stock_code", "date", "monthly_return"])],
                    ignore_index=True)
    out.to_csv(OUT, index=False, encoding="utf-8-sig")
    try:
        out.to_csv(OUT2, index=False, encoding="utf-8-sig")
    except Exception:
        pass
    dfp.close()
    n2026 = (pd.to_datetime(out["date"]) >= APPEND_FROM).sum()
    print("写出:", OUT, out.shape)
    print("时间范围:", out["date"].min(), "→", out["date"].max(),
          " 2026月收益新增:", len(new_rows), " 文件内2026行数:", int(n2026), " 失败:", fail)


if __name__ == "__main__":
    main()
