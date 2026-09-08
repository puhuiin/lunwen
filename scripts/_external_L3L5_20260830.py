# -*- coding: utf-8 -*-
"""外部效度检验 · 补 L3 配置选择与 L5 交易纪律（2026-08-30）

在 `_external_validate_20260830.py` 得到的 33 只样本上，补两个此前算不到的维度：

  L3 配置选择
    ICI  行业集中度偏差  = Σ_j (w_j − w̄_j)²，w̄_j 为同一报告期全样本的行业平均权重
    ISDI 行业风格漂移   = Σ_j |w_j,t − w_j,t−1|
    数据源：ak.fund_portfolio_industry_allocation_em —— 直接取基金行业配置，
            无需自建"股票→行业"映射。

  L5 交易执行
    SDI  策略偏离指数   = 8 季滚动回归 r ~ SMB + HML（FF5），
                          取相邻期 beta 向量的曼哈顿距离 |Δb_SMB| + |Δb_HML|

⚠️ 口径差异（不可与论文数值直接比较，只看组间相对差异）：
   · 行业为东财大类（约 11 类），论文用申万 31 行业；
   · 论文 SDI 用 8 季滚动风格回归，本脚本以 FF5 的 SMB/HML 作风格因子，是简化版。
"""
import io
import os
import sys

import numpy as np
import pandas as pd

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, 'output')
FF5 = os.path.join(BASE, '指标计算流水线', 'data', 'FF因子', 'FF5日度因子.csv')
SRC = os.path.join(OUT, '外部效度检验_2026-08-30.csv')

YEARS = ['2019', '2020', '2021', '2022', '2023', '2024', '2025', '2026']


def log(m):
    print(m, flush=True)


def load_ff5_quarter():
    ff = pd.read_csv(FF5, encoding='utf-8-sig')
    dc = [c for c in ff.columns if 'date' in c.lower() or '日期' in c][0]
    ff[dc] = pd.to_datetime(ff[dc])
    cols = {k: [c for c in ff.columns if c.lower() == k][0] for k in ('mkt', 'smb', 'hml')}
    return ff.set_index(dc)[list(cols.values())].astype(float).resample('QE').sum()


def fetch_industry(code):
    import akshare as ak
    frames = []
    for y in YEARS:
        try:
            d = ak.fund_portfolio_industry_allocation_em(symbol=code, date=y)
            if d is not None and len(d):
                frames.append(d)
        except Exception:
            pass
    if not frames:
        return pd.DataFrame()
    d = pd.concat(frames, ignore_index=True)
    d['截止时间'] = pd.to_datetime(d['截止时间'])
    d['占净值比例'] = pd.to_numeric(d['占净值比例'], errors='coerce')
    return d.dropna(subset=['占净值比例'])


def compute_ici_isdi(all_ind):
    """all_ind: 长表 [代码, 截止时间, 行业类别, 占净值比例]"""
    # 市场平均行业权重：同一报告期、跨全部样本基金
    mkt = (all_ind.groupby(['截止时间', '行业类别'])['占净值比例']
           .mean().rename('市场权重').reset_index())
    m = all_ind.merge(mkt, on=['截止时间', '行业类别'], how='left')
    m['偏离'] = m['占净值比例'] - m['市场权重']

    # ICI：单期 Σ(偏离)²，基金层取时序均值
    ici = (m.groupby(['代码', '截止时间'])['偏离']
           .apply(lambda s: float((s ** 2).sum())).rename('ici').reset_index())
    ici = ici.groupby('代码')['ici'].mean()

    # ISDI：相邻报告期 Σ|w_t − w_{t-1}|
    m = m.sort_values(['代码', '行业类别', '截止时间'])
    m['权重变化'] = m.groupby(['代码', '行业类别'])['占净值比例'].diff().abs()
    isdi = (m.dropna(subset=['权重变化']).groupby(['代码', '截止时间'])['权重变化']
            .sum().rename('isdi').reset_index())
    isdi = isdi.groupby('代码')['isdi'].mean()
    return ici, isdi


def compute_sdi(rq, style_q, w=8):
    """8 季滚动回归 r ~ SMB + HML，返回相邻期 beta 曼哈顿距离的均值。"""
    d = pd.concat([rq.rename('r'), style_q], axis=1, sort=True).dropna()
    if len(d) < w + 1:
        return np.nan
    betas = []
    for i in range(w, len(d) + 1):
        win = d.iloc[i - w:i]
        X = np.column_stack([np.ones(w), win['SMB'].values, win['HML'].values])
        b, *_ = np.linalg.lstsq(X, win['r'].values, rcond=None)
        betas.append(b[1:])
    betas = np.array(betas)
    dist = np.abs(np.diff(betas, axis=0)).sum(axis=1)
    return float(dist.mean()) if len(dist) else np.nan


