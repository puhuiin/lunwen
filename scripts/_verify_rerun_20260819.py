# -*- coding: utf-8 -*-
"""_verify_rerun_20260819.py — 重跑流水线后的可复现性验证
============================================================
比对「重跑前基准备份」与「重跑后新产物」：
  1. 面板：主分析面板_重建.csv / 主分析面板_重建_含TOwind.csv
     - MD5 / shape / 列集合；若不同 → 列级单元格差异数与最大绝对差
  2. _v4_benchmark.json：标量字段 + 全部 18 系数(beta/se/t/p 双口径 + perm/wcb p)
  3. L3_L1_regression_HONEST_TOWind_2026-08-15.json：H1–H5 逐假设 N/funds/rows
输出：_verify_rerun_20260819.json（机器可读）+ 控制台摘要
"""
import os, json, hashlib
import pandas as pd

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BK = os.path.join(HERE, "备份_重跑前基准_20260819_1545")
OUT = os.path.join(HERE, "指标计算流水线", "output")
report = {"panels": {}, "v4_benchmark": {}, "honest": {}, "verdict": None}


def md5(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------- 1. 面板比对 ----------
for name in ["主分析面板_重建.csv", "主分析面板_重建_含TOwind.csv"]:
    old_p = os.path.join(BK, name)
    new_p = os.path.join(OUT, name)
    entry = {"md5_old": md5(old_p), "md5_new": None, "identical": None}
    if os.path.exists(new_p):
        entry["md5_new"] = md5(new_p)
        entry["identical"] = entry["md5_old"] == entry["md5_new"]
        do = pd.read_csv(old_p, dtype={"fund_code": str})
        dn = pd.read_csv(new_p, dtype={"fund_code": str})
        entry["shape_old"] = list(do.shape)
        entry["shape_new"] = list(dn.shape)
        cols_o, cols_n = list(do.columns), list(dn.columns)
        entry["cols_added"] = [c for c in cols_n if c not in cols_o]
        entry["cols_removed"] = [c for c in cols_o if c not in cols_n]
        if entry["identical"]:
            entry["cell_diff_summary"] = "完全一致 (MD5 相同)"
        else:
            diffs = {}
            common = [c for c in cols_o if c in cols_n]
            for c in common:
                a, b = do[c], dn[c]
                if a.dtype.kind in "fc" and b.dtype.kind in "fc":
                    av = pd.to_numeric(a, errors="coerce")
                    bv = pd.to_numeric(b, errors="coerce")
                    na_changed = int((av.isna() != bv.isna()).sum())
                    both = (~av.isna()) & (~bv.isna())
                    d = (av[both] - bv[both]).abs()
                    ndiff = int((d > 1e-9).sum()) + na_changed
                    if ndiff:
                        diffs[c] = {"n_cells": ndiff, "max_abs_diff": float(d.max()) if len(d) else 0.0}
                else:
                    ndiff = int((a.astype(str) != b.astype(str)).sum())
                    if ndiff:
                        diffs[c] = {"n_cells": ndiff}
            entry["cell_diff_summary"] = diffs if diffs else "仅浮点序列化差异，数值列无 >1e-9 变化"
    else:
        entry["error"] = "重跑后面板缺失"
    report["panels"][name] = entry
    print("[面板] %s: identical=%s shape %s -> %s" % (name, entry["identical"], entry.get("shape_old"), entry.get("shape_new")))
    cds = entry.get("cell_diff_summary")
    if cds and isinstance(cds, dict):
        top = sorted(cds.items(), key=lambda kv: -kv[1]["n_cells"])[:12]
        for c, info in top:
            print("   差异列 %-24s n=%-7d max|Δ|=%.6g" % (c, info["n_cells"], info.get("max_abs_diff", float("nan"))))

# ---------- 2. _v4_benchmark.json 比对 ----------
ob_path, nb_path = os.path.join(BK, "_v4_benchmark.json"), os.path.join(HERE, "_v4_benchmark.json")
if os.path.exists(nb_path):
    ob = json.load(open(ob_path, encoding="utf-8"))
    nb = json.load(open(nb_path, encoding="utf-8"))
    b4 = {"scalars": {}, "coefs": {}}
    for k in ["n_obs", "n_fund", "r2", "adj_r2", "r2_without_L5", "delta_r2_L5"]:
        ov, nv = ob.get(k), nb.get(k)
        b4["scalars"][k] = {"old": ov, "new": nv,
                            "abs_diff": (abs(ov - nv) if isinstance(ov, (int, float)) and isinstance(nv, (int, float)) else None)}
    worst = {f: ("", 0.0) for f in ["beta", "se2w", "t2w", "p2w", "se1w", "t1w", "p1w"]}
    for v, oc in ob["coefs"].items():
        nc = nb["coefs"].get(v)
        if nc is None:
            b4["coefs"][v] = {"missing_in_new": True}
            continue
        rec = {}
        for f in ["beta", "se2w", "t2w", "p2w", "se1w", "t1w", "p1w"]:
            ov, nv = oc.get(f), nc.get(f)
            if isinstance(ov, (int, float)) and isinstance(nv, (int, float)):
                rec[f] = {"old": ov, "new": nv, "abs_diff": abs(ov - nv)}
                if abs(ov - nv) > worst[f][1]:
                    worst[f] = (v, abs(ov - nv))
            else:
                rec[f] = {"old": ov, "new": nv}
        for f in ["perm_p", "wcb_p"]:
            rec[f] = {"old": oc.get(f), "new": nc.get(f)}
        b4["coefs"][v] = rec
    b4["worst_abs_diff"] = {f: {"var": wv, "abs_diff": wd} for f, (wv, wd) in worst.items()}
    focus = ["de", "lsv", "risk_asym", "ICI", "ARG", "AS_improved", "log_fund_age",
             "SDI", "TO_wind", "ff5_MKT_excess", "ff5_SMB", "ff5_HML", "ff5_RMW", "ff5_CMA"]
    b4["focus_table"] = {}
    for v in focus:
        oc, nc = ob["coefs"].get(v), nb["coefs"].get(v)
        if oc and nc:
            b4["focus_table"][v] = {
                "beta_old": oc["beta"], "beta_new": nc["beta"],
                "t2w_old": oc["t2w"], "t2w_new": nc["t2w"],
                "p2w_old": oc["p2w"], "p2w_new": nc["p2w"],
            }
    report["v4_benchmark"] = b4
    print("\n[v4基准] 标量: N %s->%s  R2 %.6f->%.6f  ΔR2_L5 %.6f->%.6f" % (
        ob["n_obs"], nb["n_obs"], ob["r2"], nb["r2"], ob["delta_r2_L5"], nb["delta_r2_L5"]))
    print("[v4基准] 最大绝对差: " + ", ".join("%s(%s)=%.3g" % (f, w["var"], w["abs_diff"]) for f, w in b4["worst_abs_diff"].items()))
else:
    print("\n[v4基准] 新 _v4_benchmark.json 尚未生成（需先跑 _v4_benchmark_table.py）")

# ---------- 3. HONEST JSON 比对 ----------
oh_path = os.path.join(BK, "L3_L1_regression_HONEST_TOWind_2026-08-15.json")
nh_path = os.path.join(HERE, "L3_L1_regression_HONEST_TOWind_2026-08-15.json")
if os.path.exists(nh_path):
    oh = json.load(open(oh_path, encoding="utf-8"))["honest"]
    nh = json.load(open(nh_path, encoding="utf-8"))["honest"]
    ho = {}
    for k in oh:
        oo, nn = oh[k], nh.get(k)
        if nn is None:
            ho[k] = {"missing_in_new": True}
            continue
        rec = {"N": {"old": oo["N"], "new": nn["N"]}, "funds": {"old": oo["funds"], "new": nn["funds"]}, "rows": {}}
        ows = {r["v"]: r for r in oo["rows"]}
        nws = {r["v"]: r for r in nn["rows"]}
        worst_t = 0.0
        for v, orow in ows.items():
            nrow = nws.get(v)
            if nrow is None:
                rec["rows"][v] = {"missing_in_new": True}
                continue
            adt = abs(orow["t"] - nrow["t"])
            worst_t = max(worst_t, adt)
            rec["rows"][v] = {
                "b_old": orow["b"], "b_new": nrow["b"], "abs_diff_b": abs(orow["b"] - nrow["b"]),
                "t_old": orow["t"], "t_new": nrow["t"], "abs_diff_t": adt,
            }
        rec["max_abs_diff_t"] = worst_t
        ho[k] = rec
    report["honest"] = ho
    print("\n[HONEST] 各假设最大 |Δt|:")
    for k, rec in ho.items():
        print("   %-32s N %s->%s  max|Δt|=%.4f" % (k, rec["N"]["old"], rec["N"]["new"], rec["max_abs_diff_t"]))
else:
    print("\n[HONEST] 新 JSON 尚未生成（流水线仍在运行）")

# ---------- 判定 ----------
verdict = "PENDING_RERUN_NOT_DONE"
if os.path.exists(nb_path) and os.path.exists(nh_path):
    panel_ok = all(p.get("identical") for p in report["panels"].values() if "identical" in p)
    b4_worst = max((w["abs_diff"] for w in report["v4_benchmark"].get("worst_abs_diff", {}).values()), default=0.0)
    honest_worst = max((rec["max_abs_diff_t"] for rec in report["honest"].values() if "max_abs_diff_t" in rec), default=0.0)
    tol = 1e-6
    if panel_ok and b4_worst < tol and honest_worst < tol:
        verdict = "REPRODUCIBLE_EXACT (面板+基准+诚实回归逐字段一致，出稿无需改动)"
    else:
        verdict = "REPRODUCED_WITH_DIFFS (面板 identical=%s | v4 最大|Δ|=%.3g | HONEST 最大|Δt|=%.3g — 需核对差异点)" % (
            panel_ok, b4_worst, honest_worst)
report["verdict"] = verdict
print("\n==== 判定: %s ====" % verdict)

with open(os.path.join(HERE, "_verify_rerun_20260819.json"), "w", encoding="utf-8") as f:
    json.dump(report, f, ensure_ascii=False, indent=2)
print("写出 _verify_rerun_20260819.json")
