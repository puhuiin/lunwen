import pandas as pd

df = pd.read_csv(r'd:\Desktop\基金经理行为分析研究\output\六维能力复合得分_2026-08-25.csv')
dims = ['alloc', 'risk_rsp', 'risk_cnv', 'active', 'discipl', 'cost']
names = {'alloc': '配置力', 'risk_rsp': '风险应对', 'risk_cnv': '风险转化',
         'active': '主动收益', 'discipl': '纪律性', 'cost': '成本控制'}

df = df.dropna(subset=['ff5_adj_return'])
n5 = max(1, int(len(df) * 0.05))
top = df.nlargest(n5, 'ff5_adj_return')
bot = df.nsmallest(n5, 'ff5_adj_return')
print('N=%d, 5%%=%d只' % (len(df), n5))
print('Top5%% ff5均值=%.4f, Bottom5%%=%.4f' % (top['ff5_adj_return'].mean(), bot['ff5_adj_return'].mean()))
rows = []
for d in dims:
    rows.append((names[d], top[d].mean(), bot[d].mean(), top[d].mean() - bot[d].mean()))
rows.sort(key=lambda x: -x[3])
for nm, t, b, diff in rows:
    print('%s: top=%.3f bot=%.3f diff=%.3f' % (nm, t, b, diff))
print()
print('composite: top=%.3f bot=%.3f diff=%.3f' % (top['composite'].mean(), bot['composite'].mean(), top['composite'].mean() - bot['composite'].mean()))
print()
print('覆盖率:')
for d in dims:
    print('%s: %d/400' % (names[d], df[d].notna().sum()))
