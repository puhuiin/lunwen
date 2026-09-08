#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基金经理行为研究 — 真实数据下载脚本
====================================
使用AKShare免费接口下载研究所需数据。

可获取的数据：
  ✓ 基金净值（日度，历史完整）
  ✓ 基金季度持仓（前十大重仓股，2020-2024年）
  ✓ 基金行业配置（半年报/年报）
  ✓ 基金持仓变动（季度累计买入/卖出）
  ✓ 基金经理信息（从业时间、管理基金）
  ✓ 基金基本信息（规模、基准、成立日期）
  ✓ 指数成分股（沪深300/中证500）
  ✓ 个股月度行情（前复权收盘价）
  ✓ 申万一级行业分类

无法通过AKShare获取（需Wind/CSMAR）：
  ✗ 基金半年报/年报全持仓（AKShare仅提供前十大）
  ✗ 指数成分股精确权重（AKShare仅提供成分股列表）
  ✗ 基金费用率历史
  ✗ 基金公司规模

运行: python download_real_data.py
"""

import akshare as ak
import pandas as pd
import numpy as np
import time
import os
import warnings
from datetime import datetime
warnings.filterwarnings('ignore')

# 输出目录
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '数据')
os.makedirs(OUTPUT_DIR, exist_ok=True)


def download_fund_list(fund_type='混合型', n=200):
    """下载基金列表"""
    print(f"\n[1/8] 下载{fund_type}基金列表...")
    df = ak.fund_open_fund_rank_em(symbol=fund_type)
    df = df.rename(columns={
        '基金代码': 'code', '基金简称': 'name',
        '单位净值': 'nav', '累计净值': 'accumulated_nav',
        '近1年': 'return_1y', '近3年': 'return_3y',
        '成立来': 'return_since_inception'
    })
    df['code'] = df['code'].astype(str).str.zfill(6)
    df.to_csv(os.path.join(OUTPUT_DIR, 'fund_list.csv'), index=False)
    print(f"  保存 {len(df)} 只基金 -> fund_list.csv")
    return df


def download_fund_nav(fund_code):
    """下载基金净值数据"""
    try:
        df = ak.fund_open_fund_info_em(symbol=fund_code, indicator='单位净值走势')
        df = df.rename(columns={'净值日期': 'date', '单位净值': 'nav', '日增长率': 'daily_return'})
        df['date'] = pd.to_datetime(df['date'])
        df['fund_code'] = fund_code
        return df
    except Exception as e:
        print(f"    [错误] {fund_code} 净值: {e}")
        return pd.DataFrame()


def download_fund_accumulated_nav(fund_code):
    """下载基金累计净值"""
    try:
        df = ak.fund_open_fund_info_em(symbol=fund_code, indicator='累计净值走势')
        df = df.rename(columns={'净值日期': 'date', '累计净值': 'accumulated_nav'})
        df['date'] = pd.to_datetime(df['date'])
        df['fund_code'] = fund_code
        return df
    except:
        return pd.DataFrame()


def download_fund_holdings(fund_code, years=['2020', '2021', '2022', '2023', '2024']):
    """
    下载基金季度持仓（前十大重仓股）
    AKShare按年份获取，每年4个季度
    """
    all_dfs = []
    for year in years:
        try:
            df = ak.fund_portfolio_hold_em(symbol=fund_code, date=year)
            if df is not None and len(df) > 0:
                df = df.rename(columns={
                    '股票代码': 'stock_code',
                    '股票名称': 'stock_name',
                    '占净值比例': 'hold_ratio',
                    '持股数': 'hold_shares',
                    '持仓市值': 'hold_value',
                    '季度': 'report_period'
                })
                df['fund_code'] = fund_code
                df['year'] = year
                all_dfs.append(df)
            time.sleep(0.3)
        except Exception as e:
            print(f"    [错误] {fund_code} {year}年持仓: {e}")
    
    if all_dfs:
        return pd.concat(all_dfs, ignore_index=True)
    return pd.DataFrame()


def download_fund_industry_allocation(fund_code, years=['2020', '2021', '2022', '2023', '2024']):
    """下载基金行业配置数据"""
    all_dfs = []
    for year in years:
        try:
            df = ak.fund_portfolio_industry_allocation_em(symbol=fund_code, date=year)
            if df is not None and len(df) > 0:
                df = df.rename(columns={
                    '行业类别': 'industry',
                    '占净值比例': 'hold_ratio',
                    '市值': 'market_value',
                    '截止时间': 'report_date'
                })
                df['fund_code'] = fund_code
                all_dfs.append(df)
            time.sleep(0.3)
        except:
            pass
    
    if all_dfs:
        return pd.concat(all_dfs, ignore_index=True)
    return pd.DataFrame()


def download_fund_basic_info(fund_code):
    """下载基金基本信息"""
    try:
        df = ak.fund_individual_basic_info_xq(symbol=fund_code)
        info = dict(zip(df['item'], df['value']))
        return {
            'fund_code': fund_code,
            'fund_name': info.get('基金名称', ''),
            'inception_date': info.get('成立时间', ''),
            'size': info.get('最新规模', ''),
            'company': info.get('基金公司', ''),
            'manager': info.get('基金经理', ''),
            'fund_type': info.get('基金类型', ''),
            'benchmark': info.get('业绩比较基准', ''),
        }
    except:
        return None


def download_index_constituents(index_code='000300'):
    """下载指数成分股"""
    print(f"\n  下载指数 {index_code} 成分股...")
    try:
        df = ak.index_stock_cons_csindex(symbol=index_code)
        df = df.rename(columns={
            '成分券代码': 'stock_code',
            '成分券名称': 'stock_name'
        })
        df['index_code'] = index_code
        # 等权近似
        df['weight'] = 1.0 / len(df)
        return df[['stock_code', 'stock_name', 'weight', 'index_code']]
    except Exception as e:
        print(f"    [错误] 指数 {index_code}: {e}")
        return pd.DataFrame()


def download_stock_returns(stock_codes, start_date='20200101', end_date='20241231'):
    """下载个股月度收益率"""
    all_returns = {}
    for i, code in enumerate(stock_codes):
        try:
            df = ak.stock_zh_a_hist(
                symbol=code, period='monthly',
                start_date=start_date, end_date=end_date, adjust='qfq'
            )
            if df is not None and len(df) > 0:
                df = df.rename(columns={'日期': 'date', '收盘': 'close'})
                df['date'] = pd.to_datetime(df['date'])
                df = df.sort_values('date').reset_index(drop=True)
                df['monthly_return'] = df['close'].pct_change()
                all_returns[code] = df.set_index('date')['monthly_return']
            time.sleep(0.2)
        except:
            pass
        if (i + 1) % 100 == 0:
            print(f"    已下载 {i+1}/{len(stock_codes)} 只股票")
    
    if all_returns:
        return pd.DataFrame(all_returns)
    return pd.DataFrame()


def download_fund_managers():
    """下载基金经理信息"""
    print("\n[7/8] 下载基金经理信息...")
    try:
        df = ak.fund_manager_em()
        df = df.rename(columns={
            '姓名': 'manager_name',
            '所属公司': 'company',
            '现任基金代码': 'fund_codes',
            '现任基金': 'fund_names',
            '累计从业时间': 'experience_days',
            '现任基金资产总规模': 'total_aum',
            '现任基金最佳回报': 'best_return'
        })
        df.to_csv(os.path.join(OUTPUT_DIR, 'fund_managers.csv'), index=False)
        print(f"  保存 {len(df)} 条基金经理记录 -> fund_managers.csv")
        return df
    except Exception as e:
        print(f"  [错误] 基金经理信息: {e}")
        return pd.DataFrame()


# ============================================================
# 主下载流程
# ============================================================

def download_all(fund_codes, years=['2020', '2021', '2022', '2023', '2024']):
    """
    完整数据下载流程
    """
    print("=" * 60)
    print("基金经理行为研究 — 数据下载")
    print(f"基金数量: {len(fund_codes)}")
    print(f"时间范围: {years[0]}-{years[-1]}")
    print(f"输出目录: {OUTPUT_DIR}")
    print("=" * 60)
    
    # 1. 基金列表
    fund_list = download_fund_list()
    
    # 2. 基金基本信息
    print(f"\n[2/8] 下载基金基本信息 ({len(fund_codes)}只)...")
    basic_infos = []
    for i, code in enumerate(fund_codes):
        info = download_fund_basic_info(code)
        if info:
            basic_infos.append(info)
        if (i + 1) % 10 == 0:
            print(f"  已完成 {i+1}/{len(fund_codes)}")
        time.sleep(0.3)
    df_basic = pd.DataFrame(basic_infos)
    df_basic.to_csv(os.path.join(OUTPUT_DIR, 'fund_basic_info.csv'), index=False)
    print(f"  保存 {len(df_basic)} 条 -> fund_basic_info.csv")
    
    # 3. 基金净值
    print(f"\n[3/8] 下载基金净值 ({len(fund_codes)}只)...")
    all_nav = []
    for i, code in enumerate(fund_codes):
        nav = download_fund_nav(code)
        if not nav.empty:
            all_nav.append(nav)
        if (i + 1) % 10 == 0:
            print(f"  已完成 {i+1}/{len(fund_codes)}")
        time.sleep(0.3)
    df_nav = pd.concat(all_nav, ignore_index=True) if all_nav else pd.DataFrame()
    df_nav.to_csv(os.path.join(OUTPUT_DIR, 'fund_nav.csv'), index=False)
    print(f"  保存 {len(df_nav)} 条 -> fund_nav.csv")
    
    # 4. 基金持仓
    print(f"\n[4/8] 下载基金季度持仓 ({len(fund_codes)}只)...")
    all_holdings = []
    for i, code in enumerate(fund_codes):
        h = download_fund_holdings(code, years)
        if not h.empty:
            all_holdings.append(h)
        if (i + 1) % 10 == 0:
            print(f"  已完成 {i+1}/{len(fund_codes)}")
        time.sleep(0.5)
    df_holdings = pd.concat(all_holdings, ignore_index=True) if all_holdings else pd.DataFrame()
    df_holdings.to_csv(os.path.join(OUTPUT_DIR, 'fund_holdings.csv'), index=False)
    print(f"  保存 {len(df_holdings)} 条 -> fund_holdings.csv")
    
    # 5. 基金行业配置
    print(f"\n[5/8] 下载基金行业配置 ({len(fund_codes)}只)...")
    all_industry = []
    for i, code in enumerate(fund_codes):
        ind = download_fund_industry_allocation(code, years)
        if not ind.empty:
            all_industry.append(ind)
        if (i + 1) % 10 == 0:
            print(f"  已完成 {i+1}/{len(fund_codes)}")
        time.sleep(0.5)
    df_industry = pd.concat(all_industry, ignore_index=True) if all_industry else pd.DataFrame()
    df_industry.to_csv(os.path.join(OUTPUT_DIR, 'fund_industry.csv'), index=False)
    print(f"  保存 {len(df_industry)} 条 -> fund_industry.csv")
    
    # 6. 指数成分股
    print(f"\n[6/8] 下载指数成分股...")
    for idx_code in ['000300', '000905']:
        idx_df = download_index_constituents(idx_code)
        if not idx_df.empty:
            idx_df.to_csv(os.path.join(OUTPUT_DIR, f'index_{idx_code}_constituents.csv'), index=False)
            print(f"  {idx_code}: {len(idx_df)} 只成分股 -> index_{idx_code}_constituents.csv")
    
    # 7. 基金经理
    download_fund_managers()
    
    # 8. 个股月度收益（从持仓数据提取股票列表）
    print(f"\n[8/8] 下载个股月度收益率...")
    if not df_holdings.empty:
        all_stocks = df_holdings['stock_code'].unique()
        # 过滤港股代码（5位数字）
        a_share_stocks = [s for s in all_stocks if len(s) == 6 and s[0] in '036']
        print(f"  需下载 {len(a_share_stocks)} 只A股月度收益（已排除港股）")
        
        # 分批下载
        batch_size = 50
        all_returns = []
        for batch_start in range(0, len(a_share_stocks), batch_size):
            batch = a_share_stocks[batch_start:batch_start+batch_size]
            returns_df = download_stock_returns(batch)
            if not returns_df.empty:
                all_returns.append(returns_df.reset_index().melt(id_vars='date', var_name='stock_code', value_name='monthly_return'))
            print(f"    批次 {batch_start//batch_size + 1}/{(len(a_share_stocks)-1)//batch_size + 1} 完成")
        
        if all_returns:
            df_returns = pd.concat(all_returns, ignore_index=True)
            df_returns = df_returns.dropna()
            df_returns.to_csv(os.path.join(OUTPUT_DIR, 'stock_monthly_returns.csv'), index=False)
            print(f"  保存 {len(df_returns)} 条 -> stock_monthly_returns.csv")
    
    # 总结
    print("\n" + "=" * 60)
    print("数据下载完成！")
    print("=" * 60)
    files = os.listdir(OUTPUT_DIR)
    for f in sorted(files):
        if f.endswith('.csv'):
            size = os.path.getsize(os.path.join(OUTPUT_DIR, f))
            print(f"  {f}: {size/1024:.1f} KB")


if __name__ == '__main__':
    # 小样本测试：先下载5只基金
    test_funds = [
        '005827',  # 易方达蓝筹精选
        '161725',  # 招商中证白酒
        '163406',  # 兴全合润
        '270002',  # 广发稳健增长
        '519066',  # 汇添富蓝筹稳健
    ]
    
    download_all(test_funds, years=['2020', '2021', '2022', '2023', '2024'])
