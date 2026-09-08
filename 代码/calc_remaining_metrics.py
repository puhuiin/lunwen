# -*- coding: utf-8 -*-
"""calc_remaining_metrics.py — L1–L5 行为指标「补充生成脚本」（仓库内真源码）。

为 make_report.py 的 CALC 字典中原标记为 in_repo=False 的 9 个指标提供可运行实现：
    mgr_total_tenure_v2, log_fund_age, industry_hhi, TO_calc, OCI,
    return_volatility, de, lsv, risk_asym
算法依据：《L5数据诊断报告.md》、项目数据字典；引用 Odean(1998)、LSV(1992)、条件波动率差。
所有函数读取 数据/ 下既有原始文件，输出结构与独立指标文件 / 主面板列一致。
运行：python calc_remaining_metrics.py   （默认执行 validate()，打印各指标汇总统计量）
"""
import os
import numpy as np
import pandas as pd

BASE = r"D:\Desktop\基金经理行为分析研究"
D = lambda *p: os.path.join(BASE, "数据", *p)


# ============================ L1 背景特征 ============================
def calc_manager_tenure(obs_date, tenure_csv=None):
    """mgr_total_tenure_v2 = (观测日 − 经理任职起始日).days
    输入：基金经理任职信息.csv [manager_id, start_date, 基金代码]"""
    tenure_csv = tenure_csv or D("L1_背景特征层", "基金经理任职信息.csv")
    df = pd.read_csv(tenure_csv, encoding="utf-8-sig",
                     usecols=["manager_id", "start_date", "基金代码"])
    df["start_date"] = pd.to_datetime(df["start_date"], errors="coerce")
    df["mgr_total_tenure_v2"] = (pd.to_datetime(obs_date) - df["start_date"]).dt.days
    return df[["manager_id", "基金代码", "mgr_total_tenure_v2"]]


def calc_fund_age(obs_date, fund_csv=None):
    """log_fund_age = ln((观测日 − 成立日).days / 30.44)
    输入：基金详细信息_最终版.csv [fund_code, inception_date | 成立日期]"""
    fund_csv = fund_csv or D("L1_背景特征层", "基金详细信息_最终版.csv")
    df = pd.read_csv(fund_csv, encoding="utf-8-sig")
    col = "inception_date" if "inception_date" in df.columns else "成立日期"
    df["_inc"] = pd.to_datetime(df[col], errors="coerce")
    months = (pd.to_datetime(obs_date) - df["_inc"]).dt.days / 30.44
    years = months / 12.0
    df["log_fund_age"] = np.log(years)         # 面板口径：ln(成立至观测期年数)
    return df[["fund_code", "log_fund_age"]]


# ============================ L2 投资决策 ============================
def calc_industry_hhi(industry_csv=None):
    """industry_hhi = Σ w_i²，w_i = 各行业占净值比例之和
    输入：基金行业配置_全量.csv [fund_code, 行业类别, 占净值比例, 截止时间]"""
    f = industry_csv or D("L2_持仓偏离层", "基金行业配置_全量.csv")
    df = pd.read_csv(f, encoding="utf-8-sig")
    # 占净值比例为百分数 → 转成分数权重 w_i，使 Σw_i≈1，HHI=Σw_i² ∈ (0,1]
    df["w"] = pd.to_numeric(df["占净值比例"], errors="coerce").fillna(0) / 100.0
    # 同一行业可能多行 → 先按 (基金,日期,行业) 汇总，再逐 (基金,日期) 求 Σ w_i²
    agg = (df.groupby(["fund_code", "截止时间", "行业类别"])["w"].sum()
             .groupby(["fund_code", "截止时间"]).apply(lambda s: (s ** 2).sum()))
    return agg.rename("industry_hhi").reset_index()


# ============================ L3 交易执行 ============================
def calc_turnover(holdchg_csv=None, fund_csv=None):
    """TO_calc = min(买入,卖出)/平均净资产（剔除申赎被动交易）
    输入：基金持仓变动_批量.csv [fund_code, 季度, 本期累计买入金额]
          （本批次仅含买入金额；卖出以对称假设≈买入，故 TO = 买入/平均净资产）
    平均净资产取 基金详细信息_最终版.csv latest_scale_yi（当期截面近似）。"""
    f = holdchg_csv or D("L3_交易行为层", "基金持仓变动_批量.csv")
    df = pd.read_csv(f, encoding="utf-8-sig")
    df["buy"] = pd.to_numeric(df["本期累计买入金额"], errors="coerce").fillna(0)
    to = df.groupby(["fund_code", "季度"])["buy"].sum().rename("buy_sum").reset_index()
    fund_csv = fund_csv or D("L1_背景特征层", "基金详细信息_最终版.csv")
    fd = pd.read_csv(fund_csv, encoding="utf-8-sig")
    nav = fd.set_index("fund_code")["latest_scale_yi"]
    to["avg_nav"] = to["fund_code"].map(nav) * 1e8          # 亿元 → 元
    # 本期累计买入金额为「千元」，×1000 转元后再除以平均净资产
    to["TO_calc"] = (to["buy_sum"] * 1000 / to["avg_nav"]).replace([np.inf, -np.inf], np.nan)
    return to


