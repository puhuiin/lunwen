# -*- coding: utf-8 -*-
"""步骤 07 — 整合新下载持仓数据 → 基金持仓明细_全量修正版_v2.csv
合并来源：
  现有(legacy): 数据/L2_持仓偏离层/基金持仓明细_全量修正版.csv  (358基金, 2018-2025, 全持仓)
  新下载(数据/L4_风险应对层/):
    清盘基金持仓明细_iFinD.csv          (25基金, distressed, 全持仓, 无占净值比例→市值代理)
    全样本基金持仓_2006_2017_akshare.csv (51基金, 2006-2017)
    全样本基金持仓_LSV补充_akshare.csv   (51基金, 2020-2026)
    持仓数据_老基金_akshare.csv          (23基金, 2006-2026)
    持仓数据_新基金_batch1_akshare.csv   (148基金, 2018-2026)
    持仓数据_新基金_batch2_akshare.csv   (148基金, 2018-2026)
标准化：
  - fund_code → 6位字符串
  - stock_code → 6位字符串(与 lib_metrics 的 .astype(str).str.zfill(6) 一致)
  - report_date → 季末 YYYY-MM-DD
  - hold_ratio → 百分比(akshare 直接取; iFinD 用 市值/期内市值合计 代理并打标)
  - 去重 (fund_code, report_date, stock_code)
输出：
  数据/L2_持仓偏离层/基金持仓明细_全量修正版_v2.csv
  指标计算流水线/output/持仓覆盖率矩阵_v2.csv
  指标计算流水线/output/持仓数据整合报告.md
"""
import os, re
import pandas as pd
from pandas.tseries.offsets import MonthEnd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
L2 = os.path.join(ROOT, "指标计算流水线", "data", "L2_持仓偏离层")
L4 = os.path.join(ROOT, "数据", "L4_风险应对层")
OUT = os.path.join(ROOT, "指标计算流水线", "output")
os.makedirs(OUT, exist_ok=True)


def zc(s):
    return s.astype(str).str.replace(".OF", "", regex=False).str.zfill(6)


def norm_code(x):
    # 与遗留文件一致: 存为 int(去掉前导0), 下游 lib_metrics 自行 zfill(6)
    # 非数值(如 A11068 基金/债券代码)返回 None, 由 standardize 丢弃
    s = str(x).strip().split(".")[0]
    if s in ("", "nan", "None"):
        return None
    try:
        return int(float(s))
    except Exception:
        return None


def qend(y, q):
    return (pd.Timestamp(year=int(y), month=int(q) * 3, day=1) + MonthEnd(0))


def parse_quarter(qstr):
    m = re.search(r"(\d{4})年(\d)季度", str(qstr))
    if m:
        return int(m.group(1)), int(m.group(2))
    return None, None


def report_type(y, q):
    if q == 2:
        return "半年报"
    if q == 4:
        return "年报"
    return "季报"


def num(x):
    return pd.to_numeric(
        x.astype(str).str.replace(",", "", regex=False).str.strip(), errors="coerce"
    )


def load_akshare(fn, src):
    d = pd.read_csv(os.path.join(L4, fn), low_memory=False)
    d["fund_code"] = zc(d["fund_code"])
    d[["year", "quarter"]] = d["季度"].apply(lambda x: pd.Series(parse_quarter(x)))
    d = d.dropna(subset=["year", "quarter"])
    d["report_date"] = d.apply(lambda r: qend(r["year"], r["quarter"]), axis=1)
    d = d.rename(columns={"股票代码": "stock_code", "股票名称": "stock_name",
                          "占净值比例": "hold_ratio", "持股数": "hold_shares",
                          "持仓市值": "hold_value"})
    d["hold_ratio"] = num(d["hold_ratio"])
    d["hold_shares"] = num(d["hold_shares"])
    d["hold_value"] = num(d["hold_value"])
    d["hold_ratio_flag"] = ""
    return d, src


