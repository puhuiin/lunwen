import os, csv, calendar

OUT = r"D:/Desktop/基金经理行为分析研究/代码/tdx_chunks/chunk_07_out.csv"

# code -> list of (datestr YYYYMMDD, close float) as returned (will be sorted)
DATA = {
    "000063": [("20251231",37.43),("20260130",38.080002),("20260227",38.240002),("20260331",32.029999),("20260430",36.290001),("20260529",36.310001),("20260630",35.779999),("20260731",33.810001),("20260813",35.080002)],
    "000625": [("20251231",11.74),("20260130",11.0),("20260227",10.94),("20260331",9.88),("20260430",9.41),("20260529",7.8),("20260630",7.05),("20260731",7.87),("20260813",7.27)],
    "000725": [("20251231",4.15),("20260130",4.31),("20260227",4.42),("20260331",3.85),("20260430",4.02),("20260529",5.05),("20260630",8.68),("20260731",5.51),("20260813",5.86)],
}

def norm_month_end(dstr):
    y=int(dstr[:4]); m=int(dstr[4:6])
    last=calendar.monthrange(y,m)[1]
    return f"{y:04d}-{m:02d}-{last:02d}"

rows_out=[]
for code, pairs in DATA.items():
    pairs=sorted(pairs, key=lambda x:x[0])
    for i in range(1,len(pairs)):
        d=norm_month_end(pairs[i][0])
        y=int(d[:4]); m=int(d[5:7])
        if (y,m) < (2026,1) or (y,m) > (2026,6):
            continue
        prev=float(pairs[i-1][1]); cur=float(pairs[i][1])
        if prev==0:
            continue
        ret=cur/prev-1
        rows_out.append((code,d,ret))

write_header = not os.path.exists(OUT)
with open(OUT,"a",newline="") as f:
    w=csv.writer(f)
    if write_header:
        w.writerow(["stock_code","date","monthly_return"])
    for r in rows_out:
        w.writerow(r)
print("batch1 appended", len(rows_out), "rows; header_written=", write_header)
