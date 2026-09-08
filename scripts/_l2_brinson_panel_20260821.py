"""
L2 Brinson 配置/选股分解 — 面板级计算
- 持仓：非v2全量修正版（仅6/12月全持仓快照，权重和>80%）
- 市场组合：全市场个股月收益等权口径（5261股，无市值数据时等权为学术标准替代）
- 指标：alloc_share(配置主动份额)/select_share(行业内选股主动份额)
        alloc_ret(配置收益贡献)/select_ret(选股收益贡献)
- 时间口径：前瞻半年（6/30快照→7-12月收益；12/31快照→次年1-6月收益）
- 恒等式：alloc_ret + select_ret + interaction ≈ 基金收益 - 市场收益
产出：output/L2_Brinson面板_2026-08-21.csv（独立，不改权威面板）
"""
import pandas as pd, numpy as np, sys, os, warnings
from itertools import product
warnings.filterwarnings('ignore')

BASE = os.path.dirname(os.path.abspath(__file__))
PIPE = os.path.join(BASE, '指标计算流水线')
OUT = os.path.join(PIPE, 'output')
os.makedirs(OUT, exist_ok=True)

HOLD = os.path.join(PIPE, 'data/L2_持仓偏离层/基金持仓明细_全量修正版.csv')
INDUSTRY = os.path.join(PIPE, 'data/L2_持仓偏离层/股票行业映射.csv')
RETURNS = os.path.join(PIPE, 'data/股价行情/个股月收益率_全量.csv')
PANEL = os.path.join(OUT, '主分析面板_重建_含TOwind.csv')

print("Loading data...")
# 1. 持仓（仅6/12月全持仓）
h = pd.read_csv(HOLD, encoding='utf-8-sig', low_memory=False)
h['hold_ratio'] = pd.to_numeric(h['hold_ratio'], errors='coerce')
h['fund_code'] = h['fund_code'].astype(int)
h['stock_code'] = h['stock_code'].astype(str).str.lstrip("'").str.lstrip('0')
h = h[h['report_date'].str[5:7].isin(['06','12'])].copy()
# 权重和>80%的快照
wsum = h.groupby(['fund_code','report_date'])['hold_ratio'].sum().reset_index()
wsum = wsum[wsum['hold_ratio'] > 80]
h = h.merge(wsum[['fund_code','report_date']], on=['fund_code','report_date'])
h['hold_ratio'] = h['hold_ratio'] / 100.0  # 百分比转小数
print(f"  Holdings: {len(h)} rows, {h['fund_code'].nunique()} funds, {h['report_date'].nunique()} snapshots")

# 2. 行业映射
ind = pd.read_csv(INDUSTRY, dtype={'stock_code': str})
ind['stock_code'] = ind['stock_code'].str.lstrip("'").str.lstrip('0')
ind_map = dict(zip(ind['stock_code'], ind['sw31_industry']))
industries = sorted(set(ind_map.values()))
print(f"  Industries: {len(industries)} SW sectors")

# 3. 个股月收益
r = pd.read_csv(RETURNS, dtype={'stock_code': str})
r['stock_code'] = r['stock_code'].str.lstrip("'").str.lstrip('0')
r['date'] = pd.to_datetime(r['date'])
r['ym'] = r['date'].dt.to_period('M')
r['monthly_return'] = pd.to_numeric(r['monthly_return'], errors='coerce')
r = r.dropna(subset=['monthly_return'])
print(f"  Returns: {len(r)} rows, {r['stock_code'].nunique()} stocks, {r['ym'].min()} to {r['ym'].max()}")

# 持仓合并行业
h['industry'] = h['stock_code'].map(ind_map)
h_missing = h['industry'].isna().sum()
print(f"  Holdings missing industry: {h_missing}/{len(h)} ({h_missing/len(h)*100:.1f}%)")
h = h.dropna(subset=['industry'])

# 持仓合并收益 — 前瞻6个月
def get_forward_6m_returns(snapshot_date_str):
    """对6/30快照取7-12月，对12/31取次年1-6月"""
    dt = pd.to_datetime(snapshot_date_str)
    if dt.month == 6:
        start = pd.Timestamp(year=dt.year, month=7, day=1)
        end = pd.Timestamp(year=dt.year, month=12, day=31)
    else:  # 12
        start = pd.Timestamp(year=dt.year+1, month=1, day=1)
        end = pd.Timestamp(year=dt.year+1, month=6, day=30)
    sub = r[(r['date'] >= start) & (r['date'] <= end)].copy()
    # 每只股票半年链乘收益
    sub = sub.groupby('stock_code')['monthly_return'].apply(
        lambda x: np.prod(1 + x) - 1 if len(x) > 0 else np.nan
    ).reset_index()
    sub.columns = ['stock_code', 'ret_6m']
    return sub

