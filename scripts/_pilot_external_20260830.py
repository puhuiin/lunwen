# -*- coding: utf-8 -*-
"""外部真实案例检验 · 试点（2026-08-30）

目的：验证能否仅用公开数据（AKShare）在论文样本之外的基金上复算核心行为指标，
从而用真实世界的基金经理为论文提供外部效度证据。

试点对象（每组 1 只，先跑通流水线）：
  A 长期优胜   张坤   易方达蓝筹精选      005827
  B 陨落/高波动 葛兰   中欧医疗健康混合A   003095
  C 长期平庸   由 fund_open_fund_rank_em 自动筛选（成立满 8 年、规模 ≥10 亿、近 5 年收益靠后）

⚠️ 证据口径（务必遵守）：
  本脚本把 L2/L3/L5 视为"候选证据维度"，L4b 视为"平凡对照"。
  L4b = Sharpe/Sortino/MPPM 本身就是业绩指标，优秀组必然更高，
  该差异只作操纵性检查，**不构成外部证据**。真正的证据要看非业绩维度能否区分 A 与 C。

计算口径参照论文表 1；季频指标统一用滚动 8 季，timing 需 ≥12 季。
"""
import io
import os
import sys

import numpy as np
import pandas as pd

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, 'output')
FF5 = os.path.join(BASE, '指标计算流水线', 'data', 'FF因子', 'FF5日度因子.csv')

PILOT = [
    ('A 长期优胜', '张坤', '易方达蓝筹精选', '005827'),
    ('B 陨落高波动', '葛兰', '中欧医疗健康混合A', '003095'),
]

# 统一比较窗口：外部基金成立时间不一（张坤 2018 年、葛兰 2016 年，而 C 组可能是老基金），
# 必须截到同一区间，否则比的是"不同历史时期"而非"不同经理"。
WIN_START, WIN_END = '2019-03-31', '2026-06-30'


def log(msg):
    print(msg, flush=True)


# ---------------------------------------------------------------- 数据获取
def fetch_nav(code):
    import akshare as ak
    df = ak.fund_open_fund_info_em(symbol=code, indicator='单位净值走势')
    df = df[['净值日期', '单位净值']].copy()
    df['净值日期'] = pd.to_datetime(df['净值日期'])
    df['单位净值'] = pd.to_numeric(df['单位净值'], errors='coerce')
    return df.dropna().sort_values('净值日期').reset_index(drop=True)


