# -*- coding: utf-8 -*-
"""外部 33 只样本 × L2 de（处置效应）论文口径复核

定义（与 `指标计算流水线/lib_metrics.py:611 calc_de` 完全一致）：
  de = PGR − PLR（Odean 1998 持仓快照法）
  PGR = 盈利股中已实现卖出比例 = gs / (gs + gh)
  PLR = 亏损股中已实现卖出比例 = ls / (ls + lh)
  其中 gs = 上期持仓中已卖出且持有期收益为正的股票数
        gh = 上期持仓中继续持有且持有期收益为正的股票数
        ls/lh = 同理但收益为负
  仅采用 6/12 月快照；逐只基金对所有相邻快照计算，基金层 de = 时序均值

数据：
  外部持仓：output/external_holdings_2026-08-30.csv（33 只，半年报/年报全量 + 前十大兜底）
  个股月收益：指标计算流水线/data/股价行情/个股月收益率_全量.csv
  论文预期：de < 0（越负越果断止损 → 业绩越好）

输出：output/外部效度检验_de论文口径_2026-08-30.csv
"""
import io
import os
import sys
import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOLDINGS = os.path.join(ROOT, 'output', 'external_holdings_2026-08-30.csv')
STOCK_RET = os.path.join(ROOT, '指标计算流水线', 'data', '股价行情', '个股月收益率_全量.csv')
SRC = os.path.join(ROOT, 'output', '外部效度检验_2026-08-30.csv')
OUT_CSV = os.path.join(ROOT, 'output', '外部效度检验_de论文口径_2026-08-30.csv')


def log(m):
    print(m, flush=True)


