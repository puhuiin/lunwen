import os, csv, datetime

OUT = r"D:/Desktop/基金经理行为分析研究/代码/tdx_chunks/chunk_03_out.csv"
FAIL = r"D:/Desktop/基金经理行为分析研究/代码/tdx_chunks/chunk_03_failures.txt"

data = {
  "300092": [["20251231","15.690000"],["20260130","15.690000"],["20260227","16.209999"],["20260331","15.190000"],["20260430","16.639999"],["20260529","13.910000"],["20260630","11.540000"],["20260731","11.400000"],["20260813","11.870000"]],
  "300212": [["20251231","17.450001"],["20260130","15.500000"],["20260227","12.660000"],["20260331","11.430000"],["20260430","6.550000"],["20260529","11.000000"],["20260630","9.390000"],["20260731","8.270000"],["20260813","8.890000"]],
  "300347": [["20251231","56.570000"],["20260130","62.880001"],["20260227","59.509998"],["20260331","53.700001"],["20260430","55.070000"],["20260529","39.320000"],["20260630","47.869999"],["20260731","49.990002"],["20260813","55.320000"]],
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
print("batch8 appended rows:", len(rows), "failures:", failures)
