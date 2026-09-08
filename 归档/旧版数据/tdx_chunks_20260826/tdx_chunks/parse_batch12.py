import os, csv, datetime

OUT = r"D:/Desktop/基金经理行为分析研究/代码/tdx_chunks/chunk_03_out.csv"
FAIL = r"D:/Desktop/基金经理行为分析研究/代码/tdx_chunks/chunk_03_failures.txt"

data = {
    "301031": [["20251231","75.500000"],["20260130","96.309998"],["20260227","98.400002"],["20260331","93.089996"],["20260430","108.070000"],["20260529","117.720001"],["20260630","119.449997"],["20260731","78.099998"],["20260813","89.809998"]],
    "301150": [["20251231","29.790001"],["20260130","28.910000"],["20260227","33.099998"],["20260331","39.750000"],["20260430","48.740002"],["20260529","46.799999"],["20260630","63.110001"],["20260731","32.980000"],["20260813","39.000000"]],
    "301202": [["20251231","40.200001"],["20260130","41.889999"],["20260227","44.250000"],["20260331","36.150002"],["20260430","40.189999"],["20260529","39.090000"],["20260630","33.330002"],["20260731","30.940001"],["20260813","33.509998"]],
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

print("batch12 appended rows:", len(rows), "failures:", failures)
