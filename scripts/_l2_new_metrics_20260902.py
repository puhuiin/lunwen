# -*- coding: utf-8 -*-
"""认知层新增候选指标（2026-09-02）
从文件夹内已有文献 + 已有数据出发，构造四个新的认知偏差候选指标：

1. house_money 私房钱效应（池丽旭、庄新田 2011《管理科学学报》）
   前期盈利后是否加大风险暴露：I(上季收益>0) × 本季持仓集中度变化
2. anchor_high 锚定/最高价效应（池丽旭、庄新田 2011；Grinblatt & Han 2005）
   持仓个股现价相对其滚动最高价的位置，持仓加权 —— 锚定越强，越倾向持有"离高点远"的股票
3. cgo 资本利得悬垂（Grinblatt & Han 2005, JFE）
   g = (P − RefP)/RefP，参考价用持仓期加权均价代理，持仓加权
4. bhm_shm 买卖羊群不对称（Wermers 1999；李奇泽等 2013）
   买入羊群度 − 卖出羊群度，测"跟买"与"跟卖"的方向性差异

输出 output/L2新增候选_2026-09-02.csv 与 .json（含单变量回归）
"""
import json, os
import numpy as np, pandas as pd
import statsmodels.api as sm

BASE = r'd:\Desktop\基金经理行为分析研究'
OUT = os.path.join(BASE, 'output')
PIPE = os.path.join(BASE, '指标计算流水线')
L2D = os.path.join(PIPE, 'data', 'L2_持仓偏离层')
CTRL = ['mgr_total_tenure_v2', 'log_fund_age', 'log_aum']

hold = pd.read_csv(os.path.join(L2D, '基金持仓明细_全量修正版_v3.csv'), low_memory=False)
hold['report_date'] = pd.to_datetime(hold['report_date'], errors='coerce')
for c in ['hold_ratio', 'hold_value', 'hold_shares']:
    hold[c] = pd.to_numeric(hold[c], errors='coerce')
hold = hold.dropna(subset=['report_date', 'stock_code', 'hold_ratio'])
hold['stock_code'] = pd.to_numeric(hold['stock_code'], errors='coerce')
hold = hold.dropna(subset=['stock_code'])
hold['stock_code'] = hold['stock_code'].astype(int)

mret = pd.read_csv(os.path.join(PIPE, 'data', '股价行情', '个股月收益率_全量.csv'))
mret['date'] = pd.to_datetime(mret['date'], errors='coerce')
mret = mret.dropna(subset=['date', 'stock_code', 'monthly_return'])
mret['stock_code'] = pd.to_numeric(mret['stock_code'], errors='coerce').astype('Int64')

panel = pd.read_csv(os.path.join(OUT, '分析面板_v3_2026-08-26.csv'), parse_dates=['report_date'])

# ---------- 由月收益重建个股累计净值（用于最高价与参考价代理） ----------
mret = mret.sort_values(['stock_code', 'date'])
mret['nav'] = mret.groupby('stock_code')['monthly_return'].transform(
    lambda s: (1 + s.fillna(0)).cumprod())
mret['nav_max36'] = mret.groupby('stock_code')['nav'].transform(
    lambda s: s.rolling(36, min_periods=6).max())
# 参考价代理：过去 12 个月 nav 均值（成本基础代理，Grinblatt & Han 用换手加权，此处等权近似）
mret['nav_ref12'] = mret.groupby('stock_code')['nav'].transform(
    lambda s: s.rolling(12, min_periods=4).mean())
snap = mret[['stock_code', 'date', 'nav', 'nav_max36', 'nav_ref12']].copy()
snap['ym'] = snap['date'].dt.to_period('M')

hold['ym'] = hold['report_date'].dt.to_period('M')
hd = hold.merge(snap.drop(columns='date'), on=['stock_code', 'ym'], how='left')
print('持仓匹配行情比例 %.1f%%' % (100 * hd['nav'].notna().mean()))

hd['w'] = hd['hold_ratio'] / 100.0
# 锚定：现价距滚动最高价的相对位置（1 = 就在高点，越小越远离高点）
hd['pos_high'] = hd['nav'] / hd['nav_max36']
# 资本利得悬垂 CGO
hd['cgo_i'] = (hd['nav'] - hd['nav_ref12']) / hd['nav_ref12']


def wmean(g, col):
    m = g[col].notna() & g['w'].notna()
    if m.sum() == 0 or g.loc[m, 'w'].sum() <= 0:
        return np.nan
    return float(np.average(g.loc[m, col], weights=g.loc[m, 'w']))


hd['year'] = hd['report_date'].dt.year
hd['quarter'] = hd['report_date'].dt.quarter
agg = hd.groupby(['fund_code', 'year', 'quarter']).apply(
    lambda g: pd.Series({'anchor_high': wmean(g, 'pos_high'), 'cgo': wmean(g, 'cgo_i')}),
    include_groups=False).reset_index()
print('anchor_high 覆盖 %d 行；cgo 覆盖 %d 行' % (agg['anchor_high'].notna().sum(), agg['cgo'].notna().sum()))
agg.to_csv(os.path.join(OUT, '_l2new_holdlevel_2026-09-02.csv'), index=False, encoding='utf-8-sig')

# ---------- house_money 私房钱效应 ----------
# 池丽旭、庄新田(2011)：前期盈利后加大风险暴露。用「上季超额收益>0」× 本季风险暴露上升
p = panel.sort_values(['fund_code', 'report_date']).copy()
p['ret_prev'] = p.groupby('fund_code')['quarter_return'].shift(1)
p['vol_chg'] = p.groupby('fund_code')['return_volatility'].diff()
p['house_money'] = np.where(p['ret_prev'].notna() & p['vol_chg'].notna(),
                            (p['ret_prev'] > 0).astype(float) * p['vol_chg'], np.nan)

