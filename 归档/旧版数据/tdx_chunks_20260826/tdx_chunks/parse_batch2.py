import os, csv, datetime

OUT = r"D:/Desktop/基金经理行为分析研究/代码/tdx_chunks/chunk_03_out.csv"
FAIL = r"D:/Desktop/基金经理行为分析研究/代码/tdx_chunks/chunk_03_failures.txt"

data = {
  "002025": [["20251231","50.000000"],["20260130","50.150002"],["20260227","52.750000"],["20260331","62.740002"],["20260430","73.059998"],["20260529","65.019997"],["20260630","76.089996"],["20260731","61.369999"],["20260813","64.959999"]],
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
print("batch2 appended rows:", len(rows), "failures:", failures)