def pick_laggard():
    """自动选一只长期平庸的主动权益基金作为 C 组。"""
    import akshare as ak
    try:
        rank = ak.fund_open_fund_rank_em(symbol='混合型')
    except Exception as e:
        log('[C 组] 排行接口失败：%s' % str(e)[:80])
        return None
    cols = {c: c for c in rank.columns}
    need = ['基金代码', '基金简称', '近5年', '成立年']
    if not all(n in cols for n in need):
        log('[C 组] 排行表缺少所需列，实际列：%s' % list(rank.columns)[:10])
        return None
    r = rank[['基金代码', '基金简称', '近5年', '成立年']].copy()
    r['近5年'] = pd.to_numeric(r['近5年'], errors='coerce')
    r['成立年'] = pd.to_numeric(r['成立年'], errors='coerce')
    r = r.dropna()
    r = r[r['成立年'] <= 2017]
    if r.empty:
        return None
    r = r.sort_values('近5年').head(30)
    row = r.iloc[len(r) // 2]
    return str(row['基金代码']).zfill(6), str(row['基金简称']), float(row['近5年'])


# ---------------------------------------------------------------- 指标
def to_quarter(nav):
    """日频净值 → 季度收益（与论文一致：report_date 为季末次日，此处按季末聚合）。"""
    s = nav.set_index('净值日期')['单位净值']
    q = s.resample('QE').last()
    return q.pct_change().dropna()


def roll_sharpe(r, w=8):
    return r.rolling(w).mean() / r.rolling(w).std(ddof=1)


def roll_sortino(r, w=8):
    mu = r.rolling(w).mean()
    dn = r.rolling(w).apply(lambda x: np.std(x[x < 0], ddof=1) if (x < 0).any() else np.nan,
                            raw=True)
    return mu / dn


def mppm(r, rho=3.0):
    """Goetzmann et al. (2007) 抗操纵绩效测度，季度口径后年化。"""
    r = np.asarray(r, dtype=float)
    r = r[~np.isnan(r)]
    if len(r) == 0:
        return np.nan
    base = np.power(np.maximum(1.0 + r, 1e-8), 1.0 - rho)
    val = np.log(np.mean(base)) / (1.0 - rho)
    return float(val * 4)


def roll_mppm(r, w=8):
    return r.rolling(w).apply(lambda x: mppm(x), raw=True)


def roll_risk_asym(r, w=8):
    """risk_asym = σ(盈利期收益) − σ(亏损期收益)，滚动 8 季。"""
    def f(x):
        up, dn = x[x > 0], x[x < 0]
        if len(up) < 2 or len(dn) < 2:
            return np.nan
        return np.std(up, ddof=1) - np.std(dn, ddof=1)
    return r.rolling(w).apply(f, raw=True)


def hm_timing(r_q, mkt_q):
    """HM 分段回归：r = a + b·MKT + γ·min(0, MKT)；timing = −γ。"""
    d = pd.concat([r_q.rename('r'), mkt_q.rename('mkt')], axis=1, sort=True).dropna()
    if len(d) < 12:
        return np.nan, len(d)
    X = np.column_stack([np.ones(len(d)), d['mkt'].values,
                         np.minimum(0.0, d['mkt'].values)])
    beta, *_ = np.linalg.lstsq(X, d['r'].values, rcond=None)
    return float(-beta[2]), len(d)


def load_mkt_quarter():
    ff = pd.read_csv(FF5, encoding='utf-8-sig')
    dc = [c for c in ff.columns if '日期' in c or 'date' in c.lower()][0]
    mc = [c for c in ff.columns if 'mkt' in c.lower() or 'MKT' in c][0]
    ff[dc] = pd.to_datetime(ff[dc])
    # 量纲：本文件因子已是小数口径（日度 MKT 标准差约 0.0166，即 1.66%），不可再除以 100。
    # 曾因此把 MKT 缩小 100 倍，使 HM 的 γ 被放大 100 倍（timing 出现 65 这类荒谬值）。
    s = ff.set_index(dc)[mc].astype(float)
    return s.resample('QE').sum()


# ---------------------------------------------------------------- 主流程
def main():
    log('=' * 70)
    log('外部真实案例检验 · 试点验证')
    log('=' * 70)

    mkt_q = load_mkt_quarter()
    log('FF5 市场因子：%d 个季度（%s ~ %s）'
        % (len(mkt_q), mkt_q.index[0].date(), mkt_q.index[-1].date()))

    c = pick_laggard()
    if c:
        PILOT.append(('C 长期平庸', '（自动筛选）', c[1], c[0]))
        log('C 组自动筛选：%s %s（近5年 %.2f%%）' % (c[0], c[1], c[2]))
    else:
        log('C 组自动筛选失败，本次仅跑 A/B')

    rows = []
    for grp, mgr, name, code in PILOT:
        log('')
        log('---- %s ｜ %s ｜ %s（%s）' % (grp, mgr, name, code))
        try:
            nav = fetch_nav(code)
        except Exception as e:
            log('    净值下载失败：%s' % str(e)[:100])
            continue
        if len(nav) < 40:
            log('    净值样本不足（%d 条），跳过' % len(nav))
            continue
        rq_all = to_quarter(nav)
        rq = rq_all[(rq_all.index >= WIN_START) & (rq_all.index <= WIN_END)]
        log('    净值 %d 条 → 季度收益 %d 个（%s ~ %s）→ 统一窗口内 %d 个'
            % (len(nav), len(rq_all), rq_all.index[0].date(),
               rq_all.index[-1].date(), len(rq)))
        if len(rq) < 16:
            log('    统一窗口内季度数不足 16，跳过')
            continue

        sh = roll_sharpe(rq)
        so = roll_sortino(rq)
        mp = roll_mppm(rq)
        ra = roll_risk_asym(rq)
        tm, nreg = hm_timing(rq, mkt_q)

        rows.append({
            '组别': grp, '经理': mgr, '基金简称': name, '代码': code,
            '季度数': len(rq),
            'sharpe8': sh.mean(), 'sortino8': so.mean(), 'mppm8': mp.mean(),
            'risk_asym': ra.mean(),
            'timing': tm, 'timing回归季度': nreg,
            '年化收益': float(rq.mean() * 4), '年化波动': float(rq.std(ddof=1) * 2),
        })
        log('    sharpe8=%s sortino8=%s mppm8=%s risk_asym=%s timing=%s'
            % (round(sh.mean(), 3) if sh.notna().any() else '—',
               round(so.mean(), 3) if so.notna().any() else '—',
               round(mp.mean(), 3) if mp.notna().any() else '—',
               round(ra.mean(), 3) if ra.notna().any() else '—',
               round(tm, 3) if tm == tm else '—'))

    if not rows:
        log('\n[FAIL] 没有任何基金跑通，试点失败')
        return 2

    df = pd.DataFrame(rows)
    p = os.path.join(OUT, '外部案例试点_2026-08-30.csv')
    df.to_csv(p, index=False, encoding='utf-8-sig')

    log('')
    log('=' * 70)
    log('试点汇总（已落盘 %s）' % os.path.basename(p))
    log('=' * 70)
    show = df[['组别', '经理', '基金简称', '季度数', 'sharpe8', 'sortino8',
               'mppm8', 'risk_asym', 'timing', '年化收益']].copy()
    for c_ in ['sharpe8', 'sortino8', 'mppm8', 'risk_asym', 'timing']:
        show[c_] = show[c_].astype(float).round(3)
    show['年化收益'] = (show['年化收益'].astype(float) * 100).round(2)
    with pd.option_context('display.width', 200, 'display.max_columns', 20):
        log(show.to_string(index=False))

    log('')
    log('※ 证据口径提醒：sharpe8/sortino8/mppm8 属 L4b（业绩类），A 组更高是必然，不算证据；')
    log('  真正的外部证据要看 risk_asym(L2)、timing(L4a) 等非业绩维度能否区分 A 与 C。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
