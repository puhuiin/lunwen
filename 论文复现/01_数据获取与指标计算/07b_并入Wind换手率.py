# -*- coding: utf-8 -*-
"""
07b_并入Wind换手率.py
=====================
把图书馆 Wind 导出的「基金报告期持仓换手率」整合进主面板。合并两个 EDE 文件：
  - EDE2026081d5.xlsx   = 近期窗 2015H1-2026H1（23 个半年）
  - EDE20260815(2).xlsx = 历史补窗 2005H1-2015H1（21 个半年，与近期窗共享 2015H1 且逐值一致）
  合并得 2005H1-2026H1 连续序列（覆盖窗前拓 10 年）。

处理流程：
  1. 用 raw-XML 读取绕过 openpyxl 的 named-style bug (Wind 导出 xlsx 常见)。
  2. 归一化基金代码：剥 '.OF'/'.SZ'/'.SH' -> 去前导零 -> 对齐主面板 fund_code (纯整数字符串)。
  3. 解析两个文件共 44 个半年度列 -> (year, H1/H2)（近期 23 + 历史 21）。
  4. reshape 为长表 (norm, per, ede%)。
  5. 半年 -> 季度映射：H1(1-6月) -> Q1(01-01)+Q2(04-01)；H2(7-12月) -> Q3(07-01)+Q4(10-01)。
     换手率是半年聚合量，半年内两季度视为同一常数（符合其定义，属低频慢变特征）。
  6. 数据清洗：
       - ede% <= 0 或 ede% > 20000 视为数据错误 -> NaN（>20000% 出现两只不同基金同一
         占位值 5,955,902，判定为 Wind 占位/错误）。
       - 其余保留为 TO_wind（原始 % 单位）。
  7. 输出：
       A) 长表 CSV：指标计算流水线/data/L3_交易行为层/基金换手率_Wind_EDE20260815.csv
          (列: fund_code, report_date, TO_wind, TO_wind_clean)
       B) 合并面板：指标计算流水线/output/主分析面板_重建_含TOwind.csv
          (原面板 + TO_wind + TO_wind_clean；原面板不动)

口径：经 Wind 指标说明确认，TO_wind 为单边换手率（=MAX(买入成本,卖出收入)/AVG区间内股票市值，非买卖之和），量级约为双边口径的 1/2；仅影响尺度，不影响符号与显著性。
"""
import pandas as pd, numpy as np, os, re, zipfile, xml.etree.ElementTree as ET

# —— 可移植路径：全部由本文件位置推导，文件夹移动到任何盘符/路径都能跑 ——
HERE = os.path.dirname(os.path.abspath(__file__))          # 指标计算流水线/
ROOT = os.path.dirname(HERE)                                # 项目根目录/
PANEL = os.path.join(HERE, 'output', '主分析面板_重建.csv')
EDE   = os.path.join(ROOT, 'backups', '数据', 'EDE2026081d5.xlsx')        # 近期窗 2015H1-2026H1（2026-08-25归类后数据/移至backups/）
EDE2  = os.path.join(ROOT, 'backups', '数据', 'EDE20260815(2).xlsx')      # 历史补窗 2005H1-2015H1
OUT_LONG = os.path.join(HERE, 'data', 'L3_交易行为层', '基金换手率_Wind_EDE20260815.csv')
OUT_PANEL = os.path.join(HERE, 'output', '主分析面板_重建_含TOwind.csv')

NS = {'m': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}

def read_xlsx_raw(fp):
    z = zipfile.ZipFile(fp); shared = []
    if 'xl/sharedStrings.xml' in z.namelist():
        r = ET.fromstring(z.read('xl/sharedStrings.xml'))
        for si in r.findall('m:si', NS):
            shared.append(''.join(t.text or '' for t in si.iter(
                '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t')))
    wb = ET.fromstring(z.read('xl/workbook.xml'))
    rels = ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))
    rid2t = {rel.get('Id'): rel.get('Target') for rel in rels}
    s = wb.find('m:sheets', NS)[0]
    rid = s.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id')
    target = rid2t[rid]
    if not target.startswith('xl/'):
        target = 'xl/' + target.lstrip('/')
    root = ET.fromstring(z.read(target)); sd = root.find('m:sheetData', NS); rows = []
    for row in sd.findall('m:row', NS):
        cells = {}
        for c in row.findall('m:c', NS):
            ref = c.get('r'); t = c.get('t'); v = c.find('m:v', NS); isn = c.find('m:is', NS)
            col = re.match(r'[A-Z]+', ref).group(); ci = 0
            for ch in col:
                ci = ci * 26 + (ord(ch) - 64)
            ci -= 1
            if t == 's' and v is not None:
                val = shared[int(v.text)]
            elif isn is not None:
                val = ''.join(x.text or '' for x in isn.iter(
                    '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t'))
            elif v is not None:
                val = v.text
            else:
                val = None
            cells[ci] = val
        mx = max(cells) if cells else -1
        rows.append([cells.get(i) for i in range(mx + 1)])
    return rows

def norm_code(s):
    if s is None:
        return None
    s = str(s).replace('.OF', '').replace('.SZ', '').replace('.SH', '').strip()
    return s.lstrip('0') or '0'

