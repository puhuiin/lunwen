# -*- coding: utf-8 -*-
"""全部候选指标的单变量回归 + 三因变量对照（2026-09-02）

用途：论文改版第 7 条要求——先不预设分层，把所有研究过的指标（含背景特征、
含最终被剔除的）一起做单变量回归，展示哪些显著；再按三种因变量切换看差异。

因变量三口径（均为基金层，每只基金一个数）：
  DV1 超额收益（相对沪深300）：基金季收益 − 沪深300 季收益，取时序均值
  DV2 FF3 alpha：基金超额收益对 MKT/SMB/HML 时序回归截距
  DV3 FF5 alpha：基金超额收益对 MKT/SMB/HML/RMW/CMA 时序回归截距

回归：基金层横截面 OLS + HC1 异方差稳健标准误；自变量为基金内时序均值。
      控制变量组（任职年限/log基金年龄/log规模）在「加控制」列中出现；
      背景哑变量（性别/CFA/学历/院校层次）本身即背景，仅做裸回归。

输出 output/单变量全表_去2026Q2敏感性_2026-09-10.json / .csv
"""
import json, os
import numpy as np, pandas as pd
import statsmodels.api as sm

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, 'output')
PIPE = os.path.join(BASE, '指标计算流水线')
L1D = os.path.join(PIPE, 'data', 'L1_背景特征层')
CTRL = ['mgr_total_tenure_v2', 'log_fund_age', 'log_aum']
FF3 = ['MKT_excess', 'SMB', 'HML']
FF5 = ['ff5_MKT_excess', 'ff5_SMB', 'ff5_HML', 'ff5_RMW', 'ff5_CMA']

winsor = lambda s, q=0.01: s.clip(s.quantile(q), s.quantile(1 - q))

panel = pd.read_csv(os.path.join(OUT, '分析面板_v3_2026-08-26.csv'), parse_dates=['report_date'])
panel = panel[~((panel['year']==2026)&(panel['quarter']==2))].copy()  # 09-10敏感性：剔2026Q2
print('敏感性面板(去2026Q2):', panel.shape)
v2 = pd.read_csv(os.path.join(OUT, '指标面板_v2_2026-08-26.csv'), parse_dates=['report_date'])
for c in ['sharpe8_lag', 'sortino8_lag', 'mppm8_lag', 'rsstab_lag', 'oc_conf']:
    if c in panel.columns:
        panel = panel.drop(columns=c)
panel = panel.merge(v2[['fund_code', 'report_date', 'sharpe8_lag', 'sortino8_lag',
                        'mppm8_lag', 'rsstab_lag', 'oc_conf']],
                    on=['fund_code', 'report_date'], how='left')
newp = pd.read_csv(os.path.join(OUT, 'L2新增候选_面板_2026-09-02.csv'), parse_dates=['report_date'])
rcm = pd.read_csv(os.path.join(OUT, '认知指标_rc追涨杀跌_2026-08-25.csv'), parse_dates=['report_date'])
panel = panel.merge(rcm[['fund_code', 'report_date', 'rc_mom']],
                    on=['fund_code', 'report_date'], how='left')
panel = panel.merge(newp[['fund_code', 'report_date', 'anchor_high', 'cgo',
                          'house_money', 'bhm_shm']],
                    on=['fund_code', 'report_date'], how='left')
tim = pd.read_csv(os.path.join(OUT, '择时系数_季度HM_2026-08-26.csv')).set_index('fund_code')[['timing']]

# ---------- 因变量三口径 ----------
p_idx1 = os.path.join(OUT, '市场指数历史数据.csv')
p_idx2 = os.path.join(BASE, 'backups', '数据', '基金基础信息', '市场指数历史数据.csv')
idx_path = p_idx1 if os.path.exists(p_idx1) else p_idx2
idx = pd.read_csv(idx_path, parse_dates=['date'])
hs = idx[idx['index_code'] == 'sh000300'][['date', 'close']].sort_values('date')
hs['yq'] = hs['date'].dt.to_period('Q')
hsq = hs.groupby('yq')['close'].last().pct_change().rename('hs300_ret').reset_index()
panel['yq'] = panel['report_date'].dt.to_period('Q') - 1   # report_date = 季末+1日
panel = panel.merge(hsq, on='yq', how='left')
panel['ex_hs300'] = panel['quarter_return'] - panel['hs300_ret']

