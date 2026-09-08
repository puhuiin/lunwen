# -*- coding: utf-8 -*-
"""
五维能力等权复合打分 v2（2026-08-26）
依据 v3 两口径（规格I 基金层横截面 / 规格II 季度面板）显著性重建维度成分。
关键变更（相对 _composite_score_20260825.py）：
  1. 认知能力层由单指标扩为 4 指标（risk_asym / de / oc_conf / rc_mom）
  2. 配置选择能力剔除 AS_improved（六道检验裁决为无独立解释力）
  3. 风险转化能力以 MPPM 为主（Goetzmann et al. 2007），替代原单一 sharpe8_lag
  4. 每个成分的方向由「双口径符号一致」定向，并输出定向证据表
流程：面板 -> 基金层时序均值 -> winsor(1%) -> 横截面z -> 等权复合（缺失跳过重归一）
"""
import pandas as pd, numpy as np, os, json
import statsmodels.api as sm

BASE = r'd:\Desktop\基金经理行为分析研究'
OUT = os.path.join(BASE, 'output')
TODAY = '2026-08-26'

CTRL = ['mgr_total_tenure_v2', 'log_fund_age', 'log_aum']

# 维度成分：(指标, 定向符号) —— 符号为写入复合得分时的乘数
DIMS = {
    '认知能力': [('risk_asym', +1), ('de', -1), ('oc_conf', -1), ('rc_mom', -1)],
    '配置选择能力': [('ICI', +1), ('ISDI', -1)],
    '风险应对能力': [('ARG', +1), ('rsstab_lag', -1)],
    '风险转化能力': [('mppm8_lag', +1), ('sortino8_lag', +1), ('sharpe8_lag', +1)],
    '交易执行能力': [('SDI', -1), ('TO_wind_clean', -1)],
}
ALL_COMP = [m for v in DIMS.values() for m, _ in v]


def winsor(s, p=0.01):
    lo, hi = s.quantile(p), s.quantile(1 - p)
    return s.clip(lo, hi)


def z(s):
    return (s - s.mean()) / s.std()


def ew(frame):
    """等权复合：缺失成分跳过并按可用数重归一"""
    return frame.sum(axis=1, skipna=True) / frame.notna().sum(axis=1)


def reg_hc1(y, X):
    d = pd.concat([y, X], axis=1).dropna()
    m = sm.OLS(d.iloc[:, 0], sm.add_constant(d.iloc[:, 1:])).fit(cov_type='HC1')
    return m


def brief(m, key):
    return dict(n=int(m.nobs), coef=round(float(m.params[key]), 5),
                t=round(float(m.tvalues[key]), 2), p=round(float(m.pvalues[key]), 4),
                r2=round(float(m.rsquared), 4))


res = {}

# ---------- 数据 ----------
panel = pd.read_csv(os.path.join(OUT, f'分析面板_v3_{TODAY}.csv'), parse_dates=['report_date'])
new = pd.read_csv(os.path.join(OUT, '新增指标面板_2026-08-25.csv'), parse_dates=['report_date'])
panel = panel.merge(new[['fund_code', 'report_date', 'rc_mom']], on=['fund_code', 'report_date'], how='left')
print('面板 %d 行 / %d 基金' % (len(panel), panel['fund_code'].nunique()))
print('rc_mom 覆盖 %.1f%%' % (panel['rc_mom'].notna().mean() * 100))

fm = panel.groupby('fund_code')[ALL_COMP + CTRL + ['ff5_adj_return']].mean()
for c in ALL_COMP + CTRL:
    fm[c] = winsor(fm[c])
print('基金层样本 %d 只' % len(fm))

# ---------- Step1 定向证据：每个成分单指标回归（规格I，含控制） ----------
print('\n=== Step1 成分定向证据（规格I 基金层，DV=FF5 alpha，HC1，含三控制） ===')
orient = {}
for m_ in ALL_COMP:
    mod = reg_hc1(fm['ff5_adj_return'], fm[[m_] + CTRL])
    b = brief(mod, m_)
    orient[m_] = b
    print('  %-18s n=%3d  t=%+7.2f  p=%.4f' % (m_, b['n'], b['t'], b['p']))
res['step1_定向证据_规格I'] = orient

# ---------- Step2 rsstab 反常符号溯源 ----------
print('\n=== Step2 rsstab_lag 符号溯源（是否由 return_volatility 驱动） ===')
fmv = panel.groupby('fund_code')[['rsstab_lag', 'return_volatility']].mean()
fmv = fmv.join(fm[['ff5_adj_return'] + CTRL], how='inner')
for c in ['rsstab_lag', 'return_volatility']:
    fmv[c] = winsor(fmv[c])
