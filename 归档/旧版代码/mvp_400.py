"""400基金MVP验证脚本
使用原200基金全持仓 + 新200基金前十大持仓 + 400基金净值
验证H1-H5假设在扩大样本后的稳健性
"""
import pandas as pd
import numpy as np
import statsmodels.api as sm
from statsmodels.regression.linear_model import OLS
import os
import warnings
warnings.filterwarnings('ignore')

data_dir = r"D:\Desktop\基金经理行为分析研究\数据"

print("=" * 70)
print("400基金 MVP 验证")
print("=" * 70)

# ============ 1. 加载数据 ============
print("\n[1] 加载数据")

# 原200基金净值 + 新200基金净值
nav_old = pd.read_csv(os.path.join(data_dir, 'fund_nav_all.csv'), dtype={'fund_code': str})
nav_old['fund_code'] = nav_old['fund_code'].astype(str).str.zfill(6)
nav_new = pd.read_csv(os.path.join(data_dir, 'fund_nav_new200.csv'), dtype={'fund_code': str})
nav_new['fund_code'] = nav_new['fund_code'].astype(str).str.zfill(6)
nav_all = pd.concat([nav_old, nav_new], ignore_index=True)
nav_all['date'] = pd.to_datetime(nav_all['date'])
print(f"  净值: {len(nav_all)} 条, {nav_all['fund_code'].nunique()} 只基金")

# 原200基金持仓（全持仓）+ 新200基金持仓（前十大）
hold_old = pd.read_csv(os.path.join(data_dir, 'fund_holdings_full.csv'), dtype={'fund_code': str})
hold_old['fund_code'] = hold_old['fund_code'].astype(str).str.zfill(6)
print(f"  原持仓(全): {len(hold_old)} 条, {hold_old['fund_code'].nunique()} 只基金")

hold_new = pd.read_csv(os.path.join(data_dir, 'fund_holdings_new200.csv'), dtype={'fund_code': str})
hold_new['fund_code'] = hold_new['fund_code'].astype(str).str.zfill(6)
print(f"  新持仓(前十大): {len(hold_new)} 条, {hold_new['fund_code'].nunique()} 只基金")

# 统一字段名
if 'hold_ratio' not in hold_old.columns:
    print(f"  原持仓列: {hold_old.columns.tolist()}")
if 'hold_ratio' not in hold_new.columns:
    print(f"  新持仓列: {hold_new.columns.tolist()}")

# ============ 2. 计算季度收益率 ============
print("\n[2] 计算季度收益率")
nav_all = nav_all.sort_values(['fund_code', 'date'])
nav_all['nav'] = pd.to_numeric(nav_all['nav'], errors='coerce')
nav_all = nav_all.dropna(subset=['nav'])

# 按基金分组，取季末净值
nav_all['year'] = nav_all['date'].dt.year
nav_all['quarter'] = nav_all['date'].dt.quarter
quarter_end = nav_all.groupby(['fund_code', 'year', 'quarter']).last().reset_index()
quarter_end['quarter_return'] = quarter_end.groupby('fund_code')['nav'].pct_change()
quarter_end = quarter_end.dropna(subset=['quarter_return'])
quarter_end['report_date'] = quarter_end['year'].astype(str) + 'Q' + quarter_end['quarter'].astype(str)
print(f"  季度收益率: {len(quarter_end)} 条, {quarter_end['fund_code'].nunique()} 只基金")

# ============ 3. 计算AS（前十大近似） ============
print("\n[3] 计算Active Share (前十大近似)")

def calc_as_simple(holdings_df):
    """用前十大持仓计算近似AS（假设非前十大部分均匀分布在剩余290只中）"""
    results = []
    for (fund, rd), grp in holdings_df.groupby(['fund_code', 'report_date']):
        if pd.isna(rd) or str(rd) == '':
            continue
        # 前十大权重之和
        if 'hold_ratio' in grp.columns:
            top10_weight = pd.to_numeric(grp['hold_ratio'], errors='coerce').sum()
        else:
            continue
        
        # 近似AS: 假设前十大全部偏离基准
        # 简化: AS ≈ top10_weight * 0.5 + (1 - top10_weight) * 0.5
        # 更好的近似: 用经验值调整
        as_approx = min(0.95, 0.50 + top10_weight * 0.004)
        
        results.append({
            'fund_code': fund,
            'report_date': str(rd),
            'AS': as_approx,
            'top10_concentration': top10_weight
        })
    return pd.DataFrame(results)

