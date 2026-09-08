# -*- coding: utf-8 -*-
"""
六维能力等权复合打分【含 L1 基本面层】（2026-08-26）
=====================================================================
在五维定稿基础上，把 L1 基本面层从"纯控制变量"升级为第六个计分维度。

L1 基本面优势 = [ z(-mgr_total_tenure_v2) + z(-log_fund_age) + z(-log_aum) ] / 3
   任职年限 tenure   负向：经验悖论——Chevalier & Ellison (1999) 发现年轻经理业绩更优；
                     本样本单变量 t=-1.90*
   基金年龄 age      负向：Berk & Green (2004) 组织资本/规模侵蚀 alpha（新基金效应）；
                     本样本单变量 t=-4.13***
   基金规模 aum      负向：Berk & Green (2004) 规模不经济；Chen, Hong, Huang & Kubik (2004)
                     流动性与组织成本；本样本单变量 t=-1.20（方向一致、不显著）

注意事项：L1 的三个成分本身就是原控制变量组，因此——
  ① S1 成分定向对 L1 成分用无控制变量的单变量回归（成分即控制层，自我控制无意义）；
  ② 六维联立模型不再叠加原控制变量组（L1 得分是它们的线性组合，叠加即完全共线）；
  ③ L2–L5 各维的单维回归仍含三控制变量（与五维定稿口径一致，保证可比）。
=====================================================================
"""
import pandas as pd
import numpy as np
import os
import json
import statsmodels.api as sm

BASE = r'd:\Desktop\基金经理行为分析研究'
OUT = os.path.join(BASE, 'output')
TODAY = '2026-08-26'
CTRL = ['mgr_total_tenure_v2', 'log_fund_age', 'log_aum']

DIMS = {
    '基本面优势': [('mgr_total_tenure_v2', -1), ('log_fund_age', -1), ('log_aum', -1)],
    '认知能力': [('risk_asym', +1), ('de', -1), ('oc_conf', -1),
                 ('anchor_high', +1)],
    '配置选择能力': [('ICI', +1), ('ISDI', -1)],
    '风险应对能力': [('ARG', +1), ('timing', +1)],
    '风险转化能力': [('mppm8_lag', +1), ('sortino8_lag', +1), ('sharpe8_lag', +1)],
    '交易执行能力': [('SDI', -1), ('lsv', +1)],
}
DIM_NAMES = list(DIMS.keys())
ALL_COMP = [m for v in DIMS.values() for m, _ in v]
res = {}


def winsor(s, p=0.01):
    return s.clip(s.quantile(p), s.quantile(1 - p))


def z(s):
    return (s - s.mean()) / s.std()


def ew(frame):
    return frame.sum(axis=1, skipna=True) / frame.notna().sum(axis=1)


def reg(y, X):
    d = pd.concat([y, X], axis=1).dropna()
    return sm.OLS(d.iloc[:, 0], sm.add_constant(d.iloc[:, 1:])).fit(cov_type='HC1')


# ---------- 数据 ----------
panel = pd.read_csv(os.path.join(OUT, f'分析面板_v3_{TODAY}.csv'), parse_dates=['report_date'])
# 认知层新增候选（2026-09-02 文献挖掘）：anchor_high 锚定效应入选；
# cgo 资本利得悬垂亦过三道准入门槛但与 anchor_high 相关 0.63，二者并入会稀释维度
# （认知维联立 t：4.64 anchor-only vs 4.08 both），故仅纳入 anchor_high；cgo 留档备索
_new = pd.read_csv(os.path.join(OUT, 'L2新增候选_面板_2026-09-02.csv'), parse_dates=['report_date'])
panel = panel.merge(_new[['fund_code', 'report_date', 'anchor_high']],
                    on=['fund_code', 'report_date'], how='left')
tim = pd.read_csv(os.path.join(OUT, f'择时系数_季度HM_{TODAY}.csv'))
tim = tim.set_index('fund_code')[['timing']]

base_cols = [c for c in ALL_COMP if c != 'timing']
sel_cols = list(dict.fromkeys(base_cols + CTRL))
fm = panel.groupby('fund_code')[sel_cols + ['ff5_adj_return', 'quarter_return']].mean()
fm = fm.join(tim, how='left')
for c in ALL_COMP + CTRL:
    fm[c] = pd.to_numeric(fm[c], errors='coerce')
    fm[c] = winsor(fm[c])
Y = fm['ff5_adj_return']
print('基金层样本 %d 只；timing 覆盖 %d 只' % (len(fm), fm['timing'].notna().sum()))

# ---------- S1 成分定向证据 ----------
print('\n=== S1 成分定向证据（规格I，DV=FF5 alpha，HC1） ===')
print('    L1 成分：单变量回归（成分即控制层，不自我控制）')
print('    其余维度：含三控制变量的回归（与五维定稿口径一致）')
s1 = {}
for dim, items in DIMS.items():
    for m_, sg in items:
        if dim == '基本面优势':
            mod = reg(Y, fm[[m_]])
        else:
            mod = reg(Y, fm[[m_] + CTRL])
        t = float(mod.tvalues[m_])
        ok = '一致' if np.sign(t) == sg else '★不一致'
        s1[m_] = dict(维度=dim, 定向=sg, n=int(mod.nobs), t=round(t, 2),
                      p=round(float(mod.pvalues[m_]), 4), 判定=ok)
        print('  %-18s 定向%+d  n=%3d  t=%+7.2f  p=%.4f  %s'
              % (m_, sg, mod.nobs, t, mod.pvalues[m_], ok))
