#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
鲁棒解析东方财富 MCP (mcp__mx-ds-mcp__mx_fund_finance_data) 返回的
基金「报告期持仓换手率」JSON，校验基金代码，追加写入规范的拉长换手率 CSV。

兼容两种返回格式：
  格式A: items = [基金名(代码), 数值]
  格式B: columns[0]=指标标签, items = [基金名(代码), 数值]
代码正则匹配 (\\d+\\.(?:OF|SZ|SH))，兼容 LOF 返回的 .SZ/.SH，按数字部分对齐到样本 .OF 代码。

用法（兼容两种调用）：
    python parse_resp.py <year> <resp_json_file> [resp_json_file ...]
    python parse_resp.py <year> '<json_string>'          # 直接传 JSON 串
响应文件可为单个对象或数组合并的多个批次响应。

输出规范 CSV（data/L3_交易行为层/基金换手率_东财报告期_拉长.csv）
列：fund_code, year, report_period, turnover_rate, source
  fund_code 带 .OF 后缀（与样本对齐，如 162201.OF）
  report_period 记 YYYY
  turnover_rate 为百分比数值（如 132.5 表示 132.5%）
断点续传：已写入的 (fund_code, year) 跳过；按 OUT_CSV 累计计算 missing_<year>.txt。
"""
import json, re, sys, os

BASE = os.path.dirname(os.path.abspath(__file__))
OUT_CSV = os.path.join(BASE, "基金换手率_东财报告期_拉长.csv")
FAILED_CSV = os.path.join(BASE, "东财换手率抓取_failed.csv")
SOURCE = "mx-ds-mcp"
CODE_RE = re.compile(r'\((\d+)\.(?:OF|SZ|SH)\)', re.IGNORECASE)


def load_codes():
    """返回 (req_num 数字->.OF代码, valid_num 数字集合)"""
    req_num = {}
    valid_num = set()
    p = os.path.join(BASE, "codes_of.txt")
    if os.path.exists(p):
        with open(p, encoding="utf-8") as f:
            for line in f:
                c = line.strip()
                if not c:
                    continue
                num = c.split(".")[0]
                req_num[num] = c
                valid_num.add(num)
    # 若 codes_of.txt 缺失，回退用样本清单
    if not req_num:
        sp = os.path.join(BASE, "样本基金清单_200.csv")
        with open(sp, encoding="utf-8") as f:
            next(f, None)
            for line in f:
                num = line.strip()
                if num:
                    req_num[num] = num + ".OF"
                    valid_num.add(num)
    return req_num, valid_num


def load_done_year(year):
    done = set()
    if os.path.exists(OUT_CSV):
        with open(OUT_CSV, encoding="utf-8") as f:
            for line in f:
                p = line.rstrip("\n").split(",")
                if len(p) >= 2 and p[1] == str(year):
                    done.add(p[0])
    return done


def extract_pairs(block):
    cols = block.get("columns", [])
    pairs = []
    for item in block.get("items", []):
        if len(item) < 2:
            continue
        a, b = item[0], item[1]
        if CODE_RE.search(a):
            pairs.append((a, b))
        elif CODE_RE.search(b):
            pairs.append((b, a))
        elif cols and CODE_RE.search(cols[0]):
            pairs.append((cols[0], b))
    return pairs


def load_responses(paths_or_string):
    """paths_or_string: 文件路径列表，或单个 JSON 字符串。返回 response 对象列表。"""
    if len(paths_or_string) == 1 and not os.path.exists(paths_or_string[0]):
        # 当作内联 JSON 串
        try:
            obj = json.loads(paths_or_string[0])
            return obj if isinstance(obj, list) else [obj]
        except Exception:
            pass
    out = []
    for fp in paths_or_string:
        with open(fp, encoding="utf-8") as f:
            obj = json.load(f)
        out.extend(obj if isinstance(obj, list) else [obj])
    return out


def main():
    if len(sys.argv) < 3:
        print("usage: parse_resp.py <year> <resp_json_file|json_string> [...]")
        sys.exit(1)
    year = sys.argv[1]
    req_num, valid_num = load_codes()
    done = load_done_year(year)

    returned = {}
    unexpected = []
    for resp in load_responses(sys.argv[2:]):
        if not isinstance(resp, dict):
            continue
        for block in resp.get("data", []):
            if not isinstance(block, dict):
                continue
            for name, val in extract_pairs(block):
                m = CODE_RE.search(name)
                if not m:
                    unexpected.append((name, val, "no_code"))
                    continue
                n = m.group(1)
                returned.setdefault(n, val)

    valid = []
    for n, val in returned.items():
        if n in req_num:
            code = n  # 输出数字基金代码（与样本清单对齐，如 162201）
            if code not in done:
                valid.append((code, year, str(year), str(val), SOURCE))
        else:
            unexpected.append((n, val, "not_in_sample"))

    new = 0
    write_header = not os.path.exists(OUT_CSV)
    with open(OUT_CSV, "a", encoding="utf-8-sig") as f:
        if write_header:
            f.write("fund_code,year,report_period,turnover_rate,source\n")
        for r in valid:
            f.write(",".join(r) + "\n")
            new += 1

    # 累计 missing（基于 OUT_CSV 该年已有代码，按数字代码比较）
    done2 = load_done_year(year)
    all_codes = list(req_num.keys())  # 数字代码
    missing = [c for c in all_codes if c not in done2]
    with open(os.path.join(BASE, f"missing_{year}.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(missing) + "\n")

    print(f"[year {year}] files={len(sys.argv)-2} returned={len(returned)} "
          f"valid_new={new} unexpected={len(unexpected)} cum_missing={len(missing)}")
    if unexpected:
        print("UNEXPECTED:", unexpected[:20])


if __name__ == "__main__":
    main()
