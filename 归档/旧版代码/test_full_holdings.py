#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""验证东方财富半年报/年报全持仓数据"""
import requests
import re
from bs4 import BeautifulSoup

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Referer': 'https://fundf10.eastmoney.com/',
}

tests = [
    ('2023', '06', '2023半年报'),
    ('2023', '12', '2023年报'),
    ('2022', '06', '2022半年报'),
    ('2022', '12', '2022年报'),
    ('2021', '06', '2021半年报'),
    ('2021', '12', '2021年报'),
    ('2020', '06', '2020半年报'),
    ('2020', '12', '2020年报'),
]

for year, month, label in tests:
    url = f'https://fundf10.eastmoney.com/FundArchivesDatas.aspx?type=jjcc&code=005827&topline=500&year={year}&month={month}'
    r = requests.get(url, headers=headers, timeout=15)
    content_match = re.search(r'content:"(.*?)",', r.text, re.DOTALL)
    if content_match:
        html = content_match.group(1)
        # 简单反转义
        html = html.replace('\\"', '"').replace('\\/', '/')
        soup = BeautifulSoup(html, 'html.parser')
        tables = soup.find_all('table')
        for i, table in enumerate(tables):
            rows = table.find_all('tr')
            if len(rows) > 1:
                h4 = table.find_previous('h4')
                title = h4.get_text(strip=True) if h4 else f'表格{i+1}'
                print(f'{label} 表{i+1}: {len(rows)-1}行 | {title[:50]}')
    else:
        print(f'{label}: 无数据')
    print()
