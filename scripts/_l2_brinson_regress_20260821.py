"""
M4 规格双向聚类回归检验：L2 Brinson 分解 + DV 基准口径
检验1: alloc_ret/select_ret 替代 AS_improved
检验2: benchmark_adj_return 作为替代 DV
检验3: DE×alloc_ret / RA×select_ret 交互
"""
import pandas as pd, numpy as np, os, warnings
import statsmodels.formula.api as smf
from scipy import stats as spstats
warnings.filterwarnings('ignore')

BASE = os.path.dirname(os.path.abspath(__file__))
PIPE = os.path.join(BASE, '指标计算流水线')
OUT = os.path.join(PIPE, 'output')
PANEL = os.path.join(OUT, '主分析面板_重建_含TOwind.csv')
BRINSON = os.path.join(OUT, 'L2_Brinson面板_2026-08-21.csv')
BENCH = os.path.join(OUT, 'DV_基准调整后收益_2026-08-21.csv')
RESULTS_JSON = os.path.join(OUT, 'L2_Brinson回归结果_2026-08-21.json')

# ===================== 回归工具 =====================
def winsor(s, lo=0.01, hi=0.99):
    s = s.astype(float); a, b = s.quantile(lo), s.quantile(hi)
    return s.clip(a, b)

def _meat(groups, X, resid):
    k = X.shape[1]; meat = np.zeros((k, k))
    for gg in np.unique(groups):
        m = groups == gg; v = X[m].T @ resid[m]; meat += np.outer(v, v)
    return meat

def _oneway_V(X, resid, groups):
    return np.linalg.inv(X.T @ X) @ _meat(groups, X, resid) @ np.linalg.inv(X.T @ X)

def two_way_V(X, resid, g1, g2):
    g12 = np.array([f"{a}|{b}" for a, b in zip(g1, g2)])
    return _oneway_V(X, resid, g1) + _oneway_V(X, resid, g2) - _oneway_V(X, resid, g12)

def est(d, rhs, target, dv, fe=True):
    """返回 dict: beta, t2w, p2w, N, nfund"""
    rhs = list(rhs)
    sub = d.dropna(subset=rhs + [dv]).copy()
    keep = []
    for r in rhs:
        sv = sub[r]
        if sv.notna().sum() > 1 and sv.std() > 1e-12:
            keep.append(r)
    rhs = keep
    if len(rhs) == 0:
        return None
    form = dv + " ~ " + " + ".join(rhs) + (" + C(year)" if fe else "")
    m = smf.ols(form, data=sub).fit(cov_type="cluster", cov_kwds={"groups": sub["fund_code"]})
    X = np.asarray(m.model.data.exog, float); resid = np.asarray(m.resid, float)
    g1 = sub["fund_code"].values.astype(str)
    V2 = two_way_V(X, resid, g1, sub["year"].values.astype(str))
    se2 = np.sqrt(np.maximum(np.diag(V2), 0))
    t2 = m.params.values / se2; p2 = 2.0*spstats.t.sf(np.abs(t2), df=len(resid)-X.shape[1])
    names = list(m.params.index)
    if target not in names:
        return None
    i = names.index(target)
    return {"beta": float(m.params.values[i]), "t2w": float(t2[i]), "p2w": float(p2[i]),
            "N": int(m.nobs), "nfund": int(sub["fund_code"].nunique())}

def stars(p):
    return "" if p > 0.10 else ("*" if p > 0.05 else ("**" if p > 0.01 else "***"))

# ===================== 变量定义 =====================
FF5  = ["ff5_MKT_excess","ff5_SMB","ff5_HML","ff5_RMW","ff5_CMA"]
CONT = ["log_aum"]
L1   = ["log_fund_age","mgr_total_tenure_v2"]
L2_BASE = ["AS_improved","ICI","industry_hhi"]
L3   = ["SDI","TO_wind"]
L4   = ["ARG","return_volatility"]
L5   = ["de","lsv","risk_asym"]

# ===================== 数据加载与合并 =====================
print("Loading panel...")
p = pd.read_csv(PANEL, dtype={'fund_code':str})
p['fund_code'] = p['fund_code'].astype(int)
p['report_date'] = pd.to_datetime(p['report_date'])
p['year'] = p['report_date'].dt.year

