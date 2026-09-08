# -*- coding: utf-8 -*-
import os, json
import pandas as pd
import numpy as np
import statsmodels.api as sm
import sys, io
if hasattr(sys.stdout, 'buffer') and getattr(sys.stdout, 'encoding', '').lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'buffer') and getattr(sys.stderr, 'encoding', '').lower() != 'utf-8':
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')


BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, 'output')
PANEL_DIR = os.path.join(BASE, '原始数据', '分析面板')
RAW_DIR = os.path.join(BASE, '原始数据')
TODAY = '2026-08-26'
os.makedirs(OUT, exist_ok=True)

def find_data(fn, subdir=None):
    candidates = []
    if subdir:
        candidates.append(os.path.join(RAW_DIR, subdir, fn))
    candidates.append(os.path.join(PANEL_DIR, fn))
    candidates.append(os.path.join(OUT, fn))
    candidates.append(os.path.join(RAW_DIR, fn))
    for p in candidates:
        if os.path.exists(p):
            return p
    return candidates[0]

CTRL = ['mgr_total_tenure_v2', 'log_fund_age', 'log_aum']
DIMS = {
    '基本面优势': [('mgr_total_tenure_v2', -1), ('log_fund_age', -1), ('log_aum', -1)],
    '认知能力': [('risk_asym', +1), ('de', -1), ('oc_conf', -1), ('anchor_high', +1)],
    '配置选择能力': [('ICI', +1), ('ISDI', -1)],
    '风险应对能力': [('ARG', +1), ('timing', +1)],
    '风险转化能力': [('mppm8_lag', +1), ('sortino8_lag', +1), ('sharpe8_lag', +1)],
    '交易执行能力': [('SDI', -1), ('lsv', +1)],
}
DIM_NAMES = list(DIMS.keys())
ALL_COMP = [m for v in DIMS.values() for m, _ in v]

def winsor(s, p=0.01):
    return s.clip(s.quantile(p), s.quantile(1 - p))

def z(s):
    return (s - s.mean()) / s.std()

def ew(frame):
    return frame.sum(axis=1, skipna=True) / frame.notna().sum(axis=1)

def reg(y, X):
    d = pd.concat([y, X], axis=1).dropna()
    if len(d) < 10:
        return None
    return sm.OLS(d.iloc[:, 0], sm.add_constant(d.iloc[:, 1:])).fit(cov_type='HC1')

print('=' * 80)
print('步骤 1：加载全量分析面板与时间轴划分')
print('=' * 80)

panel = pd.read_csv(find_data('分析面板_v3_2026Q2补因子_2026-09-10.csv', '分析面板'), parse_dates=['report_date'])
_new = pd.read_csv(find_data('L2新增候选_面板_2026-09-02.csv', '分析面板'), parse_dates=['report_date'])
panel = panel.merge(_new[['fund_code', 'report_date', 'anchor_high']],
                    on=['fund_code', 'report_date'], how='left')

in_mask = panel['year'] <= 2024
out_mask = (panel['year'] >= 2025)  # 09-10:2026Q2因子已补(BetaPlus同源),6季度统一分母

in_df = panel[in_mask].copy()
out_df = panel[out_mask].copy()

n_q_in = in_df[['year', 'quarter']].drop_duplicates().shape[0]
n_q_out = out_df[['year', 'quarter']].drop_duplicates().shape[0]

print(f'样本内（2006–2024）：共 {n_q_in} 个季度，{len(in_df)} 行观测，涉及 {in_df["fund_code"].nunique()} 只基金')
print(f'样本外（2025–2026）：共 {n_q_out} 个季度，{len(out_df)} 行观测，涉及 {out_df["fund_code"].nunique()} 只基金')

print('\n' + '=' * 80)
print('步骤 2：样本内指标与六维画像构建（2006–2024 纯净数据）')
print('=' * 80)

timing_in = {}
for fcode, grp in in_df.groupby('fund_code'):
    d = grp[['quarter_return', 'ff5_MKT_excess', 'ff5_RF']].dropna()
    if len(d) >= 12:
        y = d['quarter_return'] - d['ff5_RF']
        mkt = d['ff5_MKT_excess']
        down = np.minimum(0, mkt)
        X = pd.DataFrame({'mkt': mkt, 'down': down})
        res_hm = sm.OLS(y, sm.add_constant(X)).fit()
        timing_in[fcode] = -float(res_hm.params.get('down', 0.0))

