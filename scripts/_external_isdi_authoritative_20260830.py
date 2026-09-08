# -*- coding: utf-8 -*-
"""外部 33 只样本 × ISDI 论文原始口径复核

定义（与 `指标计算流水线/scripts/_build_isdi_20260825.py` 完全一致）：
  1) 行业弹性分组：31 个申万一级行业按 Beta/弹性评分分高/中/低弹性三组
  2) 基金每期重仓股 → 股票行业映射.csv → 归入对应弹性组
  3) 每期构造组权重向量 w_t = (w_high, w_mid, w_low)，组内权重归一化
  4) ISDI_t = Σ_g |w_g,t - w_g,t-1|  (相邻报告期权重向量的曼哈顿距离)

数据：
  外部持仓：output/external_holdings_2026-08-30.csv（33 只 × 东财全持仓 + 前十大兜底）
  股票-行业映射：指标计算流水线/data/L2_持仓偏离层/股票行业映射.csv
  行业弹性评分：backups/行业弹性/申万一级行业弹性评分_20260809.xlsx

输出：
  output/外部效度检验_ISDI论文口径_2026-08-30.csv
  替换原 _external_L3L5_20260830.py 算出的 ISDI 列（论文原始口径）
"""
import io
import os
import sys
import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOLDINGS = os.path.join(ROOT, 'output', 'external_holdings_2026-08-30.csv')
MAPPING = os.path.join(ROOT, '指标计算流水线', 'data', 'L2_持仓偏离层', '股票行业映射.csv')
ELASTIC_XLSX = os.path.join(ROOT, 'backups', '行业弹性', '申万一级行业弹性评分_20260809.xlsx')
SRC = os.path.join(ROOT, 'output', '外部效度检验_2026-08-30.csv')
OUT_CSV = os.path.join(ROOT, 'output', '外部效度检验_ISDI论文口径_2026-08-30.csv')

GRP_ORDER = ['高弹性', '中弹性', '低弹性']


def log(m):
    print(m, flush=True)


