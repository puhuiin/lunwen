import os, csv, datetime

OUT = r"D:/Desktop/基金经理行为分析研究/代码/tdx_chunks/chunk_03_out.csv"
FAIL = r"D:/Desktop/基金经理行为分析研究/代码/tdx_chunks/chunk_03_failures.txt"

# wind-format: (date_iso_str, close_str)
data = {
    "688157": [["2025-12-31","30.15"],["2026-01-30","30.21"],["2026-02-27","32.62"],
               ["2026-03-31","31.36"],["2026-04-30","30.00"],["2026-05-29","23.20"],
               ["2026-06-30","21.96"],["2026-07-31","18.50"]],
    "688190": [["2025-12-31","96.37"],["2026-01-30","97.11"],["2026-02-27","113.32"],
               ["2026-03-31","93.60"],["2026-04-30","80.81"],["2026-05-29","116.20"],
               ["2026-06-30","90.71"],["2026-07-31","67.61"]],
    "688228": [["2025-12-31","194.61"],["2026-01-30","244.80"],["2026-02-27","128.01"],
               ["2026-03-31","102.50"],["2026-04-30","105.51"],["2026-05-29","88.44"],
               ["2026-06-30","77.34"],["2026-07-31","66.01"]],
    "688271": [["2025-12-31","125.30"],["2026-01-30","129.09"],["2026-02-27","130.49"],
               ["2026-03-31","111.82"],["2026-04-30","109.77"],["2026-05-29","120.10"],
               ["2026-06-30","101.06"],["2026-07-31","115.52"]],
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

print("batch26 appended rows:", len(rows), "failures:", failures)
