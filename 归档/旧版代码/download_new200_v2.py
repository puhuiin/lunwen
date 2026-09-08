"""下载新增200基金数据 - 修复版：使用AKShare获取净值，分页获取持仓"""
import akshare as ak
import pandas as pd
import numpy as np
import time
import os
import requests
import json

data_dir = r"D:\Desktop\基金经理行为分析研究\数据"
headers = {'User-Agent': 'Mozilla/5.0', 'Referer': 'https://fund.eastmoney.com/'}

# 读取已筛选的新200基金列表
fund_list = pd.read_csv(os.path.join(data_dir, 'fund_list_new200.csv'), dtype={'code': str})
fund_list['code'] = fund_list['code'].astype(str).str.zfill(6)
new_codes = fund_list['code'].tolist()
print(f"新增基金: {len(new_codes)} 只")

# Step 1: 下载净值数据（使用AKShare）
print(f"\nStep 1: 下载 {len(new_codes)} 只新基金净值（AKShare）")
new_nav_list = []

for i, code in enumerate(new_codes):
    try:
        df = ak.fund_open_fund_info_em(symbol=code, indicator='单位净值走势')
        if df is not None and len(df) > 0:
            for _, row in df.iterrows():
                new_nav_list.append({
                    'fund_code': code,
                    'date': str(row['净值日期']),
                    'nav': float(row['单位净值']),
                    'daily_return': float(row['日增长率']) if pd.notna(row['日增长率']) else ''
                })
        
        if (i + 1) % 20 == 0:
            print(f"  已下载 {i+1}/{len(new_codes)}，累计 {len(new_nav_list)} 条")
    except Exception as e:
        print(f"  [{code}] 错误: {e}")
    time.sleep(0.3)

if new_nav_list:
    new_nav_df = pd.DataFrame(new_nav_list)
    new_nav_df.to_csv(os.path.join(data_dir, 'fund_nav_new200.csv'), index=False)
    print(f"\n新增净值 {len(new_nav_df)} 条，{new_nav_df['fund_code'].nunique()} 只基金")
else:
    print("警告：未获取到净值数据")

# Step 2: 下载全持仓数据（使用东方财富API，分页）
print(f"\nStep 2: 下载 {len(new_codes)} 只新基金全持仓")
new_holdings = []

for i, code in enumerate(new_codes):
    for year in [2020, 2021, 2022, 2023, 2024, 2025]:
        for month in ['06', '12']:
            url = f"http://fundf10.eastmoney.com/FundArchivesDatas.aspx?type=jjcc&code={code}&topline=500&year={year}&month={month}"
            try:
                resp = requests.get(url, headers=headers, timeout=15)
                text = resp.text
                if 'content' in text and '{' in text:
                    start = text.index('{')
                    end = text.rindex('}') + 1
                    data = json.loads(text[start:end])
                    if data.get('content'):
                        for arr in data['content'].values():
                            if arr and len(arr) > 0:
                                for stock in arr:
                                    new_holdings.append({
                                        'fund_code': code,
                                        'report_date': f"{year}-{month}",
                                        'year': year,
                                        'stock_code': stock[1] if len(stock) > 1 else '',
                                        'stock_name': stock[2] if len(stock) > 2 else '',
                                        'hold_ratio': stock[6] if len(stock) > 6 else '',
                                    })
            except:
                pass
            time.sleep(0.15)
    if (i + 1) % 10 == 0:
        print(f"  已处理 {i+1}/{len(new_codes)}，累计 {len(new_holdings)} 条持仓")

if new_holdings:
    new_hold_df = pd.DataFrame(new_holdings)
    new_hold_df.to_csv(os.path.join(data_dir, 'fund_holdings_new200.csv'), index=False)
    print(f"\n新增持仓 {len(new_hold_df)} 条，{new_hold_df['fund_code'].nunique()} 只基金")
else:
    print("警告：未获取到持仓数据")

# 汇总
print("\n" + "=" * 60)
print("数据汇总")
print("=" * 60)
print(f"原有: 200基金，318K净值，185K持仓")
print(f"新增: {len(new_codes)}基金，{len(new_nav_list)}净值，{len(new_holdings)}持仓")
print(f"总计: {200 + len(new_codes)}基金")
