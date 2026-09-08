# -*- coding: utf-8 -*-
"""外部 33 只样本 × ISDI / SDI 论文口径 × 窗口敏感性

基准窗口：2019Q1–2026Q2（外部样本训练窗口）。
检验窗口：2019Q1–2024Q4（去 2025–2026 后段）
         2020Q1–2026Q2（去 2019 起点）
         2022Q1–2026Q2（与论文 SDI 暖机期同步）

输出：output/外部效度检验_窗口敏感性_2026-08-30.csv + 控制台报告
"""
import io
import os
import sys
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOLDINGS = os.path.join(ROOT, 'output', 'external_holdings_2026-08-30.csv')
MAPPING = os.path.join(ROOT, '指标计算流水线', 'data', 'L2_持仓偏离层', '股票行业映射.csv')
ELASTIC_XLSX = os.path.join(ROOT, 'backups', '行业弹性', '申万一级行业弹性评分_20260809.xlsx')
SRC = os.path.join(ROOT, 'output', '外部效度检验_2026-08-30.csv')
STYLE_CSV = os.path.join(ROOT, '指标计算流水线', 'data', 'L2_持仓偏离层', '风格指数季度收益.csv')

WINDOWS = [
    ('2019Q1-2026Q2', pd.Period('2019Q1', 'Q'), pd.Period('2026Q2', 'Q')),  # 基准
    ('2019Q1-2024Q4', pd.Period('2019Q1', 'Q'), pd.Period('2024Q4', 'Q')),  # 去 2025-26
    ('2020Q1-2026Q2', pd.Period('2020Q1', 'Q'), pd.Period('2026Q2', 'Q')),  # 去 2019
    ('2022Q1-2026Q2', pd.Period('2022Q1', 'Q'), pd.Period('2026Q2', 'Q')),  # SDI 暖机后
]
GRP_ORDER = ['高弹性', '中弹性', '低弹性']
SDI_WINDOWS = 8
STYLE_CODES = ['399372', '399373', '399376', '399377']


def log(m):
    print(m, flush=True)


def compute_isdi_per_window(h, grp_map, start_p, end_p):
    """论文 ISDI 口径 → 基金层时序均值（限定窗口）。"""
    h = h[(h['report_date'].dt.to_period('Q') >= start_p) &
           (h['report_date'].dt.to_period('Q') <= end_p)].copy()
    pv = h.pivot_table(index=['fund_code', 'report_date'], columns='grp',
                       values='w', aggfunc='sum').reindex(columns=GRP_ORDER).fillna(0.0)
    tot = pv.sum(axis=1)
    pv = pv.div(tot.replace(0, np.nan), axis=0).dropna()
    rows = []
    for fund, g in pv.groupby(level=0):
        g = g.sort_index(level=1)
        W = g.values
        dates = g.index.get_level_values(1)
        for i in range(1, len(W)):
            rows.append((fund, dates[i], float(np.abs(W[i] - W[i - 1]).sum())))
    out = pd.DataFrame(rows, columns=['fund_code', 'report_date', 'ISDI'])
    return out.groupby('fund_code')['ISDI'].mean()


def compute_sdi_per_window(rq_all, style, start_p, end_p):
    """论文 SDI 口径 → 基金层时序均值（限定窗口）。"""
    style_w = style[(style.index >= start_p) & (style.index <= end_p)]
    out = {}
    for code, rq in rq_all.items():
        rq_w = rq[(rq.index >= start_p) & (rq.index <= end_p)]
        merged = pd.concat([rq_w.rename('r'), style_w], axis=1, sort=True).dropna()
        if len(merged) < SDI_WINDOWS + 1:
            out[code] = np.nan
            continue
        X_all = merged[STYLE_CODES].values
        y_all = merged['r'].values
        qs = merged.index
        rows = []
        for i in range(SDI_WINDOWS, len(merged)):
            X = np.column_stack([np.ones(SDI_WINDOWS), X_all[i - SDI_WINDOWS:i]])
            y = y_all[i - SDI_WINDOWS:i]
            try:
                beta, *_ = np.linalg.lstsq(X, y, rcond=None)
            except Exception:
                continue
            w = np.maximum(beta[1:], 0)
            if w.sum() > 0:
                w = w / w.sum()
                rows.append((qs[i], w))
        if len(rows) < 2:
            out[code] = np.nan
            continue
        s = [float(np.abs(rows[i][1] - rows[i - 1][1]).sum()) for i in range(1, len(rows))]
        out[code] = float(np.mean(s)) if s else np.nan
    return pd.Series(out)


