"""快速保存AKShare持仓数据并运行400基金MVP"""
import akshare as ak
import pandas as pd
import numpy as np
import os
import re
import time
import statsmodels.api as sm
from statsmodels.regression.linear_model import OLS
import warnings
warnings.filterwarnings('ignore')

data_dir = r"D:\Desktop\基金经理行为分析研究\数据"

# ============ 1. 快速下载新200基金前十大持仓 ============
print("[1] 下载新200基金前十大持仓 (AKShare)")
fund_list = pd.read_csv(os.path.join(data_dir, 'fund_list_new200.csv'), dtype={'code': str})
fund_list['code'] = fund_list['code'].astype(str).str.zfill(6)
new_codes = fund_list['code'].tolist()

all_holdings = []
q_month = {'1': '03-31', '2': '06-30', '3': '09-30', '4': '12-31'}

for i, code in enumerate(new_codes):
    for year in ['2020', '2021', '2022', '2023', '2024', '2025']:
        try:
            df = ak.fund_portfolio_hold_em(symbol=code, date=year)
            if df is not None and len(df) > 0:
                for _, row in df.iterrows():
                    quarter_str = str(row['季度'])
                    m = re.search(r'(\d{4})年(\d)季度', quarter_str)
                    if m:
                        q = f"{m.group(1)}Q{m.group(2)}"
                        rd = f"{m.group(1)}-{q_month.get(m.group(2), '')}"
                    else:
                        q = quarter_str
                        rd = ''
                    
                    hr = row.get('占净值比例', '')
                    try:
                        hr = float(hr)
                    except:
                        hr = np.nan
                    
                    all_holdings.append({
                        'fund_code': code,
                        'report_date': rd,
                        'quarter': q,
                        'stock_code': str(row.get('股票代码', '')),
                        'stock_name': str(row.get('股票名称', '')),
                        'hold_ratio': hr,
                    })
        except:
            pass
        time.sleep(0.12)
    if (i + 1) % 50 == 0:
        print(f"  {i+1}/{len(new_codes)}, 累计 {len(all_holdings)} 条")

hold_new = pd.DataFrame(all_holdings)
hold_new.to_csv(os.path.join(data_dir, 'fund_holdings_new200.csv'), index=False)
print(f"  完成: {len(hold_new)} 条, {hold_new['fund_code'].nunique()} 只基金")

# ============ 2. 加载全部数据 ============
print("\n[2] 加载数据")
nav_old = pd.read_csv(os.path.join(data_dir, 'fund_nav_all.csv'), dtype={'fund_code': str})
nav_old['fund_code'] = nav_old['fund_code'].astype(str).str.zfill(6)
nav_new = pd.read_csv(os.path.join(data_dir, 'fund_nav_new200.csv'), dtype={'fund_code': str})
nav_new['fund_code'] = nav_new['fund_code'].astype(str).str.zfill(6)
nav_all = pd.concat([nav_old, nav_new], ignore_index=True)
nav_all['date'] = pd.to_datetime(nav_all['date'])
nav_all['nav'] = pd.to_numeric(nav_all['nav'], errors='coerce')
nav_all = nav_all.dropna(subset=['nav'])
print(f"  净值: {len(nav_all)} 条, {nav_all['fund_code'].nunique()} 只基金")

# 原200精确AS
as_old = pd.read_csv(os.path.join(data_dir, 'as_200_funds_v2.csv'), dtype={'fund_code': str})
as_old['fund_code'] = as_old['fund_code'].astype(str).str.zfill(6)
if 'report_date' in as_old.columns:
    as_old['report_date'] = as_old['report_date'].astype(str)
else:
    print(f"  原200 AS列: {as_old.columns.tolist()}")
print(f"  原200 AS: {len(as_old)} 条")

# ============ 3. 计算新200基金近似AS ============
print("\n[3] 计算新200基金近似AS (前十大)")

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

# 计算前十大集中度 → 近似AS
as_new_list = []
for (fund, q), grp in hold_new.groupby(['fund_code', 'quarter']):
    if pd.isna(q) or str(q) == '':
        continue
    top10_weight = grp['hold_ratio'].sum()
    as_approx = min(0.95, 0.50 + top10_weight * 0.004)
    as_new_list.append({
        'fund_code': fund,
        'report_date': str(q),
        'AS': as_approx
    })
as_new_df = pd.DataFrame(as_new_list)
print(f"  新200 AS: {len(as_new_df)} 条")

