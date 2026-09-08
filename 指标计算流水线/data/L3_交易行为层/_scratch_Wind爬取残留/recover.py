#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
恢复编排脚本（仅用于 team-lead 上轮遗留的原始 MCP 响应 JSON）。

背景：上轮因落盘格式错误废弃；本轮使用 team-lead 重写后的 parse_resp.py 作为
唯一落盘器（输出列结构 / 样本过滤一律由 parse_resp.py 负责，本脚本不改写）。

本脚本只做一件事：把多种遗留响应结构归一化为 parse_resp.py 期望的
{"data":[{columns:[...], items:[[name,val],...]}, ...]}，再逐年份以子进程调用
parse_resp.py <year> '<json>' 追加落盘。

支持三种遗留结构：
  A. 扁平：{"data":[{columns,items}, ...]}            -> 直接用
  B. 嵌套：[{"data":[{columns,items}]}, ...]          -> 拆开
  C. 转置：columns[0] 含 ".OF"（基金名），items 行形如 [指标名, 数值]
                                                  -> 重塑为正常块
"""
import os, sys, json, subprocess, re

BASE = os.path.dirname(os.path.abspath(__file__))
PARSE = os.path.join(BASE, "parse_resp.py")
PY = r"C:/Users/26955/.workbuddy/binaries/python/envs/default/Scripts/python.exe"

# year -> 该年遗留响应文件（顺序无所谓，parse_resp.py 内部按 (fund_code,year) 去重）
JOBS = {
    2019: ["r_2019_B1.json", "r_2019_B2.json", "r_2019_B3.json"],
    2020: ["r_2020.json"],
    2021: ["r_2021.json"],
    2022: ["r_2022.json"],
    2023: ["r_2023.json", "r_2023_rec.json"],
    2024: ["resp_2024.json", "resp_2024_r1a.json", "resp_2024_r1b.json"],
    2025: ["r_2025.json"],
}

OF_RE = re.compile(r"(\d{6})\.OF")


def reshape_block(block):
    """处理转置块：columns[0] 含 .OF 时，把 items 行的 [指标, 数值] 重塑为 [基金名, 数值]。"""
    cols = block.get("columns", []) or []
    items = block.get("items", []) or []
    if cols and isinstance(cols[0], str) and ".OF" in cols[0]:
        name = cols[0]
        new_items = []
        for row in items:
            if isinstance(row, (list, tuple)) and len(row) >= 2:
                new_items.append([name, row[1]])
        if new_items:
            return {"columns": cols, "items": new_items}
    return block


def normalize(raw):
    """把任意遗留结构归一化为 {'data':[block,...]}（block 已含 columns/items）。"""
    blocks = []
    if isinstance(raw, dict):
        elems = raw.get("data", [])
    elif isinstance(raw, list):
        elems = raw
    else:
        return {"data": []}

    for elem in elems:
        if not isinstance(elem, dict):
            continue
        if ("columns" in elem) or ("items" in elem):
            blocks.append(reshape_block(elem))
        elif isinstance(elem.get("data"), list):
            for inner in elem["data"]:
                if isinstance(inner, dict) and (("columns" in inner) or ("items" in inner)):
                    blocks.append(reshape_block(inner))
    return {"data": blocks}


def main():
    summary = {}
    for year, files in JOBS.items():
        all_blocks = []
        for fn in files:
            p = os.path.join(BASE, fn)
            if not os.path.exists(p):
                print(f"[warn] {fn} 不存在，跳过", file=sys.stderr)
                continue
            with open(p, encoding="utf-8") as f:
                raw = json.load(f)
            norm = normalize(raw)
            all_blocks.extend(norm["data"])

        if not all_blocks:
            print(f"[skip] {year}: 无可用块")
            summary[year] = 0
            continue

        payload = json.dumps({"data": all_blocks}, ensure_ascii=False)
        # 子进程调用 parse_resp.py —— 不经 shell，避免中文/引号转义问题
        r = subprocess.run(
            [PY, PARSE, str(year), payload],
            cwd=BASE, capture_output=True, text=True, encoding="utf-8",
        )
        out = (r.stdout or "").strip()
        err = (r.stderr or "").strip()
        if r.returncode != 0:
            print(f"[ERR] {year}: rc={r.returncode}\nstdout={out}\nstderr={err}", file=sys.stderr)
            summary[year] = -1
        else:
            print(f"[ok] {year}: {out}")
            # 粗略抓取 appended 行数
            m = re.search(r"appended (\d+) sample rows", out)
            summary[year] = int(m.group(1)) if m else 0
    print("SUMMARY:", summary)


if __name__ == "__main__":
    main()
