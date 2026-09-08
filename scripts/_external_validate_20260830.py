# -*- coding: utf-8 -*-
"""外部效度检验：论文样本之外的基金，行为画像能否区分绩优与绩差（2026-08-30）

思路
----
用户要求：找真实世界里绩效好 / 差的基金，用论文的方法构建画像，比较两组画像特征，
检验本画像能否刻画基金经理能力。

设计要点（务必守住，否则结论不成立）
--------------------------------
1. **这不是循环论证**。分组变量是"近 3 年收益"（业绩），检验变量是"行为维度"
   （L2 risk_asym、L4a timing），二者不同源，属于标准的**已知群体效度检验**
   （known-groups validity），结论有效。
2. **L4b 是平凡对照，不是证据**。Sharpe/Sortino/MPPM 本身就是风险调整后业绩，
   绩优组必然更高。它只作**操纵性检查**（验证分组确实生效），不计入证据。
3. **统一比较窗口**：各基金成立时间不一，必须截到同一区间，否则比的是不同历史时期。
4. **结果全部报告**，包括与预期相反的部分。

本轮范围：仅用净值可算的指标（L4a timing、L4b 三个测度、L2 risk_asym）。
持仓类指标（L3 的 ICI/ISDI、L2 的 de）需另行下载持仓，后续再补。
"""
import io
import os
import sys

import numpy as np
import pandas as pd

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, 'output')
FF5 = os.path.join(BASE, '指标计算流水线', 'data', 'FF因子', 'FF5日度因子.csv')

WIN_START, WIN_END = '2019-03-31', '2026-06-30'   # 统一比较窗口
MIN_Q = 24                                        # 窗口内最少季度数
N_EACH = 25                                       # 每组候选池大小


def log(m):
    print(m, flush=True)


# ---------------------------------------------------------------- 指标（与论文表 1 同口径）
def to_quarter(nav):
    s = nav.set_index('净值日期')['单位净值']
    return s.resample('QE').last().pct_change().dropna()


def roll_sharpe(r, w=8):
    return r.rolling(w).mean() / r.rolling(w).std(ddof=1)


def roll_sortino(r, w=8):
    mu = r.rolling(w).mean()
    dn = r.rolling(w).apply(
        lambda x: np.std(x[x < 0], ddof=1) if (x < 0).sum() >= 2 else np.nan, raw=True)
    return mu / dn


def mppm(r, rho=3.0):
    r = np.asarray(r, dtype=float)
    r = r[~np.isnan(r)]
    if len(r) == 0:
        return np.nan
    return float(np.log(np.mean(np.power(np.maximum(1.0 + r, 1e-8), 1.0 - rho))) / (1.0 - rho) * 4)


def roll_mppm(r, w=8):
    return r.rolling(w).apply(lambda x: mppm(x), raw=True)


def roll_risk_asym(r, w=8):
    def f(x):
        up, dn = x[x > 0], x[x < 0]
        if len(up) < 2 or len(dn) < 2:
            return np.nan
        return np.std(up, ddof=1) - np.std(dn, ddof=1)
    return r.rolling(w).apply(f, raw=True)


def hm_timing(r_q, mkt_q):
    d = pd.concat([r_q.rename('r'), mkt_q.rename('mkt')], axis=1, sort=True).dropna()
    if len(d) < 12:
        return np.nan
    X = np.column_stack([np.ones(len(d)), d['mkt'].values, np.minimum(0.0, d['mkt'].values)])
    b, *_ = np.linalg.lstsq(X, d['r'].values, rcond=None)
    return float(-b[2])


def load_mkt_quarter():
    ff = pd.read_csv(FF5, encoding='utf-8-sig')
    dc = [c for c in ff.columns if 'date' in c.lower() or '日期' in c][0]
    mc = [c for c in ff.columns if 'mkt' in c.lower() or 'MKT' in c][0]
    ff[dc] = pd.to_datetime(ff[dc])
    # 该文件因子已为小数口径（日 MKT 标准差约 1.66%），切勿再除以 100
    return ff.set_index(dc)[mc].astype(float).resample('QE').sum()


# ---------------------------------------------------------------- 样本筛选
def build_pool():
    import akshare as ak
    frames = []
    for sym in ('混合型', '股票型'):
        try:
            d = ak.fund_open_fund_rank_em(symbol=sym)
            d['类型'] = sym
            frames.append(d)
        except Exception as e:
            log('  排行 %s 失败：%s' % (sym, str(e)[:60]))
    if not frames:
        return pd.DataFrame()
    r = pd.concat(frames, ignore_index=True)
    r['近3年'] = pd.to_numeric(r['近3年'], errors='coerce')
    r = r.dropna(subset=['近3年'])
    # 排除 C 类份额（同一基金重复计）与带括号的分级份额
    r = r[~r['基金简称'].str.contains('C|分级|美元', na=False)]
    r['基金代码'] = r['基金代码'].astype(str).str.zfill(6)
    r = r.drop_duplicates(subset=['基金代码'])
    return r.sort_values('近3年')


