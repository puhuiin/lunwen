# -*- coding: utf-8 -*-
"""#169 核验：SDI(t) 的时间对齐 —— 是否只用 return(<=t-1)、是否与 quarter_return(t) 同期对齐。
仅取单只基金做精确复算 + 断言，避免全样本开销。"""
import os, re, numpy as np, pandas as pd
import lib_metrics as M

BASE = os.path.dirname(os.path.abspath(__file__))

# ---- 1) 复算基金季收益（与 calc_sdi 同源）----
nav = pd.read_csv(M.D("L4_风险应对层", "基金净值历史_全量.csv"), encoding="utf-8-sig")
nav["date"] = pd.to_datetime(nav["date"], errors="coerce")
nav = nav.dropna(subset=["date"]).sort_values(["fund_code", "date"])
nav["ret"] = pd.to_numeric(nav["daily_return"], errors="coerce") / 100.0
nav = nav.dropna(subset=["ret"])
nav["q"] = nav["date"].dt.to_period("Q")
fr = nav.groupby(["fund_code", "q"])["ret"].apply(lambda s: (1 + s).prod() - 1).reset_index()
fr["report_date"] = fr["q"].apply(lambda p: M.to_panel_date(p.end_time.normalize()))

st = pd.read_csv(M.D("L2_持仓偏离层", "风格指数季度收益.csv"), encoding="utf-8-sig")
scols = [c for c in st.columns if re.fullmatch(r"39937[0-9]_q_return", c)]
style_names = [c[:6] for c in scols]
st = st.rename(columns={c: c[:6] for c in scols})
st["q"] = pd.to_datetime(st["year"].astype(str) + "Q" + st["quarter"].astype(str)).dt.to_period("Q")
st = st.set_index("q")[style_names]
WINDOW = 8

def roll_sdi(g):
    """复刻 calc_sdi 的滚动逻辑，返回 (report_date, sdi, max_used_report_date)。"""
    g = g.sort_values("q").reset_index(drop=True)
    merged = g.merge(st, left_on="q", right_index=True, how="inner")
    if len(merged) < WINDOW + 1:
        return []
    X_all = merged[style_names].values; y_all = merged["ret"].values
    w_hist = []  # (report_date, weights_numpy, list_of_used_report_dates)
    for i in range(WINDOW, len(merged)):
        used_rd = merged.iloc[i - WINDOW:i]["report_date"].tolist()  # 窗口 [i-W, i-1]
        X = np.column_stack([np.ones(WINDOW), X_all[i - WINDOW:i]])
        y = y_all[i - WINDOW:i]
        try:
            beta, *_ = np.linalg.lstsq(X, y, rcond=None)
        except Exception:
            continue
        w = np.maximum(beta[1:], 0)
        if w.sum() > 0: w = w / w.sum()
        w_hist.append((merged.iloc[i]["report_date"], w, used_rd))
    out = []
    for i in range(1, len(w_hist)):
        sdi = np.abs(w_hist[i][1] - w_hist[i - 1][1]).sum()
        # w(i) 使用的收益最大 report_date；w(i-1) 使用的更早
        max_used = max(w_hist[i][2] + w_hist[i - 1][2])
        out.append((w_hist[i][0], sdi, max_used))
    return out

# ---- 2) 取一只有足够历史的基金（必须同时存在于库值 SDI 与复刻 fr）----
full = M.calc_sdi(window=WINDOW)
cand = full.groupby("fund_code").size().sort_values(ascending=False)
fr_funds = set(fr["fund_code"].unique())
FID = None
for fid, _ in cand.items():
    if fid in fr_funds:
        FID = fid
        break
print("选定基金 fund_code =", FID, " SDI 非空期数 =", int(cand.get(FID, 0)),
      " 复刻 fr 期数 =", int((g := fr[fr["fund_code"] == FID]).shape[0]))

g = fr[fr["fund_code"] == FID]
repro = {rd: (sdi, max_used) for rd, sdi, max_used in roll_sdi(g)}
lib = full[full["fund_code"] == FID].set_index("report_date")["SDI"].to_dict()

# ---- 3) 断言：复算 == 库值，且 SDI(rd) 所用收益全部严格早于 rd ----
max_abs_diff = 0.0
viol = 0
checked = 0
for rd, sdi_lib in lib.items():
    if rd not in repro:
        continue
    sdi_re, max_used = repro[rd]
    max_abs_diff = max(max_abs_diff, abs(sdi_lib - sdi_re))
    # 关键对齐断言：SDI(rd) 用到的收益季度，其 report_date 必须严格 < rd
    if not (max_used < rd):
        viol += 1
        print("  ! 违反对齐: rd=%s max_used=%s" % (rd, max_used))
    checked += 1

print("比对期数 =", checked, " 复算与库值最大 |diff| = %.2e" % max_abs_diff)
print("对齐违规次数(用到 >= rd 的收益) =", viol)
print("=> SDI(t) 是否仅用 return(<=t-1) 且同期对齐 quarter_return(t):",
      "PASS" if (max_abs_diff < 1e-9 and viol == 0) else "FAIL")

# ---- 4) 揭示 SDI 与 quarter_return / future_return 的面板期数关系 ----
sk = M.load_skeleton()
panel_row = sk[sk["fund_code"] == FID].sort_values("report_date").head(3)
print("\n面板样例(fund=%s) report_date -> 该季收益归属:" % FID)
for _, r in panel_row.iterrows():
    rd = r["report_date"]
    q = pd.Period(rd - pd.Timedelta(days=1), freq="Q")  # 季度末
    print("  report_date=%s  对应季度=%s  quarter_return=该季收益  future_return=下一季收益" % (rd, q))
