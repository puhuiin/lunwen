# -*- coding: utf-8 -*-
import os, shutil, json, re

BASE = r"D:\Desktop\基金经理行为分析研究"
DATA = os.path.join(BASE, "数据")
DRY = True  # True=只打印不移动

# ---------- 规范保留集：旧名 -> (目标子文件夹, 中文新名) ----------
# 子文件夹均位于 数据\ 下
canonical = {
    # L4 风险应对层
    # 〔2026-08-14 治理〕mvp_panel_v22 / _v2 为模拟占位旧 token，对应源已删除，移除映射。
    # "mvp_panel_v22.csv":            ("L4_风险应对层", "主分析面板_修正版.csv"),
    # "mvp_panel_v2.csv":             ("L4_风险应对层", "主分析面板_旧版v2.csv"),
    "mvp_panel_v20.csv":            ("L4_风险应对层", "预处理面板_v20_诊断用.csv"),
    "mvp_regression_v2.csv":        ("L4_风险应对层", "主回归结果_v2.csv"),
    "double_sort_AS_ICI.csv":       ("L4_风险应对层", "双重排序AS_ICI结果.csv"),
    "spec_curve_results.csv":       ("L4_风险应对层", "规格曲线结果.csv"),
    "基金净值历史_全量API.csv":        ("L4_风险应对层", "基金净值历史_全量.csv"),
    "基金排名_匹配_v2.csv":           ("L4_风险应对层", "基金排名_匹配.csv"),
    "基金规模变动_全市场.csv":          ("L4_风险应对层", "基金规模变动_全市场.csv"),
    # L5 认知行为层
    "l5_de_v22.csv":               ("L5_认知行为层", "处置效应DE指标_修正版.csv"),
    "l5_lsv_v21.csv":              ("L5_认知行为层", "羊群行为LSV指标.csv"),
    "l5_lsv_v20.csv":              ("L5_认知行为层", "羊群行为LSV指标_诊断用.csv"),
    "l5_risk_asym_v20.csv":        ("L5_认知行为层", "风险偏好不对称RA指标.csv"),
    "l5_de_fixed.csv":             ("L5_认知行为层", "处置效应DE修正_诊断用.csv"),
    "ra_purification_ff5.csv":     ("L5_认知行为层", "RA因子正交纯化结果.csv"),
    # L2 持仓偏离层
    "fund_holdings_full_v2.csv":    ("L2_持仓偏离层", "基金持仓明细_全量修正版.csv"),
    "fund_holdings_full.csv":       ("L2_持仓偏离层", "基金持仓明细_初版.csv"),
    "fund_holdings_top10.csv":      ("L2_持仓偏离层", "基金前十重仓.csv"),
    "基金行业配置_全量.csv":           ("L2_持仓偏离层", "基金行业配置_全量.csv"),
    "as_200_funds_v2.csv":          ("L2_持仓偏离层", "主动偏离AS指标_200基金.csv"),
    "ici_200_funds_v2.csv":         ("L2_持仓偏离层", "隐性交易ICI指标_200基金.csv"),
    "行业HHI_计算值.csv":            ("L2_持仓偏离层", "行业集中度HHI.csv"),
    # L3 交易行为层
    "rg_200_funds_v2.csv":          ("L3_交易行为层", "收益缺口RG指标_200基金.csv"),
    "基金换手率_补全.csv":            ("L3_交易行为层", "基金换手率.csv"),
    "基金持仓变动_批量.csv":           ("L3_交易行为层", "基金持仓变动_批量.csv"),
    # L1 背景特征层
    "经理信息_合并_v6.csv":           ("L1_背景特征层", "基金经理信息_合并最终版.csv"),
    "基金详细信息_v4_fixed.csv":      ("L1_背景特征层", "基金详细信息_最终版.csv"),
    # 基金基础信息
    "fund_list_200.csv":            ("基金基础信息", "基金列表_200只样本.csv"),
    "基金经理_全量.csv":              ("基金基础信息", "基金经理名单_全量.csv"),
    "fund_industry_200.csv":        ("基金基础信息", "基金行业映射_200只.csv"),
    "index_000300_constituents.csv":("基金基础信息", "沪深300成分股.csv"),
    "index_000905_constituents.csv":("基金基础信息", "中证500成分股.csv"),
    "index_000905_monthly.csv":     ("基金基础信息", "中证500指数月度.csv"),
    "index_000852_monthly.csv":     ("基金基础信息", "中证1000指数月度.csv"),
    # 股价行情
    "stock_prices_full.csv":        ("股价行情", "个股日行情_全量.csv"),
    "stock_monthly_returns_full.csv":("股价行情", "个股月收益率_全量.csv"),
    "stock_monthly_returns.csv":    ("股价行情", "个股月收益率_初版.csv"),
    # 宏观数据
    "宏观_CPI.csv":                 ("宏观数据", "宏观_CPI.csv"),
    "宏观_GDP.csv":                 ("宏观数据", "宏观_GDP.csv"),
    "宏观_LPR.csv":                 ("宏观数据", "宏观_LPR.csv"),
    "宏观_M2.csv":                  ("宏观数据", "宏观_M2.csv"),
    "宏观_PMI.csv":                 ("宏观数据", "宏观_PMI.csv"),
    "宏观_PPI.csv":                 ("宏观数据", "宏观_PPI.csv"),
    "宏观_外汇储备.csv":              ("宏观数据", "宏观_外汇储备.csv"),
    "宏观_社融.csv":                 ("宏观数据", "宏观_社融.csv"),
    # 外部补充数据（保留原样，仅确认存在）
    "ff_factors_complete.csv":      ("FF因子", "FF因子_合并完整版.csv"),
}

