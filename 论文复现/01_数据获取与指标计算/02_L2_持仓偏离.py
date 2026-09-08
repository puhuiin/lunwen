# -*- coding: utf-8 -*-
"""步骤 02 — L2 持仓偏离层
指标：AS_improved(主动份额), ICI(行业集中度偏差), industry_hhi(行业赫芬达尔)。
数据：L2_持仓偏离层/基金持仓明细_全量修正版.csv(基金权重),
      L2_持仓偏离层/基金行业配置_全量.csv(行业权重),
      L2_持仓偏离层/沪深300成分股权重_真实.csv + 基金基础信息/中证500成分股.csv(基准权重)。
输出：output/L2_持仓偏离.csv
"""
import os
import lib_metrics as M

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
os.makedirs(OUT, exist_ok=True)


def main():
    sk = M.load_skeleton()
    print(">> [02] L2 持仓偏离：读取骨架", len(sk), "行")
    AS = M.calc_active_share()
    ICI = M.calc_ici()
    HHI = M.calc_industry_hhi()
    ICI_raw = M.calc_ici_raw()
    HHI_raw = M.calc_industry_hhi_raw()
    ISDI = M.calc_isdi()
    out = (sk
           .merge(AS, on=["fund_code", "report_date"], how="left")
           .merge(ICI, on=["fund_code", "report_date"], how="left")
           .merge(HHI, on=["fund_code", "report_date"], how="left")
           .merge(ICI_raw, on=["fund_code", "report_date"], how="left")
           .merge(HHI_raw, on=["fund_code", "report_date"], how="left")
           .merge(ISDI, on=["fund_code", "report_date"], how="left"))
    out.to_csv(os.path.join(OUT, "L2_持仓偏离.csv"), index=False, encoding="utf-8-sig")
    print("   写出 output/L2_持仓偏离.csv:", out.shape)


if __name__ == "__main__":
    main()
