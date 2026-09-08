import os, csv, datetime

OUT = r"D:/Desktop/基金经理行为分析研究/代码/tdx_chunks/chunk_03_out.csv"
FAIL = r"D:/Desktop/基金经理行为分析研究/代码/tdx_chunks/chunk_03_failures.txt"

data = {
  "002466": [["20251231","55.380001"],["20260130","54.549999"],["20260227","56.599998"],["20260331","55.480000"],["20260430","80.029999"],["20260529","62.880001"],["20260630","61.320000"],["20260731","45.349998"],["20260813","47.759998"]],
  "002539": [["20251231","11.620000"],["20260130","14.400000"],["20260227","15.760000"],["20260331","14.000000"],["20260430","15.190000"],["20260529","12.420000"],["20260630","11.320000"],["20260731","12.060000"],["20260813","12.380000"]],
  "002595": [["20251231","57.590000"],["20260130","56.799999"],["20260227","65.860001"],["20260331","53.919998"],["20260430","59.619999"],["20260529","52.310001"],["20260630","46.599998"],["20260731","52.180000"],["20260813","51.169998"]],
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
print("batch5 appended rows:", len(rows), "failures:", failures)
