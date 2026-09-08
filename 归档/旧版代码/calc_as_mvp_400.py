"""从已下载的全持仓数据计算AS并做MVP回归
跳过下载步骤，直接用已有数据
"""
import os
import pandas as pd
import numpy as np
import statsmodels.api as sm
from statsmodels.regression.linear_model import OLS
import warnings
warnings.filterwarnings('ignore')

data_dir = r"D:\Desktop\基金经理行为分析研究\数据"

# ============ Step 1: 加载全持仓数据 ============
print("=" * 70)
print("Step 1: 加载400基金全持仓数据")
print("=" * 70)

# 原200基金
hold_old = pd.read_csv(os.path.join(data_dir, 'fund_holdings_full.csv'), dtype={'fund_code': str})
hold_old['fund_code'] = hold_old['fund_code'].astype(str).str.zfill(6)
print(f"原200基金: {len(hold_old)} 条, {hold_old['fund_code'].nunique()} 只")

# 新200基金
hold_new = pd.read_csv(os.path.join(data_dir, 'fund_holdings_new200_full.csv'), dtype={'fund_code': str})
hold_new['fund_code'] = hold_new['fund_code'].astype(str).str.zfill(6)
print(f"新200基金: {len(hold_new)} 条, {hold_new['fund_code'].nunique()} 只")

# 统一列
cols = ['fund_code', 'report_date', 'stock_code', 'stock_name', 'hold_ratio']
hold_old_c = hold_old[[c for c in cols if c in hold_old.columns]].copy()
hold_new_c = hold_new[[c for c in cols if c in hold_new.columns]].copy()
hold_all = pd.concat([hold_old_c, hold_new_c], ignore_index=True)
print(f"合并: {len(hold_all)} 条, {hold_all['fund_code'].nunique()} 只基金")

# ============ Step 2: 计算AS ============
print("\n" + "=" * 70)
print("Step 2: 计算Active Share (全持仓, 等权沪深300基准)")
print("=" * 70)

N_bench = 300
bench_weight = 1.0 / N_bench

results = []
for (fund, rd), grp in hold_all.groupby(['fund_code', 'report_date']):
    if pd.isna(rd) or str(rd) == '':
        continue
    
    # 兼容 "8.84%" 和 5.8 两种格式
    hr = grp['hold_ratio'].astype(str).str.replace('%', '').str.strip()
    fw = pd.to_numeric(hr, errors='coerce').dropna() / 100.0
    total = fw.sum()
    if total == 0:
        continue
    fw = fw / total  # 标准化
    
    n = len(fw)
    # AS = 1/2 * [sum|w_fund - w_bench| + (300-n)*w_bench]
    fund_part = sum(abs(w - bench_weight) for w in fw)
    bench_not_held = max(0, N_bench - n) * bench_weight
    as_val = min(1.0, 0.5 * (fund_part + bench_not_held))
    
    results.append({
        'fund_code': fund,
        'report_date': str(rd),
        'AS': as_val,
        'n_stocks': n
    })

as_df = pd.DataFrame(results)
print(f"AS计算: {len(as_df)} 条, {as_df['fund_code'].nunique()} 只基金")
print(f"AS均值: {as_df['AS'].mean():.4f}, 标准差: {as_df['AS'].std():.4f}")
print(f"AS范围: [{as_df['AS'].min():.4f}, {as_df['AS'].max():.4f}]")
print(f"持仓股票数均值: {as_df['n_stocks'].mean():.1f}")

# ============ Step 3: 计算季度收益率和RG ============
print("\n" + "=" * 70)
print("Step 3: 计算季度收益率和Return Gap")
print("=" * 70)

