# -*- coding: utf-8 -*-
"""
六维复合权重敏感性检验（2026-08-25）
对三个双成分维度（配置力/主动收益/纪律性），用横截面 PCA 第一主成分载荷替代等权(0.5,0.5)，
比较：1) 各维度得分等级相关  2) 综合分排名相关  3) Top/Bottom 5% 群体区分度差异
PCA 手写 SVD，不依赖 sklearn。
"""
import pandas as pd, numpy as np, os

BASE = r'd:\Desktop\基金经理行为分析研究'
OUT  = os.path.join(BASE, 'output')

panel = pd.read_csv(os.path.join(BASE, '指标计算流水线', 'output', '主分析面板_重建_含TOwind.csv'))
panel['report_date'] = pd.to_datetime(panel['report_date'])
new = pd.read_csv(os.path.join(OUT, '新增指标面板_2026-08-25.csv'), parse_dates=['report_date'])
df = panel.merge(new[['fund_code','report_date','sharpe8_lag','rc_mom']], on=['fund_code','report_date'], how='left')

cols = ['ICI','ISDI','risk_asym','sharpe8_lag','ARG','RG','de','rc_mom','TO_wind','ff5_adj_return']
fm = df.groupby('fund_code')[cols].mean()

def z(s): return (s - s.mean()) / s.std()

def pca_dim(x1, x2, name):
    """双变量 PCA 第一主成分载荷（符号对齐到与成分正相关），返回载荷与得分"""
    d = pd.concat([x1, x2], axis=1).dropna()
    M = d.values
    C = np.cov(M.T)
    w, V = np.linalg.eigh(C)          # 升序
    v = V[:, -1]                       # 第一主成分载荷
    # 符号约定：载荷和为正（与两成分同向）
    if v.sum() < 0: v = -v
    sc = pd.Series(M @ v, index=d.index)
    print(f'  {name}: PCA载荷=({v[0]:+.3f}, {v[1]:+.3f})  PC1解释方差={w[-1]/w.sum()*100:.1f}%  (等权=(+0.500, +0.500))')
    return (sc - sc.mean()) / sc.std(), v

def ew(*zs):
    arr = pd.concat(zs, axis=1)
    return arr.sum(axis=1, skipna=True) / arr.notna().sum(axis=1)

# ---------- 等权（基准方案） ----------
fm['alloc_ew']   = ew(z(fm['ICI']), z(-fm['ISDI']))
fm['active_ew']  = ew(z(fm['ARG']), z(fm['RG']))
fm['discipl_ew'] = ew(z(-fm['de']), z(-fm['rc_mom']))

# ---------- PCA 加权 ----------
print('=== 双成分维度 PCA 第一主成分载荷 vs 等权 ===')
fm['alloc_pc'], _   = pca_dim(z(fm['ICI']), z(-fm['ISDI']),  '配置力  [ICI, -ISDI]')
fm['active_pc'], _  = pca_dim(z(fm['ARG']), z(fm['RG']),     '主动收益 [ARG, RG]')
fm['discipl_pc'], _ = pca_dim(z(-fm['de']), z(-fm['rc_mom']),'纪律性  [-de, -rc]')

# 三个单指标维度不变
for d0 in ['risk_rsp','risk_cnv','cost']:
    pass
fm['risk_rsp'] = z(fm['risk_asym'])
fm['risk_cnv'] = z(fm['sharpe8_lag'])
fm['cost']     = z(-fm['TO_wind'])

fm['composite_ew'] = ew(fm['alloc_ew'],fm['risk_rsp'],fm['risk_cnv'],fm['active_ew'],fm['discipl_ew'],fm['cost'])
fm['composite_pc'] = ew(fm['alloc_pc'],fm['risk_rsp'],fm['risk_cnv'],fm['active_pc'],fm['discipl_pc'],fm['cost'])

print('\n=== 等权 vs PCA：得分等级相关（Spearman）与方向一致率 ===')
for a, b, lab in [('alloc_ew','alloc_pc','配置力'), ('active_ew','active_pc','主动收益'),
                  ('discipl_ew','discipl_pc','纪律性'), ('composite_ew','composite_pc','六维综合分')]:
    d = fm[[a,b]].dropna()
    rho = d[a].corr(d[b], method='spearman')
    # 方向一致率：两组各自 z 分数同号比例
    samesign = (np.sign(d[a]) == np.sign(d[b])).mean()
    print(f'  {lab:8s}: rho={rho:.3f}  方向一致率={samesign*100:.1f}%  N={len(d)}')

# Top/Bottom 5% 群体区分度（按基金平均 ff5 alpha 分组，两套权重对比）
fm2 = fm.dropna(subset=['ff5_adj_return'])
n5 = max(1, int(np.ceil(len(fm2)*0.05)))
top = fm2.nlargest(n5, 'ff5_adj_return'); bot = fm2.nsmallest(n5, 'ff5_adj_return')
print(f'\n=== Top5% vs Bottom5%（各{n5}只）群体区分度：等权 vs PCA ===')
print('%-10s %10s %10s' % ('维度','等权差值','PCA差值'))
for ew_c, pc_c, lab in [('alloc_ew','alloc_pc','配置力'), ('active_ew','active_pc','主动收益'),
                        ('discipl_ew','discipl_pc','纪律性')]:
    d_ew = top[ew_c].mean() - bot[ew_c].mean()
    d_pc = top[pc_c].mean() - bot[pc_c].mean()
    print('%-10s %+10.3f %+10.3f' % (lab, d_ew, d_pc))

out = fm.reset_index()[['fund_code','composite_ew','composite_pc','alloc_ew','alloc_pc',
                        'active_ew','active_pc','discipl_ew','discipl_pc']]
out.to_csv(os.path.join(OUT, '权重敏感性对比_2026-08-25.csv'), index=False, encoding='utf-8-sig')
print('\n已保存 output/权重敏感性对比_2026-08-25.csv')
