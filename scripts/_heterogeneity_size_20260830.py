# -*- coding: utf-8 -*-
"""批次③·D 候选（2026-08-30）：基金类型异质性 — 按规模/牛熊分组

设计：
  1) 规模分组：用 `画像_全样本能力表` 的 362 只基金匹配主面板的 `avg_aum`（基金层时序均值），
     3 等分（小/中/大）后分别做综合能力 5 等分 Q5−Q1 计算
  2) 牛熊分组：用沪深 300 季度收益正/负划分牛/熊期，按基金所在期做五等分 Q5−Q1
  3) 检验：各子样本内的 Q5−Q1 是否稳健
  4) 输出：output/heterogeneity_by_size_and_market_2026-08-30.json

判读：
  - 三组规模下 Q5−Q1 方向均正、t 均显著 → 综合能力区分度对不同规模基金稳健
  - 牛/熊子样本差异较大 → 暗示画像存在市场状态异质性
"""
import io
import os
import sys
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PORTRAIT = os.path.join(ROOT, 'output', '画像_全样本能力表_2026-08-26.csv')
PANEL = os.path.join(ROOT, '指标计算流水线', 'output', '主分析面板_重建_含TOwind.csv')
OUT = os.path.join(ROOT, 'output', 'heterogeneity_by_size_and_market_2026-08-30.json')


def log(m):
    print(m, flush=True)


def q5_q1_diff(cap, alpha):
    try:
        q = pd.qcut(cap, 5, labels=False, duplicates='drop')
    except Exception:
        return np.nan, np.nan
    if q.nunique() < 5:
        return np.nan, np.nan
    q5 = alpha[q == 4].mean()
    q1 = alpha[q == 0].mean()
    return q5 - q1, q


def grp_t_test(a, b):
    if len(a) < 3 or len(b) < 3:
        return np.nan
    se = np.sqrt(a.var(ddof=1) / len(a) + b.var(ddof=1) / len(b))
    if se == 0:
        return np.nan
    return (a.mean() - b.mean()) / se


