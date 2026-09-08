# -*- coding: utf-8 -*-
"""
投资经理画像（2026-08-26，六维含 L1 版）
一、群体画像：按 FF5 alpha 分 Top5% / Bottom5%，对比六维能力得分与原始指标
二、典型画像：按「综合能力 + 单维极端 + 反例」挑 6 名经理，输出画像卡素材
经理姓名来源：基金详细信息_最终版.csv 的「基金经理人」列
个人特征来源：基金经理信息_最终版.csv（school/education/gender/CFA/resume）
"""
import pandas as pd, numpy as np, os, json, re
import statsmodels.api as sm

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, 'output')
L1 = os.path.join(BASE, '指标计算流水线', 'data', 'L1_背景特征层')
TODAY = '2026-08-26'
DIM_NAMES = ['基本面优势', '认知能力', '配置选择能力', '风险应对能力', '风险转化能力', '交易执行能力']
RAW = ['mgr_total_tenure_v2', 'log_fund_age', 'log_aum',
       'risk_asym', 'de', 'oc_conf', 'anchor_high', 'ICI', 'ISDI', 'ARG', 'timing',
       'mppm8_lag', 'sortino8_lag', 'sharpe8_lag', 'SDI', 'lsv', 'AS_improved',
       'return_volatility', 'TO_wind_clean', 'quarter_return']
res = {}

score = pd.read_csv(os.path.join(OUT, f'六维能力复合得分_含L1_{TODAY}.csv'))
panel = pd.read_csv(os.path.join(OUT, f'分析面板_v3_{TODAY}.csv'), parse_dates=['report_date'])
# 认知维度新成分（2026-09-02 文献挖掘新增）：锚定效应 anchor_high
_new = pd.read_csv(os.path.join(OUT, 'L2新增候选_面板_2026-09-02.csv'), parse_dates=['report_date'])
panel = panel.merge(_new[['fund_code', 'report_date', 'anchor_high']],
                    on=['fund_code', 'report_date'], how='left')
tim = pd.read_csv(os.path.join(OUT, f'择时系数_季度HM_{TODAY}.csv')).set_index('fund_code')[['timing']]
p_info1 = os.path.join(OUT, '基金详细信息_最终版.csv')
p_info2 = os.path.join(L1, '基金详细信息_最终版.csv')
info = pd.read_csv(p_info1 if os.path.exists(p_info1) else p_info2)

p_mgr1 = os.path.join(OUT, '基金经理信息_最终版.csv')
p_mgr2 = os.path.join(L1, '基金经理信息_最终版.csv')
mgr = pd.read_csv(p_mgr1 if os.path.exists(p_mgr1) else p_mgr2)

raw = panel.groupby('fund_code')[[c for c in RAW if c != 'timing']].mean().join(tim, how='left')
d = score.set_index('fund_code').join(raw, rsuffix='_r')
d = d.dropna(subset=['ff5_alpha'])
print('可画像基金 %d 只' % len(d))

# ---------- 一、群体画像 ----------
n5 = max(1, int(np.ceil(len(d) * 0.05)))
top = d.nlargest(n5, 'ff5_alpha')
bot = d.nsmallest(n5, 'ff5_alpha')
print(f'\n=== 群体画像：Top5%（{n5}只） vs Bottom5%（{n5}只） ===')

print('\n[六维能力得分]')
cmp1 = pd.DataFrame({'Top5%': top[DIM_NAMES].mean(), 'Bottom5%': bot[DIM_NAMES].mean()})
cmp1['差值'] = cmp1['Top5%'] - cmp1['Bottom5%']
tt = {c: sm.stats.ttest_ind(top[c].dropna(), bot[c].dropna(), usevar='unequal') for c in DIM_NAMES}
cmp1['t'] = [round(float(tt[c][0]), 2) for c in DIM_NAMES]
cmp1['p'] = [round(float(tt[c][1]), 4) for c in DIM_NAMES]
print(cmp1.round(3).to_string())

