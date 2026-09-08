import os, csv, datetime

OUT = r"D:/Desktop/基金经理行为分析研究/代码/tdx_chunks/chunk_03_out.csv"
FAIL = r"D:/Desktop/基金经理行为分析研究/代码/tdx_chunks/chunk_03_failures.txt"

data = {
    "300421": [["20251231","36.630001"],["20260130","28.379999"],["20260227","27.430000"],["20260331","22.860001"],["20260430","23.629999"],["20260529","22.240000"],["20260630","18.510000"],["20260731","16.580000"],["20260813","17.480000"]],
    "300490": [["20251231","11.990000"],["20260130","15.670000"],["20260227","17.160000"],["20260331","15.970000"],["20260430","19.900000"],["20260529","15.640000"],["20260630","13.230000"],["20260731","11.390000"],["20260813","11.800000"]],
    "300571": [["20251231","27.650000"],["20260130","29.230000"],["20260227","31.780001"],["20260331","32.099998"],["20260430","44.349998"],["20260529","46.869999"],["20260630","45.660000"],["20260731","30.559999"],["20260813","33.880001"]],
}

def last_day(y, m):
    if m == 12: nm, ny = 1, y + 1
    else: nm, ny = m + 1, y
    return (datetime.date(ny, nm, 1) - datetime.timedelta(days=1)).strftime("%Y-%m-%d")

failures = []
rows = []
for code, pts in data.items():
    try:
        if not pts:
            failures.append(code); continue
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

print("batch9 appended rows:", len(rows), "failures:", failures)
