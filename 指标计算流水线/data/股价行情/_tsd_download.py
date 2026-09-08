# -*- coding: utf-8 -*-
"""直连 TuShare daily 下载629只有效股票 -> 月收益 -> 追加主表。支持断点续传与限流节奏。
用法: python _tsd_download.py
"""
import os, sys, time, json, urllib.request, calendar
from collections import defaultdict

BASE = os.path.dirname(os.path.abspath(__file__))
CODES_FILE = os.path.join(BASE, "_valid_stocks_TS.txt")
OUT = os.path.join(BASE, "个股月收益率_全量.csv")   # 主表(追加)
DONE_TXT = os.path.join(BASE, "em_parsed", "tsd_dl_done.txt")
FAIL_TXT = os.path.join(BASE, "em_parsed", "tsd_dl_failed.txt")
TOKEN = os.environ.get("TUSHARE_TOKEN", "").strip()
API = "https://api.tushare.pro"

def ym_end(ym):
    y, m = int(ym[:4]), int(ym[4:6])
    return f"{y:04d}-{m:02d}-{calendar.monthrange(y, m)[1]:02d}"

def call_tushare(api_name, params, fields):
    body = json.dumps({"api_name": api_name, "token": TOKEN,
                       "params": params, "fields": fields}).encode()
    req = urllib.request.Request(API, data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())

def fetch_monthly_returns(ts_code):
    """取 ts_code 全历史日线, 每月最后交易日收盘, 计算月收益。返回 [(code,date,ret),...]"""
    params = {"ts_code": ts_code, "start_date": "20060101", "end_date": "20261231"}
    fields = "ts_code,trade_date,close"
    recs = []
    try:
        res = call_tushare("daily", params, fields)
    except Exception as e:
        return None, f"HTTP:{repr(e)[:80]}"
    if res.get("code") != 0:
        # 限流/错误
        return None, f"CODE{res.get('code')}:{res.get('msg','')[:80]}"
    recs = res.get("data", {}).get("items", [])
    if not recs:
        return [], None
    col = res["data"]["fields"]
    di = col.index("trade_date"); ci = col.index("close")
    # 按 code+ym 保留最后交易日 close
    best = {}
    for it in recs:
        td = str(it[di]); ym = td[:6]
        key = it[0].split('.')[0]
        if (key, ym) not in best or td > best[(key, ym)][0]:
            best[(key, ym)] = (td, it[ci])
    bycode = defaultdict(dict)
    for (code, ym), (td, close) in best.items():
        bycode[code][ym] = close
    out = []
    for code, ys in bycode.items():
        prev = None
        for ym in sorted(ys):
            close = ys[ym]
            if prev is not None and close:
                ret = close / prev - 1
                out.append((code, ym_end(ym), ret))
            if close:
                prev = close
    return out, None

def main():
    if not TOKEN:
        print("未找到 TUSHARE_TOKEN"); return
    codes = [l.strip() for l in open(CODES_FILE, encoding="utf-8") if l.strip()]
    done = set()
    if os.path.exists(DONE_TXT):
        done = {l.strip() for l in open(DONE_TXT) if l.strip()}
    print(f"total={len(codes)} done={len(done)}")
    n_ok = 0
    with open(OUT, "a", encoding="utf-8") as fo, \
         open(DONE_TXT, "a", encoding="utf-8") as fd, \
         open(FAIL_TXT, "a", encoding="utf-8") as ff:
        for i, ts in enumerate(codes):
            if ts in done:
                continue
            rows, err = None, None
            for attempt in range(4):
                rows, err = fetch_monthly_returns(ts)
                if err and "频率" in err:
                    time.sleep(8)   # 限流, 等待后重试
                    continue
                break
            if rows:
                for code, date, ret in rows:
                    fo.write(f"{code},{date},{ret:.12g}\n")
                fo.flush()
                n_ok += 1
            elif rows is None:
                ff.write(f"{ts}\t{err}\n"); ff.flush()
            fd.write(ts + "\n"); fd.flush()
            # 限流节奏: daily 接口 50次/分钟
            time.sleep(1.3)
            if (i + 1) % 20 == 0:
                print(f"progress {i+1}/{len(codes)} ok={n_ok}", flush=True)
    print(f"done. ok={n_ok}")

if __name__ == "__main__":
    main()