def fetch_nav(code):
    import akshare as ak
    df = ak.fund_open_fund_info_em(symbol=code, indicator='单位净值走势')
    df = df[['净值日期', '单位净值']].copy()
    df['净值日期'] = pd.to_datetime(df['净值日期'])
    df['单位净值'] = pd.to_numeric(df['单位净值'], errors='coerce')
    return df.dropna().sort_values('净值日期').reset_index(drop=True)


# ---------------------------------------------------------------- 主流程
def main():
    log('=' * 72)
    log('外部效度检验：行为画像能否区分绩优 / 绩差基金')
    log('=' * 72)

    mkt_q = load_mkt_quarter()
    pool = build_pool()
    if pool.empty:
        log('[FAIL] 基金池为空'); return 2
    log('基金池 %d 只（混合型+股票型，非 C 类、近3年收益有效）' % len(pool))

    cands = pd.concat([pool.tail(N_EACH), pool.head(N_EACH)])
    cands['组别'] = ['绩优'] * N_EACH + ['绩差'] * N_EACH
    log('候选池：绩优 %d 只（近3年 %.1f%% ~ %.1f%%）、绩差 %d 只（%.1f%% ~ %.1f%%）'
        % (N_EACH, pool['近3年'].tail(N_EACH).min(), pool['近3年'].tail(N_EACH).max(),
           N_EACH, pool['近3年'].head(N_EACH).min(), pool['近3年'].head(N_EACH).max()))

    rows = []
    for i, (_, r) in enumerate(cands.iterrows(), 1):
        code, name = r['基金代码'], r['基金简称']
        try:
            nav = fetch_nav(code)
            rq_all = to_quarter(nav)
            rq = rq_all[(rq_all.index >= WIN_START) & (rq_all.index <= WIN_END)]
        except Exception:
            continue
        if len(rq) < MIN_Q:
            continue
        sh, so, mp, ra = roll_sharpe(rq), roll_sortino(rq), roll_mppm(rq), roll_risk_asym(rq)
        tm = hm_timing(rq, mkt_q)
        rows.append({'组别': r['组别'], '代码': code, '基金简称': name,
                     '近3年收益': float(r['近3年']), '季度数': len(rq),
                     'sharpe8': sh.mean(), 'sortino8': so.mean(), 'mppm8': mp.mean(),
                     'risk_asym': ra.mean(), 'timing': tm,
                     '年化收益': float(rq.mean() * 4), '年化波动': float(rq.std(ddof=1) * 2)})
        if i % 10 == 0:
            log('  已处理 %d/%d，有效 %d' % (i, len(cands), len(rows)))

    if len(rows) < 8:
        log('[FAIL] 有效样本不足（%d 只）' % len(rows)); return 2

    df = pd.DataFrame(rows)
    p = os.path.join(OUT, '外部效度检验_2026-08-30.csv')
    df.to_csv(p, index=False, encoding='utf-8-sig')
    log('\n有效样本 %d 只（绩优 %d / 绩差 %d），已落盘 %s'
        % (len(df), (df['组别'] == '绩优').sum(), (df['组别'] == '绩差').sum(),
           os.path.basename(p)))

    def cmp(col, label, evidence):
        a = df.loc[df['组别'] == '绩优', col].astype(float).dropna()
        b = df.loc[df['组别'] == '绩差', col].astype(float).dropna()
        if len(a) < 3 or len(b) < 3:
            return
        se = np.sqrt(a.var(ddof=1) / len(a) + b.var(ddof=1) / len(b))
        t = (a.mean() - b.mean()) / se if se > 0 else np.nan
        tag = '证据维度' if evidence else '平凡对照'
        log('  %-10s %-8s 绩优 %9.4f  绩差 %9.4f  差 %9.4f  t=%6.2f  %s'
            % (label, tag, a.mean(), b.mean(), a.mean() - b.mean(), t,
               '***' if abs(t) > 2.58 else ('**' if abs(t) > 1.96 else
                                            ('*' if abs(t) > 1.64 else 'n.s.'))))

    log('')
    log('=' * 72)
    log('两组画像对比（统一窗口 %s ~ %s）' % (WIN_START, WIN_END))
    log('=' * 72)
    cmp('年化收益', '年化收益', False)
    cmp('年化波动', '年化波动', False)
    log('  ' + '-' * 66)
    cmp('sharpe8', 'L4b·Sharpe', False)
    cmp('sortino8', 'L4b·Sortino', False)
    cmp('mppm8', 'L4b·MPPM', False)
    log('  ' + '-' * 66)
    cmp('risk_asym', 'L2·风险不对称', True)
    cmp('timing', 'L4a·下行保护', True)

    log('')
    log('※ 判读：L4b 三项与"年化收益"属业绩类，绩优组更高是必然，只证明分组生效；')
    log('  真正的外部证据看 L2 / L4a 两行——若它们也能显著区分两组，')
    log('  说明不含业绩测度的行为维度确实携带了区分经理能力的信息。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
