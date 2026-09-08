import os, csv, datetime

OUT = r"D:/Desktop/基金经理行为分析研究/代码/tdx_chunks/chunk_03_out.csv"
FAIL = r"D:/Desktop/基金经理行为分析研究/代码/tdx_chunks/chunk_03_failures.txt"

data = {
    "601519": [["20251231","12.870000"],["20260130","12.690000"],["20260227","12.270000"],["20260331","10.420000"],["20260430","10.240000"],["20260529","10.040000"],["20260630","8.630000"],["20260731","8.410000"],["20260813","8.220000"]],
    "601698": [["20251231","35.700001"],["20260130","37.970001"],["20260227","37.290001"],["20260331","32.970001"],["20260430","36.639999"],["20260529","30.070000"],["20260630","30.250000"],["20260731","25.219999"],["20260813","26.270000"]],
    "601886": [["20251231","7.810000"],["20260130","9.260000"],["20260227","9.040000"],["20260331","8.300000"],["20260430","9.580000"],["20260529","8.990000"],["20260630","8.030000"],["20260731","8.640000"],["20260813","11.530000"]],
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

print("batch20 appended rows:", len(rows), "failures:", failures)
