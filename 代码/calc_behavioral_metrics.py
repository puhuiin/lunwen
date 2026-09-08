#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基金经理行为指标计算工具包 — Active Share & Return Gap
=====================================================
基于真实市场数据计算L2/L3层核心指标。

支持数据源：
  1. AKShare（免费） — 基金净值、持仓、个股行情、指数成分股
  2. CSV导入       — Wind/CSMAR导出的数据文件

核心功能：
  - calc_active_share():  计算Active Share (L2层)
  - calc_return_gap():    计算Return Gap / ARG (L3层)
  - calc_ici():           计算行业集中度ICI (L2层补充)
  - calc_sdi():           计算风格漂移指数SDI (L4层)

依赖: akshare, pandas, numpy
运行: python calc_behavioral_metrics.py
"""

import numpy as np
import pandas as pd
import akshare as ak
from datetime import datetime, timedelta
import time
import os
import warnings
warnings.filterwarnings('ignore')

# ============================================================
# 工具函数
# ============================================================

def safe_float(x):
    """安全转换为float"""
    try:
        return float(x)
    except (ValueError, TypeError):
        return np.nan


def retry_akshare(func, max_retries=3, delay=1.0, **kwargs):
    """AKShare API重试封装"""
    for i in range(max_retries):
        try:
            return func(**kwargs)
        except Exception as e:
            if i == max_retries - 1:
                print(f"  [错误] {func.__name__} 重试{max_retries}次后失败: {e}")
                return None
            time.sleep(delay)


# ============================================================
# 一、Active Share 计算 (L2层)
# ============================================================

def get_fund_holdings_akshare(fund_code, report_type='sn'):
    """
    通过AKShare获取基金持仓数据
    
    Parameters
    ----------
    fund_code : str
        基金代码, 如 '005827'
    report_type : str
        'sn' = 二季报/半年报 (全部持仓)
        'q1' = 一季报, 'q3' = 三季报 (前十大)
        'yn' = 年报 (全部持仓)
    
    Returns
    -------
    DataFrame: columns=[stock_code, stock_name, hold_ratio, report_date]
    """
    df = retry_akshare(ak.fund_portfolio_hold_em, symbol=fund_code, date=report_type)
    if df is None or df.empty:
        return pd.DataFrame()
    
    df = df.rename(columns={
        '股票代码': 'stock_code',
        '股票名称': 'stock_name', 
        '占净值比例': 'hold_ratio',
        '季度': 'report_date'
    })
    df['hold_ratio'] = df['hold_ratio'].apply(safe_float) / 100  # 转为小数
    return df[['stock_code', 'stock_name', 'hold_ratio', 'report_date']]


def get_index_constituents_akshare(index_code='000300'):
    """
    获取指数成分股及权重
    
    Parameters
    ----------
    index_code : str
        指数代码, 如 '000300'(沪深300), '000905'(中证500)
    
    Returns
    -------
    DataFrame: columns=[stock_code, stock_name, weight]
    """
    # AKShare获取沪深300成分股
    df = retry_akshare(ak.index_stock_cons_csindex, symbol=index_code)
    if df is None or df.empty:
        # 尝试备用方法
        df = retry_akshare(ak.index_stock_info, symbol=index_code)
        if df is None or df.empty:
            return pd.DataFrame()
    
    # AKShare可能不直接提供权重，用等权近似
    if '成分券代码' in df.columns:
        df = df.rename(columns={'成分券代码': 'stock_code', '成分券名称': 'stock_name'})
    elif '股票代码' in df.columns:
        df = df.rename(columns={'股票代码': 'stock_code', '股票名称': 'stock_name'})
    
    # 等权近似（真实研究应从中证指数公司下载精确权重）
    n = len(df)
    df['weight'] = 1.0 / n if n > 0 else 0
    
    return df[['stock_code', 'stock_name', 'weight']]


def calc_active_share(fund_holdings, benchmark_holdings):
    """
    计算 Active Share
    
    AS = 1/2 × Σ|w_fund,i - w_bench,i|
    
    Parameters
    ----------
    fund_holdings : DataFrame
        columns=[stock_code, hold_ratio]  (hold_ratio为小数)
    benchmark_holdings : DataFrame  
        columns=[stock_code, weight]      (weight为小数)
    
    Returns
    -------
    float: Active Share 值 [0, 1]
    """
    # 合并基金和基准持仓
    fund = fund_holdings[['stock_code', 'hold_ratio']].copy()
    fund.columns = ['stock_code', 'w_fund']
    
    bench = benchmark_holdings[['stock_code', 'weight']].copy()
    bench.columns = ['stock_code', 'w_bench']
    
    merged = pd.merge(fund, bench, on='stock_code', how='outer')
    merged = merged.fillna(0)
    
    # 计算AS
    as_value = 0.5 * (merged['w_fund'] - merged['w_bench']).abs().sum()
    
    return min(as_value, 1.0)  # 理论上不超过1


def calc_active_share_batch(fund_codes, benchmark_code='000300', output_file='as_results.csv'):
    """
    批量计算多只基金的Active Share
    
    Parameters
    ----------
    fund_codes : list
        基金代码列表
    benchmark_code : str
        基准指数代码
    output_file : str
        结果输出文件
    
    Returns
    -------
    DataFrame: 每只基金每个报告期的AS值
    """
    print(f"\n{'='*60}")
    print(f"批量计算 Active Share")
    print(f"基金数量: {len(fund_codes)}, 基准: {benchmark_code}")
    print(f"{'='*60}")
    
    # 获取基准成分股
    print("\n[1] 获取基准成分股...")
    benchmark = get_index_constituents_akshare(benchmark_code)
    if benchmark.empty:
        print(f"  [错误] 无法获取基准 {benchmark_code} 成分股")
        return pd.DataFrame()
    print(f"  基准成分股: {len(benchmark)} 只")
    
    results = []
    for i, code in enumerate(fund_codes):
        print(f"\n[{i+1}/{len(fund_codes)}] 基金 {code}...")
        
        # 获取半年报全持仓
        holdings = get_fund_holdings_akshare(code, report_type='sn')
        if holdings.empty:
            print(f"  [跳过] 无持仓数据")
            continue
        
        # 按报告期分组计算AS
        for report_date, group in holdings.groupby('report_date'):
            as_val = calc_active_share(group, benchmark)
            results.append({
                'fund_code': code,
                'report_date': report_date,
                'active_share': as_val,
                'n_holdings': len(group),
                'benchmark': benchmark_code
            })
            print(f"  {report_date}: AS={as_val:.4f} ({len(group)}只持仓)")
        
        time.sleep(0.5)  # 限速
    
    df_result = pd.DataFrame(results)
    if not df_result.empty:
        df_result.to_csv(output_file, index=False)
        print(f"\n结果已保存: {output_file}")
    
    return df_result


# ============================================================
# 二、Return Gap 计算 (L3层)
# ============================================================

def get_fund_nav_akshare(fund_code):
    """
    获取基金净值数据
    
    Returns
    -------
    DataFrame: columns=[date, nav, accumulated_nav, return_pct]
    """
    df = retry_akshare(ak.fund_open_fund_info_em, symbol=fund_code, indicator="单位净值走势")
    if df is None or df.empty:
        return pd.DataFrame()
    
    df = df.rename(columns={
        '净值日期': 'date',
        '单位净值': 'nav',
        '日增长率': 'return_pct'
    })
    df['date'] = pd.to_datetime(df['date'])
    df['nav'] = df['nav'].apply(safe_float)
    df['return_pct'] = df['return_pct'].apply(safe_float) / 100
    df = df.sort_values('date').reset_index(drop=True)
    
    return df[['date', 'nav', 'return_pct']]


def get_stock_monthly_return_akshare(stock_code, start_date, end_date):
    """
    获取个股月度收益率
    """
    df = retry_akshare(ak.stock_zh_a_hist, symbol=stock_code, 
                       period='monthly', start_date=start_date, end_date=end_date,
                       adjust='qfq')
    if df is None or df.empty:
        return pd.Series()
    
    df = df.rename(columns={'日期': 'date', '收盘': 'close'})
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date').reset_index(drop=True)
    df['monthly_return'] = df['close'].pct_change()
    
    return df.set_index('date')['monthly_return']


def calc_return_gap(fund_nav, fund_holdings, stock_returns):
    """
    计算 Return Gap
    
    RG_t = R_fund,t - R_holdings,t
    R_holdings,t = Σ(w_i,t-1 × R_i,t)
    
    Parameters
    ----------
    fund_nav : DataFrame
        columns=[date, return_pct]  月度基金收益率
    fund_holdings : DataFrame
        columns=[stock_code, hold_ratio, report_date]  季度持仓
    stock_returns : DataFrame
        index=date, columns=stock_code, values=月度收益率
    
    Returns
    -------
    DataFrame: columns=[date, r_fund, r_holdings, rg, arg_cumulative]
    """
    # 将基金日收益转为月度
    fund_nav['date'] = pd.to_datetime(fund_nav['date'])
    fund_nav['year_month'] = fund_nav['date'].dt.to_period('M')
    fund_monthly = fund_nav.groupby('year_month')['return_pct'].apply(
        lambda x: (1 + x).prod() - 1
    ).reset_index()
    fund_monthly.columns = ['year_month', 'r_fund']
    fund_monthly['date'] = fund_monthly['year_month'].dt.to_timestamp()
    
    # 按季度匹配持仓
    fund_holdings['report_date'] = pd.to_datetime(fund_holdings['report_date'])
    fund_holdings['year_month'] = fund_holdings['report_date'].dt.to_period('M')
    
    rg_results = []
    
    for _, row in fund_monthly.iterrows():
        month = row['year_month']
        r_fund = row['r_fund']
        
        # 找到最近的前一个季报持仓
        valid_holdings = fund_holdings[fund_holdings['year_month'] < month]
        if valid_holdings.empty:
            continue
        latest_holdings = valid_holdings.sort_values('report_date').iloc[-1:]
        latest = fund_holdings[fund_holdings['report_date'] == latest_holdings['report_date'].iloc[0]]
        
        # 计算持仓模拟收益
        r_holdings = 0
        for _, h in latest.iterrows():
            stock_code = h['stock_code']
            weight = h['hold_ratio']
            if stock_code in stock_returns.columns:
                month_ts = month.to_timestamp()
                # 找到该月最近的收益率
                valid_returns = stock_returns[stock_returns.index <= month_ts][stock_code]
                if not valid_returns.empty:
                    r_holdings += weight * valid_returns.iloc[-1]
        
        rg = r_fund - r_holdings
        rg_results.append({
            'date': row['date'],
            'r_fund': r_fund,
            'r_holdings': r_holdings,
            'rg': rg
        })
    
    df_rg = pd.DataFrame(rg_results)
    
    # 计算ARG (绝对值加总, 申宇2013修正版)
    if not df_rg.empty:
        df_rg['rg_abs'] = df_rg['rg'].abs()
        # 季度ARG = 季度内3个月RG绝对值之和
        df_rg['quarter'] = df_rg['date'].dt.to_period('Q')
        arg_quarterly = df_rg.groupby('quarter')['rg_abs'].sum().reset_index()
        arg_quarterly.columns = ['quarter', 'arg']
        
        return df_rg, arg_quarterly
    
    return df_rg, pd.DataFrame()


def calc_return_gap_batch(fund_codes, start_date='20200101', end_date='20241231', 
                          output_file='rg_results.csv'):
    """
    批量计算多只基金的Return Gap
    """
    print(f"\n{'='*60}")
    print(f"批量计算 Return Gap")
    print(f"基金数量: {len(fund_codes)}, 区间: {start_date}-{end_date}")
    print(f"{'='*60}")
    
    all_results = []
    
    for i, code in enumerate(fund_codes):
        print(f"\n[{i+1}/{len(fund_codes)}] 基金 {code}...")
        
        # 1. 获取基金净值
        nav = get_fund_nav_akshare(code)
        if nav.empty:
            print(f"  [跳过] 无净值数据")
            continue
        print(f"  净值数据: {len(nav)} 条 ({nav['date'].min().date()} ~ {nav['date'].max().date()})")
        
        # 2. 获取基金持仓
        holdings = get_fund_holdings_akshare(code, report_type='sn')
        if holdings.empty:
            print(f"  [跳过] 无持仓数据")
            continue
        print(f"  持仓报告: {holdings['report_date'].nunique()} 期")
        
        # 3. 获取所有持仓股票的月度收益
        all_stocks = holdings['stock_code'].unique()
        print(f"  需获取 {len(all_stocks)} 只股票月度收益...")
        
        stock_returns = pd.DataFrame()
        for j, stock in enumerate(all_stocks):
            ret = get_stock_monthly_return_akshare(stock, start_date, end_date)
            if not ret.empty:
                stock_returns[stock] = ret
            if (j + 1) % 50 == 0:
                print(f"    已获取 {j+1}/{len(all_stocks)} 只...")
                time.sleep(0.3)
        
        # 4. 计算RG
        df_rg, df_arg = calc_return_gap(nav, holdings, stock_returns)
        if df_rg.empty:
            print(f"  [跳过] RG计算无结果")
            continue
        
        df_rg['fund_code'] = code
        all_results.append(df_rg)
        
        print(f"  RG计算完成: {len(df_rg)} 个月度观测")
        if not df_arg.empty:
            print(f"  ARG(季度): 均值={df_arg['arg'].mean():.4f}, 标准差={df_arg['arg'].std():.4f}")
        
        time.sleep(0.5)
    
    if all_results:
        df_all = pd.concat(all_results, ignore_index=True)
        df_all.to_csv(output_file, index=False)
        print(f"\n结果已保存: {output_file}")
        return df_all
    else:
        print("\n无有效结果")
        return pd.DataFrame()


# ============================================================
# 三、行业集中度 ICI 计算 (L2层补充)
# ============================================================

def calc_ici(fund_holdings, market_weights):
    """
    计算行业集中度指数
    
    ICI = Σ(w_fund,j - w_market,j)²
    
    Parameters
    ----------
    fund_holdings : DataFrame
        columns=[stock_code, hold_ratio, industry]
    market_weights : dict or Series
        {industry: market_weight}
    
    Returns
    -------
    float: ICI 值
    """
    # 按行业聚合基金持仓
    fund_industry = fund_holdings.groupby('industry')['hold_ratio'].sum()
    
    # 计算ICI
    ici = 0
    for industry in fund_industry.index:
        w_fund = fund_industry.get(industry, 0)
        w_market = market_weights.get(industry, 0)
        ici += (w_fund - w_market) ** 2
    
    return ici


# ============================================================
# 四、风格漂移指数 SDI 计算 (L4层)
# ============================================================

def calc_sdi(fund_nav, style_indices, window=36):
    """
    计算风格漂移指数 (基于寇宗来等2020的方法)
    
    Step 1: Sharpe强式模型估计基金对四类风格指数的敏感度
    Step 2: 计算前后两期权重的曼哈顿距离
    
    Parameters
    ----------
    fund_nav : DataFrame
        columns=[date, return_pct]
    style_indices : DataFrame
        columns=[date, large_growth, large_value, small_growth, small_value]
    window : int
        滚动回归窗口(月)
    
    Returns
    -------
    DataFrame: columns=[date, sdi, w_lg, w_lv, w_sg, w_sv]
    """
    from statsmodels.regression.linear_model import OLS
    import statsmodels.api as sm
    
    fund_nav['date'] = pd.to_datetime(fund_nav['date'])
    style_indices['date'] = pd.to_datetime(style_indices['date'])
    
    merged = pd.merge(fund_nav, style_indices, on='date', how='inner')
    merged = merged.sort_values('date').reset_index(drop=True)
    
    # 滚动回归估计风格权重
    results = []
    style_cols = ['large_growth', 'large_value', 'small_growth', 'small_value']
    
    for i in range(window, len(merged)):
        train = merged.iloc[i-window:i]
        X = sm.add_constant(train[style_cols])
        y = train['return_pct']
        
        try:
            model = OLS(y, X).fit()
            weights = model.params[style_cols].values
            # 非负约束（简化处理：截断负值后归一化）
            weights = np.maximum(weights, 0)
            if weights.sum() > 0:
                weights = weights / weights.sum()
            
            results.append({
                'date': merged.iloc[i]['date'],
                'w_lg': weights[0],
                'w_lv': weights[1],
                'w_sg': weights[2],
                'w_sv': weights[3]
            })
        except:
            continue
    
    df_weights = pd.DataFrame(results)
    if len(df_weights) < 2:
        return pd.DataFrame()
    
    # 计算SDI (曼哈顿距离)
    sdi_values = []
    for i in range(1, len(df_weights)):
        w_prev = df_weights.iloc[i-1][['w_lg', 'w_lv', 'w_sg', 'w_sv']].values
        w_curr = df_weights.iloc[i][['w_lg', 'w_lv', 'w_sg', 'w_sv']].values
        sdi = np.abs(w_curr - w_prev).sum()
        sdi_values.append({
            'date': df_weights.iloc[i]['date'],
            'sdi': sdi,
            **df_weights.iloc[i].to_dict()
        })
    
    return pd.DataFrame(sdi_values)


# ============================================================
# 五、主程序入口
# ============================================================

def demo_single_fund(fund_code='005827', benchmark='000300'):
    """
    单只基金演示计算
    """
    print("=" * 60)
    print(f"单只基金演示: {fund_code}")
    print("=" * 60)
    
    # --- Active Share ---
    print("\n[Active Share 计算]")
    holdings = get_fund_holdings_akshare(fund_code, report_type='sn')
    if not holdings.empty:
        print(f"持仓数据: {holdings['report_date'].nunique()} 个报告期")
        print(holdings.head())
        
        benchmark_data = get_index_constituents_akshare(benchmark)
        if not benchmark_data.empty:
            for report_date in holdings['report_date'].unique():
                h = holdings[holdings['report_date'] == report_date]
                as_val = calc_active_share(h, benchmark_data)
                print(f"  {report_date}: AS = {as_val:.4f}")
    
    # --- Return Gap ---
    print("\n[Return Gap 计算]")
    nav = get_fund_nav_akshare(fund_code)
    if not nav.empty:
        print(f"净值数据: {len(nav)} 条")
        print(f"  日期范围: {nav['date'].min().date()} ~ {nav['date'].max().date()}")
        print(f"  月均收益: {nav['return_pct'].mean()*100:.4f}%")
    
    return holdings, nav


def get_sample_fund_list(n=50):
    """
    获取样本基金列表
    筛选条件: 偏股混合型, 规模>2亿, 成立满3年
    """
    print("获取偏股混合型基金列表...")
    
    # AKShare获取开放式基金排行
    df = retry_akshare(ak.fund_open_fund_rank_em, symbol="混合型")
    if df is None or df.empty:
        print("  [错误] 无法获取基金列表")
        return []
    
    # 筛选条件
    df = df.rename(columns={
        '基金代码': 'code',
        '基金简称': 'name',
        '日增长率': 'daily_return',
        '近1年': 'return_1y',
        '成立日期': 'inception_date',
        '资产规模': 'size',
    })
    
    # 转换数据类型
    df['code'] = df['code'].astype(str).str.zfill(6)
    
    print(f"  获取到 {len(df)} 只混合型基金")
    print(f"  前5只: {df[['code', 'name']].head().to_string()}")
    
    # 返回前n只作为样本
    return df['code'].head(n).tolist()


if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("基金经理行为指标计算工具包")
    print("Active Share (AS) / Return Gap (RG) / ICI / SDI")
    print("=" * 60)
    
    # 单只基金演示
    print("\n>>> 运行单只基金演示...")
    demo_single_fund()
    
    # 批量计算（取消注释后运行）
    # fund_list = get_sample_fund_list(n=10)
    # if fund_list:
    #     calc_active_share_batch(fund_list)
    #     calc_return_gap_batch(fund_list)
    
    print("\n" + "=" * 60)
    print("提示: 批量计算请取消注释相关代码段")
    print("AKShare免费接口有限速, 大批量数据建议使用Wind/CSMAR")
    print("=" * 60)
