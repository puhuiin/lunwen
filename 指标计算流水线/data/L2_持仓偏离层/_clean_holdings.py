# -*- coding: utf-8 -*-
"""清理基金持仓明细 v2 源数据。
1. 移除 6 位但非法前缀的代码行(列错位垃圾, name 漏为 hold_value 数字)。
2. 将 1-4 位被截断的深市代码(000xxx-003xxx 前导零丢失)左补 0 还原为 6 位。
3. 输出 v3 并生成清洗报告。
"""
import pandas as pd

SRC = r'D:\Desktop\基金经理行为分析研究\指标计算流水线\data\L2_持仓偏离层\基金持仓明细_全量修正版_v2.csv'
OUT = r'D:\Desktop\基金经理行为分析研究\指标计算流水线\data\L2_持仓偏离层\基金持仓明细_全量修正版_v3.csv'
REPORT = r'D:\Desktop\基金经理行为分析研究\指标计算流水线\data\L2_持仓偏离层\_clean_report_20260815.csv'

VALID_PFX = ('000','001','002','003','300','301','400','420','430',
             '600','601','603','605','688','689',
             '830','831','832','833','834','835','836','837','838','839',
             '870','871','872','873','920')

df = pd.read_csv(SRC, dtype=str, keep_default_na=False, low_memory=False)
total = len(df)

sc = df['stock_code'].str.strip()
sn = df['stock_name'].str.strip()

def is_numeric_ish(x):
    t = x.replace(',', '').replace('.', '').replace('%', '').replace('-', '').strip()
    return t.isdigit()

# --- 垃圾判定 ---
# (a) 6 位但非法前缀
valid6 = sc.str.fullmatch(r'\d{6}')
bad_prefix = valid6 & ~sc.map(lambda c: c.startswith(VALID_PFX))
# (b) name 是数字(列错位) 或 为空
name_numeric = sn.apply(is_numeric_ish) & sn.ne('')
name_empty = sn.eq('')
# (c) 代码非数字
code_nonnumeric = ~sc.str.fullmatch(r'\d+')

garbage_mask = bad_prefix | name_numeric | name_empty | code_nonnumeric
garbage_count = int(garbage_mask.sum())

# --- 前导零修复(仅对非垃圾行中 1-4 位代码) ---
fix_mask = (~garbage_mask) & sc.str.fullmatch(r'\d{1,4}')
df.loc[fix_mask, 'stock_code'] = sc[fix_mask].str.zfill(6)
fix_count = int(fix_mask.sum())

clean = df[~garbage_mask].copy()
clean['stock_code'] = clean['stock_code'].str.strip()

# 校验修复后代码唯一完整
clean_count = len(clean)
clean['stock_code'] = clean['stock_code'].astype(str)
lens = clean['stock_code'].str.len()
print(f'总行数: {total}')
print(f'垃圾行(移除): {garbage_count}')
print(f'前导零修复行: {fix_count}')
print(f'清洗后行数: {clean_count}')
print(f'清洗后非6位代码行: {int((~lens.eq(6)).sum())}')

clean.to_csv(OUT, index=False, encoding='utf-8-sig')
print(f'已保存: {OUT}')

# 报告
report = pd.DataFrame([{
    '总行数': total, '垃圾行移除': garbage_count, '前导零修复行': fix_count,
    '清洗后行数': clean_count, '清洗后股票代码种类': clean['stock_code'].nunique()
}])
report.to_csv(REPORT, index=False, encoding='utf-8-sig')
print(f'清洗报告: {REPORT}')

# 垃圾代码清单
garbage_codes = sorted(sc[garbage_mask].unique())
with open(r'D:\Desktop\基金经理行为分析研究\指标计算流水线\data\L2_持仓偏离层\_garbage_codes_removed.txt','w',encoding='utf-8') as f:
    f.write('\n'.join(garbage_codes))
print(f'移除的垃圾代码数: {len(garbage_codes)}')