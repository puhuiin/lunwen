# -*- coding: utf-8 -*-
"""用 akshare 腾讯源下载缺失A股日线并转月度, 支持断点续传"""
import os, sys, time, calendar
import akshare as ak

BASE = os.path.dirname(os.path.abspath(__file__))
MISSING = os.path.join(BASE, "_missing_a_stocks.txt")
OUT = os.path.join(BASE, "em_parsed", "ak_output.csv")
DONE_TXT = os.path.join(BASE, "em_parsed", "ak_done.txt")
FAIL_TXT = os.path.join(BASE, "em_parsed", "ak_failed.txt")

DELAY = 0.8

def prefix(code):
    if code[:3] in ("600","601","603","605","688","689"):
        return "sh"
    if code[:3] in ("000","001","002","003","300","301","200"):
        return "sz"
    return None  # BJ 等不支持

def load_codes():
    return [c.strip() for c in open(MISSING, encoding="utf-8") if c.strip()]

def load_done():
    if not os.path.exists(DONE_TXT):
        return set()
    return {l.strip() for l in open(DONE_TXT, encoding="utf-8") if l.strip()}

def ym_end(ym):
    y, m = int(ym[:4]), int(ym[5:7])
    return f"{ym}-{calendar.monthrange(y, m)[1]:02d}"

def fetch(code):
    p = prefix(code)
    if not p:
        return None, "NO_SUPPORT"
    df = ak.stock_zh_a_hist_tx(symbol=p + code, start_date="20060101", end_date="20261231")
    if df is None or df.empty:
        return None, "EMPTY"
    df = df[["date", "close"]].copy()
    df["date"] = df["date"].astype(str).str[:7]  # 保留年月
    # 每月最后交易日收盘
    df = df.drop_duplicates(subset="date", keep="last")
    df["ret"] = df["close"].pct_change()
    out = df[["date", "ret"]].dropna(subset=["ret"])
    return [(code, ym_end(d), r) for d, r in zip(out["date"], out["ret"])], None

def main():
    codes = load_codes()
    done = load_done()
    print(f"total={len(codes)} already_done={len(done)}")
    with open(OUT, "a", encoding="utf-8") as fo, \
         open(DONE_TXT, "a", encoding="utf-8") as fd, \
         open(FAIL_TXT, "a", encoding="utf-8") as ff:
        n_suc = 0
        for i, code in enumerate(codes):
            if code in done:
                continue
            try:
                rows, msg = fetch(code)
                if rows:
                    for r in rows:
                        fo.write(f"{r[0]},{r[1]},{r[2]:.12g}\n")
                    fo.flush()
                    n_suc += 1
                else:
                    ff.write(f"{code}\t{msg}\n"); ff.flush()
                fd.write(code + "\n"); fd.flush()
            except Exception as e:
                ff.write(f"{code}\t{repr(e)[:120]}\n"); ff.flush()
            if (i + 1) % 10 == 0:
                print(f"progress {i+1}/{len(codes)} success={n_suc}", flush=True)
            time.sleep(DELAY)
    print(f"done. success={n_suc}")

if __name__ == "__main__":
    main()