# ---------- 保留但不移动（已在子目录或无需整理） ----------
# FF5因子 子目录两个干净因子 -> 合并进 FF因子\
ff5_subdir_merge = {
    "FF5_monthly.csv": ("FF因子", "FF5月度因子.csv"),
    "FF5_daily.csv":   ("FF因子", "FF5日度因子.csv"),
}

# ---------- 明确归档（无用数据）的文件名精确列表（根级） ----------
archive_exact = set()
# 版本面板：除 v2/v20/v22 外全部
for v in ["v3","v4","v5","v6","v7","v8","v9","v10","v11","v12","v14","v16",
          "v17","v18","v19","v21","final"]:
    archive_exact.add(f"mvp_panel_{v}.csv")
# l5_de 除 v22 外
for v in ["v19","v20","v21"]:
    archive_exact.add(f"l5_de_{v}.csv")
archive_exact.add("fixed_fund_level_v19.csv")
archive_exact.add("fixed_fund_level_v20.csv")
archive_exact.add("fixed_fund_level_v21.csv")
# l5_lsv 除 v20/v21 外
archive_exact.add("l5_lsv_v19.csv")
# 基金详细信息 旧版
archive_exact.update(["基金详细信息.csv","基金详细信息_v2.csv","基金详细信息_v3.csv",
                      "基金详细信息_v4.csv","基金详细信息_efinance.csv"])
# 经理信息 旧版
archive_exact.update(["经理信息_v6.csv","经理信息_v7.csv","经理信息_合并_v5.csv"])
# 基金换手率 旧版
archive_exact.update(["基金换手率_计算值.csv","基金换手率_v3.csv","待补充_基金换手率.csv"])
# 基金持仓 补充/旧
archive_exact.update(["基金持仓_补充.csv","基金持仓_补充v2.csv","基金持仓_efinance.csv"])
# 基金行业配置 补充
archive_exact.update(["基金行业配置_补充.csv","基金行业配置_AKShare.csv"])
# 基金净值 旧
archive_exact.update(["基金净值历史_API.csv","基金净值_补充.csv"])
# 基金排名 旧
archive_exact.add("基金排名_匹配.csv")
# 基金列表/经理 旧抓取
archive_exact.update(["fund_list.csv","fund_managers.csv","fund_managers_full.csv",
                      "经理个人信息_抓取.csv","经理档案_深度爬取.csv","经理学历_改进.csv",
                      "待补充_经理个人信息.csv","akshare_全部基金列表_含类型.csv",
                      "AKShare_基金经理列表.csv","efinance_基金经理数据.csv",
                      "efinance_基金基本信息_测试.csv","fundManagers_GitHub.xlsx",
                      "fund_list_GitHub.json","managers_GitHub.json","fund_industry.csv",
                      "fund_industry_all.csv"])
