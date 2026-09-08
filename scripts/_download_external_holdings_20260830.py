# -*- coding: utf-8 -*-
"""外部 33 只样本 × 东财全持仓下载（半年报/年报）

目的：为 ISDI 复核提供原始口径所需的"个股持仓 → 申万 31 行业"链路。
策略：每年 6/12 月用东财 FundArchivesDatas.aspx?toinline=500 全持仓接口；
      前十大用 akshare.fund_portfolio_hold_em 兜底。
输出：output/external_holdings_2026-08-30.csv
      列：fund_code, report_date, stock_code, stock_name, hold_ratio, source
"""
import io
import json
import os
import sys
import time
import re
import requests
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, 'output')
SRC = os.path.join(OUT_DIR, '外部效度检验_2026-08-30.csv')

YEARS = [2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026]
MONTHS_FULL = ['6', '12']  # 半年报/年报出全持仓

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
    'Referer': 'https://fund.eastmoney.com/',
}


def quarter_end(y, m):
    """东财月份 (6/12) → 季末日期。Q2 末=06-30, Q4 末=12-31。"""
    return f'{y}-{m}-30' if m == '6' else f'{y}-{m}-31'


def fetch_full(code, year, month):
    """东财 FundArchivesDatas.aspx 半年报/年报全持仓（topline=500）。"""
    url = (
        f'http://fundf10.eastmoney.com/FundArchivesDatas.aspx'
        f'?type=jjcc&code={code}&topline=500&year={year}&month={month}'
    )
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        text = r.text
        if 'content' not in text or '{' not in text:
            return []
        start = text.index('{')
        end = text.rindex('}') + 1
        data = json.loads(text[start:end])
        rows = []
        for arr in data.get('content', {}).values():
            if not arr:
                continue
            for r0 in arr:
                # 字段名在东财返回中可能中文也可能 code，先归一
                code_field = r0.get('GPDM') or r0.get('gpdm') or r0.get('CODE') or ''
                name_field = r0.get('GPJC') or r0.get('gpjc') or r0.get('NAME') or ''
                ratio = (r0.get('JZBL') or r0.get('jzbl') or r0.get('PCT') or 0)
                try:
                    ratio = float(ratio)
                except (TypeError, ValueError):
                    continue
                rows.append({
                    'stock_code': str(code_field).strip(),
                    'stock_name': str(name_field).strip(),
                    'hold_ratio': ratio,
                })
        return rows
    except Exception as e:
        return []


def fetch_top10(code, year):
    """akshare 前十大持仓兜底（季报）"""
    try:
        import akshare as ak
        df = ak.fund_portfolio_hold_em(symbol=code, date=str(year))
        if df is None or df.empty:
            return []
        rows = []
        for _, r in df.iterrows():
            qstr = str(r['季度'])
            m = re.search(r'(\d{4})年(\d)季度', qstr)
            if not m:
                continue
            mo = m.group(2)
            rd = {'1': f'{m.group(1)}-03-31', '2': f'{m.group(1)}-06-30',
                  '3': f'{m.group(1)}-09-30', '4': f'{m.group(1)}-12-31'}.get(mo, '')
            try:
                ratio = float(r['占净值比例'])
            except (TypeError, ValueError):
                continue
            rows.append({
                'stock_code': str(r['股票代码']).strip(),
                'stock_name': str(r['股票名称']).strip(),
                'hold_ratio': ratio,
                'report_date': rd,
            })
        return rows
    except Exception:
        return []


def main():
    base = pd.read_csv(SRC, encoding='utf-8-sig', dtype={'代码': str})
    base['代码'] = base['代码'].astype(str).str.zfill(6)
    codes = base['代码'].tolist()
    print(f'下载 {len(codes)} 只样本 × 东财全持仓 + akshare 前十大兜底')

    all_rows = []
    fail = []
    for i, code in enumerate(codes, 1):
        n_before = len(all_rows)
        # 1) 半年报 / 年报 全持仓
        for y in YEARS:
            for m in MONTHS_FULL:
                rd = quarter_end(y, m)
                rows = fetch_full(code, y, m)
                for r in rows:
                    all_rows.append({
                        'fund_code': code,
                        'report_date': rd,
                        'stock_code': r['stock_code'],
                        'stock_name': r['stock_name'],
                        'hold_ratio': r['hold_ratio'],
                        'source': f'em-full-{y}-{m}',
                    })
                time.sleep(0.08)
        # 2) 前十大兜底
        for y in YEARS:
            rows = fetch_top10(code, y)
            for r in rows:
                if 'report_date' not in r:
                    continue
                all_rows.append({
                    'fund_code': code,
                    'report_date': r['report_date'],
                    'stock_code': r['stock_code'],
                    'stock_name': r['stock_name'],
                    'hold_ratio': r['hold_ratio'],
                    'source': f'ak-top10-{y}',
                })
            time.sleep(0.05)
        print(f'  [{i:2d}/{len(codes)}] {code} +{len(all_rows)-n_before:5d} 条（累计 {len(all_rows)}）', flush=True)

    df = pd.DataFrame(all_rows)
    df = df.drop_duplicates(subset=['fund_code', 'report_date', 'stock_code'])
    out = os.path.join(OUT_DIR, 'external_holdings_2026-08-30.csv')
    df.to_csv(out, index=False, encoding='utf-8-sig')
    print(f'\n已落盘 {out}')
    print(f'总记录 {len(df):,} / {df["fund_code"].nunique()} 只 / {df["report_date"].nunique()} 个报告期')
    print('来源分布：')
    print(df['source'].value_counts().head(10).to_string())


if __name__ == '__main__':
    sys.exit(main() or 0)