res['S1_成分定向'] = s1

# ---------- S2 复合 ----------
score = pd.DataFrame(index=fm.index)
for dim, items in DIMS.items():
    score[dim] = ew(pd.DataFrame({m_: sg * z(fm[m_]) for m_, sg in items}))
score['综合能力'] = ew(score[DIM_NAMES])
score['ff5_alpha'] = fm['ff5_adj_return']
score['quarter_return'] = fm['quarter_return']

print('\n=== S2 六维得分相关矩阵 ===')
print(score[DIM_NAMES].corr().round(3).to_string())
res['S2_维度相关'] = json.loads(score[DIM_NAMES].corr().round(3).to_json())

# ---------- S3 有效性 ----------
print('\n=== S3 复合得分解释力（规格I，HC1） ===')
print('    L1 维：无控制变量（成分即控制层）；其余维：含三控制变量')
s3 = {}
sc = score.join(fm[CTRL])
for dim in DIM_NAMES + ['综合能力']:
    X = [dim] if dim == '基本面优势' else [dim] + CTRL
    mod = reg(sc['ff5_alpha'], sc[X])
    s3[dim] = dict(n=int(mod.nobs), coef=round(float(mod.params[dim]), 5),
                  t=round(float(mod.tvalues[dim]), 2), p=round(float(mod.pvalues[dim]), 4),
                  r2=round(float(mod.rsquared), 4))
    print('  %-8s n=%3d coef=%+.5f t=%+7.2f p=%.4f R2=%.4f'
          % (dim, mod.nobs, mod.params[dim], mod.tvalues[dim], mod.pvalues[dim], mod.rsquared))
# 六维联立：不叠加控制变量（L1 得分是它们的线性组合）
mall = reg(sc['ff5_alpha'], sc[DIM_NAMES])
print('\n  六维联立（不含控制变量，避免与 L1 完全共线） n=%d R2=%.4f'
      % (mall.nobs, mall.rsquared))
for dim in DIM_NAMES:
    print('    %-8s coef=%+.5f  t=%+6.2f  p=%.4f'
          % (dim, mall.params[dim], mall.tvalues[dim], mall.pvalues[dim]))
res['S3_单维'] = s3
res['S3_联立'] = dict(n=int(mall.nobs), r2=round(float(mall.rsquared), 4),
                      系数={d: dict(coef=round(float(mall.params[d]), 5),
                                    t=round(float(mall.tvalues[d]), 2),
                                    p=round(float(mall.pvalues[d]), 4)) for d in DIM_NAMES})
# 对照：五维联立 + 控制变量（原口径，供对比）
old5 = [d for d in DIM_NAMES if d != '基本面优势']
mo = reg(sc['ff5_alpha'], sc[old5 + CTRL])
print('\n  [对照] 五维联立 + 三控制变量 n=%d R2=%.4f' % (mo.nobs, mo.rsquared))
res['S3_联立_五维对照'] = dict(n=int(mo.nobs), r2=round(float(mo.rsquared), 4),
                               系数={d: dict(coef=round(float(mo.params[d]), 5),
                                             t=round(float(mo.tvalues[d]), 2),
                                             p=round(float(mo.pvalues[d]), 4)) for d in old5})

# ---------- S4 分组单调性 ----------
print('\n=== S4 综合能力五分组 alpha 单调性（六维口径） ===')
g = score.dropna(subset=['综合能力', 'ff5_alpha']).copy()
g['grp'] = pd.qcut(g['综合能力'], 5, labels=['Q1最低', 'Q2', 'Q3', 'Q4', 'Q5最高'])
tab = g.groupby('grp', observed=True)[['ff5_alpha', 'quarter_return']].mean()
tab['n'] = g.groupby('grp', observed=True).size()
print(tab.round(5).to_string())
hi, lo = g[g['grp'] == 'Q5最高']['ff5_alpha'], g[g['grp'] == 'Q1最低']['ff5_alpha']
tt = sm.stats.ttest_ind(hi, lo, usevar='unequal')
print('  Q5-Q1 = %+.5f  t=%+.2f  p=%.4f' % (hi.mean() - lo.mean(), tt[0], tt[1]))
res['S4_分组'] = dict(alpha均值={str(k): round(float(v), 5) for k, v in tab['ff5_alpha'].items()},
                      季度收益均值={str(k): round(float(v), 5) for k, v in tab['quarter_return'].items()},
                      规模={str(k): int(v) for k, v in tab['n'].items()},
                      Q5_Q1=round(float(hi.mean() - lo.mean()), 5),
                      t=round(float(tt[0]), 2), p=round(float(tt[1]), 4))

# ---------- 落盘 ----------
score.reset_index().to_csv(os.path.join(OUT, f'六维能力复合得分_含L1_{TODAY}.csv'),
                           index=False, encoding='utf-8-sig')
with open(os.path.join(OUT, f'六维复合定稿验证_含L1_{TODAY}.json'), 'w', encoding='utf-8') as f:
    json.dump(res, f, ensure_ascii=False, indent=2)
print(f'\n已保存 output/六维能力复合得分_含L1_{TODAY}.csv 与 六维复合定稿验证_含L1_{TODAY}.json')
