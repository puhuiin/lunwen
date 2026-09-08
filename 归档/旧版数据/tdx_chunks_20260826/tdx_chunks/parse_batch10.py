import os, csv, datetime

OUT = r"D:/Desktop/基金经理行为分析研究/代码/tdx_chunks/chunk_03_out.csv"
FAIL = r"D:/Desktop/基金经理行为分析研究/代码/tdx_chunks/chunk_03_failures.txt"

data = {
    "300658": [["20251231","14.760000"],["20260130","17.940001"],["20260227","21.910000"],["20260331","22.920000"],["20260430","21.670000"],["20260529","12.030000"],["20260630","11.430000"],["20260731","9.820000"],["20260813","10.790000"]],
    "300702": [["20251231","23.549999"],["20260130","25.950001"],["20260227","24.959999"],["20260331","23.330000"],["20260430","21.040001"],["20260529","19.180000"],["20260630","20.160000"],["20260731","19.850000"],["20260813","22.610001"]],
    "300760": [["20251231","188.889999"],["20260130","187.699997"],["20260227","184.360001"],["20260331","163.100006"],["20260430","166.839996"],["20260529","151.830002"],["20260630","135.830002"],["20260731","158.880005"],["20260813","153.389999"]],
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

print("batch10 appended rows:", len(rows), "failures:", failures)
