# -*- coding: utf-8 -*-
"""run_all.py - 顺序执行整套「数据处理」流水线，产出论文用主面板
=================================================================
执行顺序（任一步骤失败即停止并报告）：
    07_整合持仓数据.py  构建 v2 全持仓（02/03/04 的依赖，必须先跑）
    00_构建面板骨架.py  观测索引（fund_code x 季度）
    01_L1_背景特征.py   经理背景/控制变量
    02_L2_持仓偏离.py   ActiveShare / 行业集中度
    03_L3_交易执行.py   SDI / 换手率(双边) / OCI
    04_L4_风险应对.py   ARG / 收益波动
    05_L5_认知偏差.py   DE / PGR / PLR / LSV / 风险不对称
    06_因变量.py        季度收益 / 超额收益 / FF 因子
    99_合并面板.py      合并为 主分析面板_重建.csv
    07b_并入Wind换手率.py  并入图书馆 Wind 双边换手率 -> 主分析面板_重建_含TOwind.csv

所有路径均由各脚本内部基于 __file__ 推导（可移植），本机任意目录均可运行：
    python run_all.py
最终论文面板：output/主分析面板_重建_含TOwind.csv
"""
import os
import sys
import subprocess
import time

STEPS = [
    "07_整合持仓数据.py",
    "00_构建面板骨架.py",
    "01_L1_背景特征.py",
    "02_L2_持仓偏离.py",
    "03_L3_交易执行.py",
    "04_L4_风险应对.py",
    "05_L5_认知偏差.py",
    "06_因变量.py",
    "99_合并面板.py",
    "07b_并入Wind换手率.py",
]


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    py = sys.executable
    print("=" * 60)
    print("基金经理行为指标计算流水线 - 顺序执行")
    print("Python:", py)
    print("=" * 60)
    for i, step in enumerate(STEPS, 1):
        path = os.path.join(here, step)
        print()
        print("[%d/%d] 运行 %s ..." % (i, len(STEPS), step))
        t0 = time.time()
        rc = subprocess.run([py, path], cwd=here).returncode
        dt = time.time() - t0
        if rc != 0:
            print("!! %s 执行失败 (返回码 %d)，流水线中止。" % (step, rc))
            sys.exit(rc)
        print("   OK 完成（%.1fs）" % dt)
    print()
    print("=" * 60)
    print("全部完成。最终论文面板：output/主分析面板_重建_含TOwind.csv")
    print("=" * 60)


if __name__ == "__main__":
    main()
