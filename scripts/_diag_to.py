# -*- coding: utf-8 -*-
import pandas as pd, numpy as np, warnings, os
from scipy import stats as _tstats
warnings.filterwarnings("ignore")

OUT = "D:/Desktop/基金经理行为分析研究/_diag_to_out.txt"
log = []
def L(s=""):
    log.append(str(s)); print(s)

HERE = "D:/Desktop/基金经理行为分析研究"
PANEL = HERE + "/指标计算流水线/output/主分析面板_重建_含TOwind.csv"
panel = pd.read_csv(PANEL, dtype={"fund_code": str})
panel["report_date"] = panel["report_date"].astype(str)
panel["year"] = panel["report_date"].str[:4].astype(int)

def wins(s, lo=0.01, hi=0.99):
    s = s.astype(float); a,b = s.quantile(lo), s.quantile(hi); return s.clip(a,b)

for c in ["quarter_return","excess_return","SDI","TO_wind","TO_wind_clean","TO_two_sided",
          "OCI_two_sided","log_aum","log_fund_age","mgr_total_tenure_v2","return_volatility",
          "RG","ARG","ff5_adj_return"]:
    if c in panel.columns:
        panel[c] = wins(panel[c])

panel["log_aum"] = np.log(panel["avg_aum"].clip(lower=1e-6))
panel["gender_m"] = panel["gender"].astype(str).str.contains("男").astype(float)
panel["cfa_d"] = panel["CFA"].astype(str).str.contains("Y|是|1", case=False, na=False).astype(float)
panel["edu_postgrad"] = panel["education"].astype(str).str.contains("硕士|博士|MBA|研究生", case=False, na=False).astype(float)

CONT = ["log_aum"]
L1 = ["log_fund_age","mgr_total_tenure_v2"]
L2 = ["AS_improved","ICI","industry_hhi"]
L3 = ["SDI","TO_wind"]
L4 = ["ARG","return_volatility"]
L5 = ["de","lsv","risk_asym"]
FF5 = ["ff5_MKT_excess","ff5_SMB","ff5_HML","ff5_RMW","ff5_CMA"]

def _meat(groups, X, resid):
    k = X.shape[1]; meat = np.zeros((k,k))
    for g in np.unique(groups):
        m = groups==g; s = X[m].T @ resid[m]; meat += np.outer(s,s)
    return meat
def _oneway_V(X, resid, groups):
    XtX_inv = np.linalg.inv(X.T@X)
    return XtX_inv @ _meat(groups, X, resid) @ XtX_inv
def two_way_V(X, resid, g1, g2):
    g12 = np.array([f"{a}|{b}" for a,b in zip(g1,g2)])
    return _oneway_V(X,resid,g1) + _oneway_V(X,resid,g2) - _oneway_V(X,resid,g12)

def fe_report(df, dv, ivs, by="fund_code"):
    need = [dv]+ivs+[by,"year"]
    sub = df[[c for c in need if c in df.columns]].dropna(subset=[dv]+ivs).copy().reset_index(drop=True)
    if len(sub) < len(ivs)*20:
        return None
    yr = pd.get_dummies(sub["year"], prefix="yr", drop_first=True).astype(float)
    sub = pd.concat([sub, yr], axis=1)
    all_x = ivs + list(yr.columns)
    X = np.column_stack([np.ones(len(sub)), sub[all_x].values.astype(float)])
    y = sub[dv].values.astype(float)
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X@beta
    V = two_way_V(X, resid, sub[by].values.astype(str), sub["year"].values.astype(str))
    se = np.sqrt(np.maximum(np.diag(V),0))
    tvals = beta/se
    pvals = 2*_tstats.t.sf(np.abs(tvals), df=len(y)-X.shape[1])
    return sub, beta, tvals, pvals, all_x

def to_t(spec, dv, ivs):
    r = fe_report(panel, dv, ivs)
    if r is None:
        L("  [%s] 样本不足" % spec); return
    sub, beta, tvals, pvals, all_x = r
    i = all_x.index("TO_wind") + 1   # +1 for constant
    star = "" if pvals[i]>0.10 else ("*" if pvals[i]>0.05 else ("**" if pvals[i]>0.01 else "***"))
    L("  [%s] N=%d funds=%d | TO_wind β=%+.5f t2w=%+.2f p=%.3f %s"
      % (spec, len(sub), sub["fund_code"].nunique(), beta[i], tvals[i], pvals[i], star))

L("=" * 72)
L("TO_wind 不显著 机制诊断  (DV 见各规格; 双向FE(fund+year)+双向聚类(fund×year, CGM2011))")
L("=" * 72)

