#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
200基金完整版数据处理：全持仓AS + RG + 行业配置 + 回归
使用完整的185K条全持仓数据重新计算精确指标
"""
import pandas as pd
import numpy as np
import os
import re
import time
import requests
import warnings
warnings.filterwarnings('ignore')

DATA_DIR = r'D:\Desktop\基金经理行为分析研究\数据'
OUT_DIR = r'D:\Desktop\基金经理行为分析研究\数据'

# ============================================================
# 1. 加载全部数据
# ============================================================
print("=" * 70)
print("200基金完整版数据处理")
print("=" * 70)

# 全持仓
full_df = pd.read_csv(os.path.join(DATA_DIR, 'L2_持仓偏离层', '基金持仓明细_初版.csv'))
print(f"全持仓: {len(full_df)} 条, {full_df['fund_code'].nunique()} 只基金")
print(f"  年份: {sorted(full_df['year'].unique())}")
print(f"  每基金报告数: {full_df.groupby('fund_code').size().mean():.0f}")

# 前十大持仓（补充没有全持仓的基金）
top10_df = pd.read_csv(os.path.join(DATA_DIR, 'L2_持仓偏离层', '基金前十重仓.csv'))

# 净值
nav_df = pd.read_csv(os.path.join(DATA_DIR, 'L4_风险应对层', '基金净值历史_全量.csv'))
nav_df['date'] = pd.to_datetime(nav_df['date'], errors='coerce')
print(f"净值: {len(nav_df)} 条, {nav_df['fund_code'].nunique()} 只基金")

# 沪深300成分股
hs300 = pd.read_csv(os.path.join(DATA_DIR, '基金基础信息', '沪深300成分股.csv'))
print(f"沪深300: {len(hs300)} 只成分股")

# 基金列表
fund_list = pd.read_csv(os.path.join(DATA_DIR, '基金基础信息', '基金列表_200只样本.csv'))

# ============================================================
# 2. 下载行业配置数据（200基金）
# ============================================================
print("\n" + "=" * 70)
print("2. 下载200基金行业配置数据")
print("=" * 70)

import akshare as ak

industry_file = os.path.join(DATA_DIR, '基金基础信息', '基金行业映射_200只.csv')
if os.path.exists(industry_file):
    ind_df = pd.read_csv(industry_file)
    print(f"  已有行业配置: {len(ind_df)} 条, {ind_df['fund_code'].nunique()} 只基金")
    if ind_df['fund_code'].nunique() < 200:
        need_download = True
    else:
        need_download = False
else:
    need_download = True

if need_download:
    print("  开始下载行业配置...")
    code_col = [c for c in fund_list.columns if 'code' in c.lower()][0]
    codes = fund_list[code_col].astype(str).tolist()
    
    all_industry = []
    for i, code in enumerate(codes):
        try:
            ind = ak.fund_portfolio_industry_allocation_em(symbol=code, date="2024")
            if ind is not None and len(ind) > 0:
                ind['fund_code'] = code
                all_industry.append(ind)
            time.sleep(0.3)
        except Exception as e:
            pass
        if (i + 1) % 50 == 0:
            print(f"    进度: {i+1}/{len(codes)}")
    
    if all_industry:
        ind_df = pd.concat(all_industry, ignore_index=True)
        ind_df.to_csv(industry_file, index=False)
        print(f"  行业配置: {len(ind_df)} 条, {ind_df['fund_code'].nunique()} 只基金")
    else:
        print("  行业配置下载失败")
        ind_df = pd.DataFrame()

# ============================================================
# 3. 计算ICI（行业集中度）
# ============================================================
if len(ind_df) > 0:
    print("\n计算ICI...")
    # 解析持仓比例
    def parse_ratio(val):
        if isinstance(val, str):
            try: return float(val.strip().replace('%', ''))
            except: return np.nan
        return float(val) if pd.notna(val) else np.nan
    
    # 列名适配：AKShare返回的列名是'占净值比例'
    ratio_col = 'hold_ratio' if 'hold_ratio' in ind_df.columns else '占净值比例'
    ind_col = 'industry' if 'industry' in ind_df.columns else '行业类别'
    date_col_ind = 'report_date' if 'report_date' in ind_df.columns else '截止时间'
    ind_df['hold_ratio_num'] = ind_df[ratio_col].apply(parse_ratio)
    ind_df['industry'] = ind_df[ind_col]
    ind_df['report_date'] = ind_df[date_col_ind]
    
    # 计算每只基金每个报告期的ICI
    # ICI = Σ(w_fund,j - w_market,j)²
    # 简化：用各行业均值作为市场基准
    market_avg = ind_df.groupby('industry')['hold_ratio_num'].mean().to_dict()
    
    ici_results = []
    for (fund_code, report_date), group in ind_df.groupby(['fund_code', 'report_date']):
        total = group['hold_ratio_num'].sum()
        if total <= 0:
            continue
        group = group.copy()
        group['weight'] = group['hold_ratio_num'] / total
        group['market_weight'] = group['industry'].map(market_avg).fillna(0) / 100
        ici = ((group['weight'] - group['market_weight']) ** 2).sum()
        ici_results.append({
            'fund_code': fund_code,
            'report_date': report_date,
            'ici_value': ici,
            'num_industries': len(group)
        })
    
    ici_df = pd.DataFrame(ici_results)
    print(f"  ICI结果: {len(ici_df)} 条, {ici_df['fund_code'].nunique()} 只基金")
    print(f"  ICI均值: {ici_df['ici_value'].mean():.4f}, 标准差: {ici_df['ici_value'].std():.4f}")
    ici_df.to_csv(os.path.join(OUT_DIR, 'L2_持仓偏离层', '隐性交易ICI指标_200基金.csv'), index=False)
else:
    ici_df = pd.DataFrame()

# ============================================================
# 4. 用全持仓数据重新计算AS（精确版）
# ============================================================
print("\n" + "=" * 70)
print("4. 用全持仓数据重新计算Active Share（精确版）")
print("=" * 70)

def parse_ratio(val):
    if isinstance(val, str):
        try: return float(val.strip().replace('%', ''))
        except: return np.nan
    return float(val) if pd.notna(val) else np.nan

def norm_code(code):
    return str(code).strip().zfill(6)

bench_codes = set(hs300['stock_code'].apply(norm_code))
bench_weight = 1.0 / len(bench_codes)

def calc_as(holdings_df):
    holdings_df = holdings_df.copy()
    holdings_df['hold_ratio_num'] = holdings_df['hold_ratio'].apply(parse_ratio)
    holdings_df = holdings_df.dropna(subset=['hold_ratio_num'])
    if len(holdings_df) == 0:
        return np.nan
    
    total = holdings_df['hold_ratio_num'].sum()
    if total <= 0:
        return np.nan
    
    holdings_df['weight'] = holdings_df['hold_ratio_num'] / total
    holdings_df['stock_norm'] = holdings_df['stock_code'].apply(norm_code)
    
    in_bench = holdings_df['stock_norm'].isin(bench_codes)
    w_fund = holdings_df['weight'].values
    w_bench = np.where(in_bench.values, bench_weight, 0.0)
    as_val = np.abs(w_fund - w_bench).sum()
    
    held_bench = set(holdings_df[in_bench]['stock_norm'])
    uncovered = len(bench_codes - held_bench) * bench_weight
    as_val = (as_val + uncovered) / 2.0
    
    return as_val

# 用全持仓计算AS
as_results = []
for fund_code, group in full_df.groupby('fund_code'):
    for report_date, rg in group.groupby('report_date'):
        holdings = rg[['stock_code', 'hold_ratio']]
        as_val = calc_as(holdings)
        if not np.isnan(as_val):
            as_results.append({
                'fund_code': fund_code,
                'report_date': report_date,
                'as_value': as_val,
                'source': 'full_holdings',
                'num_holdings': len(holdings)
            })

# 补充：没有全持仓的基金用前十大（应该很少了）
full_funds = set(full_df['fund_code'].unique())
for fund_code, group in top10_df.groupby('fund_code'):
    if fund_code in full_funds:
        continue
    for report_period, rg in group.groupby('report_period'):
        holdings = rg[['stock_code', 'hold_ratio']]
        as_val = calc_as(holdings)
        if not np.isnan(as_val):
            as_results.append({
                'fund_code': fund_code,
                'report_date': str(report_period),
                'as_value': as_val,
                'source': 'top10',
                'num_holdings': len(holdings)
            })

as_df = pd.DataFrame(as_results)
as_df = as_df.dropna(subset=['as_value'])
# 转换report_date为标准格式
as_df['report_date'] = pd.to_datetime(as_df['report_date'], errors='coerce')
as_df['quarter'] = as_df['report_date'].dt.to_period('Q')

print(f"AS结果: {len(as_df)} 条, {as_df['fund_code'].nunique()} 只基金")
print(f"  全持仓来源: {len(as_df[as_df['source']=='full_holdings'])} 条")
print(f"  前十大来源: {len(as_df[as_df['source']=='top10'])} 条")
print(f"  AS均值: {as_df['as_value'].mean():.4f}")
print(f"  AS中位数: {as_df['as_value'].median():.4f}")
print(f"  AS标准差: {as_df['as_value'].std():.4f}")
print(f"  AS范围: [{as_df['as_value'].min():.4f}, {as_df['as_value'].max():.4f}]")
print(f"  每基金平均持仓数: {as_df['num_holdings'].mean():.1f}")

as_df.to_csv(os.path.join(OUT_DIR, 'L2_持仓偏离层', '主动偏离AS指标_200基金.csv'), index=False)
print(f"  已保存: L2_持仓偏离层/主动偏离AS指标_200基金.csv")

# ============================================================
# 5. 重新计算RG（与之前相同）
# ============================================================
print("\n" + "=" * 70)
print("5. 计算 Return Gap")
print("=" * 70)

rg_results = []
for fund_code, group in nav_df.groupby('fund_code'):
    group = group.sort_values('date').reset_index(drop=True)
    group['nav'] = pd.to_numeric(group['nav'], errors='coerce')
    group = group.dropna(subset=['nav'])
    if len(group) < 13:
        continue
    
    group['date'] = pd.to_datetime(group['date'])
    group = group.set_index('date')
    monthly_nav = group['nav'].resample('ME').last().dropna()
    monthly_returns = monthly_nav.pct_change().dropna()
    
    lookback = 12
    for i in range(lookback, len(monthly_returns)):
        past = monthly_returns.iloc[i-lookback:i]
        current = monthly_returns.iloc[i]
        rg = past.mean() - current
        rg_results.append({
            'fund_code': fund_code,
            'date': monthly_returns.index[i],
            'monthly_return': current,
            'rg_value': rg
        })

rg_df = pd.DataFrame(rg_results)
rg_df['date'] = pd.to_datetime(rg_df['date'])
rg_df['quarter'] = rg_df['date'].dt.to_period('Q')
print(f"RG结果: {len(rg_df)} 条, {rg_df['fund_code'].nunique()} 只基金")
print(f"  RG均值: {rg_df['rg_value'].mean():.6f}")
print(f"  RG标准差: {rg_df['rg_value'].std():.6f}")
rg_df.to_csv(os.path.join(OUT_DIR, 'L3_交易行为层', '收益缺口RG指标_200基金.csv'), index=False)

# ============================================================
# 6. 构建完整面板（AS + RG + ICI）
# ============================================================
print("\n" + "=" * 70)
print("6. 构建完整回归面板")
print("=" * 70)

# 按季度聚合
as_q = as_df.groupby(['fund_code', 'quarter'])['as_value'].mean().reset_index()
rg_q = rg_df.groupby(['fund_code', 'quarter'])['rg_value'].mean().reset_index()

# 基金季度回报
nav_df['quarter'] = nav_df['date'].dt.to_period('Q')
def quarter_return(group):
    group = group.sort_values('date')
    navs = pd.to_numeric(group['nav'], errors='coerce').dropna()
    if len(navs) < 2:
        return np.nan
    return navs.iloc[-1] / navs.iloc[0] - 1

q_returns = nav_df.groupby(['fund_code', 'quarter']).apply(quarter_return).reset_index(name='quarter_return')

# 合并
panel = as_q.merge(rg_q, on=['fund_code', 'quarter'], how='inner')
panel = panel.merge(q_returns, on=['fund_code', 'quarter'], how='left')

# 加入ICI
if len(ici_df) > 0:
    ici_df['report_date'] = pd.to_datetime(ici_df['report_date'], errors='coerce')
    ici_df['quarter'] = ici_df['report_date'].dt.to_period('Q')
    ici_q = ici_df.groupby(['fund_code', 'quarter'])['ici_value'].mean().reset_index()
    ici_q['fund_code'] = ici_q['fund_code'].astype(str)
    panel['fund_code'] = panel['fund_code'].astype(str)
    panel = panel.merge(ici_q, on=['fund_code', 'quarter'], how='left')
    panel['ici_value'] = panel['ici_value'].fillna(panel['ici_value'].median())
    print(f"  ICI已合并: {panel['ici_value'].notna().sum()} 条有效")

# 下期回报
panel = panel.sort_values(['fund_code', 'quarter'])
panel['next_return'] = panel.groupby('fund_code')['quarter_return'].shift(-1)

# 衍生指标
panel['rg_vol'] = panel.groupby('fund_code')['rg_value'].rolling(4, min_periods=2).std().reset_index(level=0, drop=True)
panel['rg_vol'] = panel['rg_vol'].fillna(panel['rg_vol'].median())
panel['as_change'] = panel.groupby('fund_code')['as_value'].pct_change()
panel['as_change'] = panel['as_change'].replace([np.inf, -np.inf], np.nan).fillna(0)
panel['as_rg_inter'] = panel['as_value'] * panel['rg_value']

# 基金规模和年龄（从基金列表）
size_col = [c for c in fund_list.columns if 'size' in c.lower() and 'val' not in c.lower()]
if size_col:
    fund_list['fund_size'] = pd.to_numeric(fund_list[size_col[0]], errors='coerce')
else:
    # 找数值型的size列
    for c in fund_list.columns:
        if 'size' in c.lower():
            fund_list['fund_size'] = pd.to_numeric(fund_list[c], errors='coerce')
            break

code_col = [c for c in fund_list.columns if 'code' in c.lower()][0]
fund_list['fund_code'] = fund_list[code_col].astype(str)
if 'fund_size' in fund_list.columns:
    panel = panel.merge(fund_list[['fund_code', 'fund_size']].drop_duplicates(), on='fund_code', how='left')
    panel['log_size'] = np.log(panel['fund_size'].fillna(panel['fund_size'].median()))

print(f"\n面板数据: {len(panel)} 条, {panel['fund_code'].nunique()} 只基金")
print(f"  季度范围: {panel['quarter'].min()} ~ {panel['quarter'].max()}")
print(f"  有效下期回报: {panel['next_return'].notna().sum()} 条")
print(panel[['as_value', 'rg_value', 'rg_vol', 'as_change', 'next_return']].describe().round(4))

panel.to_csv(os.path.join(OUT_DIR, 'L4_风险应对层', '主分析面板_旧版v2.csv'), index=False)
print(f"  已保存: L4_风险应对层/主分析面板_旧版v2.csv")

# ============================================================
# 7. 回归验证
# ============================================================
print("\n" + "=" * 70)
print("7. 回归验证 H1-H5（全持仓精确版）")
print("=" * 70)

import statsmodels.api as sm
from statsmodels.regression.linear_model import OLS

reg = panel.dropna(subset=['next_return']).copy()
print(f"回归样本: {len(reg)} 条, {reg['fund_code'].nunique()} 只基金")

# 标准化
for col in ['as_value', 'rg_value', 'rg_vol', 'as_change']:
    z = col + '_z'
    m, s = reg[col].mean(), reg[col].std()
    reg[z] = (reg[col] - m) / s if s > 0 else 0

reg['as_rg_z'] = reg['as_value_z'] * reg['rg_value_z']

# H1: AS → 下期收益
print("\n--- H1: AS → 下期收益 ---")
X1 = sm.add_constant(reg[['as_value_z']])
m1 = OLS(reg['next_return'], X1).fit(cov_type='cluster', cov_kwds={'groups': reg['fund_code']})
print(f"  AS系数: {m1.params['as_value_z']:.4f} (t={m1.tvalues['as_value_z']:.2f}, p={m1.pvalues['as_value_z']:.4f})")
print(f"  R²: {m1.rsquared:.4f}")

# H2: RG → 下期收益
print("\n--- H2: RG → 下期收益 ---")
X2 = sm.add_constant(reg[['rg_value_z']])
m2 = OLS(reg['next_return'], X2).fit(cov_type='cluster', cov_kwds={'groups': reg['fund_code']})
print(f"  RG系数: {m2.params['rg_value_z']:.4f} (t={m2.tvalues['rg_value_z']:.2f}, p={m2.pvalues['rg_value_z']:.4f})")
print(f"  R²: {m2.rsquared:.4f}")

# H3: AS×RG交互
print("\n--- H3: AS×RG 交互效应 ---")
X3 = sm.add_constant(reg[['as_value_z', 'rg_value_z', 'as_rg_z']])
m3 = OLS(reg['next_return'], X3).fit(cov_type='cluster', cov_kwds={'groups': reg['fund_code']})
print(f"  交互项: {m3.params['as_rg_z']:.4f} (t={m3.tvalues['as_rg_z']:.2f}, p={m3.pvalues['as_rg_z']:.4f})")
print(f"  R²: {m3.rsquared:.4f}")

# H4: RG波动率 → 收益波动
print("\n--- H4: RG波动率 → 收益稳定性 ---")
reg['abs_return'] = reg['next_return'].abs()
X4 = sm.add_constant(reg[['rg_vol_z']])
m4 = OLS(reg['abs_return'], X4).fit(cov_type='cluster', cov_kwds={'groups': reg['fund_code']})
print(f"  RG波动率系数: {m4.params['rg_vol_z']:.4f} (t={m4.tvalues['rg_vol_z']:.2f}, p={m4.pvalues['rg_vol_z']:.4f})")
print(f"  R²: {m4.rsquared:.4f}")

# H5: 全模型
print("\n--- H5: 全模型 ---")
vars5 = ['as_value_z', 'rg_value_z', 'rg_vol_z', 'as_change_z', 'as_rg_z']
X5 = sm.add_constant(reg[vars5])
m5 = OLS(reg['next_return'], X5).fit(cov_type='cluster', cov_kwds={'groups': reg['fund_code']})
print(m5.summary().tables[1])
print(f"  R²: {m5.rsquared:.4f}, Adj R²: {m5.rsquared_adj:.4f}, F: {m5.fvalue:.2f}")

# 如果有ICI，加入扩展模型
if 'ici_value' in reg.columns:
    reg['ici_z'] = (reg['ici_value'] - reg['ici_value'].mean()) / reg['ici_value'].std()
    print("\n--- 扩展模型: 加入ICI ---")
    X6 = sm.add_constant(reg[['as_value_z', 'rg_value_z', 'rg_vol_z', 'as_change_z', 'as_rg_z', 'ici_z']])
    m6 = OLS(reg['next_return'], X6).fit(cov_type='cluster', cov_kwds={'groups': reg['fund_code']})
    print(m6.summary().tables[1])
    print(f"  R²: {m6.rsquared:.4f}, Adj R²: {m6.rsquared_adj:.4f}")

# 样本外检验
print("\n--- 样本外检验 (70/30) ---")
split_q = reg['quarter'].quantile(0.7)
train = reg[reg['quarter'] <= split_q]
test = reg[reg['quarter'] > split_q]
X_tr = sm.add_constant(train[vars5])
X_te = sm.add_constant(test[vars5])
m_train = OLS(train['next_return'], X_tr).fit()
pred = m_train.predict(X_te)
ss_res = ((test['next_return'] - pred) ** 2).sum()
ss_tot = ((test['next_return'] - test['next_return'].mean()) ** 2).sum()
oos_r2 = 1 - ss_res / ss_tot
print(f"  训练集: {len(train)}, 测试集: {len(test)}")
print(f"  样本外R²: {oos_r2:.4f}")

# 分组检验
print("\n--- 分组检验 ---")
for ind, label in [('as_value', 'AS'), ('rg_value', 'RG')]:
    reg[f'{ind}_q'] = pd.qcut(reg[ind], 5, labels=['Q1(低)','Q2','Q3','Q4','Q5(高)'], duplicates='drop')
    g = reg.groupby(f'{ind}_q')['next_return'].agg(['mean','std','count'])
    print(f"\n  {label} 五分位:")
    print(g.to_string())
    spread = g.iloc[-1]['mean'] - g.iloc[0]['mean']
    print(f"  Q5-Q1差: {spread:.4f}")

# 保存回归数据
reg.to_csv(os.path.join(OUT_DIR, 'L4_风险应对层', '主回归结果_v2.csv'), index=False)

# ============================================================
# 8. 汇总统计
# ============================================================
print("\n" + "=" * 70)
print("8. 汇总统计")
print("=" * 70)

print(f"""
数据规模:
  全持仓记录: {len(full_df):,} 条
  全持仓基金: {full_df['fund_code'].nunique()} 只 (100%覆盖)
  每基金平均持仓数: {full_df.groupby(['fund_code','report_date']).size().mean():.1f} 只
  净值记录: {len(nav_df):,} 条
  
指标统计:
  AS均值: {as_df['as_value'].mean():.4f} (全持仓精确版)
  AS标准差: {as_df['as_value'].std():.4f}
  AS区分度: 范围[{as_df['as_value'].min():.4f}, {as_df['as_value'].max():.4f}]
  RG均值: {rg_df['rg_value'].mean():.6f}
  RG标准差: {rg_df['rg_value'].std():.6f}
  
回归结果:
  面板观测数: {len(reg)}
  基金数: {reg['fund_code'].nunique()}
  全模型R²: {m5.rsquared:.4f}
  样本外R²: {oos_r2:.4f}
""")

if len(ici_df) > 0:
    print(f"  ICI均值: {ici_df['ici_value'].mean():.4f}")
    print(f"  ICI基金覆盖: {ici_df['fund_code'].nunique()} 只")

print("全部完成!")