tim_df = pd.DataFrame(list(timing_in.items()), columns=['fund_code', 'timing']).set_index('fund_code')
print(f'样本内成功估计 HM 择时系数的基金数：{len(tim_df)}')

Xcols = ['ff5_MKT_excess', 'ff5_SMB', 'ff5_HML', 'ff5_RMW', 'ff5_CMA']
betas_in = {}
alphas_in_ts = {}
for fcode, grp in in_df.groupby('fund_code'):
    d = grp[['excess_return'] + Xcols].dropna()
    if len(d) >= 12:
        A = np.column_stack([np.ones(len(d)), d[Xcols].values])
        b, *_ = np.linalg.lstsq(A, d['excess_return'].values, rcond=None)
        betas_in[fcode] = b
        alphas_in_ts[fcode] = b[0]

counts = in_df.groupby('fund_code').size()
valid_funds = counts[counts >= 12].index
base_cols = [c for c in ALL_COMP if c != 'timing']
sel_cols = list(dict.fromkeys(base_cols + CTRL))

fm_in = in_df.groupby('fund_code')[sel_cols].mean().loc[valid_funds].join(tim_df, how='inner')
fm_in['ff5_alpha_in'] = pd.Series(alphas_in_ts)
fm_in = fm_in.dropna(subset=['ff5_alpha_in'])
print(f'样本内合格并进入基准模型的基金数：N = {len(fm_in)}')

for c in ALL_COMP + CTRL:
    fm_in[c] = winsor(pd.to_numeric(fm_in[c], errors='coerce'))

score_in = pd.DataFrame(index=fm_in.index)
for dim, items in DIMS.items():
    score_in[dim] = ew(pd.DataFrame({m_: sg * z(fm_in[m_]) for m_, sg in items}))
score_in['综合能力'] = ew(score_in[DIM_NAMES])
score_in['ff5_alpha_in'] = fm_in['ff5_alpha_in']

m_in_joint = reg(score_in['ff5_alpha_in'], score_in[DIM_NAMES])
print(f'\n样本内（2006–2024）六维联立回归：N = {m_in_joint.nobs:.0f}, R2 = {m_in_joint.rsquared:.4f}')
for d in DIM_NAMES:
    print(f'  {d:<10}: coef={m_in_joint.params[d]:+.5f}, t={m_in_joint.tvalues[d]:+.2f}, p={m_in_joint.pvalues[d]:.4f}')

print('\n' + '=' * 80)
print('步骤 3：样本外业绩核算（2025–2026 纯盲测）')
print('=' * 80)

out_rows = []
for idx, row in out_df.iterrows():
    fcode = row['fund_code']
    if fcode in betas_in:
        b = betas_in[fcode]
        factor_ret = np.dot(b[1:], row[Xcols].values)
        abnormal = row['excess_return'] - factor_ret
        out_rows.append({
            'fund_code': fcode,
            'report_date': row['report_date'],
            'quarter_return': row['quarter_return'],
            'excess_return': row['excess_return'],
            'abnormal_alpha': abnormal
        })

out_eval_panel = pd.DataFrame(out_rows)
out_eval = out_eval_panel.groupby('fund_code')[['quarter_return', 'excess_return', 'abnormal_alpha']].mean()

full_eval = score_in.join(out_eval, how='inner').dropna()
n_eval = len(full_eval)
print(f'在样本外持续运作并完成盲测评估的基金数：N = {n_eval}')

print('\n' + '=' * 80)
print('步骤 4：样本外五分组单调性检验')
print('=' * 80)

full_eval['grp'] = pd.qcut(full_eval['综合能力'], 5, labels=['Q1最低', 'Q2', 'Q3', 'Q4', 'Q5最高'])

tab_grp = full_eval.groupby('grp', observed=True)[['abnormal_alpha', 'excess_return', 'quarter_return', 'ff5_alpha_in']].mean()
tab_grp['n'] = full_eval.groupby('grp', observed=True).size()
print(tab_grp.round(4).to_string())

