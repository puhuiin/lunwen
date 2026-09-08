# -*- coding: utf-8 -*-
"""指标改进：L4b 行为型捕获率 + L2 认知新指标（2026-08-27）
================================================================================
目标：按接力提示词与用户三问，推进论文指标优化——
  (A) L4b 风险转化能力：用【上行捕获率 up_cap / 下行捕获率 down_cap】替代
      mppm8/sortino8/sharpe8（三者为风险调整后业绩测度，与 FF5 alpha 概念同源，
      被 D2/D3/Q2 质疑"用业绩解释业绩"）。捕获率衡量基金对市场上/下行状态的
      非对称响应——正是"风险转化"的行为含义，且可在 400 只面板季度收益上
      直接计算（覆盖≈100%），修复 _expand_search 因日频NAV薄覆盖导致的 50% 失败。
  (B) L2 认知层新增（文献依据，非第二轮已否的 6 候选）：
      ① 趋势外推偏差 extrapolation = 持仓加权个股过去12月收益（Greenwood & Shleifer 2014）
      ② 有限关注度 attention = 持仓加权个股上月|收益|极端度（Barber & Odean 2008）
      二者均从持仓+个股月收益构造，与现有 risk_asym/de/oc_conf 互补。

评估：沿用 4 门槛（方向一致 + 5%显著 + 基金层覆盖≥80% + 与现有六维相关<0.7）
      + 复合重验（新 L4b / 新 L2 的联立 t 与 R²）。
数字一律来自本脚本与 output/，不手写。
"""
import pandas as pd, numpy as np, os, json, statsmodels.api as sm

BASE = r'd:\Desktop\基金经理行为分析研究'
DATA = os.path.join(BASE, '指标计算流水线', 'data')
OUT = os.path.join(BASE, 'output')
TODAY = '2026-08-26'
CTRL = ['mgr_total_tenure_v2', 'log_fund_age', 'log_aum']
res = {}


def winsor(s, p=0.01):
    s = pd.to_numeric(s, errors='coerce')
    return s.clip(s.quantile(p), s.quantile(1 - p))


def z(s):
    s = pd.to_numeric(s, errors='coerce')
    return (s - s.mean()) / s.std()


def ew(frame):
    return frame.sum(axis=1, skipna=True) / frame.notna().sum(axis=1)


def reg(y, X):
    d = pd.concat([y, X], axis=1).dropna()
    return sm.OLS(d.iloc[:, 0], sm.add_constant(d.iloc[:, 1:])).fit(cov_type='HC1')


# ---------------- 面板 ----------------
panel = pd.read_csv(os.path.join(OUT, f'分析面板_v3_{TODAY}.csv'),
                   parse_dates=['report_date'])
panel['q'] = panel['report_date'].dt.to_period('Q')
panel['fund_ex'] = panel['quarter_return'] - panel['ff5_RF']
panel['mkt_ex'] = panel['ff5_MKT_excess']
# 择时系数（基金层，季度HM）来自独立文件，并入面板保持口径一致
_timing = pd.read_csv(os.path.join(OUT, '择时系数_季度HM_2026-08-26.csv'))[['fund_code', 'timing']]
panel = panel.merge(_timing, on='fund_code', how='left')


# ============ (A) L4b 上行/下行捕获率 ============
def cap_stats(g):
    g = g.sort_values('report_date')
    up = g[g['mkt_ex'] > 0]
    dn = g[g['mkt_ex'] < 0]
    if len(up) >= 6 and len(dn) >= 6 and up['mkt_ex'].mean() != 0 and dn['mkt_ex'].mean() != 0:
        return pd.Series({'up_cap': up['fund_ex'].mean() / up['mkt_ex'].mean(),
                          'down_cap': dn['fund_ex'].mean() / dn['mkt_ex'].mean()})
    return pd.Series({'up_cap': np.nan, 'down_cap': np.nan})


print('计算上行/下行捕获率…')
cap = panel.groupby('fund_code').apply(cap_stats, include_groups=False).reset_index()
print('  捕获率基金数：%d（覆盖 %.1f%%）' % (cap['up_cap'].notna().sum(),
      100 * cap['up_cap'].notna().mean()))
res['L4b_捕获率'] = dict(基金数=int(cap['up_cap'].notna().sum()),
                      覆盖=round(float(cap['up_cap'].notna().mean()), 4),
                      up_cap_中位=round(float(cap['up_cap'].median()), 3),
                      down_cap_中位=round(float(cap['down_cap'].median()), 3))

