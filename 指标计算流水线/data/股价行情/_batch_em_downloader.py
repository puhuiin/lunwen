#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量下载东财月K线收盘价，保存原始 JSON，再解析为 CSV
用法: python _batch_em_downloader.py <batch_file> <out_dir>
"""
import os, sys, json, re, time, subprocess
from pathlib import Path

ROOT = Path(r"d:\Desktop\基金经理行为分析研究\指标计算流水线\data\股价行情")
RAW_DIR = ROOT / "em_raw"
PARSED_DIR = ROOT / "em_parsed"
RAW_DIR.mkdir(exist_ok=True)
PARSED_DIR.mkdir(exist_ok=True)

PARSER = ROOT / "_parse_em_close.py"

def load_batch(batch_file):
    with open(batch_file, encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]

def build_query(codes):
    return "请提供以下A股证券代码的月K线收盘价（月线收盘价），返回每只股票每月的收盘价数据，列名格式为2026-06-30(月)，从上市至今：" + ",".join(codes)

def call_em(query, max_retry=3):
    # 通过 mcp 工具调用（需在本进程里跑，这里用 subprocess 调用 python -m 方式不可行，
    # 改为直接用 run_mcp 不行，只能写成供外部 Task agent 调用的独立脚本）
    # 这里只生成查询文本供人工/子代理执行；真实下载由子代理完成
    pass

def parse_raw(raw_path, out_csv):
    cmd = [sys.executable, str(PARSER), str(raw_path), str(out_csv)]
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=str(ROOT))
    return r.returncode == 0, r.stdout, r.stderr

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python _batch_em_downloader.py <batch_file> <out_dir>")
        sys.exit(1)
    batch_file = sys.argv[1]
    out_dir = Path(sys.argv[2])
    out_dir.mkdir(exist_ok=True)
    codes = load_batch(batch_file)
    print(f"Batch {len(codes)} codes")
    # 生成供子代理复制的查询文本
    q = build_query(codes)
    query_txt = out_dir / "query.txt"
    query_txt.write_text(q, encoding="utf-8")
    print(f"Query written to {query_txt}")
    print("请将 query.txt 内容复制到东财插件执行，把返回完整 JSON 存为 raw.json，再运行:")
    print(f"  python {PARSER} {out_dir}/raw.json {out_dir}/monthly.csv")