# -*- coding: utf-8 -*-
"""
RA构念纯化：对RiskAsym做FF5因子beta正交化
直接用主面板现有FF5季度因子列（ff5_MKT_excess/ff5_SMB/ff5_HML/ff5_RMW/ff5_CMA）
1. 每只基金：quarter_return ~ FF5 时序回归 → 5个FF beta
2. 基金层面：RA ~ FF5 betas 正交化 → RA_purified_FF5（残差）
3. 截面回归对比：原RA vs RA_purified_FF5
4. 逐步正交化（逐个因子）记录t值变化
"""
import pandas as pd
import numpy as np
import statsmodels.api as sm
import warnings
warnings.filterwarnings('ignore')

DATA = r'D:\Desktop\基金经理行为分析研究\数据'
FF5 = ['ff5_MKT_excess', 'ff5_SMB', 'ff5_HML', 'ff5_RMW', 'ff5_CMA']
FF5_LABEL = ['MKT', 'SMB', 'HML', 'RMW', 'CMA']

# ========== 1. 主面板加载 ==========
panel = pd.read_csv(f'{DATA}/L4_风险应对层/预处理面板_v20_诊断用.csv')
panel['fund_code'] = panel['fund_code'].astype(str).str.strip().str.zfill(6)
print(f'面板: {len(panel)}行, {panel.fund_code.nunique()}基金')
print(f'FF5因子非空: {panel[FF5[0]].notna().sum()}')

# ========== 2. 每只基金时序回归得FF5 beta ==========
def calc_ff_betas(g, fund_code=None, min_obs=12):
    g = g.dropna(subset=['quarter_return'] + FF5)
    if len(g) < min_obs:
        return None
    X = sm.add_constant(g[FF5])
    y = g['quarter_return']
    try:
        m = sm.OLS(y, X).fit()
        return {
            'fund_code': fund_code if fund_code else g.name,
            'n_obs': len(g),
            'mkt_beta': m.params.get('ff5_MKT_excess', np.nan),
            'smb_beta': m.params.get('ff5_SMB', np.nan),
            'hml_beta': m.params.get('ff5_HML', np.nan),
            'rmw_beta': m.params.get('ff5_RMW', np.nan),
            'cma_beta': m.params.get('ff5_CMA', np.nan),
            'ff5_r2': m.rsquared,
        }
    except Exception:
        return None

print('\n计算每只基金FF5 beta...')
betas_list = []
for fc, g in panel.groupby('fund_code'):
    r = calc_ff_betas(g, fund_code=fc)
    if r is not None:
        betas_list.append(r)
betas_df = pd.DataFrame(betas_list)
print(f'成功计算FF5 beta的基金: {len(betas_df)}')
print(f'FF5 R²: 均值={betas_df.ff5_r2.mean():.3f}, 中位={betas_df.ff5_r2.median():.3f}')
print(f'每基金观测数: 均值={betas_df.n_obs.mean():.1f}, 最小={betas_df.n_obs.min()}, 最大={betas_df.n_obs.max()}')

# ========== 3. 基金层面RA与FF5 beta合并 ==========
fund_ra = panel.groupby('fund_code').agg({
    'risk_asym': 'mean',
    'ff5_adj_return': 'mean',
    'log_aum': 'mean',
}).reset_index()

fund_data = fund_ra.merge(betas_df, on='fund_code', how='inner')
fund_data = fund_data.dropna(subset=['risk_asym'])
print(f'\n基金层面(有RA+FF5 beta): {len(fund_data)}基金')

# ========== 4. RA对FF5 beta正交化与截面回归 ==========
def xsec_reg(df, ra_col, label, controls=None):
    cols = [ra_col] + (controls or [])
    d = df.dropna(subset=cols + ['ff5_adj_return'])
    X = sm.add_constant(d[cols])
    m = sm.OLS(d['ff5_adj_return'], X).fit(cov_type='HC1')
    t = m.tvalues[ra_col]
    b = m.params[ra_col]
    p = m.pvalues[ra_col]
    sig = '***' if p < 0.01 else '**' if p < 0.05 else '*' if p < 0.1 else ''
    print(f'  {label}: N={len(d)}, β={b:.4f}, t={t:.2f}{sig}, R²={m.rsquared:.4f}')
    return m

print('\n=== 截面回归对比 ===')
# (a) 原RA裸效应
m1 = xsec_reg(fund_data, 'risk_asym', '原RA裸效应')
# (b) 原RA + log_aum
m2 = xsec_reg(fund_data, 'risk_asym', '原RA+log_aum', controls=['log_aum'])

