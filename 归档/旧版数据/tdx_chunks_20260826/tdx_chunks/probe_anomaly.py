from pytdx.hq import TdxHq_API
api = TdxHq_API()
api.connect('180.153.18.170', 7709, time_out=8)
for code in ['565650','920438']:
    print("="*40, code)
    for mkt in [0,1,2]:
        try:
            bars = api.get_security_bars(6, mkt, code, 0, 5)  # monthly
            print("  mkt=%d monthly n=%s sample=%s" % (mkt, len(bars or []), (bars[:2] if bars else None)))
            dbars = api.get_security_bars(4, mkt, code, 0, 5)  # daily
            print("  mkt=%d daily   n=%s sample=%s" % (mkt, len(dbars or []), (dbars[:2] if dbars else None)))
        except Exception as e:
            print("  mkt=%d ERR %s" % (mkt, e))
    # also try xdxr
    for mkt in [0,1,2]:
        try:
            x = api.get_xdxr_info(mkt, code)
            print("  mkt=%d xdxr n=%s" % (mkt, len(x or [])))
        except Exception as e:
            print("  mkt=%d xdxr ERR %s" % (mkt, e))
