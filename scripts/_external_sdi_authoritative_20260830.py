# -*- coding: utf-8 -*-
"""外部 33 只样本 × SDI 论文原始口径复核

定义（与 `指标计算流水线/lib_metrics.py:481 calc_sdi` 完全一致）：
  SDI_t = Σ_k |β_{k,t} − β_{k,t−1}|,  k∈{大盘成长,大盘价值,小盘成长,小盘价值}
  β_t 由 8 季滚动 OLS 估计：基金季收益 ~ 1 + 4 风格指数季收益
  β 非负置零、归一化；窗口=8 季；首值 2022Q2（暖机 8 季后）
  基金层 SDI = 时序均值

数据：
  风格指数季度收益：指标计算流水线/data/L2_持仓偏离层/风格指数季度收益.csv
  33 只基金日净值：akshare 现拉（fund_open_fund_info_em, indicator='单位净值走势'）

输出：
  output/外部效度检验_SDI论文口径_2026-08-30.csv  替换原 _external_L3L5_20260830.py 算出的 SDI 列
"""
import io
import os
import sys
import time
import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PIPELINE_DATA = os.path.join(ROOT, '指标计算流水线', 'data')
STYLE_CSV = os.path.join(PIPELINE_DATA, 'L2_持仓偏离层', '风格指数季度收益.csv')
SRC = os.path.join(ROOT, 'output', '外部效度检验_2026-08-30.csv')
OUT_CSV = os.path.join(ROOT, 'output', '外部效度检验_SDI论文口径_2026-08-30.csv')

WINDOW = 8
STYLE_CODES = ['399372', '399373', '399376', '399377']  # 大盘成长/价值、小盘成长/价值
STYLE_NAMES = ['大盘成长', '大盘价值', '小盘成长', '小盘价值']

START_Q = pd.Period('2022Q2', freq='Q')   # 暖机 8 季首值
END_Q = pd.Period('2026Q2', freq='Q')     # 与原外部样本窗口一致


def log(m):
    print(m, flush=True)


def load_style():
    df = pd.read_csv(STYLE_CSV, encoding='utf-8-sig')
    scols = [f'{c}_q_return' for c in STYLE_CODES]
    df['q'] = [pd.Period(year=int(y), quarter=int(q), freq='Q')
               for y, q in zip(df['year'], df['quarter'])]
    df = df.set_index('q')[scols].rename(columns={f'{c}_q_return': c for c in STYLE_CODES})
    return df


def fetch_nav(code):
    import akshare as ak
    df = ak.fund_open_fund_info_em(symbol=code, indicator='单位净值走势')
    if df is None or df.empty:
        return pd.DataFrame()
    df = df[['净值日期', '单位净值']].copy()
    df['净值日期'] = pd.to_datetime(df['净值日期'])
    df['单位净值'] = pd.to_numeric(df['单位净值'], errors='coerce')
    return df.dropna().sort_values('净值日期').reset_index(drop=True)


def quarter_returns(nav):
    """日净值 → 季度复利收益。"""
    if nav.empty:
        return pd.Series(dtype=float)
    s = nav.set_index('净值日期')['单位净值'].resample('QE').last()
    r = s.pct_change()
    r.index = r.index.to_period('Q')
    r = r.dropna()
    return r


def compute_sdi_fund(rq, style):
    """8 季滚动 OLS 计算 SDI 时序。返回 Series：index=Period(季度)，values=SDI。"""
    merged = pd.concat([rq.rename('r'), style], axis=1, sort=True).dropna()
    if len(merged) < WINDOW + 1:
        return pd.Series(dtype=float)
    X_all = merged[STYLE_CODES].values
    y_all = merged['r'].values
    qs = merged.index
    rows = []
    for i in range(WINDOW, len(merged)):
        X = np.column_stack([np.ones(WINDOW), X_all[i - WINDOW:i]])
        y = y_all[i - WINDOW:i]
        try:
            beta, *_ = np.linalg.lstsq(X, y, rcond=None)
        except Exception:
            continue
        w = np.maximum(beta[1:], 0)
        if w.sum() > 0:
            w = w / w.sum()
            rows.append((qs[i], w))
    if len(rows) < 2:
        return pd.Series(dtype=float)
    out = []
    for i in range(1, len(rows)):
        sdi = np.abs(rows[i][1] - rows[i - 1][1]).sum()
        out.append((rows[i][0], sdi))
    s = pd.Series([x[1] for x in out], index=pd.PeriodIndex([x[0] for x in out], freq='Q'))
    s = s.loc[(s.index >= START_Q) & (s.index <= END_Q)]
    return s


