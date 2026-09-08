# -*- coding: utf-8 -*-
"""步骤 03 — L3 交易执行层
指标：SDI(风格漂移), TO_two_sided(双边换手率·含卖出侧, 已统一为主变量), OCI_two_sided(其离差)。
说明：自 2026-08-12 起「全部改用真·双边换手率 TO_two_sided」，单边 TO_calc/OCI 已移除。
数据：L3_交易行为层/基金换手率_双边_含卖出.csv(买入+卖出+平均净资产),
      L4_风险应对层/基金净值历史_全量.csv(算基金季收益),
      L2_持仓偏离层/风格指数季度收益.csv(4风格指数)。
输出：output/L3_交易执行.csv
"""
import os
import lib_metrics as M

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
os.makedirs(OUT, exist_ok=True)


def main():
    sk = M.load_skeleton()
    print(">> [03] L3 交易执行：读取骨架", len(sk), "行")
    twosided = M.calc_turnover_two_sided()
    sdi = M.calc_sdi(window=8)
    out = (sk
           .merge(twosided, on=["fund_code", "report_date"], how="left")
           .merge(sdi, on=["fund_code", "report_date"], how="left"))
    out.to_csv(os.path.join(OUT, "L3_交易执行.csv"), index=False, encoding="utf-8-sig")
    print("   写出 output/L3_交易执行.csv:", out.shape)


if __name__ == "__main__":
    main()
