import os, csv, datetime

OUT = r"D:/Desktop/基金经理行为分析研究/代码/tdx_chunks/chunk_03_out.csv"
FAIL = r"D:/Desktop/基金经理行为分析研究/代码/tdx_chunks/chunk_03_failures.txt"

data = {
    "600487": [["20251231","24.459999"],["20260130","34.740002"],["20260227","47.230000"],["20260331","52.389999"],["20260430","65.430000"],["20260529","76.849998"],["20260630","109.339996"],["20260731","47.610001"],["20260813","57.250000"]],
    "600548": [["20251231","8.560000"],["20260130","8.830000"],["20260227","8.770000"],["20260331","9.100000"],["20260430","8.830000"],["20260529","8.680000"],["20260630","7.890000"],["20260731","8.730000"],["20260813","8.370000"]],
    "600623": [["20251231","7.600000"],["20260130","9.950000"],["20260227","9.440000"],["20260331","9.530000"],["20260430","10.770000"],["20260529","8.630000"],["20260630","7.960000"],["20260731","8.120000"],["20260813","8.220000"]],
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

print("batch17 appended rows:", len(rows), "failures:", failures)
