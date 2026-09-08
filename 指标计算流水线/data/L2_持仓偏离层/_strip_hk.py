# -*- coding: utf-8 -*-
"""从 v3 中剔除港股(006xxx/009xxx 等非A股代码), 生成 v3 终版(仅A股持仓)。"""
import pandas as pd

SRC = r'D:\Desktop\基金经理行为分析研究\指标计算流水线\data\L2_持仓偏离层\基金持仓明细_全量修正版_v3.csv'
OUT = r'D:\Desktop\基金经理行为分析研究\指标计算流水线\data\L2_持仓偏离层\基金持仓明细_全量修正版_v3.csv'

VALID_PFX = ('000','001','002','003','300','301','400','420','430',
             '600','601','603','605','688','689',
             '830','831','832','833','834','835','836','837','838','839',
             '870','871','872','873','920')

df = pd.read_csv(SRC, dtype=str, keep_default_na=False, low_memory=False)
sc = df['stock_code'].str.strip()
hk_mask = sc.str.startswith(('006','009','010','011','012','013','014','015','016','017','018','019','020','021','022','023','024','025','026','027','028','029')) | (~sc.map(lambda c: c.startswith(VALID_PFX)))
hk_count = int(hk_mask.sum())
hk_codes = sorted(sc[hk_mask].unique())

clean = df[~hk_mask].copy()
clean['stock_code'] = clean['stock_code'].str.strip()
clean.to_csv(OUT, index=False, encoding='utf-8-sig')

print(f'v3 原行数: {len(df)}')
print(f'剔除港股/非A股行: {hk_count}')
print(f'剔除代码数: {len(hk_codes)}')
print(f'v3 终版行数: {len(clean)}')
print('剔除代码样例:', hk_codes[:30])
# 校验终版代码全部为合法前缀
lsc = clean['stock_code'].str.strip()
bad = lsc[~lsc.map(lambda c: c.startswith(VALID_PFX))]
print(f'终版非合法前缀行: {len(bad)}')