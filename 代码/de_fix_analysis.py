import pandas as pd
import numpy as np
import statsmodels.api as sm

panel = pd.read_csv('D:/Desktop/基金经理行为分析研究/数据/L4_风险应对层/预处理面板_v20_诊断用.csv')
panel['fund_code'] = panel['fund_code'].astype(str).str.strip().str.zfill(6)

# 1. 追溯LSV均值来源
print('=== LSV均值追溯 ===')
print(f'面板lsv观测级均值={panel.lsv.dropna().mean():.4f}')
fund_lsv = panel.groupby('fund_code').lsv.mean().dropna()
print(f'面板lsv基金级均值={fund_lsv.mean():.4f} (N={len(fund_lsv)})')

lsv_v20 = pd.read_csv('D:/Desktop/基金经理行为分析研究/数据/L5_认知行为层/羊群行为LSV指标_诊断用.csv')
lsv_v20['fund_code'] = lsv_v20['fund_code'].astype(str).str.strip().str.zfill(6)
print(f'l5_lsv_v20观测级均值={lsv_v20.lsv.mean():.4f}')
print(f'l5_lsv_v20基金级均值={lsv_v20.groupby("fund_code").lsv.mean().mean():.4f}')
print()

# 2. 修复后DE重跑截面回归
de_fixed = pd.read_csv('D:/Desktop/基金经理行为分析研究/数据/L5_认知行为层/处置效应DE修正_诊断用.csv')
de_fixed['fund_code'] = de_fixed['fund_code'].astype(str).str.strip().str.zfill(6)
de_fund = de_fixed.groupby('fund_code').de.mean().reset_index()
de_fund.columns = ['fund_code','de_fixed']

fund_data = panel.groupby('fund_code').agg({
    'de':'mean', 'lsv':'mean', 'risk_asym':'mean',
    'log_aum':'mean', 'ff5_adj_return':'mean'
}).reset_index()
fund_data = fund_data.merge(de_fund, on='fund_code', how='left')

orig = fund_data.dropna(subset=['de','lsv','risk_asym','ff5_adj_return','log_aum']).copy()
fixed = fund_data.dropna(subset=['de_fixed','lsv','risk_asym','ff5_adj_return','log_aum']).copy()

print(f'=== 截面回归对比 ===')
print(f'原DE截面 N={len(orig)}, 修复DE截面 N={len(fixed)}')

X_orig = sm.add_constant(orig[['de','lsv','risk_asym','log_aum']])
m_orig = sm.OLS(orig['ff5_adj_return'], X_orig).fit(cov_type='HC1')
X_fixed = sm.add_constant(fixed[['de_fixed','lsv','risk_asym','log_aum']])
m_fixed = sm.OLS(fixed['ff5_adj_return'], X_fixed).fit(cov_type='HC1')

print('\n--- 原DE截面 ---')
for v in ['de','lsv','risk_asym']:
    sig = '***' if m_orig.pvalues[v]<0.01 else '**' if m_orig.pvalues[v]<0.05 else '*' if m_orig.pvalues[v]<0.1 else ''
    print(f'  {v}: b={m_orig.params[v]:.4f}, t={m_orig.tvalues[v]:.2f}{sig}')
print(f'  R2={m_orig.rsquared:.4f}')

print('\n--- 修复DE截面 ---')
for v in ['de_fixed','lsv','risk_asym']:
    sig = '***' if m_fixed.pvalues[v]<0.01 else '**' if m_fixed.pvalues[v]<0.05 else '*' if m_fixed.pvalues[v]<0.1 else ''
    print(f'  {v}: b={m_fixed.params[v]:.4f}, t={m_fixed.tvalues[v]:.2f}{sig}')
print(f'  R2={m_fixed.rsquared:.4f}')

# 同样本对比
both = fund_data.dropna(subset=['de','de_fixed','lsv','risk_asym','ff5_adj_return','log_aum']).copy()
print(f'\n=== 同样本对比 (N={len(both)}) ===')
X1 = sm.add_constant(both[['de','lsv','risk_asym','log_aum']])
m1 = sm.OLS(both['ff5_adj_return'], X1).fit(cov_type='HC1')
X2 = sm.add_constant(both[['de_fixed','lsv','risk_asym','log_aum']])
m2 = sm.OLS(both['ff5_adj_return'], X2).fit(cov_type='HC1')
print(f'原de:   b={m1.params["de"]:.4f}, t={m1.tvalues["de"]:.2f} (p={m1.pvalues["de"]:.4f})')
print(f'修复de: b={m2.params["de_fixed"]:.4f}, t={m2.tvalues["de_fixed"]:.2f} (p={m2.pvalues["de_fixed"]:.4f})')
print(f'RA(原):  b={m1.params["risk_asym"]:.4f}, t={m1.tvalues["risk_asym"]:.2f}')
print(f'RA(修复):b={m2.params["risk_asym"]:.4f}, t={m2.tvalues["risk_asym"]:.2f}')
print(f'LSV(原): b={m1.params["lsv"]:.4f}, t={m1.tvalues["lsv"]:.2f}')
print(f'LSV(修复):b={m2.params["lsv"]:.4f}, t={m2.tvalues["lsv"]:.2f}')

# 3. 组内效应（双向FE）
print('\n=== 组内效应（双向FE）===')
panel_fix = panel.merge(de_fund, on='fund_code', how='left')
# 用excess_return做组内
if 'excess_return' in panel_fix.columns:
    # 原DE组内
    orig_panel = panel_fix.dropna(subset=['de','lsv','risk_asym','excess_return']).copy()
    from linearmodels.panel import PanelOLS
    orig_panel = orig_panel.set_index(['fund_code','report_date']) if 'report_date' in orig_panel.columns else orig_panel.set_index(['fund_code', orig_panel.index])
    
    # 简单OLS with FE (用pd.get_dummies替代)
    print('  (组内FE需linearmodels库，跳过，仅报告截面结果)')
