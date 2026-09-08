import os, csv, datetime

OUT = r"D:/Desktop/基金经理行为分析研究/代码/tdx_chunks/chunk_03_out.csv"
FAIL = r"D:/Desktop/基金经理行为分析研究/代码/tdx_chunks/chunk_03_failures.txt"

data = {
    "301528": [["20251231","46.820000"],["20260130","46.750000"],["20260227","48.880001"],["20260331","42.680000"],["20260430","51.860001"],["20260529","46.860001"],["20260630","81.900002"],["20260731","45.080002"],["20260813","53.779999"]],
    "301584": [["20251231","29.020000"],["20260130","29.379999"],["20260227","28.790001"],["20260331","26.920000"],["20260430","26.049999"],["20260529","22.780001"],["20260630","19.940001"],["20260731","22.040001"],["20260813","23.639999"]],
    "301611": [["20251231","85.629997"],["20260130","126.580002"],["20260227","126.419998"],["20260331","96.809998"],["20260430","105.080002"],["20260529","92.440002"],["20260630","180.070007"],["20260731","84.599998"],["20260813","102.970001"]],
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

print("batch14 appended rows:", len(rows), "failures:", failures)
