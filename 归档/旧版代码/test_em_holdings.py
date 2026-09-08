#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试东方财富基金全持仓数据获取"""
import requests
import re
from bs4 import BeautifulSoup

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Referer': 'https://fundf10.eastmoney.com/',
}

# 获取2023年年报全持仓
url = 'https://fundf10.eastmoney.com/FundArchivesDatas.aspx?type=jjcc&code=005827&topline=200&year=2023&month=12'
r = requests.get(url, headers=headers, timeout=15)
text = r.text

# 提取content部分
content_match = re.search(r'content:"(.*?)",', text, re.DOTALL)
if content_match:
    html_content = content_match.group(1)
    # 反转义
    html_content = html_content.replace('\\"', '"').replace('\\/', '/').replace("\\'", "'")
    
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # 查找所有季度标题
    titles = soup.find_all('h4', class_='t')
    print('=== 季度报告 ===')
    for t in titles:
        label = t.find('label', class_='left')
        if label:
            print(f'  {label.get_text(strip=True)}')
    
    # 查找持仓表格
    tables = soup.find_all('table')
    print(f'\n=== 持仓表格数: {len(tables)} ===')
    
    for i, table in enumerate(tables):
        rows = table.find_all('tr')
        if len(rows) > 1:
            header = [th.get_text(strip=True) for th in rows[0].find_all(['th','td'])]
            print(f'\n表格{i+1}: {len(rows)-1}行数据')
            print(f'  表头: {header}')
            for row in rows[1:4]:
                cells = [td.get_text(strip=True) for td in row.find_all('td')]
                print(f'  {cells}')
            if len(rows) > 4:
                print(f'  ... 共{len(rows)-1}行')
else:
    print('未找到content')
    print(text[:1000])
