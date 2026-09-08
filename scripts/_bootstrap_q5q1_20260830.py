# -*- coding: utf-8 -*-
"""路径B·补（2026-08-30）：基金层 Q5−Q1 整簇 Bootstrap（运气 vs 实力）

设计：
  用 `画像_全样本能力表_2026-08-26.csv`（362 只基金）作为基础
  每次有放回重抽 362 只基金 → 重新按综合能力分位 5 等分 → 计算 Q5−Q1 alpha 差
  重复 1,000 次 → 经验分布、95% CI、p 值（差≤0 的比例）

判读：
  - Q5−Q1 经验 95% CI 不含 0 + p<0.01 → "实力"主导（不可被截面运气解释）
  - 反之则"运气"解释不能排除
  - 与已有面板层 RA/DE/ICI/ARG/AS 截面 Bootstrap（_batch4_bootstrap_20260822.py）互补

输出：output/bootstrap_q5q1_2026-08-30.json
"""
import io
import os
import sys
import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'output', '画像_全样本能力表_2026-08-26.csv')
OUT = os.path.join(ROOT, 'output', 'bootstrap_q5q1_2026-08-30.json')
N_BOOT = 1000
RNG = np.random.default_rng(20260830)


def log(m):
    print(m, flush=True)


def q5_q1_diff(cap, alpha):
    """按 cap 5 等分，返回 Q5 - Q1 alpha 差。"""
    try:
        q = pd.qcut(cap, 5, labels=False, duplicates='drop')
    except Exception:
        return np.nan
    if q.nunique() < 5:
        return np.nan
    out = []
    for g in range(5):
        sub = alpha[q == g]
        out.append(sub.mean() if len(sub) else np.nan)
    if any(np.isnan(out)):
        return np.nan
    return out[4] - out[0]


def main():
    df = pd.read_csv(SRC, encoding='utf-8-sig', dtype={'fund_code': str})
    log(f'画像表: {df.shape[0]} 只基金 × {df.shape[1]} 列')

    # 观测 Q5−Q1
    obs = q5_q1_diff(df['综合能力'], df['ff5_alpha'])
    log(f'观测 Q5−Q1 (ff5_alpha): {obs:+.4f} ({obs * 100:.2f} pp)')

    # 同样对 quarter_return 做
    obs_qr = q5_q1_diff(df['综合能力'], df['quarter_return'])
    log(f'观测 Q5−Q1 (quarter_return): {obs_qr:+.4f}')

    # Bootstrap
    log(f'\nBootstrap 整簇重抽样 × {N_BOOT} 次 ...')
    n = len(df)
    boot_alpha = np.empty(N_BOOT)
    boot_qr = np.empty(N_BOOT)
    for i in range(N_BOOT):
        idx = RNG.integers(0, n, n)
        d = df.iloc[idx]
        boot_alpha[i] = q5_q1_diff(d['综合能力'], d['ff5_alpha'])
        boot_qr[i] = q5_q1_diff(d['综合能力'], d['quarter_return'])

    def stat(arr, label):
        valid = arr[~np.isnan(arr)]
        lo, hi = np.percentile(valid, [2.5, 97.5])
        mean = float(valid.mean())
        median = float(np.median(valid))
        p_le_zero = float((valid <= 0).mean())
        se = float(valid.std(ddof=1))
        log(f'  {label}:')
        log(f'    N 有效 = {len(valid)}/{len(arr)}')
        log(f'    均值 = {mean:+.4f}  ({mean * 100:.2f} pp)')
        log(f'    中位数 = {median:+.4f}')
        log(f'    标准误 = {se:+.4f}')
        log(f'    95% CI = [{lo:+.4f}, {hi:+.4f}]')
        log(f'    p(Q5−Q1 ≤ 0) = {p_le_zero:.4f}  {"<-- 实力" if p_le_zero < 0.01 else "<-- 可能含运气"}')
        return {'n_valid': int(len(valid)), 'mean': round(mean, 4), 'median': round(median, 4),
                'se': round(se, 4), 'ci_lo': round(float(lo), 4), 'ci_hi': round(float(hi), 4),
                'p_le_zero': round(p_le_zero, 4)}

    log('\n=== Bootstrap 结果 (ff5_alpha) ===')
    s_alpha = stat(boot_alpha, 'ff5_alpha')
    log('\n=== Bootstrap 结果 (quarter_return) ===')
    s_qr = stat(boot_qr, 'quarter_return')

    # 与已有 _batch4_bootstrap 对比
    log('\n=== 已有面板层 Bootstrap（_batch4_bootstrap_20260822.py）回顾 ===')
    log('  RA: 97.6% 同向显著；DE: 0% 显著；ICI/ARG/AS 均同向')
    log('  本脚本是基金层 Q5−Q1 差值 Bootstrap，互补非替代')

    # 落盘
    out = {
        '生成时间': '2026-08-30',
        '设计': '基金层整簇 Bootstrap（有放回重抽 362 只基金），重算 Q5−Q1 ff5_alpha 差',
        '样本基础': '画像_全样本能力表_2026-08-26.csv（362 只基金）',
        'Bootstrap 次数': N_BOOT,
        '观测值': {
            'Q5_minus_Q1_ff5_alpha': round(float(obs), 4),
            'Q5_minus_Q1_quarter_return': round(float(obs_qr), 4),
        },
        'ff5_alpha_bootstrap': s_alpha,
        'quarter_return_bootstrap': s_qr,
        '结论': (
            '实力主导：Q5−Q1 经验 95% CI 不含 0 且 p<0.01，'
            '样本内五等分区分度不能被截面运气解释。'
            if s_alpha['p_le_zero'] < 0.01 else
            '运气解释不能排除：Q5−Q1 经验分布与 0 重叠较多。'
        ),
    }
    with open(OUT, 'w', encoding='utf-8') as f:
        import json
        json.dump(out, f, ensure_ascii=False, indent=2)
    log(f'\n已落盘 {os.path.basename(OUT)}')

    return 0


if __name__ == '__main__':
    sys.exit(main())