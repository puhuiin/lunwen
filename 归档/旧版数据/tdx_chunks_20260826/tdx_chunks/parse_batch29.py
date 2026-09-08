import os, csv, datetime

OUT = r"D:/Desktop/基金经理行为分析研究/代码/tdx_chunks/chunk_03_out.csv"
FAIL = r"D:/Desktop/基金经理行为分析研究/代码/tdx_chunks/chunk_03_failures.txt"

# wind-format: (date_iso_str, close_str)
data = {
    "688695": [["2025-12-31","27.43"],["2026-01-30","28.65"],["2026-02-27","28.73"],
               ["2026-03-31","24.25"],["2026-04-30","25.37"],["2026-05-29","21.97"],
               ["2026-06-30","18.70"],["2026-07-31","18.22"]],
    "688750": [["2025-12-31","19.94"],["2026-01-30","20.21"],["2026-02-27","22.46"],
               ["2026-03-31","17.67"],["2026-04-30","18.65"],["2026-05-29","17.34"],
               ["2026-06-30","16.61"],["2026-07-31","14.26"]],
    "688790": [["2025-12-31","147.78"],["2026-01-30","150.11"],["2026-02-27","148.82"],
               ["2026-03-31","128.83"],["2026-04-30","142.81"],["2026-05-29","132.20"],
               ["2026-06-30","133.83"],["2026-07-31","89.00"]],
    "920116": [["2025-12-31","60.28"],["2026-01-30","78.33"],["2026-02-27","74.19"],
               ["2026-03-31","64.13"],["2026-04-30","71.91"],["2026-05-29","60.60"],
               ["2026-06-30","63.69"],["2026-07-31","44.80"]],
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

print("batch29 appended rows:", len(rows), "failures:", failures)
