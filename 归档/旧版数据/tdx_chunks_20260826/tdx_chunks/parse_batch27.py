import os, csv, datetime

OUT = r"D:/Desktop/基金经理行为分析研究/代码/tdx_chunks/chunk_03_out.csv"
FAIL = r"D:/Desktop/基金经理行为分析研究/代码/tdx_chunks/chunk_03_failures.txt"

# wind-format: (date_iso_str, close_str)
data = {
    "688307": [["2025-12-31","30.77"],["2026-01-30","32.93"],["2026-02-27","35.62"],
               ["2026-03-31","48.67"],["2026-04-30","63.29"],["2026-05-29","71.99"],
               ["2026-06-30","79.95"],["2026-07-31","38.50"]],
    "688347": [["2025-12-31","107.87"],["2026-01-30","155.10"],["2026-02-27","126.78"],
               ["2026-03-31","105.90"],["2026-04-30","141.00"],["2026-05-29","236.68"],
               ["2026-06-30","336.30"],["2026-07-31","237.90"]],
    "688388": [["2025-12-31","28.28"],["2026-01-30","29.60"],["2026-02-27","30.26"],
               ["2026-03-31","28.63"],["2026-04-30","34.63"],["2026-05-29","33.64"],
               ["2026-06-30","44.00"],["2026-07-31","23.05"]],
    "688449": [["2025-12-31","45.15"],["2026-01-30","56.83"],["2026-02-27","50.24"],
               ["2026-03-31","41.68"],["2026-04-30","55.01"],["2026-05-29","75.79"],
               ["2026-06-30","86.31"],["2026-07-31","52.45"]],
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

print("batch27 appended rows:", len(rows), "failures:", failures)
