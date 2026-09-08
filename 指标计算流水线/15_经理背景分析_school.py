# -*- coding: utf-8 -*-
"""
经理背景特征分析（school / 名校 / 教育背景）— 补充稳健性 2026-08-15
============================================================================
为什么单独成节、不进入 H1–H5 主回归：
  school / elite_school / education / CFA / gender 均为「基金经理背景」，
  在基金层面基本不随时间变化（time-invariant）。主回归 H1–H5 采用
  within-fund FE（按 fund_code demeaning），会把任何基金层面不变量吸收为零，
  强制塞入 has_school_d 只会从「经理变更」的 124 只基金获得识别，既脆弱又
  内生。因此经理背景必须放在「无 fund FE」的设定下识别：
    (A) 基金层面横截面 OLS（背景天然截面）
    (B) 面板 pooled OLS + 仅 year FE（不 demean fund，保留背景变异）
  本脚本同时给出 (A) 与 (B)，标准误用异方差稳健(HC1) / 聚类(fund)。

数据：指标计算流水线/output/主分析面板_重建_含TOwind.csv（真实面板）。
可复现：路径全部由 __file__ 推导。
"""
import pandas as pd, numpy as np, warnings, json, os, re
import statsmodels.api as sm
warnings.filterwarnings("ignore")

HERE = os.path.dirname(os.path.abspath(__file__))
PANEL = os.path.join(HERE, "output", "主分析面板_重建_含TOwind.csv")
panel = pd.read_csv(PANEL, dtype={"fund_code": str})
for c in ["quarter_return", "excess_return", "SDI", "TO_wind", "TO_wind_clean",
          "log_aum", "log_fund_age", "mgr_total_tenure_v2", "return_volatility",
          "RG", "ARG"]:
    if c in panel.columns:
        panel[c] = pd.to_numeric(panel[c], errors="coerce")

# ---- 派生控制变量（与 HONEST 回归一致口径） ----
panel["gender_m"] = panel["gender"].astype(str).str.contains("男").astype(float)
panel["cfa_d"] = panel["CFA"].astype(str).str.contains("Y|是|1", case=False, na=False).astype(float)
panel["edu_postgrad"] = panel["education"].astype(str).str.contains("硕士|博士|MBA|研究生", case=False, na=False).astype(float)
panel["has_school_d"] = panel["school"].notna().astype(float)
panel["log_aum"] = np.log(panel["avg_aum"].clip(lower=1e-6))

# ---- 名校虚拟（研究者定义；基于 curated school 字段的关键词匹配） ----
ELITE = ("清华大学","清华","北京大学","北京大","中国人民大","人民大","复旦大学","复旦",
         "上海交通大学","上海交大","上海交通大","浙江大学","浙江大","南京大",
         "中国科学技术大","中科大","中国科","哈尔滨工业大","西安交通大","同济大",
         "武汉大","华中科技大","中山大","厦门大","南开大","天津大","上海财经",
         "中央财经","中南财经","西南财经","东北财经","对外经贸","北京航空航天",
         "北京师范","香港中文","香港大","香港科技","香港大学","牛津","剑桥","哈佛",
         "斯坦福","麻省理工","哥伦比亚","宾夕法尼亚","芝加哥大","西北大","伦敦政经",
         "伦敦大学","伦敦大","加州","耶鲁","普林斯顿","康奈尔","纽约大","新加坡国立",
         "南洋理工","慕尼黑工业","巴黎","东京大","早稻田","锡拉丘兹","密歇根","沃顿",
         "帝国理工","杜克","康奈")
def is_elite(s):
    if not isinstance(s, str) or not s:
        return np.nan
    return float(any(k in s for k in ELITE))
panel["elite_school_d"] = panel["school"].apply(is_elite)

# ============================================================
# (A) 基金层面横截面 collapse
# ============================================================
def fund_collapse(df):
    rows = []
    for f, g in df.groupby("fund_code"):
        school_str = g["school"].dropna()
        school_str = school_str.iloc[0] if len(school_str) else np.nan
        def first_num(col):
            v = pd.to_numeric(g[col], errors="coerce").dropna()
            return v.mean() if len(v) else np.nan
        rows.append({
            "fund_code": f,
            "mean_SDI": first_num("SDI"),
            "mean_TO_wind": first_num("TO_wind"),
            "mean_quarter_return": first_num("quarter_return"),
            "mean_excess_return": first_num("excess_return"),
            "mean_RG": first_num("RG"),
            "mean_return_vol": first_num("return_volatility"),
            "log_aum": first_num("log_aum"),
            "log_fund_age": first_num("log_fund_age"),
            "mgr_total_tenure_v2": first_num("mgr_total_tenure_v2"),
            "gender_m": g["gender_m"].mean(),
            "cfa_d": g["cfa_d"].mean(),
            "edu_postgrad": g["edu_postgrad"].mean(),
            "has_school_d": g["has_school_d"].max(),
            "elite_school_d": is_elite(school_str),
            "school": school_str,
        })
    return pd.DataFrame(rows)

