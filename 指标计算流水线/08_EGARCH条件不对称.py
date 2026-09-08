# -*- coding: utf-8 -*-
"""步骤 08 — EGARCH 条件不对称（基金层稳健性控制变量）

目的
----
RiskAsym = σ(盈利期收益) − σ(亏损期收益) 是「非条件」波动不对称（行为学构念：
前景理论下的风险承担不对称 / 锦标赛动机）。Bekaert & Wu(2000) 等企业层研究用
非对称 GARCH 拆解「条件」波动不对称（杠杆效应 vs 波动反馈）。两者是不同层级
的构念，但直接可比性存疑：RiskAsym 能否被「条件杠杆效应」机械解释？

本步为每只面板基金拟合 EGARCH(1,1)，提取条件波动非对称系数 γ：
    log(σ²_t) = ω + α(|z_{t-1}|−E|z|) + γ·z_{t-1} + β·log(σ²_{t-1})
  - γ < 0 表示杠杆效应：同等幅度的负冲击比正冲击更放大波动；
  - γ 与 RiskAsym 的符号/显著关系，决定 RiskAsym 是否被条件杠杆「吸收」。

若控制 egarch_gamma 后，RiskAsym 对 future_return 的预测力（系数与 t 值）仍显著，
则强证据支持 RiskAsym 是行为学构念而非底层股票杠杆效应的机械穿透。

数据：L4_风险应对层/基金净值历史_全量.csv（日净值/日收益）
输出：
  output/EGARCH_基金层不对称.csv       基金层 EGARCH trait（gamma/alpha/beta/omega/持久性/拟合状态）
  output/主分析面板_含EGARCH.csv       合并 gamma 后的派生面板（不覆盖主面板_重建.csv）
  output/EGARCH稳健性回归.csv          控制 EGARCH 前后 RiskAsym 显著性对比表
"""
import os
import warnings

import numpy as np
import pandas as pd
import statsmodels.api as sm
from arch import arch_model

warnings.filterwarnings("ignore")
import lib_metrics as M

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "output")
os.makedirs(OUT, exist_ok=True)


def load_panel_funds():
    panel = pd.read_csv(os.path.join(OUT, "主分析面板_重建.csv"), dtype={"fund_code": str})
    return set(int(c) for c in panel["fund_code"].unique())


def load_daily_returns(panel_funds):
    """与 lib_metrics.load_skeleton 完全一致的日收益派生逻辑：
    有 daily_return 者保留原值(/100)，缺失者由 nav.pct_change 补齐。"""
    nav = pd.read_csv(M.D("L4_风险应对层", "基金净值历史_全量.csv"), encoding="utf-8-sig")
    nav["date"] = pd.to_datetime(nav["date"], errors="coerce")
    nav = nav.dropna(subset=["date"]).sort_values(["fund_code", "date"])
    nav["nav"] = pd.to_numeric(nav["nav"], errors="coerce")
    nav["daily_return"] = pd.to_numeric(nav["daily_return"], errors="coerce")
    nav["ret"] = nav.groupby("fund_code")["nav"].pct_change()
    has = nav["daily_return"].notna()
    nav.loc[has, "ret"] = nav.loc[has, "daily_return"] / 100.0
    nav = nav.dropna(subset=["ret"])
    nav["fc"] = nav["fund_code"].astype(int)
    nav = nav[nav["fc"].isin(panel_funds)]
    return nav[["fc", "date", "ret"]]


def fit_egarch(returns, min_obs=250):
    """对单只基金日收益拟合 EGARCH(1,1)，返回非对称系数等。失败返回 None。"""
    if len(returns) < min_obs:
        return None
    r = np.asarray(returns, dtype=float)
    # 注意：arch 8.0.0 的 EGARCH 非对称项由 o（非 q）控制；p=1,q=1 会静默省略 gamma。
    # 必须 p=1, o=1, q=1 才能得到 gamma[1]（条件波动非对称 / 杠杆系数）。
    try:
        am = arch_model(r, mean="Constant", lags=0, vol="EGARCH",
                        p=1, o=1, q=1, dist="normal", rescale=False)
        res = am.fit(disp="off", show_warning=False)
    except Exception:
        try:
            am = arch_model(r, mean="Zero", vol="EGARCH", p=1, o=1, q=1, dist="normal")
            res = am.fit(disp="off", show_warning=False)
        except Exception:
            return None
    p = res.params
    # EGARCH(1,1) 波动率参数顺序：omega, alpha[1], gamma[1], beta[1]
    try:
        omega = float(p["omega"]); alpha = float(p["alpha[1]"])
        gamma = float(p["gamma[1]"]); beta = float(p["beta[1]"])
        gamma_t = float(res.tvalues["gamma[1]"])
    except Exception:
        vals = np.asarray(p.values, dtype=float)
        omega, alpha, gamma, beta = vals[0], vals[1], vals[2], vals[3]
        try:
            gamma_t = float(np.asarray(res.tvalues.values, dtype=float)[2])
        except Exception:
            gamma_t = np.nan
    persistence = alpha + beta  # EGARCH 对数方差冲击持久性 ≈ α+β
    return dict(egarch_omega=omega, egarch_alpha=alpha, egarch_gamma=gamma,
                egarch_beta=beta, egarch_persistence=persistence,
                egarch_gamma_t=gamma_t, n_obs=len(r))


