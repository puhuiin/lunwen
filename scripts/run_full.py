# -*- coding: utf-8 -*-
"""run_full.py — 一键复现：数据处理(流水线) → 回归分析
====================================================
用法（项目根目录，任意位置均可，路径由 __file__ 推导）：
    python run_full.py

等价于依次执行：
    python 指标计算流水线/run_all.py
    python L3_L1_regressions_HONEST_2026-08-14.py

产物：
    指标计算流水线/output/主分析面板_重建_含TOwind.csv   （论文用主面板）
    L3_L1_regression_HONEST_TOWind_2026-08-15.json       （回归结果）
"""
import os, sys, subprocess

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PL = os.path.join(HERE, "指标计算流水线")
STEPS = [
    (PL, "run_all.py"),
    (HERE, "L3_L1_regressions_HONEST_2026-08-14.py"),
]


def main():
    py = sys.executable
    print("=" * 64)
    print("基金经理行为分析研究 — 一键复现 (数据处理 -> 回归)")
    print("Python:", py)
    print("=" * 64)
    for cwd, script in STEPS:
        path = os.path.join(cwd, script)
        print("\n>>> 运行 %s  (cwd=%s)" % (script, cwd))
        t0 = __import__("time").time()
        rc = subprocess.run([py, path], cwd=cwd).returncode
        dt = __import__("time").time() - t0
        if rc != 0:
            print("!! %s 失败 (返回码 %d)，中止。" % (script, rc))
            sys.exit(rc)
        print("   OK %s 完成 (%.1fs)" % (script, dt))
    print("\n" + "=" * 64)
    print("全部完成。")
    print("  论文面板: 指标计算流水线/output/主分析面板_重建_含TOwind.csv")
    print("  回归JSON: L3_L1_regression_HONEST_TOWind_2026-08-15.json")
    print("=" * 64)


if __name__ == "__main__":
    main()
