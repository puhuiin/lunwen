"""下载新增200基金全持仓数据 - AKShare版
AKShare fund_portfolio_hold_em 获取前十大持仓（季报）
东方财富API获取半年报/年报全持仓（topline=500）
两者合并，半年报/年报用全持仓替代前十大
"""
import akshare as ak
import pandas as pd
import numpy as np
import time
import os
import requests
import json
import re

data_dir = r"D:\Desktop\基金经理行为分析研究\数据"
headers = {'User-Agent': 'Mozilla/5.0', 'Referer': 'https://fund.eastmoney.com/'}

# 读取新200基金列表
fund_list = pd.read_csv(os.path.join(data_dir, 'fund_list_new200.csv'), dtype={'code': str})
fund_list['code'] = fund_list['code'].astype(str).str.zfill(6)
new_codes = fund_list['code'].tolist()
print(f"新增基金: {len(new_codes)} 只")

# ============ Step 1: AKShare 获取前十大持仓（季度） ============
print(f"\nStep 1: AKShare 下载前十大持仓（季度）")
all_holdings = []

for i, code in enumerate(new_codes):
    for year in ['2020', '2021', '2022', '2023', '2024', '2025']:
        try:
            df = ak.fund_portfolio_hold_em(symbol=code, date=year)
            if df is not None and len(df) > 0:
                for _, row in df.iterrows():
                    quarter_str = str(row['季度'])
                    # 提取季度: "2024年1季度股票投资明细" -> "2024Q1"
                    m = re.search(r'(\d{4})年(\d)季度', quarter_str)
                    if m:
                        q = f"{m.group(1)}Q{m.group(2)}"
                    else:
                        q = quarter_str
                    
                    # report_date: Q1->03-31, Q2->06-30, Q3->09-30, Q4->12-31
                    q_month = {'1': '03-31', '2': '06-30', '3': '09-30', '4': '12-31'}
                    rd = f"{m.group(1)}-{q_month.get(m.group(2), '')}" if m else ''
                    
                    all_holdings.append({
                        'fund_code': code,
                        'report_date': rd,
                        'quarter': q,
                        'stock_code': str(row['股票代码']),
                        'stock_name': str(row['股票名称']),
                        'hold_ratio': float(row['占净值比例']) if pd.notna(row['占净值比例']) else '',
                    })
        except Exception as e:
            pass
        time.sleep(0.15)
    
    if (i + 1) % 20 == 0:
        print(f"  AKShare: 已处理 {i+1}/{len(new_codes)}，累计 {len(all_holdings)} 条")

print(f"  AKShare完成: {len(all_holdings)} 条持仓")

# ============ Step 2: 东方财富API 获取半年报/年报全持仓 ============
print(f"\nStep 2: 东方财富API 下载全持仓（半年报/年报）")
full_holdings = []

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
                                    full_holdings.append({
                                        'fund_code': code,
                                        'report_date': f"{year}-{month}-30" if month == '06' else f"{year}-{month}-31",
                                        'quarter': f"{year}Q{'2' if month == '06' else '4'}",
                                        'stock_code': stock[1] if len(stock) > 1 else '',
                                        'stock_name': stock[2] if len(stock) > 2 else '',
                                        'hold_ratio': float(stock[6].replace('%','')) if len(stock) > 6 and stock[6] else '',
                                    })
            except:
                pass
            time.sleep(0.12)
    
    if (i + 1) % 20 == 0:
        print(f"  全持仓: 已处理 {i+1}/{len(new_codes)}，累计 {len(full_holdings)} 条")

print(f"  全持仓完成: {len(full_holdings)} 条持仓")

# ============ Step 3: 合并去重 ============
print(f"\nStep 3: 合并去重")
ak_df = pd.DataFrame(all_holdings)
full_df = pd.DataFrame(full_holdings)

if len(ak_df) > 0 and len(full_df) > 0:
    # 对于半年报/年报(Q2, Q4)，用全持仓替代前十大
    ak_df_nonfull = ak_df[~ak_df['quarter'].str.endswith(('Q2', 'Q4'))]
    merged = pd.concat([ak_df_nonfull, full_df], ignore_index=True)
elif len(ak_df) > 0:
    merged = ak_df
elif len(full_df) > 0:
    merged = full_df
else:
    merged = pd.DataFrame()

if len(merged) > 0:
    # 去重：同一基金同一报告期同一股票保留全持仓版本
    merged = merged.drop_duplicates(subset=['fund_code', 'report_date', 'stock_code'], keep='last')
    merged.to_csv(os.path.join(data_dir, 'fund_holdings_new200.csv'), index=False)
    print(f"\n最终持仓: {len(merged)} 条，{merged['fund_code'].nunique()} 只基金")
    print(f"  报告期数: {merged['report_date'].nunique()}")
    print(f"  平均每基金: {len(merged) / merged['fund_code'].nunique():.0f} 条")
else:
    print("警告：未获取到持仓数据")

# 汇总
print("\n" + "=" * 60)
print("数据汇总")
print("=" * 60)
nav_df = pd.read_csv(os.path.join(data_dir, 'fund_nav_new200.csv'))
print(f"新200基金净值: {len(nav_df)} 条，{nav_df['fund_code'].nunique()} 只基金")
print(f"新200基金持仓: {len(merged)} 条，{merged['fund_code'].nunique()} 只基金")
print(f"总计: 400基金")
