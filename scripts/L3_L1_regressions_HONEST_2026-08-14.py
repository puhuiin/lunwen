# -*- coding: utf-8 -*-
"""
L3 (交易执行层) 与 L1 (背景特征层) 诚实回归 — 集成 Wind 换手率版 2026-08-15
============================================================================
可复现性：本脚本路径全部由 __file__ 推导，可从任意目录运行：
    python L3_L1_regressions_HONEST_2026-08-14.py

数据来源：指标计算流水线/output/主分析面板_重建_含TOwind.csv
  （由 run_all.py 完整流水线产出：00-06 合并 -> 07b 并入 Wind 双边换手率）。
  面板含 SDI(真算)、TO_wind(86%覆盖)、TO_two_sided(18%,稳健性对照)、
  全部 L1 控制变量。方法学：双向 demeaning(fund+year)+双向聚类SE(fund×year, CGM2011)。
"""
import pandas as pd, numpy as np, warnings, json, os
from scipy import stats as _tstats
warnings.filterwarnings("ignore")

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PANEL = os.path.join(HERE, "指标计算流水线", "output", "主分析面板_重建_含TOwind.csv")
panel = pd.read_csv(PANEL, dtype={"fund_code": str})
panel["report_date"] = panel["report_date"].astype(str)
panel["year"] = panel["report_date"].str[:4].astype(int)
print("面板:", PANEL)
print("  行数=%d  基金数=%d  含 TO_wind=%.1f%%" % (
    len(panel), panel["fund_code"].nunique(), panel["TO_wind"].notna().mean() * 100))


def wins(s, lo=0.01, hi=0.99):
    s = s.astype(float)
    a, b = s.quantile(lo), s.quantile(hi)
    return s.clip(a, b)


for c in ["quarter_return", "excess_return", "SDI", "TO_wind", "TO_wind_clean",
          "TO_two_sided", "OCI_two_sided",
          "log_aum", "log_fund_age", "mgr_total_tenure_v2", "return_volatility", "RG", "ARG"]:
    if c in panel.columns:
        panel[c] = wins(panel[c])

panel["log_aum"] = np.log(panel["avg_aum"].clip(lower=1e-6))
panel["gender_m"] = panel["gender"].astype(str).str.contains("男").astype(float)
panel["cfa_d"] = panel["CFA"].astype(str).str.contains("Y|是|1", case=False, na=False).astype(float)
panel["edu_postgrad"] = panel["education"].astype(str).str.contains("硕士|博士|MBA|研究生", case=False, na=False).astype(float)

CONTROLS = ["log_aum", "log_fund_age", "mgr_total_tenure_v2", "gender_m", "cfa_d", "edu_postgrad"]


# ============================================================
# 双向聚类稳健标准误（Cameron–Gelbach–Miller 2011, fund × year）
#   采用 within(基金) demeaning 后再做双向聚类：
#   V_twoway = V_fund + V_year − V_(fund∩year)
#   与「在原始 FE 模型上做 fund×year 双向聚类」等价（demeaning 是线性变换，
#   不改变聚类稳健方差估计）。v3 主口径：双向聚类(基金×年) SDI t=+2.46（基金聚类对照 t=+12.4），
#   已用 _verify_two_way_cluster.py 与 linearmodels 交叉验证；早期"t 由 12.39→12.68"压力测试为误算，废弃。
# ============================================================
def _meat(groups, X, resid):
    """Σ_g (Σ_{i∈g} X_i·e_i)(Σ_{i∈g} X_i·e_i)'。"""
    k = X.shape[1]
    meat = np.zeros((k, k))
    for g in np.unique(groups):
        m = groups == g
        s = X[m].T @ resid[m]            # (k,)
        meat += np.outer(s, s)
    return meat


def _oneway_V(X, resid, groups):
    meat = _meat(groups, X, resid)
    XtX_inv = np.linalg.inv(X.T @ X)
    return XtX_inv @ meat @ XtX_inv


def two_way_V(X, resid, g1, g2):
    V1 = _oneway_V(X, resid, g1)
    V2 = _oneway_V(X, resid, g2)
    g12 = np.array([f"{a}|{b}" for a, b in zip(g1, g2)])   # 交互簇
    V12 = _oneway_V(X, resid, g12)
    return V1 + V2 - V12


