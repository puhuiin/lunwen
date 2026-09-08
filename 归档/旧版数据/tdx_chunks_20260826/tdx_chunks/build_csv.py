import csv
import calendar
import os

CHUNK_DIR = r"D:/Desktop/基金经理行为分析研究/代码/tdx_chunks"
BATCH_FILES = ["batch1_raw.txt", "batch2_raw.txt", "batch3_raw.txt", "batch4_raw.txt", "batch5_raw.txt"]
OUT_CSV = os.path.join(CHUNK_DIR, "chunk_02_out.csv")

def month_end(datestr):
    """datestr = 'YYYYMMDD' -> actual month-end date string 'YYYY-MM-DD'"""
    y = int(datestr[:4])
    m = int(datestr[4:6])
    last = calendar.monthrange(y, m)[1]
    return f"{y}-{m:02d}-{last:02d}"

def parse_batch(path):
    """Return list of (code, [(date, close), ...])"""
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            code, rest = line.split("|", 1)
            pairs = []
            for seg in rest.split(";"):
                if not seg:
                    continue
                d, c = seg.split(":")
                pairs.append((d, float(c)))
            rows.append((code, pairs))
    return rows

all_stocks = []
for bf in BATCH_FILES:
    p = os.path.join(CHUNK_DIR, bf)
    if os.path.exists(p):
        all_stocks.extend(parse_batch(p))

out_rows = []
for code, pairs in all_stocks:
    # pairs[0] = 20251231 baseline; pairs[1..6] = 2026-01 .. 2026-06
    if len(pairs) < 7:
        # not enough data; skip this stock
        continue
    baseline = pairs[0][1]
    for i in range(1, 7):
        d, c = pairs[i]
        mret = c / baseline - 1.0
        out_rows.append((code, month_end(d), round(mret, 8)))
        baseline = c  # chain: each month return relative to previous month's close

with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["stock_code", "date", "monthly_return"])
    for r in out_rows:
        w.writerow(r)

print("stocks:", len(all_stocks))
print("rows written:", len(out_rows))
print("output:", OUT_CSV)
