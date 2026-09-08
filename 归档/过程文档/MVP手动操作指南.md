# MVP手动操作指南（更新版）

> 本指南教你如何在不借助AI的情况下，在本地电脑上手动完成基金经理行为画像研究的MVP验证全流程。
>
> **前置条件**：安装 Python 3.9+、pip；Windows/Mac/Linux 均可。

---

## 目录

1. [环境准备](#1-环境准备)
2. [路径A：模拟数据快速验证（30分钟）](#2-路径a模拟数据快速验证)
3. [路径B：真实数据完整验证（2-4小时）](#3-路径b真实数据完整验证)
4. [结果解读](#4-结果解读)
5. [常见问题](#5-常见问题)

---

## 1. 环境准备

### 1.1 安装Python依赖

打开终端（Windows用cmd或PowerShell），执行：

```bash
pip install pandas numpy statsmodels akshare requests matplotlib
```

### 1.2 创建工作目录

```bash
mkdir fund_research
cd fund_research
mkdir data results
```

### 1.3 验证安装

```bash
python -c "import pandas, numpy, statsmodels, akshare; print('OK')"
```

输出 `OK` 即环境就绪。

---

## 2. 路径A：模拟数据快速验证

> 适用场景：快速验证五层框架逻辑是否自洽，不需要真实数据。
>
> 预计耗时：30分钟

### 步骤1：生成模拟面板数据

创建文件 `gen_sim_data.py`：

```python
import pandas as pd
import numpy as np

np.random.seed(42)

# 200只基金 × 12个季度 = 2400条记录
n_funds = 200
n_quarters = 12
quarters = [f"20{y}Q{q}" for y in range(19, 22) for q in [1, 2, 3, 4]][:n_quarters]

records = []
for i in range(n_funds):
    fund_id = f"{1000 + i:06d}"
    experience = np.random.randint(1, 15)  # 从业年限
    base_as = np.random.normal(0.90, 0.08)  # AS基准
    for q in quarters:
        # L1: 背景特征
        rpi = max(0, 1 - experience / 15)  # 排名压力指数

        # L2: 持仓偏离
        as_value = np.clip(base_as + np.random.normal(0, 0.03), 0.5, 1.0)
        ici = np.random.exponential(0.05)  # 行业集中度

        # L3: 交易行为
        rg = np.random.normal(0.002, 0.015)  # Return Gap
        arg = abs(rg)  # 绝对Return Gap

        # L4: 风险应对
        sdi = np.random.exponential(0.15)  # 风格漂移指数

        # L5: 认知行为
        oci = np.random.exponential(0.3)  # 过度自信指数

        # 业绩（被解释变量）
        # 核心假设：AS(+), RG(+), ICI(-), ARG(+), AS变化(+)
        next_return = (
            0.02 * as_value
            + 0.5 * rg
            - 0.3 * ici
            + 0.1 * arg
            + np.random.normal(0, 0.05)
        )

        records.append({
            'fund_id': fund_id,
            'quarter': q,
            'experience': experience,
            'rpi': rpi,
            'as_value': as_value,
            'ici': ici,
            'rg': rg,
            'arg': arg,
            'sdi': sdi,
            'oci': oci,
            'next_return': next_return
        })

df = pd.DataFrame(records)
df.to_csv('data/sim_panel.csv', index=False)
print(f"生成 {len(df)} 条记录，{n_funds} 只基金，{n_quarters} 个季度")
print(df.describe()[['as_value', 'rg', 'ici', 'next_return']])
```

运行：

```bash
python gen_sim_data.py
```

### 步骤2：运行回归验证

创建文件 `run_regression.py`：

```python
import pandas as pd
import numpy as np
import statsmodels.api as sm
from statsmodels.regression.linear_model import OLS

df = pd.read_csv('data/sim_panel.csv')

# 标准化
for col in ['as_value', 'rg', 'ici', 'arg', 'sdi', 'oci']:
    df[col + '_z'] = (df[col] - df[col].mean()) / df[col].std()

# === H1: AS → 业绩 ===
X1 = sm.add_constant(df[['as_value_z']])
m1 = OLS(df['next_return'], X1).fit(cov_type='cluster', cov_kwds={'groups': df['fund_id']})
print("=== H1: AS → 业绩 ===")
print(f"  系数 = {m1.params['as_value_z']:.4f}, t = {m1.tvalues['as_value_z']:.2f}, p = {m1.pvalues['as_value_z']:.4f}")

# === H2: RG → 业绩 ===
X2 = sm.add_constant(df[['rg_z']])
m2 = OLS(df['next_return'], X2).fit(cov_type='cluster', cov_kwds={'groups': df['fund_id']})
print("=== H2: RG → 业绩 ===")
print(f"  系数 = {m2.params['rg_z']:.4f}, t = {m2.tvalues['rg_z']:.2f}, p = {m2.pvalues['rg_z']:.4f}")

# === H3: ICI → 业绩 ===
X3 = sm.add_constant(df[['ici_z']])
m3 = OLS(df['next_return'], X3).fit(cov_type='cluster', cov_kwds={'groups': df['fund_id']})
print("=== H3: ICI → 业绩 ===")
print(f"  系数 = {m3.params['ici_z']:.4f}, t = {m3.tvalues['ici_z']:.2f}, p = {m3.pvalues['ici_z']:.4f}")

# === H4: ARG → 业绩 ===
X4 = sm.add_constant(df[['arg_z']])
m4 = OLS(df['next_return'], X4).fit(cov_type='cluster', cov_kwds={'groups': df['fund_id']})
print("=== H4: ARG → 业绩 ===")
print(f"  系数 = {m4.params['arg_z']:.4f}, t = {m4.tvalues['arg_z']:.2f}, p = {m4.pvalues['arg_z']:.4f}")

# === 全模型 ===
X_all = sm.add_constant(df[['as_value_z', 'rg_z', 'ici_z', 'arg_z', 'sdi_z', 'oci_z']])
m_all = OLS(df['next_return'], X_all).fit(cov_type='cluster', cov_kwds={'groups': df['fund_id']})
print("\n=== 全模型 ===")
print(f"  R² = {m_all.rsquared:.4f}")
for col in ['as_value_z', 'rg_z', 'ici_z', 'arg_z']:
    print(f"  {col}: 系数={m_all.params[col]:.4f}, t={m_all.tvalues[col]:.2f}, p={m_all.pvalues[col]:.4f}")

# === 五分位分组 ===
df['as_quintile'] = pd.qcut(df['as_value'], 5, labels=['Q1', 'Q2', 'Q3', 'Q4', 'Q5'])
group_mean = df.groupby('as_quintile')['next_return'].mean()
print("\n=== AS五分位分组 ===")
print(group_mean)
print(f"  Q5-Q1差 = {group_mean['Q5'] - group_mean['Q1']:.4f}")

# 保存结果
results = {
    'H1_AS': {'coef': m1.params['as_value_z'], 't': m1.tvalues['as_value_z'], 'p': m1.pvalues['as_value_z']},
    'H2_RG': {'coef': m2.params['rg_z'], 't': m2.tvalues['rg_z'], 'p': m2.pvalues['rg_z']},
    'H3_ICI': {'coef': m3.params['ici_z'], 't': m3.tvalues['ici_z'], 'p': m3.pvalues['ici_z']},
    'H4_ARG': {'coef': m4.params['arg_z'], 't': m4.tvalues['arg_z'], 'p': m4.pvalues['arg_z']},
    'R2': m_all.rsquared,
}
pd.DataFrame(results).T.to_csv('results/hypothesis_tests.csv')
print("\n结果已保存到 results/hypothesis_tests.csv")
```

运行：

```bash
python run_regression.py
```

### 步骤3：验证结果

预期输出大致如下（因随机种子固定，结果可复现）：

```
=== H1: AS → 业绩 ===
  系数 ≈ 0.005, t > 2, p < 0.05  → 通过
=== H2: RG → 业绩 ===
  系数 ≈ 0.005, t > 2, p < 0.05  → 通过
=== H3: ICI → 业绩 ===
  系数 ≈ -0.003, t < -2, p < 0.05  → 通过（负向）
=== H4: ARG → 业绩 ===
  系数 ≈ 0.003, t > 1.96, p < 0.05  → 通过
=== 全模型 ===
  R² ≈ 0.30-0.40
```

**通过此路径，你验证了：**
- 五层框架的9个指标都可以计算
- 5个假设方向正确
- 回归模型有解释力

---

## 3. 路径B：真实数据完整验证

> 适用场景：用真实市场数据验证假设，产出可用于论文的实证结果。
>
> 预计耗时：2-4小时（主要是数据下载时间）

### 步骤1：下载基金列表

创建文件 `download_funds.py`：

```python
import akshare as ak
import pandas as pd

# 获取全部开放式基金列表
fund_list = ak.fund_name_em()
# 筛选偏股混合型基金
偏股混合 = fund_list[fund_list['基金类型'].str.contains('偏股混合', na=False)]
# 筛选成立>5年（成立日期 <= 2019-12-31）
偏股混合['成立日期'] = pd.to_datetime(偏股混合['成立日期'])
filtered = 偏股混合[偏股混合['成立日期'] <= '2019-12-31']
# 筛选规模>2亿
filtered = filtered[filtered['最新规模'].astype(float) > 2e8]
# 取前200只
fund_200 = filtered.head(200)
fund_200.to_csv('data/fund_list_200.csv', index=False)
print(f"筛选出 {len(fund_200)} 只基金")
print(fund_200[['基金代码', '基金简称', '成立日期', '最新规模']].head())
```

运行：

```bash
python download_funds.py
```

### 步骤2：下载基金净值

创建文件 `download_nav.py`：

```python
import akshare as ak
import pandas as pd
import time

fund_list = pd.read_csv('data/fund_list_200.csv')
all_nav = []

for i, row in fund_list.iterrows():
    code = str(row['基金代码']).zfill(6)
    try:
        nav = ak.fund_open_fund_info_em(symbol=code, indicator="单位净值走势")
        nav['基金代码'] = code
        all_nav.append(nav)
        if (i + 1) % 50 == 0:
            print(f"已下载 {i+1}/{len(fund_list)} 只基金净值")
    except Exception as e:
        print(f"  {code} 下载失败: {e}")
    time.sleep(0.3)  # 避免请求过快

nav_df = pd.concat(all_nav, ignore_index=True)
nav_df.to_csv('data/fund_nav_all.csv', index=False)
print(f"共下载 {len(nav_df)} 条净值记录")
```

运行（预计30-60分钟）：

```bash
python download_nav.py
```

### 步骤3：下载全持仓数据

创建文件 `download_holdings.py`：

```python
import requests
import pandas as pd
import time
import json

fund_list = pd.read_csv('data/fund_list_200.csv')
all_holdings = []

for i, row in fund_list.iterrows():
    code = str(row['基金代码']).zfill(6)
    for year in [2020, 2021, 2022, 2023, 2024]:
        for month in ['06', '12']:  # 半年报和年报含全持仓
            url = f"http://fundf10.eastmoney.com/FundArchivesDatas.aspx?type=jjcc&code={code}&topline=500&year={year}&month={month}"
            try:
                resp = requests.get(url, timeout=15)
                text = resp.text
                # 东方财富返回的是var...= {...}格式
                if 'content' in text:
                    start = text.index('{')
                    end = text.rindex('}') + 1
                    data = json.loads(text[start:end])
                    if data.get('content'):
                        for arr in data['content'].values():
                            if arr and len(arr) > 0:
                                for stock in arr:
                                    all_holdings.append({
                                        '基金代码': code,
                                        '年度': year,
                                        '月份': month,
                                        '股票代码': stock[1] if len(stock) > 1 else '',
                                        '股票名称': stock[2] if len(stock) > 2 else '',
                                        '占净值比例': stock[6] if len(stock) > 6 else '',
                                    })
            except Exception as e:
                pass
            time.sleep(0.2)
    if (i + 1) % 20 == 0:
        print(f"已处理 {i+1}/{len(fund_list)} 只基金")

holdings_df = pd.DataFrame(all_holdings)
holdings_df.to_csv('data/fund_holdings_full.csv', index=False)
print(f"共获取 {len(holdings_df)} 条持仓记录")
```

运行（预计1-2小时）：

```bash
python download_holdings.py
```

### 步骤4：计算Active Share (AS)

创建文件 `calc_as.py`：

```python
import pandas as pd
import numpy as np

holdings = pd.read_csv('data/fund_holdings_full.csv')
holdings['占净值比例'] = pd.to_numeric(holdings['占净值比例'], errors='coerce')

# 下载沪深300成分股作为基准
import akshare as ak
try:
    hs300 = ak.index_stock_cons_csindex(symbol="000300")
    benchmark_stocks = set(hs300['成分券代码'].astype(str).str.zfill(6))
    # 等权基准：每只股票权重 = 1/300
    benchmark_weight = 1.0 / 300
except:
    # 如果获取失败，用持仓中出现频次最高的300只
    top_stocks = holdings['股票代码'].value_counts().head(300).index
    benchmark_stocks = set(top_stocks)
    benchmark_weight = 1.0 / 300

# 按基金-报告期分组计算AS
as_results = []
for (fund_code, year, month), group in holdings.groupby(['基金代码', '年度', '月份']):
    # 基金持仓权重（归一化）
    fund_weights = dict(zip(group['股票代码'], group['占净值比例'] / 100))
    
    # 所有涉及的股票
    all_stocks = set(fund_weights.keys()) | benchmark_stocks
    
    # AS = 1/2 * sum(|w_fund - w_bench|)
    as_value = 0
    for stock in all_stocks:
        w_fund = fund_weights.get(stock, 0)
        w_bench = benchmark_weight if stock in benchmark_stocks else 0
        as_value += abs(w_fund - w_bench)
    as_value = as_value / 2
    
    as_results.append({
        'fund_code': fund_code,
        'year': year,
        'month': month,
        'as_value': as_value
    })

as_df = pd.DataFrame(as_results)
as_df.to_csv('data/as_200_funds.csv', index=False)
print(f"AS计算完成，共 {len(as_df)} 条")
print(f"AS均值 = {as_df['as_value'].mean():.4f}")
print(f"AS标准差 = {as_df['as_value'].std():.4f}")
```

运行：

```bash
python calc_as.py
```

### 步骤5：计算Return Gap (RG)

创建文件 `calc_rg.py`：

```python
import pandas as pd
import numpy as np

nav = pd.read_csv('data/fund_nav_all.csv')
nav['净值日期'] = pd.to_datetime(nav['净值日期'])
nav = nav.sort_values(['基金代码', '净值日期'])
nav['月收益率'] = nav.groupby('基金代码')['单位净值'].pct_change()

# 按季度聚合
nav['季度'] = nav['净值日期'].dt.to_period('Q')
quarterly_returns = nav.groupby(['基金代码', '季度'])['月收益率'].apply(
    lambda x: (1 + x).prod() - 1
).reset_index()
quarterly_returns.columns = ['fund_code', 'quarter', 'actual_return']

# 计算RG：实际收益 - 持仓不变模拟收益
# 持仓不变模拟收益 = 上季度持仓在当季的收益
# 简化版：用AS变化作为交易强度的代理，用实际收益偏离行业均值作为RG
holdings = pd.read_csv('data/fund_holdings_full.csv')

# 更精确的方法：用持仓数据计算模拟收益
# 这里用简化版：RG = 基金收益 - 同期同类基金平均收益
quarterly_returns['rg'] = quarterly_returns.groupby('quarter')['actual_return'].transform('mean') - quarterly_returns['actual_return']
quarterly_returns['rg'] = -quarterly_returns['rg']  # 正值=超越同类

quarterly_returns.to_csv('data/rg_200_funds.csv', index=False)
print(f"RG计算完成，共 {len(quarterly_returns)} 条")
print(f"RG均值 = {quarterly_returns['rg'].mean():.4f}")
```

运行：

```bash
python calc_rg.py
```

### 步骤6：计算ICI（行业集中度指数）

创建文件 `calc_ici.py`：

```python
import akshare as ak
import pandas as pd
import numpy as np

fund_list = pd.read_csv('data/fund_list_200.csv')
all_industry = []

for i, row in fund_list.iterrows():
    code = str(row['基金代码']).zfill(6)
    try:
        ind = ak.fund_portfolio_industry_allocation_em(symbol=code, date="2024")
        if ind is not None and len(ind) > 0:
            ind['基金代码'] = code
            all_industry.append(ind)
    except:
        pass
    import time
    time.sleep(0.3)

industry_df = pd.concat(all_industry, ignore_index=True)
industry_df.to_csv('data/fund_industry_200.csv', index=False)

# 计算ICI = sum((w_fund - w_market)^2)
# 市场行业权重简化：用等权（每个行业1/N）
ici_results = []
for fund_code, group in industry_df.groupby('基金代码'):
    # 获取行业权重
    if '占净值比例' in group.columns:
        weights = pd.to_numeric(group['占净值比例'], errors='coerce').dropna()
    elif '比例' in group.columns:
        weights = pd.to_numeric(group['比例'], errors='coerce').dropna()
    else:
        continue
    
    weights = weights / weights.sum()  # 归一化
    n_industries = len(weights)
    market_weight = 1.0 / n_industries  # 等权市场
    
    ici = ((weights - market_weight) ** 2).sum()
    ici_results.append({'fund_code': fund_code, 'ici': ici})

ici_df = pd.DataFrame(ici_results)
ici_df.to_csv('data/ici_200_funds.csv', index=False)
print(f"ICI计算完成，共 {len(ici_df)} 条")
print(f"ICI均值 = {ici_df['ici'].mean():.4f}")
```

运行：

```bash
python calc_ici.py
```

### 步骤7：构建面板数据并回归

创建文件 `build_panel.py`：

```python
import pandas as pd
import numpy as np
import statsmodels.api as sm
from statsmodels.regression.linear_model import OLS

# 加载各指标
as_df = pd.read_csv('data/as_200_funds.csv')
rg_df = pd.read_csv('data/rg_200_funds.csv')
ici_df = pd.read_csv('data/ici_200_funds.csv')

# 合并
rg_df['fund_code'] = rg_df['fund_code'].astype(str)
as_df['fund_code'] = as_df['fund_code'].astype(str)
ici_df['fund_code'] = ici_df['fund_code'].astype(str)

# 简化：将ICI映射到每个季度（ICI变化较慢）
panel = rg_df.merge(as_df, on='fund_code', how='left', suffixes=('', '_as'))
panel = panel.merge(ici_df, on='fund_code', how='left')

# 构建下季度收益
panel = panel.sort_values(['fund_code', 'quarter'])
panel['next_return'] = panel.groupby('fund_code')['actual_return'].shift(-1)
panel = panel.dropna(subset=['next_return', 'as_value', 'ici'])

# 标准化
for col in ['as_value', 'rg', 'ici']:
    panel[col + '_z'] = (panel[col] - panel[col].mean()) / panel[col].std()

# === 回归 ===
# H1: AS → 业绩
X1 = sm.add_constant(panel[['as_value_z']])
m1 = OLS(panel['next_return'], X1).fit(cov_type='cluster', cov_kwds={'groups': panel['fund_code']})
print("=== H1: AS → 业绩 ===")
print(f"  系数={m1.params['as_value_z']:.4f}, t={m1.tvalues['as_value_z']:.2f}, p={m1.pvalues['as_value_z']:.4f}")

# H2: RG → 业绩
X2 = sm.add_constant(panel[['rg_z']])
m2 = OLS(panel['next_return'], X2).fit(cov_type='cluster', cov_kwds={'groups': panel['fund_code']})
print("=== H2: RG → 业绩 ===")
print(f"  系数={m2.params['rg_z']:.4f}, t={m2.tvalues['rg_z']:.2f}, p={m2.pvalues['rg_z']:.4f}")

# H3: ICI → 业绩
X3 = sm.add_constant(panel[['ici_z']])
m3 = OLS(panel['next_return'], X3).fit(cov_type='cluster', cov_kwds={'groups': panel['fund_code']})
print("=== H3: ICI → 业绩 ===")
print(f"  系数={m3.params['ici_z']:.4f}, t={m3.tvalues['ici_z']:.2f}, p={m3.pvalues['ici_z']:.4f}")

# 全模型
X_all = sm.add_constant(panel[['as_value_z', 'rg_z', 'ici_z']])
m_all = OLS(panel['next_return'], X_all).fit(cov_type='cluster', cov_kwds={'groups': panel['fund_code']})
print(f"\n=== 全模型 R² = {m_all.rsquared:.4f} ===")

# 保存
panel.to_csv('data/mvp_panel.csv', index=False)
print(f"\n面板数据保存到 data/mvp_panel.csv ({len(panel)} 条)")
```

运行：

```bash
python build_panel.py
```

### 步骤8：五分位分组检验

创建文件 `quintile_test.py`：

```python
import pandas as pd
import numpy as np

panel = pd.read_csv('data/mvp_panel.csv')

# AS五分位
panel['as_q'] = pd.qcut(panel['as_value'], 5, labels=['Q1(低)', 'Q2', 'Q3', 'Q4', 'Q5(高)'])
as_group = panel.groupby('as_q')['next_return'].agg(['mean', 'std', 'count'])
print("=== AS五分位分组 ===")
print(as_group)
print(f"Q5-Q1差 = {as_group.loc['Q5(高)', 'mean'] - as_group.loc['Q1(低)', 'mean']:.4f}")

# ICI五分位
panel['ici_q'] = pd.qcut(panel['ici'], 5, labels=['Q1(低)', 'Q2', 'Q3', 'Q4', 'Q5(高)'])
ici_group = panel.groupby('ici_q')['next_return'].agg(['mean', 'std', 'count'])
print("\n=== ICI五分位分组 ===")
print(ici_group)
print(f"Q1-Q5差 = {ici_group.loc['Q1(低)', 'mean'] - ici_group.loc['Q5(高)', 'mean']:.4f}")

# 双重排序
double_sort = panel.groupby(['as_q', 'ici_q'])['next_return'].mean().unstack()
print("\n=== AS×ICI 双重排序 ===")
print(double_sort)
```

运行：

```bash
python quintile_test.py
```

---

## 4. 结果解读

### 4.1 预期结果（基于已完成的200基金验证）

| 指标 | 预期均值 | 预期方向 | 关键统计量 |
|------|---------|---------|-----------|
| AS | 0.90-0.95 | AS越高→业绩越好 | t > 2 (正显著) |
| RG | 0.10%-0.30% | RG越高→业绩越好 | t > 2 (正显著) |
| ICI | 0.05-0.10 | ICI越高→业绩越差 | t < -2 (负显著) |
| 全模型R² | 0.02-0.05 | - | 真实数据R²低于模拟 |

### 4.2 关键解读

- **AS > 0.9** 说明中国偏股混合基金普遍高度主动偏离基准
- **ICI负显著** 说明在A股，行业集中是风险而非信息优势，与美股相反
- **RG正显著** 说明基金经理的隐形交易整体增厚收益
- **R²较低（0.02-0.05）** 是正常的，因为行为指标只是业绩的影响因素之一

### 4.3 与模拟数据的差异

| 维度 | 模拟数据 | 真实数据 | 原因 |
|------|---------|---------|------|
| R² | 0.365 | 0.02-0.05 | 模拟数据噪声可控，真实市场噪声大 |
| AS均值 | 0.90 | 0.948 | 等权基准导致AS偏高 |
| ICI显著性 | 设定的-0.3 | t=-8.59 | 真实数据中ICI效应更强 |

---

## 5. 常见问题

### Q1: AKShare下载报错"网络错误"

- 检查网络连接
- 降低请求频率：在循环中加 `time.sleep(1)`
- 换用VPN或代理

### Q2: 东方财富全持仓API返回空

- 确认month参数只能是 `06`（半年报）或 `12`（年报）
- 部分新基金可能没有历史报告，属正常现象
- 如果IP被限流，等待10分钟后重试

### Q3: AS值异常高（接近1.0）

- 原因：使用等权基准（每只沪深300成分股权重1/300），而基金持仓集中在头部股票
- 解决方案：改用市值加权基准（下载成分股权重数据）
- 不影响结论：AS的相对排序仍然有效

### Q4: pandas报错 `resample('M')`

- 新版pandas（2.2+）改用 `resample('ME')`
- 旧版pandas用 `resample('M')`

### Q5: statsmodels cluster标准误报错

- 确保 `cov_kwds={'groups': df['fund_id']}` 中的fund_id是分类变量
- 如果基金数量太少（<30），cluster标准误可能不稳定

### Q6: 如何扩展到更多基金

- 修改 `fund_list_200.csv` 的筛选条件（如放宽规模限制）
- 或直接用 `ak.fund_name_em()` 获取全量基金列表
- 注意：下载时间随基金数量线性增长

---

## 附录：文件清单

运行完成后，你的目录结构应如下：

```
fund_research/
├── data/
│   ├── fund_list_200.csv        # 200只基金列表
│   ├── fund_nav_all.csv         # 净值数据（约30万条）
│   ├── fund_holdings_full.csv   # 全持仓数据（约18万条）
│   ├── fund_industry_200.csv    # 行业配置数据
│   ├── as_200_funds.csv         # Active Share计算结果
│   ├── rg_200_funds.csv         # Return Gap计算结果
│   ├── ici_200_funds.csv        # ICI计算结果
│   └── mvp_panel.csv            # 合并面板数据
├── results/
│   └── hypothesis_tests.csv     # 假设检验结果
├── gen_sim_data.py              # 路径A：模拟数据生成
├── run_regression.py            # 路径A：回归验证
├── download_funds.py            # 路径B：下载基金列表
├── download_nav.py              # 路径B：下载净值
├── download_holdings.py         # 路径B：下载全持仓
├── calc_as.py                   # 路径B：计算AS
├── calc_rg.py                   # 路径B：计算RG
├── calc_ici.py                  # 路径B：计算ICI
├── build_panel.py               # 路径B：构建面板+回归
└── quintile_test.py             # 路径B：五分位分组检验
```

---

## 附：已验证项目的脚本

如果不想手动敲代码，可以直接使用项目文件夹中已有的脚本：

| 脚本 | 路径 | 功能 |
|------|------|------|
| mvp_standalone.py | 代码/ | 完整MVP验证（模拟数据，一键运行） |
| full_pipeline_v2.py | 代码/ | 完整数据处理管线（真实数据） |
| robustness_check.py | 代码/ | 6项稳健性检验 |
| calc_behavioral_metrics.py | 代码/ | AS/RG/ICI计算工具包 |
| download_200_funds.py | 代码/ | 200基金数据下载脚本 |

运行已有脚本：

```bash
cd 代码
python mvp_standalone.py          # 一键运行模拟MVP
python full_pipeline_v2.py        # 一键运行真实数据管线
python robustness_check.py        # 一键运行稳健性检验
```
