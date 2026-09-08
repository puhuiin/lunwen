import datetime, calendar, os
from pytdx.hq import TdxHq_API

OUT = r"D:/Desktop/基金经理行为分析研究/代码/tdx_chunks/chunk_09_out.csv"

codes = """000066 000526 000630 000733 000858 000960 001221 001317 001391 002046
002102 002171 002236 002293 002353 002436 002493 002557 002612 002727
002815 002869 002947 003816 300037 300138 300274 300378 300442 300499
300593 300677 300731 300772 300833 300896 300980 301069 301165 301220
301292 301367 301486 301550 301590 301630 565650 600063 600153 600273
600352 600418 600511 600584 600686 600761 600877 600955 601006 601111
601298 601601 601799 601919 603035 603099 603162 603199 603257 603303
603370 603499 603605 603699 603816 603938 605090 605376 688016 688048
688095 688136 688169 688205 688246 688281 688322 688362 688408 688478
688518 688556 688608 688657 688710 688766 688805 920438""".split()

def mkt(c):
    if c[0] == '6':
        return 1
    if c[0] in ('4', '8'):
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
    """Return list of (date, close) daily bars, sorted ascending, ending at latest trading day."""
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
        # try 'date' field 'YYYYMMDD'
        dd = e.get('date')
        if dd:
            dd = str(dd)
            return datetime.date(int(dd[:4]), int(dd[4:6]), int(dd[6:8]))
        return None
    return datetime.date(int(y), int(mo), int(d))

def event_factor(e, cbefore):
    # pytdx xdxr quotes fenhong/songzhuangu/peigu PER 10 SHARES; peigujia is a per-share price.
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

def compute_qfq_monthly(code):
    """Return dict {(y,m): qfq_close} for Dec2025..Jun2026 using daily qfq.

    IMPORTANT: qfq reference is fixed at 2026-06-30 (the latest month-end in
    the MCP monthly series). Ex-dividend events after 2026-06-30 are excluded
    so our qfq matches the authoritative MCP source exactly.
    """
    daily = get_daily_window(code)
    if not daily:
        return {}
    ref_date = datetime.date(2026, 6, 30)  # fixed MCP reference (June month-end)
    xdxr = get_xdxr(code)
    events = []  # (ex_date, factor)
    for e in xdxr:
        dt = event_date(e)
        if dt is None:
            continue
        if dt <= ref_date:
            # close_before = last daily bar strictly before ex_date
            cb = None
            for (bd, bc) in daily:
                if bd < dt:
                    cb = bc
                else:
                    break
            f = event_factor(e, cb)
            events.append((dt, f))
    # F(d) = product of event factors for events with ex_date > d
    def F(d):
        prod = 1.0
        for (ed, f) in events:
            if ed > d:
                prod *= f
        return prod
    # month-end qfq close
    result = {}
    for (y, mo) in [(2025,12),(2026,1),(2026,2),(2026,3),(2026,4),(2026,5),(2026,6)]:
        # last daily bar in this month
        me = None
        for (bd, bc) in daily:
            if bd.year == y and bd.month == mo:
                me = (bd, bc)
        if me is None:
            continue
        (d, raw) = me
        result[(y, mo)] = raw * F(d)
    return result

# ---- VALIDATION against MCP ground truth (hardcoded monthly qfq closes) ----
MCP = {
 '000066': {(2025,12):14.41,(2026,1):15.87,(2026,2):16.59,(2026,3):14.71,(2026,4):19.82,(2026,5):17.80,(2026,6):19.05},
 '000630': {(2025,12):5.96,(2026,1):8.22,(2026,2):7.88,(2026,3):5.76,(2026,4):6.10,(2026,5):6.85,(2026,6):6.36},
 '000733': {(2025,12):52.029999,(2026,1):54.169998,(2026,2):57.360001,(2026,3):45.009998,(2026,4):42.230000,(2026,5):51.110001,(2026,6):56.639999},
 '000960': {(2025,12):27.52,(2026,1):39.57,(2026,2):44.11,(2026,3):31.309999,(2026,4):35.25,(2026,5):37.50,(2026,6):42.689999},
}
months = [(2025,12),(2026,1),(2026,2),(2026,3),(2026,4),(2026,5),(2026,6)]
print("=== VALIDATION: my qfq monthly close vs MCP qfq monthly close ===")
maxdiff = 0.0
for code, mcp_dict in MCP.items():
    daily = get_daily_window(code)
    ref_date = datetime.date(2026, 6, 30)
    xdxr = get_xdxr(code)
    events = []
    for e in xdxr:
        dt = event_date(e)
        if dt is None or dt > ref_date:
            continue
        cb = None
        for (bd, bc) in daily:
            if bd < dt:
                cb = bc
            else:
                break
        f = event_factor(e, cb)
        if f != 1.0:
            events.append((dt, f, cb, float(e.get('fenhong') or 0)/10.0))
    print(f"--- {code} events(<=2026-06-30, factor!=1):")
    for (dt, f, cb, fh) in events:
        print(f"    ex={dt} cbefore={cb} fenhong/10={fh:.4f} factor={f:.6f}")
    mine = compute_qfq_monthly(code)
    for (y, mo) in months:
        if (y, mo) in mcp_dict and (y, mo) in mine:
            diff = abs(mine[(y, mo)] - mcp_dict[(y, mo)])
            maxdiff = max(maxdiff, diff)
            print(f"{code} {y}-{mo:02d}: mine={mine[(y,mo)]:.6f} mcp={mcp_dict[(y,mo)]:.6f} diff={diff:.2e}")
print("MAX DIFF (close):", maxdiff)
# ---- RETURN-based validation (the actual deliverable) ----
months_r = [(2026,1),(2026,2),(2026,3),(2026,4),(2026,5),(2026,6)]
print("=== RETURN comparison (my qfq return vs MCP qfq return) ===")
maxrdiff = 0.0
for code, mcp_dict in MCP.items():
    mine = compute_qfq_monthly(code)
    for (y, mo) in months_r:
        py, pm = (y, mo-1) if mo > 1 else (y-1, 12)
        if (y,mo) in mine and (py,pm) in mine and (y,mo) in mcp_dict and (py,pm) in mcp_dict:
            my_r = mine[(y,mo)]/mine[(py,pm)] - 1
            mcp_r = mcp_dict[(y,mo)]/mcp_dict[(py,pm)] - 1
            rd = abs(my_r - mcp_r)
            maxrdiff = max(maxrdiff, rd)
            print(f"{code} {y}-{mo:02d}: myR={my_r:.6f} mcpR={mcp_r:.6f} rdiff={rd:.2e}")
print("MAX DIFF (return):", maxrdiff)
print("VALIDATION(close)", "PASS" if maxdiff < 0.02 else "FAIL",
      "| VALIDATION(return)", "PASS" if maxrdiff < 0.01 else "FAIL")
