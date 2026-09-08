"""下载单个批次的东方财富月K线收盘价数据并解析为CSV

用法: python _download_em_batch.py <batch_index>
- batch_index: 0-99 的批次编号
- 读取 em_batches/batch_XXX.txt 中的股票代码
- 调用东方财富 MCP 下载月K线收盘价
- 保存原始 JSON 到 em_raw/batch_XXX_raw.json
- 调用 _parse_em_close.py 解析为 em_parsed/batch_XXX_monthly.csv
"""
import sys
import os
import subprocess
import json

BASE_DIR = r"d:\Desktop\基金经理行为分析研究\指标计算流水线\data\股价行情"
BATCH_DIR = os.path.join(BASE_DIR, "em_batches")
RAW_DIR = os.path.join(BASE_DIR, "em_raw")
PARSED_DIR = os.path.join(BASE_DIR, "em_parsed")
PYTHON_EXE = r"C:\Users\26955\AppData\Local\Programs\Python\Python313\python.exe"

def main():
    if len(sys.argv) < 2:
        print("Usage: python _download_em_batch.py <batch_index>")
        sys.exit(1)

    batch_idx = int(sys.argv[1])
    batch_file = os.path.join(BATCH_DIR, f"batch_{batch_idx:03d}.txt")

    with open(batch_file, 'r') as f:
        codes_str = f.read().strip()

    codes = [c.strip() for c in codes_str.split(',') if c.strip()]
    print(f"[Batch {batch_idx:03d}] {len(codes)} codes: {','.join(codes[:5])}...")

    # 调用东方财富 MCP (通过独立脚本调用 run_mcp)
    query = f"请提供以下A股证券代码的月K线收盘价（月线收盘价），返回每只股票从上市至今每月末的收盘价，列名格式为 2026-06-30(月)，按月份从新到旧排列：{','.join(codes)}"

    # 使用 integrated_code_mode 来调用 MCP 工具
    result = call_em_mcp(query)

    if result is None:
        print(f"[Batch {batch_idx:03d}] FAILED to get data")
        sys.exit(1)

    # 保存原始 JSON
    os.makedirs(RAW_DIR, exist_ok=True)
    raw_file = os.path.join(RAW_DIR, f"batch_{batch_idx:03d}_raw.json")
    with open(raw_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"[Batch {batch_idx:03d}] Raw saved: {raw_file}")

    # 解析
    os.makedirs(PARSED_DIR, exist_ok=True)
    parsed_file = os.path.join(PARSED_DIR, f"batch_{batch_idx:03d}_monthly.csv")
    parse_script = os.path.join(BASE_DIR, "_parse_em_close.py")

    try:
        subprocess.run(
            [PYTHON_EXE, parse_script, raw_file, parsed_file],
            check=True,
            capture_output=True,
            text=True
        )
        print(f"[Batch {batch_idx:03d}] Parsed: {parsed_file}")
    except subprocess.CalledProcessError as e:
        print(f"[Batch {batch_idx:03d}] PARSE FAILED: {e.stderr}")
        sys.exit(1)

def call_em_mcp(query):
    """通过 integrated_code_mode 调用东方财富 MCP 工具"""
    # 这里需要使用 MCP 调用框架，由主进程调用 run_mcp 实现
    # 实际下载在主脚本中循环调用 run_mcp
    raise NotImplementedError("Use the main download loop with run_mcp")

if __name__ == "__main__":
    main()
