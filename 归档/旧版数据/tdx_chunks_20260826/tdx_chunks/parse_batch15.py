import os, csv, datetime

OUT = r"D:/Desktop/基金经理行为分析研究/代码/tdx_chunks/chunk_03_out.csv"
FAIL = r"D:/Desktop/基金经理行为分析研究/代码/tdx_chunks/chunk_03_failures.txt"

data = {
    "301668": [["20251231","47.509998"],["20260130","51.900002"],["20260227","54.430000"],["20260331","48.560001"],["20260430","44.389999"],["20260529","39.599998"],["20260630","32.900002"],["20260731","38.849998"],["20260813","36.320000"]],
    "600031": [["20251231","20.950001"],["20260130","21.740000"],["20260227","22.969999"],["20260331","19.040001"],["20260430","20.170000"],["20260529","17.760000"],["20260630","17.100000"],["20260731","20.549999"],["20260813","18.719999"]],
    "600114": [["20251231","30.250000"],["20260130","32.849998"],["20260227","35.209999"],["20260331","27.459999"],["20260430","33.779999"],["20260529","36.619999"],["20260630","37.759998"],["20260731","26.459999"],["20260813","29.290001"]],
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

print("batch15 appended rows:", len(rows), "failures:", failures)
