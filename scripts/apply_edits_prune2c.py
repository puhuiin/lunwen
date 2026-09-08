# -*- coding: utf-8 -*-
"""prune2c: 清理画像中遗留的 16_TO单边分析 来源引用与 SDI 的'单边主动'措辞（避免与已删除的单边TO分解混淆）。"""
PROFILE = r"D:/Desktop/基金经理行为分析研究/基金经理能力画像与业绩评价.html"

with open(PROFILE, encoding="utf-8") as f:
    s = f.read()
orig = s

edits = [
    ('15_R3_gamma截尾重跑、16_TO单边分析，及既有前向/LSV 回归',
     '15_R3_gamma截尾重跑，及既有前向/LSV 回归',
     'source list (line1151)'),
    ('本项目以单边主动成交占比代理',
     '本项目以主动成交占比代理',
     'SDI def line336'),
    ('单边主动占比代理',
     '主动占比代理',
     'SDI cell line350'),
]
for old, new, label in edits:
    c = s.count(old)
    if c == 0:
        print(f"[WARN] 未命中: {label}")
    else:
        s = s.replace(old, new)
        print(f"[OK] 替换 {c} 次: {label}")

with open(PROFILE, "w", encoding="utf-8") as f:
    f.write(s)
print(f"[INFO] 长度 {len(orig)} -> {len(s)}")
print("DONE")