def main():
    portrait = pd.read_csv(PORTRAIT, encoding='utf-8-sig', dtype={'fund_code': str})
    log(f'画像表: {len(portrait)} 只基金')

    # 1) 聚合基金层 avg_aum
    panel = pd.read_csv(PANEL, dtype={'fund_code': str}, usecols=['fund_code', 'year', 'quarter', 'avg_aum'])
    avg_aum = panel.groupby('fund_code')['avg_aum'].mean().reset_index()
    log(f'规模数据: {len(avg_aum)} 只基金有 avg_aum，匹配 {len(portrait[portrait.fund_code.isin(avg_aum.fund_code)])}')

    df = portrait.merge(avg_aum, on='fund_code', how='left')
    df = df.dropna(subset=['avg_aum'])
    log(f'合并后: {len(df)} 只基金有规模数据')

    # === (A) 规模三分位 ===
    log('\n=== A. 规模 3 等分 ===')
    df['size_q'] = pd.qcut(df['avg_aum'], 3, labels=['小', '中', '大'])
    size_results = {}
    for label, sub in df.groupby('size_q', observed=True):
        diff, _ = q5_q1_diff(sub['综合能力'], sub['ff5_alpha'])
        a = sub.loc[sub['综合能力'] >= sub['综合能力'].quantile(0.8), 'ff5_alpha']
        b = sub.loc[sub['综合能力'] <= sub['综合能力'].quantile(0.2), 'ff5_alpha']
        t = grp_t_test(a, b)
        rho, p = spearmanr(sub['综合能力'], sub['ff5_alpha'])
        log(f'  {label} 基金（n={len(sub)}）：Q5−Q1={diff:+.4f}  t={t:+.2f}  ρ={rho:+.3f} (p={p:.4f})')
        size_results[str(label)] = {
            'n': int(len(sub)),
            'avg_aum_mean': round(float(sub['avg_aum'].mean()), 0),
            'Q5_minus_Q1': round(float(diff), 4),
            't_top_vs_bottom': round(float(t), 2) if not np.isnan(t) else None,
            'spearman_rho': round(float(rho), 3),
            'spearman_p': round(float(p), 4),
        }

    # === (B) 牛熊期分组 ===
    # 取沪深 300 季度收益作为市场基准（用 FF5 面板的 MKT_excess；找包含 0 的近似的 ff5_MKT_excess 不含风险溢价）
    # 直接用 沪深 300 季收益：可以从 cs_index 拿；或用 ff5_MKT_excess + rf 重建
    # 简单做法：用 ff5_MKT_excess + ff5_RF ≈ 沪深 300 季收益
    panel2 = pd.read_csv(PANEL, dtype={'fund_code': str},
                          usecols=['fund_code', 'year', 'quarter', 'ff5_MKT_excess', 'ff5_RF'])
    panel2['mkt_total'] = panel2['ff5_MKT_excess'] + panel2['ff5_RF']
    mkt_q = panel2.groupby(['year', 'quarter'])['mkt_total'].first().reset_index()
    mkt_q['state'] = np.where(mkt_q['mkt_total'] > 0, '牛', '熊')
    log(f'\n市场状态（沪深 300 季收益）: 牛={(mkt_q["state"]=="牛").sum()} 熊={(mkt_q["state"]=="熊").sum()}')

    # 合并基金到市场状态
    df2 = portrait.merge(panel2[['fund_code', 'year', 'quarter', 'mkt_total']],
                         on='fund_code', how='left')
    df2 = df2.merge(mkt_q[['year', 'quarter', 'state']], on=['year', 'quarter'], how='left')
    log(f'合并后基金-季度观测: {len(df2)}')

    # 牛/熊期内 Q5−Q1（基金层时序聚合）
    market_results = {}
    for state in ['牛', '熊']:
        sub = df2[df2['state'] == state]
        if len(sub) < 30:
            market_results[state] = {'n_obs': int(len(sub)), 'note': '样本不足'}
            continue
        # 基金层聚合：先求每只基金在某状态下的 mean_ff5_alpha
        fund_agg = sub.groupby('fund_code').agg(
            综合能力=('综合能力', 'first'),
            alpha_state=('ff5_alpha', 'mean')).reset_index()
        diff, _ = q5_q1_diff(fund_agg['综合能力'], fund_agg['alpha_state'])
        a = fund_agg.loc[fund_agg['综合能力'] >= fund_agg['综合能力'].quantile(0.8), 'alpha_state']
        b = fund_agg.loc[fund_agg['综合能力'] <= fund_agg['综合能力'].quantile(0.2), 'alpha_state']
        t = grp_t_test(a, b)
        rho, p = spearmanr(fund_agg['综合能力'], fund_agg['alpha_state'])
        log(f'  {state}市 基金数={len(fund_agg)} 观测={len(sub)}：Q5−Q1={diff:+.4f}  t={t:+.2f}  ρ={rho:+.3f}')
        market_results[state] = {
            'n_fund': int(len(fund_agg)),
            'n_obs': int(len(sub)),
            'Q5_minus_Q1': round(float(diff), 4),
            't_top_vs_bottom': round(float(t), 2) if not np.isnan(t) else None,
            'spearman_rho': round(float(rho), 3),
            'spearman_p': round(float(p), 4),
        }

    # 落盘
    import json
    out = {
        '生成时间': '2026-08-30',
        '设计': '按基金规模（小/中/大）+ 市场状态（牛/熊）分组，比较各组综合能力 5 等分 Q5−Q1',
        '规模_3分位': size_results,
        '市场状态_牛熊': market_results,
        '结论': (
            '画像在所有规模子样本中均稳健（Q5−Q1 方向一致）'
            if all(r.get('Q5_minus_Q1', 0) > 0 for r in size_results.values()) and
            all(r.get('Q5_minus_Q1', 0) > 0 for r in market_results.values() if isinstance(r, dict) and r.get('Q5_minus_Q1') is not None)
            else '部分子样本方向不一致或样本不足'
        ),
    }
    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    log(f'\n已落盘 {os.path.basename(OUT)}')

    return 0


if __name__ == '__main__':
    sys.exit(main())