# 4. 计算每个快照的Brinson指标
snapshots = sorted(h['report_date'].unique())
results = []

print(f"\nProcessing {len(snapshots)} snapshots...")
for si, snap in enumerate(snapshots):
    if si % 20 == 0:
        print(f"  [{si+1}/{len(snapshots)}] {snap}")
    
    hold_snap = h[h['report_date'] == snap].copy()
    
    # 前瞻6个月个股收益
    fwd = get_forward_6m_returns(snap)
    hold_snap = hold_snap.merge(fwd, on='stock_code', how='left')
    n_matched = hold_snap['ret_6m'].notna().sum()
    n_total = len(hold_snap)
    # 用匹配到的个股权重归一化
    hold_matched = hold_snap.dropna(subset=['ret_6m']).copy()
    if len(hold_matched) == 0:
        continue
    
    # --- 基金侧 ---
    # 基金行业权重（用匹配到收益的个股权重归一化）
    w_p = hold_matched.groupby('industry')['hold_ratio'].sum()
    w_p = w_p / w_p.sum()
    
    # 基金行业收益（行业内个股等权加权，由持仓权重加权）
    hold_matched['wr'] = hold_matched['hold_ratio']
    grp_p = hold_matched.groupby('industry').agg(
        w_sum=('hold_ratio','sum'),
        wr_sum=('ret_6m', lambda x: (hold_matched.loc[x.index,'hold_ratio']*x).sum())
    )
    grp_p['ret_p'] = grp_p['wr_sum'] / grp_p['w_sum']
    
    # --- 市场侧 ---
    # 市场行业权重与收益（等权，全市场有收益的股票）
    fwd_all = fwd.dropna()
    fwd_all = fwd_all[fwd_all['stock_code'].isin(ind_map)]  # 只用有行业映射的
    fwd_all['industry'] = fwd_all['stock_code'].map(ind_map)
    fwd_all = fwd_all.dropna(subset=['industry'])
    
    n_total_mkt = len(fwd_all)
    mkt_by_ind = fwd_all.groupby('industry').agg(
        n=('stock_code','count'),
        ret=('ret_6m','mean')
    )
    mkt_by_ind['w_b'] = mkt_by_ind['n'] / n_total_mkt
    
    # 市场总收益（等权）
    ret_b_total = fwd_all['ret_6m'].mean()
    
    # --- 对齐行业 ---
    all_inds = sorted(set(w_p.index) | set(mkt_by_ind.index))
    w_p = w_p.reindex(all_inds, fill_value=0)
    ret_p = grp_p['ret_p'].reindex(all_inds, fill_value=0)
    w_b = mkt_by_ind['w_b'].reindex(all_inds, fill_value=0)
    ret_b = mkt_by_ind['ret'].reindex(all_inds, fill_value=0)
    
    # --- Brinson 分解（BHB模型，恒等式闭合） ---
    # AR = Σ(w_p - w_b) * r_b       (配置效应)
    # SR = Σ w_b * (r_p - r_b)       (选股效应，BHB用w_b)
    # IR = Σ(w_p - w_b)*(r_p - r_b)  (交互)
    # AR + SR + IR = R_p - R_b (恒等式)
    AR = float(((w_p - w_b) * ret_b).sum())
    SR = float((w_b * (ret_p - ret_b)).sum())
    IR = float(((w_p - w_b) * (ret_p - ret_b)).sum())
    
    # 主动份额分解
    # alloc_share = ½Σ|w_p - w_b|
    # select_share = Σ w_p * ½Σ_j|w_pj_norm - w_bj_norm| (行业内)
    alloc_share = float(0.5 * (w_p - w_b).abs().sum())
    
    # 行业内选股偏离（简化：用基金行业内持仓 vs 市场等权行业内）
    # 由于市场是等权，行业内每个股票权重 = 1/n_industry
    # 基金行业内每个股票权重 = hold_ratio / w_p[industry]
    # select_share = Σ_industry w_p[ind] * ½Σ|基金个股归一权重 - 市场个股归一权重|
    sel_parts = []
    for ind_name in all_inds:
        if w_p[ind_name] < 1e-8:
            continue
        fund_stocks = hold_matched[hold_matched['industry'] == ind_name].copy()
        if len(fund_stocks) == 0:
            continue
        fund_stocks['w_norm'] = fund_stocks['hold_ratio'] / fund_stocks['hold_ratio'].sum()
        
        mkt_stocks = fwd_all[fwd_all['industry'] == ind_name]
        n_mkt = len(mkt_stocks)
        if n_mkt == 0:
            continue
        mkt_w = 1.0 / n_mkt  # 等权
        
        # 行业内偏离 = ½Σ|基金权重 - 市场等权|
        # 用基金持仓的股票集合 vs 市场全部股票
        fund_set = set(fund_stocks['stock_code'])
        mkt_set = set(mkt_stocks['stock_code'])
        all_stocks = fund_set | mkt_set
        
        dev_sum = 0.0
        for s in all_stocks:
            fp = fund_stocks.loc[fund_stocks['stock_code']==s, 'w_norm']
            fp = float(fp.iloc[0]) if len(fp) > 0 else 0.0
            bp = mkt_w if s in mkt_set else 0.0
            dev_sum += abs(fp - bp)
        
        sel_parts.append(w_p[ind_name] * 0.5 * dev_sum)
    
    select_share = float(sum(sel_parts)) if sel_parts else np.nan
    
    # 基金总收益（前瞻6月，持仓加权）
    ret_p_total = float((hold_matched['hold_ratio'] * hold_matched['ret_6m']).sum() / hold_matched['hold_ratio'].sum())
    
    # 恒等式验证
    excess = ret_p_total - ret_b_total
    residual = excess - AR - SR - IR
    
    # 记录每只基金
    for fc in hold_snap['fund_code'].unique():
        results.append({
            'fund_code': fc,
            'report_date': snap,
            'alloc_ret': AR,
            'select_ret': SR,
            'interaction': IR,
            'alloc_share': alloc_share,
            'select_share': select_share,
            'fund_ret_6m': ret_p_total,
            'mkt_ret_6m': ret_b_total,
            'excess_ret': excess,
            'identity_residual': residual,
            'n_stocks_fund': int(hold_matched['fund_code'].eq(fc).sum()),
            'match_rate': n_matched / n_total if n_total > 0 else 0,
        })

