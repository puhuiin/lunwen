import os, csv, json, glob, datetime, re

RAW_DIR = r"D:/Desktop/基金经理行为分析研究/代码/tdx_chunks/raw13"
OUT = r"D:/Desktop/基金经理行为分析研究/代码/tdx_chunks/chunk_13_out.csv"
FAIL = r"D:/Desktop/基金经理行为分析研究/代码/tdx_chunks/chunk_13_failures.txt"

def last_day(y, m):
    if m == 12:
        nm, ny = 1, y + 1
    else:
        nm, ny = m + 1, y
    d = datetime.date(ny, nm, 1) - datetime.timedelta(days=1)
    return d.strftime("%Y-%m-%d")

# 收集每个 code 对应的原始响应文本段
segments = {}  # code -> raw text
for fp in sorted(glob.glob(os.path.join(RAW_DIR, "*.txt"))):
    text = open(fp, "r", encoding="utf-8").read()
    # 按分隔符拆分
    parts = re.split(r"===STOCK:(\d{6})===", text)
    # parts[0] 为前言, 之后每对 (code, body)
    for i in range(1, len(parts), 2):
        code = parts[i]
        body = parts[i + 1] if i + 1 < len(parts) else ""
        # 同一 code 可能跨多个文件出现, 取最后出现的
        segments[code] = body

failures = []
rows = []
for code, body in segments.items():
    try:
        idx = body.find("详细K线数据:")
        if idx < 0:
            failures.append(code)
            continue
        js = body[idx + len("详细K线数据:"):].strip()
        if not js:
            failures.append(code)
            continue
        obj = json.loads(js)
        rws = obj.get("Rows", [])
        if not rws:
            failures.append(code)
            continue
        pts = []
        for r in rws:
            d = r.get("Data")
            c = r.get("Close")
            if d is None or c is None:
                continue
            pts.append((str(d), float(c)))
        if len(pts) < 2:
            # 不足两根无法计算环比, 但仍不视为失败(仅无收益)
            pass
        pts = sorted(pts, key=lambda x: x[0])
        for i in range(1, len(pts)):
            d0, c0 = pts[i - 1]
            d1, c1 = pts[i]
            if c0 == 0:
                continue
            y = int(d1[0:4]); m = int(d1[4:6])
            if y == 2026 and 1 <= m <= 6:
                ret = c1 / c0 - 1.0
                rows.append((code, last_day(y, m), ret))
    except Exception as e:
        failures.append(code)
        print("FAIL", code, repr(e))

header = not os.path.exists(OUT)
with open(OUT, "a", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    if header:
        w.writerow(["stock_code", "date", "monthly_return"])
    for r in rows:
        w.writerow(r)
with open(FAIL, "a", encoding="utf-8") as f:
    for c in failures:
        f.write(c + "\n")

print("segments codes:", len(segments))
print("appended rows:", len(rows))
print("failures:", failures)
