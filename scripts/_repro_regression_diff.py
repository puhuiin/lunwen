# -*- coding: utf-8 -*-
"""
回归差异分解与归因（不改动流水线文件）
- 复制 L3_L1_regressions_HONEST_2026-08-14.py 的 fe_report 逻辑（双向 demean + 基金聚类SE）
- 计算 R_new（新面板，直接读 output/主分析面板_重建_含TOwind.csv）
- 计算 R_old（旧面板：备份 base + 并入未变的 EDE TO_wind 长表）
- 载入 R_aug14（旧面板 + 旧脚本，L3_L1_regression_HONEST_results_2026-08-14.json）
- 先用 R_new 校验本脚本复刻是否与真实 JSON 逐字节一致；一致则 R_old 可信
- 输出三向对比 + 面板变量变动来源归因
"""
import pandas as pd, numpy as np, statsmodels.api as sm, warnings, json, os
warnings.filterwarnings("ignore")

ROOT = r'D:/Desktop/基金经理行为分析研究'
OUT = os.path.join(ROOT, '指标计算流水线', 'output')
LONG_TO = os.path.join(ROOT, '指标计算流水线', 'data', 'L3_交易行为层', '基金换手率_Wind_EDE20260815.csv')
OLD_BASE = r'D:/Desktop/基金经理行为分析研究/._repro_backup/20260815_133543/主分析面板_重建.csv'
REAL_JSON = os.path.join(ROOT, 'L3_L1_regression_HONEST_TOWind_2026-08-15.json')
AUG14_JSON = os.path.join(ROOT, 'L3_L1_regression_HONEST_results_2026-08-14.json')


def wins(s, lo=0.01, hi=0.99):
    s = s.astype(float)
    a, b = s.quantile(lo), s.quantile(hi)
    return s.clip(a, b)


def build(panel):
    panel = panel.copy()
    panel["report_date"] = panel["report_date"].astype(str)
    panel["year"] = panel["report_date"].str[:4].astype(int)
    for c in ["quarter_return", "excess_return", "SDI", "TO_wind", "TO_wind_clean",
              "TO_two_sided", "OCI_two_sided",
              "log_aum", "log_fund_age", "mgr_total_tenure_v2", "return_volatility", "RG", "ARG"]:
        if c in panel.columns:
            panel[c] = wins(panel[c])
    panel["log_aum"] = np.log(panel["avg_aum"].clip(lower=1e-6))
    panel["gender_m"] = panel["gender"].astype(str).str.contains("男").astype(float)
    panel["cfa_d"] = panel["CFA"].astype(str).str.contains("Y|是|1", case=False, na=False).astype(float)
    panel["edu_postgrad"] = panel["education"].astype(str).str.contains("硕士|博士|MBA|研究生", case=False, na=False).astype(float)
    return panel


def fe_report(df, dv, ivs, by="fund_code"):
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
    X = Xdm[all_x].values
    res = sm.OLS(ydm, X).fit(cov_type="cluster", cov_kwds={"groups": sub[by].values})
    out = {"DV": dv, "N": int(len(sub)), "funds": int(sub[by].nunique()), "rows": []}
    for j, v in enumerate(ivs):
        out["rows"].append((v, float(res.params[j]), float(res.tvalues[j]), float(res.pvalues[j])))
    return out


CONTROLS = ["log_aum", "log_fund_age", "mgr_total_tenure_v2", "gender_m", "cfa_d", "edu_postgrad"]
HONEST = {
    "H1 SDI(真算风格漂移)": ["SDI"] + CONTROLS,
    "H2 TO_wind(Wind集成换手率)": ["TO_wind"] + CONTROLS,
    "H2b TO_two_sided(旧双边,稳健性)": ["TO_two_sided"] + CONTROLS,
    "H3 OCI_two_sided(真算)": ["OCI_two_sided"] + CONTROLS,
    "H4 SDI+TO_wind+OCI(联合)": ["SDI", "TO_wind", "OCI_two_sided"] + CONTROLS,
    "H5 SDI+控制(不含TO,大样本)": ["SDI"] + CONTROLS,
}