nav_old = pd.read_csv(os.path.join(data_dir, 'fund_nav_all.csv'), dtype={'fund_code': str})
nav_old['fund_code'] = nav_old['fund_code'].astype(str).str.zfill(6)
nav_new = pd.read_csv(os.path.join(data_dir, 'fund_nav_new200.csv'), dtype={'fund_code': str})
nav_new['fund_code'] = nav_new['fund_code'].astype(str).str.zfill(6)
nav_all = pd.concat([nav_old, nav_new], ignore_index=True)
nav_all['date'] = pd.to_datetime(nav_all['date'])
nav_all['nav'] = pd.to_numeric(nav_all['nav'], errors='coerce')
nav_all = nav_all.dropna(subset=['nav']).sort_values(['fund_code', 'date'])

nav_all['year'] = nav_all['date'].dt.year
nav_all['quarter'] = nav_all['date'].dt.quarter
qend = nav_all.groupby(['fund_code', 'year', 'quarter']).last().reset_index()
qend['quarter_return'] = qend.groupby('fund_code')['nav'].pct_change()
qend = qend.dropna(subset=['quarter_return'])
qend['report_date'] = qend['year'].astype(str) + 'Q' + qend['quarter'].astype(str)

# 基准: 全基金等权平均
bench = qend.groupby('report_date')['quarter_return'].mean().reset_index()
bench.columns = ['report_date', 'bench_return']
panel = qend.merge(bench, on='report_date', how='left')
panel['RG'] = panel['quarter_return'] - panel['bench_return']
panel['RG'] = panel['RG'].fillna(0)

print(f"季度收益: {len(panel)} 条, {panel['fund_code'].nunique()} 只基金")

# ============ Step 4: 合并面板 ============
print("\n" + "=" * 70)
print("Step 4: 合并回归面板")
print("=" * 70)

def rd_to_q(rd):
    rd = str(rd)
    if 'Q' in rd:
        return rd
    try:
        parts = rd.split('-')
        if len(parts) >= 2:
            y = parts[0]
            m = int(parts[1])
            return f"{y}Q{(m-1)//3+1}"
    except:
        pass
    return rd

as_df['rq'] = as_df['report_date'].apply(rd_to_q)
panel = panel.merge(as_df[['fund_code', 'rq', 'AS']], 
                    left_on=['fund_code', 'report_date'], 
                    right_on=['fund_code', 'rq'], how='left')
panel['AS'] = panel['AS'].fillna(panel['AS'].mean())

# AS变化率
panel = panel.sort_values(['fund_code', 'report_date'])
panel['AS_lag'] = panel.groupby('fund_code')['AS'].shift(1)
panel['delta_AS'] = panel['AS'] - panel['AS_lag']

# 滞后业绩
panel['future_return'] = panel.groupby('fund_code')['quarter_return'].shift(-1)
panel = panel.dropna(subset=['future_return'])

print(f"面板: {len(panel)} 条, {panel['fund_code'].nunique()} 只基金")
print(f"时间: {panel['report_date'].min()} ~ {panel['report_date'].max()}")
print(f"AS均值: {panel['AS'].mean():.4f}")
print(f"RG均值: {panel['RG'].mean():.6f}")

# ============ Step 5: 回归检验 ============
print("\n" + "=" * 70)
print("Step 5: 回归检验 (400基金, 全持仓统一精度)")
print("=" * 70)

for col in ['AS', 'RG', 'delta_AS']:
    panel[col + '_std'] = (panel[col] - panel[col].mean()) / (panel[col].std() + 1e-8)
panel['future_return_std'] = (panel['future_return'] - panel['future_return'].mean()) / (panel['future_return'].std() + 1e-8)

results = {}

# H1: AS → 未来业绩
d1 = panel.dropna(subset=['AS_std', 'future_return_std'])
X1 = sm.add_constant(d1['AS_std'])
m1 = OLS(d1['future_return_std'], X1).fit(cov_type='cluster', cov_kwds={'groups': d1['fund_code']})
results['H1'] = (m1.params['AS_std'], m1.tvalues['AS_std'], m1.pvalues['AS_std'], m1.rsquared)

