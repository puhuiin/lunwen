# -*- coding: utf-8 -*-
"""步骤 00 — 构建面板骨架（观测索引）
由「基金净值历史_全量.csv」的净值覆盖**派生**观测索引 (fund_code, year, quarter, report_date)：
凡能算出季度收益的 (基金,季度) 即纳入研究样本（彻底脱离论文原始面板/元面板）。
注意：只取索引，不含任何指标取值；report_date = 季度末 + 1 天（面板约定）。
输出：output/00_面板骨架.csv
"""
import os
import lib_metrics as M

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
os.makedirs(OUT, exist_ok=True)


def main():
    sk = M.load_skeleton()
    print(f">> [00] 面板骨架：{len(sk)} 行, {sk['fund_code'].nunique()} 只基金")
    sk.to_csv(os.path.join(OUT, "00_面板骨架.csv"), index=False, encoding="utf-8-sig")
    print("   写出 output/00_面板骨架.csv")


if __name__ == "__main__":
    main()
