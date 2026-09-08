# -*- coding: utf-8 -*-
"""选项2影响评估：在完全相同的诚实 M4 规范下，对比 旧面板(收益补全前) vs 新面板(收益补全后)
的 L4/L5 系数与 R2，判断月收益补全是否改变核心结论。非破坏性（只读两份面板）。"""
import pandas as pd, numpy as np, os, warnings
import statsmodels.api as sm
import statsmodels.formula.api as smf
warnings.filterwarnings("ignore")

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OLD = os.path.join(HERE, "指标计算流水线", "output", "主分析面板_重建_含TOwind.csv.bak_preARGext_20260816")
NEW = os.path.join(HERE, "指标计算流水线", "output", "主分析面板_重建_含TOwind.csv")

def load(path):
    p = pd.read_csv(path, dtype={"fund_code": str})
    p["report_date"] = p["report_date"].astype(str)
    p["year"] = p["report_date"].str[:4].astype(int)
    p["log_aum"] = np.log(p["avg_aum"].clip(lower=1e-6))
    p["gender_m"] = p["gender"].astype(str).str.contains("男").astype(float)
    p["cfa_d"] = p["gender"].map(lambda x: 0)  # placeholder, fixed below
    p["cfa_d"] = p["CFA"].astype(str).str.contains("Y|是|1", case=False, na=False).astype(float)
    p["edu_postgrad"] = p["education"].astype(str).str.contains("硕士|博士|MBA|研究生", case=False, na=False).astype(float)
    def wins(s, lo=0.01, hi=0.99):
        s = s.astype(float); a, b = s.quantile(lo), s.quantile(hi); return s.clip(a, b)
    for c in ["ff5_adj_return","SDI","TO_wind","TO_two_sided","OCI_two_sided",
              "AS_improved","ICI","industry_hhi","ARG","return_volatility",
              "de","lsv","risk_asym","log_aum","log_fund_age","mgr_total_tenure_v2"]:
        if c in p.columns: p[c] = wins(p[c])
    return p

# 与生成稿件引用数字的 _repro_all_OptionA 完全一致：不含 demographic 控制
RHS = ["ff5_MKT_excess","ff5_SMB","ff5_HML","ff5_RMW","ff5_CMA",
       "log_aum","log_fund_age","mgr_total_tenure_v2",
       "AS_improved","ICI","industry_hhi","SDI","TO_wind",
       "ARG","return_volatility","de","lsv","risk_asym"]
FOCUS = ["ARG","de","lsv","risk_asym"]

for label, path in [("旧面板(收益补全前)", OLD), ("新面板(收益补全后)", NEW)]:
    p = load(path)
    form = f"ff5_adj_return ~ {' + '.join(RHS)} + C(year)"
    sub = p.dropna(subset=["ff5_adj_return"]+RHS).copy()
    m = smf.ols(form, data=sub).fit(cov_type="cluster", cov_kwds={"groups": sub["fund_code"]})
    print("="*72)
    print(f"{label}  N={int(m.nobs)}  基金={sub.fund_code.nunique()}  R2={m.rsquared:.4f}  adjR2={m.rsquared_adj:.4f}")
    print("="*72)
    for v in FOCUS:
        b=m.params[v]; t=m.tvalues[v]; pv=m.pvalues[v]
        star="" if pv>0.10 else ("*" if pv>0.05 else ("**" if pv>0.01 else "***"))
        print(f"   {v:14s} β={b:+.5f}  t={t:+.2f}  p={pv:.3f}{star}")
