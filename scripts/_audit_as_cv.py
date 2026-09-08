# -*- coding: utf-8 -*-
"""重算原始AS(单一沪深300基准) vs AS_improved(复合基准) 的变异系数对比
验证稿件声称: CV 0.0495 -> 0.0821 (+65.9%), 最常见值占比 61.8% -> 0.2%"""
import sys
sys.path.insert(0, '指标计算流水线')
import pandas as pd
import lib_metrics as M

bench_full = M.load_benchmark_weights()
hs = pd.read_csv(M.D("L2_持仓偏离层", "沪深300成分股权重_真实.csv"), encoding="utf-8-sig")
hs300 = hs[["stock_code", "bench_weight"]].copy()
hs300["w"] = pd.to_numeric(hs300["bench_weight"], errors="coerce")
hs300 = hs300.dropna(subset=["w"])
hs300 = hs300.groupby("stock_code")["w"].sum().reset_index()
hs300["w"] = hs300["w"] / hs300["w"].sum()
hs300 = hs300.set_index("stock_code")["w"]

h = pd.read_csv(M.D("L2_持仓偏离层", "基金持仓明细_全量修正版_v3.csv"), encoding="utf-8-sig")
h["w_fund"] = pd.to_numeric(h["hold_ratio"], errors="coerce").fillna(0) / 100.0
h["report_date"] = M.to_panel_date(h["report_date"])

def calc_as(bench):
    rows = []
    for (fund, rd), g in h.groupby(["fund_code", "report_date"]):
        merged = pd.merge(
            g[["stock_code", "w_fund"]],
            bench.rename("w_bench").reset_index(),
            on="stock_code", how="outer").fillna(0)
        v = 0.5 * (merged["w_fund"] - merged["w_bench"]).abs().sum()
        rows.append((fund, rd, min(v, 1.0)))
    return pd.DataFrame(rows, columns=["fund_code", "report_date", "as"])

as_raw = calc_as(hs300)
as_imp = calc_as(bench_full)

for name, d in [("原始AS(沪深300单基准)", as_raw), ("AS_improved(复合基准)", as_imp)]:
    x = d["as"].dropna()
    mode_share = x.value_counts(normalize=True).iloc[0] * 100
    print("%s: N=%d 基金=%d mean=%.4f sd=%.4f CV=%.4f 最常见值占比=%.1f%%" % (
        name, len(x), d["fund_code"].nunique(), x.mean(), x.std(), x.std()/x.mean(), mode_share))
