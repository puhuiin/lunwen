# -*- coding: utf-8 -*-
"""
09_LSV回归重算.py
目的：在 OPTION A 修正后的【标准非负 LSV(1992)】面板上，重新计算手稿 §4.2.2/§4.2.3
      的 LSV（以及 RA/DE 一致性）回归系数，使手稿表格与流水线指标自洽。

关键修正：
  - 旧手稿表格 (lsv +0.051 t=4.81 等) 基于【旧带符号 LSV 变体】(均值为负)。
  - 现流水线 lsv 列 = 标准 LSV(1992) 非负羊群强度 (|p_j-p̄|-AF, 基金层均值恒≥0)，
    面板观测级均值 +0.096、基金级均值 +0.098、0% 基金为负。
  - 本脚本用修正后的 lsv 重跑，输出可供手稿替换的系数/t/N/R²。

输出：
  output/LSV回归重算结果.csv  (宽表，供手稿替换)
  output/LSV回归重算_诊断.csv  (覆盖率/L5完整观测等计数)
"""
import pandas as pd
import numpy as np
import statsmodels.api as sm
import statsmodels.formula.api as smf

PANEL = "指标计算流水线/output/主分析面板_重建.csv"

def main():
    df = pd.read_csv(PANEL)
    # 控制变量
    df["log_aum"] = np.log(df["avg_aum"].clip(lower=1))
    df["log_fund_age"] = df["log_fund_age"]

    results = {}
    diag = {}

    # ---------- 覆盖率 / L5 完整观测 ----------
    for c in ["lsv", "de", "risk_asym", "future_return", "ff5_adj_return", "excess_return"]:
        diag[f"{c}_nonnull_obs"] = int(df[c].notna().sum())
    diag["total_obs"] = len(df)
    diag["n_funds"] = int(df["fund_code"].nunique())
    # L5 三指标同时非缺失的观测数（对应手稿 L5完整观测 1,634）
    l5_complete = df[["lsv", "de", "risk_asym"]].notna().all(axis=1)
    diag["L5_complete_obs"] = int(l5_complete.sum())
    diag["L5_complete_funds"] = int(df.loc[l5_complete, "fund_code"].nunique())
    # 覆盖率%（占全部观测）
    diag["lsv_cov_pct"] = round(100 * df["lsv"].notna().mean(), 1)
    diag["de_cov_pct"] = round(100 * df["de"].notna().mean(), 1)
    diag["ra_cov_pct"] = round(100 * df["risk_asym"].notna().mean(), 1)

    # ---------- (A) 截面基准回归（基金层均值, N=诚实基金数）----------
    # 与手稿一致：ff5_adj_return 为每只基金常数；取基金层均值。
    g = df.groupby("fund_code")
    fund = pd.DataFrame({
        "alpha": g["ff5_adj_return"].first(),          # 常数 per fund
        "excess_mean": g["excess_return"].mean(),
        "risk_asym": g["risk_asym"].mean(),
        "lsv": g["lsv"].mean(),
        "de": g["de"].mean(),
        "log_aum": g["avg_aum"].apply(lambda s: np.log(s.dropna().mean()) if s.dropna().mean() > 0 else np.nan),
        "log_fund_age": g["log_fund_age"].first(),
    }).dropna(subset=["alpha", "risk_asym", "lsv", "de", "log_aum", "log_fund_age"])
    diag["cross_section_N"] = len(fund)
    results["cross_N"] = len(fund)

    def ols_report(data, dv, ivs, label):
        X = sm.add_constant(data[ivs])
        m = sm.OLS(data[dv], X).fit(cov_type="HC1")
        row = {"model": label, "dv": dv, "N": int(m.nobs), "R2": round(m.rsquared, 4)}
        for iv in ivs:
            row[f"{iv}_coef"] = round(m.params[iv], 4)
            row[f"{iv}_t"] = round(m.tvalues[iv], 2)
        return row, m

    ivs = ["risk_asym", "lsv", "de", "log_aum", "log_fund_age"]
    r_alpha, _ = ols_report(fund, "alpha", ivs, "CS_alpha_with_aum")
    r_exc, _ = ols_report(fund, "excess_mean", ivs, "CS_excess_with_aum")
    results["cs_alpha"] = r_alpha
    results["cs_excess"] = r_exc

    # 截面【不含 avg_aum】版本（突破 200 基金上限，扩到全 L5 可用基金）
    fund2 = pd.DataFrame({
        "alpha": g["ff5_adj_return"].first(),
        "excess_mean": g["excess_return"].mean(),
        "risk_asym": g["risk_asym"].mean(),
        "lsv": g["lsv"].mean(),
        "de": g["de"].mean(),
        "log_fund_age": g["log_fund_age"].first(),
    }).dropna(subset=["alpha", "risk_asym", "lsv", "de", "log_fund_age"])
    diag["cross_section_N_no_aum"] = len(fund2)
    ivs2 = ["risk_asym", "lsv", "de", "log_fund_age"]
    r_alpha2, _ = ols_report(fund2, "alpha", ivs2, "CS_alpha_no_aum")
    r_exc2, _ = ols_report(fund2, "excess_mean", ivs2, "CS_excess_no_aum")
    results["cs_alpha_no_aum"] = r_alpha2
    results["cs_excess_no_aum"] = r_exc2

    # ---------- (B) 前向预测回归（面板层, 含年份FE + 控制, 基金聚类）----------
    # 手稿：未来4季度 excess_return 均值 / 未来1季度 excess_return。
    # 重构：对每只基金，未来1季度 = quarter_return.shift(-1)；未来4季度 = 后4季 excess_return 均值。
    d = df.sort_values(["fund_code", "year", "quarter"]).copy()
    d["fut1q"] = d.groupby("fund_code")["excess_return"].shift(-1)
    d["fut4q"] = d.groupby("fund_code")["excess_return"].shift(-1).rolling(4).mean().reset_index(level=0, drop=True)
    # rolling 跨基金需分组；改用 groupby apply
    def roll4(s):
        return s.shift(-1).rolling(4).mean()
    d["fut4q"] = d.groupby("fund_code")["excess_return"].transform(roll4)

    fe = d.dropna(subset=["risk_asym", "lsv", "de", "log_aum", "log_fund_age"])
    # 年份固定效应
    fe = fe.copy()
    fe["year_c"] = fe["year"].astype(int)

    def ols_cluster(data, dv, ivs, label):
        # 修复：前向 DV(fut4q/fut1q) 在每基金末 3-4 季为 NaN（shift+rolling），
        # 若不剔除会使 OLS 的 y 含 NaN → 系数/R2 全为 NaN。故按 [dv]+ivs 联合 dropna。
        sub = data[[dv] + ivs + ["fund_code"]].dropna()
        X = sm.add_constant(sub[ivs])
        m = sm.OLS(sub[dv], X).fit(cov_type="cluster", cov_kwds={"groups": sub["fund_code"]})
        row = {"model": label, "dv": dv, "N": int(m.nobs), "R2": round(m.rsquared, 4)}
        for iv in ivs:
            row[f"{iv}_coef"] = round(m.params[iv], 4)
            row[f"{iv}_t"] = round(m.tvalues[iv], 2)
        return row

    ivs_f = ["risk_asym", "lsv", "de", "log_aum", "log_fund_age", "year_c"]
    r_f4 = ols_cluster(fe, "fut4q", ivs_f, "FWD_4Q_with_aum")
    r_f1 = ols_cluster(fe, "fut1q", ivs_f, "FWD_1Q_with_aum")
    results["fwd_4q"] = r_f4
    results["fwd_1q"] = r_f1

    # 前向【不含 avg_aum】版本
    fe2 = d.dropna(subset=["risk_asym", "lsv", "de", "log_fund_age"])
    fe2 = fe2.copy()
    fe2["year_c"] = fe2["year"].astype(int)
    ivs_f2 = ["risk_asym", "lsv", "de", "log_fund_age", "year_c"]
    r_f4b = ols_cluster(fe2, "fut4q", ivs_f2, "FWD_4Q_no_aum")
    r_f1b = ols_cluster(fe2, "fut1q", ivs_f2, "FWD_1Q_no_aum")
    results["fwd_4q_no_aum"] = r_f4b
    results["fwd_1q_no_aum"] = r_f1b
    diag["fwd_N_no_aum"] = int(r_f4b["N"])

    # ---------- 输出 ----------
    res_df = pd.DataFrame([results["cs_alpha"], results["cs_excess"],
                           results["cs_alpha_no_aum"], results["cs_excess_no_aum"],
                           results["fwd_4q"], results["fwd_1q"],
                           results["fwd_4q_no_aum"], results["fwd_1q_no_aum"]])
    res_df.to_csv("指标计算流水线/output/LSV回归重算结果.csv", index=False)
    diag_df = pd.DataFrame(list(diag.items()), columns=["metric", "value"])
    diag_df.to_csv("指标计算流水线/output/LSV回归重算_诊断.csv", index=False)

    # 打印
    pd.set_option("display.width", 200)
    print("==== 诊断（覆盖率 / 样本量）====")
    print(diag_df.to_string(index=False))
    print("\n==== 回归重算结果（修正后非负 LSV）====")
    print(res_df.to_string(index=False))
    print("\n--- 截面 alpha 回归 LSV/RA/DE 系数 ---")
    print(f"  RA  : {r_alpha['risk_asym_coef']:+.4f} (t={r_alpha['risk_asym_t']:+.2f})")
    print(f"  LSV : {r_alpha['lsv_coef']:+.4f} (t={r_alpha['lsv_t']:+.2f})")
    print(f"  DE  : {r_alpha['de_coef']:+.4f} (t={r_alpha['de_t']:+.2f})")
    print("--- 前向 1Q / 4Q LSV 系数 ---")
    print(f"  FWD4Q LSV (w/aum) : {r_f4['lsv_coef']:+.4f} (t={r_f4['lsv_t']:+.2f})  N={r_f4['N']}")
    print(f"  FWD1Q LSV (w/aum) : {r_f1['lsv_coef']:+.4f} (t={r_f1['lsv_t']:+.2f})  N={r_f1['N']}")
    print(f"  FWD4Q LSV (no aum): {r_f4b['lsv_coef']:+.4f} (t={r_f4b['lsv_t']:+.2f})  N={r_f4b['N']}")
    print(f"  FWD1Q LSV (no aum): {r_f1b['lsv_coef']:+.4f} (t={r_f1b['lsv_t']:+.2f})  N={r_f1b['N']}")
    print("\n--- 截面 LSV 系数 (with vs without avg_aum) ---")
    print(f"  CS_alpha LSV (w/aum) : {r_alpha['lsv_coef']:+.4f} (t={r_alpha['lsv_t']:+.2f})  N={r_alpha['N']}")
    print(f"  CS_alpha LSV (no aum): {r_alpha2['lsv_coef']:+.4f} (t={r_alpha2['lsv_t']:+.2f})  N={r_alpha2['N']}")

if __name__ == "__main__":
    main()
