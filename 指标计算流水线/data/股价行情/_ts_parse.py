# -*- coding: utf-8 -*-
"""解析 TuShare monthly 月线响应 -> code,gm,close CSV + 缺失清单。
输入: MCP 输出文件(含 "The MCP server responded with:" 前缀), 期望ts_code列表, 输出csv
"""
import sys, re, json, os

def main():
    src, out_csv, expect_ts = sys.argv[1], sys.argv[2], sys.argv[3]
    txt = open(src, encoding="utf-8").read()
    m = re.search(r'responded with:\s*(.*)', txt, re.S)
    body = m.group(1).strip() if m else txt.strip()
    # body 形如 [{"type":"text","text":"[{\"ts_code\":...}]"}]
    try:
        outer = json.loads(body)
        inner = json.loads(outer[0]["text"])
    except Exception as e:
        print("解析失败:", e)
        return
    expect = [x.strip() for x in expect_ts.split(",") if x.strip()]
    rows = []
    found = set()
    for rec in inner:
        ts = rec["ts_code"]
        code = ts.split(".")[0]
        found.add(code)
        rows.append(f"{code},{rec['trade_date']},{rec['close']}")
    missing = [c for c in expect if c.split('.')[0] not in found]
    with open(out_csv, "w", encoding="utf-8") as f:
        f.write("\n".join(rows))
        if rows:
            f.write("\n")
    miss_file = os.path.splitext(out_csv)[0] + "_missing.txt"
    with open(miss_file, "w", encoding="utf-8") as f:
        f.write(",".join(missing))
    print(f"写出 {out_csv}: {len(rows)}行, 覆盖 {len(found)}/{len(expect)}, 缺失 {len(missing)}")

if __name__ == "__main__":
    main()