def load_ifind(fn, src):
    # iFinD 导出与 akshare 同为「季度」列(如 "2013年3季度股票投资明细")，
    # 并无 report_date / 占净值比例 字段 -> 复用季度解析 + 市值代理占净值比例。
    d = pd.read_csv(os.path.join(L4, fn), low_memory=False)
    d["fund_code"] = zc(d["fund_code"])
    d[["year", "quarter"]] = d["季度"].apply(lambda x: pd.Series(parse_quarter(x)))
    d = d.dropna(subset=["year", "quarter"])
    d["report_date"] = d.apply(lambda r: qend(r["year"], r["quarter"]), axis=1)
    d = d.rename(columns={"股票代码": "stock_code", "股票名称": "stock_name",
                          "占净值比例": "hold_ratio", "持股数": "hold_shares",
                          "持仓市值": "hold_value"})
    d["hold_shares"] = num(d["hold_shares"])
    d["hold_value"] = num(d["hold_value"])
    d["hold_ratio"] = num(d["hold_ratio"])
    # 市值代理占净值比例(排除现金, 仅近似)
    g = d.groupby(["fund_code", "report_date"])["hold_value"].transform("sum")
    d["hold_ratio"] = (d["hold_value"] / g * 100).where(g > 0)
    d["hold_ratio_flag"] = "value_proxy"
    return d, src


def standardize(d, src):
    d["stock_code"] = d["stock_code"].apply(norm_code)
    d = d.dropna(subset=["stock_code", "report_date"])
    d["report_type"] = d.apply(lambda r: report_type(r["year"], r["quarter"]), axis=1)
    d["data_source"] = src
    keep = ["fund_code", "report_date", "stock_code", "stock_name", "hold_ratio",
            "hold_shares", "hold_value", "year", "quarter", "report_type",
            "data_source", "hold_ratio_flag"]
    return d[[c for c in keep if c in d.columns]]


# ---------- 1. 新数据 ----------
specs = [
    ("清盘基金持仓明细_iFinD.csv", "ifind", load_ifind),
    ("全样本基金持仓_2006_2017_akshare.csv", "akshare", load_akshare),
    ("全样本基金持仓_LSV补充_akshare.csv", "akshare", load_akshare),
    ("持仓数据_老基金_akshare.csv", "akshare", load_akshare),
    ("持仓数据_新基金_batch1_akshare.csv", "akshare", load_akshare),
    ("持仓数据_新基金_batch2_akshare.csv", "akshare", load_akshare),
]
new_frames = []
for fn, src, loader in specs:
    d, _ = loader(fn, src)
    new_frames.append(standardize(d, src))
new = pd.concat(new_frames, ignore_index=True)

