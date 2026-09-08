# -*- coding: utf-8 -*-
"""
统计性描述表（2026-08-26）—— 新报告「实证检验/数据来源说明」章节素材
一、样本覆盖：季度数、基金数、逐年基金数
二、15 个成分指标（含 L1 三项）+ 因变量的描述统计（基金层均值口径，1% winsor 后）
三、六维得分与综合能力的描述统计

口径说明：L1 基本面层三项（经理任职天数、基金年龄、基金规模）自 2026-08-26 起
由纯控制变量升级为第六个计分维度的成分，因此进入成分描述统计与覆盖率表；
它们不再单列"控制变量"分块，避免同一变量在表内出现两次。
"""
import pandas as pd, numpy as np, os, json

BASE = r'd:\Desktop\基金经理行为分析研究'
OUT = os.path.join(BASE, 'output')
TODAY = '2026-08-26'

L1 = ['mgr_total_tenure_v2', 'log_fund_age', 'log_aum']
COMP = L1 + ['risk_asym', 'de', 'oc_conf', 'ICI', 'ISDI', 'ARG', 'timing',
             'mppm8_lag', 'sortino8_lag', 'sharpe8_lag', 'SDI', 'lsv']
DV = ['ff5_adj_return', 'quarter_return']
DIM = ['基本面优势', '认知能力', '配置选择能力', '风险应对能力',
       '风险转化能力', '交易执行能力', '综合能力']

CN = {'mgr_total_tenure_v2': '经理累计任职天数', 'log_fund_age': '基金年龄对数',
      'log_aum': '基金规模对数',
      'risk_asym': '风险偏好不对称性', 'de': '处置效应', 'oc_conf': '过度自信（换手×过度交易）',
      'ICI': '行业集中度', 'ISDI': '行业风格漂移指数', 'ARG': '调仓幅度',
      'timing': '下行保护系数（−HM γ）', 'mppm8_lag': '操纵稳健业绩测度MPPM',
      'sortino8_lag': 'Sortino比率', 'sharpe8_lag': 'Sharpe比率',
      'SDI': '策略偏离指数', 'lsv': '交易趋同度LSV',
      'ff5_adj_return': 'FF5 超额收益（基金层alpha）', 'quarter_return': '季度收益'}


def winsor(s, p=0.01):
    return s.clip(s.quantile(p), s.quantile(1 - p))


panel = pd.read_csv(os.path.join(OUT, f'分析面板_v3_{TODAY}.csv'), parse_dates=['report_date'])
tim = pd.read_csv(os.path.join(OUT, f'择时系数_季度HM_{TODAY}.csv')).set_index('fund_code')[['timing']]
score = pd.read_csv(os.path.join(OUT, f'六维能力复合得分_含L1_{TODAY}.csv')).set_index('fund_code')

res = {}

# ---------- 一、样本覆盖 ----------
def qlabel(ts):
    """report_date 为「季末次日」（01-01/04-01/07-01/10-01），回推一季得到真实季度标签。
    例：2020-01-01 实为 2019Q4，2026-07-01 实为 2026Q2。"""
    mapping = {1: (ts.year - 1, 4), 4: (ts.year, 1), 7: (ts.year, 2), 10: (ts.year, 3)}
    y, q = mapping[ts.month]
    return f'{y}Q{q}'


cov = dict(
    起始季度=qlabel(panel['report_date'].min()),
    结束季度=qlabel(panel['report_date'].max()),
    季度数=int(panel['report_date'].nunique()),
    基金数=int(panel['fund_code'].nunique()),
    基金季观测=int(len(panel)),
    可进入横截面回归的基金数=int(panel.groupby('fund_code')['ff5_adj_return'].mean().notna().sum()))
# report_date 为季末次日，直接用 .dt.year 会把 Q4 观测错位到次年，
# 使「2020 年」实为 2019Q4–2020Q3 的并集（279 只）而漏掉 2020Q4（真实年末 286 只）。
# 回推一季取真实年度，保证「某年」= 该年 Q1–Q4 的并集。
_true_year = panel['report_date'].dt.year - (panel['report_date'].dt.month == 1).astype(int)
byyear = panel.assign(y=_true_year).groupby('y')['fund_code'].nunique()
print('=== 一、样本覆盖 ===')
for k, v in cov.items():
    print('  %-24s %s' % (k, v))
print('\n逐年基金数：')
print('  ' + '  '.join('%d:%d' % (y, n) for y, n in byyear.items()))
res['样本覆盖'] = cov
res['逐年基金数'] = {int(y): int(n) for y, n in byyear.items()}

# ---------- 二、指标描述统计（基金层均值口径） ----------
cols = [c for c in COMP + DV if c in panel.columns]
# 观测层覆盖率（基金—季度层面）：与基金层口径并列披露，避免两个数字被混用
obs_cov = {}
for c in COMP:
    if c == 'timing':
        continue
    s = pd.to_numeric(panel[c], errors='coerce') if c in panel.columns else None
    if s is not None:
        obs_cov[c] = round(float(s.notna().mean()), 4)

fm = panel.groupby('fund_code')[cols].mean().join(tim, how='left')
for c in fm.columns:
    fm[c] = pd.to_numeric(fm[c], errors='coerce')
raw_cov = {c: round(float(fm[c].notna().mean()), 4) for c in COMP}
for c in fm.columns:
    fm[c] = winsor(fm[c])
# 基金层零值占比：识别「零值堆积」——大量基金共享同一取值会削弱该成分在复合得分中的区分度
zero_fund = {c: round(float((fm[c].dropna() == 0).mean()), 4)
             for c in COMP if c in fm.columns}

desc = fm[[c for c in COMP + DV if c in fm.columns]].describe(
    percentiles=[.25, .5, .75]).T[['count', 'mean', 'std', 'min', '25%', '50%', '75%', 'max']]
desc.insert(0, '中文名', [CN.get(i, i) for i in desc.index])
desc['count'] = desc['count'].astype(int)
print('\n=== 二、指标描述统计（基金层均值，1% winsor） ===')
print(desc.round(4).to_string())
print('\n基金层覆盖率：' + '  '.join('%s %.1f%%' % (k, v * 100) for k, v in raw_cov.items()))
print('观测层覆盖率：' + '  '.join('%s %.1f%%' % (k, v * 100) for k, v in obs_cov.items()))
res['描述统计'] = json.loads(desc.round(4).to_json())
res['成分覆盖率'] = raw_cov          # 基金层（画像与横截面回归口径）
res['成分覆盖率_观测层'] = obs_cov   # 基金—季度层面（timing 为基金层估计，不适用）
res['成分零值占比_基金层'] = zero_fund  # 零值堆积诊断（缩尾后基金层时序均值口径）

# ---------- 三、六维得分描述统计 ----------
sd = score[DIM].describe(percentiles=[.25, .5, .75]).T[
    ['count', 'mean', 'std', 'min', '25%', '50%', '75%', 'max']]
sd['count'] = sd['count'].astype(int)
print('\n=== 三、六维能力得分描述统计 ===')
print(sd.round(3).to_string())
res['六维描述统计'] = json.loads(sd.round(4).to_json())

# ---------- 四、落盘 ----------
with open(os.path.join(OUT, f'统计性描述_{TODAY}.json'), 'w', encoding='utf-8') as f:
    json.dump(res, f, ensure_ascii=False, indent=2)
desc.round(4).to_csv(os.path.join(OUT, f'统计性描述_指标_{TODAY}.csv'), encoding='utf-8-sig')
print('\n已落盘：统计性描述_%s.json / 统计性描述_指标_%s.csv' % (TODAY, TODAY))
