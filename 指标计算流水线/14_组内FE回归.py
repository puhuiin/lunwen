# -*- coding: utf-8 -*-
"""14_组内FE回归.py —— R6 组内固定效应（within-fund fixed effects）回归。

目的
----
横截面基准（R1 / 13_分层回归）把每只基金压成「基金层均值」后做 OLS，会丢失基金
内部的时序变化，且无法控制基金层面不随时间变化的异质性（风格、成立背景、经理身份
固定效应）。R6 改用**面板（基金×季度）**口径，对每只基金做组内去均值（within
transformation），使每只基金成为自己的对照：

    y_{it} − ȳ_i = Σ_k β_k (x_{kit} − x̄_{ki}) + Σ_t γ_t (1{i∈year t}) + ε_{it}

→ 估计的是「同一只基金，行为/风险构念相对自身均值的偏离，能否预测其业绩相对自身
  均值的偏离」。这天然控制了所有 time-invariant 的基金/经理特征（含 L1 个人信息：
  性别/学历/CFA/school 被基金 FE 吸收，不再单独估计，仅作控制）。

因变量 DV 的关键约束：必须是**基金内随时变**的业绩指标。
  - ff5_adj_return 在面板中是「基金层整体 FF5 alpha」，组内标准差≈0（362 只基金
    内 361 只组内 std=0），若用作 DV 会被组内去均值完全抹除 → 系数塌缩为 0（已验证）。
  - 故 R6 采用 **quarter_return（季度原始收益）** 为主 DV，excess_return（季度超额）
    为备选，二者均 400 只基金 100% 组内变异。
标准误：基金层面聚类（cov_type="cluster", groups=fund_code），在组内去均值后估计，
等价于双向 FE 的聚类稳健推断。
样本：覆盖上限由 IV 缺失决定；de 仅半年报(46.3%)、TO 仅双边子集(18%)，故分三档设定。

输出：output/组内FE回归结果.csv（长表：spec/DV/N/var/coef/t/sig）
"""
import os
import numpy as np
import pandas as pd
import statsmodels.api as sm

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "output")
os.makedirs(OUT, exist_ok=True)
PANEL = os.path.join(OUT, "主分析面板_重建.csv")


def demean(df, cols, by):
    g = df.groupby(by)
    return df[cols] - g[cols].transform("mean")


def fe_report(df, dv, ivs, label, by="fund_code"):
    need = [dv] + ivs + [by, "year"]
    sub = df[[c for c in need if c in df.columns]].dropna(subset=[dv] + ivs).copy()
    if len(sub) < len(ivs) * 20:
        return []
    sub = sub.reset_index(drop=True)
    # 年份哑变量随 sub 携带 fund_code，一并组内去均值 → 双向 FE
    yr = pd.get_dummies(sub["year"], prefix="yr", drop_first=True).astype(float)
    sub = pd.concat([sub, yr], axis=1)
    yr_cols = list(yr.columns)
    all_x = ivs + yr_cols
    Xdm = demean(sub, all_x, by)
    ydm = demean(sub, [dv], by)[dv].values
    X = Xdm[all_x].values
    res = sm.OLS(ydm, X).fit(cov_type="cluster", cov_kwds={"groups": sub[by].values})
    rows = []
    for j, v in enumerate(ivs):
        t = float(res.tvalues[j]); b = float(res.params[j])
        rows.append({"spec": label, "DV": dv, "N": int(len(sub)),
                     "var": v, "coef": round(b, 5), "t": round(t, 3),
                     "sig": "***" if abs(t) > 2.58 else ("**" if abs(t) > 1.96 else "")})
    return rows


def main():
    df = pd.read_csv(PANEL, dtype={"fund_code": str})
    df["year"] = df["year"].astype(int)
    # 广泛可得的时序变构念（de/TO 覆盖率低，单独设档）。注意：L1 个人信息（性别/
    # 学历/CFA/school）为 time-invariant，被基金 FE 吸收，不进入 ivs。
    core = ["mgr_total_tenure_v2", "AS_improved", "ICI", "industry_hhi",
            "SDI", "ARG", "RG", "return_volatility", "risk_asym", "lsv",
            "pgr", "plr"]
    results = []
    results += fe_report(df, "quarter_return", core, "R6-core(不含de/TO)")
    results += fe_report(df, "excess_return", core, "R6-core(不含de/TO)-excess")

    add_de = core + ["de"]
    results += fe_report(df, "quarter_return", add_de, "R6+de")

    add_to = core + ["TO_two_sided"]
    results += fe_report(df, "quarter_return", add_to, "R6+TO")

    res = pd.DataFrame([r for r in results if r])
    res.to_csv(os.path.join(OUT, "组内FE回归结果.csv"), index=False, encoding="utf-8-sig")

    for spec in ["R6-core(不含de/TO)", "R6+de", "R6+TO"]:
        sub = res[res.spec == spec]
        if sub.empty:
            print(f"\n[{spec}] 无结果"); continue
        dv = sub.DV.iloc[0]; N = int(sub.N.iloc[0])
        print(f"\n[{spec}]  DV={dv}  N={N}")
        for _, row in sub.iterrows():
            print(f"   {row['var']:18s} β={row['coef']:+.5f}  t={row['t']:+.2f} {row['sig']}")
    print("\n已写出: output/组内FE回归结果.csv")


if __name__ == "__main__":
    main()
