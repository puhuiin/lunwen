# -*- coding: utf-8 -*-
"""① 参考文献_定稿 JSON 补录 [62] Berk & Green (2004)；② 指标文献映射 CSV 头部插入 L1 三行。"""
import csv
import io
import json

OUT = r'd:\Desktop\基金经理行为分析研究\output'

# ① 补录参考文献 [62]
ref_path = OUT + r'\参考文献_定稿_2026-08-26.json'
with io.open(ref_path, encoding='utf-8') as f:
    REF = json.load(f)
REF['62'] = ('BERK J B, GREEN R C. Mutual fund flows and performance in rational markets[J]. '
             'Journal of Political Economy, 2004, 112(5): 1269-1295.')
with io.open(ref_path, 'w', encoding='utf-8') as f:
    json.dump(REF, f, ensure_ascii=False, indent=2)
print('references:', len(REF))

# ② 指标文献映射 CSV 插入 L1 三行（放在最前，使理论表按 L1→L5 顺序渲染）
map_path = OUT + r'\指标文献映射_2026-08-26.csv'
with io.open(map_path, encoding='utf-8-sig') as f:
    rows = list(csv.DictReader(f))
    cols = list(rows[0].keys())

CE = ('CHEVALIER J, ELLISON G. Career concerns of mutual fund managers[J]. '
      'The Quarterly Journal of Economics, 1999, 114(2): 389-432.')
BG = REF['62']

L1_ROWS = [
    {'维度': 'L1 基本面层', '指标': 'mgr_total_tenure_v2 任职年限', '定向符号': '-',
     '主引文献序号': '26',
     '文献依据说明': 'Chevalier & Ellison (1999) 经验悖论与职业顾虑：新任经理更努力，'
                    '激励随任期衰减；本样本单变量 t=−1.85*',
     '主引文献': CE},
    {'维度': 'L1 基本面层', '指标': 'log_fund_age log 基金年龄', '定向符号': '-',
     '主引文献序号': '62',
     '文献依据说明': 'Berk & Green (2004) 理性市场模型：业绩吸引资金流入，规模膨胀与组织'
                    '老化侵蚀 alpha（新基金效应）；本样本单变量 t=−4.13***',
     '主引文献': BG},
    {'维度': 'L1 基本面层', '指标': 'log_aum log 基金规模', '定向符号': '-',
     '主引文献序号': '62',
     '文献依据说明': 'Berk & Green (2004) 规模不经济：规模膨胀稀释超额收益；'
                    '本样本单变量 t=−1.16（方向一致）',
     '主引文献': BG},
]
rows = L1_ROWS + [r for r in rows if r['维度'] != 'L1 基本面层']
with io.open(map_path, 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.DictWriter(f, fieldnames=cols)
    w.writeheader()
    w.writerows(rows)
print('map rows:', len(rows))
for r in rows[:4]:
    print(' ', r['维度'], '|', r['指标'], '|', r['主引文献序号'])
