import os, csv, datetime

OUT = r"D:/Desktop/基金经理行为分析研究/代码/tdx_chunks/chunk_03_out.csv"
FAIL = r"D:/Desktop/基金经理行为分析研究/代码/tdx_chunks/chunk_03_failures.txt"

# wind-format: (date_iso_str, close_str)
data = {
    "603997": [["2025-12-31","13.79"],["2026-01-30","14.69"],["2026-02-27","14.26"],
               ["2026-03-31","11.67"],["2026-04-30","12.07"],["2026-05-29","13.91"],
               ["2026-06-30","11.83"],["2026-07-31","13.16"],["2026-08-13","12.63"]],
    "605305": [["2025-12-31","41.27"],["2026-01-30","42.59"],["2026-02-27","40.05"],
               ["2026-03-31","40.55"],["2026-04-30","47.36"],["2026-05-29","40.83"],
               ["2026-06-30","41.92"],["2026-07-31","39.02"],["2026-08-13","38.23"]],
    "688005": [["2025-12-31","35.40"],["2026-01-30","30.65"],["2026-02-27","31.75"],
               ["2026-03-31","28.33"],["2026-04-30","34.83"],["2026-05-29","31.00"],
               ["2026-06-30","30.60"],["2026-07-31","27.95"],["2026-08-13","27.31"]],
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

print("batch24 appended rows:", len(rows), "failures:", failures)
