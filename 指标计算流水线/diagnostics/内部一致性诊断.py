# -*- coding: utf-8 -*-
"""内部一致性诊断（不依赖论文原始面板/元面板）。

目标：在「流水线自算、离线自洽」前提下，校验主分析面板_重建.csv 的内部逻辑一致性，
而非与旧面板做逐项比对。检查项：

  1. 主键完整： (fund_code, report_date) 唯一；面板行数 == 骨架行数（左拼接不增行）。
  2. 样本覆盖：基金数 / 季度数 / 时间跨度。
  3. 各指标覆盖度与分布：非空比例、均值、标准差、极值、粗异常（|z|>6）。
  4. 恒等式重建：
       - excess_return == quarter_return − rf（FF3 季度无风险）
       - future_return == 同基金下一季度 quarter_return
       - ff3/ff4/ff5_adj_return 为单基金时序回归截距 → 基金内应为常数（std≈0）
  5. 跨源一致性（两套独立 NAV 算法互验，仍不依赖元面板）：
       - 面板 quarter_return（净值日收益复利） vs 基金季度收益.csv quarter_return
         （同源于净值、不同代码路径），应高度一致。

输出：打印 JSON 摘要 + 写出 diagnostics/内部一致性报告.html。
"""
import os
import sys
import json
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import lib_metrics as M

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(BASE), "output")
PANEL = os.path.join(OUT, "主分析面板_重建.csv")


def _num_summary(s: pd.Series) -> dict:
    s = pd.to_numeric(s, errors="coerce")
    n = int(s.notna().sum())
    if n == 0:
        return {"non_null": 0, "pct": 0.0, "mean": None, "std": None,
                "min": None, "max": None, "abs_z6": 0}
    mean, std = float(s.mean()), float(s.std())
    z = (s - mean) / std if std and std > 0 else s * 0
    return {
        "non_null": n,
        "pct": round(s.notna().mean() * 100, 1),
        "mean": round(mean, 5),
        "std": round(std, 5),
        "min": round(float(s.min()), 5),
        "max": round(float(s.max()), 5),
        "abs_z6": int((z.abs() > 6).sum()),
    }


def main():
    panel = pd.read_csv(PANEL, encoding="utf-8-sig")
    rep = {}
    rep["shape"] = list(panel.shape)          # 落盘 CSV 真实列数（此时尚未加 rd 辅助列）
    panel["report_date"] = pd.to_datetime(panel["report_date"], errors="coerce")
    panel["rd"] = panel["report_date"]

    rep["n_funds"] = int(panel["fund_code"].nunique())
    rep["n_report_dates"] = int(panel["rd"].nunique())
    rep["date_min"] = str(panel["rd"].min().date()) if panel["rd"].notna().any() else None
    rep["date_max"] = str(panel["rd"].max().date()) if panel["rd"].notna().any() else None

    # 1) 主键完整
    dup = int(panel.duplicated(["fund_code", "report_date"]).sum())
    rep["duplicate_keys"] = dup
    sk = M.load_skeleton()
    rep["skeleton_rows"] = int(len(sk))
    rep["panel_rows_eq_skeleton"] = (len(panel) == len(sk))

    # 2) 各指标覆盖度与分布
    num_cols = [c for c in panel.columns
                if c not in ("fund_code", "report_date", "year", "quarter", "rd")
                and pd.api.types.is_numeric_dtype(panel[c])]
    rep["columns"] = num_cols
    rep["coverage"] = {c: _num_summary(panel[c]) for c in num_cols}

    checks = {}

    # 3a) excess_return == quarter_return − rf
    m = panel[["quarter_return", "rf", "excess_return"]].notna().all(axis=1)
    if m.sum():
        d = (panel.loc[m, "quarter_return"] - panel.loc[m, "rf"]) - panel.loc[m, "excess_return"]
        checks["excess_reconstruction"] = {
            "n": int(m.sum()),
            "exact_pct": round(float((d.abs() < 1e-6).mean()) * 100, 2),
            "max_abs_err": round(float(d.abs().max()), 8),
        }

    # 3b) future_return == 同基金下一季度 quarter_return
    ps = panel.sort_values(["fund_code", "report_date"])
    ps["_qr_next"] = ps.groupby("fund_code")["quarter_return"].shift(-1)
    m2 = ps["future_return"].notna() & ps["_qr_next"].notna()
    if m2.sum():
        d2 = (ps.loc[m2, "future_return"] - ps.loc[m2, "_qr_next"]).abs()
        checks["future_reconstruction"] = {
            "n": int(m2.sum()),
            "exact_pct": round(float((d2 < 1e-9).mean()) * 100, 2),
            "max_abs_err": round(float(d2.max()), 10),
        }

    # 3c) alpha 基金内常数
    for col in ["ff3_adj_return", "ff4_adj_return", "ff5_adj_return"]:
        if col in panel.columns:
            within = panel.groupby("fund_code")[col].std()
            checks[f"{col}_within_fund_const"] = {
                "n_funds": int(within.notna().sum()),
                "const_pct": round(float((within.fillna(0) < 1e-9).mean()) * 100, 2),
            }

    # 4) 跨源：面板 quarter_return vs 基金季度收益.csv
    qret = pd.read_csv(M.D("L4_风险应对层", "基金季度收益.csv"), encoding="utf-8-sig")
    qret["report_date"] = M.to_panel_date(qret["report_date"])
    mg = panel[["fund_code", "report_date", "quarter_return"]].merge(
        qret[["fund_code", "report_date", "quarter_return"]],
        on=["fund_code", "report_date"], suffixes=("", "_src"), how="inner")
    if len(mg):
        r = mg["quarter_return"].corr(mg["quarter_return_src"])
        mad = float((mg["quarter_return"] - mg["quarter_return_src"]).abs().max())
        checks["quarter_return_cross_source"] = {
            "n": int(len(mg)),
            "pearson": round(float(r), 5) if pd.notna(r) else None,
            "max_abs_diff": round(mad, 8),
        }

    rep["identity_checks"] = checks

    # 评级：简单汇总
    problems = []
    if rep["duplicate_keys"] > 0:
        problems.append("存在重复主键 (fund_code, report_date)")
    if not rep["panel_rows_eq_skeleton"]:
        problems.append("面板行数 != 骨架行数（左拼接异常）")
    for c, v in checks.items():
        if "exact_pct" in v and v.get("exact_pct", 100) < 99.9:
            problems.append(f"{c}: 恒等式匹配率 {v.get('exact_pct')}% < 99.9%")
        if "const_pct" in v and v.get("const_pct", 100) < 99.9:
            problems.append(f"{c}: 基金内常数比例 {v.get('const_pct')}% < 99.9%")
    rep["problems"] = problems
    rep["status"] = "OK" if not problems else "WATCH"

    print(json.dumps(rep, ensure_ascii=False, indent=2, default=str))

    # ---- 生成 HTML 报告 ----
    _write_html(rep)
    return rep