def main():
    base = pd.read_csv(SRC, encoding='utf-8-sig', dtype={'代码': str})
    base['代码'] = base['代码'].astype(str).str.zfill(6)
    codes = base['代码'].tolist()
    style = load_style()
    log(f'风格指数 {len(style)} 季 × {STYLE_CODES}；窗口={WINDOW}；区间 {START_Q}..{END_Q}')

    rows = []
    for i, code in enumerate(codes, 1):
        try:
            nav = fetch_nav(code)
            rq = quarter_returns(nav)
            sd = compute_sdi_fund(rq, style)
            sdi_mean = float(sd.mean()) if len(sd) else np.nan
            sdi_zero = bool(sdi_mean == 0 or (not np.isnan(sdi_mean) and sdi_mean < 1e-9))
            n_q = len(sd)
        except Exception as e:
            sdi_mean, sdi_zero, n_q = np.nan, False, 0
        rows.append({
            '代码': code, 'SDI_paper': sdi_mean,
            'SDI_paper_quarters': n_q, 'SDI_paper_iszero': sdi_zero,
        })
        if i % 10 == 0:
            log(f'  [{i}/{len(codes)}] {code}: SDI={sdi_mean:.4f} ({n_q} 季)')

    sdi_df = pd.DataFrame(rows)
    out = base.merge(sdi_df, on='代码', how='left')
    out.to_csv(OUT_CSV, index=False, encoding='utf-8-sig')
    log(f'\n已落盘 {os.path.basename(OUT_CSV)}')

    # 对照旧口径
    old = pd.read_csv(os.path.join(ROOT, 'output', '外部效度检验_含L3L5_2026-08-30.csv'),
                      encoding='utf-8-sig', dtype={'代码': str})
    old['代码'] = old['代码'].astype(str).str.zfill(6)
    cmp = out.merge(old[['代码', 'SDI']].rename(columns={'SDI': 'SDI_old'}), on='代码', how='left')

    log('\n' + '=' * 76)
    log('论文口径 vs 简化口径（仅 FF5 SMB+HML）逐样本对比')
    log('=' * 76)
    for _, r in cmp.iterrows():
        log(f"  {r['代码']} {r['组别']:>2}  paper={r['SDI_paper']:.4f}  old={r['SDI_old']:.4f}"
            f"  Δ={r['SDI_paper']-r['SDI_old']:+.4f}")

    log('\n' + '=' * 76)
    log('组间对比（论文预期：SDI 高=风格漂移=损害业绩，故绩优组 SDI 应较低）')
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

    compare('SDI_paper', 'SDI 论文口径')
    compare('SDI_old', 'SDI 简化口径')

    # Spearman ρ vs 近3年收益
    from scipy.stats import spearmanr
    rho_p, p_p = spearmanr(cmp['SDI_paper'].fillna(cmp['SDI_paper'].median()), cmp['近3年收益'])
    rho_o, p_o = spearmanr(cmp['SDI_old'].fillna(cmp['SDI_old'].median()), cmp['近3年收益'])
    log(f'\n  Spearman ρ vs 近3年收益:')
    log(f'    SDI 论文口径: ρ={rho_p:+.3f}  p={p_p:.4f}  (论文预期负向)')
    log(f'    SDI 简化口径: ρ={rho_o:+.3f}  p={p_o:.4f}')

    # 控制波动后偏相关
    if {'年化波动', 'SDI_paper'}.issubset(cmp.columns):
        d = cmp[['近3年收益', 'SDI_paper', '年化波动']].dropna()
        from numpy import array
        if len(d) > 5:
            def pcorr(x, y, z):
                from numpy import corrcoef
                rxy = corrcoef(x, y)[0, 1]
                rxz = corrcoef(x, z)[0, 1]
                ryz = corrcoef(y, z)[0, 1]
                return (rxy - rxz * ryz) / np.sqrt((1 - rxz ** 2) * (1 - ryz ** 2))
            log(f'\n  控制年化波动后:')
            log(f'    SDI 论文口径偏相关: {pcorr(d["近3年收益"], d["SDI_paper"], d["年化波动"]):+.3f}')

    log('\n零值基金数（论文口径 SDI=0 的基金占比）：')
    n_zero = cmp['SDI_paper_iszero'].sum()
    log(f'  {n_zero}/{len(cmp)} = {n_zero/len(cmp):.1%}（论文样本内 45.4%）')

    return 0


if __name__ == '__main__':
    sys.exit(main())