# (c) RA对FF5 beta正交化
ff_betas = ['mkt_beta', 'smb_beta', 'hml_beta', 'rmw_beta', 'cma_beta']
d = fund_data.dropna(subset=['risk_asym'] + ff_betas).copy()
X = sm.add_constant(d[ff_betas])
ra_orth = sm.OLS(d['risk_asym'], X).fit()
d['RA_purified_FF5'] = ra_orth.resid
print(f'\n  RA正交化残差: 均值={d.RA_purified_FF5.mean():.4f}, std={d.RA_purified_FF5.std():.4f}')
print(f'  原RA与残差相关: {d.risk_asym.corr(d.RA_purified_FF5):.4f}')

fund_data_pur = fund_data.merge(d[['fund_code', 'RA_purified_FF5']], on='fund_code', how='left')
# (d) 正交化后RA裸效应
m3 = xsec_reg(fund_data_pur, 'RA_purified_FF5', 'RA_purified_FF5裸效应')
# (e) 正交化后RA + log_aum
m4 = xsec_reg(fund_data_pur, 'RA_purified_FF5', 'RA_purified_FF5+log_aum', controls=['log_aum'])

# ========== 5. 逐步正交化 ==========
print('\n=== 逐步正交化（逐个加因子，记录截面t值）===')
print(f'  起点(原RA): β={m1.params["risk_asym"]:.4f}, t={m1.tvalues["risk_asym"]:.2f}')
# 合并beta到current
current = fund_data[['fund_code', 'risk_asym', 'ff5_adj_return', 'log_aum'] + ff_betas].copy()
current['ra_cur'] = current['risk_asym']
for label, beta_col in zip(FF5_LABEL, ff_betas):
    d = current.dropna(subset=[beta_col, 'ra_cur']).copy()
    X = sm.add_constant(d[[beta_col]])
    m = sm.OLS(d['ra_cur'], X).fit()
    d['ra_cur'] = m.resid.values
    # 截面回归
    d2 = d.dropna(subset=['ff5_adj_return', 'ra_cur']).copy()
    X2 = sm.add_constant(d2[['ra_cur']])
    m2 = sm.OLS(d2['ff5_adj_return'], X2).fit(cov_type='HC1')
    sig = '***' if m2.pvalues['ra_cur'] < 0.01 else '**' if m2.pvalues['ra_cur'] < 0.05 else '*' if m2.pvalues['ra_cur'] < 0.1 else ''
    print(f'  对{label}正交化后: N={len(d2)}, β={m2.params["ra_cur"]:.4f}, t={m2.tvalues["ra_cur"]:.2f}{sig}')
    # 更新current的ra_cur为残差
    current.loc[d.index, 'ra_cur'] = m.resid.values

# ========== 6. 保存 ==========
out = fund_data_pur[['fund_code', 'risk_asym', 'RA_purified_FF5',
                     'mkt_beta', 'smb_beta', 'hml_beta', 'rmw_beta', 'cma_beta',
                     'ff5_adj_return', 'log_aum', 'ff5_r2', 'n_obs']].copy()
out.to_csv(f'{DATA}/L5_认知行为层/RA因子正交纯化结果.csv', index=False, encoding='utf-8-sig')
print(f'\n已保存: 数据/ra_purification_ff5.csv ({len(out)}基金)')

# ========== 7. 关键结论 ==========
print('\n' + '='*60)
print('关键结论')
print('='*60)
print(f'原RA截面:      β={m1.params["risk_asym"]:.4f}, t={m1.tvalues["risk_asym"]:.2f}')
print(f'FF5正交化后RA: β={m3.params["RA_purified_FF5"]:.4f}, t={m3.tvalues["RA_purified_FF5"]:.2f}')
ratio = m3.params['RA_purified_FF5'] / m1.params['risk_asym'] if m1.params['risk_asym'] != 0 else 0
print(f'效应保留比例: {ratio:.1%}')
if m3.tvalues['RA_purified_FF5'] > 1.96:
    print('✅ RA携带独立于FF5因子暴露的预测信息（正交化后仍显著）')
    print(f'   论文可论证: RA不是FF5因子暴露的代理变量')
else:
    print('⚠️ RA预测力部分来自FF5因子暴露（正交化后不显著）')
    print(f'   需在论文中说明RA与因子暴露的关系')
