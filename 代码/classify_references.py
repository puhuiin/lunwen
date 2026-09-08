# -*- coding: utf-8 -*-
"""
参考文献分类整理：补充文献/子目录 → 顶层 L1-L5 + 因变量测度 + 其他文献
映射规则（基于文献盘点清单确认）：
  CN_MANAGER → L1_背景特征层（基金经理特征）
  CN_TOURNAMENT → L4_风险应对层（清单明确锦标赛归L4）
  CN_HERDING → L5_认知行为层（清单明确LSV/羊群归L5）
  CN_DISPOSITION → L5_认知行为层（处置效应）
  CN_STYLE_DRIFT → L5_认知行为层（风格漂移）
  CN_PERF_BEHAVIOR → 因变量测度（业绩行为=因变量）
  CN_FLOW_INVESTOR → 因变量测度（资金流=业绩因变量）
  CN_FUND_OTHER → 其他文献（不明确属哪层）
  UNCERTAIN → 其他文献
  CORE_INTL → 已归档副本（移到其他文献/已归档副本）
"""
import os, shutil
from pathlib import Path

BASE = Path(r'D:\Desktop\基金经理行为分析研究\参考文献')
SUPP = BASE / '补充文献'

# 映射：补充文献子目录 → 顶层目标目录
MAPPING = {
    'CN_MANAGER': 'L1_背景特征层',
    'CN_TOURNAMENT': 'L4_风险应对层',
    'CN_HERDING': 'L5_认知行为层',
    'CN_DISPOSITION': 'L5_认知行为层',
    'CN_STYLE_DRIFT': 'L5_认知行为层',
    'CN_PERF_BEHAVIOR': '因变量测度',
    'CN_FLOW_INVESTOR': '因变量测度',
    'CN_FUND_OTHER': '其他文献',
    'UNCERTAIN': '其他文献',
    'CORE_INTL': '其他文献/已归档副本',
}

# 1. 预览方案
print('='*60)
print('分类方案预览')
print('='*60)
plan = {}
for sub, target in MAPPING.items():
    src = SUPP / sub
    if not src.exists():
        continue
    pdfs = list(src.glob('*.pdf'))
    if sub not in plan:
        plan[sub] = {}
    plan[sub] = {'target': target, 'count': len(pdfs), 'files': [p.name for p in pdfs]}
    print(f'  {sub}({len(pdfs)}个) → {target}/')

print()
print('目标目录现有文件数（移动前）：')
for d in ['L1_背景特征层','L2_持仓偏离层','L3_交易行为层','L4_风险应对层','L5_认知行为层','M_方法论与识别检验']:
    p = BASE / d
    if p.exists():
        n = len(list(p.glob('*.pdf')))
        print(f'  {d}: {n}个')

# 2. 执行移动
print()
print('='*60)
print('执行移动')
print('='*60)

# 创建目标目录
for target in set(MAPPING.values()):
    (BASE / target).mkdir(parents=True, exist_ok=True)

moved = 0
conflicts = 0
log = []

for sub, target in MAPPING.items():
    src = SUPP / sub
    if not src.exists():
        continue
    dst_dir = BASE / target
    dst_dir.mkdir(parents=True, exist_ok=True)
    for pdf in src.glob('*.pdf'):
        dst = dst_dir / pdf.name
        if dst.exists():
            # 重名：加前缀
            dst = dst_dir / f'{sub}_{pdf.name}'
            conflicts += 1
        try:
            shutil.move(str(pdf), str(dst))
            moved += 1
            log.append(f'移动: {sub}/{pdf.name} → {target}/{dst.name}')
        except Exception as e:
            log.append(f'失败: {sub}/{pdf.name} → {target} | {e}')

print(f'成功移动: {moved}个')
print(f'重名处理: {conflicts}个')

# 3. 清理空的补充文献子目录
print()
print('清理空目录:')
cleaned = 0
for sub in MAPPING.keys():
    src = SUPP / sub
    if src.exists() and not any(src.iterdir()):
        src.rmdir()
        print(f'  删除空目录: {sub}')
        cleaned += 1
print(f'清理空目录: {cleaned}个')

# 4. 最终统计
print()
print('='*60)
print('最终统计')
print('='*60)
total = 0
for d in sorted(BASE.iterdir()):
    if d.is_dir():
        n = len(list(d.glob('*.pdf')))
        # 含子目录
        n_all = len(list(d.rglob('*.pdf')))
        if n_all > 0:
            print(f'  {d.name}: {n_all}个PDF (顶层{n})')
            total += n_all
print(f'  总计: {total}个PDF')

# 5. 保存日志
log_path = BASE / '分类整理日志.txt'
with open(log_path, 'w', encoding='utf-8') as f:
    f.write('\n'.join(log))
print(f'\n日志已保存: {log_path}')
