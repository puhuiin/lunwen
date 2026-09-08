import os, re, json

DATA = r"D:\Desktop\基金经理行为分析研究\数据"
# hard-coded references found in 代码/ (search results)
code_refs = {
    "mvp_panel_v20.csv","l5_lsv_v20.csv","l5_de_fixed.csv",
    "fund_holdings_full.csv","fund_holdings_top10.csv","fund_nav_all.csv",
    "index_000300_constituents.csv","fund_list_200.csv","fund_industry_200.csv",
    "fund_industry_all.csv","index_*.csv","fund_managers.csv","stock_monthly_returns.csv",
    "fund_holdings_full_v2.csv","l5_de_v22.csv","mvp_panel_v22.csv",
    "mvp_panel_v2.csv","mvp_regression_v2.csv","ra_purification_ff5.csv",
    "spec_curve_results.csv","ici_200_funds_v2.csv","as_200_funds_v2.csv",
    "rg_200_funds_v2.csv","double_sort_AS_ICI.csv","mvp_data.csv",
    "sw_industry_list.csv","em_industry_list.csv","industry_monthly_returns.csv",
    "fund_holdings_*.csv","sw_industry_index_hist.csv","em_industry_*_monthly.csv",
    "sw_all_industry_monthly.csv","fund_holdings_*_2024.csv","fund_holdings_*_2023_semi.csv",
    "mx_holdings_partial.csv","mx_full_holdings.csv","_target_funds_from_de.csv",
    "fund_list_200.csv"
}

def norm(f):
    return f.lower()

# collect root-level files (non-recursive)
root_files = [f for f in os.listdir(DATA) if os.path.isfile(os.path.join(DATA,f))]
# also subfolder names
subdirs = [f for f in os.listdir(DATA) if os.path.isdir(os.path.join(DATA,f))]

def base_group(name):
    n = name
    # strip trailing _vNN or _vNNN
    n = re.sub(r'_v\d+\.csv$', '', n, flags=re.I)
    n = re.sub(r'_v\d+$', '', n, flags=re.I)
    n = re.sub(r'_fixed$', '', n, flags=re.I)
    n = re.sub(r'_final.*$', '', n, flags=re.I)
    n = re.sub(r'_最终.*$', '', n, flags=re.I)
    n = re.sub(r'_全量$', '', n, flags=re.I)
    n = re.sub(r'_合并.*$', '', n, flags=re.I)
    n = re.sub(r'_补充.*$', '', n, flags=re.I)
    n = re.sub(r'_补全$', '', n, flags=re.I)
    n = re.sub(r'_计算值$', '', n, flags=re.I)
    return n

groups = {}
for f in root_files:
    g = base_group(f)
    groups.setdefault(g, []).append(f)

# Sort groups by count desc, report
print(f"ROOT-LEVEL FILES: {len(root_files)}")
print(f"SUBDIRS: {subdirs}\n")
print("=== GROUPS (base -> variants) ===")
for g in sorted(groups, key=lambda k: -len(groups[k])):
    variants = sorted(groups[g])
    print(f"\n[{g}]  ({len(variants)} variants)")
    for v in variants:
        sz = os.path.getsize(os.path.join(DATA,v))/1e6
        ref = "*CODE*" if (v in code_refs or any(re.match(p.replace('*','.*'), v, re.I) for p in code_refs)) else ""
        print(f"    {v:55s} {sz:8.2f}MB  {ref}")
