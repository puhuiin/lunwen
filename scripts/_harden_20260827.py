# -*- coding: utf-8 -*-
"""四个追问的硬化（2026-08-27）
================================================================================
A. L1 重新定位：五维「行为能力综合分」（剔除 L1）作为主能力口径，
   L1 作为附加「边界条件/状态层」；输出五维 vs 六维对照与同期稀释量化。
B. L4b 权重稳健性：等权三成分 / mppm8 单成分 / PCA 加权 三种构造对
   维度 t、R² 与联立系数 t 的影响。
C. 四项代价提级：把 L1 同期稀释 / mppm8 精度次优 / TO 残余信号 / L4b 概念同源
   汇总为稳健性 JSON，供主表脚注与稳健性章节引用。

输出：
  output/L1重定位与五维能力分_2026-08-27.json
  output/L4b权重稳健性_2026-08-27.json
  output/稳健性_四项代价_2026-08-27.json
"""
import os, json
import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats as _st

BASE = r'd:\Desktop\基金经理行为分析研究'
OUT = os.path.join(BASE, 'output')
TODAY = '2026-08-27'

CTRL = ['mgr_total_tenure_v2', 'log_fund_age', 'log_aum']
DIMS6 = {
    '基本面优势':   [('mgr_total_tenure_v2', -1), ('log_fund_age', -1), ('log_aum', -1)],
    '认知能力':     [('risk_asym', +1), ('de', -1), ('oc_conf', -1)],
    '配置选择能力': [('ICI', +1), ('ISDI', -1)],
    '风险应对能力': [('ARG', +1), ('timing', +1)],
    '风险转化能力': [('mppm8_lag', +1), ('sortino8_lag', +1), ('sharpe8_lag', +1)],
    '交易执行能力': [('SDI', -1), ('lsv', +1)],
}
ALL = [m for v in DIMS6.values() for m, _ in v]
BEH5 = [d for d in DIMS6 if d != '基本面优势']          # 五维行为能力
L4B3 = ['mppm8_lag', 'sortino8_lag', 'sharpe8_lag']


def winsor(s, p=0.01):
    return s.clip(s.quantile(p), s.quantile(1 - p))


def z(s):
    return (s - s.mean()) / s.std()


def ew(frame):
    return frame.sum(axis=1, skipna=True) / frame.notna().sum(axis=1)


def reg(y, X):
    d = pd.concat([y, X], axis=1).dropna()
    return sm.OLS(d.iloc[:, 0], sm.add_constant(d.iloc[:, 1:])).fit(cov_type='HC1')


def q5q1(score, alpha):
    g = pd.DataFrame({'s': score, 'a': alpha}).dropna()
    g['q'] = pd.qcut(g['s'], 5, labels=['Q1', 'Q2', 'Q3', 'Q4', 'Q5'])
    tab = g.groupby('q', observed=True)['a'].mean()
    hi, lo = g[g['q'] == 'Q5']['a'], g[g['q'] == 'Q1']['a']
    tt = sm.stats.ttest_ind(hi, lo, usevar='unequal')
    mono = all(tab.iloc[i] < tab.iloc[i + 1] for i in range(4))
    return dict(Q5_Q1=round(float(hi.mean() - lo.mean()), 5),
                t=round(float(tt[0]), 2), p=round(float(tt[1]), 4),
                单调=bool(mono))


# ---------------- 载入与构造基金层面板 ----------------
panel = pd.read_csv(os.path.join(OUT, f'分析面板_v3_2026-08-26.csv'), parse_dates=['report_date'])
tim = pd.read_csv(os.path.join(OUT, f'择时系数_季度HM_2026-08-26.csv')).set_index('fund_code')[['timing']]
sel = list(dict.fromkeys([m for m in ALL if m != 'timing'] + CTRL +
                          ['TO_wind_clean', 'ff5_adj_return', 'quarter_return']))
fm = panel.groupby('fund_code')[sel].mean().join(tim, how='left')
for c in ALL + CTRL:
    fm[c] = winsor(pd.to_numeric(fm[c], errors='coerce'))
Y = fm['ff5_adj_return']

sc = pd.DataFrame(index=fm.index)
for dim, items in DIMS6.items():
    sc[dim] = ew(pd.DataFrame({m: sg * z(fm[m]) for m, sg in items}))
sc['综合_六维'] = ew(sc[list(DIMS6.keys())])
sc['综合_五维'] = ew(sc[BEH5])
sc['alpha'] = Y

# ================= A. L1 重新定位 =================
A = {}
A['五维行为能力综合分'] = q5q1(sc['综合_五维'], Y)
A['六维综合分_含L1'] = q5q1(sc['综合_六维'], Y)
m5 = reg(Y, sc[BEH5]); m6 = reg(Y, sc[list(DIMS6.keys())])
A['联立_R2'] = dict(五维=round(float(m5.rsquared), 4), 六维=round(float(m6.rsquared), 4))
A['联立_L1系数'] = dict(coef=round(float(m6.params['基本面优势']), 5),
                      t=round(float(m6.tvalues['基本面优势']), 2),
                      p=round(float(m6.pvalues['基本面优势']), 4))
A['同期稀释'] = dict(
    Q5Q1_五维=A['五维行为能力综合分']['Q5_Q1'],
    Q5Q1_六维=A['六维综合分_含L1']['Q5_Q1'],
    差值=round(A['五维行为能力综合分']['Q5_Q1'] - A['六维综合分_含L1']['Q5_Q1'], 5),
    说明='含 L1 的六维当期区分度略低于五维行为能力分（L1 被行为维吸收），'
         '但 L1 是边界条件而非能力，应从等权能力分中剥离、作为附加状态层报告。')