# 数据完整性报告 旧
archive_exact.update(["数据完整性报告.csv","数据完整性报告_v6.txt","数据完整性报告_最终.txt"])
# 其他零散
archive_exact.update(["efinance_基金基本信息_测试.csv"])

# ---------- 按前缀/模式归档 ----------
def should_archive(name):
    if name in archive_exact:
        return True
    # FF 原始复刻（karlchencuhk / VincentGaoHJ 的原始拆分文件）
    if name.startswith("FF因子_GitHub_"):
        return True
    # 过期回归/审计 JSON 日志（v17-v21）
    if re.match(r'^(v17|v18|v19|v20|v21)_.*\.json$', name):
        return True
    if name in ("FF因子_GitHub_下载报告.json","FF因子_GitHub_下载报告.txt"):
        return True
    return False

# JSON 保留（不归档）
json_keep = {
    "v22_recalc_summary.json","v22_strict_fixes_results.json",
    "survivorship_real_correction.json","final_regression_results.json",
    "final_verification_v2.json","regression_results_final.json",
    "data_quality_report_final.json","project_audit_report.json",
    "ra_purify_results.json","oos_multi_split_results.json","data_coverage_check_v20.json",
}
# 若根目录存在 v23* 也保留
for f in os.listdir(DATA):
    if re.match(r'^v23.*\.json$', f):
        json_keep.add(f)

# ---------- 执行 ----------
root_files = [f for f in os.listdir(DATA) if os.path.isfile(os.path.join(DATA,f))]
subdirs = [f for f in os.listdir(DATA) if os.path.isdir(os.path.join(DATA,f))]

plan_canonical = []   # (old, new)
plan_archive = []     # (old, new)
plan_keep_json = []
plan_unhandled = []

for f in root_files:
    old = os.path.join(DATA, f)
    if f in canonical:
        layer, newname = canonical[f]
        dst = os.path.join(DATA, layer, newname)
        plan_canonical.append((old, dst))
    elif f in json_keep:
        plan_keep_json.append(f)  # 留在根（或并入 L4 结果）；此处留根
    elif should_archive(f):
        dst = os.path.join(DATA, "无用数据", f)
        plan_archive.append((old, dst))
    else:
        plan_unhandled.append(f)

# FF5因子 子目录合并
for fname,(layer,newname) in ff5_subdir_merge.items():
    src = os.path.join(DATA, "FF5因子", fname)
    if os.path.isfile(src):
        plan_canonical.append((src, os.path.join(DATA, layer, newname)))

# ifind下载 整目录归档
if "ifind下载" in subdirs:
    plan_archive.append((os.path.join(DATA,"ifind下载"),
                         os.path.join(DATA,"无用数据","ifind下载")))

def do_move(old, dst):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    if os.path.exists(dst):
        print(f"  [SKIP 已存在] {dst}")
        return
    if DRY:
        print(f"  [DRY] {old}\n        -> {dst}")
    else:
        shutil.move(old, dst)
        print(f"  [MOVE] {os.path.basename(old)} -> {dst}")

print("="*70)
print(f"DRY_RUN={DRY}  BASE={DATA}")
print("="*70)
print(f"\n### 规范保留（移入分层中文名）: {len(plan_canonical)} 个")
for old,dst in plan_canonical:
    do_move(old,dst)

print(f"\n### 归档到 无用数据: {len(plan_archive)} 项")
for old,dst in plan_archive:
    do_move(old,dst)

print(f"\n### JSON 结果保留（留根）: {len(plan_keep_json)} 个")
for f in plan_keep_json:
    print("   ", f)

print(f"\n### 未处理（需人工确认）: {len(plan_unhandled)} 个")
for f in sorted(plan_unhandled):
    print("   ?", f)

# manifest
manifest = {
    "canonical": [(os.path.basename(o), d) for o,d in plan_canonical],
    "archive": [(os.path.basename(o) if os.path.isfile(o) else os.path.basename(o)+"/", d) for o,d in plan_archive],
    "keep_json": plan_keep_json,
    "unhandled": sorted(plan_unhandled),
}
if not DRY:
    with open(os.path.join(DATA,"_reorg_manifest.json"),"w",encoding="utf-8") as fp:
        json.dump(manifest, fp, ensure_ascii=False, indent=2)
    print("\nManifest written: 数据\\_reorg_manifest.json")
