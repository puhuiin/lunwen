"""
盘点已成功下载的妙想MD文件，提取全持仓记录，形成部分数据集。
扫描目录：数据/外部数据/mx_raw（含子目录）及妙想skill输出目录。
"""
import os
import re
import glob
import sys

sys.path.insert(0, r"C:\Users\26955\.workbuddy\skills\mx-finance-data\scripts")
import mx_batch_fetch as mb

SCAN_DIRS = [
    r"D:\Desktop\基金经理行为分析研究\数据\外部数据\mx_raw",
    r"C:\Users\26955\.workbuddy\skills\mx-finance-data\scripts\miaoxiang\mx_finance_data",
]

def main():
    all_rows = []
    scanned = 0
    for d in SCAN_DIRS:
        if not os.path.exists(d):
            continue
        for md in glob.glob(os.path.join(d, "**", "*.md"), recursive=True):
            # 跳过 progress/说明文件
            if "说明" in md or "README" in md:
                continue
            rows = mb.parse_md(md)
            if rows:
                all_rows.extend(rows)
                scanned += 1
    print(f"扫描MD文件（有数据）: {scanned}")
    print(f"总记录（原始）: {len(all_rows)}")

    import pandas as pd
    df = pd.DataFrame(all_rows)
    if len(df) == 0:
        print("无数据")
        return
    # 去重
    df = df.drop_duplicates(subset=["fund_code", "stock_code", "report_date"])
    print(f"去重后记录: {len(df)}")
    print(f"基金数: {df.fund_code.nunique()}")
    print(f"覆盖报告期: {sorted(df.report_date.dropna().unique())}")
    # 每只基金期数
    cov = df.groupby("fund_code")["report_date"].nunique().sort_values(ascending=False)
    print("\n每只基金覆盖期数（前15）:")
    for fc, n in cov.head(15).items():
        pers = df[df.fund_code == fc].report_date.min(), df[df.fund_code == fc].report_date.max()
        print(f"  {fc}: {n} 期 ({pers[0]}~{pers[1]})")
    # 保存
    out = r"D:\Desktop\基金经理行为分析研究\数据\外部数据\mx_holdings_partial.csv"
    df.to_csv(out, index=False, encoding="utf-8-sig")
    print(f"\n已保存部分数据集 -> {out}")

if __name__ == "__main__":
    main()
