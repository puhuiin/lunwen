# -*- coding: utf-8 -*-
"""显著性审查：面板不显著成分的留一法稳健性（2026-09-02）
回答：oc_conf（规格II ns）与 lsv（规格II ns）剔除后，其所属维度与总结论是否改变。
"""
import json, os
import numpy as np, pandas as pd
import statsmodels.api as sm

BASE = r'd:\Desktop\基金经理行为分析研究'
OUT = os.path.join(BASE, 'output')
CTRL = ['mgr_total_tenure_v2', 'log_fund_age', 'log_aum']
DIMS = {
    '认知能力': [('risk_asym', +1), ('de', -1), ('oc_conf', -1), ('anchor_high', +1)],
    '配置选择能力': [('ICI', +1), ('ISDI', -1)],
    '风险应对能力': [('ARG', +1), ('timing', +1)],
    '风险转化能力': [('mppm8_lag', +1), ('sortino8_lag', +1), ('sharpe8_lag', +1)],
    '交易执行能力': [('SDI', -1), ('lsv', +1)],
}
ALL_COMP = [m for v in DIMS.values() for m, _ in v]

winsor = lambda s, p=0.01: s.clip(s.quantile(p), s.quantile(1 - p))
z = lambda s: (s - s.mean()) / s.std()
ew = lambda f: f.sum(axis=1, skipna=True) / f.notna().sum(axis=1)


def reg(y, X):
    d = pd.concat([y, X], axis=1).dropna()
    return sm.OLS(d.iloc[:, 0], sm.add_constant(d.iloc[:, 1:])).fit(cov_type='HC1')


panel = pd.read_csv(os.path.join(OUT, '分析面板_v3_2026-08-26.csv'), parse_dates=['report_date'])
tim = pd.read_csv(os.path.join(OUT, '择时系数_季度HM_2026-08-26.csv')).set_index('fund_code')[['timing']]
base = [c for c in ALL_COMP if c != 'timing']
fm = panel.groupby('fund_code')[base + CTRL + ['ff5_adj_return']].mean().join(tim, how='left')
for c in ALL_COMP + CTRL:
    fm[c] = winsor(fm[c])
fm['L1'] = ew(pd.DataFrame({c: -z(fm[c]) for c in CTRL}))
Y = fm['ff5_adj_return']

res = {}


def build(dims):
    sc = pd.DataFrame(index=fm.index)
    for d, items in dims.items():
        sc[d] = ew(pd.DataFrame({m: s * z(fm[m]) for m, s in items}))
    sc['基本面优势'] = fm['L1']
    return sc


def run(tag, dims):
    sc = build(dims)
    order = ['基本面优势'] + list(dims.keys())
    single = {}
    for d in order:
        X = sc[[d]] if d == '基本面优势' else pd.concat([sc[[d]], fm[CTRL]], axis=1)
        m = reg(Y, X)
        single[d] = dict(coef=round(float(m.params[d]), 5), t=round(float(m.tvalues[d]), 2),
                         p=round(float(m.pvalues[d]), 4), n=int(m.nobs))
    mj = reg(Y, sc[order])
    joint = {d: dict(coef=round(float(mj.params[d]), 5), t=round(float(mj.tvalues[d]), 2),
                     p=round(float(mj.pvalues[d]), 4)) for d in order}
    comp = ew(sc[order])
    mc = reg(Y, comp.rename('综合'))
    g = pd.DataFrame({'a': Y, 'c': comp}).dropna()
    g['q'] = pd.qcut(g['c'], 5, labels=['Q1', 'Q2', 'Q3', 'Q4', 'Q5'])
    gm = g.groupby('q', observed=True)['a'].mean()
    hi, lo = g[g['q'] == 'Q5']['a'], g[g['q'] == 'Q1']['a']
    tt = sm.stats.ttest_ind(hi, lo, usevar='unequal')
    res[tag] = dict(单维=single, 联立=dict(n=int(mj.nobs), r2=round(float(mj.rsquared), 4), 系数=joint),
                    综合=dict(t=round(float(mc.tvalues['综合']), 2), r2=round(float(mc.rsquared), 4)),
                    五分组=dict(Q1=round(float(gm['Q1']), 5), Q5=round(float(gm['Q5']), 5),
                              差=round(float(gm['Q5'] - gm['Q1']), 5), t=round(float(tt[0]), 2),
                              p=round(float(tt[1]), 6)))
    print(f'\n===== {tag} =====')
    print('  单维: ' + '  '.join(f'{d}t={single[d]["t"]:+.2f}' for d in order))
    print(f'  联立(R2={res[tag]["联立"]["r2"]}): ' + '  '.join(f'{d}t={joint[d]["t"]:+.2f}' for d in order))
    f = res[tag]['五分组']
    print(f'  综合t={res[tag]["综合"]["t"]:+.2f} R2={res[tag]["综合"]["r2"]}  '
          f'Q5-Q1={f["差"]*100:+.2f}pp t={f["t"]:+.2f} p={f["p"]}')


