# -*- coding: utf-8 -*-
"""解析 TuShare daily 日线响应 -> 每月最后一个交易日收盘价 CSV (code,ym,close)。
输入: persisted 文件, 期望ts_code列表, 输出csv
"""
import sys, re, json, os
from collections import defaultdict

def main():
    src, out_csv, expect_ts = sys.argv[1], sys.argv[2], sys.argv[3]
    txt = open(src, encoding="utf-8").read()
    m = re.search(r'responded with:\s*(.*)', txt, re.S)
    body = m.group(1).strip() if m else txt.strip()
    try:
        outer = json.loads(body)
        inner = json.loads(outer[0]["text"])
    except Exception as e:
        print("解析失败:", e)
        return
    # 按 code+ym 保留最后交易日的 close
    best = {}  # (code,ym) -> (tradedate, close)
    for rec in inner:
        code = rec["ts_code"].split(".")[0]
        td = rec["trade_date"]
        ym = td[:6]
        key = (code, ym)
        if key not in best or td > best[key][0]:
            best[key] = (td, rec["close"])
    rows = []
    for (code, ym), (td, close) in sorted(best.items()):
        rows.append(f"{code},{td},{close}")
    expect = [x.split('.')[0] for x in expect_ts.split(",") if x.strip()]
    found = set(b[0] for b in best)
    missing = [c for c in expect if c not in found]
    with open(out_csv, "w", encoding="utf-8") as f:
        f.write("\n".join(rows))
        if rows:
            f.write("\n")
    miss_file = os.path.splitext(out_csv)[0] + "_missing.txt"
    with open(miss_file, "w", encoding="utf-8") as f:
        f.write(",".join(missing))
    print(f"写出 {out_csv}: {len(rows)}行(月历), 覆盖 {len(found)}/{len(expect)} 只, 缺失 {len(missing)}")

if __name__ == "__main__":
    main()