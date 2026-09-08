import os, csv, datetime

OUT = r"D:/Desktop/基金经理行为分析研究/代码/tdx_chunks/chunk_03_out.csv"
FAIL = r"D:/Desktop/基金经理行为分析研究/代码/tdx_chunks/chunk_03_failures.txt"

data = {
  "002271": [["20251231","13.590000"],["20260130","17.280001"],["20260227","18.000000"],["20260331","15.310000"],["20260430","14.960000"],["20260529","13.630000"],["20260630","11.870000"],["20260731","11.880000"],["20260813","11.530000"]],
  "002335": [["20251231","37.950001"],["20260130","42.759998"],["20260227","42.860001"],["20260331","37.810001"],["20260430","41.650002"],["20260529","39.060001"],["20260630","42.450001"],["20260731","28.700001"],["20260813","32.139999"]],
  "002410": [["20251231","12.350000"],["20260130","13.530000"],["20260227","13.740000"],["20260331","10.840000"],["20260430","10.750000"],["20260529","9.900000"],["20260630","8.160000"],["20260731","9.400000"],["20260813","9.290000"]],
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
print("batch4 appended rows:", len(rows), "failures:", failures)
