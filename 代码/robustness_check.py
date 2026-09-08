#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
稳健性检验与模型优化
1. Fama-MacBeth回归
2. 基金固定效应
3. 牛熊市分组
4. 不同滞后阶数
5. 非线性项检验
6. 双重排序
"""
import pandas as pd
import numpy as np
import os
import statsmodels.api as sm
from statsmodels.regression.linear_model import OLS
import warnings
warnings.filterwarnings('ignore')

DATA_DIR = r'D:\Desktop\基金经理行为分析研究\数据'

# 加载面板
panel = pd.read_csv(os.path.join(DATA_DIR, 'L4_风险应对层', '主分析面板_旧版v2.csv'))
panel['quarter'] = pd.PeriodIndex(panel['quarter'], freq='Q')
panel['fund_code'] = panel['fund_code'].astype(str)

print("=" * 70)
print("稳健性检验与模型优化")
print("=" * 70)
print(f"面板: {len(panel)} 条, {panel['fund_code'].nunique()} 只基金")
print(f"季度: {panel['quarter'].min()} ~ {panel['quarter'].max()}")

reg = panel.dropna(subset=['next_return']).copy()

# 标准化
for col in ['as_value', 'rg_value', 'rg_vol', 'as_change']:
    z = col + '_z'
    m, s = reg[col].mean(), reg[col].std()
    reg[z] = (reg[col] - m) / s if s > 0 else 0
reg['as_rg_z'] = reg['as_value_z'] * reg['rg_value_z']
if 'ici_value' in reg.columns:
    reg['ici_z'] = (reg['ici_value'] - reg['ici_value'].mean()) / reg['ici_value'].std()
    reg['ici_sq_z'] = reg['ici_z'] ** 2
    reg['as_sq_z'] = reg['as_value_z'] ** 2

# ============================================================
# 1. Fama-MacBeth回归
# ============================================================
print("\n" + "=" * 70)
print("1. Fama-MacBeth回归")
print("=" * 70)

vars_fm = ['as_value_z', 'rg_value_z', 'as_change_z']
if 'ici_z' in reg.columns:
    vars_fm.append('ici_z')

# 按季度截面回归
quarters = sorted(reg['quarter'].unique())
fm_coefs = {v: [] for v in vars_fm}
fm_r2 = []

for q in quarters:
    q_data = reg[reg['quarter'] == q]
    if len(q_data) < 20:
        continue
    X = sm.add_constant(q_data[vars_fm])
    y = q_data['next_return']
    try:
        m = OLS(y, X).fit()
        for v in vars_fm:
            fm_coefs[v].append(m.params.get(v, np.nan))
        fm_r2.append(m.rsquared)
    except:
        pass

print(f"  有效季度数: {len(fm_r2)}")
print(f"  平均截面R²: {np.mean(fm_r2):.4f}")
print(f"\n  Fama-MacBeth系数（时间序列均值）:")
for v in vars_fm:
    coefs = np.array(fm_coefs[v])
    coefs = coefs[~np.isnan(coefs)]
    mean_coef = coefs.mean()
    std_coef = coefs.std()
    t_stat = mean_coef / (std_coef / np.sqrt(len(coefs))) if std_coef > 0 else 0
    print(f"    {v:20s}: 均值={mean_coef:.4f}, t={t_stat:.2f}, n={len(coefs)}")

# ============================================================
# 2. 基金固定效应回归
# ============================================================
print("\n" + "=" * 70)
print("2. 基金固定效应回归")
print("=" * 70)

# 创建基金哑变量（仅保留观测数>=4的基金）
fund_counts = reg['fund_code'].value_counts()
valid_funds = fund_counts[fund_counts >= 4].index
reg_fe = reg[reg['fund_code'].isin(valid_funds)].copy()

# 加入基金固定效应
fund_dummies = pd.get_dummies(reg_fe['fund_code'], prefix='fe', drop_first=True).astype(float)
vars_fe = ['as_value_z', 'rg_value_z', 'as_change_z']
if 'ici_z' in reg_fe.columns:
    vars_fe.append('ici_z')

X_fe = sm.add_constant(pd.concat([reg_fe[vars_fe], fund_dummies], axis=1))
m_fe = OLS(reg_fe['next_return'], X_fe).fit()
print(f"  样本: {len(reg_fe)}, 基金数: {reg_fe['fund_code'].nunique()}")
print(f"  固定效应模型 R²: {m_fe.rsquared:.4f}, Adj R²: {m_fe.rsquared_adj:.4f}")
for v in vars_fe:
    print(f"    {v:20s}: {m_fe.params[v]:.4f} (t={m_fe.tvalues[v]:.2f}, p={m_fe.pvalues[v]:.4f})")

# ============================================================
# 3. 牛熊市分组检验
# ============================================================
print("\n" + "=" * 70)
print("3. 市场状态分组检验")
print("=" * 70)

# 用季度回报的均值判断市场状态
q_returns = reg.groupby('quarter')['quarter_return'].mean()
print("  各季度市场平均回报:")
for q, r in q_returns.items():
    state = "牛" if r > 0 else "熊"
    print(f"    {q}: {r:.4f} ({state})")

# 定义牛熊市
bull_qs = q_returns[q_returns > 0].index
bear_qs = q_returns[q_returns <= 0].index

for state, qs in [("牛市", bull_qs), ("熊市", bear_qs)]:
    s_data = reg[reg['quarter'].isin(qs)]
    if len(s_data) < 50:
        continue
    vars_s = ['as_value_z', 'rg_value_z', 'as_change_z']
    if 'ici_z' in s_data.columns:
        vars_s.append('ici_z')
    X_s = sm.add_constant(s_data[vars_s])
    m_s = OLS(s_data['next_return'], X_s).fit(cov_type='cluster', cov_kwds={'groups': s_data['fund_code']})
    print(f"\n  {state} ({len(s_data)} 观测):")
    for v in vars_s:
        print(f"    {v:20s}: {m_s.params[v]:.4f} (t={m_s.tvalues[v]:.2f}, p={m_s.pvalues[v]:.4f})")
    print(f"    R²: {m_s.rsquared:.4f}")

# ============================================================
# 4. 不同滞后阶数检验
# ============================================================
print("\n" + "=" * 70)
print("4. 不同滞后阶数检验")
print("=" * 70)

# 重新构建面板，计算不同滞后的下期收益
panel_sorted = panel.sort_values(['fund_code', 'quarter'])
for lag in [1, 2, 3]:
    panel_sorted[f'next_{lag}q'] = panel_sorted.groupby('fund_code')['quarter_return'].shift(-lag)

for lag in [1, 2, 3]:
    col = f'next_{lag}q'
    lag_data = panel_sorted.dropna(subset=[col]).copy()
    if len(lag_data) < 100:
        continue
    
    # 标准化
    for c in ['as_value', 'rg_value', 'as_change']:
        z = c + '_z'
        m, s = lag_data[c].mean(), lag_data[c].std()
        lag_data[z] = (lag_data[c] - m) / s if s > 0 else 0
    if 'ici_value' in lag_data.columns:
        lag_data['ici_z'] = (lag_data['ici_value'] - lag_data['ici_value'].mean()) / lag_data['ici_value'].std()
    
    vars_lag = ['as_value_z', 'rg_value_z', 'as_change_z']
    if 'ici_z' in lag_data.columns:
        vars_lag.append('ici_z')
    
    X_lag = sm.add_constant(lag_data[vars_lag])
    m_lag = OLS(lag_data[col], X_lag).fit(cov_type='cluster', cov_kwds={'groups': lag_data['fund_code']})
    
    print(f"\n  滞后{lag}季度 ({len(lag_data)} 观测):")
    for v in vars_lag:
        print(f"    {v:20s}: {m_lag.params[v]:.4f} (t={m_lag.tvalues[v]:.2f}, p={m_lag.pvalues[v]:.4f})")
    print(f"    R²: {m_lag.rsquared:.4f}")

# ============================================================
# 5. 非线性项检验
# ============================================================
print("\n" + "=" * 70)
print("5. 非线性项检验（AS和ICI的二次项）")
print("=" * 70)

if 'ici_z' in reg.columns and 'as_sq_z' in reg.columns:
    vars_nl = ['as_value_z', 'as_sq_z', 'rg_value_z', 'as_change_z', 'ici_z', 'ici_sq_z']
    X_nl = sm.add_constant(reg[vars_nl])
    m_nl = OLS(reg['next_return'], X_nl).fit(cov_type='cluster', cov_kwds={'groups': reg['fund_code']})
    print(f"  非线性模型 R²: {m_nl.rsquared:.4f}")
    for v in vars_nl:
        sig = '***' if m_nl.pvalues[v] < 0.01 else ('**' if m_nl.pvalues[v] < 0.05 else ('*' if m_nl.pvalues[v] < 0.1 else ''))
        print(f"    {v:20s}: {m_nl.params[v]:.4f} (t={m_nl.tvalues[v]:.2f}, p={m_nl.pvalues[v]:.4f}) {sig}")
    
    # 检查AS的U型
    if m_nl.pvalues['as_sq_z'] < 0.1:
        axis = -m_nl.params['as_value_z'] / (2 * m_nl.params['as_sq_z'])
        print(f"  AS U型对称轴: {axis:.4f}")
    
    # 检查ICI的U型
    if m_nl.pvalues['ici_sq_z'] < 0.1:
        axis = -m_nl.params['ici_z'] / (2 * m_nl.params['ici_sq_z'])
        print(f"  ICI U型对称轴: {axis:.4f}")

# ============================================================
# 6. 双重排序（AS × ICI）
# ============================================================
print("\n" + "=" * 70)
print("6. 双重排序：AS × ICI 独立五分位")
print("=" * 70)

if 'ici_value' in reg.columns:
    # 按季度截面双重排序
    reg['as_q'] = reg.groupby('quarter')['as_value'].transform(
        lambda x: pd.qcut(x, 3, labels=['低AS', '中AS', '高AS'], duplicates='drop')
    )
    def safe_qcut(x, n=3, labels=None):
        try:
            return pd.qcut(x, n, labels=labels, duplicates='drop')
        except:
            # 如果分位数太少，用中位数分两组
            return pd.Series(np.where(x > x.median(), '高', '低'), index=x.index)
    
    reg['ici_q'] = reg.groupby('quarter')['ici_value'].transform(lambda x: safe_qcut(x, 3, ['低ICI', '中ICI', '高ICI']))
    
    double_sort = reg.groupby(['as_q', 'ici_q'])['next_return'].agg(['mean', 'std', 'count'])
    print("\n  AS × ICI 双重排序下期收益:")
    print(double_sort.to_string())
    
    # 关键对比
    low_ici_high_as = reg[(reg['ici_q'] == '低ICI') & (reg['as_q'] == '高AS')]['next_return'].mean()
    high_ici_high_as = reg[(reg['ici_q'] == '高ICI') & (reg['as_q'] == '高AS')]['next_return'].mean()
    print(f"\n  高AS+低ICI: {low_ici_high_as:.4f}")
    print(f"  高AS+高ICI: {high_ici_high_as:.4f}")
    print(f"  差异: {low_ici_high_as - high_ici_high_as:.4f}")

# ============================================================
# 7. 汇总
# ============================================================
print("\n" + "=" * 70)
print("7. 稳健性检验汇总")
print("=" * 70)

print("""
检验结论:
  1. Fama-MacBeth: 验证截面预测力的时间序列稳定性
  2. 基金固定效应: 控制个体异质性后的系数稳定性
  3. 牛熊市分组: 检验指标在不同市场状态下的差异化表现
  4. 滞后阶数: 1Q/2Q/3Q预测力的衰减速度
  5. 非线性项: AS和ICI是否存在最优区间
  6. 双重排序: AS×ICI交互组合的收益差异

核心问题诊断:
  - 全模型R²偏低(0.015-0.024)：可能原因——
    a) 等权基准导致AS区分度不足(σ=0.029)
    b) 2021-2024为持续熊市，行为指标在单边下行中预测力减弱
    c) 缺少Fama-French因子调整（超额收益而非raw return）
    d) ICI仅覆盖105只基金，限制了样本量
  - 样本外R²为负：说明模型在熊市中泛化能力不足
    改进方向：加入市场状态交互项，或使用滚动窗口预测
""")

# 保存双重排序结果
if 'ici_value' in reg.columns:
    double_sort.to_csv(os.path.join(DATA_DIR, 'L4_风险应对层', '双重排序AS_ICI结果.csv'))
    print("双重排序结果已保存: double_sort_AS_ICI.csv")

print("\n全部稳健性检验完成。")
