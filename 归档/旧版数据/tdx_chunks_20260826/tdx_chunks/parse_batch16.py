import os, csv, datetime

OUT = r"D:/Desktop/基金经理行为分析研究/代码/tdx_chunks/chunk_03_out.csv"
FAIL = r"D:/Desktop/基金经理行为分析研究/代码/tdx_chunks/chunk_03_failures.txt"

data = {
    "600211": [["20251231","41.669998"],["20260130","41.520000"],["20260227","41.700001"],["20260331","39.700001"],["20260430","39.580002"],["20260529","38.540001"],["20260630","37.389999"],["20260731","38.680000"],["20260813","40.049999"]],
    "600328": [["20251231","8.210000"],["20260130","9.200000"],["20260227","9.720000"],["20260331","8.640000"],["20260430","8.070000"],["20260529","6.740000"],["20260630","6.000000"],["20260731","6.400000"],["20260813","6.280000"]],
    "600392": [["20251231","21.230000"],["20260130","26.730000"],["20260227","33.270000"],["20260331","22.100000"],["20260430","25.730000"],["20260529","21.590000"],["20260630","29.469999"],["20260731","20.700001"],["20260813","22.850000"]],
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

print("batch16 appended rows:", len(rows), "failures:", failures)
