# -*- coding: utf-8 -*-
"""步骤 05 — L5 认知偏差层
指标：de(处置效应, =PGR−PLR), lsv(羊群效应), risk_asym(风险不对称)。
数据：L2_持仓偏离层/基金持仓明细_全量修正版.csv(持仓快照),
      股价行情/个股月收益率_全量.csv(个股收益),
      L3_交易行为层/基金持仓变动_批量.csv(买卖方向→lsv),
      L4_风险应对层/基金季度收益.csv(季度收益→risk_asym)。
输出：output/L5_认知偏差.csv
"""
import os
import lib_metrics as M

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
os.makedirs(OUT, exist_ok=True)


def main():
    sk = M.load_skeleton()
    print(">> [05] L5 认知偏差：读取骨架", len(sk), "行")
    de = M.calc_de(only_612=True)        # de 仅在 6/12 月全持仓快照上计算
    lsv = M.calc_lsv()
    ra = M.calc_risk_asym()
    out = (sk
           .merge(de, on=["fund_code", "report_date"], how="left")
           .merge(lsv, on=["fund_code", "report_date"], how="left")
           .merge(ra, on=["fund_code", "report_date"], how="left"))
    out.to_csv(os.path.join(OUT, "L5_认知偏差.csv"), index=False, encoding="utf-8-sig")
    print("   写出 output/L5_认知偏差.csv:", out.shape)


if __name__ == "__main__":
    main()
