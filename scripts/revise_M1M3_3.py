# -*- coding: utf-8 -*-
"""第三轮: DE 基金覆盖统一为诚实面板 399; 行97 数据概述三指标基金数统一。"""
import io

SRC = r"D:\Desktop\基金经理行为分析研究\merged_manuscript.html"
with io.open(SRC, "r", encoding="utf-8") as f:
    t = f.read()
orig = t

repls = [
    # DE 覆盖 385 -> 399 (DE 自身基金覆盖)
    ("46.5%（385基金）", "46.5%（399基金）"),
    # 行384 叙述
    ("覆盖385只基金。由于持仓数据的披露频率和完整性限制，DE指标的覆盖率为46.5%。",
     "覆盖399只基金。由于持仓数据的披露频率和完整性限制，DE指标的覆盖率为46.5%。"),
    # 行97 数据概述: RA/LSV/DE 基金数
    ("RiskAsym来自基金净值面板（387基金），LSV来自全持仓数据（357基金），DE来自个股收盘价与持仓数据（355基金）",
     "RiskAsym来自基金净值面板（386基金），LSV来自全持仓数据（400基金），DE来自个股收盘价与持仓数据（399基金）"),
]

for o, n in repls:
    assert o in t, "NOT FOUND: " + o[:60]
    t = t.replace(o, n)

with io.open(SRC, "w", encoding="utf-8") as f:
    f.write(t)

print("LEN", len(orig), len(t))
for bad in ["385基金", "355基金", "357基金", "387基金"]:
    print(f"  residual {bad!r}: {t.count(bad)}")
print("done")
