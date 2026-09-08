import os, csv, datetime

OUT = r"D:/Desktop/基金经理行为分析研究/代码/tdx_chunks/chunk_03_out.csv"
FAIL = r"D:/Desktop/基金经理行为分析研究/代码/tdx_chunks/chunk_03_failures.txt"

data = {
    "603341": [["2025-12-31","41.73"],["2026-01-30","44.75"],["2026-02-27","46.41"],["2026-03-31","37.23"],["2026-04-30","36.35"],["2026-05-29","34.03"],["2026-06-30","42.49"],["2026-07-31","36.43"],["2026-08-13","40.90"]],
    "603583": [["2025-12-31","37.59"],["2026-01-30","36.82"],["2026-02-27","36.38"],["2026-03-31","31.25"],["2026-04-30","28.52"],["2026-05-29","24.91"],["2026-06-30","22.80"],["2026-07-31","24.62"],["2026-08-13","24.78"]],
    "603678": [["2025-12-31","35.28"],["2026-01-30","39.15"],["2026-02-27","43.25"],["2026-03-31","33.94"],["2026-04-30","32.47"],["2026-05-29","48.38"],["2026-06-30","83.00"],["2026-07-31","40.62"],["2026-08-13","50.65"]],
    "603773": [["2025-12-31","35.38"],["2026-01-30","36.70"],["2026-02-27","41.88"],["2026-03-31","32.76"],["2026-04-30","69.35"],["2026-05-29","104.08"],["2026-06-30","162.97"],["2026-07-31","68.80"],["2026-08-13","93.80"]],
    "603893": [["2025-12-31","177.99"],["2026-01-30","191.01"],["2026-02-27","179.97"],["2026-03-31","152.23"],["2026-04-30","182.90"],["2026-05-29","175.67"],["2026-06-30","188.36"],["2026-07-31","188.00"],["2026-08-13","208.34"]],
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

print("batch23 appended rows:", len(rows), "failures:", failures)
