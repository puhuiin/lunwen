# -*- coding: utf-8 -*-
import os, shutil, json, re

BASE = r"D:\Desktop\基金经理行为分析研究"
DATA = os.path.join(BASE, "数据")
DRY = False

# ----------------- 规范保留集（旧名 -> (目标子文件夹, 中文新名)）-----------------
canonical = {
    # L4 风险应对层
    # 〔2026-08-14 治理〕mvp_panel_v22 / _v2 为模拟占位旧 token，对应源已删除，移除映射。
    # "mvp_panel_v22.csv": ("L4_风险应对层","主分析面板_修正版.csv"),
    # "mvp_panel_v2.csv": ("L4_风险应对层","主分析面板_旧版v2.csv"),
    "mvp_panel_v20.csv": ("L4_风险应对层","预处理面板_v20_诊断用.csv"),
    "mvp_panel_repaired.csv": ("L4_风险应对层","主分析面板_修复版.csv"),
    "mvp_regression_v2.csv": ("L4_风险应对层","主回归结果_v2.csv"),
    "double_sort_AS_ICI.csv": ("L4_风险应对层","双重排序AS_ICI结果.csv"),
    "spec_curve_results.csv": ("L4_风险应对层","规格曲线结果.csv"),
    "fund_nav_all.csv": ("L4_风险应对层","基金净值历史_全量.csv"),
    "基金净值历史_全量API.csv": ("L4_风险应对层","基金净值历史_API版.csv"),
    "基金排名_匹配_v2.csv": ("L4_风险应对层","基金排名_匹配.csv"),
    "基金规模变动_全市场.csv": ("L4_风险应对层","基金规模变动_全市场.csv"),
    "fund_quarterly_returns_v20.csv": ("L4_风险应对层","基金季度收益.csv"),
    "mvp_panel_v20_liquidated_sim.csv": ("L4_风险应对层","生存偏差_清盘基金面板模拟.csv"),
    "清盘基金净值_iFinD_merged.csv": ("L4_风险应对层","清盘基金净值_iFinD合并.csv"),
    "清盘基金净值_iFinD_panel.csv": ("L4_风险应对层","清盘基金净值_iFinD面板.csv"),
    "清盘候选_偏股基金列表.csv": ("L4_风险应对层","清盘候选基金列表.csv"),
    "fund_basicinfo_liquidated_sim.csv": ("L4_风险应对层","清盘基金基础信息.csv"),
    "v23_full_analysis_results.json": ("L4_风险应对层","最终结果_v23_全分析.json"),
    "v23_ps_results.json": ("L4_风险应对层","最终结果_v23_PS.json"),
    "v23_reanalysis_results.json": ("L4_风险应对层","最终结果_v23_再分析.json"),
    "v23b_consistency_check.json": ("L4_风险应对层","最终结果_v23b_一致性检验.json"),
    "v23c_l5_source_trace.json": ("L4_风险应对层","最终结果_v23c_L5来源追溯.json"),
    "v23d_clean_sample.json": ("L4_风险应对层","最终结果_v23d_清洗样本.json"),
    "v23_identification_fix_results.json": ("L4_风险应对层","最终结果_v23_识别修正.json"),
    "v23_timing_control_results.json": ("L4_风险应对层","最终结果_v23_时机控制.json"),
    # L5 认知行为层
    "l5_de_v22.csv": ("L5_认知行为层","处置效应DE指标_修正版.csv"),
    "l5_lsv_v21.csv": ("L5_认知行为层","羊群行为LSV指标.csv"),
    "l5_lsv_v20.csv": ("L5_认知行为层","羊群行为LSV指标_诊断用.csv"),
    "l5_risk_asym_v20.csv": ("L5_认知行为层","风险偏好不对称RA指标.csv"),
    "l5_de_fixed.csv": ("L5_认知行为层","处置效应DE修正_诊断用.csv"),
    "ra_purification_ff5.csv": ("L5_认知行为层","RA因子正交纯化结果.csv"),
    "l5_correlation_matrix.csv": ("L5_认知行为层","L5指标相关性矩阵.csv"),
    "l5_descriptive_stats.csv": ("L5_认知行为层","L5指标描述统计.csv"),
    "l5_vif_results.csv": ("L5_认知行为层","L5指标VIF检验.csv"),
    # L2 持仓偏离层
    "fund_holdings_full_v2.csv": ("L2_持仓偏离层","基金持仓明细_全量修正版.csv"),
    "fund_holdings_full.csv": ("L2_持仓偏离层","基金持仓明细_初版.csv"),
    "fund_holdings_top10.csv": ("L2_持仓偏离层","基金前十重仓.csv"),
    "基金行业配置_全量.csv": ("L2_持仓偏离层","基金行业配置_全量.csv"),
    "基金行业配置_批量.csv": ("L2_持仓偏离层","基金行业配置_批量.csv"),
    "as_200_funds_v2.csv": ("L2_持仓偏离层","主动偏离AS指标_200基金.csv"),
    "ici_200_funds_v2.csv": ("L2_持仓偏离层","隐性交易ICI指标_200基金.csv"),
    "行业HHI_计算值.csv": ("L2_持仓偏离层","行业集中度HHI.csv"),
    "基准成分股权重_真实.csv": ("L2_持仓偏离层","沪深300成分股权重_真实.csv"),
    "holdings_coverage_matrix.csv": ("L2_持仓偏离层","持仓覆盖率矩阵.csv"),
    "申万一级行业信息.csv": ("L2_持仓偏离层","申万一级行业分类.csv"),
    "申万行业指数收益.csv": ("L2_持仓偏离层","申万行业指数收益.csv"),
    "股票行业映射.csv": ("L2_持仓偏离层","股票行业映射.csv"),
    "风格指数日线数据.csv": ("L2_持仓偏离层","风格指数日线.csv"),
    "风格指数季度收益.csv": ("L2_持仓偏离层","风格指数季度收益.csv"),
    "北向资金历史.csv": ("L2_持仓偏离层","北向资金历史.csv"),
    "行业资金流_AKShare.csv": ("L2_持仓偏离层","行业资金流.csv"),
    # L3 交易行为层
    "rg_200_funds_v2.csv": ("L3_交易行为层","收益缺口RG指标_200基金.csv"),
    "基金换手率_补全.csv": ("L3_交易行为层","基金换手率.csv"),
    "基金持仓变动_批量.csv": ("L3_交易行为层","基金持仓变动_批量.csv"),
    # L1 背景特征层
    "经理信息_最终v2.csv": ("L1_背景特征层","基金经理信息_最终版.csv"),
    "经理任职信息.csv": ("L1_背景特征层","基金经理任职信息.csv"),
    "基金详细信息_v4_fixed.csv": ("L1_背景特征层","基金详细信息_最终版.csv"),
    "基金规模历史_批量.csv": ("L1_背景特征层","基金规模历史_批量.csv"),
    # 基金基础信息
    "fund_list_200.csv": ("基金基础信息","基金列表_200只样本.csv"),
    "基金经理_全量.csv": ("基金基础信息","基金经理名单_全量.csv"),
    "fund_industry_200.csv": ("基金基础信息","基金行业映射_200只.csv"),
    "index_000300_constituents.csv": ("基金基础信息","沪深300成分股.csv"),
    "index_000905_constituents.csv": ("基金基础信息","中证500成分股.csv"),
    "index_000905_monthly.csv": ("基金基础信息","中证500指数月度.csv"),
    "index_000852_monthly.csv": ("基金基础信息","中证1000指数月度.csv"),
    "基金评级_fund_rating_all.csv": ("基金基础信息","基金评级全量.csv"),
    "基金分红排行.csv": ("基金基础信息","基金分红排行.csv"),
    "基金申购状态_含费率.csv": ("基金基础信息","基金申购状态含费率.csv"),
    "同花顺基金费率.csv": ("基金基础信息","基金费率_同花顺.csv"),
    "基金市场规模走势.csv": ("基金基础信息","基金市场规模走势.csv"),
    "基金公司规模排名.csv": ("基金基础信息","基金公司规模排名.csv"),
    "市场指数历史数据.csv": ("基金基础信息","市场指数历史数据.csv"),
    "基金每日数据_AKShare.csv": ("基金基础信息","基金每日数据_AKShare.csv"),
    "全部基金列表_含清盘.csv": ("基金基础信息","全部基金列表_含清盘.csv"),
    # 股价行情
    "stock_prices_full.csv": ("股价行情","个股日行情_全量.csv"),
    "stock_monthly_returns_full.csv": ("股价行情","个股月收益率_全量.csv"),
    "stock_monthly_returns.csv": ("股价行情","个股月收益率_初版.csv"),
    # 宏观数据
    "宏观_CPI.csv": ("宏观数据","宏观_CPI.csv"),
    "宏观_GDP.csv": ("宏观数据","宏观_GDP.csv"),
    "宏观_LPR.csv": ("宏观数据","宏观_LPR.csv"),
    "宏观_M2.csv": ("宏观数据","宏观_M2.csv"),
    "宏观_PMI.csv": ("宏观数据","宏观_PMI.csv"),
    "宏观_PPI.csv": ("宏观数据","宏观_PPI.csv"),
    "宏观_外汇储备.csv": ("宏观数据","宏观_外汇储备.csv"),
    "宏观_社融.csv": ("宏观数据","宏观_社融.csv"),
    "国债收益率_AKShare.csv": ("宏观数据","国债收益率.csv"),
    "中国国债收益率曲线_AKShare.csv": ("宏观数据","国债收益率曲线.csv"),
    # FF因子
    "ff_factors_complete.csv": ("FF因子","FF因子_合并完整版.csv"),
    # 补充数据源（原始下载/替代源，保留不删）
    "开放式基金排行_东财.csv": ("补充数据源","开放式基金排行_东财.csv"),
    "开放式基金排行_混合型.csv": ("补充数据源","开放式基金排行_混合型.csv"),
    "雪球基金信息.csv": ("补充数据源","雪球基金信息.csv"),
    "基金名称大全_AKShare.csv": ("补充数据源","基金名称大全_AKShare.csv"),
    "基金经理大全_AKShare.csv": ("补充数据源","基金经理大全_AKShare.csv"),
    "基金经理列表_em.csv": ("补充数据源","基金经理列表_em.csv"),
    "经理信息_GitHub提取.csv": ("补充数据源","经理信息_GitHub提取.csv"),
    "经理个人信息_补充.csv": ("补充数据源","经理个人信息_补充.csv"),
    "经理学历_爬取v2.csv": ("补充数据源","经理学历_爬取v2.csv"),
    "经理ID映射.csv": ("补充数据源","经理ID映射.csv"),
    "顶流经理_GitHub资料.csv": ("补充数据源","顶流经理_GitHub资料.csv"),
    "基金经理变更公告_批量.csv": ("补充数据源","基金经理变更公告_批量.csv"),
    # 文档与元数据（清单/报告，保留不删）
    "数据文件清单.csv": ("文档与元数据","数据文件清单.csv"),
    "数据完整性报告_final.json": ("文档与元数据","数据完整性报告_final.json"),
}

