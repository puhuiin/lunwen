# -*- coding: utf-8 -*-
"""修正两处表述风险（2026-09-01）

风险①：「18.0% 的增量 R²」易被误读为相对提升，实为 R² 的绝对增量 0.1796
        （相对全模型 R² 的降幅为 39.4%）。统一改为「绝对增量 X（占全模型 R² 的 Y%）」。
风险②：两个 t=+5.38 撞车——表 4 中 sortino8 规格II 的同期单一成分 t，
        与结论 D2 样本外跨期复合维度的单维 t，数值相同纯属巧合。加显式消歧。

按整串精确替换（读取时 universal newlines，写入时还原 CRLF），
规避全角符号与行尾差异导致的匹配失败。每个替换必须命中且仅命中 1 次。
"""
import io
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SDIR = os.path.join(ROOT, 'scripts')
BAK = '.bak_20260901'

RATIO_D = '{DG["D3_剔除L4b"]["增量R2"] / DG["D3_剔除L4b"]["含L4b"]["r2"]:.1%}'
RATIO_R = "'%.1f%%' % (DG['D3_剔除L4b']['增量R2'] / DG['D3_剔除L4b']['含L4b']['r2'] * 100)"

NL = chr(10)
DISAMBIG_HTML = (
    '<span class="footnote">数值巧合提示：此处的样本外单维 t 值与指标汇总表中 '
    'sortino8 规格II 的 t 值数值相同，纯属巧合——前者为跨期的复合维度，'
    '后者为同期的单一成分，口径与对象均不同，引用时须区分。</span>'
)


def patch(fn, pairs):
    p = os.path.join(SDIR, fn)
    src = io.open(p, encoding='utf-8').read()
    bak = p + BAK
    if not os.path.exists(bak):
        io.open(bak, 'w', encoding='utf-8').write(src)
    hit = 0
    for old, new in pairs:
        c = src.count(old)
        if c != 1:
            print('  !! %s 命中 %d 次（应为 1）：%s' % (fn, c, old[:70].replace(NL, '\\n')))
            continue
        src = src.replace(old, new, 1)
        hit += 1
    io.open(p, 'w', encoding='utf-8').write(src)
    print('  %s：替换 %d/%d' % (fn, hit, len(pairs)))
    return hit == len(pairs)


ok = True

# ------------------------------------------------- 方法详解 HTML
ok &= patch('_detail_html_20260826.py', [
    ('（增量 R²={DG["D3_剔除L4b"]["增量R2"]:.4f}）；',
     '（绝对增量 {DG["D3_剔除L4b"]["增量R2"]:.4f}，占全模型 R² 的 ' + RATIO_D + '）；'),
    ('{DG["D3_剔除L4b"]["增量R2"]:.1%} 的增量 R² 有一部分来自定义同源，',
     '{DG["D3_剔除L4b"]["增量R2"]:.3f} 的增量 R²（绝对增量，占全模型 R² 的 '
     + RATIO_D + '）有一部分来自定义同源，'),
    ('证明它含有跨期可预测的信息，而非同期恒等式。',
     '证明它含有跨期可预测的信息，而非同期恒等式。' + NL + DISAMBIG_HTML),
])

# ------------------------------------------------- 画像 HTML
ok &= patch('_report_20260826.py', [
    ('<td class="dir">R² 由 %s 降至 %s（增量 %s）；其余维度符号与显著性不变</td>',
     '<td class="dir">R² 由 %s 降至 %s（绝对增量 %s，占全模型 R² 的 %s）；'
     '其余维度符号与显著性不变</td>'),
    ("""  % (f(DG['D3_剔除L4b']['含L4b']['r2'], 4), f(DG['D3_剔除L4b']['去L4b']['r2'], 4),
     f(DG['D3_剔除L4b']['增量R2'], 4)))""",
     """  % (f(DG['D3_剔除L4b']['含L4b']['r2'], 4), f(DG['D3_剔除L4b']['去L4b']['r2'], 4),
     f(DG['D3_剔除L4b']['增量R2'], 4),
     """ + RATIO_R + """))"""),
    ("'它 %s 的增量 R² 里确实有一部分来自定义同源，'",
     "'它 %s 的增量 R²（绝对增量，占全模型 R² 的 %s）里确实有一部分来自定义同源，'"),
    ("""  % (f(DG['D3_剔除L4b']['增量R2'], 4),
     f(DG['D2_样本外']['单维']['风险转化能力']['t'], 2)))""",
     """  % (f(DG['D3_剔除L4b']['增量R2'], 4),
     """ + RATIO_R + """,
     f(DG['D2_样本外']['单维']['风险转化能力']['t'], 2)))"""),
    ("  '不是同期恒等式。'",
     "  '不是同期恒等式。'" + NL + "  '<span class=\"evid\">" + DISAMBIG_HTML + "</span>'"),
])

print('全部替换成功' if ok else '存在未命中项，请检查上方 !! 行')
sys.exit(0 if ok else 1)