run('基准_六维原口径', DIMS)

d2 = {k: [x for x in v if x[0] != 'oc_conf'] for k, v in DIMS.items()}
run('剔除oc_conf', d2)

d3 = {k: [x for x in v if x[0] != 'lsv'] for k, v in DIMS.items()}
run('剔除lsv_L5仅SDI', d3)

d4 = {k: [x for x in v if x[0] not in ('oc_conf', 'lsv')] for k, v in DIMS.items()}
run('同时剔除oc_conf与lsv', d4)

d5 = {k: v for k, v in DIMS.items() if k != '交易执行能力'}
run('整维剔除交易执行能力', d5)

with open(os.path.join(OUT, '显著性审查_留一法_2026-09-02.json'), 'w', encoding='utf-8') as f:
    json.dump(res, f, ensure_ascii=False, indent=1)
print('\n已保存 output/显著性审查_留一法_2026-09-02.json')


# ============ 追加：oc_conf 与 lsv 的准入三门槛逐条检验（2026-09-02） ============
def gate_tests():
    """三条剔除门槛：①符号翻转 ②显著性依赖控制变量 ③群体差异不显著。
    任一成立即剔除。对 oc_conf / lsv 逐条判定。"""
    import scipy.stats as st
    g = {}
    for m in ['oc_conf', 'lsv']:
        sg = -1 if m == 'oc_conf' else +1
        # 门槛① 符号翻转：规格I / 规格II 符号是否一致
        r3 = json.load(open(os.path.join(OUT, '主回归_v3_2026-08-26.json'), encoding='utf-8'))
        b1 = r3['spec1_cross_section']['univariate'][m]['coef'][m]['b']
        b2 = r3['spec2_panel']['univariate'][m]['coef'][m]['b']
        flip = (np.sign(b1) != np.sign(b2))
        # 门槛② 显著性依赖控制变量：裸回归 vs 加三控制
        m_bare = reg(Y, fm[[m]])
        m_ctrl = reg(Y, fm[[m] + CTRL])
        dep_ctrl = (m_bare.pvalues[m] > 0.05) != (m_ctrl.pvalues[m] > 0.05)
        # 门槛③ 群体差异：按该成分定向分位五等分，Q5 vs Q1 的 alpha 差
        d = pd.DataFrame({'a': Y, 'x': sg * fm[m]}).dropna()
        d['q'] = pd.qcut(d['x'], 5, labels=['Q1', 'Q2', 'Q3', 'Q4', 'Q5'])
        hi, lo = d[d['q'] == 'Q5']['a'], d[d['q'] == 'Q1']['a']
        tt = st.ttest_ind(hi, lo, equal_var=False)
        grp_ns = (tt.pvalue > 0.05)
        g[m] = dict(
            门槛1_符号翻转=dict(b_规格I=round(float(b1), 6), b_规格II=round(float(b2), 6),
                          同号=bool(not flip), 判定='通过' if not flip else '★触发剔除'),
            门槛2_依赖控制=dict(裸回归_t=round(float(m_bare.tvalues[m]), 2),
                          裸回归_p=round(float(m_bare.pvalues[m]), 4),
                          加控制_t=round(float(m_ctrl.tvalues[m]), 2),
                          加控制_p=round(float(m_ctrl.pvalues[m]), 4),
                          判定='通过' if not dep_ctrl else '★触发剔除'),
            门槛3_群体差异=dict(Q1=round(float(lo.mean()), 5), Q5=round(float(hi.mean()), 5),
                          差pp=round(float((hi.mean() - lo.mean()) * 100), 3),
                          t=round(float(tt.statistic), 2), p=round(float(tt.pvalue), 6),
                          判定='通过' if not grp_ns else '★触发剔除'),
            结论='保留' if not (flip or dep_ctrl or grp_ns) else '剔除',
        )
        print(f'\n----- {m} 准入三门槛 -----')
        for k, v in g[m].items():
            print(f'  {k}: {v}')
    return g


res['准入门槛_oc_conf与lsv'] = gate_tests()
with open(os.path.join(OUT, '显著性审查_留一法_2026-09-02.json'), 'w', encoding='utf-8') as f:
    json.dump(res, f, ensure_ascii=False, indent=1)
print('\n已更新 output/显著性审查_留一法_2026-09-02.json（含准入三门槛）')
