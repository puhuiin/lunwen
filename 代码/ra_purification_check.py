# -*- coding: utf-8 -*-
"""
RA构念纯化核对：在同一N≈288样本上对比三种正交化
1. HM择时系数正交化（复现§4.4.5，应t仍显著）
2. SMB beta正交化（我的发现，应t消失）
3. HM择时+SMB正交化（看SMB是否仍吃掉预测力）
同时核对原RA系数差异（§4.4.5=0.173 vs 我=0.112）
"""
import pandas as pd
import numpy as np
import statsmodels.api as sm
import warnings
warnings.filterwarnings('ignore')

DATA = r'D:\Desktop\基金经理行为分析研究\数据'
FF5 = ['ff5_MKT_excess', 'ff5_SMB', 'ff5_HML', 'ff5_RMW', 'ff5_CMA']

panel = pd.read_csv(f'{DATA}/L4_风险应对层/预处理面板_v20_诊断用.csv')
panel['fund_code'] = panel['fund_code'].astype(str).str.strip().str.zfill(6)

# ========== 1. 计算HM择时系数和FF5 beta（需≥16期，对齐§4.4.5）==========
def calc_betas(g, fund_code, min_obs=16):
    g = g.dropna(subset=['quarter_return', 'ff5_MKT_excess'] + FF5)
    if len(g) < min_obs:
        return None
    y = g['quarter_return']
    # HM择时: r = a + b1*MKT + b2*max(MKT,0) + e
    mkt = g['ff5_MKT_excess']
    X_hm = sm.add_constant(pd.DataFrame({'MKT': mkt, 'MKT_up': mkt.clip(lower=0)}))
    try:
        m_hm = sm.OLS(y, X_hm).fit()
        hm_timing = m_hm.params.get('MKT_up', np.nan)
    except Exception:
        hm_timing = np.nan
    # FF5 beta
    X_ff5 = sm.add_constant(g[FF5])
    try:
        m_ff5 = sm.OLS(y, X_ff5).fit()
        return {
            'fund_code': fund_code,
            'n_obs': len(g),
            'hm_timing': hm_timing,
            'mkt_beta': m_ff5.params.get('ff5_MKT_excess', np.nan),
            'smb_beta': m_ff5.params.get('ff5_SMB', np.nan),
            'hml_beta': m_ff5.params.get('ff5_HML', np.nan),
            'rmw_beta': m_ff5.params.get('ff5_RMW', np.nan),
            'cma_beta': m_ff5.params.get('ff5_CMA', np.nan),
        }
    except Exception:
        return None

print('计算HM择时系数+FF5 beta（≥16期，对齐§4.4.5）...')
betas_list = []
for fc, g in panel.groupby('fund_code'):
    r = calc_betas(g, fc, min_obs=16)
    if r is not None:
        betas_list.append(r)
betas_df = pd.DataFrame(betas_list)
print(f'成功: {len(betas_df)}基金')

# 基金层面
fund_ra = panel.groupby('fund_code').agg({
    'risk_asym': 'mean', 'ff5_adj_return': 'mean', 'log_aum': 'mean',
}).reset_index()
fund_data = fund_ra.merge(betas_df, on='fund_code', how='inner').dropna(subset=['risk_asym'])
print(f'基金层面(有RA+择时+FF5 beta): {len(fund_data)}基金')

# ========== 2. 截面回归辅助函数 ==========
def xsec(df, ra_col, label, controls=None):
    cols = [ra_col] + (controls or [])
    d = df.dropna(subset=cols + ['ff5_adj_return', 'log_aum'])
    X = sm.add_constant(d[cols + ['log_aum']])
    m = sm.OLS(d['ff5_adj_return'], X).fit(cov_type='HC1')
    t = m.tvalues[ra_col]; b = m.params[ra_col]; p = m.pvalues[ra_col]
    sig = '***' if p < 0.01 else '**' if p < 0.05 else '*' if p < 0.1 else ''
    print(f'  {label}: N={len(d)}, β={b:.4f}, t={t:.2f}{sig}')
    return m

# ========== 3. 核对原RA系数差异 ==========
print('\n=== 核对原RA系数（控制log_aum）===')
# 全样本(N=343档)
xsec(fund_data, 'risk_asym', '原RA(N=全样本)')
# 限制到有hm_timing的样本
d288 = fund_data.dropna(subset=['hm_timing']).copy()
print(f'  有hm_timing的基金: {len(d288)}')
xsec(d288, 'risk_asym', '原RA(N=有择时系数)')

# ========== 4. 三种正交化对比（同一N≈288样本）==========
print(f'\n=== 三种正交化对比（同一N={len(d288)}样本）===')

# (a) 原RA基准
xsec(d288, 'risk_asym', '基准:原RA')

# (b) 对HM择时正交化（复现§4.4.5）
d = d288.dropna(subset=['hm_timing']).copy()
X = sm.add_constant(d[['hm_timing']])
d['RA_orth_HM'] = sm.OLS(d['risk_asym'], X).fit().resid
d288 = d288.merge(d[['fund_code', 'RA_orth_HM']], on='fund_code', how='left')
xsec(d288, 'RA_orth_HM', '对HM择时正交化(§4.4.5方法)')

# (c) 对SMB正交化
d = d288.dropna(subset=['smb_beta']).copy()
X = sm.add_constant(d[['smb_beta']])
d['RA_orth_SMB'] = sm.OLS(d['risk_asym'], X).fit().resid
d288 = d288.merge(d[['fund_code', 'RA_orth_SMB']], on='fund_code', how='left')
xsec(d288, 'RA_orth_SMB', '对SMB正交化(我的发现)')

# (d) 对HM择时+SMB正交化
d = d288.dropna(subset=['hm_timing', 'smb_beta']).copy()
X = sm.add_constant(d[['hm_timing', 'smb_beta']])
d['RA_orth_HM_SMB'] = sm.OLS(d['risk_asym'], X).fit().resid
d288 = d288.merge(d[['fund_code', 'RA_orth_HM_SMB']], on='fund_code', how='left')
xsec(d288, 'RA_orth_HM_SMB', '对HM择时+SMB正交化')

# (e) 对完整FF5正交化
d = d288.dropna(subset=['mkt_beta','smb_beta','hml_beta','rmw_beta','cma_beta']).copy()
X = sm.add_constant(d[['mkt_beta','smb_beta','hml_beta','rmw_beta','cma_beta']])
d['RA_orth_FF5'] = sm.OLS(d['risk_asym'], X).fit().resid
d288 = d288.merge(d[['fund_code', 'RA_orth_FF5']], on='fund_code', how='left')
xsec(d288, 'RA_orth_FF5', '对完整FF5正交化')

# ========== 5. RA与各beta的相关性 ==========
print('\n=== RA与各beta的基金层面相关系数 ===')
for col in ['hm_timing','mkt_beta','smb_beta','hml_beta','rmw_beta','cma_beta']:
    r = d288['risk_asym'].corr(d288[col])
    print(f'  RA ~ {col}: r={r:.3f}')

# ========== 6. 关键结论 ==========
print('\n' + '='*60)
print('核对结论')
print('='*60)
print(f'§4.4.5原RA(N=288): β≈0.173, t≈5.88 (论文报告)')
print(f'本次原RA(N={len(d288)}): 见上方基准')
print()
print('关键问题: HM择时正交化后RA是否仍显著(复现§4.4.5)?')
print('         SMB正交化后RA是否消失(我的发现)?')
print('         两者同时正交化后RA如何?')