# 优先使用面板自带的基金层 alpha（与论文 N=362 口径一致）
rows = []
for fc, g in panel.groupby('fund_code'):
    d = {'fund_code': fc}
    g3 = g['ff3_adj_return'].dropna()
    if len(g3):
        d['ff3_alpha'] = float(g3.iloc[0])
    g5 = g['ff5_adj_return'].dropna()
    if len(g5):
        d['ff5_alpha'] = float(g5.iloc[0])
    d['ex_hs300'] = float(g['ex_hs300'].mean()) if g['ex_hs300'].notna().any() else np.nan
    rows.append(d)
dv = pd.DataFrame(rows).set_index('fund_code')
print('因变量覆盖：超沪深300 %d ｜ FF3 alpha %d ｜ FF5 alpha %d'
      % (dv['ex_hs300'].notna().sum(), dv['ff3_alpha'].notna().sum(), dv['ff5_alpha'].notna().sum()))
print('三因变量相关：\n%s' % dv.corr().round(3).to_string())

# ---------- 自变量清单：全部研究过的指标 ----------
# 连续型行为/绩效指标（进入「裸回归」与「加控制」两列）
CONT = ['risk_asym', 'de', 'oc_conf', 'rc_mom', 'anchor_high',
        'ICI', 'ISDI', 'AS_improved',
        'ARG', 'timing', 'return_volatility', 'rsstab_lag',
        'mppm8_lag', 'sortino8_lag', 'sharpe8_lag',
        'SDI', 'lsv', 'TO_wind_clean']
# 背景特征（本身即背景，只做裸回归；学历/CFA/性别为哑变量）
BG_CONT = ['mgr_total_tenure_v2', 'log_fund_age', 'log_aum']
BG_DUM = ['male', 'has_CFA', 'master_up', 'top_school']

base = [c for c in CONT if c != 'timing']
fm = panel.groupby('fund_code')[base + BG_CONT].mean().join(tim, how='left')

p_info1 = os.path.join(OUT, '基金详细信息_最终版.csv')
p_info2 = os.path.join(L1D, '基金详细信息_最终版.csv')
info = pd.read_csv(p_info1 if os.path.exists(p_info1) else p_info2)

p_mgr1 = os.path.join(OUT, '基金经理信息_最终版.csv')
p_mgr2 = os.path.join(L1D, '基金经理信息_最终版.csv')
mgr = pd.read_csv(p_mgr1 if os.path.exists(p_mgr1) else p_mgr2)
fm = fm.join(info.set_index('fund_code')[['基金经理人']], how='left')
mg = mgr.drop_duplicates('manager_name').set_index('manager_name')[['gender', 'education', 'CFA', 'school']]
fm = fm.join(mg, on='基金经理人', how='left')
fm['male'] = np.where(fm['gender'].isna(), np.nan, (fm['gender'].astype(str) == '男').astype(float))
fm['has_CFA'] = np.where(fm['CFA'].isna(), np.nan, (fm['CFA'].astype(str) == '是').astype(float))
fm['master_up'] = np.where(fm['education'].isna(), np.nan,
                           fm['education'].astype(str).isin(['硕士', '博士']).astype(float))
TOP = ['北京大学', '清华大学', '复旦大学', '上海交通大学', '中国人民大学', '浙江大学',
       '南京大学', '武汉大学', '中山大学', '南开大学', '厦门大学', '中央财经大学',
       '上海财经大学', '对外经济贸易大学', '西安交通大学', '哈尔滨工业大学']
_sch = fm['school'].astype('object').where(fm['school'].notna(), None)
fm['top_school'] = [np.nan if (v is None) else float(any(t in str(v) for t in TOP))
                    for v in _sch]
fm = fm.join(dv, how='left')

DVS = [('ex_hs300', '超额收益(相对沪深300)'), ('ff3_alpha', 'FF3 alpha'), ('ff5_alpha', 'FF5 alpha')]


def reg1(y, x, with_ctrl):
    cols = [y, x] + (CTRL if with_ctrl else [])
    dd = fm[cols].dropna()
    if len(dd) < 40:
        return None
    dd = dd.copy()
    for c in [y, x]:
        if dd[c].nunique() > 2:
            dd[c] = winsor(dd[c])
    m = sm.OLS(dd[y].astype(float), sm.add_constant(dd[[x] + (CTRL if with_ctrl else [])].astype(float))
               ).fit(cov_type='HC1')
    return dict(n=int(m.nobs), b=round(float(m.params[x]), 6), t=round(float(m.tvalues[x]), 2),
                p=round(float(m.pvalues[x]), 4), r2=round(float(m.rsquared), 4))


