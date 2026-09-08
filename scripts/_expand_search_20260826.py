# -*- coding: utf-8 -*-
"""候选指标扩展搜索——第二轮（2026-08-26）
================================================================================
背景：现有 15 成分之外，按文献再扫一轮候选，全部用本沙箱数据实测，
按与既有指标相同的准入规则裁决（方向与文献一致 + 5% 显著 + 基金层覆盖 ≥80%
+ 与现有维度相关 <0.7 避免冗余）。

候选池（文献出处）：
  C1 AG_SEL   选择度 1−R²      Amihud & Goyenko (2013 RFS)     → L3 配置选择
  C2 LOTTO_MAX 彩票偏好 MAX    Bali, Cakici & Whitelaw (2011 JFE) → L2 认知
  C3 LOTTO_ISKEW 偏好偏度      Kumar (2009 JF)                  → L2 认知
  C4 DCAP     下行捕获率       标准非参数择时度量               → L4a 对照
  C5 DUR      隐含持仓久期     Cremers & Pareek (2016 JFE)      → L5 交易执行
  C6 NCSKEW   残差偏度         Harvey & Siddique (2000 JF)      → 对照（风险暴露）

输出：output/候选扩展_2026-08-26.json
"""
import pandas as pd
import numpy as np
import os
import json
import statsmodels.api as sm

BASE = r'd:\Desktop\基金经理行为分析研究'
DATA = os.path.join(BASE, '指标计算流水线', 'data')
OUT = os.path.join(BASE, 'output')
TODAY = '2026-08-26'
CTRL = ['mgr_total_tenure_v2', 'log_fund_age', 'log_aum']
res = {'检索说明': 'Exa 限流(HTTP 429)、Jina Reader 被 IP 信誉拦截(401)，'
                   '外网检索不可用；候选出处依据本地文献底库与经典文献，'
                   'PDF 核验沿用参考文献工作流。'}


def winsor(s, p=0.01):
    return s.clip(s.quantile(p), s.quantile(1 - p))


def z(s):
    return (s - s.mean()) / s.std()


def ew(frame):
    return frame.sum(axis=1, skipna=True) / frame.notna().sum(axis=1)


def reg(y, X):
    d = pd.concat([y, X], axis=1).dropna()
    return sm.OLS(d.iloc[:, 0], sm.add_constant(d.iloc[:, 1:])).fit(cov_type='HC1')


# ---------------- 数据 ----------------
print('读取净值…')
nav = pd.read_csv(os.path.join(DATA, 'L4_风险应对层', '基金净值历史_全量.csv'),
                  usecols=['fund_code', 'date', 'daily_return'])
nav = nav.rename(columns={'daily_return': 'ret'})
# 日度收益率列单位为万分之几（如 2.7154 ≈ 0.027%）
nav['ret'] = pd.to_numeric(nav['ret'], errors='coerce') / 10000
nav['date'] = pd.to_datetime(nav['date'])
nav = nav.dropna(subset=['ret'])
nav['ym'] = nav['date'].dt.to_period('M')
# 日度复利 → 月度
mret = (nav.groupby(['fund_code', 'ym'])
        .apply(lambda g: (1 + g['ret']).prod() - 1, include_groups=False)
        .reset_index(name='ret'))
print('月度基金收益：%d 条' % len(mret))

ff = pd.read_csv(os.path.join(DATA, 'FF因子', 'FF5月度因子.csv'), parse_dates=['date'])
ff['ym'] = ff['date'].dt.to_period('M')
ff = ff.set_index('ym')[['RF', 'MKT', 'SMB', 'HML']]

mg = mret.merge(ff.reset_index(), on='ym', how='inner')
mg['ex'] = mg['ret'] - mg['RF']
mg['ym'] = mg['ym'].astype('str')


