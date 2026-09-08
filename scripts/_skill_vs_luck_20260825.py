# -*- coding: utf-8 -*-
"""
sharpe8_lag 技能 vs 运气剥离检验 v2（2026-08-25）
数据结构发现：面板 ff5_adj_return 对 362/约400 只基金为基金内常数（基金层alpha按季铺开），
无法做"FF5口径滚动夏普"。改用以下来源：
检验1（技能）：全样本基金层 FF5 回归残差 -> 滚动8季信息比率 ir8_lag（事后分解口径，明确标注）
检验2（行情馈赠）：DV 换 quarter_return（逐季真实变异），sharpe8_lag × 牛市哑变量交互 + 牛/熊子样本
"""
import pandas as pd, numpy as np, statsmodels.api as sm, os

BASE = r'd:\Desktop\基金经理行为分析研究'
OUT  = os.path.join(BASE, 'output')

panel = pd.read_csv(os.path.join(BASE, '指标计算流水线', 'output', '主分析面板_重建_含TOwind.csv'))
panel['report_date'] = pd.to_datetime(panel['report_date'])

q = panel[['fund_code','report_date','quarter_return','rf',
           'ff5_MKT_excess','ff5_SMB','ff5_HML','ff5_RMW','ff5_CMA']].drop_duplicates() \
     .sort_values(['fund_code','report_date'])
q['ex'] = q['quarter_return'] - q['rf']

FF5 = ['ff5_MKT_excess','ff5_SMB','ff5_HML','ff5_RMW','ff5_CMA']

def roll_sharpe(x):
    x = x.shift(1)
    return x.rolling(8, min_periods=4).mean() / x.rolling(8, min_periods=4).std()

def per_fund(g):
    g = g.sort_values('report_date').copy()
    g['sharpe8_lag'] = roll_sharpe(g['ex'])
    # 基金层全样本 FF5 回归 -> 残差（事后分解）
    d = g.dropna(subset=['ex'] + FF5)
    if len(d) >= 10 and d[FF5].std().min() > 0:
        Xf = sm.add_constant(d[FF5].astype(float))
        mf = sm.OLS(d['ex'].astype(float), Xf).fit()
        g.loc[d.index, 'ff5_resid'] = d['ex'] - mf.fittedvalues
    else:
        g['ff5_resid'] = np.nan
    g['ir8_lag'] = roll_sharpe(g['ff5_resid'])
    return g

q = q.groupby('fund_code', group_keys=False).apply(per_fund)
q = q.reset_index(drop=True)
if 'fund_code' not in q.columns:
    q['fund_code'] = panel[['fund_code','report_date']].drop_duplicates().sort_values(['fund_code','report_date'])['fund_code'].values
q = q.replace([np.inf, -np.inf], np.nan)

df = panel.merge(q[['fund_code','report_date','sharpe8_lag','ir8_lag']],
                 on=['fund_code','report_date'], how='left')
df['log_aum'] = np.log(df['avg_aum'].clip(lower=1e-9))
df['bull'] = (df['MKT_excess'] > 0).astype(float)

print('>>> 覆盖率: sharpe8_lag %.1f%%  ir8_lag %.1f%%  两口径相关 %.3f' % (
    df['sharpe8_lag'].notna().mean()*100, df['ir8_lag'].notna().mean()*100,
    df[['sharpe8_lag','ir8_lag']].corr().iloc[0,1]))
print('>>> 牛市季占比 %.1f%%' % (df['bull'].mean()*100))

CTRL = ['mgr_total_tenure_v2','log_fund_age','log_aum']
OLD9 = ['risk_asym','de','lsv','ICI','AS_improved','ISDI','ARG','return_volatility','TO_wind']

def winsor(s, p=0.01):
    lo, hi = s.quantile(p), s.quantile(1-p)
    return s.clip(lo, hi)

def fit(data, dv, rhs, tag, show=None):
    d = data[[dv,'fund_code','year'] + rhs + CTRL].dropna()
    y = winsor(d[dv])
    X = sm.add_constant(d[rhs + CTRL].astype(float))
    X = X.join(pd.get_dummies(d['year'], prefix='y', drop_first=True).astype(float))
    m = sm.OLS(y, X).fit(cov_type='cluster', cov_kwds={'groups': d['fund_code']})
    print(f'\n=== {tag}  N={len(d)}  R2={m.rsquared:.3f} ===')
    for v in (show or rhs):
        b,t,p = m.params[v], m.tvalues[v], m.pvalues[v]
        star = '***' if p<0.01 else ('**' if p<0.05 else ('*' if p<0.1 else ''))
        print(f'  {v:24s} {b:+.4f} ({t:+.2f}){star}')
    return m

