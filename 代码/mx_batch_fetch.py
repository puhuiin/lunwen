"""
东方财富妙想 基金全持仓 批量获取脚本（带断点续传）

策略：对每只基金查询 8 个年份的"年报全部持股明细"，妙想每次返回
      相邻3期（前一年年报 + 同年半年报 + 目标年报），
      8次查询即可覆盖 2018-2025 全部半年报/年报共 16+ 期。

特性：
- 断点续传：已完成的基金写入 mx_progress.json，重跑自动跳过
- 错误重试：单次查询失败重试最多 3 次
- 实时保存：每完成一只基金，追加写入全局 CSV
- 代理禁用：妙想服务器被本机代理拦截，运行前 unset

输出：
- 数据/外部数据/mx_full_holdings.csv  （累计全持仓，长表）
- 数据/外部数据/mx_progress.json       （已完成基金 + 统计）
"""
import os
import sys
import json
import time
import asyncio
import argparse

for p in ["HTTPS_PROXY", "HTTP_PROXY", "https_proxy", "http_proxy"]:
    os.environ.pop(p, None)

SCRIPTS_DIR = r"C:\Users\26955\.workbuddy\skills\mx-finance-data\scripts"
sys.path.insert(0, SCRIPTS_DIR)
import get_data as mx

BASE = r"D:\Desktop\基金经理行为分析研究"
FUND_LIST = os.path.join(BASE, r"代码\_target_funds_from_de.csv")
OUT_DIR = os.path.join(BASE, r"数据\外部数据\mx_raw")
OUT_CSV = os.path.join(BASE, r"数据\外部数据\mx_full_holdings.csv")
PROGRESS = os.path.join(BASE, r"数据\外部数据\mx_progress.json")

YEARS = list(range(2018, 2026))  # 2018-2025 年报

def parse_md(md_path):
    """解析妙想返回的MD宽表，提取 (fund_code, stock_code, report_date, shares_wan, mv_wan, nav_pct)。"""
    import re
    if not md_path or not os.path.exists(md_path):
        return []
    rows = []
    fund_code = None
    with open(md_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # 提取基金代码（从标题 ## 基金名（001412.OF）或 (001412.OF)）
    for ln in lines:
        m = re.search(r"[（(](\d{6})\.OF[）)]", ln)
        if m:
            fund_code = m.group(1)
            break

    # 按表分块（连续 | 开头的行构成一个表）
    tables = []
    cur = []
    for ln in lines:
        if ln.strip().startswith("|"):
            cur.append(ln.rstrip("\n"))
        else:
            if cur:
                tables.append(cur)
                cur = []
    if cur:
        tables.append(cur)

    for tbl in tables:
        # 找到各指标行
        def row_val(name):
            for ln in tbl:
                cells = [c.strip() for c in ln.strip().strip("|").split("|")]
                if cells and cells[0] == name:
                    return cells[1:]
            return None
        stock_codes = row_val("股票代码")
        periods = row_val("报告期")
        shares = row_val("持股数量(万股)")
        mv = row_val("持股市值(万元)")
        nav = row_val("占净值比(%)")
        if not stock_codes:
            continue
        n = len(stock_codes)
        for i in range(n):
            sc = stock_codes[i]
            if not re.match(r"\d{6}\.(SH|SZ)", sc):
                continue
            period = periods[i] if (periods and i < len(periods)) else None
            sh = shares[i] if (shares and i < len(shares)) else None
            mvi = mv[i] if (mv and i < len(mv)) else None
            nv = nav[i] if (nav and i < len(nav)) else None
            try:
                sh_f = float(sh) if sh not in (None, "") else None
            except:
                sh_f = None
            try:
                mv_f = float(mvi) if mvi not in (None, "") else None
            except:
                mv_f = None
            try:
                nv_f = float(nv) if nv not in (None, "") else None
            except:
                nv_f = None
            rows.append({
                "fund_code": fund_code,
                "stock_code": sc,
                "report_date": period,
                "shares_wan": sh_f,
                "mv_wan": mv_f,
                "nav_pct": nv_f,
            })
    return rows

async def fetch_one(fund, year):
    query = f"基金{fund}的{year}年年报全部持股明细"
    indicators = f"{year}年年报全部持股明细，含股票代码、持股数量、持股市值、占净值比、报告期"
    out_dir = os.path.join(OUT_DIR, fund)
    os.makedirs(out_dir, exist_ok=True)
    try:
        result = await mx.query_mx_finance_data(
            query=query, indicators=indicators, output_dir=out_dir
        )
    except Exception as e:
        return [], f"exception: {e}"
    if result.get("error"):
        # 拦截所有错误：积分耗尽、频控、业务错误等，避免静默返回0条
        return [], result.get("error")
    md_path = result.get("md_path")
    if not md_path or not os.path.exists(md_path):
        return [], "no_md"
    rows = parse_md(md_path)
    return rows, None

def load_progress():
    if os.path.exists(PROGRESS):
        try:
            return json.load(open(PROGRESS, encoding="utf-8"))
        except:
            pass
    return {"done": [], "stats": {}}

def save_progress(prog):
    with open(PROGRESS, "w", encoding="utf-8") as f:
        json.dump(prog, f, ensure_ascii=False, indent=2)

def append_csv(rows):
    import pandas as pd
    df = pd.DataFrame(rows)
    write_header = not os.path.exists(OUT_CSV)
    df.to_csv(OUT_CSV, mode="a", header=write_header, index=False, encoding="utf-8-sig")

async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="仅跑前N只基金（验证用）")
    ap.add_argument("--start", type=int, default=0, help="起始基金索引")
    args = ap.parse_args()

    funds = []
    with open(FUND_LIST, encoding="utf-8") as f:
        for line in f:
            c = line.strip().split(",")[0]
            if c and c != "fund_code":
                funds.append(c)
    if args.limit:
        funds = funds[args.start:args.start + args.limit]
    else:
        funds = funds[args.start:]

    prog = load_progress()
    done = set(prog.get("done", []))
    funds_todo = [f for f in funds if f not in done]

    print(f"总基金: {len(funds)}, 已完成: {len(done)}, 待处理: {len(funds_todo)}")

    for fi, fund in enumerate(funds_todo):
        all_rows = []
        errs = []
        for year in YEARS:
            for attempt in range(3):
                rows, err = await fetch_one(fund, year)
                if err is None:
                    all_rows.extend(rows)
                    break
                else:
                    if attempt < 2:
                        time.sleep(2)
                    else:
                        errs.append(f"{year}:{err}")
            await asyncio.sleep(1)  # 礼貌间隔，降低频控风险
        # 去重（同基金-股票-报告期）
        seen = set()
        dedup = []
        for r in all_rows:
            key = (r["fund_code"], r["stock_code"], r["report_date"])
            if key in seen:
                continue
            seen.add(key)
            dedup.append(r)
        append_csv(dedup)
        prog["done"].append(fund)
        # 统计覆盖期数
        pers = sorted(set(r["report_date"] for r in dedup if r["report_date"]))
        prog["stats"][fund] = {
            "records": len(dedup),
            "periods": pers,
            "errors": errs,
        }
        save_progress(prog)
        print(f"[{fi+1}/{len(funds_todo)}] 基金 {fund}: {len(dedup)} 条, {len(pers)} 期, 错误 {len(errs)}")

    print("批量获取完成。")

if __name__ == "__main__":
    asyncio.run(main())
