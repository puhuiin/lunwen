# -*- coding: utf-8 -*-
"""把 _missing_a_stocks.txt(851) 生成 TuShare 月线批量查询文件。
规则: 000/001/002/003/300/301->.SZ; 600/601/603/605/688/689->.SH; 8xx/920/430/400->.BJ
日期范围: 2006-01-01 ~ 2026-08-31 (与主表一致)
"""
import os
BASE = r"d:\Desktop\基金经理行为分析研究\指标计算流水线\data\股价行情"
OUT = os.path.join(BASE, "em_parsed", "ts_batches")
os.makedirs(OUT, exist_ok=True)

def suffix(code):
    if code[:3] in ("600","601","603","605","688","689"):
        return "SH"
    if code[:3] in ("000","001","002","003","300","301"):
        return "SZ"
    return "BJ"  # 8xx/920/430/400

codes = [c.strip() for c in open(os.path.join(BASE, "_missing_a_stocks.txt"), encoding="utf-8") if c.strip()]
print("缺失A股数:", len(codes))
byxf = {}
for c in codes:
    byxf.setdefault(suffix(c), []).append(c)
for xf, cs in byxf.items():
    print(f"  {xf}: {len(cs)}")

# 分批: 每批12只
BATCH = 12
batches = []
n = (len(codes) + BATCH - 1) // BATCH
for i in range(n):
    sub = codes[i*BATCH:(i+1)*BATCH]
    tscodes = ",".join(f"{c}.{suffix(c)}" for c in sub)
    batches.append((i, sub, tscodes))

meta = []
for i, sub, tscodes in batches:
    fn = os.path.join(OUT, f"ts_{i:03d}.txt")
    with open(fn, "w", encoding="utf-8") as f:
        f.write(tscodes)
    meta.append((i, sub))
    print(f"ts_{i:03d}: {len(sub)}只 = {tscodes[:60]}...")

with open(os.path.join(OUT, "_batches.txt"), "w", encoding="utf-8") as f:
    for i, sub in meta:
        f.write(f"{i}:{','.join(sub)}\n")
print("总批次数:", n)