# H3: RG → 未来业绩
d3 = panel.dropna(subset=['RG_std', 'future_return_std'])
X3 = sm.add_constant(d3['RG_std'])
m3 = OLS(d3['future_return_std'], X3).fit(cov_type='cluster', cov_kwds={'groups': d3['fund_code']})
results['H3'] = (m3.params['RG_std'], m3.tvalues['RG_std'], m3.pvalues['RG_std'], m3.rsquared)

# H5: ΔAS → 未来业绩
d5 = panel.dropna(subset=['delta_AS_std', 'future_return_std'])
X5 = sm.add_constant(d5['delta_AS_std'])
m5 = OLS(d5['future_return_std'], X5).fit(cov_type='cluster', cov_kwds={'groups': d5['fund_code']})
results['H5'] = (m5.params['delta_AS_std'], m5.tvalues['delta_AS_std'], m5.pvalues['delta_AS_std'], m5.rsquared)

# 全模型
dfull = panel.dropna(subset=['AS_std', 'RG_std', 'delta_AS_std', 'future_return_std'])
X_full = sm.add_constant(dfull[['AS_std', 'RG_std', 'delta_AS_std']])
m_full = OLS(dfull['future_return_std'], X_full).fit(cov_type='cluster', cov_kwds={'groups': dfull['fund_code']})

# 打印结果
print(f"\n{'假设':<6} {'变量':<8} {'系数':>10} {'t值':>10} {'p值':>10} {'R²':>8} {'结论':>6}")
print("-" * 65)
for h, (coef, t, p, r2) in results.items():
    sig = '***' if p < 0.01 else ('**' if p < 0.05 else ('*' if p < 0.1 else ''))
    passed = '通过' if p < 0.05 else '未通过'
    var_name = {'H1': 'AS', 'H3': 'RG', 'H5': 'ΔAS'}[h]
    print(f"{h:<6} {var_name:<8} {coef:>10.4f} {t:>10.2f} {p:>10.4f} {r2:>8.4f} {passed:>6} {sig}")

print(f"\n全模型 R²={m_full.rsquared:.4f}")
for v in m_full.params.index:
    if v != 'const':
        p = m_full.pvalues[v]
        sig = '***' if p < 0.01 else ('**' if p < 0.05 else ('*' if p < 0.1 else ''))
        print(f"  {v}: β={m_full.params[v]:.4f}, t={m_full.tvalues[v]:.2f}, p={p:.4f} {sig}")

# 对比表
print(f"\n{'='*70}")
print("四轮MVP对比")
print(f"{'='*70}")
print(f"{'指标':<25} {'V1模拟':>10} {'V2原200':>10} {'V3 400近似':>12} {'V4 400全持仓':>14}")
print("-" * 75)
print(f"{'样本量':<25} {'2,400':>10} {'1,597':>10} {'9,581':>12} {len(panel):>14}")
print(f"{'基金数':<25} {'200':>10} {'200':>10} {'400':>12} {panel['fund_code'].nunique():>14}")
print(f"{'AS精度':<25} {'模拟':>10} {'全持仓':>10} {'前十大':>12} {'全持仓':>14}")
print(f"{'AS均值':<25} {'0.95':>10} {'0.948':>10} {'0.705':>12} {panel['AS'].mean():>14.4f}")
print(f"{'H1(AS→业绩) t':<25} {'N/A':>10} {'2.57**':>10} {'6.34***':>12} {results['H1'][1]:>14.2f}")
print(f"{'H3(RG→业绩) t':<25} {'N/A':>10} {'2.43**':>10} {'-3.67***':>12} {results['H3'][1]:>14.2f}")
print(f"{'H5(ΔAS→业绩) t':<25} {'N/A':>10} {'2.80***':>10} {'-9.10***':>12} {results['H5'][1]:>14.2f}")
print(f"{'全模型R²':<25} {'0.365':>10} {'0.024':>10} {'0.029':>12} {m_full.rsquared:>14.4f}")

# 保存
panel.to_csv(os.path.join(data_dir, 'mvp_panel_400_full.csv'), index=False)
print(f"\n面板已保存: mvp_panel_400_full.csv ({len(panel)} 条)")