# ============ (B) L2 认知新指标 ============
print('个股月收益 → 趋势外推/有限关注特征…')
stk = pd.read_csv(os.path.join(DATA, '股价行情', '个股月收益率_全量.csv'))
scol = {c.upper(): c for c in stk.columns}
dcol = [c for c in stk.columns if 'date' in c.lower() or '月份' in c or '日期' in c][0]
rcol = [c for c in stk.columns if 'ret' in c.lower() or '收益' in c][0]
codecol = [c for c in stk.columns if 'code' in c.lower() or '代码' in c][0]
stk[dcol] = pd.to_datetime(stk[dcol])
stk['ym'] = stk[dcol].dt.to_period('M')
stk[rcol] = pd.to_numeric(stk[rcol].astype(str).str.replace('%', ''), errors='coerce') / 100
stk = stk.dropna(subset=[rcol])
g = stk.sort_values([codecol, 'ym']).groupby(codecol)
# 趋势外推：个股过去12月平均收益（动量暴露）
stk['mom12'] = g[rcol].transform(lambda s: s.rolling(12, min_periods=9).mean())
# 有限关注：个股上月|收益|极端度（注意力代理）= 个股月收益绝对值
stk['absret1m'] = stk[rcol].abs()
hold = pd.read_csv(os.path.join(DATA, 'L2_持仓偏离层', '基金持仓明细_全量修正版_v3.csv'),
                   usecols=['fund_code', 'report_date', 'stock_code', 'hold_ratio'],
                   low_memory=False)
hold['stock_code'] = hold['stock_code'].astype(str).str.split('.').str[0].str.zfill(6)
hold['report_date'] = pd.to_datetime(hold['report_date'])
hold['q'] = hold['report_date'].dt.to_period('Q')
hold['ym_feat'] = hold['report_date'].dt.to_period('M').apply(lambda p: p - 1)
# 个股特征以真实月份 ym 为索引；持仓端 ym_feat = 报告月-1，
# 自然取到"报告前一个月"的个股特征（无前视偏差，原 stk_lag 移位会导致前视）。
feat = stk.copy()
feat[codecol] = feat[codecol].astype(str).str.split('.').str[0].str.zfill(6)
feat = feat.set_index([codecol, 'ym'])[['mom12', 'absret1m']]
feat.index.names = ['stock_code', 'ym_feat']
hold = hold.merge(feat.reset_index(), on=['stock_code', 'ym_feat'], how='left')
hold['w'] = pd.to_numeric(hold['hold_ratio'], errors='coerce') / 100
agg = (hold.dropna(subset=['mom12', 'w']).query('w > 0')
       .groupby(['fund_code', 'q'])
       .apply(lambda x: pd.Series({'extrap': np.average(x['mom12'], weights=x['w']),
                                   'attn': np.average(x['absret1m'], weights=x['w'])}),
              include_groups=False).reset_index())
print('  L2 候选（持仓加权）：%d 条基金-季' % len(agg))
panel = panel.merge(agg, on=['fund_code', 'q'], how='left')

# ============ 基金层汇总 ============
base_comps = ['risk_asym', 'de', 'oc_conf', 'ICI', 'ISDI', 'ARG', 'timing',
              'mppm8_lag', 'sortino8_lag', 'sharpe8_lag', 'SDI', 'lsv']
sel = base_comps + CTRL + ['ff5_adj_return']
fm = panel.groupby('fund_code')[sel].mean()
for c in base_comps + CTRL:
    fm[c] = winsor(fm[c])
fm = fm.join(cap.set_index('fund_code')[['up_cap', 'down_cap']], how='left')
# L2 候选：基金层时序均值
l2c = panel.groupby('fund_code')[['extrap', 'attn']].mean()
for c in ['extrap', 'attn']:
    l2c[c] = winsor(l2c[c])
fm = fm.join(l2c, how='left')
Y = fm['ff5_adj_return']
print('基金层样本 %d 只' % len(fm))

# ============ 现有六维得分（冗余检查用） ============
DIMS6 = {
    '基本面优势': [('mgr_total_tenure_v2', -1), ('log_fund_age', -1), ('log_aum', -1)],
    '认知能力': [('risk_asym', +1), ('de', -1), ('oc_conf', -1)],
    '配置选择能力': [('ICI', +1), ('ISDI', -1)],
    '风险应对能力': [('ARG', +1), ('timing', +1)],
    '风险转化能力': [('mppm8_lag', +1), ('sortino8_lag', +1), ('sharpe8_lag', +1)],
    '交易执行能力': [('SDI', -1), ('lsv', +1)],
}
ALLC = [m for v in DIMS6.values() for m, _ in v]
sc = pd.DataFrame(index=fm.index)
for dim, items in DIMS6.items():
    sc[dim] = ew(pd.DataFrame({m: sg * z(fm[m]) for m, sg in items}))

