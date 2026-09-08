# -*- coding: utf-8 -*-
"""
一键全量复现主脚本.py
================================================================================
用途：端到端一键执行论文全部 12 张学术三线表与 3 张高精度插图的复现计算。
运行环境：Python 3.10+（需包含 pandas, numpy, scipy, statsmodels, matplotlib）
执行方式：python 一键全量复现主脚本.py
================================================================================
"""
import os, sys, time, subprocess

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
EMP_DIR = os.path.join(BASE_DIR, '02_实证回归与论文图表')
PYTHON_EXE = sys.executable

STEPS = [
    ('Step 01', '表 3：逐年分布与宏观环境描述', 'step01_表3_逐年描述统计.py'),
    ('Step 02', '表 4 & 表 5：25指标单变量回归与三因变量对照', 'step02_表4_表5_单变量与三因变量回归.py'),
    ('Step 03', '表 6：六维复合能力主回归模型', 'step03_表6_六维能力主回归.py'),
    ('Step 04', '表 8：改进主动份额 AS_improved 六道检验裁决', 'step04_表8_AS改进主动份额六道裁决.py'),
    ('Step 05', '表 9、10、11：群体画像与典型经理切面分析', 'step05_表9_表10_表11_群体与典型画像.py'),
    ('Step 06', '表 12：2025–2026 样本外 6 季度长周期盲测', 'step06_表12_样本外6季度长周期盲测.py'),
    ('Step 07', '稳健性检验：隔离 2026Q2 极端行情敏感性分析', 'step07_稳健性_剔除2026Q2极端季检验.py'),
    ('Step 08', '图 1、2、3：相关热力图、五分组柱状图、雷达图生成', 'step08_图1_图2_图3_高精度图表生成.py')
]

def main():
    print("=" * 80)
    print("《中国主动权益投资经理画像研究》论文实证结果全量自动化复现流水线")
    print(f"执行目录: {BASE_DIR}")
    print(f"Python 环境: {PYTHON_EXE}")
    print("=" * 80)

    start_total = time.time()
    success_count = 0

    for code, title, script_name in STEPS:
        script_path = os.path.join(EMP_DIR, script_name)
        if not os.path.exists(script_path):
            print(f"[-] {code} 脚本未找到: {script_path}")
            continue

        print(f"\n>>> 正在执行 {code} [{title}] ...")
        t0 = time.time()
        try:
            # Set UTF-8 encoding
            env = os.environ.copy()
            env['PYTHONIOENCODING'] = 'utf-8'
            res = subprocess.run([PYTHON_EXE, script_path], cwd=BASE_DIR, env=env, capture_output=True, text=True, encoding='utf-8', errors='ignore')
            cost = time.time() - t0
            if res.returncode == 0:
                print(f"[OK] {code} 运行成功 (耗时: {cost:.2f}s)")
                success_count += 1
            else:
                print(f"[FAIL] {code} 运行失败 (耗时: {cost:.2f}s)")
                print("--- 错误信息摘要 ---")
                err_lines = [l for l in res.stderr.splitlines() if l.strip()]
                for el in err_lines[-6:]:
                    print("   ", el)
        except Exception as e:
            print(f"[!] {code} 调用异常: {e}")

    total_cost = time.time() - start_total
    print("\n" + "=" * 80)
    print(f"复现流程执行完毕！成功: {success_count}/{len(STEPS)}, 总耗时: {total_cost:.2f}s")
    print("全量实证产物均已保存在 output/ 与 figures/ 目录下，对应数据与《论文初稿_2026-09-10_学术定稿版.docx》逐单元格对齐。")
    print("=" * 80)

if __name__ == '__main__':
    main()
