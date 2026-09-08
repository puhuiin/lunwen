# -*- coding: utf-8 -*-
"""
新指标构建（2026-08-25）
1) 风险转化能力：sharpe8 / sortino8（滚动8季度，与RV同窗口）
2) 认知能力候选：rc_mom（追涨杀跌，持仓变动×个股前期动量的秩相关）
输出覆盖率与描述统计，供后续进 M4 回归。
"""
import pandas as pd, numpy as np, os

BASE = r'd:\Desktop\基金经理行为分析研究'
OUT  = os.path.join(BASE, 'output')
os.makedirs(OUT, exist_ok=True)

panel = pd.read_csv(os.path.join(BASE, '指标计算流水线', 'output', '主分析面板_重建_含TOwind.csv'))
panel['report_date'] = pd.to_datetime(panel['report_date'])

# ---------- 1. 风险转化：Sharpe / Sortino（滚动8季） ----------
q = panel[['fund_code','report_date','quarter_return','rf']].drop_duplicates().sort_values(['fund_code','report_date'])
q['ex'] = q['quarter_return'] - q['rf']  # 季度超额收益

def roll_stats(g):
    g = g.sort_values('report_date')
    m  = g['ex'].rolling(8, min_periods=4).mean()
    sd = g['ex'].rolling(8, min_periods=4).std()
    g['sharpe8'] = m / sd
    dn = g['ex'].where(g['ex'] < 0)
    dd = dn.rolling(8, min_periods=4).std()
    g['sortino8'] = np.where(dd > 1e-6, m / dd, np.nan)
    return g

q = q.groupby('fund_code', group_keys=False).apply(roll_stats).reset_index(drop=True)
if 'fund_code' not in q.columns:
    q['fund_code'] = panel[['fund_code','report_date']].drop_duplicates().sort_values(['fund_code','report_date'])['fund_code'].values
risk_conv = q[['fund_code','report_date','sharpe8','sortino8']]

# ---------- 2. 认知候选：RC 追涨杀跌 ----------
hold = pd.read_csv(os.path.join(BASE, '指标计算流水线', 'data', 'L2_持仓偏离层', '基金持仓明细_全量修正版_v3.csv'))
hold['report_date'] = pd.to_datetime(hold['report_date'])
hold['hold_ratio'] = pd.to_numeric(hold['hold_ratio'], errors='coerce')
hold['stock_code'] = pd.to_numeric(hold['stock_code'], errors='coerce')
hold = hold[hold['hold_ratio'] > 0]

mret = pd.read_csv(os.path.join(BASE, 'backups', '数据', '股价行情', '个股月收益率_全量.csv'))
mret['date'] = pd.to_datetime(mret['date'])
mret = mret.sort_values(['stock_code','date'])
# 个股12个月动量（跳过最近1个月）
mret['mom'] = mret.groupby('stock_code')['monthly_return'].transform(
    lambda s: (1+s).rolling(13).apply(np.prod, raw=True)/(1+s) - 1)

# 把月动量对齐到季度报告日：取报告日前最近一个月的 mom
qdates = sorted(hold['report_date'].unique())
mdates = np.array(sorted(mret['date'].unique()))
mom_map = {}
for d in qdates:
    past = mdates[mdates <= np.datetime64(d)]
    mom_map[d] = past.max() if len(past) else None
mom_lookup = mret.set_index(['stock_code','date'])['mom']

hold['mdate'] = hold['report_date'].map(mom_map)
hold['mom'] = [mom_lookup.get((s, d), np.nan) for s, d in zip(hold['stock_code'], hold['mdate'])]

hold = hold.sort_values(['fund_code','stock_code','report_date'])
hold['w_prev'] = hold.groupby(['fund_code','stock_code'])['hold_ratio'].shift(1)
hold['dw'] = hold['hold_ratio'] - hold['w_prev']

rc_rows = []
for (fc, d), g in hold.dropna(subset=['dw','mom']).groupby(['fund_code','report_date']):
    g2 = g.dropna(subset=['mom'])
    if len(g2) >= 10 and g2['dw'].std() > 0 and g2['mom'].std() > 0:
        rc_rows.append({'fund_code': fc, 'report_date': d,
                        'rc_mom': g2['dw'].corr(g2['mom'], method='spearman'),
                        'n_stk': len(g2)})
rc = pd.DataFrame(rc_rows)
rc['report_date'] = pd.to_datetime(rc['report_date']) + pd.Timedelta(days=1)  # 季末→面板季初标签

# ---------- 覆盖率与描述统计 ----------
print('=== 覆盖率（相对主面板基金-季度观测） ===')
key = panel[['fund_code','report_date']]
for name, df in [('sharpe8/sortino8', risk_conv), ('rc_mom', rc)]:
    merged = key.merge(df, on=['fund_code','report_date'], how='left', indicator=True)
    cov = (merged['_merge'] == 'both').mean()
    print(f'{name}: 匹配观测 {int((merged["_merge"]=="both").sum())} / {len(key)} = {cov:.1%}')

desc = pd.concat([
    risk_conv[['sharpe8','sortino8']].describe().T,
    rc[['rc_mom']].describe().T], axis=0)
print(); print(desc[['count','mean','std','min','50%','max']].round(3).to_string())

risk_conv.to_csv(os.path.join(OUT, '风险转化指标_2026-08-25.csv'), index=False, encoding='utf-8-sig')
rc.to_csv(os.path.join(OUT, '认知指标_rc追涨杀跌_2026-08-25.csv'), index=False, encoding='utf-8-sig')
print(); print('已保存 output/风险转化指标_2026-08-25.csv, output/认知指标_rc追涨杀跌_2026-08-25.csv')
