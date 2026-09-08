"""
DV 口径升级：法定基准调整后收益 benchmark_adj_return
- 基准定义表 355只基金/839成分行 → 匹配市场指数日线
- 缺失处理：恒生/港股通 → 缺失; 债券 → RF近似(标记); 富时A200/A600 → 沪深300替代
- 时间口径：前瞻半年（与Brinson一致），06-30→07-01, 12-31→次年01-01
产出：output/DV_基准调整后收益_2026-08-21.csv（独立）
"""
import pandas as pd, numpy as np, os, warnings
warnings.filterwarnings('ignore')

BASE = os.path.dirname(os.path.abspath(__file__))
PIPE = os.path.join(BASE, '指标计算流水线')
OUT = os.path.join(PIPE, 'output')
os.makedirs(OUT, exist_ok=True)

BENCH_DEF = os.path.join(BASE, '数据/基金基础信息/基金基准定义表.csv')
INDEX_HIST = os.path.join(BASE, '数据/基金基础信息/市场指数历史数据.csv')
FF5_DAILY = os.path.join(PIPE, 'data/FF因子/FF5日度因子.csv')
PANEL = os.path.join(OUT, '主分析面板_重建_含TOwind.csv')
BRINSON = os.path.join(OUT, 'L2_Brinson面板_2026-08-21.csv')

print("Loading data...")
# 1. 基准定义表
bdef = pd.read_csv(BENCH_DEF)
bdef['基金代码'] = bdef['基金代码'].astype(int)
print(f"  Benchmark defs: {len(bdef)} rows, {bdef['基金代码'].nunique()} funds")

# 2. 指数日线
idx = pd.read_csv(INDEX_HIST)
idx['date'] = pd.to_datetime(idx['date'])
idx['daily_ret'] = idx.groupby('index_code')['close'].pct_change()
print(f"  Index daily: {len(idx)} rows, {idx['index_code'].nunique()} indices")

# 3. FF5 日度（取 RF）
ff5 = pd.read_csv(FF5_DAILY)
ff5['date'] = pd.to_datetime(ff5['date'])
ff5['RF'] = pd.to_numeric(ff5['RF'], errors='coerce')
print(f"  FF5 daily: {len(ff5)} rows, RF range {ff5['date'].min().date()} to {ff5['date'].max().date()}")

# 指数名称映射（基准表中文名 → 市场指数代码或合成方法）
INDEX_MAP = {
    '沪深300指数': 'sh000300',
    '沪深300': 'sh000300',
    '中证500指数': 'sh000905',
    '中证500': 'sh000905',
    '中证1000指数': 'sh000852',
    '中证1000': 'sh000852',
    '上证50指数': 'sh000016',
    '上证50': 'sh000016',
    '上证综指': 'sh000001',
    '上证综合指数': 'sh000001',
    '上证指数': 'sh000001',
    '深证成指': 'sz399001',
    '深证成份指数': 'sz399001',
    '创业板指': 'sz399006',
    '创业板指数': 'sz399006',
    '中小板指': 'sz399005',
    '中小100': 'sz399005',
    # 中证800 = 沪深300 + 中证500，合成
    '中证800指数': 'CSI800_SYNTH',
    '中证800': 'CSI800_SYNTH',
    # 富时A200/A600 → 用沪深300近似（大盘股替代）
    '富时中国A200指数': 'sh000300',
    '富时中国A600指数': 'sh000300',
    # 中国战略新兴产业 → 用创业板近似
    '中国战略新兴产业成份指数': 'sz399006',
}

# 无法匹配的（标记为缺失）
MISSING_INDICES = {'恒生指数', '恒生中国国企指数', '中证港股通综合指数（人民币）',
                   '中证港股通综合指数', '恒生港股通指数', '恒生中国企业指数',
                   '中债总指数', '中债综合指数', '中债综合全价指数', '上证国债指数',
                   '中证全债指数', '中证综合债券指数', '中证综合债指数',
                   '中国债券总指数', '中国债券综合指数', '中国债券综合全价指数',
                   '活期存款基准利率', '一年期定期存款利率', '中证短融指数',
                   '中债-综合全价（总值）指数', '中债-总全价（总值）指数',
                   '中债-综合财富（总值）指数'}

def get_index_return(index_code, start, end):
    """计算指数在[start,end]期间的累积收益（日链乘）"""
    if index_code == 'CSI800_SYNTH':
        r300 = get_index_return('sh000300', start, end)
        r500 = get_index_return('sh000905', start, end)
        if pd.isna(r300) or pd.isna(r500):
            return np.nan
        return 0.5 * r300 + 0.5 * r500
    
    sub = idx[(idx['index_code'] == index_code) & 
              (idx['date'] >= start) & (idx['date'] <= end)]
    if len(sub) == 0 or sub['daily_ret'].isna().all():
        return np.nan
    return float(np.prod(1 + sub['daily_ret'].fillna(0)) - 1)

def get_rf_return(start, end):
    """无风险利率累积"""
    sub = ff5[(ff5['date'] >= start) & (ff5['date'] <= end)]
    if len(sub) == 0:
        return np.nan
    return float(np.prod(1 + sub['RF'].fillna(0)) - 1)

def get_fund_ret_6m(fund_code, snapshot_date, panel):
    """从面板取基金前瞻6月收益（复用Brinson的fund_ret_6m）"""
    pass  # 从Brinson CSV取

# 4. 对每只基金-快照计算基准收益
brinson = pd.read_csv(BRINSON)
brinson['fund_code'] = brinson['fund_code'].astype(int)
fund_rets = brinson[['fund_code','report_date','fund_ret_6m']].copy()

