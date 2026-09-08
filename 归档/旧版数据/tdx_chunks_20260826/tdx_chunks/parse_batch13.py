import os, csv, datetime

OUT = r"D:/Desktop/基金经理行为分析研究/代码/tdx_chunks/chunk_03_out.csv"
FAIL = r"D:/Desktop/基金经理行为分析研究/代码/tdx_chunks/chunk_03_failures.txt"

data = {
    "301261": [["20251231","85.279999"],["20260130","73.959999"],["20260227","72.690002"],["20260331","62.919998"],["20260430","72.110001"],["20260529","75.680000"],["20260630","64.879997"],["20260731","52.770000"],["20260813","58.930000"]],
    "301338": [["20251231","62.560001"],["20260130","89.120003"],["20260227","106.559998"],["20260331","120.290001"],["20260430","138.139999"],["20260529","177.419998"],["20260630","162.889999"],["20260731","78.330002"],["20260813","98.599998"]],
    "301413": [["20251231","103.459999"],["20260130","120.839996"],["20260227","111.550003"],["20260331","88.510002"],["20260430","77.220001"],["20260529","88.739998"],["20260630","70.879997"],["20260731","56.549999"],["20260813","69.099998"]],
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

print("batch13 appended rows:", len(rows), "failures:", failures)