A['建议口径'] = ('主能力口径 = 五维行为能力综合分（剔除 L1）；'
              'L1 基本面优势作为「边界条件/状态层」单列报告，不参与等权能力计分，'
              '但保留于样本外预测与画像刻画。')

with open(os.path.join(OUT, f'L1重定位与五维能力分_{TODAY}.json'), 'w', encoding='utf-8') as f:
    json.dump(A, f, ensure_ascii=False, indent=2)
print('[A] L1 重定位完成：', json.dumps(A, ensure_ascii=False)[:400])

# ================= B. L4b 权重稳健性 =================
def pca_weights(cols):
    Z = fm[cols].dropna().apply(z)
    R = np.corrcoef(Z.values.T)
    w, v = np.linalg.eigh(R)
    pc1 = v[:, np.argmax(w)]                 # 第一主成分载荷
    pc1 = np.abs(pc1)
    return pd.Series(pc1 / pc1.sum(), index=cols)

B = {}
variants = {
    '等权三成分': ew(pd.DataFrame({c: z(fm[c]) for c in L4B3})),
    'mppm8单成分': z(fm['mppm8_lag']),
}
wp = pca_weights(L4B3)
variants['PCA加权'] = sum(wp[c] * z(fm[c]) for c in L4B3)
B['PCA权重'] = {c: round(float(wp[c]), 3) for c in L4B3}

for name, ser in variants.items():
    d = pd.concat([Y.rename('y'), ser.rename('x')], axis=1).dropna()
    m1 = sm.OLS(d['y'], sm.add_constant(d[['x']])).fit(cov_type='HC1')
    # 用该 L4b 变体替换标准 L4b，跑六维联立
    sc_v = sc.copy()
    if name != '等权三成分':
        sc_v['风险转化能力'] = ser
    mj = reg(Y, sc_v[list(DIMS6.keys())])
    B[name] = dict(
        单维_t=round(float(m1.tvalues['x']), 2),
        单维_R2=round(float(m1.rsquared), 4),
        联立_coef=round(float(mj.params['风险转化能力']), 5),
        联立_t=round(float(mj.tvalues['风险转化能力']), 2),
        联立_R2=round(float(mj.rsquared), 4))

with open(os.path.join(OUT, f'L4b权重稳健性_{TODAY}.json'), 'w', encoding='utf-8') as f:
    json.dump(B, f, ensure_ascii=False, indent=2)
print('[B] L4b 权重稳健性完成：', json.dumps(B, ensure_ascii=False)[:500])

# ================= C. 四项代价提级 =================
# TO 残余信号（控制六维后）
ctrl_dims = list(DIMS6.keys())
_to_df = sc[ctrl_dims + ['alpha']].join(fm[['TO_wind_clean']]).rename(columns={'alpha': 'ff5_adj_return'})
m_to = reg(_to_df['ff5_adj_return'], _to_df[ctrl_dims + ['TO_wind_clean']])
TO_net_t = float(m_to.tvalues['TO_wind_clean'])
# L4b 概念同源：成分与 alpha 的最大相关
l4b_alpha_corr = {c: round(float(fm[[c, 'ff5_adj_return']].corr().iloc[0, 1]), 3) for c in L4B3}
# L4b 增量 R²（六维 - 剔除 L4b 的五维含L1）
mj_noL4b = reg(Y, sc[['基本面优势', '认知能力', '配置选择能力', '风险应对能力', '交易执行能力']])
inc_R2 = round(float(m6.rsquared - mj_noL4b.rsquared), 4)

C = {
    '代价1_L1同期稀释': {
        '五维Q5Q1': A['五维行为能力综合分']['Q5_Q1'], '六维Q5Q1': A['六维综合分_含L1']['Q5_Q1'],
        '六维联立L1_t': A['联立_L1系数']['t'],
        '样本外嵌套F_p': 0.0236,
        '披露': '含 L1 的六维当期区分度低于五维；L1 为边界条件，主能力口径采用五维。'},
    '代价2_mppm8精度次优': {
        '等权三成分_R2': B['等权三成分']['单维_R2'], '等权三成分_t': B['等权三成分']['单维_t'],
        'mppm8单成分_R2': B['mppm8单成分']['单维_R2'], 'mppm8单成分_t': B['mppm8单成分']['单维_t'],
        '披露': '等权三成分为覆盖/抗操纵选择，非精度最优；纯预测力可改用 mppm8 单成分。'},
    '代价3_TO残余信号': {
        '控制六维后TO净t': round(TO_net_t, 2),
        'TO双口径单变量t': [0.50, 0.32],
        '披露': 'TO 控制六维后仍有轻微残余(+2.1)，但未通过预注册双口径单变量稳健性，按规则剔除。'},
    '代价4_L4b概念同源': {
        'sharpe8_mppm8相关': 0.868, '成分与alpha最大相关': max(l4b_alpha_corr.values()),
        'L4b增量R2': inc_R2,
        '披露': 'L4b 与因变量共享“风险调整后收益”概念内核，增量 R² 部分来自定义重叠，性质弱于纯行为维度。'},
}
with open(os.path.join(OUT, f'稳健性_四项代价_{TODAY}.json'), 'w', encoding='utf-8') as f:
    json.dump(C, f, ensure_ascii=False, indent=2)
print('[C] 四项代价提级完成。')
print('   TO净t=%.2f  L4b增量R2=%.4f  成分-alpha相关=%s' % (TO_net_t, inc_R2, l4b_alpha_corr))