res = {'因变量': {k: v for k, v in DVS},
       '因变量覆盖': {k: int(dv[k].notna().sum()) for k, _ in DVS},
       '因变量相关': json.loads(dv.corr().round(3).to_json()),
       '覆盖率_基金层': {}, '结果': {}}
ALLX = CONT + BG_CONT + BG_DUM
for x in ALLX:
    res['覆盖率_基金层'][x] = round(float(fm[x].notna().mean()), 4)
    res['结果'][x] = {}
    for y, _ in DVS:
        res['结果'][x][y] = {
            '裸回归': reg1(y, x, False),
            '加控制': None if x in BG_CONT + BG_DUM else reg1(y, x, True),
        }

st = lambda p: '***' if p < 0.01 else ('**' if p < 0.05 else ('*' if p < 0.1 else ''))
print('\n=== 单变量回归全表（基金层横截面 OLS + HC1；加控制=含任职/年龄/规模）===')
print('%-20s %6s | %-16s | %-16s | %-16s' % ('指标', '覆盖', '超沪深300', 'FF3 alpha', 'FF5 alpha'))
for x in ALLX:
    cells = []
    for y, _ in DVS:
        r = res['结果'][x][y]
        v = r['加控制'] or r['裸回归']
        cells.append('—' if v is None else 't=%+6.2f%-3s' % (v['t'], st(v['p'])))
    print('%-20s %5.0f%% | %-16s | %-16s | %-16s'
          % (x, res['覆盖率_基金层'][x] * 100, cells[0], cells[1], cells[2]))

with open(os.path.join(OUT, '单变量全表_去2026Q2敏感性_2026-09-10.json'), 'w', encoding='utf-8') as f:
    json.dump(res, f, ensure_ascii=False, indent=1)
fm.reset_index().to_csv(os.path.join(OUT, '单变量全表_基金层数据_去2026Q2_2026-09-10.csv'),
                        index=False, encoding='utf-8-sig')
print('\n已保存 output/单变量全表_去2026Q2敏感性_2026-09-10.json')

# ---------- 「总的」联立回归：全部连续型指标同时进入 ----------
res['联立'] = {}
for y, lab in DVS:
    xs = [x for x in CONT if res['覆盖率_基金层'][x] >= 0.85]
    dd = fm[[y] + xs + CTRL].dropna()
    dd = dd.copy()
    for c in dd.columns:
        dd[c] = winsor(dd[c])
    m = sm.OLS(dd[y].astype(float), sm.add_constant(dd[xs + CTRL].astype(float))).fit(cov_type='HC1')
    res['联立'][y] = dict(n=int(m.nobs), r2=round(float(m.rsquared), 4), 变量数=len(xs),
                        系数={x: dict(b=round(float(m.params[x]), 6), t=round(float(m.tvalues[x]), 2),
                                    p=round(float(m.pvalues[x]), 4)) for x in xs + CTRL})

print('\n=== 联立回归（全部连续指标 + 三控制，覆盖率≥85%）===')
for y, lab in DVS:
    v = res['联立'][y]
    print('\n--- DV = %s（N=%d，R²=%.4f，%d 个指标）---' % (lab, v['n'], v['r2'], v['变量数']))
    for x, c in v['系数'].items():
        print('   %-20s b=%+.6f t=%+6.2f%s' % (x, c['b'], c['t'], st(c['p'])))

# 显著性汇总：三因变量下的显著次数（|t| 且 p<0.05，加控制口径）
res['显著性汇总'] = {}
for x in ALLX:
    cnt = 0
    dirs = []
    for y, _ in DVS:
        r = res['结果'][x][y]
        v = r['加控制'] or r['裸回归']
        if v and v['p'] < 0.05:
            cnt += 1
            dirs.append(int(np.sign(v['b'])))
    res['显著性汇总'][x] = dict(显著次数=cnt, 方向一致=bool(len(set(dirs)) <= 1) if dirs else None)

print('\n=== 三因变量显著性稳健度（p<0.05 的口径数 / 3）===')
for x in ALLX:
    s = res['显著性汇总'][x]
    print('  %-20s %d/3  方向一致=%s' % (x, s['显著次数'], s['方向一致']))

with open(os.path.join(OUT, '单变量全表_去2026Q2敏感性_2026-09-10.json'), 'w', encoding='utf-8') as f:
    json.dump(res, f, ensure_ascii=False, indent=1)
print('\n已更新 output/单变量全表_去2026Q2敏感性_2026-09-10.json（含联立与显著性汇总）')