def main():
    base = pd.read_csv(SRC, encoding='utf-8-sig', dtype={'代码': str})
    base['代码'] = base['代码'].astype(str).str.zfill(6)

    # 准备 ISDI 数据
    el = pd.read_excel(ELASTIC_XLSX)[['行业', '弹性等级']]
    grp_map = dict(zip(el['行业'], el['弹性等级']))
    h = pd.read_csv(HOLDINGS, encoding='utf-8-sig', dtype={'fund_code': str})
    h['fund_code'] = h['fund_code'].astype(str).str.zfill(6)
    h['stock_code'] = h['stock_code'].astype(str).str.zfill(6)
    h['w'] = pd.to_numeric(h['hold_ratio'], errors='coerce').fillna(0) / 100.0
    h['report_date'] = pd.to_datetime(h['report_date'], errors='coerce')
    m = pd.read_csv(MAPPING, encoding='utf-8-sig', dtype={'stock_code': str})
    m['stock_code'] = m['stock_code'].astype(str).str.zfill(6)
    s2i = dict(zip(m['stock_code'], m['sw31_industry']))
    h['industry'] = h['stock_code'].map(s2i)
    h['grp'] = h['industry'].map(grp_map)
    h = h.dropna(subset=['grp', 'report_date'])

    # 准备 SDI 数据（日净值一次性缓存）
    style = pd.read_csv(STYLE_CSV, encoding='utf-8-sig')
    style['q'] = [pd.Period(year=int(y), quarter=int(q), freq='Q')
                  for y, q in zip(style['year'], style['quarter'])]
    scols = [f'{c}_q_return' for c in STYLE_CODES]
    style = style.set_index('q')[scols].rename(columns={f'{c}_q_return': c for c in STYLE_CODES})

    log('一次性拉取 33 只基金日净值...')
    import akshare as ak
    rq_all = {}
    for code in base['代码'].tolist():
        try:
            df = ak.fund_open_fund_info_em(symbol=code, indicator='单位净值走势')
            if df is None or df.empty:
                rq_all[code] = pd.Series(dtype=float)
                continue
            df = df[['净值日期', '单位净值']].copy()
            df['净值日期'] = pd.to_datetime(df['净值日期'])
            df['单位净值'] = pd.to_numeric(df['单位净值'], errors='coerce')
            df = df.dropna().set_index('净值日期')['单位净值'].resample('QE').last().pct_change().dropna()
            df.index = df.index.to_period('Q')
            rq_all[code] = df
        except Exception:
            rq_all[code] = pd.Series(dtype=float)

    # 跑每个窗口
    results = []
    log('\n' + '=' * 86)
    log(f"{'窗口':<14} {'指标':<8} {'绩优n':<5} {'绩优均值':<10} {'绩差n':<5} "
        f"{'绩差均值':<10} {'差':<8} {'t':<8} {'ρ':<8} {'p':<8}")
    log('=' * 86)
    for wname, sp, ep in WINDOWS:
        isdi = compute_isdi_per_window(h, grp_map, sp, ep)
        sdi = compute_sdi_per_window(rq_all, style, sp, ep)

        for ind_name, ind in [('ISDI', isdi), ('SDI', sdi)]:
            merged = base.merge(ind.rename(ind_name).reset_index().rename(
                columns={ind.index.name or 'index': '代码'}), on='代码', how='left')
            a = merged.loc[merged['组别'] == '绩优', ind_name].astype(float).dropna()
            b = merged.loc[merged['组别'] == '绩差', ind_name].astype(float).dropna()
            if len(a) < 3 or len(b) < 3:
                log(f'{wname:<14} {ind_name:<8} 样本不足')
                continue
            se = np.sqrt(a.var(ddof=1) / len(a) + b.var(ddof=1) / len(b))
            t = (a.mean() - b.mean()) / se if se > 0 else np.nan
            star = '***' if abs(t) > 2.58 else ('**' if abs(t) > 1.96 else
                                                ('*' if abs(t) > 1.64 else 'n.s.'))
            rho, p = spearmanr(merged[ind_name].fillna(merged[ind_name].median()),
                                merged['近3年收益'])
            rho_s = '***' if p < 0.01 else ('**' if p < 0.05 else ('*' if p < 0.1 else 'n.s.'))
            log(f'{wname:<14} {ind_name:<8} {len(a):<5} {a.mean():<10.4f} {len(b):<5} '
                f'{b.mean():<10.4f} {a.mean()-b.mean():<+8.4f} {t:<+8.2f} {star:<4} '
                f'{rho:<+8.3f} {p:<8.4f}')
            results.append({
                'window': wname, 'metric': ind_name,
                'n_good': len(a), 'n_bad': len(b),
                'mean_good': a.mean(), 'mean_bad': b.mean(),
                'diff': a.mean() - b.mean(), 't': t, 't_star': star,
                'spearman_rho': rho, 'spearman_p': p, 'rho_star': rho_s,
            })

    df_out = pd.DataFrame(results)
    out_path = os.path.join(ROOT, 'output', '外部效度检验_窗口敏感性_2026-08-30.csv')
    df_out.to_csv(out_path, index=False, encoding='utf-8-sig')
    log(f'\n已落盘 {os.path.basename(out_path)}')

    log('\n' + '=' * 86)
    log('结论')
    log('=' * 86)
    isdi_rs = [r for r in results if r['metric'] == 'ISDI']
    sdi_rs = [r for r in results if r['metric'] == 'SDI']
    isdi_neg = all(r['diff'] < 0 for r in isdi_rs)
    isdi_sig = sum(1 for r in isdi_rs if abs(r['t']) > 1.64) / len(isdi_rs)
    sdi_neg = sum(1 for r in sdi_rs if r['diff'] < 0)
    sdi_sig = sum(1 for r in sdi_rs if abs(r['t']) > 1.64)
    log(f'  ISDI: {isdi_rs[0]["window"]} 基准 ρ={isdi_rs[0]["spearman_rho"]:+.3f}; '
        f'4 个窗口中方向均正确：{isdi_neg}；均值 t 显著：{isdi_sig * 100:.0f}%')
    log(f'  SDI:  {sdi_rs[0]["window"]} 基准 ρ={sdi_rs[0]["spearman_rho"]:+.3f}; '
        f'4 个窗口中方向正确：{sdi_neg}/4；t 显著：{sdi_sig}/4')


if __name__ == '__main__':
    sys.exit(main())