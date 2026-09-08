# -*- coding: utf-8 -*-
"""东财MCP响应解析器: 读取原始响应文本(纯JSON串) -> 生成 em_parsed/{wkey}_b{nnn}.csv
用法: python _em_parse.py <raw_json_file> <out_csv> <codes_csv_line>
示例: python _em_parse.py raw_q4_000.json em_parsed/q4_b000.csv "000006,000007,..."
"""
import sys, re, json, os

def parse(resp_text, expect_codes):
    """解析回原始可读文本(格式为 [{"type":"text","text":"{...}"}])"""
    # 去掉外层包装
    try:
        obj = json.loads(resp_text) if resp_text.strip().startswith('[') else None
    except Exception:
        obj = None
    inner = None
    if isinstance(obj, list):
        for d in obj:
            if isinstance(d, dict) and "text" in d:
                inner = d["text"]
                break
    if inner is None:
        inner = resp_text
    try:
        data = json.loads(inner)
    except Exception as e:
        return [], [], f"JSON解析失败: {e}"
    items = None
    columns = None
    if isinstance(data, dict) and "data" in data and isinstance(data["data"], list) and data["data"]:
        columns = data["data"][0].get("columns")
        items = data["data"][0].get("items")
    if not columns or not items:
        return [], list(expect_codes), "无data/columns/items"
    months = [c[:7] for c in columns[1:]]
    rows = []
    found = set()
    # 格式1: 多只股票, columns[0]="收盘价", items每行=股票
    for row in items:
        name = row[0]
        m = re.search(r'\((\d{6})', name)
        if not m:
            continue
        code = m.group(1)
        if "(指数)" in name:
            continue
        found.add(code)
        prices = row[1:]
        for i, p in enumerate(prices):
            if i >= len(months):
                break
            val = str(p).replace("元", "").replace("点", "").strip()
            if val in ("-", "", "None", "null"):
                val = ""
            rows.append(f"{code},{months[i]},{val}")
    # 格式2: 单只股票, columns[0]=股票名, items[0][0]="收盘价"
    if not found and len(items) == 1:
        m0 = re.search(r'\((\d{6})', columns[0])
        if m0 and items[0][0] == "收盘价":
            code = m0.group(1)
            for i, p in enumerate(items[0][1:]):
                if i >= len(months):
                    break
                val = str(p).replace("元", "").replace("点", "").strip()
                if val in ("-", "", "None", "null"):
                    val = ""
                rows.append(f"{code},{months[i]},{val}")
            found.add(code)
    missing = [c for c in expect_codes if c not in found]
    return rows, missing, None

def main():
    if len(sys.argv) < 4:
        print("用法: python _em_parse.py <raw> <out_csv> <codes_csv>")
        sys.exit(1)
    raw_path, out_csv, codes_line = sys.argv[1], sys.argv[2], sys.argv[3]
    expect = codes_line.strip().split(",")
    with open(raw_path, encoding="utf-8") as f:
        resp = f.read()
    # 若内容为包含text字段的对象,直接使用
    rows, missing, err = parse(resp, expect)
    if err:
        print(f"错误: {err}")
        sys.exit(2)
    with open(out_csv, "w", encoding="utf-8", newline="") as f:
        f.write("\n".join(rows) + ("\n" if rows else ""))
    print(f"写出 {out_csv}: {len(rows)} 行, 覆盖 {len(expect)-len(missing)}/{len(expect)} 只股票")
    if missing:
        miss_path = out_csv.replace(".csv", "_missing.txt")
        with open(miss_path, "w", encoding="utf-8") as f:
            f.write("\n".join(missing))
        print(f"缺失: {missing} -> {miss_path}")
    return 0

if __name__ == "__main__":
    sys.exit(main())