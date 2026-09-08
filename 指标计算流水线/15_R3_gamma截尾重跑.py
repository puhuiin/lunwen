# -*- coding: utf-8 -*-
"""15_R3_gamma截尾重跑.py —— R3 条件不对称稳健性：对 egarch_gamma 截尾后重跑。

问题（前次诊断）：egarch_gamma 中位 −0.0033，但存在 1 只基金的极端值 −8869，
把 1%/99% 分位数拉到 [−0.086, +0.069] 之外。原 08 的 M2 中 egarch_gamma
β=1.35e-5、t=26.3 的「显著」实质由该极端值放大标度所致，不可信。

本步：直接读取 08 已合并好的 主分析面板_含EGARCH.csv（无需重拟合 EGARCH），
对 egarch_gamma 在 1%/99% 截尾，重跑 M1(RA+控制) vs M2(RA+γ_wins+控制)，
DV=future_return，基金聚类 SE。并报告截尾前后 γ 的描述与显著基金占比。

输出：output/R3_gamma截尾重跑.csv
"""
import os
import numpy as np
import pandas as pd
import statsmodels.api as sm

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "output")
os.makedirs(OUT, exist_ok=True)
PANEL = os.path.join(OUT, "主分析面板_含EGARCH.csv")


def cluster(y, X, groups):
    try:
        return sm.OLS(y, X).fit(cov_type="cluster", cov_kwds={"groups": groups})
    except Exception:
        return sm.OLS(y, X).fit(cov_type="HC1")


def main():
    panel = pd.read_csv(PANEL, dtype={"fund_code": str})
    panel["log_aum"] = np.log(panel["avg_aum"].clip(lower=1.0))
    panel["log_age"] = panel["log_fund_age"]
    panel["rv"] = panel["return_volatility"]

    # 截尾
    g = panel["egarch_gamma"]
    lo, hi = g.quantile(.01), g.quantile(.99)
    panel["egarch_gamma_wins"] = g.clip(lo, hi)

    print(">> [15] 截尾前 γ: min/max = %.3f / %.3f" % (g.min(), g.max()))
    print(">> [15] 截尾后 γ_wins: min/max = %.4f / %.4f" % (panel.egarch_gamma_wins.min(), panel.egarch_gamma_wins.max()))

    d = panel.dropna(subset=["future_return", "risk_asym", "egarch_gamma_wins",
                             "log_aum", "log_age", "rv"]).copy()
    print(f">> [15] 重跑样本: {len(d)} obs, {d['fund_code'].nunique()} funds")

    y = d["future_return"]
    X0 = sm.add_constant(d[["risk_asym", "log_aum", "log_age", "rv"]])
    X1 = sm.add_constant(d[["risk_asym", "egarch_gamma_wins", "log_aum", "log_age", "rv"]])
    m0 = cluster(y, X0, d["fund_code"].values)
    m1 = cluster(y, X1, d["fund_code"].values)

    def row(model, label):
        b_r = float(model.params["risk_asym"]); t_r = float(model.tvalues["risk_asym"])
        if "egarch_gamma_wins" in model.params:
            b_g = float(model.params["egarch_gamma_wins"]); t_g = float(model.tvalues["egarch_gamma_wins"])
        else:
            b_g = t_g = np.nan
        return dict(model=label, risk_asym_b=round(b_r, 5), risk_asym_t=round(t_r, 2),
                    egarch_gamma_b=round(b_g, 6), egarch_gamma_t=round(t_g, 2),
                    n=int(model.nobs), r2=round(float(model.rsquared), 4))

    res = pd.DataFrame([row(m0, "M1: RA + 控制变量"),
                        row(m1, "M2: RA + γ_wins(1/99) + 控制变量")])
    res.to_csv(os.path.join(OUT, "R3_gamma截尾重跑.csv"), index=False, encoding="utf-8-sig")

    print("\n=== R3 重跑（γ 已 1/99 截尾）: future_return ~ risk_asym (+/- γ) + 控制 ===")
    print(res.to_string(index=False))

    corr = d[["risk_asym", "egarch_gamma_wins"]].corr().iloc[0, 1]
    gt = d["egarch_gamma_t"]
    print(f"\nrisk_asym ↔ γ_wins 相关: {corr:.4f}")
    print(f"γ_wins 均值: {d['egarch_gamma_wins'].mean():.5f}（负=杠杆效应）")
    print(f"  γ<0（存在杠杆效应）基金占比: {(d['egarch_gamma_wins'] < 0).mean()*100:.1f}%")
    if gt.notna().any():
        print(f"  γ 统计显著(|t|>1.96) 基金占比（截尾前）: {(gt.abs() > 1.96).mean()*100:.1f}%")
    print("\n已写出: output/R3_gamma截尾重跑.csv")


if __name__ == "__main__":
    main()
