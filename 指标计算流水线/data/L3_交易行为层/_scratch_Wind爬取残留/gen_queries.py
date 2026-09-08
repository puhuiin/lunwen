#!/usr/bin/env python3
# 为指定年份打印 7 个批次的查询串（3x50 + 4x15 结构，与已验证稳定模式一致）
import sys, os
BASE = os.path.dirname(os.path.abspath(__file__))
codes = []
with open(os.path.join(BASE, "codes_of.txt"), encoding="utf-8") as f:
    for line in f:
        c = line.strip()
        if c:
            codes.append(c)
assert len(codes) == 200, f"codes count={len(codes)}"

def batch(idxs):
    return [codes[i] for i in idxs]

# B1 1-50, B2 51-100, B3 101-150 (0-based: 0-49,50-99,100-149)
# S1 151-165, S2 166-180, S3 181-195, S4 196-200 (0-based:150-164,165-179,180-194,195-199)
groups = {
    "B1": list(range(0, 50)),
    "B2": list(range(50, 100)),
    "B3": list(range(100, 150)),
    "S1": list(range(150, 165)),
    "S2": list(range(165, 180)),
    "S3": list(range(180, 195)),
    "S4": list(range(195, 200)),
}

year = sys.argv[1] if len(sys.argv) > 1 else "2019"
for g, idxs in groups.items():
    cs = batch(idxs)
    q = f"以下基金 {year}年的报告期持仓换手率（百分比）：" + "、".join(cs) + "，分别给出各基金数值"
    print(f"=== {g} ({len(cs)}) ===")
    print(q)
    print()
