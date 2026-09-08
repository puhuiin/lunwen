"""获取外部数据：申万行业指数 + 半年报全持仓样本"""
import akshare as ak
import pandas as pd
import os
import time

OUT_DIR = 'D:/Desktop/基金经理行为分析研究/数据/外部数据'
os.makedirs(OUT_DIR, exist_ok=True)

# ========== 1. 申万一级行业指数 ==========
print('='*60)
print('1. 获取申万一级行业指数')
print('='*60)

try:
    # 获取申万行业指数列表
    industry_list = ak.stock_board_industry_index_ths()
    print(f'申万行业指数列表: {len(industry_list)}条')
    print(industry_list.head(10).to_string())
    industry_list.to_csv(os.path.join(OUT_DIR, 'sw_industry_list.csv'), index=False)
    print(f'已保存: sw_industry_list.csv')
except Exception as e:
    print(f'stock_board_industry_index_ths 失败: {e}')
    try:
        # 备用接口
        industry_list = ak.stock_board_industry_name_em()
        print(f'东方财富行业列表: {len(industry_list)}条')
        print(industry_list.head(10).to_string())
        industry_list.to_csv(os.path.join(OUT_DIR, 'em_industry_list.csv'), index=False)
        print(f'已保存: em_industry_list.csv')
    except Exception as e2:
        print(f'备用接口也失败: {e2}')

print()

# ========== 2. 获取申万行业指数历史数据（用于计算行业beta） ==========
print('='*60)
print('2. 获取申万行业指数历史数据')
print('='*60)

try:
    # 获取申万一级行业分类
    sw_industries = ak.stock_board_industry_name_em()
    print(f'行业板块列表: {len(sw_industries)}条')
    print(sw_industries[['板块名称']].head(10).to_string())
    
    # 获取前5个行业的历史指数数据
    industry_returns = []
    for idx, row in sw_industries.head(10).iterrows():
        name = row['板块名称']
        try:
            # 获取行业板块成分股
            hist = ak.stock_board_industry_hist_em(symbol=name, period='日', 
                                                     start_date='20180101', end_date='20260810',
                                                     adjust='')
            if hist is not None and len(hist) > 0:
                hist['行业'] = name
                # 计算月度收益率
                hist['日期'] = pd.to_datetime(hist['日期'])
                hist = hist.set_index('日期')
                hist['月度收益率'] = hist['收盘'].resample('M').last().pct_change()
                industry_returns.append(hist[['行业','月度收益率']].dropna().reset_index())
                print(f'  {name}: {len(hist)}条日数据')
            time.sleep(0.5)
        except Exception as e:
            print(f'  {name} 失败: {e}')
            time.sleep(1)
    
    if industry_returns:
        all_returns = pd.concat(industry_returns, ignore_index=True)
        all_returns.to_csv(os.path.join(OUT_DIR, 'industry_monthly_returns.csv'), index=False)
        print(f'\n已保存: industry_monthly_returns.csv ({len(all_returns)}行)')
except Exception as e:
    print(f'行业指数获取失败: {e}')

print()

# ========== 3. 获取样本基金的半年报全持仓 ==========
print('='*60)
print('3. 获取样本基金半年报全持仓')
print('='*60)

# 取几只样本基金测试
test_funds = ['001412', '001715', '001037', '005827', '162201']

try:
    for fund_code in test_funds:
        try:
            # 获取基金持仓明细（全持仓）
            holdings = ak.fund_portfolio_holdem(symbol=fund_code, date='2024')
            if holdings is not None and len(holdings) > 0:
                print(f'基金{fund_code}: {len(holdings)}条持仓记录')
                print(f'  列: {list(holdings.columns)}')
                print(f'  日期范围: {holdings.iloc[:,1].min()} ~ {holdings.iloc[:,1].max()}' if len(holdings)>0 else '')
                # 检查是否有季度标记
                date_cols = [c for c in holdings.columns if '日期' in c or '季度' in c or '报告' in c]
                if date_cols:
                    print(f'  日期列: {date_cols}')
                    for dc in date_cols:
                        print(f'    {dc}唯一值: {holdings[dc].unique()[:10]}')
                # 保存
                holdings.to_csv(os.path.join(OUT_DIR, f'fund_holdings_{fund_code}.csv'), index=False)
                print(f'  已保存: fund_holdings_{fund_code}.csv')
            else:
                print(f'基金{fund_code}: 无数据')
            time.sleep(1)
        except Exception as e:
            print(f'基金{fund_code} 失败: {e}')
            time.sleep(1)
except Exception as e:
    print(f'基金持仓获取失败: {e}')

print()
print('='*60)
print('获取完成')
print('='*60)
