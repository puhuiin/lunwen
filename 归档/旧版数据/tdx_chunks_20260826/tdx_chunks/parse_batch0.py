import os, csv, datetime

OUT = r"D:/Desktop/基金经理行为分析研究/代码/tdx_chunks/chunk_03_out.csv"
FAIL = r"D:/Desktop/基金经理行为分析研究/代码/tdx_chunks/chunk_03_failures.txt"

# 已从 MCP 工具 mcp__tdx-connector__tdx_kline 返回文本中提取的 (Data, Close) 列表
data = {
  "000034": [["20251231","27.740000"],["20260130","27.120001"],["20260227","28.969999"],["20260331","23.780001"],["20260430","26.860001"],["20260529","25.840000"],["20260630","27.750000"],["20260731","24.100000"],["20260813","24.889999"]],
  "000403": [["20251231","13.690000"],["20260130","13.690000"],["20260227","14.110000"],["20260331","12.940000"],["20260430","11.950000"],["20260529","12.900000"],["20260630","8.790000"],["20260731","10.430000"],["20260813","11.170000"]],
  "000596": [["20251231","128.199997"],["20260130","127.720001"],["20260227","117.809998"],["20260331","99.449997"],["20260430","103.830002"],["20260529","89.629997"],["20260630","76.400002"],["20260731","94.949997"],["20260813","100.419998"]],
  "000695": [["20251231","12.710000"],["20260130","12.340000"],["20260227","13.320000"],["20260331","13.270000"],["20260430","15.500000"],["20260529","15.140000"],["20260630","12.500000"],["20260731","12.620000"],["20260813","14.390000"]],
}

def last_day(y, m):
    if m == 12:
        nm, ny = 1, y + 1
    else:
        nm, ny = m + 1, y
    d = datetime.date(ny, nm, 1) - datetime.timedelta(days=1)
    return d.strftime("%Y-%m-%d")

failures = []
rows = []
for code, pts in data.items():
    try:
        if not pts:
            failures.append(code)
            continue
        pts = sorted([(r[0], float(r[1])) for r in pts], key=lambda x: x[0])
        for i in range(1, len(pts)):
            d0, c0 = pts[i-1]
            d1, c1 = pts[i]
            y = int(d1[0:4]); m = int(d1[4:6])
            if y == 2026 and 1 <= m <= 6:
                ret = c1 / c0 - 1.0
                rows.append((code, last_day(y, m), ret))
    except Exception as e:
        failures.append(code)
        print("FAIL", code, e)

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
print("batch0 appended rows:", len(rows))
print("batch0 failures:", failures)