print('\n[原始指标]')
rc = [c for c in RAW if c in d.columns]
cmp2 = pd.DataFrame({'Top5%': top[rc].mean(), 'Bottom5%': bot[rc].mean()})
cmp2['差值'] = cmp2['Top5%'] - cmp2['Bottom5%']
tt2 = {c: sm.stats.ttest_ind(top[c].dropna(), bot[c].dropna(), usevar='unequal') for c in rc}
cmp2['t'] = [round(float(tt2[c][0]), 2) for c in rc]
cmp2['p'] = [round(float(tt2[c][1]), 4) for c in rc]
print(cmp2.round(4).to_string())

print('\n[业绩]')
for lab, s in [('Top5%', top), ('Bottom5%', bot)]:
    print('  %-9s FF5 alpha 均值 %+.4f  季度收益均值 %+.4f  综合能力 %+.3f'
          % (lab, s['ff5_alpha'].mean(), s['quarter_return'].mean(), s['综合能力'].mean()))

res['群体画像'] = dict(
    n_each=n5,
    六维=json.loads(cmp1.round(4).to_json()),
    原始指标=json.loads(cmp2.round(4).to_json()),
    业绩=dict(top_alpha=round(float(top['ff5_alpha'].mean()), 4),
              bot_alpha=round(float(bot['ff5_alpha'].mean()), 4),
              top_综合=round(float(top['综合能力'].mean()), 3),
              bot_综合=round(float(bot['综合能力'].mean()), 3)))

# ---------- 二、经理身份映射 ----------
INFO_COLS = ['基金简称', '基金经理人', 'management_company', 'latest_scale_yi',
             'management_fee', 'benchmark', 'investment_style', 'risk_level', 'fund_type_fixed']
inf = info.set_index('fund_code')[[c for c in INFO_COLS if c in info.columns]]
d = d.join(inf, how='left')

mg = mgr.drop_duplicates('manager_name').set_index('manager_name')[['school', 'education', 'gender', 'CFA', 'resume']]
d = d.join(mg, on='基金经理人', how='left')
print('\n经理姓名可匹配 %d / %d ；个人特征可匹配 %d'
      % (d['基金经理人'].notna().sum(), len(d), d['education'].notna().sum()))

# ---------- 三、能力分层的背景特征（配合群体画像） ----------
d['规模亿'] = pd.to_numeric(d.get('latest_scale_yi'), errors='coerce')
d['费率'] = d['management_fee'].astype(str).str.extract(r'([\d.]+)').astype(float) if 'management_fee' in d else np.nan
d['grp'] = pd.qcut(d['综合能力'], 5, labels=['Q1最低', 'Q2', 'Q3', 'Q4', 'Q5最高'])
prof = d.groupby('grp', observed=True).agg(
    n=('综合能力', 'size'), 综合能力=('综合能力', 'mean'), ff5_alpha=('ff5_alpha', 'mean'),
    季度收益=('quarter_return', 'mean'), 规模亿=('规模亿', 'median'), 管理费率=('费率', 'mean'),
    硕士以上占比=('education', lambda s: float((s.astype(str).isin(['硕士', '博士'])).mean())),
    CFA占比=('CFA', lambda s: float((s.astype(str) == '是').mean())))
print('\n=== 综合能力五分组的背景特征（六维口径） ===')
print(prof.round(4).to_string())
res['能力五分组背景'] = json.loads(prof.round(4).to_json())

# ---------- 四、典型画像：6 名经理 ----------
def pick(col, how='max', used_mgr=()):
    s = d.dropna(subset=[col, '基金经理人'])
    s = s[~s['基金经理人'].isin(used_mgr)]
    return (s[col].idxmax() if how == 'max' else s[col].idxmin())

