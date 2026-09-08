# -*- coding: utf-8 -*-
"""逐年统计性描述（2026-09-03）

用途：论文改版必备件之一——提示词要求「制作一个表格，展示样本基金在各个年份的
数量、平均规模、平均换手率、平均收益率等，证明样本具有广泛代表性」。

数据来源：output/分析面板_v3_2026-08-26.csv（9,974 基金—季观测，2006Q3–2026Q2）
口径要点：
  - year 列已与 report_date 回推季度口径校对一致（一致率 1.0），直接取用
  - avg_aum 单位＝亿元；quarter_return / excess_return 为小数（0.02＝2%）
  - TO_wind 为 Wind 单边年化换手率（%），半年频，同年内两季取值相同；
    长尾极端值严重（p95≈592%、最大 3780%），故先在观测层 1%/99% 缩尾再聚合
  - ⚠️ ff5_adj_return 是「基金层常数」（每只基金全样本回归的截距），
    逐年取均值无意义，改用观测层变量 excess_return（相对基准超额收益）
  - 逐年先按「基金—年」聚合再跨基金取均值，避免大基金/长样本基金主导
输出：output/逐年统计性描述_2026-09-03.json
"""
import json, os
import numpy as np
import pandas as pd

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, 'output')

panel = pd.read_csv(os.path.join(OUT, '分析面板_v3_2026-08-26.csv'))
panel['TO_wins'] = panel['TO_wind'].clip(panel['TO_wind'].quantile(0.01),
                                         panel['TO_wind'].quantile(0.99))

rows = []
for y, g in panel.groupby('year'):
    # 基金—年 层聚合（避免观测数多的基金权重过大）
    fy = g.groupby('fund_code').agg(
        aum=('avg_aum', 'mean'),
        to=('TO_wins', 'mean'),
        ret=('quarter_return', 'mean'),
        exc=('excess_return', 'mean'),
        nq=('quarter_return', 'size'),
    )
    rows.append({
        '年份': int(y),
        '基金数': int(g['fund_code'].nunique()),
        '观测数': int(len(g)),
        '季度数': int(g['quarter'].nunique()),
        '平均规模_亿': round(float(fy['aum'].mean()), 2),
        '规模中位数_亿': round(float(fy['aum'].median()), 2),
        '平均换手率_单边': None if fy['to'].isna().all() else round(float(fy['to'].mean()), 1),
        '换手率覆盖基金数': int(fy['to'].notna().sum()),
        '平均季度收益': round(float(fy['ret'].mean()) * 100, 2),
        '平均超额收益': None if fy['exc'].isna().all() else round(float(fy['exc'].mean()) * 100, 2),
    })

rows.sort(key=lambda r: r['年份'])

# 全样本汇总行
allf = panel.groupby('fund_code').agg(
    aum=('avg_aum', 'mean'), to=('TO_wins', 'mean'),
    ret=('quarter_return', 'mean'), exc=('excess_return', 'mean'))
summary = {
    '年份': '全样本',
    '基金数': int(panel['fund_code'].nunique()),
    '观测数': int(len(panel)),
    '季度数': int(panel['report_date'].nunique()),
    '平均规模_亿': round(float(allf['aum'].mean()), 2),
    '规模中位数_亿': round(float(allf['aum'].median()), 2),
    '平均换手率_单边': round(float(allf['to'].mean()), 1),
    '换手率覆盖基金数': int(allf['to'].notna().sum()),
    '平均季度收益': round(float(allf['ret'].mean()) * 100, 2),
    '平均超额收益': round(float(allf['exc'].mean()) * 100, 2),
}

# 关键市场区间（用于正文"覆盖完整牛熊周期"的表述）
def _win(a, b, label):
    m = panel[(panel['year'] >= a) & (panel['year'] <= b)]
    return {'区间': label, '年份': f'{a}–{b}',
            '基金数': int(m['fund_code'].nunique()),
            '平均季度收益': round(float(m['quarter_return'].mean()) * 100, 2)}

# ⚠️ 2007–2008 金融危机期仅 1 只基金有数据（代表性不足），不计入区间证据；
#    以 2015 年之后的四段行情作为"覆盖完整牛熊周期"的依据。
windows = [_win(2015, 2016, '杠杆牛熊转换'), _win(2018, 2018, '去杠杆熊市'),
           _win(2019, 2021, '结构性行情'), _win(2022, 2025, '调整与修复')]

res = {
    '口径': {
        '样本期': '2006Q3–2026Q2',
        '来源面板': '分析面板_v3_2026-08-26.csv',
        '规模单位': '亿元',
        '换手率口径': 'Wind 单边年化换手率（%），半年频，观测层 1%/99% 缩尾后聚合',
        '收益率口径': '基金—年均值后再跨基金取均值，单位 %',
        '超额收益口径': '基金季度收益减沪深300季度收益，观测层变量',
        '剔除列': 'ff5_adj_return 为基金层常数（全样本回归截距），逐年无变异，不进入本表',
        '聚合方式': '先按基金—年聚合，再跨基金取均值（每只基金等权）',
    },
    '逐年': rows,
    '全样本': summary,
    '代表性区间': windows,
}

with open(os.path.join(OUT, '逐年统计性描述_2026-09-03.json'), 'w', encoding='utf-8') as f:
    json.dump(res, f, ensure_ascii=False, indent=1)

print(f"{'年份':<6}{'基金数':>6}{'规模(亿)':>10}{'换手%':>8}{'覆盖':>6}{'季收益%':>9}{'超额%':>8}")
for r in rows:
    to = '—' if r['平均换手率_单边'] is None else r['平均换手率_单边']
    print(f"{r['年份']:<6}{r['基金数']:>6}{r['平均规模_亿']:>10}{str(to):>8}"
          f"{r['换手率覆盖基金数']:>6}{r['平均季度收益']:>9}{str(r['平均超额收益']):>8}")
print('全样本:', summary)
print('区间:', windows)