def rolling_ff3_stats(g, window=24):
    """逐基金滚动 FF3 回归 → R²、残差偏度。"""
    g = g.sort_values('ym').reset_index(drop=True)
    out = []
    X = g[['MKT', 'SMB', 'HML']].values
    ex = g['ex'].values
    mkt = g['MKT'].values
    for i in range(window, len(g) + 1):
        xs, ys, ms = X[i - window:i], ex[i - window:i], mkt[i - window:i]
        if np.std(ys) < 1e-8:
            continue
        Z = np.column_stack([np.ones(window), xs])
        beta, *_ = np.linalg.lstsq(Z, ys, rcond=None)
        resid = ys - Z @ beta
        ss_res = np.sum(resid ** 2)
        ss_tot = np.sum((ys - ys.mean()) ** 2)
        r2 = 1 - ss_res / ss_tot if ss_tot > 0 else np.nan
        sd = resid.std()
        sk = float(np.mean(((resid - resid.mean()) / sd) ** 3)) if sd > 1e-8 else np.nan
        # 下行捕获（同窗口）
        dn = ms < 0
        dcap = float(ys[dn].mean() / ms[dn].mean()) if dn.sum() >= 6 and ms[dn].mean() < 0 else np.nan
        out.append((g['ym'].iloc[i - 1], 1 - r2, sk, dcap))
    return out


print('滚动 FF3 统计（24 个月窗口）…')
rows = []
for fc, g in mg.groupby('fund_code'):
    for ym, sel, sk, dcap in rolling_ff3_stats(g):
        rows.append((fc, ym, sel, sk, dcap))
roll = pd.DataFrame(rows, columns=['fund_code', 'ym', 'ag_sel', 'ncskew', 'dcap'])
print('滚动统计：%d 条' % len(roll))

# 季度末取值 + 滞后一期（与主口径一致：上期值解释本期）
roll['q'] = pd.to_datetime(roll['ym'].astype(str)).dt.to_period('Q')
rq = (roll.sort_values('ym')
      .groupby(['fund_code', 'q']).last().reset_index())
rq['q_lag'] = rq.groupby('fund_code')['q'].shift(1)
cand = rq.dropna(subset=['q_lag']).set_index(['fund_code', 'q_lag'])[
    ['ag_sel', 'ncskew', 'dcap']]

# 面板对齐
panel = pd.read_csv(os.path.join(OUT, f'分析面板_v3_{TODAY}.csv'), parse_dates=['report_date'])
panel['q'] = panel['report_date'].dt.to_period('Q')
panel = panel.set_index(['fund_code', 'q'])
panel = panel.join(cand, how='left')
panel = panel.reset_index()

# ---------------- C2/C3 彩票偏好（持仓加权个股 MAX / 偏度） ----------------
print('个股月收益 → MAX / 偏度…')
stk = pd.read_csv(os.path.join(DATA, '股价行情', '个股月收益率_全量.csv'))
scol = {c.upper(): c for c in stk.columns}
print('个股月收益列：', list(stk.columns)[:8], '行数', len(stk))
dcol = [c for c in stk.columns if 'date' in c.lower() or '月份' in c or '日期' in c][0]
rcol = [c for c in stk.columns if 'ret' in c.lower() or '收益' in c][0]
codecol = [c for c in stk.columns if 'code' in c.lower() or '代码' in c][0]
stk[dcol] = pd.to_datetime(stk[dcol])
stk['ym'] = stk[dcol].dt.to_period('M')
stk[rcol] = pd.to_numeric(stk[rcol].astype(str).str.replace('%', ''), errors='coerce') / 100
stk = stk.dropna(subset=[rcol])

g = stk.sort_values([codecol, 'ym']).groupby(codecol)
stk['max12'] = g[rcol].transform(lambda s: s.rolling(12, min_periods=9).max())
stk['iskew36'] = g[rcol].transform(lambda s: s.rolling(36, min_periods=24).skew())
stk_lag = stk.copy()
stk_lag['ym_lag1'] = stk_lag.groupby(codecol)['ym'].shift(1)  # 滞后一个月的个股特征

