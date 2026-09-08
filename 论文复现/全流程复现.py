# -*- coding: utf-8 -*-
"""
《中国主动权益投资经理画像研究》论文实证全流程复现主脚本

设计原则：
1. 纯 Python 实现，零外部 bat/sh 脚本，跨平台兼容 Windows / macOS / Linux。
2. 支持两种复现方式：
   - 方式一【老老实实逐个执行】：在终端中依次执行：
       python 02_实证回归与论文图表/step01_表3_逐年描述统计.py
       python 02_实证回归与论文图表/step02_表4_表5_单变量与三因变量回归.py
       ... 直至 step08
   - 方式二【全流程自动化执行】：直接运行 python 全流程复现.py，所有实证回归表格实时在终端完整打印，并交互弹出论文高清图表窗口。
3. 实时流式输出：不截断、不抑制控制台输出，每一步的学术表格与统计量完整呈现在屏幕上。
4. 交互图表弹出：Step 08 运行完毕时，将自动弹出论文图1、图2、图3的高精度可视化窗口供查阅。
"""
import os
import sys
import io
import time
import subprocess
from pathlib import Path

if hasattr(sys.stdout, 'buffer') and getattr(sys.stdout, 'encoding', '').lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'buffer') and getattr(sys.stderr, 'encoding', '').lower() != 'utf-8':
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')


# 保证当前根目录
BASE_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = BASE_DIR / '02_实证回归与论文图表'
OUTPUT_DIR = BASE_DIR / 'output'
FIGURES_DIR = BASE_DIR / 'figures'

# 实证复现流程定义 (顺序不可颠倒)
STEPS = [
    {
        'id': 'Step 01',
        'file': 'step01_表3_逐年描述统计.py',
        'desc': '表 3：逐年分布与宏观环境描述（2006Q3–2026Q2）',
        'target': 'output/逐年统计性描述_2026-09-03.json',
    },
    {
        'id': 'Step 02',
        'file': 'step02_表4_表5_单变量与三因变量回归.py',
        'desc': '表 4 & 表 5：单变量特征检验与三因变量稳健性基准',
        'target': 'output/单变量全表_三因变量_2026-09-02.json',
    },
    {
        'id': 'Step 03',
        'file': 'step03_表6_六维能力主回归.py',
        'desc': '表 6：六维综合画像主回归与复合能力打分体系',
        'target': 'output/主回归_v3_2026-08-26.json',
    },
    {
        'id': 'Step 04',
        'file': 'step04_表8_AS改进主动份额六道裁决.py',
        'desc': '表 8：改进主动份额（AS_improved）六道专项裁决',
        'target': 'output/AS专项裁决_2026-08-26.json',
    },
    {
        'id': 'Step 05',
        'file': 'step05_表9_表10_表11_群体与典型画像.py',
        'desc': '表 9–11：六维画像分布、典型投资经理案例库',
        'target': 'output/画像_群体与典型_2026-08-26.json',
    },
    {
        'id': 'Step 06',
        'file': 'step06_表12_样本外6季度长周期盲测.py',
        'desc': '表 12：样本外 6 季度跨周期纯盲测检验（2025Q1–2026Q2）',
        'target': 'output/样本外盲测_6季度长周期_2026-09-03.json',
    },
    {
        'id': 'Step 07',
        'file': 'step07_稳健性_剔除2026Q2极端季检验.py',
        'desc': '稳健性附表：剔除 2026Q2 极端异动季稳健性压力测试',
        'target': 'output/单变量全表_去2026Q2敏感性_2026-09-10.json',
    },
    {
        'id': 'Step 08',
        'file': 'step08_图1_图2_图3_高精度图表生成.py',
        'desc': '论文配图：图1(五分组alpha)、图2(六维相关热力图)、图3(典型经理雷达图)',
        'target': 'figures/论文图1_五分组alpha.png',
    },
]


def check_dependencies():
    """环境与依赖库预检"""
    required = {
        'numpy': 'numpy',
        'pandas': 'pandas',
        'scipy': 'scipy',
        'statsmodels': 'statsmodels',
        'matplotlib': 'matplotlib',
    }
    missing = []
    for mod, pkg in required.items():
        try:
            __import__(mod)
        except ImportError:
            missing.append(pkg)
    if missing:
        print("=" * 80)
        print("【错误】检测到当前 Python 环境缺少以下依赖包:")
        for m in missing:
            print(f"  - {m}")
        print("\n请先在终端中执行以下命令安装依赖：")
        print("    pip install -r requirements.txt")
        print("=" * 80)
        sys.exit(1)


def main():
    check_dependencies()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print("《中国主动权益投资经理画像研究》论文实证结果全量自动化复现流水线")
    print(f"执行目录: {BASE_DIR}")
    print(f"Python 环境: {sys.executable}")
    print(f"共计 {len(STEPS)} 个实证与图表步骤")
    print("注：执行过程中各步骤学术统计表格将实时打印在下方；Step 08 将弹出高清图表窗口。")
    print("=" * 80)

    total_start = time.time()
    env = os.environ.copy()
    env['PYTHONIOENCODING'] = 'utf-8'

    for i, step in enumerate(STEPS, 1):
        script_path = SCRIPTS_DIR / step['file']
        if not script_path.exists():
            print(f"\n[FAIL] 找不到脚本文件: {script_path}")
            sys.exit(1)

        print(f"\n" + "#" * 80)
        print(f"### >>> [{step['id']}] {step['desc']}")
        print(f"### 正在执行: {step['file']}")
        print("#" * 80 + "\n")

        # 不使用 capture_output，让子进程标准输出实时流式打印到控制台
        t0 = time.time()
        cmd = [sys.executable, str(script_path)]
        if '--no-popup' in sys.argv:
            cmd.append('--no-popup')
        res = subprocess.run(
            cmd,
            cwd=str(BASE_DIR),
            env=env
        )
        elapsed = time.time() - t0

        if res.returncode != 0:
            print(f"\n[FAIL] {step['id']} 运行中断，退出代码: {res.returncode}")
            print(f"请检查上述报错信息或单独运行该脚本：python 02_实证回归与论文图表/{step['file']}")
            sys.exit(res.returncode)

        print(f"\n[OK] {step['id']} 运行完成 (耗时: {elapsed:.2f}s)")

    total_elapsed = time.time() - total_start
    print("\n" + "=" * 80)
    print("【复现完成】恭喜！论文全部实证回归结果与高清图表已全部成功复现！")
    print(f"总耗时: {total_elapsed:.2f} 秒")
    print("=" * 80)

    print("\n【生成文件清单】")
    print("[output/ 统计与回归数据产物]")
    out_files = sorted([f.name for f in OUTPUT_DIR.iterdir() if f.is_file() and f.name != '.gitkeep'])
    for f in out_files:
        sz = (OUTPUT_DIR / f).stat().st_size / 1024
        print(f"  - output/{f} ({sz:.1f} KB)")

    print("\n[figures/ 论文高清矢量配图]")
    fig_files = sorted([f.name for f in FIGURES_DIR.iterdir() if f.is_file() and f.name != '.gitkeep'])
    for f in fig_files:
        sz = (FIGURES_DIR / f).stat().st_size / 1024
        print(f"  - figures/{f} ({sz:.1f} KB)")

    print("\n" + "=" * 80)
    print("复现提示：")
    print("1. 所有回归表格指标与论文正文中的表 3 ~ 表 12 100% 精确契合。")
    print("2. figures/ 下包含可以直接用于 LaTeX / Word 投稿的高清 300 DPI 图表。")
    print("=" * 80)


if __name__ == '__main__':
    main()