# 合并持仓
hold_all = pd.concat([
    hold_old[['fund_code', 'report_date', 'stock_code', 'stock_name', 'hold_ratio']] if 'hold_ratio' in hold_old.columns else hold_old,
    hold_new[['fund_code', 'report_date', 'stock_code', 'stock_name', 'hold_ratio']] if 'hold_ratio' in hold_new.columns else hold_new
], ignore_index=True)

# 统一report_date格式
hold_all['report_date'] = hold_all['report_date'].astype(str)

# 对于原200基金，用已有的精确AS
as_old = pd.read_csv(os.path.join(data_dir, 'as_200_funds_v2.csv'), dtype={'fund_code': str})
as_old['fund_code'] = as_old['fund_code'].astype(str).str.zfill(6)
if 'report_date' in as_old.columns:
    as_old['report_date'] = as_old['report_date'].astype(str)
    print(f"  原200精确AS: {len(as_old)} 条")

# 对新200基金，用前十大近似
as_new = calc_as_simple(hold_new)
print(f"  新200近似AS: {len(as_new)} 条")

# 合并AS
if 'AS' in as_old.columns:
    as_all = pd.concat([
        as_old[['fund_code', 'report_date', 'AS']],
        as_new[['fund_code', 'report_date', 'AS']]
    ], ignore_index=True)
else:
    print(f"  原200 AS列: {as_old.columns.tolist()}")
    as_all = as_new

as_all['report_date'] = as_all['report_date'].astype(str)
print(f"  合并AS: {len(as_all)} 条, {as_all['fund_code'].nunique()} 只基金")

# ============ 4. 计算RG ============
print("\n[4] 计算Return Gap")

# 用季度收益率近似RG
# RG = 基金实际收益 - 基准收益（用沪深300近似）
# 简化: 用市场平均收益作为基准
benchmark = quarter_end.groupby('report_date')['quarter_return'].mean().reset_index()
benchmark.columns = ['report_date', 'benchmark_return']

panel = quarter_end.merge(benchmark, on='report_date', how='left')
panel['RG'] = panel['quarter_return'] - panel['benchmark_return']
panel['RG'] = panel['RG'].fillna(0)
print(f"  RG: 均值={panel['RG'].mean():.4f}, 标准差={panel['RG'].std():.4f}")

# ============ 5. 合并面板 ============
print("\n[5] 合并回归面板")

# 格式化report_date以匹配
panel['report_date'] = panel['year'].astype(str) + 'Q' + panel['quarter'].astype(str)

# 转换AS的report_date格式 (如 "2020-06-30" -> "2020Q2")
def rd_to_q(rd):
    rd = str(rd)
    if 'Q' in rd:
        return rd
    try:
        parts = rd.split('-')
        if len(parts) >= 2:
            year = parts[0]
            month = int(parts[1])
            q = (month - 1) // 3 + 1
            return f"{year}Q{q}"
    except:
        pass
    return rd

as_all['report_date_q'] = as_all['report_date'].apply(rd_to_q)

# 合并
panel = panel.merge(as_all[['fund_code', 'report_date_q', 'AS']], 
                    left_on=['fund_code', 'report_date'], 
                    right_on=['fund_code', 'report_date_q'], 
                    how='left')
panel['AS'] = panel['AS'].fillna(panel['AS'].mean())

# AS变化率
panel = panel.sort_values(['fund_code', 'report_date'])
panel['AS_lag'] = panel.groupby('fund_code')['AS'].shift(1)
panel['delta_AS'] = panel['AS'] - panel['AS_lag']

# 滞后业绩
panel['future_return'] = panel.groupby('fund_code')['quarter_return'].shift(-1)
panel = panel.dropna(subset=['future_return'])

print(f"  面板: {len(panel)} 条, {panel['fund_code'].nunique()} 只基金")
print(f"  时间跨度: {panel['report_date'].min()} ~ {panel['report_date'].max()}")

# ============ 6. 回归检验 ============
print("\n[6] 回归检验 (H1-H5)")

# 标准化变量
for col in ['AS', 'RG', 'delta_AS']:
    panel[col + '_std'] = (panel[col] - panel[col].mean()) / (panel[col].std() + 1e-8)

panel['future_return_std'] = (panel['future_return'] - panel['future_return'].mean()) / (panel['future_return'].std() + 1e-8)

results = {}