def main():
    pf = load_panel_funds()
    print(">> [08] 面板基金数:", len(pf))
    nav = load_daily_returns(pf)
    print(">> [08] 可用日收益基金数:", nav["fc"].nunique())

    rows = []
    for fc, g in nav.groupby("fc"):
        r = g.sort_values("date")["ret"].astype(float).values
        d = fit_egarch(r)
        rec = {"fund_code": fc}
        if d is None:
            for k in ["egarch_omega", "egarch_alpha", "egarch_gamma",
                      "egarch_beta", "egarch_persistence", "egarch_gamma_t", "n_obs"]:
                rec[k] = np.nan
            rec["fit_ok"] = 0
        else:
            rec.update(d)
            rec["fit_ok"] = 1
        rows.append(rec)

    eg = pd.DataFrame(rows)
    eg = eg.rename(columns={"fund_code": "fc"})
    eg.to_csv(os.path.join(OUT, "EGARCH_基金层不对称.csv"),
              index=False, encoding="utf-8-sig")
    print(">> [08] 写出 EGARCH_基金层不对称.csv:", eg.shape,
          "| fit_ok =", int(eg.fit_ok.sum()), "/", len(eg))

    # 合并进派生面板（不覆盖主面板_重建.csv）
    panel = pd.read_csv(os.path.join(OUT, "主分析面板_重建.csv"), dtype={"fund_code": str})
    panel["fc"] = panel["fund_code"].astype(int)
    panel = panel.merge(eg, on="fc", how="left").drop(columns=["fc"])
    panel.to_csv(os.path.join(OUT, "主分析面板_含EGARCH.csv"),
                 index=False, encoding="utf-8-sig")
    print(">> [08] 写出 主分析面板_含EGARCH.csv:", panel.shape)

    run_robustness(panel)


def _ols_cluster(y, X, groups):
    try:
        return sm.OLS(y, X).fit(cov_type="cluster", cov_kwds={"groups": groups})
    except Exception:
        return sm.OLS(y, X).fit(cov_type="HC1")


def run_robustness(panel):
    d = panel.dropna(subset=["future_return", "risk_asym"]).copy()
    d["log_aum"] = np.log(d["avg_aum"].clip(lower=1.0))
    d["log_age"] = d["log_fund_age"]
    d["rv"] = d["return_volatility"]
    need = ["future_return", "risk_asym", "egarch_gamma", "log_aum", "log_age", "rv"]
    # 样本构成诊断：逐列非缺失基金数，解释回归样本为何收窄
    print(">> [08] 各必需列非缺失基金数（面板 400 只）：")
    for c in ["risk_asym", "future_return", "return_volatility", "egarch_gamma"]:
        print(f"      {c}: {panel[c].notna().sum()} obs / {panel.loc[panel[c].notna(),'fund_code'].nunique()} funds")
    d = d.dropna(subset=need)
    print(f">> [08] 稳健性回归样本: {len(d)} obs, {d['fund_code'].nunique()} funds")

    y = d["future_return"]
    X0 = sm.add_constant(d[["risk_asym", "log_aum", "log_age", "rv"]])
    X1 = sm.add_constant(d[["risk_asym", "egarch_gamma", "log_aum", "log_age", "rv"]])

    m0 = _ols_cluster(y, X0, d["fund_code"].values)
    m1 = _ols_cluster(y, X1, d["fund_code"].values)

    def row(model, label):
        b_r = float(model.params["risk_asym"]); t_r = float(model.tvalues["risk_asym"])
        if "egarch_gamma" in model.params:
            b_g = float(model.params["egarch_gamma"]); t_g = float(model.tvalues["egarch_gamma"])
        else:
            b_g = t_g = np.nan
        return dict(model=label, risk_asym_b=b_r, risk_asym_t=t_r,
                    egarch_gamma_b=b_g, egarch_gamma_t=t_g,
                    n=int(model.nobs), r2=float(model.rsquared))

    res = pd.DataFrame([row(m0, "M1: RA + 控制变量"),
                        row(m1, "M2: RA + EGARCHγ + 控制变量")])
    res.to_csv(os.path.join(OUT, "EGARCH稳健性回归.csv"),
               index=False, encoding="utf-8-sig")

    print("\n=== 稳健性回归：future_return ~ risk_asym (+/- egarch_gamma) + 控制 ===")
    print(res.to_string(index=False))

    corr = d[["risk_asym", "egarch_gamma"]].corr().iloc[0, 1]
    print(f"\nrisk_asym ↔ egarch_gamma 相关: {corr:.4f}")
    print(f"egarch_gamma 均值: {d['egarch_gamma'].mean():.4f} （负=杠杆效应）")
    print(f"  γ<0（存在杠杆效应）基金占比: {(d['egarch_gamma'] < 0).mean()*100:.1f}%")
    print(f"  γ 统计显著(|t|>1.96) 基金占比: {(d['egarch_gamma_t'].abs() > 1.96).mean()*100:.1f}%")


if __name__ == "__main__":
    main()