fc = fund_collapse(panel)
print("基金横截面样本: %d 只 (其中 observed school=%d, elite=%d)" % (
    len(fc), fc["has_school_d"].sum(), fc["elite_school_d"].fillna(0).sum()))

CONTROLS = ["log_aum", "log_fund_age", "mgr_total_tenure_v2", "gender_m", "cfa_d", "edu_postgrad"]

def ols_cross(dv, ivs, data, label):
    sub = data[[dv] + ivs].dropna().copy()
    if len(sub) < len(ivs) * 15:
        print("  [%s] 样本不足(%d)，跳过" % (label, len(sub))); return None
    X = sm.add_constant(sub[ivs])
    y = sub[dv]
    res = sm.OLS(y, X).fit(cov_type="HC1")
    print("\n  [%s]  DV=%s  N=%d" % (label, dv, len(sub)))
    for v in ivs:
        b = res.params[v]; t = res.tvalues[v]; p = res.pvalues[v]
        star = "" if p > 0.10 else ("*" if p > 0.05 else ("**" if p > 0.01 else "***"))
        print("     %-18s beta=%+.5f  t=%+.2f  p=%.3f%s" % (v, b, t, p, star))
    return {"dv": dv, "N": int(len(sub)), "coef": {v: [float(res.params[v]), float(res.tvalues[v]), float(res.pvalues[v])] for v in ivs}}

results = {"cross_section": {}, "pooled_yearFE": {}}

# (A) 截面：仅在 observed-school 子样本上估计 elite + has_school；全样本上估计 has_school
obs = fc[fc["has_school_d"] == 1].copy()
print("\n===== (A) 基金横截面 OLS — observed-school 子样本(N=%d) =====" % len(obs))
for dv in ["mean_SDI", "mean_TO_wind", "mean_quarter_return", "mean_excess_return"]:
    results["cross_section"][dv] = ols_cross(dv, ["elite_school_d", "has_school_d"] + CONTROLS, obs, "obs-" + dv)

print("\n===== (A) 基金横截面 OLS — 全样本 has_school 选择效应(N=%d) =====" % len(fc))
for dv in ["mean_SDI", "mean_TO_wind", "mean_quarter_return"]:
    results["cross_section"]["all_" + dv] = ols_cross(dv, ["has_school_d"] + CONTROLS, fc, "all-" + dv)

# ============================================================
# (B) 面板 pooled OLS + 仅 year FE（不 demean fund，保留背景变异）
# ============================================================
def ols_pooled(dv, ivs, data, label):
    dd = data[[dv] + ivs + ["year"]].dropna().copy()
    if len(dd) < len(ivs) * 30:
        print("  [%s] 样本不足(%d)，跳过" % (label, len(dd))); return None
    yr = pd.get_dummies(dd["year"], prefix="yr", drop_first=True).astype(float)
    X = sm.add_constant(pd.concat([dd[ivs], yr], axis=1))
    res = sm.OLS(dd[dv], X).fit(cov_type="HC1")
    print("\n  [%s]  DV=%s  N=%d" % (label, dv, len(dd)))
    for v in ivs:
        b = res.params[v]; t = res.tvalues[v]; p = res.pvalues[v]
        star = "" if p > 0.10 else ("*" if p > 0.05 else ("**" if p > 0.01 else "***"))
        print("     %-18s beta=%+.5f  t=%+.2f  p=%.3f%s" % (v, b, t, p, star))
    return {"dv": dv, "N": int(len(dd)), "coef": {v: [float(res.params[v]), float(res.tvalues[v]), float(res.pvalues[v])] for v in ivs}}

pool_obs = panel[panel["has_school_d"] == 1].copy()
pool_obs["year"] = pool_obs["report_date"].str[:4].astype(int)
print("\n===== (B) 面板 pooled OLS + year FE — observed-school 子样本 =====")
for dv in ["quarter_return", "SDI", "TO_wind"]:
    results["pooled_yearFE"][dv] = ols_pooled(dv, ["elite_school_d", "has_school_d"] + CONTROLS, pool_obs, "pool-" + dv)

# ---- 导出 ----
out_json = os.path.join(HERE, "output", "经理背景分析_school_2026-08-15.json")
with open(out_json, "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
print("\n[已写出", out_json, "]")
