#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基金经理行为研究 — 200只基金完整数据下载
==========================================
数据源：
  1. AKShare: 基金净值、季度前十大持仓、行业配置、基金经理、基金列表
  2. 东方财富API: 半年报/年报全持仓数据（关键！）

输出数据：
  - fund_list_200.csv         筛选后的200只基金列表
  - fund_nav_all.csv          所有基金日度净值
  - fund_holdings_top10.csv   季度前十大重仓股
  - fund_holdings_full.csv    半年报/年报全持仓（核心数据）
  - fund_industry_all.csv     行业配置
  - fund_basic_info_200.csv   基金基本信息
  - fund_managers.csv         基金经理信息
  - index_constituents.csv    指数成分股
  - stock_monthly_returns.csv 个股月度收益率
"""
import akshare as ak
import pandas as pd
import numpy as np
import requests
import re
import time
import os
import json
from bs4 import BeautifulSoup
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, '..', '数据')
os.makedirs(DATA_DIR, exist_ok=True)

EM_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Referer': 'https://fundf10.eastmoney.com/',
}

YEARS = ['2020', '2021', '2022', '2023', '2024']


# ============================================================
# 1. 筛选200只基金
# ============================================================
def select_funds(target_n=200):
    """筛选符合条件的偏股混合型基金"""
    print("[1] 筛选基金...")
    df = ak.fund_open_fund_rank_em(symbol='混合型')
    df = df.rename(columns={'基金代码': 'code', '基金简称': 'name'})
    df['code'] = df['code'].astype(str).str.zfill(6)

    # 获取基本信息来筛选
    selected = []
    seen_codes = set()

    # 先从列表中取偏股混合型
    for _, row in df.iterrows():
        code = row['code']
        if code in seen_codes:
            continue
        try:
            info = ak.fund_individual_basic_info_xq(symbol=code)
            info_dict = dict(zip(info['item'], info['value']))
            fund_type = info_dict.get('基金类型', '')
            inception = info_dict.get('成立时间', '')
            size_str = info_dict.get('最新规模', '0')

            # 筛选条件
            if '偏股' not in fund_type:
                continue
            if not inception or inception > '2020-01-01':
                continue

            # 解析规模
            size_val = 0
            try:
                if '亿' in size_str:
                    size_val = float(re.search(r'[\d.]+', size_str).group())
                elif '万' in size_str:
                    size_val = float(re.search(r'[\d.]+', size_str).group()) / 10000
                else:
                    size_val = float(re.search(r'[\d.]+', size_str).group())
            except:
                pass

            if size_val < 2:
                continue

            selected.append({
                'code': code,
                'name': row['name'],
                'fund_type': fund_type,
                'inception_date': inception,
                'size': size_str,
                'size_val': size_val,
                'company': info_dict.get('基金公司', ''),
                'manager': info_dict.get('基金经理', ''),
                'benchmark': info_dict.get('业绩比较基准', ''),
            })
            seen_codes.add(code)

            if len(selected) % 20 == 0:
                print(f"  已筛选 {len(selected)} 只...")
            if len(selected) >= target_n:
                break

            time.sleep(0.3)
        except:
            continue

    result = pd.DataFrame(selected[:target_n])
    result.to_csv(os.path.join(DATA_DIR, '基金基础信息', '基金列表_200只样本.csv'), index=False)
    print(f"  筛选完成: {len(result)} 只基金 -> fund_list_200.csv")
    return result


# ============================================================
# 2. 下载基金净值
# ============================================================
def download_nav(fund_codes):
    print(f"\n[2] 下载基金净值 ({len(fund_codes)}只)...")
    all_nav = []
    for i, code in enumerate(fund_codes):
        try:
            df = ak.fund_open_fund_info_em(symbol=code, indicator='单位净值走势')
            df = df.rename(columns={'净值日期': 'date', '单位净值': 'nav', '日增长率': 'daily_return'})
            df['date'] = pd.to_datetime(df['date'])
            df['fund_code'] = code
            # 筛选2020年以后
            df = df[df['date'] >= '2020-01-01']
            all_nav.append(df)
        except:
            pass
        if (i + 1) % 20 == 0:
            print(f"  {i+1}/{len(fund_codes)}")
        time.sleep(0.3)

    df_nav = pd.concat(all_nav, ignore_index=True) if all_nav else pd.DataFrame()
    df_nav.to_csv(os.path.join(DATA_DIR, 'L4_风险应对层', '基金净值历史_全量.csv'), index=False)
    print(f"  保存 {len(df_nav)} 条 -> fund_nav_all.csv")
    return df_nav


# ============================================================
# 3. 下载前十大重仓股（AKShare，季度）
# ============================================================
def download_top10_holdings(fund_codes):
    print(f"\n[3] 下载前十大重仓股 ({len(fund_codes)}只)...")
    all_h = []
    for i, code in enumerate(fund_codes):
        for year in YEARS:
            try:
                df = ak.fund_portfolio_hold_em(symbol=code, date=year)
                if df is not None and len(df) > 0:
                    df = df.rename(columns={
                        '股票代码': 'stock_code', '股票名称': 'stock_name',
                        '占净值比例': 'hold_ratio', '持股数': 'hold_shares',
                        '持仓市值': 'hold_value', '季度': 'report_period'
                    })
                    df['fund_code'] = code
                    all_h.append(df)
                time.sleep(0.3)
            except:
                pass
        if (i + 1) % 20 == 0:
            print(f"  {i+1}/{len(fund_codes)}")

    df_h = pd.concat(all_h, ignore_index=True) if all_h else pd.DataFrame()
    df_h.to_csv(os.path.join(DATA_DIR, 'L2_持仓偏离层', '基金前十重仓.csv'), index=False)
    print(f"  保存 {len(df_h)} 条 -> fund_holdings_top10.csv")
    return df_h


# ============================================================
# 4. 下载全持仓（东方财富API，半年报+年报）
# ============================================================
def download_full_holdings(fund_codes, max_retries=3):
    """
    从东方财富获取半年报(Q2)和年报(Q4)的全持仓数据
    关键：topline=500 确保获取全部持仓
    """
    print(f"\n[4] 下载全持仓数据 ({len(fund_codes)}只)...")
    all_holdings = []

    for i, code in enumerate(fund_codes):
        for year in YEARS:
            for month in ['06', '12']:  # 半年报和年报
                for retry in range(max_retries):
                    try:
                        url = f'https://fundf10.eastmoney.com/FundArchivesDatas.aspx?type=jjcc&code={code}&topline=500&year={year}&month={month}'
                        r = requests.get(url, headers=EM_HEADERS, timeout=15)
                        if r.status_code != 200:
                            time.sleep(1)
                            continue

                        content_match = re.search(r'content:"(.*?)",', r.text, re.DOTALL)
                        if not content_match:
                            break

                        html = content_match.group(1)
                        html = html.replace('\\"', '"').replace('\\/', '/')

                        soup = BeautifulSoup(html, 'html.parser')
                        tables = soup.find_all('table')

                        for table in tables:
                            rows = table.find_all('tr')
                            if len(rows) <= 1:
                                continue

                            # 获取报告期
                            h4 = table.find_previous('h4')
                            if h4:
                                h4_text = h4.get_text(strip=True)
                                # 提取季度和截止日期
                                date_match = re.search(r'截止至：(\d{4}-\d{2}-\d{2})', h4_text)
                                q_match = re.search(r'(\d{4})年(\d)季度', h4_text)
                                if date_match and q_match:
                                    report_date = date_match.group(1)
                                    year_q = q_match.group(1)
                                    q_num = int(q_match.group(2))

                                    # 只保留全持仓（行数>10的表）
                                    if len(rows) - 1 <= 10:
                                        continue

                                    for row in rows[1:]:
                                        cells = [td.get_text(strip=True) for td in row.find_all('td')]
                                        if len(cells) >= 6:
                                            all_holdings.append({
                                                'fund_code': code,
                                                'report_date': report_date,
                                                'year': int(year_q),
                                                'quarter': q_num,
                                                'stock_code': cells[1] if len(cells) > 1 else '',
                                                'stock_name': cells[2] if len(cells) > 2 else '',
                                                'hold_ratio': cells[4] if len(cells) > 4 else '',
                                                'hold_shares': cells[5] if len(cells) > 5 else '',
                                                'hold_value': cells[6] if len(cells) > 6 else '',
                                            })
                        break  # 成功则跳出重试
                    except Exception as e:
                        if retry < max_retries - 1:
                            time.sleep(2)
                        else:
                            pass

                time.sleep(0.5)  # 限速

        if (i + 1) % 10 == 0:
            print(f"  {i+1}/{len(fund_codes)}")
            # 定期保存
            if all_holdings:
                pd.DataFrame(all_holdings).to_csv(
                    os.path.join(DATA_DIR, 'L2_持仓偏离层', '基金持仓明细_初版.csv'), index=False)

    df_full = pd.DataFrame(all_holdings)
    if not df_full.empty:
        # 清理数据
        df_full['hold_ratio'] = df_full['hold_ratio'].str.replace('%', '').astype(float) / 100
        df_full.to_csv(os.path.join(DATA_DIR, 'L2_持仓偏离层', '基金持仓明细_初版.csv'), index=False)
    print(f"  保存 {len(df_full)} 条 -> fund_holdings_full.csv")
    return df_full


# ============================================================
# 5. 下载行业配置
# ============================================================
def download_industry(fund_codes):
    print(f"\n[5] 下载行业配置 ({len(fund_codes)}只)...")
    all_ind = []
    for i, code in enumerate(fund_codes):
        for year in YEARS:
            try:
                df = ak.fund_portfolio_industry_allocation_em(symbol=code, date=year)
                if df is not None and len(df) > 0:
                    df = df.rename(columns={
                        '行业类别': 'industry', '占净值比例': 'hold_ratio',
                        '市值': 'market_value', '截止时间': 'report_date'
                    })
                    df['fund_code'] = code
                    all_ind.append(df)
                time.sleep(0.3)
            except:
                pass
        if (i + 1) % 20 == 0:
            print(f"  {i+1}/{len(fund_codes)}")

    df_ind = pd.concat(all_ind, ignore_index=True) if all_ind else pd.DataFrame()
    df_ind.to_csv(os.path.join(DATA_DIR, 'fund_industry_all.csv'), index=False)
    print(f"  保存 {len(df_ind)} 条 -> fund_industry_all.csv")
    return df_ind


# ============================================================
# 6. 下载指数成分股
# ============================================================
def download_index():
    print(f"\n[6] 下载指数成分股...")
    for idx_code in ['000300', '000905']:
        try:
            df = ak.index_stock_cons_csindex(symbol=idx_code)
            df = df.rename(columns={'成分券代码': 'stock_code', '成分券名称': 'stock_name'})
            df['index_code'] = idx_code
            df['weight'] = 1.0 / len(df)
            df.to_csv(os.path.join(DATA_DIR, f'index_{idx_code}.csv'), index=False)
            print(f"  {idx_code}: {len(df)} 只")
        except:
            pass


# ============================================================
# 7. 下载基金经理信息
# ============================================================
def download_managers():
    print(f"\n[7] 下载基金经理信息...")
    try:
        df = ak.fund_manager_em()
        df.to_csv(os.path.join(DATA_DIR, 'fund_managers.csv'), index=False)
        print(f"  保存 {len(df)} 条")
    except:
        pass


# ============================================================
# 8. 下载个股月度收益
# ============================================================
def download_stock_returns(all_stocks):
    # 过滤港股（5位数字）和非A股
    a_stocks = [s for s in all_stocks if len(str(s)) == 6 and str(s)[0] in '036']
    print(f"\n[8] 下载个股月度收益 ({len(a_stocks)}只A股)...")

    all_returns = []
    batch_size = 30
    for batch_start in range(0, len(a_stocks), batch_size):
        batch = a_stocks[batch_start:batch_start + batch_size]
        for stock in batch:
            try:
                df = ak.stock_zh_a_hist(symbol=stock, period='monthly',
                                        start_date='20200101', end_date='20241231',
                                        adjust='qfq')
                if df is not None and len(df) > 0:
                    df = df.rename(columns={'日期': 'date', '收盘': 'close'})
                    df['date'] = pd.to_datetime(df['date'])
                    df = df.sort_values('date').reset_index(drop=True)
                    df['monthly_return'] = df['close'].pct_change()
                    df['stock_code'] = stock
                    all_returns.append(df[['date', 'stock_code', 'monthly_return']].dropna())
                time.sleep(0.15)
            except:
                pass

        print(f"  {min(batch_start + batch_size, len(a_stocks))}/{len(a_stocks)}")
        # 定期保存
        if all_returns:
            pd.concat(all_returns, ignore_index=True).to_csv(
                os.path.join(DATA_DIR, 'stock_monthly_returns.csv'), index=False)

    if all_returns:
        df_ret = pd.concat(all_returns, ignore_index=True)
        df_ret.to_csv(os.path.join(DATA_DIR, 'stock_monthly_returns.csv'), index=False)
        print(f"  保存 {len(df_ret)} 条 -> stock_monthly_returns.csv")
        return df_ret
    return pd.DataFrame()


# ============================================================
# 主程序
# ============================================================
if __name__ == '__main__':
    print("=" * 60)
    print("基金经理行为研究 — 200只基金完整数据下载")
    print(f"时间范围: 2020-2024")
    print(f"输出目录: {DATA_DIR}")
    print("=" * 60)

    # 1. 筛选基金
    fund_list = select_funds(target_n=200)
    fund_codes = fund_list['code'].tolist()

    # 2. 下载净值
    download_nav(fund_codes)

    # 3. 下载前十大持仓
    download_top10_holdings(fund_codes)

    # 4. 下载全持仓（核心！）
    download_full_holdings(fund_codes)

    # 5. 下载行业配置
    download_industry(fund_codes)

    # 6. 下载指数成分股
    download_index()

    # 7. 下载基金经理
    download_managers()

    # 8. 下载个股收益
    # 从全持仓+前十大中提取所有股票
    full_h = pd.read_csv(os.path.join(DATA_DIR, 'L2_持仓偏离层', '基金持仓明细_初版.csv'))
    top10_h = pd.read_csv(os.path.join(DATA_DIR, 'L2_持仓偏离层', '基金前十重仓.csv'))
    all_stocks = set(full_h['stock_code'].unique()) | set(top10_h['stock_code'].unique())
    download_stock_returns(list(all_stocks))

    # 总结
    print("\n" + "=" * 60)
    print("下载完成！文件清单:")
    print("=" * 60)
    for f in sorted(os.listdir(DATA_DIR)):
        if f.endswith('.csv'):
            size = os.path.getsize(os.path.join(DATA_DIR, f))
            print(f"  {f}: {size / 1024:.1f} KB")
