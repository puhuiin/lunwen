import os, csv, datetime

OUT = r"D:/Desktop/基金经理行为分析研究/代码/tdx_chunks/chunk_03_out.csv"
FAIL = r"D:/Desktop/基金经理行为分析研究/代码/tdx_chunks/chunk_03_failures.txt"

# wind-finance 前复权月线: (date_str, close)
data = {
    "603193": [["2025-12-31","23.94"],["2026-01-30","23.56"],["2026-02-27","23.18"],["2026-03-31","21.97"],["2026-04-30","25.66"],["2026-05-29","22.11"],["2026-06-30","18.55"],["2026-07-31","21.96"],["2026-08-13","20.87"]],
    "603233": [["2025-12-31","17.08"],["2026-01-30","19.38"],["2026-02-27","18.98"],["2026-03-31","17.23"],["2026-04-30","18.14"],["2026-05-29","15.99"],["2026-06-30","15.03"],["2026-07-31","18.85"],["2026-08-13","17.94"]],
    "603286": [["2025-12-31","69.16"],["2026-01-30","68.86"],["2026-02-27","66.36"],["2026-03-31","57.69"],["2026-04-30","64.52"],["2026-05-29","55.36"],["2026-06-30","45.63"],["2026-07-31","37.75"],["2026-08-13","42.75"]],
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
            y = int(d1[0:4]); m = int(d1[5:7])
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

print("batch22 appended rows:", len(rows), "failures:", failures)