# 合并AS
as_col = 'AS' if 'AS' in as_old.columns else [c for c in as_old.columns if 'as' in c.lower() or 'AS' in c][0]
as_all = pd.concat([
    as_old[['fund_code', 'report_date', as_col]].rename(columns={as_col: 'AS'}),
    as_new_df
], ignore_index=True)
as_all['report_date'] = as_all['report_date'].astype(str)
print(f"  合并AS: {len(as_all)} 条, {as_all['fund_code'].nunique()} 只基金")

# ============ 4. 计算季度收益率和RG ============
print("\n[4] 计算季度收益率和RG")
nav_all = nav_all.sort_values(['fund_code', 'date'])
nav_all['year'] = nav_all['date'].dt.year
nav_all['quarter'] = nav_all['date'].dt.quarter
quarter_end = nav_all.groupby(['fund_code', 'year', 'quarter']).last().reset_index()
quarter_end['quarter_return'] = quarter_end.groupby('fund_code')['nav'].pct_change()
quarter_end = quarter_end.dropna(subset=['quarter_return'])
quarter_end['report_date'] = quarter_end['year'].astype(str) + 'Q' + quarter_end['quarter'].astype(str)

# RG = 基金收益 - 同期市场平均
benchmark = quarter_end.groupby('report_date')['quarter_return'].mean().reset_index()
benchmark.columns = ['report_date', 'benchmark_return']
panel = quarter_end.merge(benchmark, on='report_date', how='left')
panel['RG'] = panel['quarter_return'] - panel['benchmark_return']
panel['RG'] = panel['RG'].fillna(0)

# 合并AS
panel = panel.merge(as_all[['fund_code', 'report_date', 'AS']], on=['fund_code', 'report_date'], how='left')
panel['AS'] = panel['AS'].fillna(panel['AS'].mean())

# AS变化率
panel = panel.sort_values(['fund_code', 'report_date'])
panel['AS_lag'] = panel.groupby('fund_code')['AS'].shift(1)
panel['delta_AS'] = panel['AS'] - panel['AS_lag']

# 滞后业绩
panel['future_return'] = panel.groupby('fund_code')['quarter_return'].shift(-1)
panel = panel.dropna(subset=['future_return'])

print(f"  面板: {len(panel)} 条, {panel['fund_code'].nunique()} 只基金")
print(f"  时间: {panel['report_date'].min()} ~ {panel['report_date'].max()}")
print(f"  AS均值: {panel['AS'].mean():.3f}")
print(f"  RG均值: {panel['RG'].mean():.4f}")

# ============ 5. 回归检验 ============
print("\n[5] 回归检验")
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

# 打印
print(f"\n{'假设':<6} {'变量':<8} {'系数':>10} {'t值':>10} {'p值':>10} {'R²':>8} {'结论':>6}")
print("-" * 65)
for h, (coef, t, p, r2) in results.items():
    sig = '***' if p < 0.01 else ('**' if p < 0.05 else ('*' if p < 0.1 else ''))
    passed = '通过' if p < 0.05 else '未通过'
    print(f"{h:<6} {'':>8} {coef:>10.4f} {t:>10.2f} {p:>10.4f} {r2:>8.4f} {passed:>6} {sig}")

print(f"\n全模型 R²={m_full.rsquared:.4f}")
for v in m_full.params.index:
    if v != 'const':
        p = m_full.pvalues[v]
        sig = '***' if p < 0.01 else ('**' if p < 0.05 else ('*' if p < 0.1 else ''))
        print(f"  {v}: β={m_full.params[v]:.4f}, t={m_full.tvalues[v]:.2f}, p={p:.4f} {sig}")

# 对比
print(f"\n{'='*65}")
print("与原200基金对比")
print(f"{'指标':<25} {'原200':>12} {'400基金':>12}")
print("-" * 55)
print(f"{'样本量':<25} {'1,597':>12} {len(panel):>12}")
print(f"{'基金数':<25} {'200':>12} {panel['fund_code'].nunique():>12}")
print(f"{'AS均值':<25} {'0.948':>12} {panel['AS'].mean():>12.3f}")
print(f"{'RG均值':<25} {'0.20%':>12} {panel['RG'].mean():>12.4f}")
print(f"{'H1(AS→业绩) t':<25} {'2.57':>12} {results['H1'][1]:>12.2f}")
print(f"{'H3(RG→业绩) t':<25} {'2.43':>12} {results['H3'][1]:>12.2f}")
print(f"{'H5(ΔAS→业绩) t':<25} {'2.80':>12} {results['H5'][1]:>12.2f}")
print(f"{'全模型 R²':<25} {'0.024':>12} {m_full.rsquared:>12.4f}")

panel.to_csv(os.path.join(data_dir, 'mvp_panel_400.csv'), index=False)
print(f"\n面板已保存: mvp_panel_400.csv")
