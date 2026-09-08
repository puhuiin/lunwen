# -*- coding: utf-8 -*-
"""步骤 01 — L1 背景特征层
指标：mgr_total_tenure_v2(经理任职天数), log_fund_age(ln成立年数),
      控制变量 gender/education/CFA/school(取任职最久经理的个人特征)。
数据：L1_背景特征层/基金经理任职信息.csv(宽表→经理映射), 基金详细信息_最终版.csv(成立日), 基金经理信息_最终版.csv(个人特征)。
输出：output/L1_背景特征.csv
"""
import os
import lib_metrics as M

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
os.makedirs(OUT, exist_ok=True)


def main():
    sk = M.load_skeleton()
    print(">> [01] L1 背景特征：读取骨架", len(sk), "行")
    ten = M.calc_manager_tenure(sk)
    age = M.calc_fund_age(sk)
    cv = M.calc_control_vars(sk)
    out = (sk.merge(ten, on=["fund_code", "report_date"], how="left")
              .merge(age, on=["fund_code", "report_date"], how="left")
              .merge(cv, on=["fund_code", "report_date"], how="left"))
    out.to_csv(os.path.join(OUT, "L1_背景特征.csv"), index=False, encoding="utf-8-sig")
    print("   写出 output/L1_背景特征.csv:", out.shape)


if __name__ == "__main__":
    main()
