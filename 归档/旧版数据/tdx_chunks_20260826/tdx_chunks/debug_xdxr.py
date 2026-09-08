import datetime
from pytdx.hq import TdxHq_API

def mkt(c):
    if c[0] == '6': return 1
    if c[0] in ('4','8'): return 2
    return 0
api = TdxHq_API()
api.connect('180.153.18.170', 7709, time_out=8)

for code in ['000630','000733','000960']:
    print("="*60)
    print("CODE", code)
    x = api.get_xdxr_info(mkt(code), code)
    print("RAW XDXR records (count=%d):" % len(x or []))
    for e in (x or []):
        print("  ", {k: e.get(k) for k in ['category','year','month','day','date','fenhong','songzhuangu','peigu','peigujia'] if k in e})
    # daily bars around to see close_before
    bars = api.get_security_bars(4, mkt(code), code, 0, 60)
    bars = sorted(bars, key=lambda b:(b['year'],b['month'],b['day']))
    print("Last daily bars:")
    for b in bars[-10:]:
        print("   %d-%02d-%02d close=%s" % (b['year'],b['month'],b['day'],b['close']))
    # show monthly raw for Dec2025..Jun2026
    mb = api.get_security_bars(6, mkt(code), code, 0, 12)
    print("Monthly raw (last 12):")
    for b in sorted(mb, key=lambda b:(b['year'],b['month'],b['day'])):
        if (b['year'],b['month']) >= (2025,12):
            print("   %d-%02d-%02d close=%s" % (b['year'],b['month'],b['day'],b['close']))