# ----------------- 明确归档（无用数据）-----------------
archive_exact = set()
for v in ["v3","v4","v5","v6","v7","v8","v9","v10","v11","v12","v14","v16",
          "v17","v18","v19","v21","final"]:
    archive_exact.add(f"mvp_panel_{v}.csv")
for v in ["v19","v20","v21"]:
    archive_exact.add(f"l5_de_{v}.csv")
archive_exact.update(["fixed_fund_level_v19.csv","fixed_fund_level_v20.csv","fixed_fund_level_v21.csv",
                      "l5_lsv_v19.csv","l5_de.csv","l5_lsv.csv","l5_risk_asym.csv","l5_de_fixed_fund_level.csv"])
archive_exact.update(["基金详细信息.csv","基金详细信息_v2.csv","基金详细信息_v3.csv","基金详细信息_v4.csv","基金详细信息_efinance.csv"])
archive_exact.update(["经理信息_v6.csv","经理信息_v7.csv","经理信息_合并_v5.csv","经理信息_合并_v6.csv"])
archive_exact.update(["基金换手率_计算值.csv","基金换手率_v3.csv","基金换手率_v4.csv","待补充_基金换手率.csv",
                      "换手率_合并_v5.csv","换手率_按基金_v5.csv","基金换手率_持仓变动计算.csv"])