def run_panel(panel):
    panel = build(panel)
    res = {}
    for name, ivs in HONEST.items():
        res[name] = fe_report(panel, "quarter_return", ivs)
    return res


def serial(r):
    return {k: None if v is None else {kk: v[kk] for kk in ("DV", "N", "funds")} | {
        "rows": [(a, round(b, 12), round(t, 6), round(p, 6)) for a, b, t, p in v["rows"]]}
        for k, v in r.items()}


# ---- R_new: 直接读当前含TOwind面板 ----
new_panel = pd.read_csv(os.path.join(OUT, "主分析面板_重建_含TOwind.csv"), dtype={"fund_code": str})
R_new = run_panel(new_panel)

# ---- 校验复刻是否逐字节一致于真实JSON ----
real = json.load(open(REAL_JSON, encoding="utf-8"))["honest"]
mismatch = []
for k in HONEST:
    rr = R_new[k]
    if rr is None:
        mismatch.append((k, "R_new None"))
        continue
    rreal = real.get(k)
    if rreal is None:
        continue
    for (va, ba, ta, pa), row in zip(rr["rows"], rreal["rows"]):
        if abs(ba - row["b"]) > 1e-9 or abs(ta - row["t"]) > 1e-6 or rr["N"] != rreal["N"]:
            mismatch.append((k, va, ba, row["b"]))
print("=== 复刻校验（R_new vs 真实JSON）===")
print("  不匹配项:", mismatch if mismatch else "0 项 — 复刻逐字节一致，R_old 可信")

# ---- R_old: 旧base面板 + 并入未变的 EDE TO_wind 长表 ----
old_base = pd.read_csv(OLD_BASE, dtype={"fund_code": str})
long_to = pd.read_csv(LONG_TO, dtype={"fund_code": str})
long_to["report_date"] = long_to["report_date"].astype(str)
old_merge = old_base.merge(long_to[["fund_code", "report_date", "TO_wind", "TO_wind_clean"]],
                           on=["fund_code", "report_date"], how="left")
R_old = run_panel(old_merge)

# ---- R_aug14: 旧面板 + 旧脚本（直接读JSON）----
aug14 = json.load(open(AUG14_JSON, encoding="utf-8"))["honest"]


def round_json(d):
    return {k: None if v is None else {kk: v[kk] for kk in ("DV", "N", "funds")} | {
        "rows": [(row["v"], round(row["b"], 12), round(row["t"], 6), round(row["p"], 6)) for row in v["rows"]]}
        for k, v in d.items()}


R_aug14 = round_json(aug14)


# ---- 面板变量变动归因：旧 vs 新 base 面板（含TOwind前）----
def panel_diff_cols(old, new):
    cols = [c for c in new.columns if c in old.columns and old[c].dtype != object or (c in old.columns)]
    out = {}
    common = [c for c in new.columns if c in old.columns]
    o = old[common].copy(); n = new[common].copy()
    # 对齐 index 无意义，用 (fund_code,report_date) 键
    key = ["fund_code", "report_date"]
    oi = o.drop_duplicates(key).set_index(key)
    ni = n.drop_duplicates(key).set_index(key)
    idx = oi.index.intersection(ni.index)
    for c in common:
        if c in key:
            continue
        try:
            a = oi.loc[idx, c]; b = ni.loc[idx, c]
            diff = (~(a.fillna(-999999).astype(str) == b.fillna(-999999).astype(str))).sum()
            if diff > 0:
                out[c] = int(diff)
        except Exception:
            pass
    return out


# 用新base面板（output/主分析面板_重建.csv）与旧base对比
new_base = pd.read_csv(os.path.join(OUT, "主分析面板_重建.csv"), dtype={"fund_code": str})
diffs = panel_diff_cols(old_base, new_base)
reg_vars = set()
for ivs in HONEST.values():
    reg_vars.update(ivs)
# 衍生变量来源
derived = {"gender_m": "gender", "cfa_d": "CFA", "edu_postgrad": "education", "log_aum": "avg_aum",
           "log_fund_age": "fund_age"}