hi_ab = full_eval[full_eval['grp'] == 'Q5最高']['abnormal_alpha']
lo_ab = full_eval[full_eval['grp'] == 'Q1最低']['abnormal_alpha']
tt_ab = sm.stats.ttest_ind(hi_ab, lo_ab, usevar='unequal')

hi_ret = full_eval[full_eval['grp'] == 'Q5最高']['quarter_return']
lo_ret = full_eval[full_eval['grp'] == 'Q1最低']['quarter_return']
tt_ret = sm.stats.ttest_ind(hi_ret, lo_ret, usevar='unequal')

hi_ex = full_eval[full_eval['grp'] == 'Q5最高']['excess_return']
lo_ex = full_eval[full_eval['grp'] == 'Q1最低']['excess_return']
tt_ex = sm.stats.ttest_ind(hi_ex, lo_ex, usevar='unequal')

diff_ab = hi_ab.mean() - lo_ab.mean()
diff_ret = hi_ret.mean() - lo_ret.mean()
diff_ex = hi_ex.mean() - lo_ex.mean()

print(f'\n样本外异常超额收益（Abnormal Alpha）：Q5-Q1 = {diff_ab*100:+.2f} 个百分点/季，t = {tt_ab[0]:+.2f}，p = {tt_ab[1]:.4e}')
print(f'样本外季度超额收益（Excess Return）：Q5-Q1 = {diff_ex*100:+.2f} 个百分点/季，t = {tt_ex[0]:+.2f}，p = {tt_ex[1]:.4e}')
print(f'样本外原始季度收益（Quarter Return）：Q5-Q1 = {diff_ret*100:+.2f} 个百分点/季，t = {tt_ret[0]:+.2f}，p = {tt_ret[1]:.4e}')

print('\n' + '=' * 80)
print('步骤 5：样本外预测回归分析（冻结得分对未来收益的预测）')
print('=' * 80)

m_comp = reg(full_eval['abnormal_alpha'], full_eval[['综合能力']])
print(f'综合能力预测回归：beta = {m_comp.params["综合能力"]:+.4f}, t = {m_comp.tvalues["综合能力"]:+.2f}, p = {m_comp.pvalues["综合能力"]:.4f}, R2 = {m_comp.rsquared:.4f}')

dim_uni = {}
for d in DIM_NAMES:
    m = reg(full_eval['abnormal_alpha'], full_eval[[d]])
    dim_uni[d] = {
        'coef': round(float(m.params[d]), 5),
        't': round(float(m.tvalues[d]), 2),
        'p': round(float(m.pvalues[d]), 4),
        'r2': round(float(m.rsquared), 4)
    }
    print(f'  {d:<10}: beta={m.params[d]:+.4f}, t={m.tvalues[d]:+.2f}, p={m.pvalues[d]:.4f}, R2={m.rsquared:.4f}')

m_joint_out = reg(full_eval['abnormal_alpha'], full_eval[DIM_NAMES])
print(f'\n六维联立预测回归：R2 = {m_joint_out.rsquared:.4f}')
dim_joint = {}
for d in DIM_NAMES:
    dim_joint[d] = {
        'coef': round(float(m_joint_out.params[d]), 5),
        't': round(float(m_joint_out.tvalues[d]), 2),
        'p': round(float(m_joint_out.pvalues[d]), 4)
    }
    print(f'  {d:<10}: beta={m_joint_out.params[d]:+.4f}, t={m_joint_out.tvalues[d]:+.2f}, p={m_joint_out.pvalues[d]:.4f}')

print('\n' + '=' * 80)
print('步骤 6：Top 5% vs Bottom 5% 极端群体样本外跟踪')
print('=' * 80)

full_eval['score_pct'] = full_eval['综合能力'].rank(pct=True)
top5 = full_eval[full_eval['score_pct'] >= 0.95]
bot5 = full_eval[full_eval['score_pct'] <= 0.05]

top_ab = top5['abnormal_alpha'].mean()
bot_ab = bot5['abnormal_alpha'].mean()
top_ret = top5['quarter_return'].mean()
bot_ret = bot5['quarter_return'].mean()

