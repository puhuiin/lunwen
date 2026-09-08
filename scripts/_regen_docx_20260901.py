# -*- coding: utf-8 -*-
"""重生成论文 docx，遇 Word 占用时自动回退到临时文件名（2026-09-01）

若 reports/论文初稿_2026-08-31.docx 正被 Word 打开，直接写入会抛 PermissionError。
本脚本先探测可写性：可写则原地覆盖；不可写则改输出到
reports/论文初稿_2026-08-31.new.docx，并提示用户关闭 Word 后手动替换。
"""
import io
import os
import runpy
import sys

sys.stdout.reconfigure(encoding='utf-8')

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SDIR = os.path.join(ROOT, 'scripts')
MAIN = os.path.join(SDIR, '_draft_docx_20260826.py')
TARGET = "out_path = REP / '论文初稿_2026-08-31.docx'"
DOCX = os.path.join(ROOT, 'reports', '论文初稿_2026-08-31.docx')
TMP = os.path.join(SDIR, '_tmp_draft_20260901.py')


def writable(p):
    if not os.path.exists(p):
        return True
    try:
        with io.open(p, 'r+b'):
            return True
    except (PermissionError, OSError):
        return False


src = io.open(MAIN, encoding='utf-8').read()
if TARGET not in src:
    print('!! 未找到输出语句，请检查脚本是否已改名')
    sys.exit(1)

if writable(DOCX):
    print('目标可写，原地覆盖重生成')
    runpy.run_path(MAIN, run_name='__main__')
else:
    alt = "out_path = REP / '论文初稿_2026-08-31.new.docx'"
    print('!! 目标被占用（Word 未关闭），改为输出到 论文初稿_2026-08-31.new.docx')
    io.open(TMP, 'w', encoding='utf-8').write(src.replace(TARGET, alt, 1))
    try:
        runpy.run_path(TMP, run_name='__main__')
    finally:
        if os.path.exists(TMP):
            os.remove(TMP)
    print('\n提示：关闭 Word 后运行  mv reports/论文初稿_2026-08-31.new.docx '
          'reports/论文初稿_2026-08-31.docx  完成替换，然后重跑核验。')
