"""下载400基金全持仓数据（HTML解析版）
原200基金已有全持仓(fund_holdings_full.csv)
新200基金用东方财富API + BeautifulSoup解析HTML获取全持仓
然后统一计算AS并重做MVP
"""
import requests
import re
import time
import os
import pandas as pd
import numpy as np
from bs4 import BeautifulSoup
import statsmodels.api as sm
from statsmodels.regression.linear_model import OLS
import warnings
warnings.filterwarnings('ignore')

data_dir = r"D:\Desktop\基金经理行为分析研究\数据"
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)', 'Referer': 'https://fundf10.eastmoney.com/'}

def parse_holdings_html(text):
    """从东方财富API返回的JavaScript中解析持仓数据"""
    content_match = re.search(r'content:"(.+?)",arryear:', text, re.DOTALL)
    if not content_match:
        return []
    
    html_content = content_match.group(1)
    soup = BeautifulSoup(html_content, 'html.parser')
    
    stocks = []
    for table in soup.find_all('table'):
        for row in table.find_all('tr'):
            cells = row.find_all('td')
            if len(cells) >= 5:
                stock_code = cells[1].get_text(strip=True)
                stock_name = cells[2].get_text(strip=True)
                hold_ratio_str = cells[4].get_text(strip=True)  # 占净值比例
                if stock_code and hold_ratio_str and '%' in hold_ratio_str:
                    try:
                        hr = float(hold_ratio_str.replace('%', ''))
                    except:
                        hr = np.nan
                    stocks.append({
                        'stock_code': stock_code,
                        'stock_name': stock_name,
                        'hold_ratio': hr
                    })
    return stocks

# ============ Step 1: 下载新200基金全持仓 ============
print("=" * 70)
print("Step 1: 下载新200基金全持仓（半年报/年报）")
print("=" * 70)

fund_list = pd.read_csv(os.path.join(data_dir, 'fund_list_new200.csv'), dtype={'code': str})
fund_list['code'] = fund_list['code'].astype(str).str.zfill(6)
new_codes = fund_list['code'].tolist()

all_full_holdings = []

for i, code in enumerate(new_codes):
    for year in [2020, 2021, 2022, 2023, 2024, 2025]:
        for month in ['06', '12']:
            url = f'http://fundf10.eastmoney.com/FundArchivesDatas.aspx?type=jjcc&code={code}&topline=500&year={year}&month={month}'
            try:
                resp = requests.get(url, headers=headers, timeout=15)
                stocks = parse_holdings_html(resp.text)
                rd = f"{year}-{month}-30" if month == '06' else f"{year}-{month}-31"
                q = f"{year}Q2" if month == '06' else f"{year}Q4"
                for s in stocks:
                    all_full_holdings.append({
                        'fund_code': code,
                        'report_date': rd,
                        'quarter': q,
                        'stock_code': s['stock_code'],
                        'stock_name': s['stock_name'],
                        'hold_ratio': s['hold_ratio']
                    })
            except Exception as e:
                pass
            time.sleep(0.15)
    
    if (i + 1) % 20 == 0:
        print(f"  已处理 {i+1}/{len(new_codes)}，累计 {len(all_full_holdings)} 条持仓")

print(f"  完成: {len(all_full_holdings)} 条全持仓")

# 保存
full_df = pd.DataFrame(all_full_holdings)
full_df.to_csv(os.path.join(data_dir, 'fund_holdings_new200_full.csv'), index=False)
print(f"  保存: fund_holdings_new200_full.csv ({len(full_df)} 条, {full_df['fund_code'].nunique()} 只基金)")

# ============ Step 2: 合并400基金全持仓 ============
print("\n" + "=" * 70)
print("Step 2: 合并400基金全持仓")
print("=" * 70)

# 原200基金全持仓
hold_old = pd.read_csv(os.path.join(data_dir, 'fund_holdings_full.csv'), dtype={'fund_code': str})
hold_old['fund_code'] = hold_old['fund_code'].astype(str).str.zfill(6)
print(f"原200基金: {len(hold_old)} 条, {hold_old['fund_code'].nunique()} 只")

# 统一列名
cols = ['fund_code', 'report_date', 'stock_code', 'stock_name', 'hold_ratio']
hold_old_clean = hold_old[[c for c in cols if c in hold_old.columns]].copy()
full_df_clean = full_df[cols].copy()

hold_all = pd.concat([hold_old_clean, full_df_clean], ignore_index=True)
print(f"合并: {len(hold_all)} 条, {hold_all['fund_code'].nunique()} 只基金")

# ============ Step 3: 统一计算AS ============
print("\n" + "=" * 70)
print("Step 3: 统一计算Active Share (全持仓)")
print("=" * 70)

