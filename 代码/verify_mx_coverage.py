"""
验证东方财富妙想对单只基金"全部持股明细"查询的报告期覆盖范围。
决定批量策略：若覆盖 2018-2025 全部报告期，则 142 次查询即可；
若仅返回最近 1-2 期，则需逐期精确查询（2272 次）。
"""
import os
import sys
import asyncio
import re

# 禁用代理（妙想授权/查数服务器被本机代理拦截）
for p in ["HTTPS_PROXY", "HTTP_PROXY", "https_proxy", "http_proxy"]:
    os.environ.pop(p, None)

SCRIPTS_DIR = r"C:\Users\26955\.workbuddy\skills\mx-finance-data\scripts"
sys.path.insert(0, SCRIPTS_DIR)

import get_data as mx

def parse_report_periods(md_path):
    """从妙想返回的 MD 宽表中提取所有报告期值。"""
    periods = []
    fund_block = {}  # fund -> set(periods)
    current_fund = None
    with open(md_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    # 收集所有"报告期"行的值
    for i, line in enumerate(lines):
        # 报告期行：| 报告期 | 2024-06-30 | 2024-06-30 | ...
        if line.strip().startswith("|") and "报告期" in line:
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            # 去掉首列"报告期"
            vals = [c for c in cells[1:] if re.match(r"\d{4}-\d{2}-\d{2}", c)]
            periods.extend(vals)
    return periods

async def main():
    fund = sys.argv[1] if len(sys.argv) > 1 else "001412"
    query = f"基金{fund}的全部持股明细"
    indicators = "全部持股明细，含股票代码、持股数量、持股市值、占净值比、报告期"
    out_dir = r"D:\Desktop\基金经理行为分析研究\数据\外部数据\mx_raw"
    os.makedirs(out_dir, exist_ok=True)
    result = await mx.query_mx_finance_data(
        query=query, indicators=indicators, output_dir=out_dir
    )
    if result.get("error"):
        print(f"[ERROR] {result['error']}")
        return
    md_path = result.get("md_path")
    print(f"基金 {fund} 查询成功")
    print(f"  返回实体数: {result.get('returned_entity_count')}")
    print(f"  MD 路径: {md_path}")
    if md_path and os.path.exists(md_path):
        periods = parse_report_periods(md_path)
        from collections import Counter
        cnt = Counter(periods)
        print(f"  报告期分布（共 {len(periods)} 个持仓记录）:")
        for p, c in sorted(cnt.items()):
            print(f"    {p}: {c} 只股票")
        # 识别半年报(06-30)和年报(12-31)
        hy = [p for p in cnt if p.endswith("06-30")]
        nf = [p for p in cnt if p.endswith("12-31")]
        print(f"  半年报期数: {len(hy)} ({min(hy) if hy else '-'} ~ {max(hy) if hy else '-'})")
        print(f"  年报期数: {len(nf)} ({min(nf) if nf else '-'} ~ {max(nf) if nf else '-'})")

if __name__ == "__main__":
    asyncio.run(main())
