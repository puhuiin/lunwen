#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
200基金真实数据：AS/RG计算 + MVP回归验证
- AS: 使用全持仓数据（有全持仓的用全持仓，没有的用前十大近似）
- RG: 使用净值数据计算Return Gap
- MVP: 用真实指标复现H1-H5回归
"""
import pandas as pd
import numpy as np
import os
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

DATA_DIR = r'D:\Desktop\基金经理行为分析研究\数据'
OUTPUT_DIR = r'D:\Desktop\基金经理行为分析研究\数据'

# ============================================================
# 1. 加载数据
# ============================================================
print("=" * 60)
print("1. 加载数据")
print("=" * 60)

# 基金列表
fund_list = pd.read_csv(os.path.join(DATA_DIR, 'fund_list_200.csv'))
print(f"基金列表: {len(fund_list)} 只")

# 净值数据
nav_df = pd.read_csv(os.path.join(DATA_DIR, 'fund_nav_all.csv'))
nav_df['date'] = pd.to_datetime(nav_df['date'])
print(f"净值数据: {len(nav_df)} 条, {nav_df['fund_code'].nunique()} 只基金")

# 前十大持仓
top10_df = pd.read_csv(os.path.join(DATA_DIR, 'fund_holdings_top10.csv'))
# 解析中文格式: '2020年1季度股票投资明细' -> 季度末日期
import re
def parse_report_period(s):
    m = re.match(r'(\d{4})年(\d)季度', str(s))
    if m:
        year, q = int(m.group(1)), int(m.group(2))
        month = {1: 3, 2: 6, 3: 9, 4: 12}[q]
        return pd.Timestamp(year=year, month=month, day=30)
    return pd.NaT

top10_df['report_period'] = top10_df['report_period'].apply(parse_report_period)
print(f"前十大持仓: {len(top10_df)} 条, {top10_df['fund_code'].nunique()} 只基金")

# 全持仓
full_df = pd.read_csv(os.path.join(DATA_DIR, 'fund_holdings_full.csv'))
print(f"全持仓: {len(full_df)} 条, {full_df['fund_code'].nunique()} 只基金")

# 指数成分股
hs300 = pd.read_csv(os.path.join(DATA_DIR, 'index_000300_constituents.csv'))
zz500 = pd.read_csv(os.path.join(DATA_DIR, 'index_000905_constituents.csv'))
print(f"沪深300成分股: {len(hs300)} 只, 中证500成分股: {len(zz500)} 只")

# ============================================================
# 2. 计算Active Share (AS)
# ============================================================
print("\n" + "=" * 60)
print("2. 计算Active Share (AS)")
print("=" * 60)

def parse_hold_ratio(val):
    """解析持仓比例，支持 '8.84%' 和 8.84 两种格式"""
    if isinstance(val, str):
        val = val.strip().replace('%', '')
        try:
            return float(val)
        except:
            return np.nan
    return float(val) if pd.notna(val) else np.nan

def normalize_stock_code(code):
    """统一股票代码为6位字符串"""
    return str(code).strip().zfill(6)

def calc_active_share(holdings_df, benchmark_stocks):
    """
    AS = 0.5 * sum(|w_fund_i - w_bench_i|)
    基准: 沪深300等权（简化）
    """
    bench_codes = set(benchmark_stocks['stock_code'].apply(normalize_stock_code))
    bench_weight = 1.0 / len(bench_codes) if len(bench_codes) > 0 else 0
    
    holdings_df = holdings_df.copy()
    holdings_df['hold_ratio_num'] = holdings_df['hold_ratio'].apply(parse_hold_ratio)
    holdings_df = holdings_df.dropna(subset=['hold_ratio_num'])
    
    total_weight = holdings_df['hold_ratio_num'].sum()
    if total_weight <= 0:
        return np.nan
    
    holdings_df['weight'] = holdings_df['hold_ratio_num'] / total_weight
    holdings_df['stock_norm'] = holdings_df['stock_code'].apply(normalize_stock_code)
    
    # 向量化计算
    in_bench = holdings_df['stock_norm'].isin(bench_codes)
    w_fund = holdings_df['weight']
    w_bench = np.where(in_bench, bench_weight, 0.0)
    as_value = (w_fund - w_bench).abs().sum()
    
    # 基准中未持有的部分
    covered = holdings_df[in_bench]['weight'].sum() / total_weight  # 已覆盖的基金权重
    # 基准中未出现在基金持仓的成分股权重
    held_bench_stocks = set(holdings_df[in_bench]['stock_norm'])
    uncovered_bench_count = len(bench_codes - held_bench_stocks)
    uncovered_bench_weight = uncovered_bench_count * bench_weight
    as_value += uncovered_bench_weight
    
    return as_value / 2.0

# 合并持仓数据：优先用全持仓，没有的用前十大
all_holdings = []

# 先处理全持仓
for fund_code, group in full_df.groupby('fund_code'):
    for report_date, rg in group.groupby('report_date'):
        holdings = rg[['stock_code', 'stock_name', 'hold_ratio']].dropna(subset=['hold_ratio'])
        if len(holdings) > 0:
            as_val = calc_active_share(holdings, hs300)
            all_holdings.append({
                'fund_code': fund_code,
                'report_date': report_date,
                'as_value': as_val,
                'source': 'full',
                'num_holdings': len(holdings)
            })

# 再处理只有前十大的基金（跳过已有全持仓的）
full_funds = set(full_df['fund_code'].unique())
for fund_code, group in top10_df.groupby('fund_code'):
    if fund_code in full_funds:
        continue
    for report_period, rg in group.groupby('report_period'):
        holdings = rg[['stock_code', 'stock_name', 'hold_ratio']].dropna(subset=['hold_ratio'])
        if len(holdings) > 0:
            as_val = calc_active_share(holdings, hs300)
            all_holdings.append({
                'fund_code': fund_code,
                'report_date': report_period,
                'as_value': as_val,
                'source': 'top10',
                'num_holdings': len(holdings)
            })

as_df = pd.DataFrame(all_holdings)
as_df = as_df.dropna(subset=['as_value'])
as_df['report_quarter'] = pd.to_datetime(as_df['report_date']).dt.to_period('Q')

print(f"AS计算结果: {len(as_df)} 条记录, {as_df['fund_code'].nunique()} 只基金")
print(f"  数据来源: full={len(as_df[as_df['source']=='full'])}, top10={len(as_df[as_df['source']=='top10'])}")
print(f"  AS均值: {as_df['as_value'].mean():.4f}")
print(f"  AS中位数: {as_df['as_value'].median():.4f}")
print(f"  AS标准差: {as_df['as_value'].std():.4f}")
print(f"  AS范围: [{as_df['as_value'].min():.4f}, {as_df['as_value'].max():.4f}]")

as_df.to_csv(os.path.join(OUTPUT_DIR, 'as_200_funds.csv'), index=False)
print("  已保存: as_200_funds.csv")

# ============================================================
# 3. 计算Return Gap (RG)
# ============================================================
print("\n" + "=" * 60)
print("3. 计算Return Gap (RG)")
print("=" * 60)

def calc_return_gap(nav_group, lookback_months=12):
    """
    RG_t = R_hold_t - R_trade_t
    R_hold_t: 过去12个月持有不变组合的回报（用滞后一期持仓的回报）
    R_trade_t: 基金实际回报
    
    简化实现: 用过去12个月平均月回报与当月回报之差作为RG近似
    RG_t = mean(R_{t-12:t-1}) - R_t
    """
    nav_group = nav_group.sort_values('date').reset_index(drop=True)
    nav_group['nav'] = pd.to_numeric(nav_group['nav'], errors='coerce')
    nav_group = nav_group.dropna(subset=['nav'])
    
    if len(nav_group) < 13:
        return []
    
    # 计算月度回报
    nav_group['date'] = pd.to_datetime(nav_group['date'])
    nav_group = nav_group.set_index('date')
    monthly_nav = nav_group['nav'].resample('ME').last().dropna()
    monthly_returns = monthly_nav.pct_change().dropna()
    
    results = []
    for i in range(lookback_months, len(monthly_returns)):
        past_returns = monthly_returns.iloc[i-lookback_months:i]
        current_return = monthly_returns.iloc[i]
        
        # RG = 持有期平均回报 - 当期实际回报
        rg = past_returns.mean() - current_return
        
        results.append({
            'fund_code': nav_group['fund_code'].iloc[0],
            'date': monthly_returns.index[i],
            'monthly_return': current_return,
            'past_avg_return': past_returns.mean(),
            'rg_value': rg
        })
    
    return results

# 计算所有基金的RG
rg_results = []
fund_codes = nav_df['fund_code'].unique()
for i, fund_code in enumerate(fund_codes):
    fund_nav = nav_df[nav_df['fund_code'] == fund_code]
    rg_data = calc_return_gap(fund_nav)
    rg_results.extend(rg_data)
    if (i + 1) % 50 == 0:
        print(f"  已处理 {i+1}/{len(fund_codes)} 只基金")

rg_df = pd.DataFrame(rg_results)
print(f"\nRG计算结果: {len(rg_df)} 条记录, {rg_df['fund_code'].nunique()} 只基金")
if len(rg_df) > 0:
    print(f"  RG均值: {rg_df['rg_value'].mean():.6f}")
    print(f"  RG中位数: {rg_df['rg_value'].median():.6f}")
    print(f"  RG标准差: {rg_df['rg_value'].std():.6f}")
    rg_df['report_quarter'] = rg_df['date'].dt.to_period('Q')
    rg_df.to_csv(os.path.join(OUTPUT_DIR, 'rg_200_funds.csv'), index=False)
    print("  已保存: rg_200_funds.csv")

# ============================================================
# 4. 构建MVP回归面板
# ============================================================
print("\n" + "=" * 60)
print("4. 构建MVP回归面板数据")
print("=" * 60)

# 按季度聚合AS和RG
as_quarterly = as_df.groupby(['fund_code', 'report_quarter'])['as_value'].mean().reset_index()
rg_quarterly = rg_df.groupby(['fund_code', 'report_quarter'])['rg_value'].mean().reset_index()

# 计算基金季度回报
nav_df['quarter'] = nav_df['date'].dt.to_period('Q')
quarterly_returns = nav_df.groupby(['fund_code', 'quarter']).apply(
    lambda x: (x.sort_values('date')['nav'].iloc[-1] / x.sort_values('date')['nav'].iloc[0] - 1) 
    if len(x) > 1 else np.nan
).reset_index(name='quarter_return')
quarterly_returns.rename(columns={'quarter': 'report_quarter'}, inplace=True)

# 合并面板
panel = as_quarterly.merge(rg_quarterly, on=['fund_code', 'report_quarter'], how='inner')
panel = panel.merge(quarterly_returns, on=['fund_code', 'report_quarter'], how='left')

# 计算下期回报（业绩预测变量）
panel = panel.sort_values(['fund_code', 'report_quarter'])
panel['next_quarter_return'] = panel.groupby('fund_code')['quarter_return'].shift(-1)
panel['next_quarter_excess'] = panel['next_quarter_return']  # 简化：无风险利率设为0

# 计算RG波动率（RG的过去4期标准差，作为交易行为稳定性指标）
panel['rg_volatility'] = panel.groupby('fund_code')['rg_value'].rolling(4, min_periods=2).std().reset_index(level=0, drop=True)

# 计算AS变化率（持仓偏离的变化，作为主动调仓指标）
panel['as_change'] = panel.groupby('fund_code')['as_value'].pct_change()
panel['as_change'] = panel['as_change'].replace([np.inf, -np.inf], np.nan)

# 填充缺失值
panel['rg_volatility'] = panel['rg_volatility'].fillna(panel['rg_volatility'].median())
panel['as_change'] = panel['as_change'].fillna(0)

print(f"面板数据: {len(panel)} 条, {panel['fund_code'].nunique()} 只基金")
print(f"  季度范围: {panel['report_quarter'].min()} ~ {panel['report_quarter'].max()}")
print(panel.describe())

panel.to_csv(os.path.join(OUTPUT_DIR, 'mvp_panel_200.csv'), index=False)
print("  已保存: mvp_panel_200.csv")

# ============================================================
# 5. MVP回归验证 H1-H5
# ============================================================
print("\n" + "=" * 60)
print("5. MVP回归验证 (200基金真实数据)")
print("=" * 60)

import statsmodels.api as sm
from statsmodels.regression.linear_model import OLS

regression_data = panel.dropna(subset=['next_quarter_return']).copy()
print(f"回归样本: {len(regression_data)} 条, {regression_data['fund_code'].nunique()} 只基金")

# 标准化自变量
for col in ['as_value', 'rg_value', 'rg_volatility', 'as_change']:
    mean_val = regression_data[col].mean()
    std_val = regression_data[col].std()
    if std_val > 0:
        regression_data[col + '_z'] = (regression_data[col] - mean_val) / std_val
    else:
        regression_data[col + '_z'] = 0

# H1: AS正向预测未来超额收益
print("\n--- H1: Active Share正向预测未来收益 ---")
X1 = sm.add_constant(regression_data[['as_value_z']])
m1 = OLS(regression_data['next_quarter_return'], X1).fit(cov_type='cluster', 
          cov_kwds={'groups': regression_data['fund_code']})
print(f"  AS系数: {m1.params['as_value_z']:.4f} (t={m1.tvalues['as_value_z']:.2f})")
print(f"  R²: {m1.rsquared:.4f}")
print(f"  H1{'通过' if m1.params['as_value_z'] > 0 and m1.pvalues['as_value_z'] < 0.1 else '未通过'}")

# H2: RG负向预测未来收益
print("\n--- H2: Return Gap负向预测未来收益 ---")
X2 = sm.add_constant(regression_data[['rg_value_z']])
m2 = OLS(regression_data['next_quarter_return'], X2).fit(cov_type='cluster',
          cov_kwds={'groups': regression_data['fund_code']})
print(f"  RG系数: {m2.params['rg_value_z']:.4f} (t={m2.tvalues['rg_value_z']:.2f})")
print(f"  R²: {m2.rsquared:.4f}")
print(f"  H2{'通过' if m2.params['rg_value_z'] < 0 and m2.pvalues['rg_value_z'] < 0.1 else '未通过'}")

# H3: AS与RG交互效应
print("\n--- H3: AS×RG交互效应 ---")
regression_data['as_rg_inter'] = regression_data['as_value_z'] * regression_data['rg_value_z']
X3 = sm.add_constant(regression_data[['as_value_z', 'rg_value_z', 'as_rg_inter']])
m3 = OLS(regression_data['next_quarter_return'], X3).fit(cov_type='cluster',
          cov_kwds={'groups': regression_data['fund_code']})
print(f"  交互项系数: {m3.params['as_rg_inter']:.4f} (t={m3.tvalues['as_rg_inter']:.2f})")
print(f"  R²: {m3.rsquared:.4f}")
print(f"  H3{'通过' if m3.pvalues['as_rg_inter'] < 0.1 else '未通过'}")

# H4: RG波动率预测收益稳定性
print("\n--- H4: RG波动率预测收益稳定性 ---")
regression_data['abs_excess'] = regression_data['next_quarter_return'].abs()
X4 = sm.add_constant(regression_data[['rg_volatility_z']])
m4 = OLS(regression_data['abs_excess'], X4).fit(cov_type='cluster',
          cov_kwds={'groups': regression_data['fund_code']})
print(f"  RG波动率系数: {m4.params['rg_volatility_z']:.4f} (t={m4.tvalues['rg_volatility_z']:.2f})")
print(f"  R²: {m4.rsquared:.4f}")
print(f"  H4{'通过' if m4.params['rg_volatility_z'] > 0 and m4.pvalues['rg_volatility_z'] < 0.1 else '未通过'}")

# H5: 全模型
print("\n--- H5: 全模型 ---")
X5 = sm.add_constant(regression_data[['as_value_z', 'rg_value_z', 'rg_volatility_z', 'as_change_z', 'as_rg_inter']])
m5 = OLS(regression_data['next_quarter_return'], X5).fit(cov_type='cluster',
          cov_kwds={'groups': regression_data['fund_code']})
print(m5.summary().tables[1])
print(f"  R²: {m5.rsquared:.4f}, Adj R²: {m5.rsquared_adj:.4f}")
print(f"  F-stat: {m5.fvalue:.2f}")

# 样本外检验
print("\n--- 样本外检验 ---")
split_quarter = regression_data['report_quarter'].quantile(0.7)
train = regression_data[regression_data['report_quarter'] <= split_quarter]
test = regression_data[regression_data['report_quarter'] > split_quarter]
X_train = sm.add_constant(train[['as_value_z', 'rg_value_z', 'rg_volatility_z', 'as_change_z', 'as_rg_inter']])
X_test = sm.add_constant(test[['as_value_z', 'rg_value_z', 'rg_volatility_z', 'as_change_z', 'as_rg_inter']])
m5_train = OLS(train['next_quarter_return'], X_train).fit()
pred_test = m5_train.predict(X_test)
ss_res = ((test['next_quarter_return'] - pred_test) ** 2).sum()
ss_tot = ((test['next_quarter_return'] - test['next_quarter_return'].mean()) ** 2).sum()
oos_r2 = 1 - ss_res / ss_tot if ss_tot > 0 else np.nan
print(f"  训练集: {len(train)} 条, 测试集: {len(test)} 条")
print(f"  样本外R²: {oos_r2:.4f}")

# ============================================================
# 6. 分组检验
# ============================================================
print("\n" + "=" * 60)
print("6. 分组检验")
print("=" * 60)

# 按AS五分组
as_quantiles = regression_data.groupby('report_quarter')['as_value'].transform(
    lambda x: pd.qcut(x, 5, labels=['Q1(低)', 'Q2', 'Q3', 'Q4', 'Q5(高)'], duplicates='drop')
)
regression_data['as_quintile'] = as_quantiles
group_result = regression_data.groupby('as_quintile')['next_quarter_return'].agg(['mean', 'std', 'count'])
print("\nAS五分组收益:")
print(group_result)
print(f"\n  Q5-Q1收益差: {group_result.loc['Q5(高)', 'mean'] - group_result.loc['Q1(低)', 'mean']:.4f}")

# 按RG五分组
rg_quantiles = regression_data.groupby('report_quarter')['rg_value'].transform(
    lambda x: pd.qcut(x, 5, labels=['Q1(低RG)', 'Q2', 'Q3', 'Q4', 'Q5(高RG)'], duplicates='drop')
)
regression_data['rg_quintile'] = rg_quantiles
rg_group = regression_data.groupby('rg_quintile')['next_quarter_return'].agg(['mean', 'std', 'count'])
print("\nRG五分组收益:")
print(rg_group)

# 保存完整结果
regression_data.to_csv(os.path.join(OUTPUT_DIR, 'mvp_regression_results_200.csv'), index=False)
print("\n  已保存: mvp_regression_results_200.csv")

print("\n" + "=" * 60)
print("全部完成!")
print("=" * 60)