tt_top_bot = sm.stats.ttest_ind(top5['abnormal_alpha'], bot5['abnormal_alpha'], usevar='unequal')
print(f'Top 5%（N={len(top5)}）样本外异常 Alpha：{top_ab*100:.2f}%，季度收益：{top_ret*100:.2f}%')
print(f'Bottom 5%（N={len(bot5)}）样本外异常 Alpha：{bot_ab*100:.2f}%，季度收益：{bot_ret*100:.2f}%')
print(f'Top 5% - Bottom 5% 异常 Alpha 差值：{(top_ab - bot_ab)*100:+.2f} 个百分点，t = {tt_top_bot[0]:+.2f}，p = {tt_top_bot[1]:.4e}')

res_oos = {
    '样本信息': {
        '样本内区间': '2006Q3–2024Q4',
        '样本内季度数': n_q_in,
        '样本内基金数': len(fm_in),
        '样本外区间': '2025Q1–2026Q2',
        '样本外季度数': n_q_out,
        '样本外检验基金数': n_eval
    },
    '样本内建模': {
        '联立R2': round(float(m_in_joint.rsquared), 4),
        '联立系数': {d: {'coef': round(float(m_in_joint.params[d]), 5),
                         't': round(float(m_in_joint.tvalues[d]), 2),
                         'p': round(float(m_in_joint.pvalues[d]), 4)} for d in DIM_NAMES}
    },
    '样本外五分组': {
        '异常Alpha均值': {str(k): round(float(v), 5) for k, v in tab_grp['abnormal_alpha'].items()},
        '超额收益均值': {str(k): round(float(v), 5) for k, v in tab_grp['excess_return'].items()},
        '季度收益均值': {str(k): round(float(v), 5) for k, v in tab_grp['quarter_return'].items()},
        '样本内Alpha对照': {str(k): round(float(v), 5) for k, v in tab_grp['ff5_alpha_in'].items()},
        '每组基金数': {str(k): int(v) for k, v in tab_grp['n'].items()},
        'Q5_Q1_异常Alpha': round(float(diff_ab), 5),
        'Q5_Q1_异常Alpha_t': round(float(tt_ab[0]), 2),
        'Q5_Q1_异常Alpha_p': round(float(tt_ab[1]), 4),
        'Q5_Q1_季度收益': round(float(diff_ret), 5),
        'Q5_Q1_季度收益_t': round(float(tt_ret[0]), 2),
        'Q5_Q1_季度收益_p': round(float(tt_ret[1]), 4),
    },
    '样本外预测回归': {
        '综合能力': {
            'coef': round(float(m_comp.params['综合能力']), 5),
            't': round(float(m_comp.tvalues['综合能力']), 2),
            'p': round(float(m_comp.pvalues['综合能力']), 4),
            'r2': round(float(m_comp.rsquared), 4)
        },
        '各维度单变量': dim_uni,
        '各维度联立': {
            'r2': round(float(m_joint_out.rsquared), 4),
            '系数': dim_joint
        }
    },
    'TopBottom群体样本外': {
        'n_top': len(top5),
        'n_bottom': len(bot5),
        'top_abnormal_alpha': round(float(top_ab), 5),
        'bottom_abnormal_alpha': round(float(bot_ab), 5),
        'diff_abnormal_alpha': round(float(top_ab - bot_ab), 5),
        't_abnormal_alpha': round(float(tt_top_bot[0]), 2),
        'top_quarter_return': round(float(top_ret), 5),
        'bottom_quarter_return': round(float(bot_ret), 5),
        'diff_quarter_return': round(float(top_ret - bot_ret), 5),
    }
}

json_path = os.path.join(OUT, '样本外检验_2006_2024_2026Q2_6Q.json')
with open(json_path, 'w', encoding='utf-8') as f:
    json.dump(res_oos, f, ensure_ascii=False, indent=2)

csv_path = os.path.join(OUT, '样本外基金得分与表现明细_20260910_6Q.csv')
full_eval.reset_index().to_csv(csv_path, index=False, encoding='utf-8-sig')

print(f'\n已成功输出结构化核算数据：\n  JSON -> {json_path}\n  CSV  -> {csv_path}')
