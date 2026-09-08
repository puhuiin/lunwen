import os, csv, datetime

OUT = r"D:/Desktop/基金经理行为分析研究/代码/tdx_chunks/chunk_03_out.csv"
FAIL = r"D:/Desktop/基金经理行为分析研究/代码/tdx_chunks/chunk_03_failures.txt"

# wind-format: (date_iso_str, close_str)
data = {
    "603409": [["2025-12-31","24.75"],["2026-01-30","26.61"],["2026-02-27","24.86"],
               ["2026-03-31","25.13"],["2026-04-30","28.81"],["2026-05-29","25.94"],
               ["2026-06-30","18.35"],["2026-07-31","16.96"]],
    "688036": [["2025-12-31","65.21"],["2026-01-30","57.30"],["2026-02-27","56.98"],
               ["2026-03-31","54.07"],["2026-04-30","56.92"],["2026-05-29","60.20"],
               ["2026-06-30","58.95"],["2026-07-31","64.47"]],
    "688072": [["2025-12-31","329.82"],["2026-01-30","352.55"],["2026-02-27","369.20"],
               ["2026-03-31","369.80"],["2026-04-30","444.76"],["2026-05-29","627.65"],
               ["2026-06-30","832.00"],["2026-07-31","664.97"]],
    "688120": [["2025-12-31","107.11"],["2026-01-30","134.81"],["2026-02-27","138.33"],
               ["2026-03-31","124.19"],["2026-04-30","140.91"],["2026-05-29","186.49"],
               ["2026-06-30","322.18"],["2026-07-31","256.98"]],
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

print("batch25 appended rows:", len(rows), "failures:", failures)