def fetch_nav(code):
    import akshare as ak
    df = ak.fund_open_fund_info_em(symbol=code, indicator='单位净值走势')
    df = df[['净值日期', '单位净值']].copy()
    df['净值日期'] = pd.to_datetime(df['净值日期'])
    df['单位净值'] = pd.to_numeric(df['单位净值'], errors='coerce')
    return df.dropna().sort_values('净值日期').reset_index(drop=True)


def main():
    base = pd.read_csv(SRC, encoding='utf-8-sig')
    base['代码'] = base['代码'].astype(str).str.zfill(6)
    codes = base['代码'].tolist()
    log('样本 %d 只，开始下载行业配置（%d 个年度 × %d 只）'
        % (len(codes), len(YEARS), len(codes)))

    all_ind = []
    for i, c in enumerate(codes, 1):
        d = fetch_industry(c)
        if len(d):
            d = d[['截止时间', '行业类别', '占净值比例']].copy()
            d['代码'] = c
            all_ind.append(d)
        if i % 10 == 0:
            log('  行业配置已下载 %d/%d（有效 %d）' % (i, len(codes), len(all_ind)))

    if len(all_ind) < 8:
        log('[FAIL] 行业配置有效样本不足（%d 只）' % len(all_ind))
        return 2
    all_ind = pd.concat(all_ind, ignore_index=True)
    log('行业配置：%d 条，覆盖 %d 只基金、%d 个行业、%d 个报告期'
        % (len(all_ind), all_ind['代码'].nunique(),
           all_ind['行业类别'].nunique(), all_ind['截止时间'].nunique()))

    ici, isdi = compute_ici_isdi(all_ind)

    ff_q = load_ff5_quarter()
    style_q = ff_q[['SMB', 'HML']]
    rows = []
    for i, c in enumerate(codes, 1):
        try:
            nav = fetch_nav(c)
            rq_all = nav.set_index('净值日期')['单位净值'].resample('QE').last().pct_change().dropna()
            rq = rq_all[(rq_all.index >= '2019-03-31') & (rq_all.index <= '2026-06-30')]
            sdi = compute_sdi(rq, style_q)
        except Exception:
            sdi = np.nan
        rows.append({'代码': c, 'ICI': ici.get(c, np.nan),
                     'ISDI': isdi.get(c, np.nan), 'SDI': sdi})
        if i % 10 == 0:
            log('  SDI 已算 %d/%d' % (i, len(codes)))

    df = base.merge(pd.DataFrame(rows), on='代码', how='left')
    p = os.path.join(OUT, '外部效度检验_含L3L5_2026-08-30.csv')
    df.to_csv(p, index=False, encoding='utf-8-sig')
    log('\n已落盘 %s' % os.path.basename(p))

    log('')
    log('=' * 74)
    log('补维后的两组对比（绩优 n=%d ／ 绩差 n=%d）'
        % ((df['组别'] == '绩优').sum(), (df['组别'] == '绩差').sum()))
    log('=' * 74)

    def cmp(col, label, evidence):
        a = df.loc[df['组别'] == '绩优', col].astype(float).dropna()
        b = df.loc[df['组别'] == '绩差', col].astype(float).dropna()
        if len(a) < 3 or len(b) < 3:
            log('  %-16s 样本不足（%d/%d）' % (label, len(a), len(b)))
            return
        se = np.sqrt(a.var(ddof=1) / len(a) + b.var(ddof=1) / len(b))
        t = (a.mean() - b.mean()) / se if se > 0 else np.nan
        star = '***' if abs(t) > 2.58 else ('**' if abs(t) > 1.96 else
                                           ('*' if abs(t) > 1.64 else 'n.s.'))
        log('  %-16s %-8s 绩优 %9.4f  绩差 %9.4f  差 %9.4f  t=%6.2f  %s'
            % (label, '证据维度' if evidence else '平凡对照',
               a.mean(), b.mean(), a.mean() - b.mean(), t, star))

    cmp('sharpe8', 'L4b·Sharpe', False)
    cmp('risk_asym', 'L2·风险不对称', True)
    cmp('timing', 'L4a·下行保护', True)
    log('  ' + '-' * 70)
    cmp('ICI', 'L3·行业集中度', True)
    cmp('ISDI', 'L3·行业风格漂移', True)
    cmp('SDI', 'L5·策略偏离', True)

    log('')
    log('※ 论文预期方向：ICI 正向（集中押注体现信息优势）、ISDI 负向（频繁轮动稀释优势）、')
    log('  SDI 负向（风格漂移损害业绩）。若符号与预期一致且显著，即构成外部支持。')
    log('※ 行业口径为东财大类（非申万 31 行业），数值不可与论文直接比较，只看组间差异。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
