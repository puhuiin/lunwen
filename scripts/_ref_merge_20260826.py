# -*- coding: utf-8 -*-
"""
汇总新报告参考文献清单（报告素材）

输入：output/文献底库_merged_2026-08-26.json（51 条，编号 1-51，已核验 GB/T 7714）
新增：本会话网络核验的 10 条（52-61），全部含卷期页/DOI
输出：output/参考文献_定稿_2026-08-26.json
      output/参考文献_定稿_2026-08-26.csv
      output/指标文献映射_2026-08-26.csv
"""
import os, json
import pandas as pd

BASE = r'd:\Desktop\基金经理行为分析研究'
OUT = os.path.join(BASE, 'output')

refs = json.load(open(os.path.join(OUT, '文献底库_merged_2026-08-26.json'), encoding='utf-8'))
refs = {int(k): v.replace('&amp;', '&') for k, v in refs.items()}

NEW = {
    52: 'GOETZMANN W N, INGERSOLL J, SPIEGEL M, WELCH I. Portfolio performance manipulation and manipulation-proof performance measures[J]. The Review of Financial Studies, 2007, 20(5): 1503-1546.',
    53: 'SORTINO F A, PRICE L N. Performance measurement in a downside risk framework[J]. The Journal of Investing, 1994, 3(3): 59-64.',
    54: 'SHARPE W F. Mutual fund performance[J]. The Journal of Business, 1966, 39(1): 119-138.',
    55: 'FRAZZINI A, FRIEDMAN J, POMORSKI L. Deactivating active share[J]. Financial Analysts Journal, 2016, 72(2): 14-21.',
    56: 'PETAJISTO A. Author response to "Deactivating active share"[J]. Financial Analysts Journal, 2016, 72(4): 11-12.',
    57: 'WERMERS R. A matter of style: the causes and consequences of style drift in institutional portfolios[R]. Working Paper, University of Maryland, 2012.',
    58: 'CHEN Y, WEI H. Fund style drift and fund performance: evidence from China[J]. PLoS ONE, 2025, 20(2): e0316932.',
    59: 'PUETZ A, RUENZI S. Overconfidence among professional investors: evidence from mutual fund managers[J]. Journal of Business Finance & Accounting, 2011, 38(5-6): 684-712.',
    60: 'KACPERCZYK M, SIALM C, ZHENG L. Unobserved actions of mutual funds[J]. The Review of Financial Studies, 2008, 21(6): 2379-2416.',
    61: 'TREYNOR J L, MAZUY K K. Can mutual funds outguess the market?[J]. Harvard Business Review, 1966, 44(4): 131-136.',
}

DOI = {
    52: '10.1093/rfs/hhm025', 53: '10.3905/joi.3.3.59', 55: '10.2469/faj.v72.n2.2',
    57: '10.2139/ssrn.1573410', 58: '10.1371/journal.pone.0316932',
    59: '10.1111/j.1468-5957.2010.02237.x', 60: '10.1093/rfs/hhm034',
}

dup = sorted(set(NEW) & set(refs))
assert not dup, f'编号冲突: {dup}'
refs.update(NEW)

miss = [i for i in range(1, max(refs) + 1) if i not in refs]
print('总条数:', len(refs), '| 编号范围: 1 -', max(refs), '| 缺号:', miss)
assert not miss

bad = [k for k, v in refs.items() if ('[J]' not in v and '[M]' not in v and '[R]' not in v)]
print('文献类型标识缺失:', bad)
print('残留 HTML 实体:', [k for k, v in refs.items() if '&amp;' in v or '&lt;' in v])

