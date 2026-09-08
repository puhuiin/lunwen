import os, csv, datetime

OUT = r"D:/Desktop/基金经理行为分析研究/代码/tdx_chunks/chunk_03_out.csv"
FAIL = r"D:/Desktop/基金经理行为分析研究/代码/tdx_chunks/chunk_03_failures.txt"

data = {
    "300814": [["20251231","73.889999"],["20260130","74.199997"],["20260227","99.650002"],["20260331","80.279999"],["20260430","108.050003"],["20260529","159.740005"],["20260630","204.449997"],["20260731","100.169998"],["20260813","139.500000"]],
    "300861": [["20251231","14.750000"],["20260130","16.740000"],["20260227","18.840000"],["20260331","15.450000"],["20260430","19.610001"],["20260529","19.730000"],["20260630","25.010000"],["20260731","15.800000"],["20260813","17.070000"]],
    "300963": [["20251231","20.750000"],["20260130","19.780001"],["20260227","20.469999"],["20260331","16.709999"],["20260430","16.809999"],["20260529","14.620000"],["20260630","13.400000"],["20260731","11.520000"],["20260813","11.910000"]],
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

print("batch11 appended rows:", len(rows), "failures:", failures)