hold = pd.read_csv(os.path.join(DATA, 'L2_持仓偏离层', '基金持仓明细_全量修正版_v3.csv'),
                   usecols=['fund_code', 'report_date', 'stock_code', 'hold_ratio'],
                   low_memory=False)
hold['stock_code'] = hold['stock_code'].astype(str).str.split('.').str[0].str.zfill(6)
hold['report_date'] = pd.to_datetime(hold['report_date'])
hold['q'] = hold['report_date'].dt.to_period('Q')
# 用滞后一月的个股特征（期末持仓 × 上月特征 ≈ 期初可观测）
hold['ym_feat'] = hold['report_date'].dt.to_period('M').apply(lambda p: p - 1)
feat = stk_lag.copy()
feat[codecol] = feat[codecol].astype(str).str.split('.').str[0].str.zfill(6)
feat = feat.set_index([codecol, 'ym_lag1'])[['max12', 'iskew36']]
feat.index.names = ['stock_code', 'ym_feat']
hold = hold.merge(feat.reset_index(), on=['stock_code', 'ym_feat'], how='left')
hold['w'] = pd.to_numeric(hold['hold_ratio'], errors='coerce') / 100

agg = (hold.dropna(subset=['max12', 'w'])
       .query('w > 0')
       .groupby(['fund_code', 'q'])
       .apply(lambda g: pd.Series({
           'lotto_max': np.average(g['max12'], weights=g['w']),
           'lotto_iskew': np.average(g['iskew36'], weights=g['w'])},
           index=['lotto_max', 'lotto_iskew']),
           include_groups=False)
       .reset_index())
print('彩票偏好（持仓加权）：%d 条' % len(agg))
panel = panel.merge(agg, on=['fund_code', 'q'], how='left')

# ---------------- C5 持仓久期 ----------------
print('隐含持仓久期…')
hold_s = hold[['fund_code', 'q', 'stock_code', 'w']].dropna()
qs = sorted(hold_s['q'].unique())
dur_rows = []
for fc, gfc in hold_s.groupby('fund_code'):
    gfc = gfc.sort_values('q')
    qs_f = gfc['q'].unique()
    for a, b in zip(qs_f[:-1], qs_f[1:]):
        wa = gfc[gfc['q'] == a].set_index('stock_code')['w']
        wb = gfc[gfc['q'] == b].set_index('stock_code')['w']
        j = pd.concat([wa, wb], axis=1, join='inner').dropna()
        if len(j) == 0:
            continue
        overlap = float(np.minimum(j.iloc[:, 0], j.iloc[:, 1]).sum())
        keep = 1 - overlap
        if keep > 1e-4:
            dur_rows.append((fc, b, 1.0 / keep))
dur = pd.DataFrame(dur_rows, columns=['fund_code', 'q', 'dur'])
dur['dur'] = dur['dur'].clip(upper=20)  # 极端值保护
print('久期：%d 条，中位数 %.2f 季' % (len(dur), dur['dur'].median()))
panel = panel.merge(dur, on=['fund_code', 'q'], how='left')

# ---------------- 基金层汇总 + S1 定向检验 ----------------
CANDS = {
    'ag_sel': ('C1 选择度 1−R²', 'Amihud & Goyenko (2013 RFS)', '+', 'L3 配置选择'),
    'lotto_max': ('C2 彩票偏好 MAX', 'Bali, Cakici & Whitelaw (2011 JFE)', '−', 'L2 认知'),
    'lotto_iskew': ('C3 彩票偏好 偏度', 'Kumar (2009 JF)', '−', 'L2 认知'),
    'dcap': ('C4 下行捕获率', '标准非参数择时度量', '−', 'L4a 对照'),
    'dur': ('C5 隐含持仓久期', 'Cremers & Pareek (2016 JFE)', '+', 'L5 交易执行'),
    'ncskew': ('C6 残差偏度', 'Harvey & Siddique (2000 JF)', 'ns', '对照（风险暴露）'),
}
fm = panel.groupby('fund_code')[
    list(CANDS) + CTRL + ['ff5_adj_return']].mean()
