# -*- coding: utf-8 -*-
"""
V2 指标扩充：认知层新增 + 风险转化层重构（每项均有文献出处）
文献锚点：
  oc_conf   Puetz & Ruenzi (2011) JBFA 38(5-6):684-712
  rc_mom    Grinblatt, Titman & Wermers (1995) AER 85(5):1088-1105
  mppm      Goetzmann, Ingersoll, Spiegel & Welch (2007) RFS 20(5):1503-1546
  sortino   Sortino & Price (1994) Journal of Investing 3(3):59-64
  rsstab    Huang, Sialm & Zhang (2011) RFS 24(8):2575-2616
输出 output/指标面板_v2_2026-08-26.csv
"""
import numpy as np
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PANEL = ROOT / '指标计算流水线' / 'output' / '主分析面板_重建_含TOwind.csv'
OUT = ROOT / 'output'

RHO = 3.0          # MPPM 相对风险厌恶系数（Goetzmann et al. 2007 建议 2~4）
DT = 0.25          # 季度频率
WIN = 8            # 滚动 8 季（与 return_volatility 同窗口）
MINP = 4


def main():
    df = pd.read_csv(PANEL, parse_dates=['report_date'])
    df = df.sort_values(['fund_code', 'report_date']).reset_index(drop=True)
    df['rf'] = df['rf'].fillna(0.0025)
    df['ex'] = df['quarter_return'] - df['rf']

    g = df.groupby('fund_code')

    # --- 风险转化 1：Sharpe（Sharpe 1966） ---
    m = g['ex'].transform(lambda s: s.rolling(WIN, min_periods=MINP).mean())
    sd = g['ex'].transform(lambda s: s.rolling(WIN, min_periods=MINP).std())
    df['sharpe8'] = np.where(sd > 1e-8, m / sd, np.nan)

    # --- 风险转化 2：Sortino（Sortino & Price 1994）下行风险 ---
    dn = df['ex'].where(df['ex'] < 0)
    dd = dn.groupby(df['fund_code']).transform(
        lambda s: s.rolling(WIN, min_periods=3).std())
    n_dn = dn.notna().groupby(df['fund_code']).transform(
        lambda s: s.rolling(WIN, min_periods=1).sum())
    df['sortino8'] = np.where((dd > 0.01) & (n_dn >= 3), m / dd, np.nan)

    # --- 风险转化 3：MPPM 抗操纵测度（Goetzmann et al. 2007） ---
    df['_g'] = ((1 + df['quarter_return']) / (1 + df['rf'])) ** (1 - RHO)
    gm = df.groupby('fund_code')['_g'].transform(
        lambda s: s.rolling(WIN, min_periods=MINP).mean())
    df['mppm8'] = np.log(gm.where(gm > 0)) / ((1 - RHO) * DT)

    # --- 风险转化 4：风险转移稳定性（Huang, Sialm & Zhang 2011），取负号使高=稳 ---
    sd4 = g['ex'].transform(lambda s: s.rolling(4, min_periods=3).std())
    df['sd4'] = sd4
    df['sd4_prev'] = df.groupby('fund_code')['sd4'].shift(1)
    df['rsstab'] = -(df['sd4'] - df['sd4_prev']).abs()

    # --- 事后度量统一滞后一期（避免与同期业绩机械同源） ---
    for c in ['sharpe8', 'sortino8', 'mppm8']:
        df[c + '_lag'] = df.groupby('fund_code')[c].shift(1)
    df['rsstab_lag'] = df.groupby('fund_code')['rsstab'].shift(1)

    # --- 认知层新增 1：过度自信（Puetz & Ruenzi 2011） ---
    # 用 TO_wind_clean（已剔除极端值版本），避免个别 5.9e6 量级异常值主导
    df['to_prev'] = df.groupby('fund_code')['TO_wind_clean'].shift(1)
    df['ret_prev'] = df.groupby('fund_code')['quarter_return'].shift(1)
    df['oc_conf'] = (df['TO_wind_clean'] - df['to_prev']) * (df['ret_prev'] > 0).astype(float)
    df.loc[df['to_prev'].isna() | df['ret_prev'].isna(), 'oc_conf'] = np.nan

    keep = ['fund_code', 'report_date', 'sharpe8', 'sortino8', 'mppm8', 'rsstab',
            'sharpe8_lag', 'sortino8_lag', 'mppm8_lag', 'rsstab_lag', 'oc_conf']
    out = df[keep]
    OUT.mkdir(exist_ok=True)
    out.to_csv(OUT / '指标面板_v2_2026-08-26.csv', index=False, encoding='utf-8-sig')

    print('rows', len(out), 'funds', out['fund_code'].nunique())
    print(out[['sharpe8_lag', 'sortino8_lag', 'mppm8_lag', 'rsstab_lag', 'oc_conf']]
          .describe().to_string())
    print('\ncorr (fund-level means):')
    fm = out.groupby('fund_code')[['sharpe8_lag', 'sortino8_lag', 'mppm8_lag',
                                   'rsstab_lag', 'oc_conf']].mean()
    print(fm.corr().round(3).to_string())


if __name__ == '__main__':
    main()
