# -*- coding: utf-8 -*-
"""#170 交叉验证：自实现 CGM 双向聚类 vs linearmodels.PanelOLS 双向聚类(金标准)。
若两者一致，证明自实现正确；差异则定位 bug。"""
import os, numpy as np, pandas as pd, warnings
warnings.filterwarnings("ignore")
from scipy import stats as _tstats

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PANEL = os.path.join(HERE, "指标计算流水线", "output", "主分析面板_重建_含TOwind.csv")
panel = pd.read_csv(PANEL, dtype={"fund_code": str})
panel["report_date"] = panel["report_date"].astype(str)
panel["year"] = panel["report_date"].str[:4].astype(int)
for c in ["quarter_return", "SDI"]:
    panel[c] = panel[c].astype(float)

CONTROLS = ["log_aum", "log_fund_age", "mgr_total_tenure_v2", "gender_m", "cfa_d", "edu_postgrad"]
panel["log_aum"] = np.log(panel["avg_aum"].clip(lower=1e-6))
panel["gender_m"] = panel["gender"].astype(str).str.contains("男").astype(float)
panel["cfa_d"] = panel["CFA"].astype(str).str.contains("Y|是|1", case=False, na=False).astype(float)
panel["edu_postgrad"] = panel["education"].astype(str).str.contains("硕士|博士|MBA|研究生", case=False, na=False).astype(float)

dv, iv = "quarter_return", ["SDI"] + CONTROLS

# ---------- 子集 ----------
need = [dv] + iv + ["fund_code", "year"]
sub = panel[[c for c in need if c in panel.columns]].dropna(subset=[dv] + iv).copy().reset_index(drop=True)
print("子集 N=%d 基金=%d" % (len(sub), sub["fund_code"].nunique()))

# ---------- (A) 自实现 CGM 双向聚类（与回归脚本同口径：仅 fund demeaning + year 哑变量）----------
yr = pd.get_dummies(sub["year"], prefix="yr", drop_first=True).astype(float)
sub = pd.concat([sub, yr], axis=1)
all_x = iv + list(yr.columns)
g = sub.groupby("fund_code")
Xdm = sub[all_x] - g[all_x].transform("mean")
ydm = (sub[dv] - g[dv].transform("mean")).values
X = Xdm[all_x].values.astype(float); y = ydm.astype(float)
beta, *_ = np.linalg.lstsq(X, y, rcond=None)
resid = y - X @ beta

def _meat(groups, X, resid):
    k = X.shape[1]; meat = np.zeros((k, k))
    for gg in np.unique(groups):
        m = groups == gg; s = X[m].T @ resid[m]; meat += np.outer(s, s)
    return meat
def _oneway_V(X, resid, groups):
    XtX_inv = np.linalg.inv(X.T @ X); return XtX_inv @ _meat(groups, X, resid) @ XtX_inv
def two_way_V(X, resid, g1, g2):
    g12 = np.array([f"{a}|{b}" for a, b in zip(g1, g2)])
    return _oneway_V(X, resid, g1) + _oneway_V(X, resid, g2) - _oneway_V(X, resid, g12)

V = two_way_V(X, resid, sub["fund_code"].values.astype(str), sub["year"].values.astype(str))
se = np.sqrt(np.maximum(np.diag(V), 0))
t_mine = beta / se
p_mine = 2.0 * _tstats.t.sf(np.abs(t_mine), df=len(y) - X.shape[1])
j_sdi = iv.index("SDI")
print("\n[A] 自实现 CGM 双向聚类:")
print("    SDI beta=%.5f  t=%.3f  p=%.4f" % (beta[j_sdi], t_mine[j_sdi], p_mine[j_sdi]))

# ---------- (B) linearmodels 金标准：双向 FE + 双向聚类 ----------
try:
    from linearmodels.panel import PanelOLS
    p = sub.copy()
    p["entity"] = p["fund_code"].astype(str)
    p["time"] = p["year"].astype(int)
    p = p.set_index(["entity", "time"]).sort_index()
    exog = p[iv + ["year"]]  # year 作为时变控制（PanelOLS 用 time_effects 吸收年份）
    # 用 time_effects 吸收年份固定效应；cluster 双向
    mod = PanelOLS(p[dv], exog, entity_effects=True, time_effects=True,
                   drop_absorbed=True).fit(cov_type="clustered",
                                           cluster_entity=True, cluster_time=True)
    sdi_row = [i for i, n in enumerate(mod.params.index) if n == "SDI"][0]
    b2 = mod.params.iloc[sdi_row]; t2 = mod.tstats.iloc[sdi_row]; p2 = mod.pvalues.iloc[sdi_row]
    print("\n[B] linearmodels 双向FE+双向聚类(金标准):")
    print("    SDI beta=%.5f  t=%.3f  p=%.4f" % (b2, t2, p2))
    print("\n一致？（|t| 差 < 0.05）=", abs(t_mine[j_sdi] - t2) < 0.05)
except ImportError:
    print("\n[B] linearmodels 未安装，尝试 pip（仅本沙箱验证用）")
    import subprocess, sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "linearmodels", "-q"])
    from linearmodels.panel import PanelOLS
    # 重复上面
    p = sub.copy(); p["entity"] = p["fund_code"].astype(str); p["time"] = p["year"].astype(int)
    p = p.set_index(["entity", "time"]).sort_index()
    exog = p[iv + ["year"]]
    mod = PanelOLS(p[dv], exog, entity_effects=True, time_effects=True,
                   drop_absorbed=True).fit(cov_type="clustered",
                                           cluster_entity=True, cluster_time=True)
    sdi_row = [i for i, n in enumerate(mod.params.index) if n == "SDI"][0]
    b2 = mod.params.iloc[sdi_row]; t2 = mod.tstats.iloc[sdi_row]; p2 = mod.pvalues.iloc[sdi_row]
    print("\n[B] linearmodels 双向FE+双向聚类(金标准):")
    print("    SDI beta=%.5f  t=%.3f  p=%.4f" % (b2, t2, p2))
    print("\n一致？（|t| 差 < 0.05）=", abs(t_mine[j_sdi] - t2) < 0.05)