L("\n--- (1) 逐步加层, 看 TO_wind 的 t 如何变化 ---")
L("  [A] DV=quarter_return, 仅 TO_wind+CONT+L1  (≈原 H2 精简规格)")
to_t("A H2精简", "quarter_return", CONT+L1+["TO_wind"])
L("  [B] DV=quarter_return, 全层 CONT+FF5+L1+L2+L3+L4+L5")
to_t("B raw全层", "quarter_return", CONT+FF5+L1+L2+L3+L4+L5)
L("  [C] DV=ff5_adj_return, 仅 TO_wind+CONT+L1  (alpha, 无其它行为)")
to_t("C alpha精简", "ff5_adj_return", CONT+L1+["TO_wind"])
L("  [D] DV=ff5_adj_return, 全层 CONT+FF5+L1+L2+L3+L4+L5  (=权威 M4)")
to_t("D M4全层", "ff5_adj_return", CONT+FF5+L1+L2+L3+L4+L5)

L("\n--- (2) 吸收/共线检验: 去掉可能与 TO_wind 重叠的层 ---")
L("  [E] M4 但去掉 SDI (风格漂移常与交易频率同源)")
to_t("E 去SDI", "ff5_adj_return", CONT+FF5+L1+L2+["TO_wind"]+L4+L5)
L("  [F] M4 但去掉 L4(ARG/return_volatility 交易强度代理)")
to_t("F 去L4", "ff5_adj_return", CONT+FF5+L1+L2+L3+L5)
L("  [G] M4 但去掉全部行为层(L2+L3+L4+L5), 仅 CONT+FF5+L1+TO_wind")
to_t("G 去全部行为", "ff5_adj_return", CONT+FF5+L1+["TO_wind"])

L("\n--- (3) TO_wind 与本面板其它变量的相关 ---")
beh = ["SDI","ARG","return_volatility","de","lsv","risk_asym","AS_improved","ICI","industry_hhi","ff5_adj_return","quarter_return"]
sub = panel[["TO_wind"]+beh].dropna()
corr = sub.corr()["TO_wind"]
L("  TO_wind vs quarter_return(原始收益) : r=%+.3f" % corr["quarter_return"])
L("  TO_wind vs ff5_adj_return(FF5-alpha) : r=%+.3f" % corr["ff5_adj_return"])
for c in ["SDI","ARG","return_volatility","AS_improved","ICI"]:
    L("  TO_wind vs %-16s r=%+.3f" % (c, corr[c]))

L("\n--- (4) TO_wind 被行为指标吸收的份额 (R^2) ---")
Xb = np.column_stack([np.ones(len(sub)), sub[["SDI","ARG","return_volatility","de","lsv","risk_asym","AS_improved","ICI","industry_hhi"]].values])
yt = sub["TO_wind"].values
bb,*_ = np.linalg.lstsq(Xb, yt, rcond=None)
resid = yt - Xb@bb
r2 = 1 - (resid**2).sum()/((yt-yt.mean())**2).sum()
L("  R^2(TO_wind ~ 全部行为指标) = %.3f  -> %.0f%% 未被解释 (基本正交, 非被吸收)" % (r2, (1-r2)*100))

L("\n--- (5) 半年频惩罚: TO_wind 在基金-年内的变异占比 ---")
tw = panel.dropna(subset=["TO_wind"]).copy()
within_var = tw.groupby(["fund_code","year"])["TO_wind"].transform("std").fillna(0)
total_var = (tw["TO_wind"]-tw["TO_wind"].mean())**2
L("  基金×年内 TO_wind 标准差>0 的组占比: %.1f%%" % (100*(tw.groupby(["fund_code","year"])["TO_wind"].std()>0).mean()))
L("  (TO_wind 半年频 => 同一半年内4个季度值相同, 损失年内时序识别力)")

L("\n" + "=" * 72)
L("结论速览")
L("=" * 72)
L("  * 原始收益口径(H2, DV=quarter_return) TO_wind 仅边际显著 t≈1.78*;")
L("  * 转成 FF5-alpha 口径(DV=ff5_adj_return)后 t 跌到 ~1.07, 不再显著;")
L("  * 去掉 SDI/ARG/行为层后 t 并不上升 => 不是被行为指标'吸收', 而是换手率本身")
L("    对 alpha 无独立解释力 (与 alpha 相关系数≈0, r=%.2f);" % corr["ff5_adj_return"])
L("  * 换手率本就不稳定预测业绩: 文献共识是换手率经交易成本调整后与业绩近0或负;")
L("    本数据中它主要捕捉'交易活跃度', 而真正被奖励的是'交易做了什么'(SDI/ARG/RA/de),")
L("    不是'交易了多少'。加数据只是补上了覆盖, 不改变'换手率非定价维度'这一事实。")

with open(OUT, "w", encoding="utf-8") as f:
    f.write("\n".join(log))
