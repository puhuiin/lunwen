"""扩展数据下载v2：直接用东方财富API，绕过AKShare"""
import pandas as pd
import numpy as np
import time
import os
import requests
import json

data_dir = r"D:\Desktop\基金经理行为分析研究\数据"
os.makedirs(data_dir, exist_ok=True)

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Referer': 'https://fund.eastmoney.com/'
}

# ============ Step 1: 获取基金列表 ============
print("=" * 60)
print("Step 1: 获取偏股混合基金列表")
print("=" * 60)

url = "https://fundapi.eastmoney.com/fundtradenew.aspx"
params = {
    'ft': 'hh',  # 混合型
    'sc': '1nnf',
    'st': 'desc',
    'pi': '1',
    'pn': '5000',
    'zf': 'diy',
    'sh': 'list',
}

try:
    resp = requests.get(url, params=params, headers=headers, timeout=30)
    text = resp.text
    # 解析JSONP
    if 'var ' in text:
        start = text.index('=') + 2
        end = text.rindex('}') + 1
        data = json.loads(text[start:end])
    else:
        data = resp.json()
    
    fund_list = pd.DataFrame(data.get('Data', data.get('datas', [])))
    print(f"获取到 {len(fund_list)} 只基金")
    
    # 筛选
    if 'FTYPE' in fund_list.columns:
        fund_list = fund_list[fund_list['FTYPE'].str.contains('偏股|灵活', na=False)]
    elif 'fundtype' in fund_list.columns:
        fund_list = fund_list[fund_list['fundtype'].str.contains('偏股|灵活', na=False)]
    
    print(f"筛选后 {len(fund_list)} 只基金")
    print(fund_list.columns.tolist())
    
except Exception as e:
    print(f"获取基金列表失败: {e}")
    # 使用已有200只
    fund_200 = pd.read_csv(os.path.join(data_dir, 'fund_list_200.csv'))
    codes = fund_200['code'].tolist()
    print(f"使用已有 {len(codes)} 只基金")

# ============ Step 2: 下载净值（直接用东方财富API）============
print("\n" + "=" * 60)
print("Step 2: 下载基金净值")
print("=" * 60)

# 如果已有200基金净值，只需下载新增的
existing_codes = set()
try:
    nav_existing = pd.read_csv(os.path.join(data_dir, 'fund_nav_all.csv'), usecols=['fund_code'])
    existing_codes = set(nav_existing['fund_code'].astype(str).str.zfill(6).unique())
    print(f"已有净值基金数: {len(existing_codes)}")
except:
    pass

# 获取更多基金代码
try:
    more_funds = fund_list['FCODE'].tolist() if 'FCODE' in fund_list.columns else []
except:
    more_funds = []

if not more_funds:
    more_funds = codes if 'codes' in dir() else list(existing_codes)

# 合并所有基金代码
all_codes = sorted(set(list(existing_codes) + [str(c).zfill(6) for c in more_funds]))
new_codes = [c for c in all_codes if c not in existing_codes]
print(f"总计基金: {len(all_codes)}，需新增下载: {len(new_codes)}")

new_nav_list = []
for i, code in enumerate(new_codes[:300]):  # 限制前300只新增
    try:
        # 东方财富基金净值API
        nav_url = f"https://api.fund.eastmoney.com/f10/lsjz"
        params = {
            'fundCode': code,
            'pageIndex': '1',
            'pageSize': '3000',
            'startDate': '2019-01-01',
            'endDate': '2026-12-31'
        }
        resp = requests.get(nav_url, params=params, headers=headers, timeout=15)
        data = resp.json()
        
        if data.get('Data') and data['Data'].get('LSJZList'):
            records = data['Data']['LSJZList']
            for r in records:
                new_nav_list.append({
                    'fund_code': code,
                    'date': r.get('FSRQ', ''),
                    'nav': r.get('DWJZ', ''),
                    'daily_return': r.get('JZZZL', '')
                })
        
        if (i + 1) % 20 == 0:
            print(f"  已下载 {i+1}/{min(len(new_codes), 300)}，累计 {len(new_nav_list)} 条")
    except Exception as e:
        if (i + 1) % 50 == 0:
            print(f"  {code} 失败: {e}")
    time.sleep(0.3)

if new_nav_list:
    new_nav_df = pd.DataFrame(new_nav_list)
    new_nav_df.to_csv(os.path.join(data_dir, 'fund_nav_extended.csv'), index=False)
    print(f"新增净值 {len(new_nav_df)} 条，{new_nav_df['fund_code'].nunique()} 只基金")

# ============ Step 3: 下载全持仓（新增基金）============
print("\n" + "=" * 60)
print("Step 3: 下载全持仓")
print("=" * 60)

existing_hold_codes = set()
try:
    hold_existing = pd.read_csv(os.path.join(data_dir, 'fund_holdings_full.csv'), usecols=['fund_code'])
    existing_hold_codes = set(hold_existing['fund_code'].astype(str).str.zfill(6).unique())
    print(f"已有持仓基金数: {len(existing_hold_codes)}")
except:
    pass

new_hold_codes = [c for c in all_codes if c not in existing_hold_codes]
print(f"需新增持仓基金数: {len(new_hold_codes)}")

new_holdings = []
for i, code in enumerate(new_hold_codes[:300]):  # 限制前300只
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
        print(f"  已处理 {i+1}/{min(len(new_hold_codes), 300)} 只基金，累计 {len(new_holdings)} 条持仓")

if new_holdings:
    new_hold_df = pd.DataFrame(new_holdings)
    new_hold_df.to_csv(os.path.join(data_dir, 'fund_holdings_extended.csv'), index=False)
    print(f"新增持仓 {len(new_hold_df)} 条，{new_hold_df['fund_code'].nunique()} 只基金")

print("\n" + "=" * 60)
print("数据下载完成！")
print("=" * 60)
