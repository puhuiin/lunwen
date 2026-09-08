# -*- coding: utf-8 -*-
"""16_TO单边分析.py —— 换手率「单边口径能否提高覆盖率」诊断 + 单边回归。

用户问题：换手（TO）能不能采用单边（仅买/仅卖）来提高我们的覆盖率，然后做一次回归？

数据事实（已核对 主分析面板_重建.csv）：
  total_buy / total_sell 是**联合存在**的——有买入记录的季度必然同时有卖出记录
  （buy-only=0，sell-only=0，both=1800 obs），底层源文件
  data/L3_交易行为层/基金换手率_双边_含卖出.csv 本身就是双边披露。
  → 在现有源文件下，单边换手**不能**提高覆盖率：单边并集基金数 = 双边基金数 = 200 只。
    覆盖率天花板是「源文件只覆盖 200 只基金」这一结构性限制，而非单边/双边口径。

本步仍按用户要求「做一次回归」：
  1) 构造单边口径 TO_buy = total_buy/avg_aum、TO_sell = total_sell/avg_aum；
  2) 截面（基金层均值）回归 ff5_adj_return ~ TO_buy + 控制，与双边 TO_two_sided 系数对比
     （理论上 buy≈sell，单边与双边系数应几乎一致）；
  3) 额外做「买卖分解」回归 ff5_adj ~ TO_buy + TO_sell + 控制，检验买/卖侧是否不对称。

真实覆盖率提升需 CSMAR/Wind 全样本交易数据（项目 P1 项），本步据实说明。

输出：output/TO单边分析.csv
"""
import os
import numpy as np
import pandas as pd
import statsmodels.api as sm

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "output")
os.makedirs(OUT, exist_ok=True)
PANEL = os.path.join(OUT, "主分析面板_重建.csv")


def main():
    df = pd.read_csv(PANEL, dtype={"fund_code": str})
    df["log_aum"] = np.log(df["avg_aum"].clip(lower=1.0))
    aum = df["avg_aum"].replace(0, np.nan)
    df["TO_buy"] = df["total_buy"] / aum
    df["TO_sell"] = df["total_sell"] / aum

    # ---- 覆盖率诊断 ----
    bil = df["TO_two_sided"].notna()
    buy = df["TO_buy"].notna()
    sell = df["TO_sell"].notna()
    print(">> [16] 覆盖率诊断（面板 400 只）:")
    print(f"     双边 TO_two_sided 基金数 : {df.loc[bil,'fund_code'].nunique()}")
    print(f"     单边 TO_buy 基金数       : {df.loc[buy,'fund_code'].nunique()}")
    print(f"     单边 TO_sell 基金数      : {df.loc[sell,'fund_code'].nunique()}")
    print(f"     单边并集(买或卖) 基金数  : {df.loc[buy|sell,'fund_code'].nunique()}")
    print("     → 单边不能提高覆盖率（源文件双边联合披露）。")

    # ---- 基金层均值截面（镜像 R1 / 13）----
    controls = ["log_aum", "log_fund_age"]
    mean_cols = ["ff5_adj_return"] + controls + ["TO_two_sided", "TO_buy", "TO_sell"]
    fm = df.groupby("fund_code")[mean_cols].mean(numeric_only=True).reset_index()

    def ols(d, dv, ivs, label):
        sub = d[[dv] + ivs].dropna()
        if len(sub) < len(ivs) + 5:
            return []
        X = sm.add_constant(sub[ivs])
        m = sm.OLS(sub[dv], X).fit(cov_type="HC1")
        rows = []
        for v in ivs:
            rows.append({"model": label, "DV": dv, "N": int(len(sub)),
                         "var": v, "coef": round(float(m.params[v]), 5),
                         "t": round(float(m.tvalues[v]), 3),
                         "sig": "***" if abs(m.tvalues[v]) > 2.58 else ("**" if abs(m.tvalues[v]) > 1.96 else "")})
        return rows

    results = []
    results += ols(fm, "ff5_adj_return", ["TO_two_sided"] + controls, "双边TO")
    results += ols(fm, "ff5_adj_return", ["TO_buy"] + controls, "单边TO_buy")
    results += ols(fm, "ff5_adj_return", ["TO_sell"] + controls, "单边TO_sell")
    results += ols(fm, "ff5_adj_return", ["TO_buy", "TO_sell"] + controls, "买卖分解")
    res = pd.DataFrame([r for r in results if r])
    res.to_csv(os.path.join(OUT, "TO单边分析.csv"), index=False, encoding="utf-8-sig")

    for mdl in ["双边TO", "单边TO_buy", "单边TO_sell", "买卖分解"]:
        sub = res[res.model == mdl]
        if sub.empty:
            continue
        print(f"\n[{mdl}] N={int(sub.N.iloc[0])}")
        for _, r in sub.iterrows():
            print(f"   {r['var']:14s} β={r['coef']:+.5f}  t={r['t']:+.2f} {r['sig']}")
    print("\n已写出: output/TO单边分析.csv")


if __name__ == "__main__":
    main()