def per_to_quarters(year, htype):
    """半年 -> 当年两个季初 report_date 字符串"""
    if htype == 'H1':
        return [f'{year}-01-01', f'{year}-04-01']
    else:
        return [f'{year}-07-01', f'{year}-10-01']

# ---- 1+2. 读取两个 EDE 文件并各自 reshape 为长表 ----
def ede_to_long(fp, tag):
    print(f'[1] 读取 EDE ({tag}) ...')
    rows = read_xlsx_raw(fp)
    hdr = rows[0]
    df = pd.DataFrame(rows[1:], columns=hdr)
    df['norm'] = df.iloc[:, 0].map(norm_code)
    per_cols = []
    for h in hdr[2:]:
        if h is None:
            continue
        m = re.search(r'\[年度\]\s*(\d{4})\s*\[区间类型\]\s*(上半年|下半年)', str(h))
        if m:
            per_cols.append((int(m.group(1)), 'H1' if m.group(2) == '上半年' else 'H2', h))
    print(f'    {tag} 半年度列数: {len(per_cols)}  起止: {per_cols[0][0]}{per_cols[0][1]} ... {per_cols[-1][0]}{per_cols[-1][1]}')
    recs = []
    for y, ht, h in per_cols:
        col = df[['norm', h]].copy()
        col.columns = ['norm', 'val']
        col['year'] = y
        col['ht'] = ht
        col['val'] = pd.to_numeric(col['val'], errors='coerce')
        recs.append(col)
    long = pd.concat(recs, ignore_index=True).dropna(subset=['val'])
    print(f'    {tag} 有效 cell: {len(long)}')
    return long

long_n = ede_to_long(EDE,  '近期窗 2015H1-2026H1')
long_h = ede_to_long(EDE2, '历史窗 2005H1-2015H1')
long = pd.concat([long_n, long_h], ignore_index=True)
print(f'[2] 合并两窗长表: 总有效 cell = {len(long)}（2015H1 为桥接，两文件逐值一致）')

# ---- 3. 半年 -> 季度 ----
print('[3] 半年 -> 季度映射 ...')
expand = []
for _, r in long.iterrows():
    for rd in per_to_quarters(r['year'], r['ht']):
        expand.append((r['norm'], rd, r['val']))
exp = pd.DataFrame(expand, columns=['fund_code', 'report_date', 'TO_wind'])
# EDE 含 F 前缀等特殊代码（如 F050004），无法匹配纯数字面板 fund_code，安全转 int 并丢弃
exp['fund_code'] = pd.to_numeric(exp['fund_code'], errors='coerce')
exp = exp.dropna(subset=['fund_code'])
exp['fund_code'] = exp['fund_code'].astype(int)  # 对齐主面板 int 型 fund_code
# 两窗在 2015H1 重叠且逐值一致；去重 (fund_code, report_date) 保留非空 TO_wind，避免合并后重复键
exp = exp.sort_values('TO_wind', na_position='last').drop_duplicates(['fund_code', 'report_date'], keep='first').reset_index(drop=True)
print(f'    [3] 去重后 (fund_code, report_date) 唯一数: {len(exp)}')

# ---- 4. 清洗 ----
print('[4] 数据清洗 ...')
raw = exp['TO_wind'].copy()
neg = (raw <= 0).sum()
absurd = (raw > 20000).sum()
print(f'    <=0: {neg}  | >20000%: {absurd}')
clean = raw.where((raw > 0) & (raw <= 20000))
exp['TO_wind_clean'] = clean

# ---- 5. 输出长表（仅面板 400 只，保持产物聚焦）----
pan = pd.read_csv(PANEL)
pf = set(pan['fund_code'].astype(int))
exp = exp[exp['fund_code'].isin(pf)].copy()
os.makedirs(os.path.dirname(OUT_LONG), exist_ok=True)
exp_out = exp.sort_values(['fund_code', 'report_date']).reset_index(drop=True)
exp_out.to_csv(OUT_LONG, index=False, encoding='utf-8-sig')
print(f'    长表写出: {OUT_LONG}  ({len(exp_out)} 行, 仅面板基金)')

# ---- 6. 合并进面板 ----
print('[6] 合并进主面板 ...')
before_cols = list(pan.columns)
merged = pan.merge(exp_out[['fund_code', 'report_date', 'TO_wind', 'TO_wind_clean']],
                   on=['fund_code', 'report_date'], how='left')
merged.to_csv(OUT_PANEL, index=False, encoding='utf-8-sig')
print(f'    合并面板写出: {OUT_PANEL}  shape={merged.shape}')

# ---- 7. 覆盖率汇报 ----
n_to = merged['TO_wind'].notna().sum()
n_toc = merged['TO_wind_clean'].notna().sum()
print('\n==== 整合结果汇报 ====')
print(f'面板总行数: {len(merged)}')
print(f'TO_wind(原始%) 非空: {n_to} ({n_to/len(merged)*100:.1f}%)')
print(f'TO_wind_clean 非空: {n_toc} ({n_toc/len(merged)*100:.1f}%)')
print(f'覆盖基金数(TO_wind_clean): {merged.loc[merged.TO_wind_clean.notna(),"fund_code"].nunique()}')
print(f'对比旧 TO_two_sided 非空: {pan["TO_two_sided"].notna().sum()} ({pan["TO_two_sided"].notna().mean()*100:.1f}%)')
print('done.')
