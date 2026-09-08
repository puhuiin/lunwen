import os, csv, datetime

OUT = r"D:/Desktop/基金经理行为分析研究/代码/tdx_chunks/chunk_03_out.csv"
FAIL = r"D:/Desktop/基金经理行为分析研究/代码/tdx_chunks/chunk_03_failures.txt"

data = {
    "600733": [["20251231","8.030000"],["20260130","8.050000"],["20260227","7.990000"],["20260331","7.150000"],["20260430","7.110000"],["20260529","6.110000"],["20260630","4.870000"],["20260731","6.020000"],["20260813","5.400000"]],
    "600859": [["20251231","15.530000"],["20260130","14.500000"],["20260227","13.860000"],["20260331","12.180000"],["20260430","12.370000"],["20260529","11.180000"],["20260630","9.180000"],["20260731","10.480000"],["20260813","10.150000"]],
    "600925": [["20251231","4.520000"],["20260130","4.730000"],["20260227","4.750000"],["20260331","4.630000"],["20260430","4.670000"],["20260529","4.680000"],["20260630","4.010000"],["20260731","4.390000"],["20260813","4.340000"]],
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

print("batch18 appended rows:", len(rows), "failures:", failures)
