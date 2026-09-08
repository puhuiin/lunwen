# -*- coding: utf-8 -*-
"""TuShare daily 甄别: 从持久化文件提取有数据的有效股票代码。用法:
python _tsd_screen.py <persisted_file> <ts_codes逗号分隔> <valid_txt>
输出(追加写入 valid_txt): 每个有效代码一行
"""
import sys, re, json

def main():
    src, ts_codes, valid_txt = sys.argv[1:4]
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
    present = set(r["ts_code"].split(".")[0] for r in inner)
    valid = [c for c in expect if c in present]
    with open(valid_txt, "a", encoding="utf-8") as f:
        for c in valid:
            f.write(c + "\n")
    print(f"BATCH_VALID:{','.join(valid)} n={len(valid)}")

if __name__ == "__main__":
    main()