def _write_html(rep):
    rows = ""
    for c in rep["columns"]:
        v = rep["coverage"][c]
        rows += (f"<tr><td>{c}</td><td>{v['non_null']}</td><td>{v['pct']}%</td>"
                 f"<td>{v['mean']}</td><td>{v['std']}</td><td>{v['min']}</td>"
                 f"<td>{v['max']}</td><td>{v['abs_z6']}</td></tr>")

    ids = ""
    for k, v in rep["identity_checks"].items():
        items = "".join(f"<li>{kk}: <b>{vv}</b></li>" for kk, vv in v.items())
        ids += f"<div class='card'><h4>{k}</h4><ul>{items}</ul></div>"

    status_color = "#2e7d32" if rep["status"] == "OK" else "#ef6c00"
    probs = "".join(f"<li>{p}</li>" for p in rep["problems"]) or "<li>无</li>"

    html = f"""<!doctype html><html lang='zh'><head><meta charset='utf-8'>
<style>
body{{font-family:-apple-system,'Segoe UI',sans-serif;margin:24px;color:#222;background:#fafafa}}
h1{{font-size:22px}} h2{{font-size:17px;margin-top:28px;border-left:4px solid #1565c0;padding-left:8px}}
.card{{background:#fff;border:1px solid #e0e0e0;border-radius:8px;padding:12px 16px;margin:8px 0;box-shadow:0 1px 2px rgba(0,0,0,.04)}}
table{{border-collapse:collapse;width:100%;font-size:13px;background:#fff}}
th,td{{border:1px solid #e0e0e0;padding:6px 8px;text-align:right}}
th:nth-child(1),td:nth-child(1){{text-align:left}}
th{{background:#1565c0;color:#fff}}
.badge{{display:inline-block;padding:4px 12px;border-radius:12px;color:#fff;font-weight:600;background:{status_color}}}
ul{{margin:4px 0}}
</style></head><body>
<h1>指标计算流水线 · 内部一致性诊断报告</h1>
<p>生成口径：仅依赖流水线自算数据与原始数据，<b>不</b>与论文原始面板(元面板)比对。</p>
<p>状态：<span class='badge'>{rep['status']}</span></p>
<div class='card'>
  <h4>面板概况</h4>
  <ul>
    <li>形状：{rep['shape']}</li>
    <li>基金数：{rep['n_funds']} ｜ 报告期数：{rep['n_report_dates']}</li>
    <li>时间跨度：{rep['date_min']} → {rep['date_max']}</li>
    <li>骨架行数：{rep['skeleton_rows']} ｜ 面板行数==骨架：{rep['panel_rows_eq_skeleton']}</li>
    <li>重复主键数：{rep['duplicate_keys']}</li>
  </ul>
</div>
<h2>恒等式 / 跨源一致性校验</h2>
{ids}
<h2>各指标覆盖度与分布</h2>
<table><thead><tr><th>指标</th><th>非空</th><th>覆盖</th><th>均值</th><th>标准差</th><th>最小</th><th>最大</th><th>|z|&gt;6</th></tr></thead>
<tbody>{rows}</tbody></table>
<h2>问题清单</h2><ul>{probs}</ul>
</body></html>"""
    out = os.path.join(BASE, "内部一致性报告.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    print("写出:", out)


if __name__ == "__main__":
    main()
