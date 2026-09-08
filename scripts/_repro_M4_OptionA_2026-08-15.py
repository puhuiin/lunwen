# -*- coding: utf-8 -*-
"""
Option A 收口脚本 — 重建 M4 完整模型与描述性统计（真实可复现列）
=================================================================
目标：消除 merged_manuscript.html 中表4-2 / 表4-5 / 表4-6 对已删除
模拟列 TO_calc / OCI 的引用，改用真实可复现列：
  - TO_calc(87.5%覆盖) -> TO_wind(86.6%覆盖，H2 规范换手率，覆盖兼容)
  - OCI(87.5%覆盖, 占位) -> OCI_two_sided(18%覆盖，真实；因覆盖过低
    无法塞入头条 M4，改为从 M4 移除并在脚注指向 H3 独立结果)
所有数字均来自 主分析面板_重建_含TOwind.csv（run_full.py 产物），可复现。
"""
import pandas as pd, numpy as np, json, os, warnings
import statsmodels.api as sm
import statsmodels.formula.api as smf
warnings.filterwarnings("ignore")

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PANEL = os.path.join(HERE, "指标计算流水线", "output", "主分析面板_重建_含TOwind.csv")
panel = pd.read_csv(PANEL, dtype={"fund_code": str})
panel["report_date"] = panel["report_date"].astype(str)
panel["year"] = panel["report_date"].str[:4].astype(int)

# ---- 派生（与诚实回归脚本一致）----
panel["log_aum"] = np.log(panel["avg_aum"].clip(lower=1e-6))
panel["gender_m"] = panel["gender"].astype(str).str.contains("男").astype(float)
panel["cfa_d"] = panel["CFA"].astype(str).str.contains("Y|是|1", case=False, na=False).astype(float)
panel["edu_postgrad"] = panel["education"].astype(str).str.contains("硕士|博士|MBA|研究生", case=False, na=False).astype(float)

# ---- 1%/99% 缩尾（与稿件"所有连续变量均经过1%/99%缩尾处理"一致）----
def wins(s, lo=0.01, hi=0.99):
    s = s.astype(float); a, b = s.quantile(lo), s.quantile(hi); return s.clip(a, b)
for c in ["ff5_adj_return","SDI","TO_wind","TO_two_sided","OCI_two_sided",
          "AS_improved","ICI","industry_hhi","ARG","return_volatility",
          "de","lsv","risk_asym","log_aum","log_fund_age","mgr_total_tenure_v2"]:
    if c in panel.columns:
        panel[c] = wins(panel[c])

def desc(col):
    s = panel[col].dropna()
    return dict(mean=s.mean(), std=s.std(), mn=s.min(), med=s.median(),
                mx=s.max(), cov=s.notna().mean()*100 if False else len(s)/len(panel)*100,
                n=len(s))

print("="*72)
print("一、描述性统计（1%/99%缩尾，N=9,974）— 表4-2 替换行")
print("="*72)
for v in ["SDI","TO_wind","TO_two_sided","OCI_two_sided","AS_improved","ICI",
          "industry_hhi","ARG","return_volatility","de","lsv","risk_asym","log_aum"]:
    d = desc(v)
    print(f"  {v:16s} mean={d['mean']:.3f} sd={d['std']:.3f} min={d['mn']:.3f} "
          f"med={d['med']:.3f} max={d['mx']:.3f} cov={d['cov']:.1f}% n={d['n']}")

# ---- M4 完整模型：ff5_adj_return ~ 全 L1-L5 + 年份FE，基金聚类SE ----
RHS = ["SDI","TO_wind","AS_improved","ICI","industry_hhi","ARG","return_volatility",
       "de","lsv","risk_asym","log_aum","log_fund_age","mgr_total_tenure_v2",
       "gender_m","cfa_d","edu_postgrad"]
rhs_formula = " + ".join(RHS)
for tag, extra in [("A: TO_wind, 无OCI", ""), ("B: +OCI_two_sided", " + OCI_two_sided")]:
    form = f"ff5_adj_return ~ {rhs_formula}{extra} + C(year)"
    sub = panel.dropna(subset=["ff5_adj_return"]+RHS+([ "OCI_two_sided"] if "OCI" in extra else [])).copy()
    m = smf.ols(form, data=sub).fit(cov_type="cluster", cov_kwds={"groups": sub["fund_code"]})
    print("\n" + "="*72)
    print(f"M4 [{tag}]  N={int(m.nobs)}  基金={sub.fund_code.nunique()}  R2={m.rsquared:.4f}")
    print("="*72)
    for v in ["SDI","TO_wind","OCI_two_sided","AS_improved","ICI","industry_hhi",
              "ARG","return_volatility","de","lsv","risk_asym","log_aum","log_fund_age"]:
        if v in m.params:
            b=m.params[v]; t=m.tvalues[v]; p=m.pvalues[v]
            star="" if p>0.10 else ("*" if p>0.05 else ("**" if p>0.01 else "***"))
            print(f"   {v:16s} β={b:+.5f}  t={t:+.2f}  p={p:.3f}{star}")

# ---- VIF（M4 RHS，含 TO_wind 与 OCI_two_sided 对照）----
def vif_table(cols):
    d = panel.dropna(subset=cols).copy()
    X = sm.add_constant(d[cols])
    out={}
    for i,c in enumerate(cols):
        y = d[c]; Xo = X.drop(columns=[c])
        r2 = sm.OLS(y, sm.add_constant(Xo)).fit().rsquared
        out[c] = 1/(1-r2) if r2<1 else np.inf
    return out

print("\n" + "="*72)
print("二、VIF（表4-6）— 用真实列")
print("="*72)
vif_cols = ["log_aum","ARG","log_fund_age","ICI","SDI","AS_improved",
            "risk_asym","de","lsv","TO_wind","OCI_two_sided"]
v = vif_table(vif_cols)
for c in vif_cols:
    print(f"   {c:16s} VIF={v[c]:.2f}  1/VIF={1/v[c]:.3f}")

print("\n[DONE]")