def fe_report(df, dv, ivs, label, by="fund_code"):
    need = [dv] + ivs + [by, "year"]
    sub = df[[c for c in need if c in df.columns]].dropna(subset=[dv] + ivs).copy().reset_index(drop=True)
    if len(sub) < len(ivs) * 20:
        return None
    yr = pd.get_dummies(sub["year"], prefix="yr", drop_first=True).astype(float)
    sub = pd.concat([sub, yr], axis=1)
    all_x = ivs + list(yr.columns)
    g = sub.groupby(by)
    Xdm = sub[all_x] - g[all_x].transform("mean")
    ydm = (sub[dv] - g[dv].transform("mean")).values
    X = Xdm[all_x].values.astype(float)
    y = ydm.astype(float)
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ beta
    V = two_way_V(X, resid, sub[by].values.astype(str), sub["year"].values.astype(str))
    se = np.sqrt(np.maximum(np.diag(V), 0))
    tvals = beta / se
    pvals = 2.0 * _tstats.t.sf(np.abs(tvals), df=len(y) - X.shape[1])
    # 对照：单维基金聚类 SE（CGM one-way，与早期 statsmodels 单维口径一致）
    V1 = _oneway_V(X, resid, sub[by].values.astype(str))
    se1 = np.sqrt(np.maximum(np.diag(V1), 0))
    tvals1 = beta / se1
    out = {"spec": label, "DV": dv, "N": int(len(sub)), "funds": int(sub[by].nunique()), "rows": []}
    for j, v in enumerate(ivs):
        t = float(tvals[j]); b = float(beta[j]); p = float(pvals[j])
        t1 = float(tvals1[j])
        star = "" if p > 0.10 else ("*" if p > 0.05 else ("**" if p > 0.01 else "***"))
        out["rows"].append((v, b, t, p, star, t1))
    return out


def run_and_print(specs, dv="quarter_return", tag="", df=None):
    if df is None:
        df = panel
    print("\n" + "=" * 72)
    print("%s  DV=%s  双向 FE(fund+year)+双向聚类SE(fund×year)" % (tag, dv))
    print("=" * 72)
    out = {}
    for name, ivs in specs.items():
        r = fe_report(df, dv, ivs, name)
        out[name] = r
        if r is None:
            print("  [%s] 样本不足，跳过" % name)
            continue
        print("  [%s] N=%d 基金=%d" % (name, r["N"], r["funds"]))
        for v, b, t, p, s, t1 in r["rows"]:
            if v in ["SDI", "TO_wind", "TO_wind_clean", "TO_two_sided", "OCI_two_sided", "log_aum", "log_fund_age"]:
                src = "【真算/集成】" if v in ("SDI", "TO_wind", "TO_wind_clean") else ""
                print("     %-16s beta=%+.5f  t2w=%+.2f  t1w=%+.2f  p=%.3f%s  %s"
                      % (v, b, t, t1, p, s, src))
    return out


# ============ 集成 Wind 换手率版：主换手率 = TO_wind（86% 覆盖） ============
HONEST = {
    "H1 SDI(真算风格漂移)":           ["SDI"] + CONTROLS,
    "H2 TO_wind(Wind集成换手率)":     ["TO_wind"] + CONTROLS,
    "H2b TO_two_sided(旧双边,稳健性)": ["TO_two_sided"] + CONTROLS,
    "H3 OCI_two_sided(真算)":         ["OCI_two_sided"] + CONTROLS,
    "H4 SDI+TO_wind+OCI(联合)":       ["SDI", "TO_wind", "OCI_two_sided"] + CONTROLS,
    "H5 SDI+控制(不含TO,大样本)":     ["SDI"] + CONTROLS,
}
honest_res = run_and_print(HONEST, tag="【诚实版 L3/L1 集成 Wind 换手率】")


# ============ 导出 JSON 供报告使用 ============
def to_serial(d):
    return {k: (None if v is None else {
        "spec": v["spec"], "DV": v["DV"], "N": v["N"], "funds": v["funds"],
        "rows": [{"v": a, "b": b, "t": t, "p": p, "s": s, "t1": t1}
                 for a, b, t, p, s, t1 in v["rows"]]})
        for k, v in d.items()}


blob = {"honest": to_serial(honest_res)}
out_json = os.path.join(HERE, "L3_L1_regression_HONEST_TOWind_2026-08-15.json")
with open(out_json, "w", encoding="utf-8") as f:
    json.dump(blob, f, ensure_ascii=False, indent=2)
print("\n[已写出", out_json, "]（集成 Wind 换手率版诚实回归结果）")