archive_exact.update(["基金持仓_补充.csv","基金持仓_补充v2.csv","基金持仓_efinance.csv"])
archive_exact.update(["基金行业配置_补充.csv","基金行业配置_AKShare.csv","申万一级行业信息_AKShare.csv","申万一级行业信息_新版.csv",
                      "行业HHI_v5.csv","行业HHI_按基金_v5.csv"])
archive_exact.update(["基金净值历史_API.csv","基金净值_补充.csv","基金排名_匹配.csv"])
archive_exact.update(["fund_list.csv","fund_managers.csv","fund_managers_full.csv","fund_industry.csv","fund_industry_all.csv",
                      "fund_basic_info_v19.csv"])
archive_exact.update(["经理个人信息_抓取.csv","经理档案_深度爬取.csv","经理学历_改进.csv","待补充_经理个人信息.csv",
                      "akshare_全部基金列表_含类型.csv","AKShare_基金经理列表.csv","efinance_基金经理数据.csv",
                      "efinance_基金基本信息_测试.csv","fundManagers_GitHub.xlsx",
                      "fund_list_GitHub.json","managers_GitHub.json"])
archive_exact.update(["数据完整性报告.csv","数据完整性报告_v6.txt","数据完整性报告_最终.txt"])
archive_exact.update(["数据完整性报告_v10.json","数据完整性报告_v11.json","数据完整性报告_v12.json",
                      "mvp_v14_results.json","mvp_v15_advanced_results.json","mvp_regression_results.json",
                      "spec_curve_summary.json","学术优化结果.json"])