# ---------- bhm_shm 买卖羊群不对称（Wermers 1999） ----------
# 用持仓比例变动方向定义买/卖；对每个股票-季度算买方占比 p，再算 BHM 与 SHM
hd2 = hold[['fund_code', 'report_date', 'stock_code', 'hold_ratio']].copy()
hd2 = hd2.sort_values(['fund_code', 'stock_code', 'report_date'])
hd2['d'] = hd2.groupby(['fund_code', 'stock_code'])['hold_ratio'].diff()
hd2 = hd2.dropna(subset=['d'])
hd2 = hd2[hd2['d'].abs() > 1e-9]
hd2['buy'] = (hd2['d'] > 0).astype(int)

st = hd2.groupby(['report_date', 'stock_code']).agg(B=('buy', 'sum'), N=('buy', 'size')).reset_index()
st = st[st['N'] >= 5]
st['pi'] = st['B'] / st['N']
ep = st.groupby('report_date').apply(lambda g: g['B'].sum() / g['N'].sum(), include_groups=False)
st['Ep'] = st['report_date'].map(ep)
# AF：无羊群零假设下 |p−E[p]| 的期望，用二项分布模拟
from scipy.stats import binom
def af(n, q):
    k = np.arange(0, n + 1)
    return float(np.sum(binom.pmf(k, n, q) * np.abs(k / n - q)))
st['AF'] = [af(int(n), float(q)) for n, q in zip(st['N'], st['Ep'])]
st['HM'] = (st['pi'] - st['Ep']).abs() - st['AF']
st['BHM'] = np.where(st['pi'] > st['Ep'], st['HM'], np.nan)
st['SHM'] = np.where(st['pi'] < st['Ep'], st['HM'], np.nan)

j = hd2.merge(st[['report_date', 'stock_code', 'BHM', 'SHM']], on=['report_date', 'stock_code'], how='inner')
j['year'] = j['report_date'].dt.year
j['quarter'] = j['report_date'].dt.quarter
fh = j.groupby(['fund_code', 'year', 'quarter']).agg(
    bhm=('BHM', 'mean'), shm=('SHM', 'mean')).reset_index()
fh['bhm_shm'] = fh['bhm'].fillna(0) - fh['shm'].fillna(0)
print('bhm_shm 覆盖 %d 行 / %d 基金' % (len(fh), fh['fund_code'].nunique()))

# ---------- 合并进面板并跑单变量回归 ----------
NEW = ['anchor_high', 'cgo', 'house_money', 'bhm_shm']
p = p.merge(agg, on=['fund_code', 'year', 'quarter'], how='left')
p = p.merge(fh[['fund_code', 'year', 'quarter', 'bhm_shm']], on=['fund_code', 'year', 'quarter'], how='left')
p.to_csv(os.path.join(OUT, 'L2新增候选_面板_2026-09-02.csv'), index=False, encoding='utf-8-sig')

winsor = lambda s, q=0.01: s.clip(s.quantile(q), s.quantile(1 - q))
fm = p.groupby('fund_code')[NEW + CTRL + ['ff5_adj_return']].mean().dropna(subset=['ff5_adj_return'])
res = {'覆盖率_基金层': {}, '单变量回归': {}, '与现有认知成分相关': {}}
for c in NEW:
    res['覆盖率_基金层'][c] = round(float(fm[c].notna().mean()), 4)

for c in NEW:
    dd = fm[[c, 'ff5_adj_return'] + CTRL].dropna()
    if len(dd) < 40:
        res['单变量回归'][c] = {'n': len(dd), 'note': 'insufficient'}
        continue
    for k in [c, 'ff5_adj_return'] + CTRL:
        dd[k] = winsor(dd[k])
    m = sm.OLS(dd['ff5_adj_return'], sm.add_constant(dd[[c] + CTRL])).fit(cov_type='HC1')
    res['单变量回归'][c] = dict(n=int(m.nobs), b=round(float(m.params[c]), 6),
                            t=round(float(m.tvalues[c]), 2), p=round(float(m.pvalues[c]), 4),
                            r2=round(float(m.rsquared), 4))

old = pd.read_csv(os.path.join(OUT, '指标面板_v2_2026-08-26.csv'), parse_dates=['report_date'])
base = panel.groupby('fund_code')[['risk_asym', 'de', 'oc_conf']].mean()
cmp = fm[NEW].join(base)
res['与现有认知成分相关'] = json.loads(cmp.corr().round(3).loc[NEW, ['risk_asym', 'de', 'oc_conf']].to_json())

print('\n=== 新增候选：基金层覆盖率与单变量回归（DV=FF5 alpha，HC1，含三控制） ===')
for c in NEW:
    v = res['单变量回归'][c]
    cov = res['覆盖率_基金层'][c]
    if 'coef' in v or 't' in v:
        print('  %-13s 覆盖 %5.1f%%  n=%3d  b=%+.6f  t=%+6.2f  p=%.4f' %
              (c, cov * 100, v['n'], v['b'], v['t'], v['p']))
    else:
        print('  %-13s 覆盖 %5.1f%%  %s' % (c, cov * 100, v))
print('\n=== 与现有认知层成分的相关性 ===')
print(cmp.corr().round(3).loc[NEW, ['risk_asym', 'de', 'oc_conf']].to_string())

with open(os.path.join(OUT, 'L2新增候选_2026-09-02.json'), 'w', encoding='utf-8') as f:
    json.dump(res, f, ensure_ascii=False, indent=1)
print('\n已保存 output/L2新增候选_2026-09-02.json')