def main():
    # 1) 加载外部持仓（仅 6/12 月）
    h = pd.read_csv(HOLDINGS, encoding='utf-8-sig', dtype={'fund_code': str, 'stock_code': str})
    h['fund_code'] = h['fund_code'].astype(str).str.zfill(6)
    h['stock_code'] = h['stock_code'].astype(str).str.zfill(6)
    h['report_date'] = pd.to_datetime(h['report_date'], errors='coerce')
    h = h[h['report_date'].dt.month.isin([6, 12])].copy()
    h = h.dropna(subset=['report_date'])
    log(f'外部 6/12 月持仓: {len(h):,} 条 / {h["fund_code"].nunique()} 只 / {h["report_date"].nunique()} 期')

    # 2) 加载个股月收益，建字典
    sm = pd.read_csv(STOCK_RET, encoding='utf-8-sig', dtype={'stock_code': str})
    sm['stock_code'] = sm['stock_code'].astype(str).str.zfill(6)
    sm['date'] = pd.to_datetime(sm['date'], errors='coerce')
    sm = sm.dropna(subset=['date']).sort_values(['stock_code', 'date'])
    stock_dict = {}
    for code, g in sm.groupby('stock_code'):
        stock_dict[code] = (g['date'].values, g['monthly_return'].values)
    log(f'个股月收益字典: {len(stock_dict):,} 只股票')

    # 3) 区间累计收益查询
    def period_ret(code, t0, t1):
        if code not in stock_dict:
            return np.nan
        ds, rs = stock_dict[code]
        mask = (ds > np.datetime64(t0)) & (ds <= np.datetime64(t1))
        sub = rs[mask]
        return float(sub.sum()) if len(sub) else np.nan

    # 4) 逐只逐期计算 PGR/PLR/DE
    rows = []
    for fund, fdf in h.groupby('fund_code'):
        fdf = fdf.sort_values('report_date')
        dates = fdf['report_date'].unique()
        for i in range(1, len(dates)):
            t0, t1 = dates[i - 1], dates[i]
            prev = set(fdf[fdf['report_date'] == t0]['stock_code'])
            cur = set(fdf[fdf['report_date'] == t1]['stock_code'])
            sold, held = prev - cur, prev & cur
            gs = gh = ls = lh = 0
            for c in sold:
                r = period_ret(c, t0, t1)
                if pd.isna(r):
                    continue
                if r > 0:
                    gs += 1
                else:
                    ls += 1
            for c in held:
                r = period_ret(c, t0, t1)
                if pd.isna(r):
                    continue
                if r > 0:
                    gh += 1
                else:
                    lh += 1
            dg, dl = gs + gh, ls + lh
            pgr = gs / dg if dg else np.nan
            plr = ls / dl if dl else np.nan
            de = pgr - plr if (dg and dl) else np.nan
            rows.append((fund, pd.Timestamp(t1), de, pgr, plr, gs, gh, ls, lh))
    out = pd.DataFrame(rows, columns=['fund_code', 'report_date', 'de', 'pgr', 'plr',
                                      'gains_sold', 'gains_held', 'losses_sold', 'losses_held'])
    log(f'论文口径 DE 观测: {len(out):,} / {out["fund_code"].nunique()} 只')

    # 5) 基金层时序均值
    de_fund = out.groupby('fund_code')['de'].mean().rename('de_paper').reset_index()
    de_fund['de_paper_n'] = out.groupby('fund_code').size().values
    de_fund['de_pgr_mean'] = out.groupby('fund_code')['pgr'].mean().values
    de_fund['de_plr_mean'] = out.groupby('fund_code')['plr'].mean().values

    # 6) 与 33 只样本对齐
    base = pd.read_csv(SRC, encoding='utf-8-sig', dtype={'代码': str})
    base['代码'] = base['代码'].astype(str).str.zfill(6)
    out2 = base.merge(de_fund.rename(columns={'fund_code': '代码'}), on='代码', how='left')
    out2.to_csv(OUT_CSV, index=False, encoding='utf-8-sig')
    log(f'\n已落盘 {os.path.basename(OUT_CSV)}')

    # 7) 组间对比
    log('\n' + '=' * 76)
    log('组间对比（论文预期：de 越负越果断止损 → 业绩越好，故绩优组 de 应较低）')
    log('=' * 76)

    def compare(col, label):
        a = out2.loc[out2['组别'] == '绩优', col].astype(float).dropna()
        b = out2.loc[out2['组别'] == '绩差', col].astype(float).dropna()
        if len(a) < 3 or len(b) < 3:
            log(f'  {label}: 样本不足 ({len(a)}/{len(b)})')
            return
        se = np.sqrt(a.var(ddof=1) / len(a) + b.var(ddof=1) / len(b))
        t = (a.mean() - b.mean()) / se if se > 0 else np.nan
        star = '***' if abs(t) > 2.58 else ('**' if abs(t) > 1.96 else
                                            ('*' if abs(t) > 1.64 else 'n.s.'))
        log(f'  {label:<14}  绩优={a.mean():+.4f}  绩差={b.mean():+.4f}'
            f'  差={(a.mean()-b.mean()):+.4f}  t={t:+.2f} {star}')

    compare('de_paper', 'de 论文口径')

    # Spearman ρ
    from scipy.stats import spearmanr
    rho_p, p_p = spearmanr(out2['de_paper'].fillna(out2['de_paper'].median()), out2['近3年收益'])
    log(f'\n  Spearman ρ vs 近3年收益:')
    log(f'    de 论文口径: ρ={rho_p:+.3f}  p={p_p:.4f}  (论文预期负向)')

    # 控制年化波动后
    d = out2[['近3年收益', 'de_paper', '年化波动']].dropna()
    if len(d) > 5:
        from numpy import corrcoef
        def pcorr(x, y, z):
            rxy = corrcoef(x, y)[0, 1]; rxz = corrcoef(x, z)[0, 1]; ryz = corrcoef(y, z)[0, 1]
            return (rxy - rxz * ryz) / np.sqrt((1 - rxz ** 2) * (1 - ryz ** 2))
        log(f'\n  控制年化波动后:')
        log(f'    de 论文口径偏相关: {pcorr(d["近3年收益"], d["de_paper"], d["年化波动"]):+.3f}')

    # 样本量分布
    log(f'\n样本量分布:')
    log(out2['de_paper_n'].describe().to_string())

    return 0


if __name__ == '__main__':
    sys.exit(main())