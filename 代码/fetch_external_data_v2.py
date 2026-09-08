"""获取外部数据v2：正确的akshare函数名"""
import akshare as ak
import pandas as pd
import os
import time

OUT_DIR = 'D:/Desktop/基金经理行为分析研究/数据/外部数据'
os.makedirs(OUT_DIR, exist_ok=True)

# ========== 1. 获取样本基金全持仓 ==========
print('='*60)
print('1. 获取样本基金全持仓 (fund_portfolio_hold_em)')
print('='*60)

test_funds = ['001412', '001715', '005827', '162201', '630001']

for fund_code in test_funds:
    try:
        holdings = ak.fund_portfolio_hold_em(symbol=fund_code, date='2024')
        if holdings is not None and len(holdings) > 0:
            print(f'\n基金{fund_code}: {len(holdings)}条持仓记录')
            print(f'  列: {list(holdings.columns)}')
            # 检查季度标记
            if '季度' in holdings.columns:
                print(f'  季度值: {sorted(holdings["季度"].unique())}')
            if '股票代码' in holdings.columns:
                print(f'  股票数(去重): {holdings["股票代码"].nunique()}')
            # 保存
            holdings.to_csv(os.path.join(OUT_DIR, f'fund_holdings_{fund_code}_2024.csv'), index=False)
            print(f'  已保存: fund_holdings_{fund_code}_2024.csv')
        else:
            print(f'基金{fund_code}: 无数据')
        time.sleep(1.5)
    except Exception as e:
        print(f'基金{fund_code} 失败: {e}')
        time.sleep(2)

# ========== 2. 获取2023年半年报全持仓（验证用） ==========
print('\n' + '='*60)
print('2. 获取2023年半年报全持仓')
print('='*60)

for fund_code in test_funds[:3]:
    try:
        holdings = ak.fund_portfolio_hold_em(symbol=fund_code, date='2023')
        if holdings is not None and len(holdings) > 0:
            if '季度' in holdings.columns:
                # 只取半年报和年报
                semi = holdings[holdings['季度'].astype(str).str.contains('半年|年报|06|12', na=False)]
                if len(semi) > 0:
                    print(f'基金{fund_code} 2023半年报/年报: {len(semi)}条')
                    semi.to_csv(os.path.join(OUT_DIR, f'fund_holdings_{fund_code}_2023_semi.csv'), index=False)
                else:
                    print(f'基金{fund_code} 2023: {len(holdings)}条 (季度值: {holdings["季度"].unique()[:5]})')
        time.sleep(1.5)
    except Exception as e:
        print(f'基金{fund_code} 2023失败: {e}')
        time.sleep(2)

# ========== 3. 获取申万一级行业指数历史数据 ==========
print('\n' + '='*60)
print('3. 获取申万一级行业指数历史数据')
print('='*60)

try:
    # 获取申万一级行业列表
    sw_names = ak.stock_board_industry_name_ths()
    print(f'申万行业列表(ths): {len(sw_names)}条')
    print(sw_names.head(5).to_string())
    
    # 获取前5个行业的历史数据
    industry_data = []
    for idx, row in sw_names.head(5).iterrows():
        name = row.iloc[0] if len(row)>0 else str(row)
        try:
            hist = ak.stock_board_industry_index_ths(symbol=name)
            if hist is not None and len(hist) > 0:
                hist['行业'] = name
                industry_data.append(hist)
                print(f'  {name}: {len(hist)}条')
            time.sleep(1)
        except Exception as e:
            print(f'  {name} 失败: {e}')
            time.sleep(2)
    
    if industry_data:
        all_ind = pd.concat(industry_data, ignore_index=True)
        all_ind.to_csv(os.path.join(OUT_DIR, 'sw_industry_index_hist.csv'), index=False)
        print(f'\n已保存: sw_industry_index_hist.csv ({len(all_ind)}行)')
except Exception as e:
    print(f'申万行业指数获取失败: {e}')
    # 备用：用东方财富接口
    try:
        em_names = ak.stock_board_industry_name_em()
        print(f'东方财富行业列表: {len(em_names)}条')
        # 获取前3个行业的历史K线
        for idx, row in em_names.head(3).iterrows():
            name = row['板块名称']
            try:
                hist = ak.stock_board_industry_hist_em(symbol=name, period='月', 
                                                         start_date='20180101', end_date='20260810')
                if hist is not None and len(hist) > 0:
                    hist['行业'] = name
                    hist.to_csv(os.path.join(OUT_DIR, f'em_industry_{name}_monthly.csv'), index=False)
                    print(f'  {name}: {len(hist)}条月度数据')
                time.sleep(1.5)
            except Exception as e2:
                print(f'  {name} 失败: {e2}')
                time.sleep(2)
    except Exception as e3:
        print(f'备用接口也失败: {e3}')

print('\n' + '='*60)
print('获取完成')
print('='*60)