# 半年映射：panel report_date → 对应持仓快照的半年
def to_snapshot_date(rd):
    """季度初 → 最近过去的半年末快照"""
    if rd.month in [7,8,9,10,11,12]:
        return pd.Timestamp(year=rd.year, month=6, day=30)
    else:
        return pd.Timestamp(year=rd.year-1, month=12, day=31)
p['snapshot_date'] = p['report_date'].apply(to_snapshot_date)
p['snapshot_date_str'] = p['snapshot_date'].dt.strftime('%Y-%m-%d')

print("Loading Brinson...")
br = pd.read_csv(BRINSON)
br['fund_code'] = br['fund_code'].astype(int)
br_cols = ['fund_code','report_date','alloc_ret','select_ret','interaction','alloc_share']
br = br[br_cols].rename(columns={'report_date': 'snapshot_date_str'})

print("Loading benchmark DV...")
bm = pd.read_csv(BENCH)
bm['fund_code'] = bm['fund_code'].astype(int)
bm_cols = ['fund_code','report_date','benchmark_adj_return','coverage']
bm = bm[bm_cols].rename(columns={'report_date': 'snapshot_date_str'})

# 合并
p = p.merge(br, on=['fund_code','snapshot_date_str'], how='left')
p = p.merge(bm, on=['fund_code','snapshot_date_str'], how='left')
print(f"  Panel: {len(p)} rows")
print(f"  alloc_ret non-null: {p['alloc_ret'].notna().sum()}")
print(f"  benchmark_adj_return non-null: {p['benchmark_adj_return'].notna().sum()}")

# 缩尾
for v in CONT + FF5 + L1 + L2_BASE + L3 + L4 + L5 + ['alloc_ret','select_ret','interaction','alloc_share']:
    if v in p.columns:
        p[v+"_w"] = winsor(p[v])
p['ff5_adj_return_w'] = winsor(p['ff5_adj_return'])
p['benchmark_adj_return_w'] = winsor(p['benchmark_adj_return'])
p['log_aum'] = np.log(pd.to_numeric(p['avg_aum'], errors='coerce').clip(lower=1e-9))
p['log_aum_w'] = winsor(p['log_aum'])

# ===================== 回归检验 =====================
results = {}

# ---- 检验1: alloc_ret/select_ret 替代 AS_improved ----
print("\n" + "="*72)
print("检验1: L2 Brinson 分解替代 AS_improved (DV=ff5_adj_return_w)")
print("="*72)

# 1a. 基线（含 AS_improved）
rhs_base = CONT + ["log_aum_w"] if "log_aum_w" not in CONT else CONT
# 正确的控制变量列表
rhs_M4_base = ["log_aum_w"] + FF5 + L1 + L2_BASE + L3 + L4 + L5
for v in FF5:
    rhs_M4_base = [x if x != v else v+"_w" for x in rhs_M4_base]
# 简化：用 _w 版本
rhs_base = (["log_aum_w"] + [f+"_w" for f in FF5] + 
            [f+"_w" for f in L1] + 
            ["AS_improved_w"] + [f+"_w" for f in ["ICI","industry_hhi"]] +
            [f+"_w" for f in L3] + [f+"_w" for f in L4] + [f+"_w" for f in L5])

for tgt in ["de_w","lsv_w","risk_asym_w"]:
    r = est(p, rhs_base, tgt, dv="ff5_adj_return_w")
    if r:
        print(f"  基线 {tgt}: β={r['beta']:.5f} t2w={r['t2w']:.2f} p={r['p2w']:.3f}{stars(r['p2w'])} N={r['N']}")
        results[f"1a_baseline_{tgt}"] = r

# 1b. 替代：alloc_ret + select_ret 替代 AS_improved
rhs_alt = [x for x in rhs_base if x != "AS_improved_w"] + ["alloc_ret_w","select_ret_w"]
for tgt in ["de_w","lsv_w","risk_asym_w"]:
    r = est(p, rhs_alt, tgt, dv="ff5_adj_return_w")
    if r:
        print(f"  替代 {tgt}: β={r['beta']:.5f} t2w={r['t2w']:.2f} p={r['p2w']:.3f}{stars(r['p2w'])} N={r['N']}")
        results[f"1b_brinson_{tgt}"] = r

