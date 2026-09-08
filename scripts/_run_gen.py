# -*- coding: utf-8 -*-
import traceback, sys
try:
    with open("D:/Desktop/基金经理行为分析研究/_gen_results_html.py", encoding="utf-8") as f:
        code = f.read()
    ns = {}
    exec(compile(code, "_gen_results_html.py", "exec"), ns)
    with open("D:/Desktop/基金经理行为分析研究/_gen_ok.txt", "w", encoding="utf-8") as g:
        g.write("OK\n")
except Exception:
    with open("D:/Desktop/基金经理行为分析研究/_gen_ok.txt", "w", encoding="utf-8") as g:
        g.write(traceback.format_exc())