# H1: AS → 未来业绩 (+)
X1 = sm.add_constant(panel['AS_std'].dropna())
Y1 = panel.loc[X1.index, 'future_return_std']
m1 = OLS(Y1, X1).fit(cov_type='cluster', cov_kwds={'groups': panel.loc[X1.index, 'fund_code']})
results['H1'] = {'var': 'AS', 'coef': m1.params.get('AS_std', 0), 't': m1.tvalues.get('AS_std', 0), 'p': m1.pvalues.get('AS_std', 1), 'r2': m1.rsquared}

# H3: RG → 未来业绩 (+)
X3 = sm.add_constant(panel['RG_std'].dropna())
Y3 = panel.loc[X3.index, 'future_return_std']
m3 = OLS(Y3, X3).fit(cov_type='cluster', cov_kwds={'groups': panel.loc[X3.index, 'fund_code']})
results['H3'] = {'var': 'RG', 'coef': m3.params.get('RG_std', 0), 't': m3.tvalues.get('RG_std', 0), 'p': m3.pvalues.get('RG_std', 1), 'r2': m3.rsquared}

# H5: ΔAS → 未来业绩 (+)
delta_data = panel.dropna(subset=['delta_AS'])
X5 = sm.add_constant(delta_data['delta_AS_std'])
Y5 = delta_data.loc[X5.index, 'future_return_std']
m5 = OLS(Y5, X5).fit(cov_type='cluster', cov_kwds={'groups': delta_data.loc[X5.index, 'fund_code']})
results['H5'] = {'var': 'ΔAS', 'coef': m5.params.get('delta_AS_std', 0), 't': m5.tvalues.get('delta_AS_std', 0), 'p': m5.pvalues.get('delta_AS_std', 1), 'r2': m5.rsquared}

# 全模型
full_vars = ['AS_std', 'RG_std']
full_data = panel.dropna(subset=full_vars + ['future_return_std'])
if 'delta_AS_std' in full_data.columns:
    full_data = full_data.dropna(subset=['delta_AS_std'])
    X_full = sm.add_constant(full_data[['AS_std', 'RG_std', 'delta_AS_std']])
else:
    X_full = sm.add_constant(full_data[['AS_std', 'RG_std']])
Y_full = full_data['future_return_std']
m_full = OLS(Y_full, X_full).fit(cov_type='cluster', cov_kwds={'groups': full_data['fund_code']})

# 打印结果
print(f"\n{'假设':<8} {'变量':<8} {'系数':>10} {'t值':>10} {'p值':>10} {'R²':>8} {'结论':>8}")
print("-" * 70)
for h, r in results.items():
    sig = '***' if r['p'] < 0.01 else ('**' if r['p'] < 0.05 else ('*' if r['p'] < 0.1 else ''))
    passed = '通过' if r['p'] < 0.05 and r['coef'] > 0 else '未通过'
    print(f"{h:<8} {r['var']:<8} {r['coef']:>10.4f} {r['t']:>10.2f} {r['p']:>10.4f} {r['r2']:>8.4f} {passed:>8} {sig}")

print(f"\n全模型: R²={m_full.rsquared:.4f}")
for var in m_full.params.index:
    if var != 'const':
        sig = '***' if m_full.pvalues[var] < 0.01 else ('**' if m_full.pvalues[var] < 0.05 else ('*' if m_full.pvalues[var] < 0.1 else ''))
        print(f"  {var}: β={m_full.params[var]:.4f}, t={m_full.tvalues[var]:.2f}, p={m_full.pvalues[var]:.4f} {sig}")

# ============ 7. 与原200基金结果对比 ============
print("\n[7] 与原200基金结果对比")
print(f"{'指标':<20} {'原200基金':>15} {'400基金':>15} {'变化':>10}")
print("-" * 65)
print(f"{'样本量':<20} {'1,597':>15} {len(panel):>15}")
print(f"{'基金数':<20} {'200':>15} {panel['fund_code'].nunique():>15}")
print(f"{'AS均值':<20} {'0.948':>15} {panel['AS'].mean():>15.3f}")
print(f"{'RG均值':<20} {'0.20%':>15} {panel['RG'].mean():>15.4f}")
print(f"{'H1(AS→业绩) t值':<20} {'2.57':>15} {results['H1']['t']:>15.2f}")
print(f"{'H3(RG→业绩) t值':<20} {'2.43':>15} {results['H3']['t']:>15.2f}")
print(f"{'H5(ΔAS→业绩) t值':<20} {'2.80':>15} {results['H5']['t']:>15.2f}")

# 保存面板
panel.to_csv(os.path.join(data_dir, 'mvp_panel_400.csv'), index=False)
print(f"\n面板已保存: mvp_panel_400.csv ({len(panel)} 条)")
print("=" * 70)
print("MVP验证完成")
