import csv, os, sys, calendar, json
from datetime import date

OUT = r"D:/Desktop/基金经理行为分析研究/代码/tdx_chunks/chunk_06_out.csv"
# target months 2026-01 .. 2026-06
MONTHS = [202601, 202602, 202603, 202604, 202605, 202606]

def normalize_month(m):
    y, mo = m // 100, m % 100
    last = calendar.monthrange(y, mo)[1]
    return date(y, mo, last).isoformat()  # 'YYYY-MM-DD'

def main():
    batch_file = sys.argv[1]
    with open(batch_file, "r", encoding="utf-8") as f:
        batch = json.load(f)  # {code: [close0..close6]}  (7 closes: 202512..202606)
    failed = []
    rows = []
    for code, closes in batch.items():
        if not isinstance(closes, list) or len(closes) < 7:
            failed.append(code)
            continue
        try:
            for i, m in enumerate(MONTHS):
                c_prev = float(closes[i])
                c_cur = float(closes[i + 1])
                if c_prev == 0:
                    failed.append(code)
                    break
                ret = c_cur / c_prev - 1.0
                rows.append((code, normalize_month(m), ret))
        except Exception:
            failed.append(code)
    write_header = not os.path.exists(OUT)
    with open(OUT, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if write_header:
            w.writerow(["stock_code", "date", "monthly_return"])
        for r in rows:
            w.writerow(r)
    print(f"batch stocks={len(batch)} appended_rows={len(rows)} failed={failed}")

if __name__ == "__main__":
    main()
