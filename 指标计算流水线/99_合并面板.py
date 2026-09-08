# -*- coding: utf-8 -*-
"""步骤 99 — 合并面板（最终产出）
把各层输出按观测索引 [fund_code, report_date] 左拼接成一张完整的「主分析面板_重建.csv」。
对齐顺序：00 骨架 → L1 → L2 → L3 → L4 → L5。
控制变量 gender/education/CFA/school 在 L1 已按 fund_code 铺满到该基金所有季度。
输出：output/主分析面板_重建.csv
"""
import os
import pandas as pd
import lib_metrics as M

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
os.makedirs(OUT, exist_ok=True)

# 各层产物中需要保留进最终面板的列（去掉中间辅助列）
KEEP = {
    "L1_背景特征.csv": ["fund_code", "report_date", "mgr_total_tenure_v2", "log_fund_age",
                      "gender", "education", "CFA", "school"],
    "L2_持仓偏离.csv": ["fund_code", "report_date", "AS_improved", "ICI", "industry_hhi",
                      "ICI_raw", "industry_hhi_raw", "ISDI"],
    "L3_交易执行.csv": ["fund_code", "report_date", "SDI",
                     "TO_two_sided", "OCI_two_sided", "total_buy", "total_sell"],
    "L4_风险应对.csv": ["fund_code", "report_date", "ARG", "return_volatility"],
    "L5_认知偏差.csv": ["fund_code", "report_date", "de", "pgr", "plr", "lsv", "risk_asym",
                       "n_gain", "n_loss"],
    "L6_因变量.csv": ["fund_code", "report_date", "quarter_return", "future_return",
                     "excess_return", "RG", "abs_return",
                     "ff3_adj_return", "ff4_adj_return", "ff5_adj_return",
                     "MKT_excess", "SMB", "HML", "MOM", "rf",
                     "ff5_MKT_excess", "ff5_SMB", "ff5_HML", "ff5_RMW", "ff5_CMA", "ff5_RF"],
}


def main():
    sk = M.load_skeleton()[["fund_code", "year", "quarter", "report_date"]]
    print(">> [99] 合并面板：骨架", len(sk), "行")

    base = sk
    for fname, cols in KEEP.items():
        df = pd.read_csv(os.path.join(OUT, fname), encoding="utf-8-sig")
        df = df[[c for c in cols if c in df.columns]]
        df = df.drop_duplicates(["fund_code", "report_date"])  # 防止右表重复键导致拼接爆炸
        # CSV 读回后 report_date 为字符串，骨架为 datetime64 → 统一为 datetime 再拼接
        df["report_date"] = pd.to_datetime(df["report_date"], errors="coerce")
        base = base.merge(df, on=["fund_code", "report_date"], how="left")
        print(f"   合并 {fname}: {base.shape}")

    # 独立并入 avg_aum（基金规模，亿元）：取自基金规模历史_批量.csv 的 net_asset，
    # 与 TO 的 200 只子集解耦，恢复全样本 400 只规模控制变量（~98% 覆盖）。
    aum = M.calc_avg_aum()
    aum["report_date"] = pd.to_datetime(aum["report_date"], errors="coerce")
    n0 = base["avg_aum"].notna().sum() if "avg_aum" in base.columns else 0
    base = base.merge(aum, on=["fund_code", "report_date"], how="left")
    print(f"   并入 avg_aum（规模）: 非空行 {n0} -> {base['avg_aum'].notna().sum()}")

    base = base.sort_values(["fund_code", "report_date"]).reset_index(drop=True)
    base.to_csv(os.path.join(OUT, "主分析面板_重建.csv"), index=False, encoding="utf-8-sig")
    print("   写出 output/主分析面板_重建.csv:", base.shape)

    # 覆盖度速览
    ind_cols = ["mgr_total_tenure_v2", "log_fund_age", "AS_improved", "ICI", "industry_hhi",
                "ICI_raw", "industry_hhi_raw", "ISDI",
                "SDI", "TO_two_sided", "OCI_two_sided", "ARG", "return_volatility", "de", "lsv", "risk_asym"]
    cov = base[ind_cols].notna().mean().round(3)
    print("\n   各指标非空覆盖比例：")
    for c in ind_cols:
        print(f"     {c:20s} {cov[c]*100:6.2f}%")


if __name__ == "__main__":
    main()
