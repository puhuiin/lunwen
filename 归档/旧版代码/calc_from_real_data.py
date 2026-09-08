#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""用真实下载数据计算Active Share和Return Gap"""
import pandas as pd
import numpy as np
import os

data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '数据')

# ============================================================
# 1. Active Share 计算
# ============================================================
print("=" * 60)
print("真实数据 Active Share 计算")
print("=" * 60)

holdings = pd.read_csv(os.path.join(data_dir, 'fund_holdings.csv'))
idx300 = pd.read_csv(os.path.join(data_dir, 'index_000300_constituents.csv'))
idx300['weight'] = 1.0 / len(idx300)  # 等权近似

print(f"\n注意: AKShare仅提供前十大重仓股，AS会偏高")
print(f"      精确AS需半年报全持仓数据(Wind/CSMAR)\n")

def parse_quarter(q):
    q = str(q)
    year = q[:4]
    q_num = q[5] if '季度' in q else '?'
    return f"{year}Q{q_num}"

holdings['quarter_label'] = holdings['report_period'].apply(parse_quarter)

results = []
for fund_code in holdings['fund_code'].unique():
    fund_data = holdings[holdings['fund_code'] == fund_code]
    for period in sorted(fund_data['report_period'].unique()):
        h = fund_data[fund_data['report_period'] == period]
        fund = h[['stock_code', 'hold_ratio']].copy()
        fund['hold_ratio'] = fund['hold_ratio'] / 100
        fund.columns = ['stock_code', 'w_fund']
        bench = idx300[['stock_code', 'weight']].copy()
        bench.columns = ['stock_code', 'w_bench']
        merged = pd.merge(fund, bench, on='stock_code', how='outer').fillna(0)
        as_val = 0.5 * (merged['w_fund'] - merged['w_bench']).abs().sum()
        as_val = min(as_val, 1.0)
        overlap = len(fund[fund['stock_code'].isin(bench['stock_code'])])
        results.append({
            'fund_code': fund_code,
            'period': parse_quarter(period),
            'active_share': round(as_val, 4),
            'n_holdings': len(h),
            'n_in_benchmark': overlap
        })

df_as = pd.DataFrame(results)
print(df_as.to_string(index=False))
print(f"\nAS均值: {df_as['active_share'].mean():.4f}")
print(f"AS标准差: {df_as['active_share'].std():.4f}")
df_as.to_csv(os.path.join(data_dir, 'active_share_results.csv'), index=False)
print(f"结果已保存: active_share_results.csv")

# ============================================================
# 2. Return Gap 计算
# ============================================================
print("\n" + "=" * 60)
print("真实数据 Return Gap 计算")
print("=" * 60)

nav = pd.read_csv(os.path.join(data_dir, 'fund_nav.csv'))
nav['date'] = pd.to_datetime(nav['date'])
stock_ret = pd.read_csv(os.path.join(data_dir, 'stock_monthly_returns.csv'))
stock_ret['date'] = pd.to_datetime(stock_ret['date'])

# 透视: 行=日期, 列=股票代码
ret_pivot = stock_ret.pivot(index='date', columns='stock_code', values='monthly_return')

# 季度到月份映射
def quarter_to_months(quarter_label):
    """2020Q1 -> ['2020-01-31', '2020-02-28', '2020-03-31']"""
    year = int(quarter_label[:4])
    q = int(quarter_label[-1])
    months = []
    for m in [(q-1)*3+1, (q-1)*3+2, (q-1)*3+3]:
        try:
            months.append(pd.Timestamp(year=year, month=m, day=1) + pd.offsets.MonthEnd(0))
        except:
            pass
    return months

# 上一个季度的持仓用于计算当前季度的RG
all_rg = []

for fund_code in holdings['fund_code'].unique():
    fund_hold = holdings[holdings['fund_code'] == fund_code].copy()
    fund_nav = nav[nav['fund_code'] == fund_code].copy()
    
    if fund_nav.empty:
        continue
    
    # 计算基金月度收益
    fund_nav['year_month'] = fund_nav['date'].dt.to_period('M')
    fund_monthly = fund_nav.groupby('year_month')['daily_return'].apply(
        lambda x: (1 + x.astype(float) / 100).prod() - 1
    ).reset_index()
    fund_monthly.columns = ['year_month', 'r_fund']
    fund_monthly['date'] = fund_monthly['year_month'].dt.to_timestamp() + pd.offsets.MonthEnd(0)
    
    # 获取该基金所有季度持仓
    quarters = sorted(fund_hold['quarter_label'].unique())
    
    for i in range(1, len(quarters)):
        prev_q = quarters[i-1]  # 上季度持仓
        curr_q = quarters[i]    # 当前季度收益
        
        prev_holdings = fund_hold[fund_hold['quarter_label'] == prev_q]
        months = quarter_to_months(curr_q)
        
        for month_ts in months:
            # 基金真实收益
            fund_row = fund_monthly[fund_monthly['date'] == month_ts]
            if fund_row.empty:
                # 找最近的
                fund_row = fund_monthly[fund_monthly['date'] <= month_ts].tail(1)
            if fund_row.empty:
                continue
            r_fund = fund_row.iloc[0]['r_fund']
            
            # 持仓模拟收益
            r_holdings = 0
            for _, h in prev_holdings.iterrows():
                stock_code = str(h['stock_code'])
                weight = float(h['hold_ratio']) / 100
                if stock_code in ret_pivot.columns:
                    # 找该月的股票收益
                    valid = ret_pivot[ret_pivot.index <= month_ts][stock_code].dropna()
                    if not valid.empty:
                        r_holdings += weight * valid.iloc[-1]
            
            rg = r_fund - r_holdings
            all_rg.append({
                'fund_code': fund_code,
                'date': month_ts,
                'quarter': curr_q,
                'prev_hold_quarter': prev_q,
                'r_fund': round(r_fund, 6),
                'r_holdings': round(r_holdings, 6),
                'rg': round(rg, 6)
            })

df_rg = pd.DataFrame(all_rg)
if not df_rg.empty:
    print(f"\nReturn Gap计算结果:")
    print(f"  总观测数: {len(df_rg)}")
    print(f"  基金数: {df_rg['fund_code'].nunique()}")
    print(f"\n  按基金统计:")
    for code in df_rg['fund_code'].unique():
        sub = df_rg[df_rg['fund_code'] == code]
        print(f"    {code}: {len(sub)}月, RG均值={sub['rg'].mean()*100:.4f}%, "
              f"ARG={sub['rg'].abs().sum():.4f}")
    
    # 计算季度ARG
    df_rg['rg_abs'] = df_rg['rg'].abs()
    arg_q = df_rg.groupby(['fund_code', 'quarter'])['rg_abs'].sum().reset_index()
    arg_q.columns = ['fund_code', 'quarter', 'arg']
    print(f"\n  季度ARG统计:")
    print(arg_q.to_string(index=False))
    
    df_rg.to_csv(os.path.join(data_dir, 'return_gap_results.csv'), index=False)
    arg_q.to_csv(os.path.join(data_dir, 'arg_quarterly_results.csv'), index=False)
    print(f"\n  结果已保存: return_gap_results.csv, arg_quarterly_results.csv")
else:
    print("  无有效RG结果")

print("\n" + "=" * 60)
print("计算完成!")
print("=" * 60)
