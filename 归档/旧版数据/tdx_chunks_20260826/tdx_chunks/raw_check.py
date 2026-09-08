import datetime, calendar
from pytdx.hq import TdxHq_API

codes = ['000960','000733','000630','002353']
def mkt(c):
    if c[0]=='6': return 1
    if c[0] in ('4','8'): return 2
    return 0
api=TdxHq_API()
api.connect('180.153.18.170',7709)
for code in codes:
    bars=api.get_security_bars(6, mkt(code), code, 0, 20)
    print("===",code,"raw monthly close (year-month-day : close) ===")
    for b in sorted(bars,key=lambda x:(x['year'],x['month'],x['day'])):
        if (b['year'],b['month']) in [(2025,12),(2026,1),(2026,2),(2026,3),(2026,4),(2026,5),(2026,6)]:
            print(f"  {b['year']}-{b['month']:02d}-{b['day']:02d}  raw_close={b['close']}")
