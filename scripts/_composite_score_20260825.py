# -*- coding: utf-8 -*-
"""
六维能力等权复合打分（2026-08-25）
维度成分（用户确认方案 2026-08-25）：
  配置力   alloc   = [ z(ICI) + z(-ISDI) ] / 2
  风险应对 risk_rsp = z(RA)
  风险转化 risk_cnv = z(sharpe8_lag)
  主动收益 active   = [ z(ARG) + z(RG) ] / 2
  纪律性   discipl  = [ z(-de) + z(-rc_mom) ] / 2
  成本控制 cost     = z(-TO_wind)
流程：面板 -> 基金层时序均值 -> 横截面z -> 等权复合（缺失成分跳过重归一）
同时输出：按基金平均ff5_adj_return分Top5%/Bottom5%的六维对比（群体画像证据）
"""
import pandas as pd, numpy as np, os

BASE = r'd:\Desktop\基金经理行为分析研究'
OUT  = os.path.join(BASE, 'output')

panel = pd.read_csv(os.path.join(BASE, '指标计算流水线', 'output', '主分析面板_重建_含TOwind.csv'))
panel['report_date'] = pd.to_datetime(panel['report_date'])
new = pd.read_csv(os.path.join(OUT, '新增指标面板_2026-08-25.csv'), parse_dates=['report_date'])
df = panel.merge(new[['fund_code','report_date','sharpe8_lag','rc_mom']], on=['fund_code','report_date'], how='left')

print('RG 覆盖率: %.1f%%  TO_wind 覆盖率: %.1f%%' % (
    df['RG'].notna().mean()*100, df['TO_wind'].notna().mean()*100))

# 基金层时序均值
cols = ['ICI','ISDI','risk_asym','sharpe8_lag','ARG','RG','de','rc_mom','TO_wind','ff5_adj_return','quarter_return']
fm = df.groupby('fund_code')[cols].mean()

def z(s):
    return (s - s.mean()) / s.std()

def ew(*zs):
    """等权复合：缺失成分跳过并按可用数重归一"""
    arr = pd.concat(zs, axis=1)
    return arr.sum(axis=1, skipna=True) / arr.notna().sum(axis=1)

fm['alloc']    = ew(z(fm['ICI']), z(-fm['ISDI']))
fm['risk_rsp'] = z(fm['risk_asym'])
fm['risk_cnv'] = z(fm['sharpe8_lag'])
fm['active']   = ew(z(fm['ARG']), z(fm['RG']))
fm['discipl']  = ew(z(-fm['de']), z(-fm['rc_mom']))
fm['cost']     = z(-fm['TO_wind'])

dims = ['alloc','risk_rsp','risk_cnv','active','discipl','cost']
fm['composite'] = ew(*[fm[d] for d in dims])

# 覆盖统计
print('\n各维度得分非缺失基金数（共%d只）:' % len(fm))
for d in dims:
    print('  %-8s %d' % (d, fm[d].notna().sum()))

# 群体画像：按基金平均 ff5 alpha 分 Top/Bottom 5%
fm2 = fm.dropna(subset=['ff5_adj_return'])
n5 = max(1, int(np.ceil(len(fm2)*0.05)))
top = fm2.nlargest(n5, 'ff5_adj_return')
bot = fm2.nsmallest(n5, 'ff5_adj_return')
print(f'\n=== 群体画像：最好5%（{n5}只） vs 最差5%（{n5}只） 六维得分均值 ===')
comp = pd.DataFrame({'Top5%': top[dims].mean(), 'Bottom5%': bot[dims].mean()})
comp['差值'] = comp['Top5%'] - comp['Bottom5%']
print(comp.round(3).to_string())

fm.reset_index().to_csv(os.path.join(OUT, '六维能力复合得分_2026-08-25.csv'), index=False, encoding='utf-8-sig')
print('\n已保存 output/六维能力复合得分_2026-08-25.csv')