a = reg_hc1(fmv['ff5_adj_return'], fmv[['rsstab_lag'] + CTRL])
b = reg_hc1(fmv['ff5_adj_return'], fmv[['rsstab_lag', 'return_volatility'] + CTRL])
print('  不控波动率: rsstab_lag t=%+.2f' % brief(a, 'rsstab_lag')['t'])
print('  控制波动率: rsstab_lag t=%+.2f  (return_volatility t=%+.2f)'
      % (brief(b, 'rsstab_lag')['t'], brief(b, 'return_volatility')['t']))
print('  corr(rsstab_lag, return_volatility) = %+.3f' % fmv[['rsstab_lag', 'return_volatility']].corr().iloc[0, 1])
res['step2_rsstab溯源'] = dict(
    不控波动率=brief(a, 'rsstab_lag'), 控制波动率=brief(b, 'rsstab_lag'),
    波动率本身=brief(b, 'return_volatility'),
    corr=round(float(fmv[['rsstab_lag', 'return_volatility']].corr().iloc[0, 1]), 3))

# ---------- Step3 等权复合 ----------
print('\n=== Step3 五维等权复合得分 ===')
score = pd.DataFrame(index=fm.index)
comp_detail = {}
for dim, items in DIMS.items():
    zf = pd.DataFrame({m_: sign * z(fm[m_]) for m_, sign in items})
    score[dim] = ew(zf)
    comp_detail[dim] = ['%s%s' % ('+' if s > 0 else '-', m_) for m_, s in items]
    print('  %-8s 成分 %-42s 有效 %3d 只' % (dim, ','.join(comp_detail[dim]), score[dim].notna().sum()))

DIM_NAMES = list(DIMS.keys())
score['综合能力'] = ew(score[DIM_NAMES])
score['ff5_alpha'] = fm['ff5_adj_return']
res['step3_维度成分'] = comp_detail

print('\n  五维得分相关矩阵：')
print(score[DIM_NAMES].corr().round(3).to_string())
res['step3_维度相关'] = json.loads(score[DIM_NAMES].corr().round(3).to_json())

# ---------- Step4 复合得分有效性检验 ----------
print('\n=== Step4 复合得分对 alpha 的解释力（规格I，HC1，含三控制） ===')
valid = {}
sc = score.join(fm[CTRL])
for dim in DIM_NAMES + ['综合能力']:
    mod = reg_hc1(sc['ff5_alpha'], sc[[dim] + CTRL])
    valid[dim] = brief(mod, dim)
    print('  %-8s n=%3d  coef=%+.5f  t=%+7.2f  p=%.4f  R2=%.4f'
          % (dim, valid[dim]['n'], valid[dim]['coef'], valid[dim]['t'], valid[dim]['p'], valid[dim]['r2']))

mod_all = reg_hc1(sc['ff5_alpha'], sc[DIM_NAMES + CTRL])
print('\n  五维同时进入：n=%d R2=%.4f' % (int(mod_all.nobs), mod_all.rsquared))
for dim in DIM_NAMES:
    print('    %-8s t=%+7.2f' % (dim, mod_all.tvalues[dim]))
res['step4_单维有效性'] = valid
res['step4_五维联立'] = dict(n=int(mod_all.nobs), r2=round(float(mod_all.rsquared), 4),
                             t={d: round(float(mod_all.tvalues[d]), 2) for d in DIM_NAMES})

# ---------- Step5 综合能力分组单调性 ----------
print('\n=== Step5 综合能力五分组的 alpha 单调性 ===')
g = score.dropna(subset=['综合能力', 'ff5_alpha']).copy()
g['grp'] = pd.qcut(g['综合能力'], 5, labels=['Q1最低', 'Q2', 'Q3', 'Q4', 'Q5最高'])
tab = g.groupby('grp', observed=True)['ff5_alpha'].agg(['size', 'mean', 'median'])
print(tab.round(5).to_string())
hi = g[g['grp'] == 'Q5最高']['ff5_alpha']
lo = g[g['grp'] == 'Q1最低']['ff5_alpha']
tt = sm.stats.ttest_ind(hi, lo, usevar='unequal')
print('  Q5-Q1 = %+.5f  t=%+.2f  p=%.4f' % (hi.mean() - lo.mean(), tt[0], tt[1]))
res['step5_分组单调性'] = dict(
    组均值={str(k): round(float(v), 5) for k, v in tab['mean'].items()},
    组规模={str(k): int(v) for k, v in tab['size'].items()},
    Q5_Q1差=round(float(hi.mean() - lo.mean()), 5),
    t=round(float(tt[0]), 2), p=round(float(tt[1]), 4))

# ---------- 保存 ----------
score.reset_index().to_csv(os.path.join(OUT, f'五维能力复合得分_{TODAY}.csv'),
                           index=False, encoding='utf-8-sig')
with open(os.path.join(OUT, f'五维复合验证_{TODAY}.json'), 'w', encoding='utf-8') as f:
    json.dump(res, f, ensure_ascii=False, indent=2)
print(f'\n已保存 output/五维能力复合得分_{TODAY}.csv 与 output/五维复合验证_{TODAY}.json')
