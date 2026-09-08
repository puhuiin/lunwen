import os, csv, datetime

OUT = r"D:/Desktop/基金经理行为分析研究/代码/tdx_chunks/chunk_03_out.csv"
FAIL = r"D:/Desktop/基金经理行为分析研究/代码/tdx_chunks/chunk_03_failures.txt"

data = {
  "002080": [["20251231","35.910000"],["20260130","42.450001"],["20260227","50.200001"],["20260331","38.840000"],["20260430","54.740002"],["20260529","71.150002"],["20260630","90.000000"],["20260731","43.139999"],["20260813","55.759998"]],
  "002154": [["20251231","3.680000"],["20260130","3.860000"],["20260227","3.830000"],["20260331","3.450000"],["20260430","3.990000"],["20260529","4.100000"],["20260630","3.560000"],["20260731","3.920000"],["20260813","4.220000"]],
  "002221": [["20251231","8.100000"],["20260130","8.640000"],["20260227","8.580000"],["20260331","8.670000"],["20260430","8.050000"],["20260529","6.340000"],["20260630","5.260000"],["20260731","5.630000"],["20260813","5.490000"]],
}

def last_day(y, m):
    if m == 12:
        nm, ny = 1, y + 1
    else:
        nm, ny = m + 1, y
    return (datetime.date(ny, nm, 1) - datetime.timedelta(days=1)).strftime("%Y-%m-%d")

failures = []; rows = []
for code, pts in data.items():
    try:
        if not pts: failures.append(code); continue
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
print("batch3 appended rows:", len(rows), "failures:", failures)
