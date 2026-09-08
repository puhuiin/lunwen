# -*- coding: utf-8 -*-
"""
10_前向回归核对.py
独立、透明地重算手稿 §4.2.3 前向预测表（4季度均值 / 1季度），并补齐
无 avg_aum（突破200基金上限）版本，作为 Option A 后手稿表格的可信来源。

构造（与手稿一致）：
  fut1q = 同基金 excess_return 滞后1期（下一季度）
  fut4q = 同基金 未来连续4季度 excess_return 的均值
控制：risk_asym, lsv, de, log_aum(可选), log_fund_age, 年份FE
标准误：基金层面聚类稳健

同时复算 EGARCH 前向（future_return=下一季度 quarter_return）含/不含 avg_aum，
服务于 Task #72（avg_aum 覆盖上限）。
"""
import os
import numpy as np
import pandas as pd
import statsmodels.api as sm

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "output")
PANEL = os.path.join(OUT, "主分析面板_重建.csv")


def load():
    df = pd.read_csv(PANEL, dtype={"fund_code": str})
    df["log_aum"] = np.log(df["avg_aum"].clip(lower=1.0))
    df["log_age"] = df["log_fund_age"]
    return df


def build_forward(df):
    d = df.sort_values(["fund_code", "year", "quarter"]).copy()

    def roll4(s):
        return s.shift(-1).rolling(4, min_periods=4).mean()

    d["fut1q"] = d.groupby("fund_code")["excess_return"].shift(-1)
    d["fut4q"] = d.groupby("fund_code")["excess_return"].transform(roll4)
    d["year_c"] = d["year"].astype(int)
    return d


def ols_clu(data, dv, ivs):
    # 修复：前向 DV(fut4q/fut1q) 在每基金末 3-4 季为 NaN，须联合 dropna 否则 y 含 NaN → 结果全 NaN。
    sub = data[[dv] + ivs + ["fund_code"]].dropna()
    X = sm.add_constant(sub[ivs])
    m = sm.OLS(sub[dv], X).fit(cov_type="cluster", cov_kwds={"groups": sub["fund_code"].values})
    row = {"dv": dv, "N": int(m.nobs), "R2": round(m.rsquared, 4)}
    for iv in ivs:
        row[f"{iv}_b"] = round(float(m.params[iv]), 4)
        row[f"{iv}_t"] = round(float(m.tvalues[iv]), 2)
    return row


def main():
    df = load()
    d = build_forward(df)

    # 含 avg_aum（N≈1355，与手稿表 N=1,355 一致）
    fe = d.dropna(subset=["risk_asym", "lsv", "de", "log_aum", "log_age", "year_c"]).copy()
    ivs = ["risk_asym", "lsv", "de", "log_aum", "log_age", "year_c"]
    r4 = ols_clu(fe, "fut4q", ivs)
    r1 = ols_clu(fe, "fut1q", ivs)

    # 不含 avg_aum（突破200基金上限，扩到全 L5 可用基金）
    fe2 = d.dropna(subset=["risk_asym", "lsv", "de", "log_age", "year_c"]).copy()
    ivs2 = ["risk_asym", "lsv", "de", "log_age", "year_c"]
    r4b = ols_clu(fe2, "fut4q", ivs2)
    r1b = ols_clu(fe2, "fut1q", ivs2)

    res = pd.DataFrame([r4, r1, r4b, r1b])
    res.insert(0, "model", ["FWD_4Q_with_aum", "FWD_1Q_with_aum", "FWD_4Q_no_aum", "FWD_1Q_no_aum"])
    res.to_csv(os.path.join(OUT, "前向回归核对结果.csv"), index=False)

    pd.set_option("display.width", 220)
    print("==== 前向回归核对（当前面板）====")
    print(res.to_string(index=False))

    print("\n--- 与手稿 §4.2.3 表的对照（含 aum, N=1,355）---")
    print(f"  risk_asym 4Q : {r4['risk_asym_b']:+.4f} (t={r4['risk_asym_t']:+.2f})  | 手稿旧值 +0.127 (t=4.95)")
    print(f"  risk_asym 1Q : {r1['risk_asym_b']:+.4f} (t={r1['risk_asym_t']:+.2f})  | 手稿旧值 -0.077 (t=-1.36)")
    print(f"  lsv       4Q : {r4['lsv_b']:+.4f} (t={r4['lsv_t']:+.2f})  | 手稿 +0.057 (t=1.81)")
    print(f"  lsv       1Q : {r1['lsv_b']:+.4f} (t={r1['lsv_t']:+.2f})  | 手稿 +0.110 (t=1.61)")
    print(f"  de        4Q : {r4['de_b']:+.4f} (t={r4['de_t']:+.2f})  | 手稿旧值 -0.004 (t=-1.06)")
    print(f"  de        1Q : {r1['de_b']:+.4f} (t={r1['de_t']:+.2f})  | 手稿旧值 +0.010 (t=1.01)")
    print(f"  N/R2 4Q : {r4['N']} / {r4['R2']}  1Q : {r1['N']} / {r1['R2']}")
    print("\n--- 不含 avg_aum（更大样本）---")
    print(f"  risk_asym 4Q(no_aum) : {r4b['risk_asym_b']:+.4f} (t={r4b['risk_asym_t']:+.2f}) N={r4b['N']}")
    print(f"  risk_asym 1Q(no_aum) : {r1b['risk_asym_b']:+.4f} (t={r1b['risk_asym_t']:+.2f}) N={r1b['N']}")
    print(f"  de        4Q(no_aum) : {r4b['de_b']:+.4f} (t={r4b['de_t']:+.2f})")
    print(f"  de        1Q(no_aum) : {r1b['de_b']:+.4f} (t={r1b['de_t']:+.2f})")


if __name__ == "__main__":
    main()
