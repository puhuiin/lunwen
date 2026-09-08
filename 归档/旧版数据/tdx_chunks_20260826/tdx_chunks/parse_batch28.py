import os, csv, datetime

OUT = r"D:/Desktop/基金经理行为分析研究/代码/tdx_chunks/chunk_03_out.csv"
FAIL = r"D:/Desktop/基金经理行为分析研究/代码/tdx_chunks/chunk_03_failures.txt"

# wind-format: (date_iso_str, close_str)
data = {
    "688506": [["2025-12-31","323.10"],["2026-01-30","277.75"],["2026-02-27","264.60"],
               ["2026-03-31","278.00"],["2026-04-30","272.74"],["2026-05-29","238.57"],
               ["2026-06-30","294.03"],["2026-07-31","298.00"]],
    "688539": [["2025-12-31","49.20"],["2026-01-30","45.74"],["2026-02-27","45.18"],
               ["2026-03-31","35.66"],["2026-04-30","37.12"],["2026-05-29","32.95"],
               ["2026-06-30","31.88"],["2026-07-31","23.48"]],
    "688590": [["2025-12-31","18.66"],["2026-01-30","18.95"],["2026-02-27","17.24"],
               ["2026-03-31","13.10"],["2026-04-30","14.87"],["2026-05-29","14.08"],
               ["2026-06-30","12.43"],["2026-07-31","13.13"]],
    "688630": [["2025-12-31","134.16"],["2026-01-30","178.53"],["2026-02-27","198.46"],
               ["2026-03-31","192.87"],["2026-04-30","257.75"],["2026-05-29","335.00"],
               ["2026-06-30","549.39"],["2026-07-31","325.23"]],
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

print("batch28 appended rows:", len(rows), "failures:", failures)
