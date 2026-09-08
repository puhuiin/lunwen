import os, csv, datetime

OUT = r"D:/Desktop/基金经理行为分析研究/代码/tdx_chunks/chunk_03_out.csv"
FAIL = r"D:/Desktop/基金经理行为分析研究/代码/tdx_chunks/chunk_03_failures.txt"

data = {
    "603013": [["20251231","24.320000"],["20260130","24.480000"],["20260227","24.150000"],["20260331","18.610001"],["20260430","20.059999"],["20260529","19.240000"],["20260630","15.790000"],["20260731","17.240000"],["20260813","16.620001"]],
    "603072": [["20251231","40.439999"],["20260130","43.750000"],["20260227","44.430000"],["20260331","35.509998"],["20260430","37.290001"],["20260529","35.639999"],["20260630","39.200001"],["20260731","32.000000"],["20260813","31.750000"]],
    "603127": [["20251231","34.889999"],["20260130","37.889999"],["20260227","36.610001"],["20260331","34.080002"],["20260430","38.750000"],["20260529","35.049999"],["20260630","38.220001"],["20260731","41.540001"],["20260813","51.900002"]],
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

print("batch21 appended rows:", len(rows), "failures:", failures)