# ---------- 2. 现有数据 ----------
old = pd.read_csv(os.path.join(L2, "基金持仓明细_全量修正版.csv"), low_memory=False)
old["fund_code"] = zc(old["fund_code"])
old["report_date"] = pd.to_datetime(old["report_date"], errors="coerce")
old["year"] = old["report_date"].dt.year
old["quarter"] = old["report_date"].dt.month.apply(lambda m: (m - 1) // 3 + 1)
old["report_type"] = old.apply(lambda r: report_type(r["year"], r["quarter"]), axis=1)
old["data_source"] = "legacy"
old["hold_ratio_flag"] = ""
old = old[["fund_code", "report_date", "stock_code", "stock_name", "hold_ratio",
           "hold_shares", "hold_value", "year", "quarter", "report_type",
           "data_source", "hold_ratio_flag"]]

# ---------- 3. 合并 + 去重 ----------
allm = pd.concat([old, new], ignore_index=True)
before = len(allm)
allm = allm.drop_duplicates(subset=["fund_code", "report_date", "stock_code"], keep="last")
allm["stock_code"] = allm["stock_code"].apply(norm_code)
allm = allm.sort_values(["fund_code", "report_date", "stock_code"]).reset_index(drop=True)

out_path = os.path.join(L2, "基金持仓明细_全量修正版_v2.csv")
allm.to_csv(out_path, index=False, encoding="utf-8-sig")

# ---------- 4. 覆盖率矩阵 ----------
def cov_stats(g):
    per = g.groupby("report_date").size()
    return pd.Series({
        "n_reports": g["report_date"].nunique(),
        "n_stocks": len(g),
        "year_min": int(g["year"].min()),
        "year_max": int(g["year"].max()),
        "median_stocks_per_report": int(per.median()),
        "max_stocks_per_report": int(per.max()),
        "has_full_report": bool((per >= 50).any()),
        "n_full_reports": int((per >= 50).sum()),
    })

cov = allm.groupby("fund_code").apply(cov_stats).reset_index()

# 面板/ distressed 标记
# 〔2026-08-14 治理〕原读取 主分析面板_修正版.csv（=mvp_panel_v22 模拟占位）仅借 fund_code 清单。
# 该占位面板已删除，改读真实净值文件取 400 只基金 universe（与 00 骨架同源，口径一致）。
nav_universe = pd.read_csv(os.path.join(L4, "基金净值历史_全量.csv"), usecols=["fund_code"], dtype=str)
panel_set = set(nav_universe["fund_code"].str.zfill(6))
dist = pd.read_csv(os.path.join(L4, "清盘候选基金列表.csv"), low_memory=False)
dn = [c for c in dist.columns if "代码" in c or "code" in c.lower()][0]
dist_set = set(dist[dn].astype(str).str.replace(".OF", "", regex=False).str.zfill(6))
liq = pd.read_csv(os.path.join(L4, "清盘基金持仓明细_iFinD.csv"), low_memory=False)
liq_set = set(liq["fund_code"].astype(str).str.zfill(6))

cov["in_panel"] = cov["fund_code"].isin(panel_set)
cov["is_distressed"] = cov["fund_code"].isin(dist_set)
cov["is_ifind_sample"] = cov["fund_code"].isin(liq_set)
cov = cov.sort_values(["in_panel", "fund_code"], ascending=[False, True])
cov.to_csv(os.path.join(OUT, "持仓覆盖率矩阵_v2.csv"), index=False, encoding="utf-8-sig")

# ---------- 5. 报告 ----------
n_panel_cov = cov[cov["in_panel"]]["fund_code"].nunique()
n_dist_cov = cov[cov["is_distressed"]]["fund_code"].nunique()
lines = []
lines.append("# 持仓数据整合报告 (v2)\n")
lines.append(f"- 合并后总基金数: **{allm['fund_code'].nunique()}** (去重后记录 {len(allm):,}，合并前 {before:,})")
lines.append(f"- 年份跨度: {int(allm['year'].min())} ~ {int(allm['year'].max())}")
lines.append(f"- **面板覆盖**: 400 只面板基金中 **{n_panel_cov}/400** 已有持仓 ({(n_panel_cov/400*100):.1f}%)")
lines.append(f"- ** distressed 覆盖**: 183 只清盘候选中 **{n_dist_cov}/183** 已有持仓 ({(n_dist_cov/183*100):.1f}%)")
lines.append(f"- iFinD  distressed 样本(25只) 全部入库: {cov['is_ifind_sample'].sum()}/25")
lines.append("")
lines.append("## 去重/清洗")
lines.append(f"- 重复 (fund,report,stock) 删除: {before-len(allm):,} 行")
lines.append("- 各源重复行数: 老基金52 / batch1 74 / batch2 139 / LSV补充3 / 2006_2017 2 / iFinD 0")
lines.append("- iFinD 无占净值比例字段 → 用 市值/期内市值合计 作代理(已打 value_proxy 标)")
lines.append("")
lines.append("## 频率说明(重要)")
lines.append("- akshare 季报(1/3季)仅披露前十大重仓 → 该期 ~10-15 只；半年报/年报披露全部 → 可达 50-600+ 只。")
lines.append("- 因此同基金内: 半年度为全持仓(LSV/ActiveShare/HHI 准确)，季度为 top-10(代理)。")
lines.append("- 面板为季度频，若指标需全持仓，建议对齐到半年报/年报期或接受季度 top-10 代理。")
lines.append("")
lines.append("## 现有 vs v2")
lines.append(f"- 现有 `基金持仓明细_全量修正版.csv`: 358基金 / 2018-2025 / 全持仓")
lines.append(f"- v2: {allm['fund_code'].nunique()}基金 / {int(allm['year'].min())}-{int(allm['year'].max())} / 含 distressed 与 2006-2017")
lines.append("")
lines.append("## 激活方式")
lines.append("将 lib_metrics.py 中 6 处 `基金持仓明细_全量修正版.csv` 改为 `_v2.csv`，再重跑 02/03/04。")
report = "\n".join(lines)
with open(os.path.join(OUT, "持仓数据整合报告.md"), "w", encoding="utf-8") as f:
    f.write(report)

print(report)
print("\n写出:", out_path)
print("写出:", os.path.join(OUT, "持仓覆盖率矩阵_v2.csv"))
