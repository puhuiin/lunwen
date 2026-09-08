# -*- coding: utf-8 -*-
"""画像节数据复核（2026-09-02）
重点：五分组背景表中「学历/CFA 占比随能力组不升反降」是否为缺失率假象。
问题机制：占比以全组人数为分母，但背景数据覆盖率本身随能力组单调下降
（Q1 98.6% → Q5 82.2%），缺失被当作「非硕士」计入分母，制造虚假下降趋势。
"""
import json, os
import numpy as np, pandas as pd
import scipy.stats as st

BASE = r'd:\Desktop\基金经理行为分析研究'
OUT = os.path.join(BASE, 'output')
L1D = os.path.join(BASE, '指标计算流水线', 'data', 'L1_背景特征层')

score = pd.read_csv(os.path.join(OUT, '六维能力复合得分_含L1_2026-08-26.csv'))
info = pd.read_csv(os.path.join(L1D, '基金详细信息_最终版.csv'))
mgr = pd.read_csv(os.path.join(L1D, '基金经理信息_最终版.csv'))

d = score.set_index('fund_code').dropna(subset=['ff5_alpha'])
d = d.join(info.set_index('fund_code')[['基金经理人', 'latest_scale_yi']], how='left')
d = d.join(mgr.drop_duplicates('manager_name').set_index('manager_name')[['education', 'CFA', 'school']],
           on='基金经理人', how='left')
d['规模亿'] = pd.to_numeric(d['latest_scale_yi'], errors='coerce')
d['grp'] = pd.qcut(d['综合能力'], 5, labels=['Q1最低', 'Q2', 'Q3', 'Q4', 'Q5最高'])

res = {'样本': {'N': int(len(d)),
               'education覆盖': round(float(d['education'].notna().mean()), 4),
               'CFA覆盖': round(float(d['CFA'].notna().mean()), 4),
               'school覆盖': round(float(d['school'].notna().mean()), 4),
               'CFA持有人数': int((d['CFA'].astype(str) == '是').sum())}}

rows = {}
for g, s in d.groupby('grp', observed=True):
    sub_e = s.dropna(subset=['education'])
    sub_c = s.dropna(subset=['CFA'])
    rows[g] = dict(
        n=int(len(s)),
        背景覆盖率=round(float(s['education'].notna().mean()), 4),
        硕士以上_全组分母=round(float((s['education'].astype(str).isin(['硕士', '博士'])).mean()), 4),
        硕士以上_有效分母=round(float((sub_e['education'].isin(['硕士', '博士'])).mean()), 4),
        CFA_全组分母=round(float((s['CFA'].astype(str) == '是').mean()), 4),
        CFA_有效分母=round(float((sub_c['CFA'] == '是').mean()), 4),
        规模亿_中位=round(float(s['规模亿'].median()), 3),
        规模亿_均值=round(float(s['规模亿'].mean()), 3),
    )
res['五分组'] = rows

# 有效样本内相关性检验（缺失剔除后趋势是否还存在）
se = d.dropna(subset=['education'])
r_e, p_e = st.pearsonr(se['综合能力'], (se['education'].isin(['硕士', '博士'])).astype(float))
sc = d.dropna(subset=['CFA'])
r_c, p_c = st.pearsonr(sc['综合能力'], (sc['CFA'] == '是').astype(float))
# 覆盖率本身与能力得分的相关（证明缺失非随机）
r_m, p_m = st.pearsonr(d['综合能力'], d['education'].notna().astype(float))
res['有效样本内检验'] = {
    '硕士以上': dict(n=int(len(se)), r=round(float(r_e), 4), p=round(float(p_e), 4),
                 判定='无趋势' if p_e > 0.05 else '有趋势'),
    'CFA': dict(n=int(len(sc)), r=round(float(r_c), 4), p=round(float(p_c), 4),
                判定='无趋势' if p_c > 0.05 else '有趋势（10% 水平）'),
    '缺失非随机': dict(r_覆盖率与能力=round(float(r_m), 4), p=round(float(p_m), 6),
                  判定='缺失与能力显著相关，占比按全组分母计算会产生假趋势'
                  if p_m < 0.05 else '缺失随机'),
}

print('=== 样本与覆盖率 ===')
for k, v in res['样本'].items():
    print(f'  {k} = {v}')
print('\n=== 五分组：全组分母 vs 有效分母 ===')
print('%-7s %4s %8s | %10s %10s | %9s %9s | %9s %9s' %
      ('组', 'n', '覆盖率', '硕全组', '硕有效', 'CFA全组', 'CFA有效', '规模中位', '规模均值'))
for g, v in rows.items():
    print('%-7s %4d %7.1f%% | %10.3f %10.3f | %9.3f %9.3f | %9.2f %9.2f' %
          (g, v['n'], v['背景覆盖率'] * 100, v['硕士以上_全组分母'], v['硕士以上_有效分母'],
           v['CFA_全组分母'], v['CFA_有效分母'], v['规模亿_中位'], v['规模亿_均值']))
print('\n=== 有效样本内检验 ===')
for k, v in res['有效样本内检验'].items():
    print(f'  {k}: {v}')

with open(os.path.join(OUT, '画像审查_背景变量缺失偏差_2026-09-02.json'), 'w', encoding='utf-8') as f:
    json.dump(res, f, ensure_ascii=False, indent=1)
print('\n已保存 output/画像审查_背景变量缺失偏差_2026-09-02.json')
