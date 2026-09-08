# -*- coding: utf-8 -*-
"""统一产物文件日期为 2026-08-31（2026-09-01）

背景：reports/ 下的权威产物已命名为 2026-08-31（论文初稿、方法详解），
但三个生成脚本与核验脚本里的输出名仍写死 2026-08-26，导致核验脚本找不到产物。
本脚本把「产物文件名」统一到 2026-08-31；中间 JSON 的日期常量（TODAY=2026-08-26）不动。
"""
import io
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SDIR = os.path.join(ROOT, 'scripts')
BAK = '.bak_20260901'
OLD, NEW = '2026-08-26', '2026-08-31'


def rd(p):
    return io.open(p, encoding='utf-8').read()


def wr(p, s):
    io.open(p, 'w', encoding='utf-8').write(s)


def patch(fn, pairs, label):
    p = os.path.join(SDIR, fn)
    src = rd(p)
    bak = p + BAK
    if not os.path.exists(bak):
        wr(bak, src)
    hit = 0
    for old, new in pairs:
        if old not in src:
            print('  !! 未命中（%s）：%s' % (fn, old[:70]))
            continue
        src = src.replace(old, new)
        hit += 1
    wr(p, src)
    print('  %s %s：替换 %d/%d' % (label, fn, hit, len(pairs)))
    return hit == len(pairs)


ok = True

# 论文 docx：注释 + 代码各一处
ok &= patch('_draft_docx_20260826.py', [
    ('论文初稿_' + OLD + '.docx', '论文初稿_' + NEW + '.docx'),
], '产物名')

# 方法详解 HTML：注释 + 代码各一处（同一字符串，replace 全部）
ok &= patch('_detail_html_20260826.py', [
    ('方法详解_' + OLD + '.html', '方法详解_' + NEW + '.html'),
], '产物名')

# 画像 HTML
ok &= patch('_report_20260826.py', [
    ('投资经理行为画像_' + OLD + '.html', '投资经理行为画像_' + NEW + '.html'),
], '产物名')

# 核验脚本：仅产物读取改用 ART，JSON 仍用 TODAY
ok &= patch('_xcheck_20260826.py', [
    ("TODAY = '" + OLD + "'",
     "TODAY = '" + OLD + "'\nART = '" + NEW + "'  # 产物文件日期（8-30 深夜那轮重生成后为 31 日）"),
    ("read_docx_text(os.path.join(REP, f'论文初稿_{TODAY}.docx'))",
     "read_docx_text(os.path.join(REP, f'论文初稿_{ART}.docx'))"),
    ("read_text(os.path.join(REP, f'方法详解_{TODAY}.html'))",
     "read_text(os.path.join(REP, f'方法详解_{ART}.html'))"),
    ("read_text(os.path.join(REP, f'投资经理行为画像_{TODAY}.html'))",
     "read_text(os.path.join(REP, f'投资经理行为画像_{ART}.html'))"),
    ("_zf.ZipFile(os.path.join(REP, f'论文初稿_{TODAY}.docx'))",
     "_zf.ZipFile(os.path.join(REP, f'论文初稿_{ART}.docx'))"),
], '核验引用')

print('全部成功' if ok else '存在未命中项')
sys.exit(0 if ok else 1)