# ============ 4 门槛评估 ============
print('\n' + '=' * 88)
print('新/改进指标 4 门槛评估（S1 定向：含三控制变量，HC1）')
print('=' * 88)
NEW = {
    'up_cap': ('上行捕获率', 'L4b 风险转化', '+', '市场上行段参与能力'),
    'down_cap': ('下行捕获率', 'L4b 风险转化', '-', '市场下行段规避能力'),
    'extrap': ('趋势外推偏差', 'L2 认知', '-', 'Greenwood & Shleifer (2014)'),
    'attn': ('有限关注度', 'L2 认知', '-', 'Barber & Odean (2008)'),
}
verdict = {}
for k, (name, layer, direction, lit) in NEW.items():
    s = fm[k]
    cov = float(s.notna().mean())
    d = pd.concat([Y.rename('y'), s.rename('x'), fm[CTRL]], axis=1).dropna()
    m = sm.OLS(d['y'], sm.add_constant(d[['x'] + CTRL])).fit(cov_type='HC1')
    t_, p_ = float(m.tvalues['x']), float(m.pvalues['x'])
    j = pd.concat([z(s).rename('cand'), sc], axis=1).dropna()
    corr_max = float(j.corr()['cand'].drop('cand').abs().max())
    corr_with = str(j.corr()['cand'].drop('cand').abs().idxmax())
    dir_ok = ((direction == '+' and t_ > 0) or (direction == '-' and t_ < 0))
    sig = p_ < 0.05
    gates = dict(方向一致=bool(dir_ok), 显著=bool(sig), 覆盖=bool(cov >= 0.8),
                 冗余=bool(corr_max < 0.7))
    passed = all(gates.values()) and True
    verdict[k] = dict(名称=name, 层=layer, 文献=lit, 预期方向=direction,
                      n=int(m.nobs), t=round(t_, 2), p=round(p_, 4),
                      覆盖=round(cov, 4), 与现有维度最大相关=round(corr_max, 3),
                      最大相关维度=corr_with, 准入门槛=gates, 裁决='通过' if passed else '不通过')
    print('%-10s %-12s 预期%s t=%+7.2f p=%.4f 覆盖%5.1f%% max|r|=%.3f(%s) → %s'
          % (k, name, direction, t_, p_, cov * 100, corr_max, corr_with,
             '通过' if passed else '不通过'))
res['新指标4门槛'] = verdict

# ============ 复合重验：新 L4b / 新 L2 ============
print('\n=== 复合重验 ===')
# 基线 L4b（旧）
score_base = pd.DataFrame(index=fm.index)
score_base['L4b旧'] = ew(pd.DataFrame({m: sg * z(fm[m]) for m, sg in
                                      [('mppm8_lag', +1), ('sortino8_lag', +1), ('sharpe8_lag', +1)]}))
# 新 L4b（捕获率）
score_new = pd.DataFrame(index=fm.index)
score_new['L4b新'] = ew(pd.DataFrame({'up_cap': +1 * z(fm['up_cap']),
                                      'down_cap': -1 * z(fm['down_cap'])}))
# 新 L2（加 extrap/attn）
l2_new = ew(pd.DataFrame({'risk_asym': +1 * z(fm['risk_asym']),
                          'de': -1 * z(fm['de']),
                          'oc_conf': -1 * z(fm['oc_conf']),
                          'extrap': -1 * z(fm['extrap']),
                          'attn': -1 * z(fm['attn'])}))
score_new['L2新'] = l2_new
sc_all = sc.rename(columns={'认知能力': '认知能力_旧'}).copy()
sc_all['风险转化能力_旧'] = score_base['L4b旧']
sc_all['风险转化能力_新'] = score_new['L4b新']
sc_all['认知能力_新'] = score_new['L2新']
sc_all = sc_all.join(fm[CTRL])
for tag in ['风险转化能力_旧', '风险转化能力_新', '认知能力_旧', '认知能力_新']:
    X = [tag] if tag.startswith('认知') or tag.startswith('风险转化') else [tag] + CTRL
    # 认知/风险转化均为行为维，含三控制变量（与口径一致）
    X = [tag] + CTRL
    mod = reg(Y, sc_all[X])
    print('  %-14s coef=%+.5f t=%+6.2f p=%.4f R2=%.4f' % (tag, mod.params[tag], mod.tvalues[tag], mod.pvalues[tag], mod.rsquared))

# 六维联立对照（旧 L4b vs 新 L4b）
print('\n六维联立对照（L1–L5 六维，不叠加控制变量）：')
for l4b_tag, l4b_series in [('旧L4b', score_base['L4b旧']), ('新L4b', score_new['L4b新'])]:
    dims = {'基本面优势': ew(pd.DataFrame({m: sg * z(fm[m]) for m, sg in DIMS6['基本面优势']})),
            '认知能力': sc['认知能力'],
            '配置选择能力': sc['配置选择能力'],
            '风险应对能力': sc['风险应对能力'],
            l4b_tag: l4b_series,
            '交易执行能力': sc['交易执行能力']}
    dd = pd.concat(dims.values(), axis=1)
    dd.columns = list(dims.keys())
    mall = reg(Y, dd)
    print('  %s: R2=%.4f  L4b t=%+6.2f' % (l4b_tag, mall.rsquared, mall.tvalues[l4b_tag]))
res['复合重验'] = '见上方打印'

with open(os.path.join(OUT, f'指标改进_{TODAY[:7]}-27.json'), 'w', encoding='utf-8') as f:
    json.dump(res, f, ensure_ascii=False, indent=2, default=str)
print('\n已落盘：output/指标改进_%s.json' % (TODAY[:7] + '-27'))