def calc_active_share(holdings_df):
    """用全持仓数据计算AS
    AS = 1/2 * sum(|w_fund_i - w_bench_i|)
    基准: 等权沪深300 (每只股票 1/300)
    """
    results = []
    N_bench = 300  # 沪深300成分股数量
    bench_weight = 1.0 / N_bench  # 等权基准
    
    for (fund, rd), grp in holdings_df.groupby(['fund_code', 'report_date']):
        if pd.isna(rd) or str(rd) == '':
            continue
        
        # 基金持仓权重 (兼容"8.84%"字符串和5.8浮点数两种格式)
        hr = grp['hold_ratio'].astype(str).str.replace('%', '').str.strip()
        fund_weights = pd.to_numeric(hr, errors='coerce').dropna() / 100.0  # 转为比例
        fund_total = fund_weights.sum()
        
        if fund_total == 0:
            continue
        
        # 标准化
        fund_weights = fund_weights / fund_total
        
        n_fund_stocks = len(fund_weights)
        
        # AS = 1/2 * sum_i |w_fund_i - w_bench_i|
        # 基准: 等权沪深300，每只成分股权重 = 1/300
        # 假设基金持有的股票均在沪深300中（中国主动权益基金重仓股多为沪深300成分股）
        # Part 1: 基金持有股票的偏离
        fund_part = sum(abs(w - bench_weight) for w in fund_weights)
        # Part 2: 基准中基金未持有股票的偏离
        bench_not_held = max(0, N_bench - n_fund_stocks) * bench_weight
        as_exact = 0.5 * (fund_part + bench_not_held)
        as_exact = min(1.0, as_exact)
        
        results.append({
            'fund_code': fund,
            'report_date': str(rd),
            'AS': as_exact,
            'n_stocks': n_fund_stocks,
            'top10_concentration': fund_weights.head(10).sum() if n_fund_stocks >= 10 else fund_weights.sum()
        })
    
    return pd.DataFrame(results)

as_all = calc_active_share(hold_all)
print(f"AS计算: {len(as_all)} 条, {as_all['fund_code'].nunique()} 只基金")
print(f"AS均值: {as_all['AS'].mean():.3f}, 标准差: {as_all['AS'].std():.3f}")
print(f"AS范围: [{as_all['AS'].min():.3f}, {as_all['AS'].max():.3f}]")

# ============ Step 4: 计算RG ============
print("\n" + "=" * 70)
print("Step 4: 计算季度收益率和RG")
print("=" * 70)

nav_old = pd.read_csv(os.path.join(data_dir, 'fund_nav_all.csv'), dtype={'fund_code': str})
nav_old['fund_code'] = nav_old['fund_code'].astype(str).str.zfill(6)
nav_new = pd.read_csv(os.path.join(data_dir, 'fund_nav_new200.csv'), dtype={'fund_code': str})
nav_new['fund_code'] = nav_new['fund_code'].astype(str).str.zfill(6)
nav_all = pd.concat([nav_old, nav_new], ignore_index=True)
nav_all['date'] = pd.to_datetime(nav_all['date'])
nav_all['nav'] = pd.to_numeric(nav_all['nav'], errors='coerce')
nav_all = nav_all.dropna(subset=['nav'])

nav_all = nav_all.sort_values(['fund_code', 'date'])
nav_all['year'] = nav_all['date'].dt.year
nav_all['quarter'] = nav_all['date'].dt.quarter
quarter_end = nav_all.groupby(['fund_code', 'year', 'quarter']).last().reset_index()
quarter_end['quarter_return'] = quarter_end.groupby('fund_code')['nav'].pct_change()
quarter_end = quarter_end.dropna(subset=['quarter_return'])
quarter_end['report_date'] = quarter_end['year'].astype(str) + 'Q' + quarter_end['quarter'].astype(str)

benchmark = quarter_end.groupby('report_date')['quarter_return'].mean().reset_index()
benchmark.columns = ['report_date', 'benchmark_return']
panel = quarter_end.merge(benchmark, on='report_date', how='left')
panel['RG'] = panel['quarter_return'] - panel['benchmark_return']
panel['RG'] = panel['RG'].fillna(0)

# ============ Step 5: 合并面板 ============
print("\n" + "=" * 70)
print("Step 5: 合并回归面板")
print("=" * 70)

# 转换AS的report_date为季度格式
def rd_to_q(rd):
    rd = str(rd)
    if 'Q' in rd:
        return rd
    try:
        parts = rd.split('-')
        if len(parts) >= 2:
            year = parts[0]
            month = int(parts[1])
            q = (month - 1) // 3 + 1
            return f"{year}Q{q}"
    except:
        pass
    return rd

as_all['report_date_q'] = as_all['report_date'].apply(rd_to_q)
panel = panel.merge(as_all[['fund_code', 'report_date_q', 'AS']], 
                    left_on=['fund_code', 'report_date'], 
                    right_on=['fund_code', 'report_date_q'], 
                    how='left')
panel['AS'] = panel['AS'].fillna(panel['AS'].mean())

# AS变化率
panel = panel.sort_values(['fund_code', 'report_date'])
panel['AS_lag'] = panel.groupby('fund_code')['AS'].shift(1)
panel['delta_AS'] = panel['AS'] - panel['AS_lag']

# 滞后业绩
panel['future_return'] = panel.groupby('fund_code')['quarter_return'].shift(-1)
panel = panel.dropna(subset=['future_return'])