print("\n=== 面板变量变动（旧base vs 新base，按 (fund_code,report_date) 对齐）===")
print("  变动列及变动单元数:")
for c, n in sorted(diffs.items(), key=lambda x: -x[1]):
    enters = "进入HONEST? " + ("是(衍生:%s)" % derived.get(c, c) if c in reg_vars or c in derived.values() else "否")
    print("    %-22s %8d  %s" % (c, n, enters))

print("\n=== 三向回归对比（beta / t / N,funds）===")
def fmt(r):
    if r is None:
        return "None"
    return "N=%d,f=%d" % (r["N"], r["funds"])

# 对齐映射：aug14 的 H2(TO_two_sided) <-> H2b；aug14 的 H4(TO_two_sided) <-> H4(TO_wind) 仅SDI/OCI可比
compare_map = [
    ("H1 SDI(真算风格漂移)", "H1 SDI(真算风格漂移)"),
    ("H2b TO_two_sided(旧双边,稳健性)", "H2 TO_two_sided(真算双边)"),
    ("H3 OCI_two_sided(真算)", "H3 OCI_two_sided(真算)"),
    ("H5 SDI+控制(不含TO,大样本)", "H5 SDI+控制(不含TO,大样本)"),
]
print("\n-- 完全相同口径（新=旧面板+新脚本 vs 旧面板+旧脚本）--")
for newk, oldk in compare_map:
    a = R_new[newk]; b = R_aug14.get(oldk)
    print("\n[%s]  R_new:%s  R_aug14:%s" % (newk, fmt(a), fmt(b)))
    if a is None or b is None:
        print("   跳过(样本不足)")
        continue
    ad = {r[0]: r for r in a["rows"]}; bd = {r[0]: r for r in b["rows"]}
    for v in ad:
        if v in bd:
            ba, ta = ad[v][1], ad[v][2]; bb, tb = bd[v][1], bd[v][2]
            d = abs(ba - bb)
            flag = "  <-- 差!" if d > 1e-9 else ""
            print("    %-16s new(b=%.6f t=%.2f)  aug14(b=%.6f t=%.2f)  Δb=%.2e%s" % (v, ba, ta, bb, tb, d, flag))

print("\n-- H4 联合（新脚本用TO_wind / 旧脚本用TO_two_sided，换手率口径不同）--")
a = R_new["H4 SDI+TO_wind+OCI(联合)"]; b = R_aug14.get("H4 SDI+TO+OCI(真算联合)")
print("  R_new(H4,TO_wind): %s" % fmt(a))
print("  R_aug14(H4,TO_two_sided): %s" % fmt(b))
if a and b:
    ad = {r[0]: r for r in a["rows"]}; bd = {r[0]: r for r in b["rows"]}
    for v in ["SDI", "OCI_two_sided"]:
        if v in ad and v in bd:
            ba, ta = ad[v][1], ad[v][2]; bb, tb = bd[v][1], bd[v][2]
            print("    %-16s new(b=%.6f t=%.2f)  aug14(b=%.6f t=%.2f)  Δb=%.2e" % (v, ba, ta, bb, tb, ba - bb))

print("\n-- 数据演进效应（新面板+新脚本 vs 旧面板+新脚本，同脚本隔离数据）--")
for k in HONEST:
    a = R_new[k]; b = R_old.get(k)
    if a is None or b is None:
        print("  [%s] 新:%s 旧:%s 跳过" % (k, fmt(a), fmt(b)))
        continue
    ad = {r[0]: r for r in a["rows"]}; bd = {r[0]: r for r in b["rows"]}
    maxd = 0.0
    for v in ad:
        if v in bd:
            maxd = max(maxd, abs(ad[v][1] - bd[v][1]))
    verdict = "一致(Δb<1e-9)" if maxd < 1e-9 else "有差异(Δb=%.2e)" % maxd
    print("  [%s] %s  数据演进效应: %s" % (k, verdict, verdict))

# 保存 R_old JSON 供记录
out_old = {"honest": serial(R_old)}
with open(os.path.join(ROOT, "L3_L1_regression_OLD_PANEL_2026-08-15.json"), "w", encoding="utf-8") as f:
    json.dump(out_old, f, ensure_ascii=False, indent=2)
print("\n[已写出 R_old -> L3_L1_regression_OLD_PANEL_2026-08-15.json]")
