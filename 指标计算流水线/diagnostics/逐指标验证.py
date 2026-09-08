# -*- coding: utf-8 -*-
"""
逐指标验证：流水线面板 vs 原始面板（主分析面板_修正版.csv）
目标：判断每个自变量/控制变量是否被"正确计算"，并识别"比错列"与方法升级导致的预期差异。

方法：
1. 以 (fund_code, report_date) 为键做内连接（不走位置对齐，避免错位）。
2. 数值列：与原始面板"同名列"算 Pearson 相关 + 最佳匹配列(Top5)发现变体错配 + 均值对比。
3. 类别列(gender/education/CFA/school)：算与原始面板同名列的"取值一致率"。
4. 列出原始面板中的"因变量"并确认其是否在流水线面板中缺失。
"""
import os, json
import pandas as pd
import numpy as np

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PIPE = os.path.join(BASE, "output", "主分析面板_重建.csv")
# 〔2026-08-14 治理〕主分析面板_修正版.csv（模拟占位）已删除。
# 历史对比基准改读 .bak_preSimDelete 备份（保留 SDI_hc/OCI_hc/TO_calc/SDI_original 污染列，供差异识别）。
ORIG = os.path.join(BASE, "output", "主分析面板_重建.csv.bak_preSimDelete")

pipe = pd.read_csv(PIPE)
orig = pd.read_csv(ORIG)
KEYS = ["fund_code", "report_date"]
for df in (pipe, orig):
    df["report_date"] = df["report_date"].astype(str)

# 显式加后缀，避免"仅单侧存在"的列不被加后缀
pipe2 = pipe.copy()
pipe2.columns = [c + "_p" if c not in KEYS else c for c in pipe2.columns]
orig2 = orig.copy()
orig2.columns = [c + "_o" if c not in KEYS else c for c in orig2.columns]
m = pipe2.merge(orig2, on=KEYS, how="inner")
assert len(m) == len(pipe), "键未 1:1 对齐，存在重复或丢失！"

print(f"内连接后样本数: {len(m)} (pipe={len(pipe)}, orig={len(orig)})")

# 仅对"原始就是数值"的列做数值化；类别列保持字符串
pipe_num = {c: pd.api.types.is_numeric_dtype(pipe[c]) for c in pipe.columns}
orig_num = {c: pd.api.types.is_numeric_dtype(orig[c]) for c in orig.columns}
for c in m.columns:
    if c in KEYS:
        continue
    base = c[:-2]  # 去掉 _p / _o
    if base in pipe_num and pipe_num[base]:
        m[c] = pd.to_numeric(m[c], errors="coerce")

pipe_cols = [c for c in pipe.columns if c not in KEYS]
orig_num_cols = [c for c in orig.columns if c not in KEYS and orig_num[c]]

DEP_KEYWORDS = ["return", "excess", "ff3", "ff4", "ff5", "bench", "RG", "BHS", "CR", "RAR",
                "alpha", "sharpe", "abs_return", "ret_", "risk_asym", "return_volatility"]
dep_in_orig = [c for c in orig.columns if any(k in c.lower() for k in DEP_KEYWORDS)]


def safe_corr(a, b):
    s = pd.DataFrame({"a": a, "b": b}).dropna()
    if len(s) < 10 or s["a"].std() == 0 or s["b"].std() == 0:
        return np.nan, np.nan, len(s)
    pr = s["a"].corr(s["b"])
    try:
        sp = s["a"].corr(s["b"], method="spearman")
    except Exception:
        sp = np.nan
    return pr, sp, len(s)


results = []
for col in pipe_cols:
    pc = col + "_p"
    is_num = pipe_num.get(col, False)
    row = {"pipeline_col": col, "type": "num" if is_num else "cat",
           "pipe_nonnull": int(m[pc].notna().sum())}
    same = col + "_o" if (col + "_o") in m.columns else None
    if is_num:
        if same is not None:
            pr, sp, n = safe_corr(m[pc], m[same])
            row.update({"same_name_orig": col, "same_pearson": round(pr, 4) if pd.notna(pr) else None,
                        "same_spearman": round(sp, 4) if pd.notna(sp) else None, "same_n": n,
                        "pipe_mean": round(float(m[pc].mean()), 5) if m[pc].notna().any() else None,
                        "orig_mean": round(float(m[same].mean()), 5) if m[same].notna().any() else None})
        else:
            row.update({"same_name_orig": "(无同名列)", "same_pearson": None, "same_spearman": None,
                        "same_n": None, "pipe_mean": round(float(m[pc].mean()), 5) if m[pc].notna().any() else None,
                        "orig_mean": None})
        best = []
        for oc in orig_num_cols:
            ocx = oc + "_o"
            prc, _, nn = safe_corr(m[pc], m[ocx])
            if pd.notna(prc):
                best.append((oc, round(prc, 4), nn))
        best.sort(key=lambda x: abs(x[1]), reverse=True)
        row["top_match"] = "; ".join(f"{b[0]}(r={b[1]},n={b[2]})" for b in best[:5])
    else:
        # 类别列：一致率
        if same is not None:
            s = pd.DataFrame({"a": m[pc].astype(str), "b": m[same].astype(str)}).dropna()
            agree = (s["a"] == s["b"]).mean() if len(s) else np.nan
            row.update({"same_name_orig": col, "agreement": round(float(agree), 4) if pd.notna(agree) else None,
                        "same_n": len(s),
                        "pipe_levels": str(sorted(m[pc].dropna().astype(str).unique().tolist())[:6]),
                        "orig_levels": str(sorted(m[same].dropna().astype(str).unique().tolist())[:6])})
        else:
            row.update({"same_name_orig": "(无同名列)", "agreement": None, "same_n": None,
                        "pipe_levels": str(sorted(m[pc].dropna().astype(str).unique().tolist())[:6]),
                        "orig_levels": None})
        row["top_match"] = ""
    results.append(row)

res_df = pd.DataFrame(results)
pd.set_option("display.max_colwidth", 130)
pd.set_option("display.width", 260)

print("\n===== 数值/类别指标对比 =====")
num_show = res_df[res_df["type"] == "num"][["pipeline_col", "pipe_nonnull", "same_name_orig",
              "same_pearson", "same_spearman", "same_n", "pipe_mean", "orig_mean"]]
print(num_show.to_string(index=False))
cat_show = res_df[res_df["type"] == "cat"][["pipeline_col", "pipe_nonnull", "same_name_orig",
              "agreement", "same_n", "pipe_levels", "orig_levels"]]
print("\n----- 类别控制变量(一致率) -----")
print(cat_show.to_string(index=False))

print("\n===== 原始面板中的因变量（绩效/风险） =====")
print("原始面板因变量列:", dep_in_orig)
dep_in_pipe = [c for c in pipe.columns if any(k in c.lower() for k in DEP_KEYWORDS)]
print("流水线面板是否含因变量:", dep_in_pipe if dep_in_pipe else "(缺失!)")

out_dir = os.path.dirname(os.path.abspath(__file__))
res_df.to_csv(os.path.join(out_dir, "逐指标验证_结果.csv"), index=False, encoding="utf-8-sig")
with open(os.path.join(out_dir, "逐指标验证_结果.json"), "w", encoding="utf-8") as f:
    json.dump({"pipe_n": len(pipe), "orig_n": len(orig), "merged_n": len(m),
               "results": results, "dep_in_orig": dep_in_orig, "dep_in_pipe": dep_in_pipe},
              f, ensure_ascii=False, indent=2)
print("\n报告已保存: 逐指标验证_结果.csv / .json")