def should_archive(name):
    if name in archive_exact: return True
    if name.startswith("FF因子_GitHub_"): return True
    if re.match(r'^(v17|v18|v19|v20|v21)_.*\.json$', name): return True
    if name in ("FF因子_GitHub_下载报告.json","FF因子_GitHub_下载报告.txt"): return True
    return False

json_keep = {
    "v22_recalc_summary.json","v22_strict_fixes_results.json","survivorship_real_correction.json",
    "final_regression_results.json","final_verification_v2.json","regression_results_final.json",
    "data_quality_report_final.json","project_audit_report.json","ra_purify_results.json",
    "oos_multi_split_results.json","data_coverage_check_v20.json",
}
for f in os.listdir(DATA):
    if re.match(r'^v23.*\.json$', f): json_keep.add(f)

ff5_subdir_merge = {
    "FF5_monthly.csv": ("FF因子","FF5月度因子.csv"),
    "FF5_daily.csv": ("FF因子","FF5日度因子.csv"),
}

# ----------------- 执行 -----------------
root_files = [f for f in os.listdir(DATA) if os.path.isfile(os.path.join(DATA,f))]
subdirs = [f for f in os.listdir(DATA) if os.path.isdir(os.path.join(DATA,f))]

plan_canonical=[]; plan_archive=[]; plan_meta_json=[]; plan_fallback=[]

for f in root_files:
    old=os.path.join(DATA,f)
    if f in canonical:
        layer,nn=canonical[f]; plan_canonical.append((old,os.path.join(DATA,layer,nn)))
    elif f in json_keep:
        plan_meta_json.append(f)  # 留在根（最终结果）
    elif should_archive(f):
        plan_archive.append((old,os.path.join(DATA,"无用数据",f)))
    else:
        plan_fallback.append((old,os.path.join(DATA,"文档与元数据",f)))  # 安全兜底：不删

for fname,(layer,nn) in ff5_subdir_merge.items():
    src=os.path.join(DATA,"FF5因子",fname)
    if os.path.isfile(src): plan_canonical.append((src,os.path.join(DATA,layer,nn)))

if "ifind下载" in subdirs:
    plan_archive.append((os.path.join(DATA,"ifind下载"),os.path.join(DATA,"无用数据","ifind下载")))

def do_move(old,dst):
    os.makedirs(os.path.dirname(dst),exist_ok=True)
    if os.path.exists(dst):
        print(f"  [SKIP 已存在] {os.path.basename(old)}"); return
    if DRY: print(f"  [DRY] {os.path.basename(old)}\n        -> {dst}")
    else:
        shutil.move(old,dst); print(f"  [OK] {os.path.basename(old)}")

print("="*60); print(f"DRY_RUN={DRY}"); print("="*60)
print(f"\n### 规范保留（分层中文名）: {len(plan_canonical)}")
for o,d in plan_canonical: do_move(o,d)
print(f"\n### 归档无用数据: {len(plan_archive)}")
for o,d in plan_archive: do_move(o,d)
print(f"\n### 根留最终结果JSON: {len(plan_meta_json)}")
for f in plan_meta_json: print("   ",f)
print(f"\n### 兜底→文档与元数据: {len(plan_fallback)}")
for o,d in plan_fallback: do_move(o,d)

# 清理空目录
if not DRY:
    for sd in ["FF5因子"]:
        p=os.path.join(DATA,sd)
        if os.path.isdir(p) and not os.listdir(p):
            os.rmdir(p); print(f"  [RMDIR] {sd}")

manifest={"canonical":[(os.path.basename(o),d) for o,d in plan_canonical],
          "archive":[os.path.basename(o) if os.path.isfile(o) else os.path.basename(o)+"/" for o,d in plan_archive],
          "meta_json":plan_meta_json,
          "fallback":[os.path.basename(o) for o,d in plan_fallback]}
if not DRY:
    with open(os.path.join(DATA,"_reorg_manifest.json"),"w",encoding="utf-8") as fp:
        json.dump(manifest,fp,ensure_ascii=False,indent=2)
    print("\nManifest -> 数据\\_reorg_manifest.json")
