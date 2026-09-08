# -*- coding: utf-8 -*-
"""
输家型分型规则在六维复合坐标下的重定义（2026-08-26）
背景：_archetype_relink_20260825.py 中"cost<=-0.5 & risk_rsp<=0"在复合空间仅命中 2 只，
原因有两条：(a) 优先级上"行业集中下注型(alloc>=0.5)"先行截流；(b) 硬阈值交集过窄且 cost 维
仅约 200 只有 TO_wind 覆盖。本脚本对比四套规则，选出可支撑检验的输家型定义。

V0 现行规则（对照）
V1 优先级修正：赢家 → 输家 → 集中下注 → 纪律 → 均衡（阈值不变）
V2 分位数交集：cost 与 discipl 双维各取后 20% 的交集（自适应样本，免受阈值刻度影响）
V3 综合分最差十分位：composite 后 10% 直接定义为输家
V4 稳健性：剔除风险转化力维（risk_cnv 含 sharpe8_lag，与 ff5_adj_return 有已知机械关联）后
   重算五维均值 composite_ex，取其后 10% —— 用于检验 V3 的显著性是否为构造性产物。
统一输出：各型 N、有 alpha 样本数、组均 alpha / composite、与均衡型 Welch t。
"""
import pandas as pd, numpy as np, os
from scipy import stats

BASE = r'd:\Desktop\基金经理行为分析研究'
OUT = os.path.join(BASE, 'output')
df = pd.read_csv(os.path.join(OUT, '六维能力复合得分_2026-08-25.csv'))

WIN, BET, DIS, LOSE, MID = '风控择股型(赢家)', '行业集中下注型', '低偏误纪律型', '高换手噪声型(输家)', '均衡型(其他)'
ORDER = [WIN, BET, DIS, LOSE, MID]

is_win = lambda r: r['risk_rsp'] >= 0.5 and r['active'] >= 0.5 and r['discipl'] >= -0.3
is_bet = lambda r: r['alloc'] >= 0.5
is_dis = lambda r: r['discipl'] >= 0.5


def v0(r):
    if is_win(r): return WIN
    if is_bet(r): return BET
    if is_dis(r): return DIS
    if r['cost'] <= -0.5 and r['risk_rsp'] <= 0: return LOSE
    return MID


def v1(r):
    if is_win(r): return WIN
    if r['cost'] <= -0.5 and r['risk_rsp'] <= 0: return LOSE
    if is_bet(r): return BET
    if is_dis(r): return DIS
    return MID


q_cost = df['cost'].quantile(0.20)
q_disc = df['discipl'].quantile(0.20)


def v2(r):
    if is_win(r): return WIN
    if r['cost'] <= q_cost and r['discipl'] <= q_disc: return LOSE
    if is_bet(r): return BET
    if is_dis(r): return DIS
    return MID


q_comp = df['composite'].quantile(0.10)


def v3(r):
    if is_win(r): return WIN
    if r['composite'] <= q_comp: return LOSE
    if is_bet(r): return BET
    if is_dis(r): return DIS
    return MID


DIMS_EX = ['alloc', 'risk_rsp', 'active', 'discipl', 'cost']
df['composite_ex'] = df[DIMS_EX].mean(axis=1, skipna=True)
q_comp_ex = df['composite_ex'].quantile(0.10)


def v4(r):
    if is_win(r): return WIN
    if r['composite_ex'] <= q_comp_ex: return LOSE
    if is_bet(r): return BET
    if is_dis(r): return DIS
    return MID


def evaluate(tag, fn):
    lab = df.apply(fn, axis=1)
    base = df.loc[lab == MID, 'ff5_adj_return'].dropna()
    rows = []
    print(f'\n=== {tag} ===')
    for a in ORDER:
        sub = df[lab == a]
        alpha = sub['ff5_adj_return'].dropna()
        t = p = np.nan
        sig = ''
        if a != MID and len(alpha) >= 5:
            t, p = stats.ttest_ind(alpha, base, equal_var=False)
            sig = '***' if p < 0.01 else ('**' if p < 0.05 else ('*' if p < 0.1 else 'ns'))
        rows.append({'规则版本': tag, '原型': a, '数量': len(sub), '有alpha样本': len(alpha),
                     '组均alpha': round(alpha.mean(), 4) if len(alpha) else np.nan,
                     '组均composite': round(sub['composite'].mean(), 3),
                     'vs均衡_t': round(t, 2) if not np.isnan(t) else '', 'sig': sig})
        ts = f'{t:+.2f}' if not np.isnan(t) else '  n/a'
        am = f'{alpha.mean():+.4f}' if len(alpha) else '   n/a'
        print(f'  {a:14s} N={len(sub):3d}(alpha {len(alpha):3d})  alpha={am}  comp={sub["composite"].mean():+.3f}  t={ts}{sig}')
    w = df.loc[lab == WIN, 'ff5_adj_return'].dropna()
    l = df.loc[lab == LOSE, 'ff5_adj_return'].dropna()
    if len(w) >= 5 and len(l) >= 5:
        t, p = stats.ttest_ind(w, l, equal_var=False)
        sig = '***' if p < 0.01 else ('**' if p < 0.05 else ('*' if p < 0.1 else 'ns'))
        print(f'  >>> 赢家({len(w)}) vs 输家({len(l)}) alpha差={w.mean()-l.mean():+.4f} t={t:+.2f}{sig}')
    else:
        print(f'  >>> 赢家({len(w)}) vs 输家({len(l)}) 样本不足，无法对照')
    return rows, lab


print(f'样本 N={len(df)}；cost 后20%阈值={q_cost:.3f}，discipl 后20%阈值={q_disc:.3f}，composite 后10%阈值={q_comp:.3f}，composite_ex(剔风险转化) 后10%阈值={q_comp_ex:.3f}')
print(f'cost 维非缺失={df["cost"].notna().sum()}，ff5_adj_return 非缺失={df["ff5_adj_return"].notna().sum()}')

all_rows = []
labs = {}
for tag, fn in [('V0 现行(对照)', v0), ('V1 优先级修正', v1), ('V2 分位数交集', v2),
                ('V3 综合分末十分位', v3), ('V4 剔风险转化后末十分位', v4)]:
    r, lab = evaluate(tag, fn)
    all_rows += r
    labs[tag] = lab

res = pd.DataFrame(all_rows)
res.to_csv(os.path.join(OUT, '输家型规则重定义_2026-08-26.csv'), index=False, encoding='utf-8-sig')
det = df[['fund_code', 'composite', 'ff5_adj_return']].copy()
for tag, lab in labs.items():
    det[tag] = lab
det.to_csv(os.path.join(OUT, '输家型规则明细_2026-08-26.csv'), index=False, encoding='utf-8-sig')
print('\n已保存 output/输家型规则重定义_2026-08-26.csv 与 输家型规则明细_2026-08-26.csv')