print(f"面板: {len(panel)} 条, {panel['fund_code'].nunique()} 只基金")
print(f"时间: {panel['report_date'].min()} ~ {panel['report_date'].max()}")
print(f"AS均值: {panel['AS'].mean():.3f}")
print(f"RG均值: {panel['RG'].mean():.4f}")

# ============ Step 6: 回归检验 ============
print("\n" + "=" * 70)
print("Step 6: 回归检验 (全持仓统一精度)")
print("=" * 70)

for col in ['AS', 'RG', 'delta_AS']:
    panel[col + '_std'] = (panel[col] - panel[col].mean()) / (panel[col].std() + 1e-8)
panel['future_return_std'] = (panel['future_return'] - panel['future_return'].mean()) / (panel['future_return'].std() + 1e-8)

results = {}

# H1: AS → 未来业绩
d1 = panel.dropna(subset=['AS_std', 'future_return_std'])
X1 = sm.add_constant(d1['AS_std'])
m1 = OLS(d1['future_return_std'], X1).fit(cov_type='cluster', cov_kwds={'groups': d1['fund_code']})
results['H1'] = (m1.params['AS_std'], m1.tvalues['AS_std'], m1.pvalues['AS_std'], m1.rsquared)

# H3: RG → 未来业绩
d3 = panel.dropna(subset=['RG_std', 'future_return_std'])
X3 = sm.add_constant(d3['RG_std'])
m3 = OLS(d3['future_return_std'], X3).fit(cov_type='cluster', cov_kwds={'groups': d3['fund_code']})
results['H3'] = (m3.params['RG_std'], m3.tvalues['RG_std'], m3.pvalues['RG_std'], m3.rsquared)

# H5: ΔAS → 未来业绩
d5 = panel.dropna(subset=['delta_AS_std', 'future_return_std'])
X5 = sm.add_constant(d5['delta_AS_std'])
m5 = OLS(d5['future_return_std'], X5).fit(cov_type='cluster', cov_kwds={'groups': d5['fund_code']})
results['H5'] = (m5.params['delta_AS_std'], m5.tvalues['delta_AS_std'], m5.pvalues['delta_AS_std'], m5.rsquared)

# 全模型
dfull = panel.dropna(subset=['AS_std', 'RG_std', 'delta_AS_std', 'future_return_std'])
X_full = sm.add_constant(dfull[['AS_std', 'RG_std', 'delta_AS_std']])
m_full = OLS(dfull['future_return_std'], X_full).fit(cov_type='cluster', cov_kwds={'groups': dfull['fund_code']})

# 打印结果
print(f"\n{'假设':<6} {'变量':<8} {'系数':>10} {'t值':>10} {'p值':>10} {'R²':>8} {'结论':>6}")
print("-" * 65)
for h, (coef, t, p, r2) in results.items():
    sig = '***' if p < 0.01 else ('**' if p < 0.05 else ('*' if p < 0.1 else ''))
    passed = '通过' if p < 0.05 else '未通过'
    var_name = {'H1': 'AS', 'H3': 'RG', 'H5': 'ΔAS'}[h]
    print(f"{h:<6} {var_name:<8} {coef:>10.4f} {t:>10.2f} {p:>10.4f} {r2:>8.4f} {passed:>6} {sig}")

print(f"\n全模型 R²={m_full.rsquared:.4f}")
for v in m_full.params.index:
    if v != 'const':
        p = m_full.pvalues[v]
        sig = '***' if p < 0.01 else ('**' if p < 0.05 else ('*' if p < 0.1 else ''))
        print(f"  {v}: β={m_full.params[v]:.4f}, t={m_full.tvalues[v]:.2f}, p={p:.4f} {sig}")

# 对比表
print(f"\n{'='*70}")
print("三轮MVP对比")
print(f"{'='*70}")
print(f"{'指标':<25} {'V1模拟':>10} {'V2原200':>10} {'V3 400全持仓':>15}")
print("-" * 65)
print(f"{'样本量':<25} {'2,400':>10} {'1,597':>10} {len(panel):>15}")
print(f"{'基金数':<25} {'200':>10} {'200':>10} {panel['fund_code'].nunique():>15}")
print(f"{'AS精度':<25} {'模拟':>10} {'全持仓':>10} {'全持仓':>15}")
print(f"{'AS均值':<25} {'0.95':>10} {'0.948':>10} {panel['AS'].mean():>15.3f}")
print(f"{'H1(AS→业绩) t':<25} {'N/A':>10} {'2.57**':>10} {results['H1'][1]:>15.2f}")
print(f"{'H3(RG→业绩) t':<25} {'N/A':>10} {'2.43**':>10} {results['H3'][1]:>15.2f}")
print(f"{'H5(ΔAS→业绩) t':<25} {'N/A':>10} {'2.80***':>10} {results['H5'][1]:>15.2f}")
print(f"{'全模型R²':<25} {'0.365':>10} {'0.024':>10} {m_full.rsquared:>15.4f}")

panel.to_csv(os.path.join(data_dir, 'mvp_panel_400_full.csv'), index=False)
print(f"\n面板已保存: mvp_panel_400_full.csv ({len(panel)} 条)")