used = []
plan = [('全能型：综合能力最高', '综合能力', 'max'),
        ('风险定价型：风险转化能力最高', '风险转化能力', 'max'),
        ('认知纪律型：认知能力最高', '认知能力', 'max'),
        ('攻守转换型：风险应对能力最高', '风险应对能力', 'max'),
        ('基本面优势型：基本面优势最高', '基本面优势', 'max'),
        ('反例：综合能力最低', '综合能力', 'min')]
cards = []
for label, col, how in plan:
    fc = pick(col, how, used_mgr=used)
    r = d.loc[fc]
    used.append(r['基金经理人'])
    card = dict(标签=label, fund_code=int(fc), 基金简称=r.get('基金简称'), 经理=r.get('基金经理人'),
                公司=r.get('management_company'), 类型=r.get('fund_type_fixed'),
                规模亿=None if pd.isna(r.get('规模亿')) else round(float(r['规模亿']), 2),
                管理费率=None if pd.isna(r.get('费率')) else float(r['费率']),
                学历=None if pd.isna(r.get('education')) else str(r['education']),
                性别=None if pd.isna(r.get('gender')) else str(r['gender']),
                CFA=None if pd.isna(r.get('CFA')) else str(r['CFA']),
                院校=None if pd.isna(r.get('school')) else str(r['school']),
                ff5_alpha=round(float(r['ff5_alpha']), 4),
                季度收益=round(float(r['quarter_return']), 4),
                综合能力=round(float(r['综合能力']), 3),
                综合能力分位=round(float((d['综合能力'] < r['综合能力']).mean()), 3),
                六维={k: round(float(r[k]), 3) for k in DIM_NAMES},
                六维分位={k: round(float((d[k] < r[k]).mean()), 3) for k in DIM_NAMES},
                关键原始指标={k: (None if pd.isna(r.get(k)) else round(float(r[k]), 4))
                              for k in ['mgr_total_tenure_v2', 'log_fund_age', 'log_aum',
                                        'risk_asym', 'de', 'oc_conf', 'ICI', 'ISDI', 'ARG', 'timing',
                                        'mppm8_lag', 'sharpe8_lag', 'SDI', 'lsv']})
    cards.append(card)

print('\n=== 典型画像（6 名） ===')
for c in cards:
    print('\n[%s] %s（%s，%s，%s）' % (c['标签'], c['经理'], c['基金简称'], c['公司'], c['类型']))
    print('  alpha %+.4f  季度收益 %+.4f  综合能力 %+.3f（分位 %.0f%%）'
          % (c['ff5_alpha'], c['季度收益'], c['综合能力'], c['综合能力分位'] * 100))
    print('  六维：' + '  '.join('%s %+.2f(%.0f%%)' % (k, v, c['六维分位'][k] * 100)
                                for k, v in c['六维'].items()))
    print('  背景：学历 %s / 性别 %s / CFA %s / 规模 %s亿 / 费率 %s%%'
          % (c['学历'], c['性别'], c['CFA'], c['规模亿'], c['管理费率']))
res['典型画像'] = cards

# ---------- 五、落盘 ----------
with open(os.path.join(OUT, f'画像_群体与典型_{TODAY}.json'), 'w', encoding='utf-8') as f:
    json.dump(res, f, ensure_ascii=False, indent=2)
pd.DataFrame(cards).drop(columns=['六维', '六维分位', '关键原始指标']).to_csv(
    os.path.join(OUT, f'画像_典型经理_{TODAY}.csv'), index=False, encoding='utf-8-sig')
d.reset_index()[['fund_code', '基金简称', '基金经理人', 'management_company'] + DIM_NAMES +
                ['综合能力', 'ff5_alpha', 'quarter_return', 'grp']].to_csv(
    os.path.join(OUT, f'画像_全样本能力表_{TODAY}.csv'), index=False, encoding='utf-8-sig')
print('\n已落盘：画像_群体与典型 / 画像_典型经理 / 画像_全样本能力表（六维含 L1）')
