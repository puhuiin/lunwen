# -*- coding: utf-8 -*-
"""步骤 04 — L4 风险应对层
指标：ARG(主动风险增益), return_volatility(收益波动率)。
数据：L4_风险应对层/基金净值历史_全量.csv(基金月收益),
      L2_持仓偏离层/基金持仓明细_全量修正版.csv(持仓权重快照),
      股价行情/个股月收益率_全量.csv(个股月收益),
      L4_风险应对层/基金季度收益.csv(季度收益→滚动波动率)。
输出：output/L4_风险应对.csv
"""
import os
import lib_metrics as M

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
os.makedirs(OUT, exist_ok=True)


def main():
    sk = M.load_skeleton()
    print(">> [04] L4 风险应对：读取骨架", len(sk), "行")
    arg = M.calc_arg()
    rv = M.calc_return_volatility()
    out = (sk
           .merge(arg, on=["fund_code", "report_date"], how="left")
           .merge(rv, on=["fund_code", "report_date"], how="left"))
    out.to_csv(os.path.join(OUT, "L4_风险应对.csv"), index=False, encoding="utf-8-sig")
    print("   写出 output/L4_风险应对.csv:", out.shape)


if __name__ == "__main__":
    main()
