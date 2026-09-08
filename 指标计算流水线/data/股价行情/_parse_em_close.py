# -*- coding: utf-8 -*-
"""解析东财 mx_ashare_finance_data 返回的「月K线收盘价」JSON → 标准 monthly_return(out).
东财返回封装为 MCP 数组: [{"type":"text","text":"{\"data\":[...]}"}], text 字段是 JSON 转义的 data 对象。
data[].columns = ["收盘价","2026-06-30(月)",...]  (月份降序)
data[].items   = [["万科A(000002.SZ)",p1,p2,...],...]  (每只股票一行; "-" 为停牌/未上市占位)
解析: 代码取收盘价序列 → pct_change 得逐月收益(小数) → 输出 (stock_code,date,monthly_return)
用法: python _parse_em_close.py <raw_json_file> <out_csv>
"""
import os, sys, json, re
import pandas as pd

def parse_file(path):
    text = open(path, encoding="utf-8").read()
    # 1) 提取 MCP 外层数组
    arr_m = re.search(r"\[.*\]", text, re.S)
    if not arr_m:
        print("no outer array")
        return None
    try:
        outer = json.loads(arr_m.group(0))
    except Exception as e:
        print("outer json fail:", e)
        return None
    # 2) 收集所有 data 对象
    data_objs = []
    for msg in outer:
        if isinstance(msg, dict) and msg.get("type") == "text":
            inner = msg.get("text", "")
            # 定位 {"data":
            try:
                inner = inner[inner.find("{"):]
                obj = json.loads(inner)
                data_objs.append(obj)
            except Exception as e:
                print("inner json fail:", e)
    if not data_objs:
        print("no data objects")
        return None
    rows = []
    for obj in data_objs:
        for blk in obj.get("data", []):
            cols = blk.get("columns", [])
            items = blk.get("items", [])
            if not cols or not items:
                continue
            months = []
            for c in cols[1:]:
                dm = re.search(r"(\d{4}-\d{2}-\d{2})", str(c))
                months.append((dm.group(1) if dm else None))
            for it in items:
                code_m = re.search(r"\((\d{6})", str(it[0]))
                if not code_m:
                    continue
                code = code_m.group(1)
                vals = []
                for i, mnth in enumerate(months):
                    if i + 1 >= len(it):
                        break
                    p = it[i + 1]
                    pv = None
                    try:
                        if str(p).strip() not in ("-", "", "None"):
                            pv = float(str(p).replace("元", "").replace(",", ""))
                    except Exception:
                        pv = None
                    vals.append((mnth, pv))
                vals.sort(key=lambda x: (x[0] is None, x[0] or ""))
                prev = None
                for mnth, cur in vals:
                    if mnth is None or cur is None:
                        prev = cur
                        continue
                    if prev is not None and prev > 0:
                        rows.append({"stock_code": code, "date": mnth, "monthly_return": cur / prev - 1.0})
                    prev = cur
    if not rows:
        print("no parseable rows")
        return None
    df = pd.DataFrame(rows)
    df = df.drop_duplicates(subset=["stock_code", "date"], keep="last")
    return df

if __name__ == "__main__":
    raw, out = sys.argv[1], sys.argv[2]
    df = parse_file(raw)
    if df is not None:
        df.to_csv(out, index=False, encoding="utf-8-sig")
        print(f"saved {len(df)} rows, stocks={df['stock_code'].nunique()} -> {out}")
        print(df.head(3).to_string())
    else:
        print("FAIL", raw)