# -*- coding: utf-8 -*-
import io
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'output')
h = io.open(os.path.join(ROOT, 'reports', '投资经理行为画像_2026-08-26.html'),
            encoding='utf-8').read()


def rj(n):
    return json.load(io.open(os.path.join(OUT, n), encoding='utf-8'))


VER = rj('五维复合定稿验证_2026-08-26.json')
REG = rj('主回归_v3_2026-08-26.json')
POR = rj('画像_群体与典型_2026-08-26.json')
DESC = rj('统计性描述_2026-08-26.json')
REF = rj('参考文献_定稿_2026-08-26.json')

checks = []


def want(tag, s):
    checks.append((tag, s in h, s))


for d, v in VER['S3_单维'].items():
    want('S3单维 ' + d, '%.5f' % v['coef'])
    want('S3单维t ' + d, '%.2f' % v['t'])
for d, v in VER['S3_联立']['系数'].items():
    want('S3联立 ' + d, '%.5f' % v['coef'])
for k, v in VER['S1_成分定向'].items():
    want('S1 t ' + k, '%.2f' % v['t'])
for k, v in REG['AS_five_specs'].items():
    c = v.get('coef', {}).get('AS_improved')
    if c:
        want('AS ' + k, '%.6f' % c['b'])
for d in POR['群体画像']['五维']['差值']:
    want('群体差值 ' + d, '%.4f' % POR['群体画像']['五维']['差值'][d])
for g in ['Q1最低', 'Q5最高']:
    want('分组规模 ' + g, '%.2f' % POR['能力五分组背景']['规模亿'][g])
    want('分组alpha ' + g, '%.4f' % POR['能力五分组背景']['ff5_alpha'][g])
want('样本 基金数', str(DESC['样本覆盖']['基金数']))
want('样本 季度数', str(DESC['样本覆盖']['季度数']))
want('文献 61 条', REF['61'][:40])
want('文献 1 条', REF['1'][:40])

bad = [c for c in checks if not c[1]]
print('checked:', len(checks), 'missing:', len(bad))
for tag, _, s in bad:
    print('  MISS', tag, '->', s)
