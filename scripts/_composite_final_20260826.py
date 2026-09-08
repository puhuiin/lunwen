# -*- coding: utf-8 -*-
"""
五维能力等权复合打分【定稿】（2026-08-26）
=====================================================================
成分定稿依据（全部经单指标显著性 + 逐步加控制 + 分组单调性三重检验）：

L2 认知能力  = [ z(risk_asym) + z(-de) + z(-oc_conf) ] / 3
   risk_asym 风险不对称        Kahneman & Tversky (1979) 前景理论 / Brown et al. (1996) 锦标赛
   de        处置效应          Shefrin & Statman (1985); Odean (1998)
   oc_conf   过度自信          Puetz & Ruenzi (2011), JBFA 38(5-6)
   [剔除] rc_mom 追涨杀跌：覆盖 53.5%、单指标 t=-0.51 ns、纳入后维度 t 由 7.69 降至 6.91
   [剔除] lsv 交易趋同：符号为正（与羊群损害预期相反），归入 L5 并按 Wermers (1999) 解释

L3 配置选择能力 = [ z(ICI) + z(-ISDI) ] / 2
   ICI  行业集中度            Kacperczyk, Sialm & Zheng (2005), JF 60(4)
   ISDI 行业风格漂移          Wermers (2012); Chen & Wei (2025), PLoS ONE 20(2)
   [剔除] AS_improved：六道检验裁定无独立解释力（Frazzini, Friedman & Pomorski, 2016, FAJ）

L4a 风险应对能力 = [ z(ARG) + z(timing) ] / 2
   ARG    调仓收益            Kacperczyk, Sialm & Zheng (2008), RFS 21(6)
   timing 下行保护（-γ_HM）    Henriksson & Merton (1981), JB 54(4), 513-533
   [剔除] rsstab_lag：与 return_volatility corr=-0.749，正交化后 t=-0.87 ns

L4b 风险转化能力 = [ z(mppm8) + z(sortino8) + z(sharpe8) ] / 3
   mppm8   抗操纵绩效         Goetzmann, Ingersoll, Spiegel & Welch (2007), RFS 20(5)
   sortino8 下行风险调整      Sortino & Price (1994), Journal of Investing 3(3)
   sharpe8  基准参照          Sharpe (1966)

L5 交易执行能力 = [ z(-SDI) + z(lsv) ] / 2
   SDI 风格漂移离散度         Wermers (2012)
   lsv 交易趋同度             Lakonishok, Shleifer & Vishny (1992); Wermers (1999), JF 54(2)
       （Wermers 1999 发现被机构共识买入的股票随后跑赢，故正向定义为「共识信息利用」）
   [剔除] TO_wind_clean 换手率：双口径均 ns（I: t=+0.50 / II: t=+0.32）
=====================================================================
"""
import pandas as pd, numpy as np, os, json
import statsmodels.api as sm

BASE = r'd:\Desktop\基金经理行为分析研究'
OUT = os.path.join(BASE, 'output')
TODAY = '2026-08-26'
CTRL = ['mgr_total_tenure_v2', 'log_fund_age', 'log_aum']

DIMS = {
    '认知能力': [('risk_asym', +1), ('de', -1), ('oc_conf', -1)],
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
tim = pd.read_csv(os.path.join(OUT, f'择时系数_季度HM_{TODAY}.csv'))
tim = tim.set_index('fund_code')[['timing']]

base_cols = [c for c in ALL_COMP if c != 'timing']
fm = panel.groupby('fund_code')[base_cols + CTRL + ['ff5_adj_return', 'quarter_return']].mean()
fm = fm.join(tim, how='left')
for c in ALL_COMP + CTRL:
    fm[c] = winsor(fm[c])
Y = fm['ff5_adj_return']
print('基金层样本 %d 只；timing 覆盖 %d 只' % (len(fm), fm['timing'].notna().sum()))

# ---------- S1 成分定向证据 ----------
print('\n=== S1 成分定向证据（规格I，DV=FF5 alpha，HC1，含三控制） ===')
s1 = {}
for m_, sg in [(m, s) for v in DIMS.values() for m, s in v]:
    mod = reg(Y, fm[[m_] + CTRL])
    t = float(mod.tvalues[m_])
    ok = '一致' if np.sign(t) == sg else '★不一致'
    s1[m_] = dict(定向=sg, n=int(mod.nobs), t=round(t, 2), p=round(float(mod.pvalues[m_]), 4), 判定=ok)
    print('  %-16s 定向%+d  n=%3d  t=%+7.2f  p=%.4f  %s' % (m_, sg, mod.nobs, t, mod.pvalues[m_], ok))
res['S1_成分定向'] = s1

# ---------- S2 复合 ----------
score = pd.DataFrame(index=fm.index)
for dim, items in DIMS.items():
    score[dim] = ew(pd.DataFrame({m_: sg * z(fm[m_]) for m_, sg in items}))
score['综合能力'] = ew(score[DIM_NAMES])
score['ff5_alpha'] = fm['ff5_adj_return']
score['quarter_return'] = fm['quarter_return']

print('\n=== S2 五维得分相关矩阵 ===')
print(score[DIM_NAMES].corr().round(3).to_string())
res['S2_维度相关'] = json.loads(score[DIM_NAMES].corr().round(3).to_json())

# ---------- S3 有效性 ----------
print('\n=== S3 复合得分解释力（规格I，HC1，含三控制） ===')
sc = score.join(fm[CTRL])
s3 = {}
for dim in DIM_NAMES + ['综合能力']:
    mod = reg(sc['ff5_alpha'], sc[[dim] + CTRL])
    s3[dim] = dict(n=int(mod.nobs), coef=round(float(mod.params[dim]), 5),
                   t=round(float(mod.tvalues[dim]), 2), p=round(float(mod.pvalues[dim]), 4),
                   r2=round(float(mod.rsquared), 4))
    print('  %-8s n=%3d coef=%+.5f t=%+7.2f p=%.4f R2=%.4f'
          % (dim, mod.nobs, mod.params[dim], mod.tvalues[dim], mod.pvalues[dim], mod.rsquared))
mall = reg(sc['ff5_alpha'], sc[DIM_NAMES + CTRL])
print('\n  五维联立 n=%d R2=%.4f' % (mall.nobs, mall.rsquared))
for dim in DIM_NAMES:
    print('    %-8s coef=%+.5f  t=%+6.2f  p=%.4f' % (dim, mall.params[dim], mall.tvalues[dim], mall.pvalues[dim]))
res['S3_单维'] = s3
res['S3_联立'] = dict(n=int(mall.nobs), r2=round(float(mall.rsquared), 4),
                      系数={d: dict(coef=round(float(mall.params[d]), 5), t=round(float(mall.tvalues[d]), 2),
                                    p=round(float(mall.pvalues[d]), 4)) for d in DIM_NAMES})

# ---------- S4 分组单调性 ----------
print('\n=== S4 综合能力五分组 alpha 单调性 ===')
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

score.reset_index().to_csv(os.path.join(OUT, f'五维能力复合得分_定稿_{TODAY}.csv'),
                           index=False, encoding='utf-8-sig')
with open(os.path.join(OUT, f'五维复合定稿验证_{TODAY}.json'), 'w', encoding='utf-8') as f:
    json.dump(res, f, ensure_ascii=False, indent=2)
print(f'\n已保存 output/五维能力复合得分_定稿_{TODAY}.csv')