def calc_oci(to_df):
    """OCI = (TO − T̄)/σ(TO)，按基金自身历史标准化"""
    to_df = to_df.copy()
    g = to_df.groupby("fund_code")["TO_calc"]
    to_df["OCI"] = (to_df["TO_calc"] - g.transform("mean")) / g.transform("std")
    return to_df


# ============================ L4 风险管理 ============================
def calc_return_volatility(qret_csv=None):
    """return_volatility = 季度收益滚动 8 期标准差
    输入：基金季度收益.csv [fund_code, report_date, quarter_return]"""
    f = qret_csv or D("L4_风险应对层", "基金季度收益.csv")
    df = pd.read_csv(f, encoding="utf-8-sig")
    df = df.sort_values(["fund_code", "report_date"])
    df["return_volatility"] = df.groupby("fund_code")["quarter_return"].transform(
        lambda s: s.rolling(8, min_periods=3).std())
    return df[["fund_code", "report_date", "return_volatility"]]


# ============================ L5 认知偏差 ============================
def calc_de(holdings_csv=None, stock_csv=None, only_612=True, fund_limit=None):
    """de = PGR − PLR（Odean 1998 持仓快照法）
    PGR = gains_sold/(gains_sold+gains_held); PLR = losses_sold/(losses_sold+losses_held)
    输入：基金持仓明细_全量修正版.csv [fund_code, report_date, stock_code, hold_ratio]
          stock_monthly_return: 股价行情/个股月收益率_全量.csv [date, stock_code, monthly_return]
    only_612: 仅用 6/12 月全持仓口径（同《L5数据诊断报告》修复）
    fund_limit: 仅计算前 N 只基金（用于快速验证，None=全部）"""
    h = pd.read_csv(holdings_csv or D("L2_持仓偏离层", "基金持仓明细_全量修正版.csv"),
                    encoding="utf-8-sig")
    h["report_date"] = pd.to_datetime(h["report_date"])
    if only_612:
        h = h[h["report_date"].dt.month.isin([6, 12])]
    sm = pd.read_csv(stock_csv or D("股价行情", "个股月收益率_全量.csv"), encoding="utf-8-sig")
    sm["date"] = pd.to_datetime(sm["date"])
    sm = sm.sort_values(["stock_code", "date"])
    rows = []
    funds = list(h["fund_code"].unique())[:fund_limit]
    for fund in funds:
        fdf = h[h["fund_code"] == fund].sort_values("report_date")
        dates = fdf["report_date"].unique()
        for i in range(1, len(dates)):
            t0, t1 = dates[i - 1], dates[i]
            prev = set(fdf[fdf["report_date"] == t0]["stock_code"])
            cur = set(fdf[fdf["report_date"] == t1]["stock_code"])
            sold = prev - cur   # 上期持有、本期消失 → 实现卖出
            held = prev & cur   # 两期都持有 → 账面持有
            def period_ret(code):
                sub = sm[(sm["stock_code"] == code) & (sm["date"] > t0) & (sm["date"] <= t1)]
                return sub["monthly_return"].sum() if len(sub) else np.nan
            gs = gh = ls = lh = 0
            for c in sold:
                r = period_ret(c)
                if pd.isna(r):
                    continue
                if r > 0: gs += 1
                else: ls += 1
            for c in held:
                r = period_ret(c)
                if pd.isna(r):
                    continue
                if r > 0: gh += 1
                else: lh += 1
            dg, dl = gs + gh, ls + lh
            pgr = gs / dg if dg else np.nan
            plr = ls / dl if dl else np.nan
            de = pgr - plr if (dg and dl) else np.nan
            rows.append((fund, t1, de, pgr, plr, gs, gh, ls, lh))
    out = pd.DataFrame(rows, columns=["fund_code", "report_date", "de", "pgr", "plr",
                                      "gains_sold", "gains_held", "losses_sold", "losses_held"])
    return out


