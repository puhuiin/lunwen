import os, csv, datetime

OUT = r"D:/Desktop/基金经理行为分析研究/代码/tdx_chunks/chunk_03_out.csv"
FAIL = r"D:/Desktop/基金经理行为分析研究/代码/tdx_chunks/chunk_03_failures.txt"

data = {
  "002683": [["20251231","47.349998"],["20260130","48.759998"],["20260227","47.029999"],["20260331","38.709999"],["20260430","36.320000"],["20260529","32.049999"],["20260630","29.290001"],["20260731","28.040001"],["20260813","28.799999"]],
  "002779": [["20251231","113.389999"],["20260130","98.769997"],["20260227","95.330002"],["20260331","88.129997"],["20260430","79.879997"],["20260529","70.209999"],["20260630","78.559998"],["20260731","57.400002"],["20260813","79.000000"]],
  "002847": [["20251231","67.309998"],["20260130","67.010002"],["20260227","64.300003"],["20260331","58.369999"],["20260430","57.720001"],["20260529","58.029999"],["20260630","44.599998"],["20260731","52.029999"],["20260813","49.130001"]],
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
print("batch6 appended rows:", len(rows), "failures:", failures)
