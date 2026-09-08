import os, glob, csv, calendar

RAW_DIR = os.path.dirname(os.path.abspath(__file__)) + "/raw_data"
OUT = os.path.dirname(os.path.abspath(__file__)) + "/chunk_10_out.csv"

# target months: 2026-01 .. 2026-06 inclusive
TARGET_YM = [(2026, m) for m in range(1, 7)]

def month_end(y, m):
    d = calendar.monthrange(y, m)[1]
    return f"{y:04d}-{m:02d}-{d:02d}"

def normalize_date(yyyymmdd):
    y = int(yyyymmdd[:4]); m = int(yyyymmdd[4:6])
    return month_end(y, m)

rows = []  # (stock_code, date, monthly_return)
stocks_seen = set()

for fn in sorted(glob.glob(RAW_DIR + "/data_*.txt")):
    with open(fn, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            code = parts[0]
            if code in stocks_seen:
                continue
            stocks_seen.add(code)
            # build { (y,m): close }
            closes = {}
            for tok in parts[1:]:
                if ":" not in tok:
                    continue
                d, c = tok.split(":", 1)
                try:
                    y = int(d[:4]); m = int(d[4:6]); close = float(c)
                except Exception:
                    continue
                closes[(y, m)] = close
            # compute monthly returns only when previous calendar month exists
            for (y, m) in TARGET_YM:
                if (y, m) not in closes:
                    continue
                pm = m - 1
                py = y
                if pm == 0:
                    pm = 12; py = y - 1
                if (py, pm) not in closes:
                    continue  # gap -> cannot compute true monthly return
                ret = closes[(y, m)] / closes[(py, pm)] - 1.0
                rows.append((code, normalize_date(f"{y:04d}{m:02d}01"), ret))

rows.sort(key=lambda r: (r[0], r[1]))
with open(OUT, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["stock_code", "date", "monthly_return"])
    for r in rows:
        w.writerow(r)

print("stocks:", len(stocks_seen))
print("rows:", len(rows))
print("file:", OUT)
