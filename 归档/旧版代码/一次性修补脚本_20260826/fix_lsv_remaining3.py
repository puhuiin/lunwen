# -*- coding: utf-8 -*-
"""
fix_lsv_remaining3.py
清理残余陈旧引用（fixer2 因 (a) 含 </strong> 与 p&lt;0.001 而失败，且文件未落盘）。
本次覆盖全部 7 处，全部精确短语替换 + 计数断言。
"""
import shutil

SRC = r"d:\Desktop\基金经理行为分析研究\merged_manuscript.html"
BAK = SRC + ".bak_lsvfix3"
shutil.copy(SRC, BAK)
print("已备份 ->", BAK)

html = open(SRC, encoding="utf-8").read()

repls = [
    # L117 创新四
    ("未来一年的业绩（t=4.95）", "未来4季度的业绩（t=10.51）"),
    # L510 面板规模
    ("包含9,581行 × 154列", "包含9,974行 × 154列"),
    # L662 核心发现2（含 </strong> 与 p&lt;0.001）
    ("显著预测未来一年的基金业绩</strong>（系数+0.313, t=10.51, p&lt;0.001）",
     "显著预测未来4季度的基金业绩</strong>（系数+0.313, t=10.51, p&lt;0.001）"),
    # L1043 §4.16 第二（同时覆盖“并能”前缀）
    ("显著预测未来一年业绩（前向4季度，t≈4.95）",
     "显著预测未来4季度业绩（t≈10.51）"),
    # L1062 本章核心结论：未来一年 -> 未来4季度
    ("可预测未来一年业绩", "可预测未来4季度业绩"),
    # L1062：符号反转 -> 方向不稳（与全文修正口径一致）
    ("但其截面符号在纠正幸存者偏差后发生反转",
     "但其截面关联对样本选择高度敏感（存活为正、全样本口径方向不稳）"),
    # L1383 iFinD 交叉验证
    ("LSV的符号反转结论保留CSMAR口径", "LSV的方向敏感性结论保留CSMAR口径"),
]

for old, new in repls:
    c = html.count(old)
    if c != 1:
        raise SystemExit(f"[FAIL] 计数异常({c}次): {old!r}")
    html = html.replace(old, new, 1)
    print(f"[OK] {old!r}")

open(SRC, "w", encoding="utf-8").write(html)
print("\n完成。")