def calc_lsv(holdchg_csv=None):
    """lsv = |p_j − p̄_t| − AF（LSV 1992 横截面趋同度）
    对每季 t、每只股票 j：p_j = 买入该股的基金数 / 交易该股的基金数；
    p̄_t = 当季所有股票 p_j 的均值；AF = 零假设期望偏离（小样本修正，取经验均值）。
    输入：基金持仓变动_批量.csv [fund_code, 季度, 股票代码, 本期累计买入金额]
    返回：基金-季度级 lsv（基金当季交易股票上的 LSV 均值），对齐面板列。"""
    f = holdchg_csv or D("L3_交易行为层", "基金持仓变动_批量.csv")
    df = pd.read_csv(f, encoding="utf-8-sig")
    df["buy"] = pd.to_numeric(df["本期累计买入金额"], errors="coerce").fillna(0)
    df["is_buy"] = df["buy"] > 0
    grp = df.groupby(["季度", "fund_code", "股票代码"])["is_buy"].max().reset_index()
    stock_q = grp.groupby(["季度", "股票代码"]).agg(
        n_buy=("is_buy", "sum"), n_trade=("is_buy", "count")).reset_index()
    stock_q["p_j"] = stock_q["n_buy"] / stock_q["n_trade"]
    pbar = stock_q.groupby("季度")["p_j"].mean().rename("p_bar")
    stock_q = stock_q.merge(pbar, on="季度")
    stock_q["dev"] = (stock_q["p_j"] - stock_q["p_bar"]).abs()
    af = stock_q.groupby("季度")["dev"].mean().rename("AF")   # 小样本修正项（经验均值）
    stock_q = stock_q.merge(af, on="季度")
    stock_q["lsv"] = stock_q["dev"] - stock_q["AF"]
    fund_q = grp.merge(stock_q[["季度", "股票代码", "lsv"]], on=["季度", "股票代码"])
    fund_lsv = fund_q.groupby(["季度", "fund_code"])["lsv"].mean().rename("lsv").reset_index()
    return fund_lsv


def calc_risk_asym(qret_csv=None):
    """risk_asym = σ(盈利期收益) − σ(亏损期收益)（条件波动率不对称）
    输入：基金季度收益.csv [fund_code, report_date, quarter_return]"""
    f = qret_csv or D("L4_风险应对层", "基金季度收益.csv")
    df = pd.read_csv(f, encoding="utf-8-sig")
    def _ra(s):
        gain = s[s > 0]; loss = s[s <= 0]
        sg = gain.std() if len(gain) > 1 else np.nan
        sl = loss.std() if len(loss) > 1 else np.nan
        return sg - sl
    out = df.groupby("fund_code").apply(
        lambda g: pd.Series({"risk_asym": _ra(g["quarter_return"]),
                             "n_gain": int((g["quarter_return"] > 0).sum()),
                             "n_loss": int((g["quarter_return"] <= 0).sum())})
    ).reset_index()
    return out


# ============================ 验证入口 ============================
def validate():
    print("=== validate: calc_remaining_metrics.py ===")
    OBS = "2026-03-31"
    mt = calc_manager_tenure(OBS)
    print(f"[mgr_total_tenure_v2] n={len(mt)} mean={mt['mgr_total_tenure_v2'].mean():.1f} "
          f"min={mt['mgr_total_tenure_v2'].min()} max={mt['mgr_total_tenure_v2'].max()}")
    fa = calc_fund_age(OBS)
    print(f"[log_fund_age]      n={len(fa)} mean={fa['log_fund_age'].mean():.3f} "
          f"min={fa['log_fund_age'].min():.3f} max={fa['log_fund_age'].max():.3f}")
    ih = calc_industry_hhi()
    print(f"[industry_hhi]      n={len(ih)} mean={ih['industry_hhi'].mean():.4f} "
          f"median={ih['industry_hhi'].median():.4f}")
    to = calc_turnover()
    print(f"[TO_calc]           n={len(to)} mean={to['TO_calc'].mean():.4f} "
          f"median={to['TO_calc'].median():.4f}")
    to = calc_oci(to)
    print(f"[OCI]               mean={to['OCI'].mean():.4f} std~{to['OCI'].std():.4f} "
          f"(理论均值≈0)")
    rv = calc_return_volatility()
    print(f"[return_volatility] n={len(rv)} mean={rv['return_volatility'].mean():.4f} "
          f"median={rv['return_volatility'].median():.4f}")
    ra = calc_risk_asym()
    print(f"[risk_asym]         n={len(ra)} mean={ra['risk_asym'].mean():.4f} "
          f"median={ra['risk_asym'].median():.4f}")
    lsv = calc_lsv()
    print(f"[lsv]               n={len(lsv)} mean={lsv['lsv'].mean():.4f} "
          f"median={lsv['lsv'].median():.4f}")
    de = calc_de(fund_limit=12)   # 仅前 12 只基金做快速验证
    print(f"[de] (subset 12 funds) n={len(de)} mean={de['de'].mean():.4f} "
          f"pgr={de['pgr'].mean():.3f} plr={de['plr'].mean():.3f}")
    print("=== done ===")


if __name__ == "__main__":
    validate()