# R1 基准复核（毛收益口径夏普 -> 基金层alpha DV）
fit(df, 'ff5_adj_return', OLD9 + ['sharpe8_lag'], 'R1 基准复核：M4 + sharpe8_lag', show=['sharpe8_lag'])

# 检验1：FF5残差信息比率（纯技能口径）
fit(df, 'ff5_adj_return', OLD9 + ['ir8_lag'], 'R2 技能检验：M4 + ir8_lag（FF5残差IR）', show=['ir8_lag'])
fit(df, 'ff5_adj_return', OLD9 + ['sharpe8_lag','ir8_lag'], 'R3 两口径同入',
    show=['sharpe8_lag','ir8_lag'])

# 检验2：行情馈赠（DV=quarter_return 逐季变异）
df['s8Xbull'] = df['sharpe8_lag'] * df['bull']
fit(df, 'quarter_return', ['sharpe8_lag','s8Xbull'], 'R4 牛熊交互（DV=当季收益, bull主效应被yearFE吸收）',
    show=['sharpe8_lag','s8Xbull'])
for st, lab in [(1,'牛市季'), (0,'熊市季')]:
    fit(df[df['bull']==st], 'quarter_return', ['sharpe8_lag'], f'R5 子样本：仅{lab}', show=['sharpe8_lag'])

# R5b 前向对照：sharpe8_lag / ir8_lag -> 下季收益
fit(df, 'future_return', ['sharpe8_lag','ir8_lag'], 'R5b 前向：下一季收益', show=['sharpe8_lag','ir8_lag'])

# ================= R6 分半样本外检验（决定性问题）====================
# sharpe 用前半段估计、alpha 用后半段 FF5 重新估计，两窗口不相交 -> 彻底排除机械重叠
print('\n\n================ R6 分半样本外检验 ================')
rows = []
for fc, g in panel[['fund_code','report_date','quarter_return','rf','avg_aum',
                    'mgr_total_tenure_v2','log_fund_age'] + FF5].dropna(
                    subset=['quarter_return','rf'] + FF5).sort_values(
                    ['fund_code','report_date']).groupby('fund_code'):
    n = len(g)
    if n < 12:
        continue
    h = n // 2
    g1, g2 = g.iloc[:h], g.iloc[h:]
    if len(g1) < 6 or len(g2) < 6:
        continue
    ex1 = g1['quarter_return'] - g1['rf']
    if ex1.std() < 1e-9:
        continue
    s_first = ex1.mean() / ex1.std()
    # 前半段 FF5 残差 IR
    Xf1 = sm.add_constant(g1[FF5].astype(float)); m1 = sm.OLS(ex1.astype(float), Xf1).fit()
    r1 = ex1 - m1.fittedvalues
    ir_first = r1.mean() / r1.std() if r1.std() > 1e-9 else np.nan
    # 后半段 FF5 alpha（季度化）
    ex2 = g2['quarter_return'] - g2['rf']
    Xf2 = sm.add_constant(g2[FF5].astype(float)); m2 = sm.OLS(ex2.astype(float), Xf2).fit()
    rows.append({'fund_code': fc, 'alpha_2nd': m2.params['const'],
                 'sharpe_1st': s_first, 'ir_1st': ir_first,
                 'log_aum': np.log(g['avg_aum'].clip(lower=1e-9)).mean(),
                 'mgr_total_tenure_v2': g['mgr_total_tenure_v2'].mean(),
                 'log_fund_age': g['log_fund_age'].mean()})
halves = pd.DataFrame(rows)
print('分半成功基金数:', len(halves))
print('sharpe_1st 与 alpha_2nd 截面相关: %.3f (Pearson) / %.3f (Spearman)' % (
    halves['sharpe_1st'].corr(halves['alpha_2nd']),
    halves['sharpe_1st'].corr(halves['alpha_2nd'], method='spearman')))
for x in ['sharpe_1st','ir_1st']:
    d = halves.dropna(subset=[x,'alpha_2nd','mgr_total_tenure_v2','log_fund_age','log_aum'])
    Xd = sm.add_constant(d[[x,'mgr_total_tenure_v2','log_fund_age','log_aum']].astype(float))
    md = sm.OLS(winsor(d['alpha_2nd']), Xd).fit(cov_type='HC3')
    b,t,p = md.params[x], md.tvalues[x], md.pvalues[x]
    star = '***' if p<0.01 else ('**' if p<0.05 else ('*' if p<0.1 else ''))
    print(f'  R6 样本外: alpha_后半段 ~ {x}:  {b:+.4f} ({t:+.2f}){star}   N={len(d)}  R2={md.rsquared:.3f}')

halves.to_csv(os.path.join(OUT, '分半样本外检验_2026-08-25.csv'), index=False, encoding='utf-8-sig')