json.dump({str(k): refs[k] for k in sorted(refs)},
          open(os.path.join(OUT, '参考文献_定稿_2026-08-26.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=2)

rows = []
for k in sorted(refs):
    v = refs[k]
    rows.append({'序号': k, '文献': v, 'DOI': DOI.get(k, ''),
                 '类型': '期刊论文' if '[J]' in v else ('专著' if '[M]' in v else '工作论文'),
                 '语种': '中文' if any('\u4e00' <= c <= '\u9fff' for c in v) else '英文',
                 '来源': '既有底库' if k <= 51 else '本轮新增核验'})
df = pd.DataFrame(rows)
df.to_csv(os.path.join(OUT, '参考文献_定稿_2026-08-26.csv'), index=False, encoding='utf-8-sig')
print(df.groupby(['来源', '类型']).size())
print('中文文献:', int((df['语种'] == '中文').sum()), '条')

MAP = [
    ('L2 认知能力', 'risk_asym 风险偏好不对称性', '+', 1, 'Kahneman & Tversky (1979) 前景理论：损失域与收益域的风险态度不对称'),
    ('L2 认知能力', 'de 处置效应', '-', 15, 'Shefrin & Statman (1985) 提出处置效应；Odean (1998)=[16] 给出实证测度'),
    ('L2 认知能力', 'oc_conf 过度自信（换手×过度交易）', '-', 59, 'Puetz & Ruenzi (2011) 以业绩后换手率上升识别基金经理过度自信；Gervais & Odean (2001)=[13] 提供理论'),
    ('L3 配置选择能力', 'ICI 行业集中度', '+', 30, 'Kacperczyk, Sialm & Zheng (2005) 行业集中度衡量主动配置信息优势'),
    ('L3 配置选择能力', 'ISDI 行业风格漂移指数', '-', 58, 'Chen & Wei (2025) 提出基于行业配置的漂移测度；Wermers (2012)=[57] 为方法论源头'),
    ('L4a 风险应对能力', 'ARG 调仓收益', '+', 60, 'Kacperczyk, Sialm & Zheng (2008) return gap：持仓外的未观测调仓贡献'),
    ('L4a 风险应对能力', 'timing 下行保护系数（−HM γ）', '+', 45, 'Henriksson & Merton (1981) 分段市场择时检验；Treynor & Mazuy (1966)=[61] 为二次项前身'),
    ('L4b 风险转化能力', 'mppm8_lag 抗操纵绩效测度', '+', 52, 'Goetzmann et al. (2007) 操纵稳健业绩测度，规避择时/期权化操纵'),
    ('L4b 风险转化能力', 'sortino8_lag Sortino 比率', '+', 53, 'Sortino & Price (1994) 下行风险框架下的绩效测度；Ang, Chen & Xing (2006)=[39] 提供下行风险定价依据'),
    ('L4b 风险转化能力', 'sharpe8_lag Sharpe 比率', '+', 54, 'Sharpe (1966) 总风险调整后收益基准参照'),
    ('L5 交易执行能力', 'SDI 策略偏离指数', '-', 57, 'Wermers (2012) 风格漂移的离散度刻画'),
    ('L5 交易执行能力', 'lsv 交易趋同度', '+', 34, 'Lakonishok, Shleifer & Vishny (1992) LSV 羊群度量；Wermers (1999)=[31] 给出基金层应用'),
    ('剔除', 'AS_improved 改进主动份额', 'ns', 55, 'Frazzini, Friedman & Pomorski (2016) 控制基准后 AS 无预测力；Cremers & Petajisto (2009)=[28]、Petajisto (2013)=[29]、Petajisto (2016)=[56] 为争议对方'),
    ('剔除', 'TO_wind_clean 换手率', 'ns', 59, '双口径均不显著且符号反向；换手率作为过度自信代理已由 oc_conf 承载'),
    ('剔除', 'rc_mom 追涨杀跌', 'ns', 35, 'Grinblatt, Titman & Wermers (1995) 动量交易度量；本样本覆盖仅 53.5%、单指标 t=−0.51'),
    ('剔除', 'rsstab_lag 风险稳定性', 'ns', 33, 'Brown, Harlow & Starks (1996) 锦标赛式风险调整；与收益波动率 corr=−0.749，正交化后 t=−0.87'),
    ('业绩基准', 'ff5_adj_return / alpha_q', '因变量', 23, 'Fama & French (2015) 五因子模型；李志冰等 (2017)=[43] 为中国市场适用性检验'),
]
mp = pd.DataFrame(MAP, columns=['维度', '指标', '定向符号', '主引文献序号', '文献依据说明'])
mp['主引文献'] = mp['主引文献序号'].map(refs)
assert mp['主引文献'].notna().all()
mp.to_csv(os.path.join(OUT, '指标文献映射_2026-08-26.csv'), index=False, encoding='utf-8-sig')
print('\n指标文献映射:', mp.shape, '| 覆盖维度:', mp['维度'].nunique())
print(mp[['维度', '指标', '定向符号', '主引文献序号']].to_string(index=False))
