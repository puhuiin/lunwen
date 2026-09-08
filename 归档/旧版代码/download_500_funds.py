"""扩展数据下载：500+基金，补充行业配置和基金经理数据"""
import akshare as ak
import pandas as pd
import numpy as np
import time
import os
import requests
import json

data_dir = r"D:\Desktop\基金经理行为分析研究\数据"
os.makedirs(data_dir, exist_ok=True)

# ============ Step 1: 扩展基金列表到500+ ============
print("=" * 60)
print("Step 1: 扩展基金列表到500+")
print("=" * 60)

try:
    fund_all = ak.fund_name_em()
    # 筛选偏股混合型
    type_keywords = ['偏股混合', '灵活配置', '平衡混合']
    mask = fund_all['基金类型'].str.contains('|'.join(type_keywords), na=False)
    filtered = fund_all[mask].copy()
    
    # 成立日期 <= 2019-12-31 (成立>5年)
    filtered['成立日期'] = pd.to_datetime(filtered['成立日期'], errors='coerce')
    filtered = filtered[filtered['成立日期'] <= '2019-12-31']
    
    # 规模 > 2亿
    filtered['最新规模'] = pd.to_numeric(filtered['最新规模'], errors='coerce')
    filtered = filtered[filtered['最新规模'] > 2e8]
    
    # 取前500只
    fund_500 = filtered.head(500).copy()
    fund_500['code'] = fund_500['基金代码'].astype(str).str.zfill(6)
    fund_500.to_csv(os.path.join(data_dir, 'fund_list_500.csv'), index=False)
    print(f"筛选出 {len(fund_500)} 只基金")
    print(fund_500[['基金代码', '基金简称', '基金类型', '成立日期', '最新规模']].head(10))
except Exception as e:
    print(f"获取基金列表失败: {e}")
    # 如果失败，用已有的200只 + 手动扩展
    fund_200 = pd.read_csv(os.path.join(data_dir, 'fund_list_200.csv'))
    fund_500 = fund_200.copy()
    print(f"使用已有200只基金列表")

# ============ Step 2: 下载新增基金的净值 ============
print("\n" + "=" * 60)
print(f"Step 2: 下载新增基金净值 (共{len(fund_500)}只)")
print("=" * 60)

existing_codes = set()
try:
    nav_existing = pd.read_csv(os.path.join(data_dir, 'fund_nav_all.csv'), usecols=['fund_code'])
    existing_codes = set(nav_existing['fund_code'].astype(str).str.zfill(6).unique())
    print(f"已有净值基金数: {len(existing_codes)}")
except:
    pass

new_codes = [c for c in fund_500['code'].tolist() if c not in existing_codes]
print(f"需新增下载基金数: {len(new_codes)}")

new_nav_list = []
for i, code in enumerate(new_codes):
    try:
        nav = ak.fund_open_fund_info_em(symbol=code, indicator="单位净值走势")
        nav['fund_code'] = code
        new_nav_list.append(nav)
        if (i + 1) % 20 == 0:
            print(f"  已下载 {i+1}/{len(new_codes)}")
    except Exception as e:
        print(f"  {code} 下载失败: {e}")
    time.sleep(0.3)

if new_nav_list:
    new_nav_df = pd.concat(new_nav_list, ignore_index=True)
    new_nav_df.to_csv(os.path.join(data_dir, 'fund_nav_new.csv'), index=False)
    print(f"新增净值 {len(new_nav_df)} 条，{new_nav_df['fund_code'].nunique()} 只基金")

# ============ Step 3: 下载新增基金的全持仓 ============
print("\n" + "=" * 60)
print(f"Step 3: 下载新增基金全持仓")
print("=" * 60)

existing_hold_codes = set()
try:
    hold_existing = pd.read_csv(os.path.join(data_dir, 'fund_holdings_full.csv'), usecols=['fund_code'])
    existing_hold_codes = set(hold_existing['fund_code'].astype(str).str.zfill(6).unique())
    print(f"已有持仓基金数: {len(existing_hold_codes)}")
except:
    pass

new_hold_codes = [c for c in fund_500['code'].tolist() if c not in existing_hold_codes]
print(f"需新增下载基金数: {len(new_hold_codes)}")

new_holdings = []
for i, code in enumerate(new_hold_codes):
    for year in [2020, 2021, 2022, 2023, 2024, 2025]:
        for month in ['06', '12']:
            url = f"http://fundf10.eastmoney.com/FundArchivesDatas.aspx?type=jjcc&code={code}&topline=500&year={year}&month={month}"
            try:
                resp = requests.get(url, timeout=15)
                text = resp.text
                if 'content' in text:
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
        print(f"  已处理 {i+1}/{len(new_hold_codes)} 只基金")

if new_holdings:
    new_hold_df = pd.DataFrame(new_holdings)
    new_hold_df.to_csv(os.path.join(data_dir, 'fund_holdings_new.csv'), index=False)
    print(f"新增持仓 {len(new_hold_df)} 条")

# ============ Step 4: 下载行业配置数据 ============
print("\n" + "=" * 60)
print(f"Step 4: 下载行业配置数据 (全部{len(fund_500)}只)")
print("=" * 60)

all_industry = []
for i, row in fund_500.iterrows():
    code = str(row['code']).zfill(6)
    try:
        for year in ['2024', '2023', '2022']:
            ind = ak.fund_portfolio_industry_allocation_em(symbol=code, date=year)
            if ind is not None and len(ind) > 0:
                ind['fund_code'] = code
                ind['year'] = year
                all_industry.append(ind)
    except:
        pass
    time.sleep(0.3)
    if (i + 1) % 50 == 0:
        print(f"  已处理 {i+1}/{len(fund_500)} 只基金")

if all_industry:
    industry_df = pd.concat(all_industry, ignore_index=True)
    industry_df.to_csv(os.path.join(data_dir, 'fund_industry_500.csv'), index=False)
    print(f"行业配置 {len(industry_df)} 条，{industry_df['fund_code'].nunique()} 只基金")

# ============ Step 5: 下载基金经理信息 ============
print("\n" + "=" * 60)
print("Step 5: 下载基金经理信息")
print("=" * 60)

try:
    managers = ak.fund_manager_em()
    managers.to_csv(os.path.join(data_dir, 'fund_managers_all.csv'), index=False)
    print(f"基金经理信息 {len(managers)} 条")
except Exception as e:
    print(f"下载基金经理失败: {e}")

print("\n" + "=" * 60)
print("数据下载完成！")
print("=" * 60)
print(f"数据目录: {data_dir}")
print("\n文件清单:")
for f in sorted(os.listdir(data_dir)):
    fpath = os.path.join(data_dir, f)
    size = os.path.getsize(fpath) / 1024
    print(f"  {f}: {size:.0f} KB")