snapshots = sorted(bdef.set_index('基金_code' if '基金_code' in bdef else '基金代码').index.unique()) \
    if False else sorted(brinson['report_date'].unique())

results = []
n_resolved = 0
n_partial = 0
n_failed = 0

print(f"\nProcessing {len(snapshots)} snapshots × {bdef['基金代码'].nunique()} funds...")
for snap in snapshots:
    dt = pd.to_datetime(snap)
    if dt.month == 6:
        start = pd.Timestamp(year=dt.year, month=7, day=1)
        end = pd.Timestamp(year=dt.year, month=12, day=31)
    else:
        start = pd.Timestamp(year=dt.year+1, month=1, day=1)
        end = pd.Timestamp(year=dt.year+1, month=6, day=30)
    
    snap_funds = fund_rets[fund_rets['report_date'] == snap]
    
    for _, fr in snap_funds.iterrows():
        fc = fr['fund_code']
        fund_ret = fr['fund_ret_6m']
        if pd.isna(fund_ret):
            continue
        
        bdef_fund = bdef[bdef['基金代码'] == fc]
        if len(bdef_fund) == 0:
            continue  # 无基准定义
        
        bench_ret = 0.0
        equity_weight_sum = 0.0
        matched_weight = 0.0
        rf_approx_weight = 0.0
        missing_weight = 0.0
        n_components = len(bdef_fund)
        
        for _, comp in bdef_fund.iterrows():
            idx_name = comp['成分指数'].strip()
            w = comp['权重']
            asset_class = comp['资产类别']
            
            mapped = INDEX_MAP.get(idx_name)
            
            if mapped:
                r = get_index_return(mapped, start, end)
                if pd.isna(r):
                    # 指数数据不在该时间段
                    missing_weight += w
                else:
                    bench_ret += w * r
                    matched_weight += w
                    if asset_class == 'equity':
                        equity_weight_sum += w
            elif idx_name in MISSING_INDICES:
                if asset_class == 'bond':
                    # 债券用RF近似
                    r = get_rf_return(start, end)
                    if pd.isna(r):
                        missing_weight += w
                    else:
                        bench_ret += w * r
                        rf_approx_weight += w
                else:
                    missing_weight += w
            else:
                missing_weight += w
        
        total_w = matched_weight + rf_approx_weight + missing_weight
        
        if total_w > 0:
            # 归一化（如果missing>0，按已匹配的归一）
            if missing_weight > 0 and matched_weight + rf_approx_weight > 0:
                scale = 1.0 / (matched_weight + rf_approx_weight)
                bench_ret *= scale
            
            adj_ret = fund_ret - bench_ret
            
            if missing_weight < 0.01:
                coverage = 'full'
                n_resolved += 1
            elif rf_approx_weight > 0:
                coverage = 'partial_rf'
                n_partial += 1
            else:
                coverage = 'partial'
                n_partial += 1
        else:
            adj_ret = np.nan
            coverage = 'failed'
            n_failed += 1
        
        results.append({
            'fund_code': fc,
            'report_date': snap,
            'fund_ret_6m': fund_ret,
            'bench_ret_6m': bench_ret if total_w > 0 else np.nan,
            'benchmark_adj_return': adj_ret,
            'coverage': coverage,
            'equity_weight': equity_weight_sum,
            'matched_weight': matched_weight,
            'rf_approx_weight': rf_approx_weight,
            'missing_weight': missing_weight,
            'n_components': n_components,
        })

df = pd.DataFrame(results)
print(f"\nDone. {len(df)} fund-snapshots.")
print(f"  full coverage: {n_resolved} | partial (rf approx): {n_partial} | failed: {n_failed}")

print("\n=== benchmark_adj_return 描述统计 ===")
s = df['benchmark_adj_return'].dropna()
print(f"  N={len(s)}, mean={s.mean():.4f}, std={s.std():.4f}, min={s.min():.4f}, max={s.max():.4f}")

print("\n=== coverage 分布 ===")
print(df['coverage'].value_counts().to_string())

# 与面板对齐（panel_date映射）
df['panel_date'] = df['report_date'].apply(
    lambda d: pd.Timestamp(d).replace(month=7, day=1).strftime('%Y-%m-%d') if d[5:7]=='06'
    else (pd.Timestamp(d)+pd.Timedelta(days=1)).replace(month=1, day=1).strftime('%Y-%m-%d')
)

# 与 ff5_adj_return 对齐检验
panel = pd.read_csv(PANEL, usecols=['fund_code','report_date','ff5_adj_return','quarter_return'], dtype={'fund_code':str})
panel['fund_code'] = panel['fund_code'].astype(int)
merged = df.merge(panel, left_on=['fund_code','panel_date'], right_on=['fund_code','report_date'], how='inner', suffixes=('_bm','_panel'))
print(f"\n=== 与面板对齐: {len(merged)} obs ===")
if len(merged) > 10:
    m = merged.dropna(subset=['benchmark_adj_return','ff5_adj_return'])
    if len(m) > 10:
        c = m['benchmark_adj_return'].corr(m['ff5_adj_return'])
        c2 = m['benchmark_adj_return'].corr(m['quarter_return'])
        print(f"  corr(benchmark_adj_return, ff5_adj_return) = {c:.3f}")
        print(f"  corr(benchmark_adj_return, quarter_return) = {c2:.3f}")
        print(f"  corr(fund_ret_6m, quarter_return) = {m['fund_ret_6m'].corr(m['quarter_return']):.3f}")

out_path = os.path.join(OUT, 'DV_基准调整后收益_2026-08-21.csv')
df.to_csv(out_path, index=False)
print(f"\nOutput: {out_path}")
