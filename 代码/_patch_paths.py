# -*- coding: utf-8 -*-
import os, io

BASE = r"D:\Desktop\基金经理行为分析研究"
CODE = os.path.join(BASE, "代码")

# token -> (subfolder, newname)   [subfolder is relative to 数据\]
MAP = {
    "fund_holdings_full_v2.csv": ("L2_持仓偏离层","基金持仓明细_全量修正版.csv"),
    "l5_de_v22.csv": ("L5_认知行为层","处置效应DE指标_修正版.csv"),
    # 〔2026-08-14 治理〕mvp_panel_v22 / mvp_panel_v20 等为模拟占位面板的旧 token，
    # 对应源文件已删除，相关映射一并移除，避免工具误把真实脚本改回模拟路径。
    # "mvp_panel_v22.csv": ("L4_风险应对层","主分析面板_修正版.csv"),
    # "mvp_panel_v20.csv": ("L4_风险应对层","预处理面板_v20_诊断用.csv"),
    "l5_lsv_v20.csv": ("L5_认知行为层","羊群行为LSV指标_诊断用.csv"),
    "l5_de_fixed.csv": ("L5_认知行为层","处置效应DE修正_诊断用.csv"),
    "mvp_panel_v2.csv": ("L4_风险应对层","主分析面板_旧版v2.csv"),
    "ra_purification_ff5.csv": ("L5_认知行为层","RA因子正交纯化结果.csv"),
    "double_sort_AS_ICI.csv": ("L4_风险应对层","双重排序AS_ICI结果.csv"),
    "fund_holdings_full.csv": ("L2_持仓偏离层","基金持仓明细_初版.csv"),
    "fund_holdings_top10.csv": ("L2_持仓偏离层","基金前十重仓.csv"),
    "fund_nav_all.csv": ("L4_风险应对层","基金净值历史_全量.csv"),
    "index_000300_constituents.csv": ("基金基础信息","沪深300成分股.csv"),
    "fund_list_200.csv": ("基金基础信息","基金列表_200只样本.csv"),
    "fund_industry_200.csv": ("基金基础信息","基金行业映射_200只.csv"),
    "mvp_regression_v2.csv": ("L4_风险应对层","主回归结果_v2.csv"),
    "as_200_funds_v2.csv": ("L2_持仓偏离层","主动偏离AS指标_200基金.csv"),
    "rg_200_funds_v2.csv": ("L3_交易行为层","收益缺口RG指标_200基金.csv"),
    "ici_200_funds_v2.csv": ("L2_持仓偏离层","隐性交易ICI指标_200基金.csv"),
}

TARGETS = [
    "inspect_inventory.py","inspect_inventory2.py","inspect_inventory3.py",
    "de_fix_analysis.py","ra_purification_check.py","ra_purification_ff5.py",
    "robustness_check.py","full_pipeline_v2.py","download_200_funds.py",
]

ABS = r"D:/Desktop/基金经理行为分析研究/数据"

def build_replacements(token, sub, newname):
    reps = []
    # os.path.join(DATA, 'token')  and "token"
    reps.append((f"os.path.join(DATA, '{token}')", f"os.path.join(DATA, '{sub}', '{newname}')"))
    reps.append((f'os.path.join(DATA, "{token}")', f'os.path.join(DATA, "{sub}", "{newname}")'))
    reps.append((f"os.path.join(DATA_DIR, '{token}')", f"os.path.join(DATA_DIR, '{sub}', '{newname}')"))
    reps.append((f'os.path.join(DATA_DIR, "{token}")', f'os.path.join(DATA_DIR, "{sub}", "{newname}")'))
    # f-string f'{DATA}/token'
    reps.append((f"{{DATA}}/{token}", f"{{DATA}}/{sub}/{newname}"))
    # absolute
    reps.append((f"'{ABS}/{token}'", f"'{ABS}/{sub}/{newname}'"))
    reps.append((f'"{ABS}/{token}"', f'"{ABS}/{sub}/{newname}"'))
    return reps

all_reps = []
for tok,(sub,nn) in MAP.items():
    all_reps += build_replacements(tok, sub, nn)

total_changes = 0
for fn in TARGETS:
    p = os.path.join(CODE, fn)
    with io.open(p, encoding="utf-8") as f:
        s = f.read()
    orig = s
    for old,new in all_reps:
        if old in s:
            s = s.replace(old, new)
            total_changes += 1
    if s != orig:
        with io.open(p, "w", encoding="utf-8") as f:
            f.write(s)
        print(f"  patched {fn}")
    else:
        print(f"  (no change) {fn}")

print(f"\nTotal replacements: {total_changes}")
