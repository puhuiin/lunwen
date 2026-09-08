import os, csv, datetime

OUT = r"D:/Desktop/基金经理行为分析研究/代码/tdx_chunks/chunk_03_out.csv"
FAIL = r"D:/Desktop/基金经理行为分析研究/代码/tdx_chunks/chunk_03_failures.txt"

data = {
    "600988": [["20251231","30.920000"],["20260130","42.880001"],["20260227","39.599998"],["20260331","42.830002"],["20260430","37.680000"],["20260529","33.369999"],["20260630","26.320000"],["20260731","39.560001"],["20260813","38.660000"]],
    "601069": [["20251231","26.520000"],["20260130","44.560001"],["20260227","36.099998"],["20260331","31.290001"],["20260430","32.430000"],["20260529","27.280001"],["20260630","22.000000"],["20260731","25.450001"],["20260813","27.540001"]],
    "601198": [["20251231","13.790000"],["20260130","13.810000"],["20260227","13.870000"],["20260331","12.230000"],["20260430","13.110000"],["20260529","13.280000"],["20260630","13.500000"],["20260731","13.830000"],["20260813","13.880000"]],
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

print("batch19 appended rows:", len(rows), "failures:", failures)
