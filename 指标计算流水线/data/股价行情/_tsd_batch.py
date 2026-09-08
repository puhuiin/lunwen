# -*- coding: utf-8 -*-
"""TuShare daily 批次处理: 解析持久化文件->月历->月收益->追加到主表。用法:
python _tsd_batch.py <persisted_file> <ts_codes逗号分隔> <out_master_csv> <done_txt> <empty_txt>
输出: 覆盖的股票代码(逗号分隔) 打印到 stdout
"""
import sys, re, json, os, calendar

def ym_end(ym):
    y, m = int(ym[:4]), int(ym[4:6])
    return f"{ym[:6]}-{calendar.monthrange(y, m)[1]:02d}"

def main():
    src, ts_codes, out_master, done_txt, empty_txt = sys.argv[1:6]
    txt = open(src, encoding="utf-8").read()
    m = re.search(r'responded with:\s*(.*)', txt, re.S)
    body = m.group(1).strip() if m else txt.strip()
    try:
        outer = json.loads(body)
        inner = json.loads(outer[0]["text"])
    except Exception as e:
        print(f"PARSE_ERR:{e}")
        return
    expect = [x.strip().split('.')[0] for x in ts_codes.split(",") if x.strip()]
    # 按 code+ym 保留最后交易日 close
    best = {}
    for rec in inner:
        code = rec["ts_code"].split(".")[0]
        td = rec["trade_date"]
        ym = td[:6]
        key = (code, ym)
        if key not in best or td > best[key][0]:
            best[key] = (td, rec["close"])
    # 按 code 分组并排序计算月收益
    from collections import defaultdict
    bycode = defaultdict(dict)  # code -> {ym: close(按最后交易日)}
    for (code, ym), (td, close) in best.items():
        bycode[code][ym] = close
    found = []
    with open(out_master, "a", encoding="utf-8") as fo:
        for code in expect:
            if code not in bycode:
                continue
            found.append(code)
            ys = sorted(bycode[code].items())  # [(ym, close)]
            prev = None
            for ym, close in ys:
                if prev is not None:
                    ret = close / prev - 1
                    fo.write(f"{code},{ym_end(ym)},{ret:.12g}\n")
                prev = close
    with open(done_txt, "a", encoding="utf-8") as fd:
        for c in found:
            fd.write(c + "\n")
    with open(empty_txt, "a", encoding="utf-8") as fe:
        for c in expect:
            if c not in found:
                fe.write(c + "\n")
    print(f"COVERED:{','.join(found)} fixtured={len(found)}")

if __name__ == "__main__":
    main()