df = pd.DataFrame(results)
print(f"\nDone. {len(df)} fund-snapshots computed.")

# 恒等式检验
print("\n=== 恒等式检验 ===")
print(f"  alloc_ret + select_ret + interaction mean: {df[['alloc_ret','select_ret','interaction']].sum(axis=1).mean():.6f}")
print(f"  excess_ret mean: {df['excess_ret'].mean():.6f}")
print(f"  identity_residual: mean={df['identity_residual'].mean():.2e}, std={df['identity_residual'].std():.2e}, max|.|={df['identity_residual'].abs().max():.2e}")

# 描述统计
print("\n=== 指标描述统计 ===")
for col in ['alloc_ret','select_ret','interaction','alloc_share','select_share','excess_ret']:
    s = df[col].dropna()
    print(f"  {col}: N={len(s)}, mean={s.mean():.4f}, std={s.std():.4f}, min={s.min():.4f}, max={s.max():.4f}")

# 与面板AS_improved对齐检验
print("\n=== 与面板AS_improved对齐 ===")
panel = pd.read_csv(PANEL, usecols=['fund_code','report_date','AS_improved'], dtype={'fund_code':str})
panel['fund_code'] = panel['fund_code'].astype(int)
# 持仓快照06-30 → 面板07-01; 12-31 → 次年01-01
df['panel_date'] = df['report_date'].apply(
    lambda d: pd.Timestamp(d).replace(month=7, day=1) if d[5:7]=='06' 
    else (pd.Timestamp(d)+pd.Timedelta(days=1)).replace(month=1, day=1)
)
df['panel_date'] = df['panel_date'].dt.strftime('%Y-%m-%d')
merged = df.merge(panel, left_on=['fund_code','panel_date'], right_on=['fund_code','report_date'], how='inner', suffixes=('_brin','_panel'))
print(f"  Merged: {len(merged)} obs")
if len(merged) > 10:
    for col in ['alloc_share','alloc_ret','select_ret']:
        c = merged[col].corr(merged['AS_improved'])
        print(f"  corr({col}, AS_improved) = {c:.3f}")

# 输出
out_path = os.path.join(OUT, 'L2_Brinson面板_2026-08-21.csv')
df.to_csv(out_path, index=False)
print(f"\nOutput: {out_path}")
