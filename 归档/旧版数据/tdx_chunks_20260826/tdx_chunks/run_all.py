import datetime, calendar, os, csv
from pytdx.hq import TdxHq_API

OUT = r"D:/Desktop/基金经理行为分析研究/代码/tdx_chunks/chunk_09_out.csv"

all_codes = """000066 000526 000630 000733 000858 000960 001221 001317 001391 002046
002102 002171 002236 002293 002353 002436 002493 002557 002612 002727
002815 002869 002947 003816 300037 300138 300274 300378 300442 300499
300593 300677 300731 300772 300833 300896 300980 301069 301165 301220
301292 301367 301486 301550 301590 301630 565650 600063 600153 600273
600352 600418 600511 600584 600686 600761 600877 600955 601006 601111
601298 601601 601799 601919 603035 603099 603162 603199 603257 603303
603370 603499 603605 603699 603816 603938 605090 605376 688016 688048
688095 688136 688169 688205 688246 688281 688322 688362 688408 688478
688518 688556 688608 688657 688710 688766 688805 920438""".split()

# codes already written to CSV via authoritative MCP source (preserve exactly)
DONE = {'000066','000526','000630','000733','000858'}

def mkt(c):
    if c[0] == '6':
        return 1
    if c[0] in ('4','8','9'):   # 深圳/上海/北京(北交所) -- 4/8/9 开头为北交所
        return 2
    return 0

HOSTS = ['180.153.18.170', '60.12.136.250', '60.12.136.251']

def connect():
    last = None
    for h in HOSTS:
        try:
            api = TdxHq_API()
            if api.connect(h, 7709, time_out=8):
                return api
        except Exception as e:
            last = e
    raise RuntimeError("no tdx host reachable: %s" % last)

api = connect()

def get_daily_window(code, count=220):
    bars = api.get_security_bars(4, mkt(code), code, 0, count)
    out = []
    for b in bars:
        try:
            dt = datetime.date(int(b['year']), int(b['month']), int(b['day']))
        except Exception:
            continue
        out.append((dt, float(b['close'])))
    out.sort(key=lambda x: x[0])
    return out

def get_xdxr(code):
    try:
        x = api.get_xdxr_info(mkt(code), code)
    except Exception:
        x = []
    return x or []

def event_date(e):
    y = e.get('year'); mo = e.get('month'); d = e.get('day')
    if y is None:
        dd = e.get('date')
        if dd:
            dd = str(dd)
            return datetime.date(int(dd[:4]), int(dd[4:6]), int(dd[6:8]))
        return None
    return datetime.date(int(y), int(mo), int(d))

def event_factor(e, cbefore):
    # pytdx xdxr quotes fenhong/songzhuangu/peigu PER 10 SHARES; peigujia is per-share price.
    fh = float(e.get('fenhong') or 0.0) / 10.0
    sg = float(e.get('songzhuangu') or 0.0) / 10.0
    pg = float(e.get('peigu') or 0.0) / 10.0
    pgj = float(e.get('peigujia') or 0.0)
    if cbefore is None or cbefore <= 0:
        return 1.0
    denom = cbefore * (1.0 + sg + pg)
    if denom == 0:
        return 1.0
    return (cbefore - fh + pg * pgj) / denom

REF = datetime.date(2026, 6, 30)  # fixed MCP qfq reference (June month-end)

def qfq_month_end(code):
    """Return dict {(y,m): qfq_close} for Dec2025..Jun2026."""
    daily = get_daily_window(code)
    if not daily:
        return {}
    xdxr = get_xdxr(code)
    events = []
    for e in xdxr:
        dt = event_date(e)
        if dt is None or dt > REF:
            continue
        cb = None
        for (bd, bc) in daily:
            if bd < dt:
                cb = bc
            else:
                break
        f = event_factor(e, cb)
        if f != 1.0:
            events.append((dt, f))
    def F(d):
        prod = 1.0
        for (ed, f) in events:
            if ed > d:
                prod *= f
        return prod
    result = {}
    for (y, mo) in [(2025,12),(2026,1),(2026,2),(2026,3),(2026,4),(2026,5),(2026,6)]:
        me = None
        for (bd, bc) in daily:
            if bd.year == y and bd.month == mo:
                me = (bd, bc)
        if me is None:
            continue
        (d, raw) = me
        result[(y, mo)] = raw * F(d)
    return result

def monthly_returns(qfq):
    rows = []
    for (y, mo) in [(2026,1),(2026,2),(2026,3),(2026,4),(2026,5),(2026,6)]:
        py, pm = (y, mo-1) if mo > 1 else (y-1, 12)
        if (y, mo) in qfq and (py, pm) in qfq:
            r = qfq[(y, mo)] / qfq[(py, pm)] - 1.0
            # normalize date to calendar month-end
            lastday = calendar.monthrange(y, mo)[1]
            date_str = "%04d-%02d-%02d" % (y, mo, lastday)
            rows.append((date_str, r))
    return rows

# ---- load existing authoritative rows ----
existing = {}
if os.path.exists(OUT):
    with open(OUT, 'r', newline='') as f:
        rd = csv.reader(f)
        header = next(rd, None)
        for row in rd:
            if len(row) >= 3:
                existing.setdefault(row[0], []).append((row[1], float(row[2])))

# ---- process ----
all_rows = {}   # code -> list of (date, return)
failures = []
attempted = 0
success = 0

for code in all_codes:
    attempted += 1
    if code in DONE and code in existing:
        all_rows[code] = existing[code]
        success += 1
        continue
    try:
        qfq = qfq_month_end(code)
        rows = monthly_returns(qfq)
        if not rows:
            failures.append(code)
            continue
        all_rows[code] = rows
        success += 1
    except Exception as ex:
        failures.append(code)
        print("FAIL %s: %s" % (code, ex))

# ---- write CSV (fresh, sorted by code then date) ----
with open(OUT, 'w', newline='') as f:
    w = csv.writer(f)
    w.writerow(['stock_code', 'date', 'monthly_return'])
    for code in sorted(all_rows.keys()):
        for (date_str, r) in all_rows[code]:
            w.writerow([code, date_str, repr(r)])

rows_written = sum(len(v) for v in all_rows.values())
print("=" * 50)
print("attempted :", attempted)
print("success   :", success)
print("rows_written:", rows_written)
print("failed    :", failures)
print("DONE.")
