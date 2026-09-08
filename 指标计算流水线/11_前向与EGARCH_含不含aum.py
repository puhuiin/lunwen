# -*- coding: utf-8 -*-
"""
11_前向与EGARCH_含不含aum.py
- 修复 4Q_no_aum 的 NaN（cluster 协方差在大样本/年份FE下失败 → 回退 HC1）。
- 复算 EGARCH 前向（future_return=下一季度 quarter_return）含/不含 avg_aum，
  服务于 Task #72（avg_aum 覆盖上限 200 基金 → 不含则扩到全 L5 可用基金）。
输出：output/前向与EGARCH_含不含aum.csv
"""
import os
import warnings
import numpy as np
import pandas as pd
import statsmodels.api as sm
from arch import arch_model

warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "output")
PANEL = os.path.join(OUT, "主分析面板_重建.csv")


def load():
    return pd.read_csv(PANEL, dtype={"fund_code": str})


def fit_egarch(returns, min_obs=250):
    if len(returns) < min_obs:
        return None
    r = np.asarray(returns, dtype=float)
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
    try:
        gamma = float(p["gamma[1]"]); gamma_t = float(res.tvalues["gamma[1]"])
    except Exception:
        vals = np.asarray(p.values, dtype=float)
        gamma = float(vals[2]); gamma_t = float(np.asarray(res.tvalues.values, dtype=float)[2])
    return dict(egarch_gamma=gamma, egarch_gamma_t=gamma_t, n_obs=len(r))


def ols_robust(y, X, groups):
    """优先 cluster；cluster 失败回退 HC1；HC1 仍失败（如年份FE导致奇异）回退普通 OLS。"""
    try:
        m = sm.OLS(y, X).fit(cov_type="cluster", cov_kwds={"groups": groups})
        if np.any(np.isnan(m.tvalues.values)):
            raise ValueError("cluster produced NaN t")
        return m, "cluster"
    except Exception:
        pass
    try:
        m = sm.OLS(y, X).fit(cov_type="HC1")
        if np.any(np.isnan(m.tvalues.values)):
            raise ValueError("HC1 produced NaN t")
        return m, "HC1"
    except Exception:
        m = sm.OLS(y, X).fit()  # 普通 OLS（年份FE在大样本下数值奇异时的兜底）
        return m, "OLS"


def main():
    panel = load()
    panel["log_aum"] = np.log(panel["avg_aum"].clip(lower=1.0))
    panel["log_age"] = panel["log_fund_age"]
    panel["year_c"] = panel["year"].astype(int)

    rows = []
    # ---------- (A) 前向回归 含/不含 avg_aum ----------
    d = panel.sort_values(["fund_code", "year", "quarter"]).copy()

    def roll4(s):
        return s.shift(-1).rolling(4, min_periods=4).mean()

    d["fut1q"] = d.groupby("fund_code")["excess_return"].shift(-1)
    d["fut4q"] = d.groupby("fund_code")["excess_return"].transform(roll4)

    for spec, sub, ivs in [
        ("4Q_with_aum", d.dropna(subset=["risk_asym", "lsv", "de", "log_aum", "log_age", "year_c", "fut4q"]),
         ["risk_asym", "lsv", "de", "log_aum", "log_age", "year_c"]),
        ("1Q_with_aum", d.dropna(subset=["risk_asym", "lsv", "de", "log_aum", "log_age", "year_c", "fut1q"]),
         ["risk_asym", "lsv", "de", "log_aum", "log_age", "year_c"]),
        ("4Q_no_aum", d.dropna(subset=["risk_asym", "lsv", "de", "log_age", "year_c", "fut4q"]),
         ["risk_asym", "lsv", "de", "log_age", "year_c"]),
        ("1Q_no_aum", d.dropna(subset=["risk_asym", "lsv", "de", "log_age", "year_c", "fut1q"]),
         ["risk_asym", "lsv", "de", "log_age", "year_c"]),
    ]:
        dv = "fut4q" if spec.startswith("4Q") else "fut1q"
        X = sm.add_constant(sub[ivs])
        m, kind = ols_robust(sub[dv], X, sub["fund_code"].values)
        row = {"block": "FORWARD", "model": spec, "dv": dv, "se": kind,
               "N": int(m.nobs), "R2": round(m.rsquared, 4)}
        for iv in ivs:
            row[f"{iv}_b"] = round(float(m.params[iv]), 4)
            row[f"{iv}_t"] = round(float(m.tvalues[iv]), 2)
        rows.append(row)
        print(f"[FORWARD {spec}] N={row['N']} R2={row['R2']} se={kind} | "
              f"RA={row['risk_asym_b']:+.4f}(t={row['risk_asym_t']:+.2f}) "
              f"LSV={row['lsv_b']:+.4f}(t={row['lsv_t']:+.2f}) "
              f"DE={row['de_b']:+.4f}(t={row['de_t']:+.2f})")

    # ---------- (B) EGARCH 前向（future_return=下一季度，面板层，与 08 口径一致）----------
    # 关键：egarch_gamma 是「基金层」trait，须按 fund_code 广播到该基金所有季度行，
    # 不得与含重复 fund_code 的面板做多对多合并（会导致 N 爆炸）。
    eg = pd.read_csv(os.path.join(OUT, "EGARCH_基金层不对称.csv"), dtype={"fc": str})
    eg = eg.rename(columns={"fc": "fund_code"})
    eg = eg[["fund_code", "egarch_gamma", "egarch_gamma_t", "fit_ok"]].copy()

    # 面板层（保留季度变异，与 08 与 §4.2.3 面板前向一致），按 fund_code 广播 gamma
    p = panel.merge(eg[["fund_code", "egarch_gamma"]], on="fund_code", how="left")
    p["rv"] = p["return_volatility"]
    p["year_c"] = p["year"].astype(int)

    for spec, need, ivs in [
        ("EGARCH_fwd_with_aum", ["future_return", "risk_asym", "egarch_gamma", "log_aum", "log_age", "rv"],
         ["risk_asym", "egarch_gamma", "log_aum", "log_age", "rv"]),
        ("EGARCH_fwd_no_aum", ["future_return", "risk_asym", "egarch_gamma", "log_age", "rv"],
         ["risk_asym", "egarch_gamma", "log_age", "rv"]),
    ]:
        sub = p.dropna(subset=need).copy()
        X = sm.add_constant(sub[ivs])
        m, kind = ols_robust(sub["future_return"], X, sub["fund_code"].values)
        row = {"block": "EGARCH_FWD", "model": spec, "dv": "future_return", "se": kind,
               "N": int(m.nobs), "R2": round(m.rsquared, 4)}
        for iv in ivs:
            row[f"{iv}_b"] = round(float(m.params[iv]), 4)
            row[f"{iv}_t"] = round(float(m.tvalues[iv]), 2)
        rows.append(row)
        print(f"[EGARCH {spec}] N={row['N']} R2={row['R2']} se={kind} | "
              f"RA={row['risk_asym_b']:+.4f}(t={row['risk_asym_t']:+.2f}) "
              f"gamma={row['egarch_gamma_b']:+.4f}(t={row['egarch_gamma_t']:+.2f})")

    res = pd.DataFrame(rows)
    res.to_csv(os.path.join(OUT, "前向与EGARCH_含不含aum.csv"), index=False)
    print("\n写出 output/前向与EGARCH_含不含aum.csv")


if __name__ == "__main__":
    main()
