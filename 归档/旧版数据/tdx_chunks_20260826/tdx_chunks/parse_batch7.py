import os, csv, datetime

OUT = r"D:/Desktop/基金经理行为分析研究/代码/tdx_chunks/chunk_03_out.csv"
FAIL = r"D:/Desktop/基金经理行为分析研究/代码/tdx_chunks/chunk_03_failures.txt"

data = {
  "002916": [["20251231","229.889999"],["20260130","231.199997"],["20260227","283.059998"],["20260331","217.110001"],["20260430","310.100006"],["20260529","411.410004"],["20260630","457.899994"],["20260731","308.000000"],["20260813","377.980011"]],
  "002988": [["20251231","36.799999"],["20260130","38.580002"],["20260227","35.709999"],["20260331","30.059999"],["20260430","34.650002"],["20260529","30.000000"],["20260630","22.059999"],["20260731","20.260000"],["20260813","21.180000"]],
  "300014": [["20251231","65.529999"],["20260130","63.560001"],["20260227","62.099998"],["20260331","62.000000"],["20260430","72.360001"],["20260529","63.680000"],["20260630","65.029999"],["20260731","54.259998"],["20260813","55.880001"]],
}

def last_day(y, m):
    if m == 12:
        nm, ny = 1, y + 1
    else:
        nm, ny = m + 1, y
    return (datetime.date(ny, nm, 1) - datetime.timedelta(days=1)).strftime("%Y-%m-%d")

failures = []; rows = []
for code, pts in data.items():
    try:
        if not pts: failures.append(code); continue
        pts = sorted([(r[0], float(r[1])) for r in pts], key=lambda x: x[0])
        for i in range(1, len(pts)):
            d0, c0 = pts[i-1]; d1, c1 = pts[i]
            y = int(d1[0:4]); m = int(d1[4:6])
            if y == 2026 and 1 <= m <= 6:
                rows.append((code, last_day(y, m), c1 / c0 - 1.0))
    except Exception as e:
        failures.append(code); print("FAIL", code, e)

header = not os.path.exists(OUT)
with open(OUT, "a", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    if header: w.writerow(["stock_code","date","monthly_return"])
    for r in rows: w.writerow(r)
with open(FAIL, "a", encoding="utf-8") as f:
    for c in failures: f.write(c + "\n")
print("batch7 appended rows:", len(rows), "failures:", failures)
