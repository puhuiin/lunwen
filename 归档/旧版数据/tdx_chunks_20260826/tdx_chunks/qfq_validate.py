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
    for h in HOSTS:
        try:
            api = TdxHq_API()
            if api.connect(h, 7709, time_out=8):
                return api
        except Exception:
            pass
    raise RuntimeError("no tdx host reachable")

api = connect()

def get_monthly_raw(code):
    bars = api.get_security_bars(6, mkt(code), code, 0, 30)
    d = {}
    for b in bars:
        d[(int(b['year']), int(b['month']))] = float(b['close'])
    return d

def get_xdxr(code):
    try:
        x = api.get_xdxr_info(mkt(code), code)
    except Exception:
        x = []
    return x or []

def get_cbefore(code, ex_date):
    # raw close on the last trading day strictly before ex_date
    bars = api.get_security_bars(4, mkt(code), code, 0, 260)
    bars = sorted(bars, key=lambda b: (int(b['year']), int(b['month']), int(b['day'])))
    cbefore = None
    for b in bars:
        dt = datetime.date(int(b['year']), int(b['month']), int(b['day']))
        if dt < ex_date:
            cbefore = float(b['close'])
        else:
            break
    return cbefore

def event_factor(e, cbefore):
    fh = e.get('fenhong') or 0.0
    sg = e.get('songzhuangu') or 0.0
    pg = e.get('peigu') or 0.0
    pgj = e.get('peigujia') or 0.0
    return (cbefore - fh + pg * pgj) / (cbefore * (1.0 + sg + pg))

def in_window_events(code):
    # events with price impact in (2025-12-31, 2026-06-30]
    evs = []
    for e in get_xdxr(code):
        y, mo, d = e.get('year'), e.get('month'), e.get('day')
        if y is None:
            continue
        dt = datetime.date(int(y), int(mo), int(d))
        if datetime.date(2025, 12, 31) < dt <= datetime.date(2026, 6, 30):
            fh = e.get('fenhong') or 0.0
            sg = e.get('songzhuangu') or 0.0
            pg = e.get('peigu') or 0.0
            if fh > 0 or sg > 0 or pg > 0:
                evs.append((dt, e))
    return evs

# ---- VALIDATION against MCP ground truth (hardcoded qfq closes) ----
# keyed by stock -> { (year,month): qfq_close }
MCP = {
 '000066': {(2025,12):14.41,(2026,1):15.87,(2026,2):16.59,(2026,3):14.71,(2026,4):19.82,(2026,5):17.80,(2026,6):19.05},
 '000630': {(2025,12):5.96,(2026,1):8.22,(2026,2):7.88,(2026,3):5.76,(2026,4):6.10,(2026,5):6.85,(2026,6):6.36},
 '000733': {(2025,12):52.029999,(2026,1):54.169998,(2026,2):57.360001,(2026,3):45.009998,(2026,4):42.230000,(2026,5):51.110001,(2026,6):56.639999},
 '000960': {(2025,12):27.52,(2026,1):39.57,(2026,2):44.11,(2026,3):31.309999,(2026,4):35.25,(2026,5):37.50,(2026,6):42.689999},
}
TARGET = [(2026,1),(2026,2),(2026,3),(2026,4),(2026,5),(2026,6)]
print("=== VALIDATION (my qfq return vs MCP qfq return) ===")
maxdiff = 0.0
for code, mcp_dict in MCP.items():
    raw = get_monthly_raw(code)
    evs = in_window_events(code)
    factors = {}  # ex_date -> factor
    for dt, e in evs:
        cb = get_cbefore(code, dt)
        if cb is None:
            continue
        factors[dt] = event_factor(e, cb)
    # compute my qfq monthly returns
    my_ret = {}
    for (y, mo) in TARGET:
        py, pm = (y, mo-1) if mo > 1 else (y-1, 12)
        if (y, mo) in raw and (py, pm) in raw:
            prev_end = datetime.date(py, pm, calendar.monthrange(py, pm)[1])
            m_end = datetime.date(y, mo, calendar.monthrange(y, mo)[1])
            ratio = 1.0
            for dt, f in factors.items():
                if prev_end < dt <= m_end:
                    ratio *= f
            raw_ratio = raw[(y, mo)] / raw[(py, pm)]
            my_ret[(y, mo)] = raw_ratio * ratio - 1
    # mcp returns
    mcp_ret = {}
    for (y, mo) in TARGET:
        py, pm = (y, mo-1) if mo > 1 else (y-1, 12)
        if (y, mo) in mcp_dict and (py, pm) in mcp_dict:
            mcp_ret[(y, mo)] = mcp_dict[(y, mo)] / mcp_dict[(py, pm)] - 1
    for (y, mo) in TARGET:
        if (y, mo) in my_ret and (y, mo) in mcp_ret:
            diff = abs(my_ret[(y, mo)] - mcp_ret[(y, mo)])
            maxdiff = max(maxdiff, diff)
            print(f"{code} {y}-{mo:02d}: my={my_ret[(y,mo)]:.6f} mcp={mcp_ret[(y,mo)]:.6f} diff={diff:.2e}")
print("MAX DIFF:", maxdiff)
print("VALIDATION", "PASS" if maxdiff < 1e-4 else "FAIL")
