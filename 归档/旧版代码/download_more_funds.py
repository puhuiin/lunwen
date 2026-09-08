"""直接从东方财富获取更多基金代码并下载数据"""
import requests
import json
import pandas as pd
import time
import os

data_dir = r"D:\Desktop\基金经理行为分析研究\数据"
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Referer': 'https://fund.eastmoney.com/'
}

# Step 1: 获取基金列表（东方财富基金排行API）
print("Step 1: 获取偏股混合基金列表")
url = "https://fund.eastmoney.com/Data/rank_handler.aspx"
params = {
    'op': 'ph',
    'dt': 'kf',
    'ft': 'hh',  # 混合型
    'rs': 1,
    'gs': 0,
    'sc': '1nzf',
    'st': 'desc',
    'sd': '2019-01-01',
    'ed': '2026-08-03',
    'qdii': '',
    'tabSubtype': ',,,,,',
    'pi': '1',
    'pn': '10000',
    'dx': '1',
}

try:
    resp = requests.get(url, params=params, headers=headers, timeout=30)
    text = resp.text
    # 东方财富返回的是 var rankData = {...}; 格式
    if 'var ' in text:
        start = text.index('=') + 2
        end = text.rindex('}') + 1
        data = json.loads(text[start:end])
    else:
        data = json.loads(text)
    
    funds = data.get('Data', data.get('datas', []))
    print(f"获取到 {len(funds)} 只混合型基金")
    
    # 解析为DataFrame
    if isinstance(funds, list) and len(funds) > 0:
        if isinstance(funds[0], list):
            # 数据是列表的列表格式
            fund_df = pd.DataFrame(funds, columns=[
                'code', 'name', 'abbrev', 'date', 'nav', 'nav_acc', 'daily_return',
                'w1', 'w4', 'w12', 'y1', 'y2', 'y3', 'ytd', 'm6', 'm3', 'm1',
                'fee_rate', 'custodian_fee', 'management_fee', 'fund_type',
                'scale', 'manager', 'inception_date', 'benchmark'
            ])
        else:
            fund_df = pd.DataFrame(funds)
        
        # 筛选成立日期 <= 2019-12-31
        if 'inception_date' in fund_df.columns:
            fund_df['inception_date'] = pd.to_datetime(fund_df['inception_date'], errors='coerce')
            fund_df = fund_df[fund_df['inception_date'] <= '2019-12-31']
        
        # 筛选规模 > 2亿
        if 'scale' in fund_df.columns:
            fund_df['scale'] = pd.to_numeric(fund_df['scale'], errors='coerce')
            fund_df = fund_df[fund_df['scale'] > 2.0]  # 单位：亿元
        
        fund_df['code'] = fund_df['code'].astype(str).str.zfill(6)
        print(f"筛选后（成立>5年、规模>2亿）: {len(fund_df)} 只基金")
        
        # 保存
        fund_df.to_csv(os.path.join(data_dir, 'fund_list_extended.csv'), index=False)
        
        # 找出新增基金
        existing_nav = set()
        try:
            nav_df = pd.read_csv(os.path.join(data_dir, 'fund_nav_all.csv'), usecols=['fund_code'])
            existing_nav = set(nav_df['fund_code'].astype(str).str.zfill(6).unique())
        except:
            pass
        
        new_codes = [c for c in fund_df['code'].tolist() if c not in existing_nav]
        print(f"已有净值: {len(existing_nav)}，新增需下载: {len(new_codes)}")
        
        # 保存新增代码列表
        with open(os.path.join(data_dir, 'new_fund_codes.txt'), 'w') as f:
            for c in new_codes:
                f.write(c + '\n')
        
    else:
        print("未获取到基金数据")
        new_codes = []
        
except Exception as e:
    print(f"获取基金列表失败: {e}")
    import traceback
    traceback.print_exc()
    new_codes = []

# Step 2: 下载新增基金净值
if new_codes:
    print(f"\nStep 2: 下载 {len(new_codes)} 只新基金净值")
    new_nav_list = []
    
    for i, code in enumerate(new_codes[:200]):  # 限制前200只
        try:
            nav_url = "https://api.fund.eastmoney.com/f10/lsjz"
            params = {
                'fundCode': code,
                'pageIndex': '1',
                'pageSize': '5000',
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
                print(f"  已下载 {i+1}/{min(len(new_codes), 200)}，累计 {len(new_nav_list)} 条")
        except Exception as e:
            if (i + 1) % 50 == 0:
                print(f"  {code} 失败: {e}")
        time.sleep(0.5)
    
    if new_nav_list:
        new_nav_df = pd.DataFrame(new_nav_list)
        new_nav_df.to_csv(os.path.join(data_dir, 'fund_nav_new.csv'), index=False)
        print(f"新增净值 {len(new_nav_df)} 条，{new_nav_df['fund_code'].nunique()} 只基金")
    
    # Step 3: 下载新增基金全持仓
    print(f"\nStep 3: 下载新增基金全持仓")
    new_holdings = []
    
    for i, code in enumerate(new_codes[:200]):
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
            print(f"  已处理 {i+1}/{min(len(new_codes), 200)}，累计 {len(new_holdings)} 条持仓")
    
    if new_holdings:
        new_hold_df = pd.DataFrame(new_holdings)
        new_hold_df.to_csv(os.path.join(data_dir, 'fund_holdings_new.csv'), index=False)
        print(f"新增持仓 {len(new_hold_df)} 条，{new_hold_df['fund_code'].nunique()} 只基金")

print("\n完成！")