for c in list(CANDS) + CTRL:
    fm[c] = winsor(pd.to_numeric(fm[c], errors='coerce'))
Y = fm['ff5_adj_return']

# 现有六维得分（用于冗余检查）
DIMS6 = {
    '基本面优势': [('mgr_total_tenure_v2', -1), ('log_fund_age', -1), ('log_aum', -1)],
    '认知能力': [('risk_asym', +1), ('de', -1), ('oc_conf', -1)],
    '配置选择能力': [('ICI', +1), ('ISDI', -1)],
    '风险应对能力': [('ARG', +1), ('timing', +1)],
    '风险转化能力': [('mppm8_lag', +1), ('sortino8_lag', +1), ('sharpe8_lag', +1)],
    '交易执行能力': [('SDI', -1), ('lsv', +1)],
}
ALLC = [m for v in DIMS6.values() for m, _ in v]
sel_cols = list(dict.fromkeys([m for m in ALLC if m != 'timing'] + CTRL))
fmx = panel.groupby('fund_code')[sel_cols].mean().join(
    pd.read_csv(os.path.join(OUT, f'择时系数_季度HM_{TODAY}.csv')).set_index('fund_code')[['timing']],
    how='left')
for c in ALLC:
    fmx[c] = winsor(pd.to_numeric(fmx[c], errors='coerce'))
sc = pd.DataFrame(index=fmx.index)
for dim, items in DIMS6.items():
    sc[dim] = ew(pd.DataFrame({m: sg * z(fmx[m]) for m, sg in items}))

print()
print('=' * 88)
print('候选实测：S1 定向（含三控制变量，HC1） + 覆盖 + 与现有维度最大相关')
print('=' * 88)
verdict = {}
for k, (name, lit, direction, layer) in CANDS.items():
    s = fm[k]
    cov = float(s.notna().mean())
    d = pd.concat([Y.rename('y'), s.rename('x'), fm[CTRL]], axis=1).dropna()
    m = sm.OLS(d['y'], sm.add_constant(d[['x'] + CTRL])).fit(cov_type='HC1')
    t_, p_ = float(m.tvalues['x']), float(m.pvalues['x'])
    # 与现有六维的最大相关
    j = pd.concat([z(s).rename('cand'), sc], axis=1).dropna()
    corr_max = float(j.corr()['cand'].drop('cand').abs().max())
    corr_with = str(j.corr()['cand'].drop('cand').abs().idxmax())
    dir_ok = ((direction == '+' and t_ > 0) or (direction == '−' and t_ < 0)
              or direction == 'ns')
    sig = p_ < 0.05
    gates = dict(方向一致=bool(dir_ok), 显著=bool(sig), 覆盖=bool(cov >= 0.8),
                 冗余=bool(corr_max < 0.7))
    passed = all(gates.values()) and direction != 'ns'
    verdict[k] = dict(名称=name, 文献=lit, 层=layer, 预期方向=direction,
                      n=int(m.nobs), t=round(t_, 2), p=round(p_, 4),
                      覆盖=round(cov, 4), 与现有维度最大相关=round(corr_max, 3),
                      最大相关维度=corr_with, 准入门槛=gates,
                      裁决='通过' if passed else '不通过')
    print('%-14s %-34s 预期%s  t=%+7.2f  p=%.4f  覆盖 %5.1f%%  max|r|=%.3f(%s)  → %s'
          % (k, name[:32], direction, t_, p_, cov * 100, corr_max, corr_with,
             '通过' if passed else '不通过'))

res['候选'] = verdict
res['面板季度对齐数'] = int(len(panel))
with open(os.path.join(OUT, f'候选扩展_{TODAY}.json'), 'w', encoding='utf-8') as f:
    json.dump(res, f, ensure_ascii=False, indent=2, default=str)
print('\n已落盘：output/候选扩展_%s.json' % TODAY)