def main():
    # 1) 弹性分组
    el = pd.read_excel(ELASTIC_XLSX)[['行业', '弹性等级']]
    grp_map = dict(zip(el['行业'], el['弹性等级']))
    n_h = sum(1 for v in grp_map.values() if v == '高弹性')
    n_m = sum(1 for v in grp_map.values() if v == '中弹性')
    n_l = sum(1 for v in grp_map.values() if v == '低弹性')
    log(f'行业分组: 高={n_h} 中={n_m} 低={n_l}')

    # 2) 持仓 + 股票→行业映射
    h = pd.read_csv(HOLDINGS, encoding='utf-8-sig', dtype={'fund_code': str})
    h['fund_code'] = h['fund_code'].astype(str).str.zfill(6)
    h['stock_code'] = h['stock_code'].astype(str).str.zfill(6)
    h['w'] = pd.to_numeric(h['hold_ratio'], errors='coerce').fillna(0) / 100.0
    h['report_date'] = pd.to_datetime(h['report_date'], errors='coerce')
    log(f'外部持仓: {len(h):,} 条 / {h["fund_code"].nunique()} 只 / {h["report_date"].nunique()} 期')

    m = pd.read_csv(MAPPING, encoding='utf-8-sig', dtype={'stock_code': str})
    m['stock_code'] = m['stock_code'].astype(str).str.zfill(6)
    stock2industry = dict(zip(m['stock_code'], m['sw31_industry']))
    h['industry'] = h['stock_code'].map(stock2industry)
    h['grp'] = h['industry'].map(grp_map)
    n0 = len(h)
    h = h.dropna(subset=['grp', 'report_date'])
    log(f'持仓→弹性组: {n0:,} → {len(h):,}（覆盖 {len(h)/n0:.1%}）')

    # 3) 每基金-报告期的组权重向量
    pv = h.pivot_table(index=['fund_code', 'report_date'], columns='grp',
                       values='w', aggfunc='sum').reindex(columns=GRP_ORDER).fillna(0.0)
    tot = pv.sum(axis=1)
    pv = pv.div(tot.replace(0, np.nan), axis=0).dropna()
    log(f'基金-报告期组权重向量: {len(pv):,} / {pv.index.get_level_values(0).nunique()} 只')

    # 4) 相邻期曼哈顿距离
    rows = []
    for fund, g in pv.groupby(level=0):
        g = g.sort_index(level=1)
        W = g.values
        dates = g.index.get_level_values(1)
        for i in range(1, len(W)):
            isdi = float(np.abs(W[i] - W[i - 1]).sum())
            rows.append((fund, dates[i], isdi))
    out = pd.DataFrame(rows, columns=['fund_code', 'report_date', 'ISDI_paper'])
    log(f'ISDI 观测: {len(out):,} / {out["fund_code"].nunique()} 只')

    # 5) 基金层时序均值（与论文 `_build_isdi` 一致）
    isdi_fund = out.groupby('fund_code')['ISDI_paper'].mean().rename('ISDI_paper').reset_index()
    isdi_fund['ISDI_paper_quarters'] = out.groupby('fund_code').size().values

    # 6) 与原始 33 只外部样本对齐
    base = pd.read_csv(SRC, encoding='utf-8-sig', dtype={'代码': str})
    base['代码'] = base['代码'].astype(str).str.zfill(6)
    out2 = base.merge(isdi_fund.rename(columns={'fund_code': '代码'}), on='代码', how='left')
    out2.to_csv(OUT_CSV, index=False, encoding='utf-8-sig')
    log(f'\n已落盘 {os.path.basename(OUT_CSV)}')

    # 7) 对照旧口径（用东财 11 个行业做的简化版）
    old = pd.read_csv(os.path.join(ROOT, 'output', '外部效度检验_含L3L5_2026-08-30.csv'),
                      encoding='utf-8-sig', dtype={'代码': str})
    old['代码'] = old['代码'].astype(str).str.zfill(6)
    cmp = out2.merge(old[['代码', 'ISDI']].rename(columns={'ISDI': 'ISDI_old'}), on='代码', how='left')

    log('\n' + '=' * 76)
    log('论文口径 vs 简化口径（东财大类）逐样本对比')
    log('=' * 76)
    for _, r in cmp.iterrows():
        log(f"  {r['代码']} {r['组别']:>2}  paper={r['ISDI_paper']:.4f}"
            f"  old={r['ISDI_old']:.4f}  Δ={r['ISDI_paper']-r['ISDI_old']:+.4f}"
            f"  ({int(r['ISDI_paper_quarters'])} 季)")

    log('\n' + '=' * 76)
    log('组间对比（论文预期：ISDI 高=频繁行业轮动=损害业绩，绩优组应较低）')
    log('=' * 76)

    def compare(col, label):
        a = cmp.loc[cmp['组别'] == '绩优', col].astype(float).dropna()
        b = cmp.loc[cmp['组别'] == '绩差', col].astype(float).dropna()
        if len(a) < 3 or len(b) < 3:
            log(f'  {label}: 样本不足 ({len(a)}/{len(b)})')
            return
        se = np.sqrt(a.var(ddof=1) / len(a) + b.var(ddof=1) / len(b))
        t = (a.mean() - b.mean()) / se if se > 0 else np.nan
        star = '***' if abs(t) > 2.58 else ('**' if abs(t) > 1.96 else
                                            ('*' if abs(t) > 1.64 else 'n.s.'))
        log(f'  {label:<14}  绩优={a.mean():.4f}  绩差={b.mean():.4f}'
            f'  差={(a.mean()-b.mean()):+.4f}  t={t:+.2f} {star}')

    compare('ISDI_paper', 'ISDI 论文口径')
    compare('ISDI_old', 'ISDI 简化口径')

    # Spearman ρ
    from scipy.stats import spearmanr
    rho_p, p_p = spearmanr(cmp['ISDI_paper'].fillna(cmp['ISDI_paper'].median()), cmp['近3年收益'])
    rho_o, p_o = spearmanr(cmp['ISDI_old'].fillna(cmp['ISDI_old'].median()), cmp['近3年收益'])
    log(f'\n  Spearman ρ vs 近3年收益:')
    log(f'    ISDI 论文口径: ρ={rho_p:+.3f}  p={p_p:.4f}  (论文预期负向)')
    log(f'    ISDI 简化口径: ρ={rho_o:+.3f}  p={p_o:.4f}')

    # 偏相关
    d = cmp[['近3年收益', 'ISDI_paper', '年化波动']].dropna()
    if len(d) > 5:
        from numpy import corrcoef
        def pcorr(x, y, z):
            rxy = corrcoef(x, y)[0, 1]; rxz = corrcoef(x, z)[0, 1]; ryz = corrcoef(y, z)[0, 1]
            return (rxy - rxz * ryz) / np.sqrt((1 - rxz ** 2) * (1 - ryz ** 2))
        log(f'\n  控制年化波动后:')
        log(f'    ISDI 论文口径偏相关: {pcorr(d["近3年收益"], d["ISDI_paper"], d["年化波动"]):+.3f}')

    return 0


if __name__ == '__main__':
    sys.exit(main())