# alloc_ret/select_ret 自身系数
for tgt in ["alloc_ret_w","select_ret_w"]:
    r = est(p, rhs_alt, tgt, dv="ff5_adj_return_w")
    if r:
        print(f"  {tgt}: β={r['beta']:.5f} t2w={r['t2w']:.2f} p={r['p2w']:.3f}{stars(r['p2w'])} N={r['N']}")
        results[f"1b_{tgt}"] = r

# ---- 检验2: benchmark_adj_return 作为替代 DV ----
print("\n" + "="*72)
print("检验2: benchmark_adj_return 作为替代 DV (DE/RA 系数稳健性)")
print("="*72)

rhs_M4 = rhs_base  # 含 AS_improved_w
for tgt in ["de_w","lsv_w","risk_asym_w"]:
    r = est(p, rhs_M4, tgt, dv="benchmark_adj_return_w")
    if r:
        print(f"  DV=benchmark_adj {tgt}: β={r['beta']:.5f} t2w={r['t2w']:.2f} p={r['p2w']:.3f}{stars(r['p2w'])} N={r['N']}")
        results[f"2_bench_dv_{tgt}"] = r

# ---- 检验3: 交互效应 ----
print("\n" + "="*72)
print("检验3: DE×alloc_ret / RA×select_ret 交互")
print("="*72)

p["de_x_alloc"] = p["de_w"] * p["alloc_ret_w"]
p["ra_x_select"] = p["risk_asym_w"] * p["select_ret_w"]
p["de_x_alloc_w"] = winsor(p["de_x_alloc"])
p["ra_x_select_w"] = winsor(p["ra_x_select"])

rhs_int = rhs_alt + ["de_x_alloc_w","ra_x_select_w"]
for tgt in ["de_x_alloc_w","ra_x_select_w"]:
    r = est(p, rhs_int, tgt, dv="ff5_adj_return_w")
    if r:
        print(f"  {tgt}: β={r['beta']:.5f} t2w={r['t2w']:.2f} p={r['p2w']:.3f}{stars(r['p2w'])} N={r['N']}")
        results[f"3_interaction_{tgt}"] = r

# 交互下 DE/RA 主效应
for tgt in ["de_w","risk_asym_w"]:
    r = est(p, rhs_int, tgt, dv="ff5_adj_return_w")
    if r:
        print(f"  交互下 {tgt}: β={r['beta']:.5f} t2w={r['t2w']:.2f} p={r['p2w']:.3f}{stars(r['p2w'])} N={r['N']}")
        results[f"3_main_{tgt}"] = r

# ===================== 输出 =====================
import json
with open(RESULTS_JSON, 'w', encoding='utf-8') as f:
    json.dump(results, f, indent=2, ensure_ascii=False)
print(f"\nResults saved: {RESULTS_JSON}")
print(f"\n{'='*72}")
print("SUMMARY")
print(f"{'='*72}")
print("检验1 (alloc/select 替代 AS_improved):")
for k in sorted(results.keys()):
    if k.startswith("1"):
        r = results[k]
        print(f"  {k:30s} β={r['beta']:+.5f} t2w={r['t2w']:+.2f} p={r['p2w']:.3f}{stars(r['p2w'])}")
print("检验2 (benchmark_adj_return DV):")
for k in sorted(results.keys()):
    if k.startswith("2"):
        r = results[k]
        print(f"  {k:30s} β={r['beta']:+.5f} t2w={r['t2w']:+.2f} p={r['p2w']:.3f}{stars(r['p2w'])}")
print("检验3 (交互效应):")
for k in sorted(results.keys()):
    if k.startswith("3"):
        r = results[k]
        print(f"  {k:30s} β={r['beta']:+.5f} t2w={r['t2w']:+.2f} p={r['p2w']:.3f}{stars(r['p2w'])}")
