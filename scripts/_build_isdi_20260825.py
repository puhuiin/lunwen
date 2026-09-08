# -*- coding: utf-8 -*-
"""
行业风格漂移指数（ISDI, Industry Style Drift Index）
==============================================
构建逻辑（与SDI同构，但基于实际持仓而非净值回归）：
  1. 行业弹性分组：31个申万一级行业按与市场涨跌幅相关性（Beta/弹性评分）
     分为高弹性(11)、中弹性(10)、低弹性(10)三组
     —— 数据源：backups/行业弹性/申万一级行业弹性评分_20260809.xlsx
  2. 基金每期前十大重仓股 → 股票行业映射.csv → 归入高/中/低beta组
  3. 每期构造组权重向量 w_t = (w_high, w_mid, w_low)，组内权重归一化
  4. ISDI_t = Σ|w_t − w_{t-1}|（相邻报告期权重向量的曼哈顿距离）

解读：ISDI越大，基金经理在高beta（进攻型）与低beta（防御型）行业之间
轮动越频繁，行业风格越不稳定。与SDI（基于净值的四宫格风格漂移）互补：
SDI看"结果风格"，ISDI看"配置行为"。

输出：指标计算流水线/data/L2_持仓偏离层/行业风格漂移ISDI.csv
"""
import os
import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
L2 = os.path.join(ROOT, '指标计算流水线', 'data', 'L2_持仓偏离层')
ELASTIC_XLSX = os.path.join(ROOT, 'backups', '行业弹性', '申万一级行业弹性评分_20260809.xlsx')
OUT_CSV = os.path.join(L2, '行业风格漂移ISDI.csv')

# ====== 1. 行业弹性分组 ======
el = pd.read_excel(ELASTIC_XLSX)[['行业', 'Beta', '弹性等级']]
grp_map = dict(zip(el['行业'], el['弹性等级']))
grp_order = ['高弹性', '中弹性', '低弹性']
print(f'行业分组: 高={sum(1 for v in grp_map.values() if v=="高弹性")}, '
      f'中={sum(1 for v in grp_map.values() if v=="中弹性")}, '
      f'低={sum(1 for v in grp_map.values() if v=="低弹性")}')

# ====== 2. 持仓 → 行业 → 弹性组 ======
h = pd.read_csv(os.path.join(L2, '基金持仓明细_全量修正版_v3.csv'), encoding='utf-8-sig')
h['stock_code'] = h['stock_code'].astype(str).str.zfill(6)
h['w'] = pd.to_numeric(h['hold_ratio'], errors='coerce').fillna(0) / 100.0
h['report_date'] = pd.to_datetime(h['report_date'], errors='coerce')

m = pd.read_csv(os.path.join(L2, '股票行业映射.csv'), encoding='utf-8-sig')
m['stock_code'] = m['stock_code'].astype(str).str.zfill(6)
stock2grp = dict(zip(m['stock_code'], m['sw31_industry'].map(grp_map)))

h['grp'] = h['stock_code'].map(stock2grp)
n0 = len(h)
h = h.dropna(subset=['grp'])
print(f'持仓行 {n0:,} → 映射到弹性组后 {len(h):,}（覆盖 {len(h)/n0:.1%}）')

# ====== 3. 每基金-报告期的组权重向量 ======
# 权重 = 该组重仓股市值权重之和 / 三组总权重（重仓股内归一化）
pv = h.pivot_table(index=['fund_code', 'report_date'], columns='grp',
                   values='w', aggfunc='sum').fillna(0.0)
pv = pv.reindex(columns=grp_order)  # 固定列序：高/中/低
tot = pv.sum(axis=1)
pv = pv.div(tot.replace(0, np.nan), axis=0)  # 归一化
pv = pv.dropna()
print(f'基金-报告期观测: {len(pv):,} / 基金数 {pv.index.get_level_values(0).nunique()}')

# ====== 4. 相邻期曼哈顿距离 ======
rows = []
for fund, g in pv.groupby(level=0):
    g = g.sort_index(level=1)
    W = g.values
    dates = g.index.get_level_values(1)
    for i in range(1, len(W)):
        isdi = np.abs(W[i] - W[i - 1]).sum()
        rows.append((fund, dates[i], isdi))

out = pd.DataFrame(rows, columns=['fund_code', 'report_date', 'ISDI'])
# 面板约定：report_date = 报告期末 + 1天（与lib_metrics.to_panel_date一致）
out['report_date'] = pd.to_datetime(out['report_date']) + pd.Timedelta(days=1)

# ====== 5. 保存 ======
out.to_csv(OUT_CSV, index=False, encoding='utf-8-sig')
print(f'\n已保存: {OUT_CSV}')
print(f'ISDI观测: {len(out):,} / 基金数 {out.fund_code.nunique()}')
print(out['ISDI'].describe().round(4).to_string())
