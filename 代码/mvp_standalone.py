#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基金经理行为画像研究 — Phase 1.0 MVP验证脚本
================================================
使用基于真实文献参数的模拟数据，验证五层递进框架(L1-L5)的H1-H5假设。

样本设计：200只基金 × 12季度 = 2400观测
模拟参数来源：
  - AS均值~0.70 (Cremers & Petajisto 2009, 美国样本均值)
  - RG月度均值~0.05% (Kacperczyk et al. 2008)
  - SDI~0.15 (寇宗来等 2020, 中国样本)
  - Experience均值~4.5年 (中国基金经理中位数)

依赖: pandas, numpy, statsmodels, scipy, matplotlib
运行: python mvp_standalone.py
"""

import numpy as np
import pandas as pd
from scipy import stats
import statsmodels.api as sm
from statsmodels.regression.linear_model import OLS
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import warnings
warnings.filterwarnings('ignore')

# ============================================================
# 一、数据生成（基于真实文献参数的模拟数据）
# ============================================================

np.random.seed(42)

N_FUNDS = 200       # 基金数量
N_QUARTERS = 12     # 季度数量（3年）
N_OBS = N_FUNDS * N_QUARTERS

print("=" * 70)
print("基金经理行为画像研究 — Phase 1.0 MVP验证")
print("=" * 70)
print(f"\n样本设计: {N_FUNDS}只基金 × {N_QUARTERS}个季度 = {N_OBS}个观测值\n")

# 基金固定效应
fund_ids = np.repeat(np.arange(N_FUNDS), N_QUARTERS)
quarters = np.tile(np.arange(N_QUARTERS), N_FUNDS)

# --- L1: 背景特征层 ---
# Experience: 从业年限, U(1, 12), 均值约6.5年（中国基金经理偏年轻）
experience_base = np.random.uniform(1, 12, N_FUNDS)
experience = np.repeat(experience_base, N_QUARTERS) + quarters * 0.25  # 随时间增长

# RPI: 排名压力指数, 基于从业年限反比构造（年轻经理压力更大）
rpi_base = 1.0 / (1.0 + experience_base * 0.15)
rpi = np.repeat(rpi_base, N_QUARTERS) + np.random.normal(0, 0.05, N_OBS)
rpi = np.clip(rpi, 0, 1)

# --- L2: 持仓层 ---
# AS: Active Share, N(0.70, 0.15), 受Experience正向影响（H1）
as_true = (
    np.repeat(experience_base * 0.008, N_QUARTERS)  # H1: 经验→AS 正向
    + np.random.normal(0.65, 0.12, N_OBS)           # 基准均值
)
as_value = np.clip(as_true, 0, 1)

# ICI: 行业集中度, N(0.10, 0.06), 与AS弱正相关
ici = as_value * 0.05 + np.random.normal(0.05, 0.04, N_OBS)
ici = np.clip(ici, 0, 0.5)

# --- L3: 交易层 ---
# RG: Return Gap (季度), N(0.002, 0.008), 受AS正向影响
rg = (
    as_value * 0.003                                    # AS→RG 正向
    + np.random.normal(0.001, 0.006, N_OBS)             # 基准
)
# ARG: 绝对收益缺口 (申宇2013修正版), 取月度RG绝对值加总
arg = np.abs(rg) * 3 + np.random.normal(0.005, 0.003, N_OBS)
arg = np.clip(arg, 0, 0.05)

# --- L4: 风险应对层 ---
# SDI: 风格漂移指数, N(0.15, 0.08), 与业绩呈U型关系
sdi = np.random.normal(0.15, 0.06, N_OBS)
sdi = np.clip(sdi, 0, 0.5)

# 波动率管理: 基金特有波动率, N(0.18, 0.05)
vol_mgmt = np.random.normal(0.18, 0.04, N_OBS)

# --- L5: 认知行为层 ---
# OCI: 过度自信指数, 与Experience负相关（年轻经理更过度自信）
oci = (
    -experience * 0.002                                  # 经验降低过度自信
    + np.random.normal(0.15, 0.05, N_OBS)
)
oci = np.clip(oci, 0, 0.5)

# LA: 损失厌恶指数
la = np.random.normal(0.12, 0.04, N_OBS)
la = np.clip(la, 0, 0.3)

# --- 控制变量 ---
fund_size = np.random.lognormal(22, 0.8, N_OBS)  # 基金规模(元)
expense_ratio = np.random.uniform(0.005, 0.020, N_OBS)  # 费用率
turnover = np.random.uniform(1.0, 5.0, N_OBS)  # 换手率
fund_age = np.random.uniform(1, 10, N_OBS)  # 基金年龄(年)

# --- 被解释变量: 基金超额收益 (季度) ---
# 真实DGP: 综合各层指标的线性+非线性组合
alpha_true = (
    # H2: AS → 业绩 正向 (系数~0.04)
    as_value * 0.041
    # H3: RG → 业绩 正向 (系数~0.96)
    + rg * 0.96
    # H4: SDI → 业绩 U型 (一次项负, 二次项正)
    - sdi * 0.15 + sdi**2 * 0.12
    # H5: OCI → 业绩 负向 (系数~-0.016)
    - oci * 0.016
    # 控制变量
    - expense_ratio * 0.5
    + np.log(fund_size) * 0.001
    - turnover * 0.0005
    # 随机扰动
    + np.random.normal(0, 0.015, N_OBS)
)

# 组装DataFrame
df = pd.DataFrame({
    'fund_id': fund_ids,
    'quarter': quarters,
    'experience': experience,
    'rpi': rpi,
    'as': as_value,
    'ici': ici,
    'rg': rg,
    'arg': arg,
    'sdi': sdi,
    'vol_mgmt': vol_mgmt,
    'oci': oci,
    'la': la,
    'fund_size': fund_size,
    'expense_ratio': expense_ratio,
    'turnover': turnover,
    'fund_age': fund_age,
    'excess_return': alpha_true,
})

print("数据生成完成。描述统计：\n")
print(df[['experience', 'as', 'ici', 'rg', 'arg', 'sdi', 'oci', 'excess_return']].describe().round(4))
print()

# ============================================================
# 二、假设检验
# ============================================================

controls = ['fund_size', 'expense_ratio', 'turnover', 'fund_age']
df['log_size'] = np.log(df['fund_size'])

print("=" * 70)
print("假设检验结果")
print("=" * 70)

# --- H1: L1 Experience → L2 AS ---
print("\n--- H1: 从业年限 → Active Share ---")
X_h1 = sm.add_constant(df[['experience'] + controls_ctrl] if (controls_ctrl := ['log_size', 'expense_ratio', 'turnover']) else df[['experience']])
model_h1 = OLS(df['as'], X_h1).fit(cov_type='cluster', cov_kwds={'groups': df['fund_id']})
print(f"  Experience系数: {model_h1.params['experience']:.4f}")
print(f"  t值: {model_h1.tvalues['experience']:.2f}")
print(f"  p值: {model_h1.pvalues['experience']:.4f}")
print(f"  R²: {model_h1.rsquared:.4f}")
h1_pass = model_h1.pvalues['experience'] < 0.05
print(f"  结果: {'通过 ✓' if h1_pass else '未通过 ✗'}")

# --- H2: L2 AS → 业绩 ---
print("\n--- H2: Active Share → 基金超额收益 ---")
X_h2 = sm.add_constant(df[['as'] + ['log_size', 'expense_ratio', 'turnover']])
model_h2 = OLS(df['excess_return'], X_h2).fit(cov_type='cluster', cov_kwds={'groups': df['fund_id']})
print(f"  AS系数: {model_h2.params['as']:.4f}")
print(f"  t值: {model_h2.tvalues['as']:.2f}")
print(f"  p值: {model_h2.pvalues['as']:.4f}")
print(f"  R²: {model_h2.rsquared:.4f}")
h2_pass = model_h2.pvalues['as'] < 0.05 and model_h2.params['as'] > 0
print(f"  结果: {'通过 ✓' if h2_pass else '未通过 ✗'}")

# --- H3: L3 RG → 业绩 ---
print("\n--- H3: Return Gap → 基金超额收益 ---")
X_h3 = sm.add_constant(df[['rg'] + ['log_size', 'expense_ratio', 'turnover']])
model_h3 = OLS(df['excess_return'], X_h3).fit(cov_type='cluster', cov_kwds={'groups': df['fund_id']})
print(f"  RG系数: {model_h3.params['rg']:.4f}")
print(f"  t值: {model_h3.tvalues['rg']:.2f}")
print(f"  p值: {model_h3.pvalues['rg']:.4f}")
print(f"  R²: {model_h3.rsquared:.4f}")
h3_pass = model_h3.pvalues['rg'] < 0.05 and model_h3.params['rg'] > 0
print(f"  结果: {'通过 ✓' if h3_pass else '未通过 ✗'}")

# --- H4: L4 SDI → 业绩 (U型关系) ---
print("\n--- H4: 风格漂移指数 → 基金超额收益 (U型) ---")
df['sdi_sq'] = df['sdi'] ** 2
X_h4 = sm.add_constant(df[['sdi', 'sdi_sq'] + ['log_size', 'expense_ratio', 'turnover']])
model_h4 = OLS(df['excess_return'], X_h4).fit(cov_type='cluster', cov_kwds={'groups': df['fund_id']})
print(f"  SDI一次项: {model_h4.params['sdi']:.4f} (t={model_h4.tvalues['sdi']:.2f}, p={model_h4.pvalues['sdi']:.4f})")
print(f"  SDI二次项: {model_h4.params['sdi_sq']:.4f} (t={model_h4.tvalues['sdi_sq']:.2f}, p={model_h4.pvalues['sdi_sq']:.4f})")
# U型: 二次项显著为正
symmetry_axis = -model_h4.params['sdi'] / (2 * model_h4.params['sdi_sq']) if model_h4.params['sdi_sq'] != 0 else float('nan')
print(f"  U型对称轴: {symmetry_axis:.4f}")
print(f"  R²: {model_h4.rsquared:.4f}")
h4_pass = model_h4.pvalues['sdi_sq'] < 0.05 and model_h4.params['sdi_sq'] > 0
print(f"  结果: {'通过 ✓' if h4_pass else '未通过 ✗'}")

# --- H5: L5 OCI → 业绩 (负向) ---
print("\n--- H5: 过度自信指数 → 基金超额收益 (负向) ---")
X_h5 = sm.add_constant(df[['oci'] + ['log_size', 'expense_ratio', 'turnover']])
model_h5 = OLS(df['excess_return'], X_h5).fit(cov_type='cluster', cov_kwds={'groups': df['fund_id']})
print(f"  OCI系数: {model_h5.params['oci']:.4f}")
print(f"  t值: {model_h5.tvalues['oci']:.2f}")
print(f"  p值: {model_h5.pvalues['oci']:.4f}")
print(f"  R²: {model_h5.rsquared:.4f}")
h5_pass = model_h5.pvalues['oci'] < 0.05 and model_h5.params['oci'] < 0
print(f"  结果: {'通过 ✓' if h5_pass else '未通过 ✗'}")

# ============================================================
# 三、全模型回归
# ============================================================

print("\n" + "=" * 70)
print("全模型回归 (L1-L5全指标)")
print("=" * 70)

full_vars = ['experience', 'as', 'rg', 'sdi', 'sdi_sq', 'oci', 'log_size', 'expense_ratio', 'turnover']
X_full = sm.add_constant(df[full_vars])
model_full = OLS(df['excess_return'], X_full).fit(cov_type='cluster', cov_kwds={'groups': df['fund_id']})
print(model_full.summary().tables[1])
print(f"\n全模型 R²: {model_full.rsquared:.4f}")
print(f"调整 R²: {model_full.rsquared_adj:.4f}")

# ============================================================
# 四、样本外检验
# ============================================================

print("\n" + "=" * 70)
print("样本外检验 (前8季度训练, 后4季度测试)")
print("=" * 70)

train = df[df['quarter'] < 8].copy()
test = df[df['quarter'] >= 8].copy()

X_train = sm.add_constant(train[full_vars])
X_test = sm.add_constant(test[full_vars])
model_train = OLS(train['excess_return'], X_train).fit()

# 样本内R²
y_pred_train = model_train.predict(X_train)
ss_res_train = ((train['excess_return'] - y_pred_train) ** 2).sum()
ss_tot_train = ((train['excess_return'] - train['excess_return'].mean()) ** 2).sum()
r2_in = 1 - ss_res_train / ss_tot_train

# 样本外R²
y_pred_test = model_train.predict(X_test)
ss_res_test = ((test['excess_return'] - y_pred_test) ** 2).sum()
ss_tot_test = ((test['excess_return'] - test['excess_return'].mean()) ** 2).sum()
r2_out = 1 - ss_res_test / ss_tot_test

print(f"  样本内 R²: {r2_in:.4f}")
print(f"  样本外 R²: {r2_out:.4f}")

# ============================================================
# 五、分组检验
# ============================================================

print("\n" + "=" * 70)
print("分组检验 (五分位)")
print("=" * 70)

for indicator in ['as', 'rg', 'sdi', 'oci']:
    df['quintile'] = pd.qcut(df[indicator], 5, labels=['Q1(低)', 'Q2', 'Q3', 'Q4', 'Q5(高)'])
    group_means = df.groupby('quintile')['excess_return'].mean()
    print(f"\n  {indicator.upper()} 五分位组超额收益:")
    for q, v in group_means.items():
        print(f"    {q}: {v:.4f}")
    spread = group_means.iloc[-1] - group_means.iloc[0]
    print(f"    Q5-Q1 差: {spread:.4f}")

# ============================================================
# 六、可视化图表
# ============================================================

print("\n" + "=" * 70)
print("生成可视化图表...")
print("=" * 70)

fig, axes = plt.subplots(2, 3, figsize=(16, 10))
fig.suptitle('基金经理行为画像 MVP验证结果', fontsize=14, fontweight='bold')

# H1: Experience vs AS
axes[0, 0].scatter(df['experience'], df['as'], alpha=0.15, s=10, c='steelblue')
z = np.polyfit(df['experience'], df['as'], 1)
p = np.poly1d(z)
x_line = np.linspace(df['experience'].min(), df['experience'].max(), 100)
axes[0, 0].plot(x_line, p(x_line), 'r-', linewidth=2)
axes[0, 0].set_xlabel('Experience (years)')
axes[0, 0].set_ylabel('Active Share')
axes[0, 0].set_title(f'H1: Experience → AS (β={model_h1.params["experience"]:.4f})')

# H2: AS vs Return
axes[0, 1].scatter(df['as'], df['excess_return'], alpha=0.15, s=10, c='darkgreen')
z = np.polyfit(df['as'], df['excess_return'], 1)
p = np.poly1d(z)
x_line = np.linspace(df['as'].min(), df['as'].max(), 100)
axes[0, 1].plot(x_line, p(x_line), 'r-', linewidth=2)
axes[0, 1].set_xlabel('Active Share')
axes[0, 1].set_ylabel('Excess Return')
axes[0, 1].set_title(f'H2: AS → Return (β={model_h2.params["as"]:.4f})')

# H3: RG vs Return
axes[0, 2].scatter(df['rg'], df['excess_return'], alpha=0.15, s=10, c='orange')
z = np.polyfit(df['rg'], df['excess_return'], 1)
p = np.poly1d(z)
x_line = np.linspace(df['rg'].min(), df['rg'].max(), 100)
axes[0, 2].plot(x_line, p(x_line), 'r-', linewidth=2)
axes[0, 2].set_xlabel('Return Gap')
axes[0, 2].set_ylabel('Excess Return')
axes[0, 2].set_title(f'H3: RG → Return (β={model_h3.params["rg"]:.4f})')

# H4: SDI vs Return (U型)
axes[1, 0].scatter(df['sdi'], df['excess_return'], alpha=0.15, s=10, c='purple')
z = np.polyfit(df['sdi'], df['excess_return'], 2)
p = np.poly1d(z)
x_line = np.linspace(df['sdi'].min(), df['sdi'].max(), 100)
axes[1, 0].plot(x_line, p(x_line), 'r-', linewidth=2)
axes[1, 0].set_xlabel('Style Drift Index')
axes[1, 0].set_ylabel('Excess Return')
axes[1, 0].set_title(f'H4: SDI → Return (U-shape, β₂={model_h4.params["sdi_sq"]:.4f})')

# H5: OCI vs Return
axes[1, 1].scatter(df['oci'], df['excess_return'], alpha=0.15, s=10, c='crimson')
z = np.polyfit(df['oci'], df['excess_return'], 1)
p = np.poly1d(z)
x_line = np.linspace(df['oci'].min(), df['oci'].max(), 100)
axes[1, 1].plot(x_line, p(x_line), 'r-', linewidth=2)
axes[1, 1].set_xlabel('Overconfidence Index')
axes[1, 1].set_ylabel('Excess Return')
axes[1, 1].set_title(f'H5: OCI → Return (β={model_h5.params["oci"]:.4f})')

# 分组检验条形图
df['as_quintile'] = pd.qcut(df['as'], 5, labels=['Q1', 'Q2', 'Q3', 'Q4', 'Q5'])
group_means = df.groupby('as_quintile')['excess_return'].mean()
axes[1, 2].bar(range(5), group_means.values, color='steelblue', alpha=0.8)
axes[1, 2].set_xticks(range(5))
axes[1, 2].set_xticklabels(['Q1(低)', 'Q2', 'Q3', 'Q4', 'Q5(高)'])
axes[1, 2].set_xlabel('Active Share Quintile')
axes[1, 2].set_ylabel('Mean Excess Return')
axes[1, 2].set_title('AS分组: Q5-Q1超额收益差')

plt.tight_layout()
output_path = 'mvp_framework_validation.png'
plt.savefig(output_path, dpi=150, bbox_inches='tight')
plt.close()
print(f"  图表已保存: {output_path}")

# ============================================================
# 七、总结
# ============================================================

print("\n" + "=" * 70)
print("验证总结")
print("=" * 70)
print(f"""
  H1 (Experience → AS):     {'通过 ✓' if h1_pass else '未通过 ✗'}  系数={model_h1.params['experience']:.4f}, p={model_h1.pvalues['experience']:.4f}
  H2 (AS → 业绩):           {'通过 ✓' if h2_pass else '未通过 ✗'}  系数={model_h2.params['as']:.4f}, p={model_h2.pvalues['as']:.4f}
  H3 (RG → 业绩):           {'通过 ✓' if h3_pass else '未通过 ✗'}  系数={model_h3.params['rg']:.4f}, p={model_h3.pvalues['rg']:.4f}
  H4 (SDI → 业绩 U型):      {'通过 ✓' if h4_pass else '未通过 ✗'}  二次项={model_h4.params['sdi_sq']:.4f}, p={model_h4.pvalues['sdi_sq']:.4f}
  H5 (OCI → 业绩 负向):     {'通过 ✓' if h5_pass else '未通过 ✗'}  系数={model_h5.params['oci']:.4f}, p={model_h5.pvalues['oci']:.4f}
  
  全模型 R²: {model_full.rsquared:.4f}
  样本外 R²: {r2_out:.4f}
""")

# 保存数据
df.to_csv('mvp_data.csv', index=False)
print("  数据已保存: mvp_data.csv")
print("  图表已保存: mvp_framework_validation.png")
print("\nMVP验证完成。")
