# -*- coding: utf-8 -*-
"""
lib_metrics.py — 基金经理行为指标「统一计算库」（离线、纯本地数据）
================================================================
本文件是「指标计算流水线」的唯一计算源码，被 01~05 各分层步骤脚本调用。
所有函数读取 ./data/ 下的本地 CSV（已与源码放在一起），不依赖 AKShare / 网络。

指标覆盖（L1–L5，共 13 个行为指标 + 4 个控制变量）：
  L1 背景特征 : mgr_total_tenure_v2, log_fund_age, gender/education/CFA/school(控制)
  L2 持仓偏离 : AS_improved, ICI(归一化), industry_hhi(归一化), ICI_raw, industry_hhi_raw
  L3 交易执行 : SDI, TO_two_sided(真·双边), OCI_two_sided
  L4 风险应对 : ARG, return_volatility
  L5 认知偏差 : de, lsv, risk_asym

日期约定（重要）：
  各原始文件的日期多为「季度末/半年末」(如 2020-03-31, 2018-06-30)。
  主面板的 report_date = 季度末 + 1 天（如 2020-04-01），即「该季度开始的日期」。
  本库统一用 to_panel_date() 把计算出的指标对齐到面板这一约定，便于 99_合并面板 精确拼接。
"""
import os
import re
import time
import warnings
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

# 自动智能定位数据目录：
# 1. 优先使用环境变量 LIB_DATA（若指定）
# 2. 其次探测同级上层的「原始数据」目录 (论文复现/原始数据)
# 3. 再次探测本目录下的 data/ 或上级目录下的 data/
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_candidate_dirs = [
    os.environ.get("LIB_DATA"),
    os.path.join(os.path.dirname(BASE_DIR), "原始数据"),
    os.path.join(BASE_DIR, "data"),
    os.path.join(os.path.dirname(BASE_DIR), "data"),
]
DATA = None
for _d in _candidate_dirs:
    if _d and os.path.exists(_d):
        DATA = _d
        break
if DATA is None:
    DATA = os.path.join(os.path.dirname(BASE_DIR), "原始数据")


def D(*p):
    return os.path.join(DATA, *p)


# ============================================================
# 通用工具
# ============================================================
def to_panel_date(s):
    """原始「季度末/半年末」日期 → 面板约定(report_date = 季度末 + 1 天)。"""
    dt = pd.to_datetime(s, errors="coerce")
    return dt + pd.Timedelta(days=1)


def _safe_div(a, b):
    out = a / b.replace(0, np.nan)
    return out.replace([np.inf, -np.inf], np.nan)


# ============================================================
# 基准权重（AS / ICI 用）：沪深300(真实权重) + 中证500(等权) 合并后归一
# ============================================================
def load_benchmark_weights():
    """返回 Series: stock_code -> 归一化权重 (Σ=1)。"""
    hs = pd.read_csv(D("L2_持仓偏离层", "沪深300成分股权重_真实.csv"), encoding="utf-8-sig")
    hs = hs[["stock_code", "bench_weight"]].copy()
    hs["w"] = pd.to_numeric(hs["bench_weight"], errors="coerce")
    cs = pd.read_csv(D("基金基础信息", "中证500成分股.csv"), encoding="utf-8-sig")
    cs = cs[["stock_code", "weight"]].copy()
    cs["w"] = pd.to_numeric(cs["weight"], errors="coerce")
    bench = pd.concat([hs[["stock_code", "w"]], cs[["stock_code", "w"]]], ignore_index=True)
    bench = bench.dropna(subset=["w"])
    bench = bench.groupby("stock_code")["w"].sum().reset_index()
    bench["w"] = bench["w"] / bench["w"].sum()          # 归一化到 Σ=1
    return bench.set_index("stock_code")["w"]


# ============================================================
# L1 背景特征
# ============================================================
def _manager_fund_map():
    """从「基金经理任职信息.csv」(宽表：基金代码是列名，单元格=基金概况串) 还原 基金→经理 映射。
    单元格形如 '华夏X | ... | 2026-02-10 ~ 至今 | 177天 | 31.85%'。
    提取每只经理在该基金的任职起止日：
      start_date = '~' 前的首个 YYYY-MM-DD；
      end_date   = '~' 后的首个 YYYY-MM-DD；若为 '至今/现在' 则留空(仍在任)。
    一只基金可有多个经理(多段任职)。返回 manager_id, fund_code(int), start_date, end_date。"""
    ten = pd.read_csv(D("L1_背景特征层", "基金经理任职信息.csv"), encoding="utf-8-sig")
    fund_cols = [c for c in ten.columns if re.fullmatch(r"\d{6}", str(c))]
    melt = ten.melt(id_vars=["manager_id"], value_vars=fund_cols,
                    var_name="fund_code", value_name="cell")
    melt = melt.dropna(subset=["cell"])
    melt["fund_code"] = melt["fund_code"].astype(int)
    melt["start_date"] = pd.to_datetime(
        melt["cell"].str.extract(r"(\d{4}-\d{2}-\d{2})\s*~")[0], errors="coerce")
    # '~' 之后若为具体日期则取之；'至今/现在' → NaT(仍在任)
    end_raw = melt["cell"].str.extract(r"~\s*([\d]{4}-[\d]{2}-[\d]{2})")[0]
    melt["end_date"] = pd.to_datetime(end_raw, errors="coerce")
    melt = melt.dropna(subset=["start_date"])
    return melt[["manager_id", "fund_code", "start_date", "end_date"]]


def _active_manager(mp, fund, rd):
    """在 (fund, report_date=rd) 时刻「在任」的经理：start_date <= rd 且
    (end_date 缺失 或 end_date >= rd)。多人在任时取最近开始任职者(末位)。"""
    sub = mp[mp["fund_code"] == fund]
    active = sub[(sub["start_date"] <= rd) &
                 (sub["end_date"].isna() | (sub["end_date"] >= rd))]
    if len(active) == 0:
        return None
    return active.sort_values("start_date").iloc[-1]


def calc_manager_tenure(skeleton):
    """mgr_total_tenure_v2 = (report_date − 该期末在任经理的任职起始日).days。
    修复：原实现取「全期最早任职经理」，会导致早期季度的 tenure 为负(起始日>报告日)。
    现改为取 report_date 时刻「在任」经理(始<=报告日<=止)，任期不可能为负。"""
    mp = _manager_fund_map()
    sk = skeleton[["fund_code", "report_date"]].copy()
    sk["report_date"] = pd.to_datetime(sk["report_date"], errors="coerce")
    rows = []
    for (fund, rd), _ in sk.groupby(["fund_code", "report_date"]):
        mgr = _active_manager(mp, fund, rd)
        rows.append((fund, rd, (rd - mgr["start_date"]).days if mgr is not None else np.nan))
    out = pd.DataFrame(rows, columns=["fund_code", "report_date", "mgr_total_tenure_v2"])
    return out.sort_values(["fund_code", "report_date"]).reset_index(drop=True)


def calc_fund_age(skeleton):
    """log_fund_age = ln((report_date − 成立日).days / 30.44 / 12)  —— 面板口径 ln(年)。"""
    fd = pd.read_csv(D("L1_背景特征层", "基金详细信息_最终版.csv"), encoding="utf-8-sig")
    col = "inception_date" if "inception_date" in fd.columns else "成立日期"
    fd = fd[["fund_code", col]].copy()
    fd["_inc"] = pd.to_datetime(fd[col], errors="coerce")
    sk = skeleton[["fund_code", "report_date"]].copy()
    sk = sk.merge(fd, on="fund_code", how="left")
    yrs = (pd.to_datetime(sk["report_date"]) - sk["_inc"]).dt.days / 30.44 / 12.0
    sk["log_fund_age"] = np.log(yrs)
    return sk[["fund_code", "report_date", "log_fund_age"]]


def calc_control_vars(skeleton):
    """控制变量 gender/education/CFA/school：取 report_date 时刻「在任」经理的个人特征
    （与 calc_manager_tenure 同一口径，保证 traits 与任期来自同一经理）。"""
    mp = _manager_fund_map()[["manager_id", "fund_code", "start_date", "end_date"]]
    info = pd.read_csv(D("L1_背景特征层", "基金经理信息_最终版.csv"), encoding="utf-8-sig")
    info = info[["manager_id", "school", "education", "gender", "CFA"]].drop_duplicates("manager_id")
    sk = skeleton[["fund_code", "report_date"]].copy()
    sk["report_date"] = pd.to_datetime(sk["report_date"], errors="coerce")
    rows = []
    for (fund, rd), _ in sk.groupby(["fund_code", "report_date"]):
        mgr = _active_manager(mp, fund, rd)
        rows.append((fund, rd, mgr["manager_id"] if mgr is not None else None))
    mmap = pd.DataFrame(rows, columns=["fund_code", "report_date", "manager_id"])
    cv = mmap.merge(info, on="manager_id", how="left")
    cv = cv.drop_duplicates(["fund_code", "report_date"])
    return cv[["fund_code", "report_date", "school", "education", "gender", "CFA"]]


# ============================================================
# L2 持仓偏离
# ============================================================
def calc_active_share():
    """AS_improved = ½ Σ|w_fund − w_bench|，基准=沪深300+中证500合并权重。
    输入：基金持仓明细_全量修正版_v3.csv [fund_code, report_date, stock_code, hold_ratio(%)]"""
    bench = load_benchmark_weights()
    h = pd.read_csv(D("L2_持仓偏离层", "基金持仓明细_全量修正版_v3.csv"), encoding="utf-8-sig")
    h["w_fund"] = pd.to_numeric(h["hold_ratio"], errors="coerce").fillna(0) / 100.0
    h["report_date"] = to_panel_date(h["report_date"])
    rows = []
    for (fund, rd), g in h.groupby(["fund_code", "report_date"]):
        merged = pd.merge(
            g[["stock_code", "w_fund"]],
            bench.rename("w_bench").reset_index(),
            on="stock_code", how="outer").fillna(0)
        as_val = 0.5 * (merged["w_fund"] - merged["w_bench"]).abs().sum()
        rows.append((fund, rd, min(as_val, 1.0)))
    out = pd.DataFrame(rows, columns=["fund_code", "report_date", "AS_improved"])
    return out.sort_values(["fund_code", "report_date"])


# ============================================================================
# 行业分类归一化：把「基金行业配置_全量.csv」的 82 个混标 → 申万31（权威名单见
# 数据/L2_持仓偏离层/申万一级行业分类.csv，共 31 个行业名称）。
# 该文件的 行业类别 列混写了 证监会19门类 / 申万一级 / 中信一级 / GICS(数字码+中英文)
# 至少 4 套体系，同一真实行业被多种命名重复拆分（如「信息技术」有 7 种写法）。
# 归一规则：每个原始标签 → 其代表的申万31行业集合；该标签权重在集合内**等权拆分**
# （粗分类无法还原真实分布，等权是最透明的中性假设）。返回长表 w 已按基金-期归一(Σ=1)。
# ============================================================================
SW31_MAP = {
    # ---- GICS 数字码 (10/15/20/25/30/35/40/45/50/55/60) ----
    "10能源": ["石油石化", "煤炭"],
    "15原材料": ["基础化工", "钢铁", "有色金属", "煤炭"],
    "20工业": ["机械设备", "建筑装饰", "国防军工", "电力设备", "汽车"],
    "25可选消费": ["商贸零售", "家用电器", "汽车", "纺织服饰", "轻工制造"],
    "30主要消费": ["食品饮料"],
    "30日常消费": ["食品饮料"],
    "35医药卫生": ["医药生物"],
    "40金融": ["银行", "非银金融"],
    "45信息技术": ["电子", "计算机", "通信", "传媒"],
    "50电信服务": ["通信"],
    "50通信服务": ["通信"],
    "55公用事业": ["公用事业", "环保"],
    "60房地产": ["房地产"],
    # ---- 字母前缀 (A基础材料 / B消费者非必需品 / ... GICS 变体) ----
    "A基础材料": ["基础化工", "钢铁", "有色金属"],
    "B消费者非必需品": ["商贸零售", "家用电器", "汽车", "纺织服饰", "轻工制造"],
    "C消费者常用品": ["食品饮料"],
    "D能源": ["石油石化", "煤炭"],
    "E金融": ["银行", "非银金融"],
    "F医疗保健": ["医药生物"],
    "G工业": ["机械设备", "建筑装饰", "国防军工", "电力设备", "汽车"],
    "H信息技术": ["电子", "计算机", "通信", "传媒"],
    "I电信服务": ["通信"],
    "K房地产": ["房地产"],
    # ---- 中信一级 (中文短名) ----
    "主要消费": ["食品饮料"],
    "可选消费": ["商贸零售", "家用电器", "汽车", "纺织服饰", "轻工制造"],
    "原材料": ["基础化工", "钢铁", "有色金属"],
    "工业": ["机械设备", "建筑装饰", "国防军工", "电力设备", "汽车"],
    "能源": ["石油石化", "煤炭"],
    "公用事业": ["公用事业", "环保"],
    "金融": ["银行", "非银金融"],
    "医疗保健": ["医药生物"],
    "信息技术": ["电子", "计算机", "通信", "传媒"],
    "电信服务": ["通信"],
    "房地产": ["房地产"],
    "材料": ["基础化工", "钢铁", "有色金属"],
    "基础材料": ["基础化工", "钢铁", "有色金属"],
    # ---- 证监会19门类 (中文全称) ----
    "交通运输、仓储和邮政业": ["交通运输"],
    "住宿和餐饮业": ["社会服务"],
    "信息传输、软件和信息技术服务业": ["电子", "计算机", "通信", "传媒"],
    "制造业": ["食品饮料", "纺织服饰", "轻工制造", "家用电器", "医药生物", "汽车",
            "机械设备", "电力设备", "电子", "计算机", "通信", "传媒",
            "国防军工", "基础化工", "钢铁", "有色金属", "建筑材料"],
    "房地产业": ["房地产"],
    "建筑业": ["建筑装饰"],
    "批发和零售业": ["商贸零售"],
    "农、林、牧、渔业": ["农林牧渔"],
    "采矿业": ["石油石化", "煤炭", "有色金属"],
    "电力、热力、燃气及水生产和供应业": ["公用事业"],
    "水利、环境和公共设施管理业": ["环保"],
    "科学研究和技术服务业": ["综合"],
    "租赁和商务服务业": ["商贸零售"],
    "卫生和社会工作": ["医药生物"],
    "文化、体育和娱乐业": ["传媒"],
    "教育": ["社会服务"],
    "综合": ["综合"],
    "金融业": ["银行", "非银金融"],
    # ---- GICS 英文 / 中英混排 ----
    "保健": ["医药生物"],
    "保健HealthCare": ["医药生物"],
    "医药卫生": ["医药生物"],
    "能源Energy": ["石油石化", "煤炭"],
    "金融Financials": ["银行", "非银金融"],
    "信息技术Information": ["电子", "计算机", "通信", "传媒"],
    "信息技术InformationTechnology": ["电子", "计算机", "通信", "传媒"],
    "信息科技": ["电子", "计算机", "通信", "传媒"],
    "科技": ["电子", "计算机", "通信", "传媒"],
    "必需消费品": ["食品饮料"],
    "日常消费品": ["食品饮料"],
    "消费者常用品": ["食品饮料"],
    "消费者非必需品": ["商贸零售", "家用电器", "汽车", "纺织服饰", "轻工制造"],
    "电信业务": ["通信"],
    "通信服务": ["通信"],
    "通信服务Communication": ["通信"],
    "通信服务CommunicationServices": ["通信"],
    "通讯": ["通信"],
    "通讯业务": ["通信"],
    "通讯服务": ["通信"],
    "非周期性消费品": ["食品饮料"],
    "非必需消费": ["商贸零售", "家用电器", "汽车", "纺织服饰", "轻工制造"],
    "非必需消费品": ["商贸零售", "家用电器", "汽车", "纺织服饰", "轻工制造"],
    "非必需消费品Consumer": ["商贸零售", "家用电器", "汽车", "纺织服饰", "轻工制造"],
    "非必需消费品ConsumerDiscretionary": ["商贸零售", "家用电器", "汽车", "纺织服饰", "轻工制造"],
    "非必须消费品": ["商贸零售", "家用电器", "汽车", "纺织服饰", "轻工制造"],
    "非日常生活消费品": ["商贸零售", "家用电器", "汽车", "纺织服饰", "轻工制造"],
    "金融信息技术": ["计算机"],
}


def _norm_industry():
    """[DEPRECATED] 82 混标 → 申万31 等权归一（数据质量事故口径，已废弃）。
    现 ICI / industry_hhi 改用 _load_hhi_merged() 读取股票级聚合成品，见 calc_ici / calc_industry_hhi。"""
    """把 82 混标 → 申万31 长表 [fund_code, report_date, sw31, w]。
    w 为归一化权重(同一基金-期 Σ=1)：原始标签权重在其映射到的申万31集合内等权拆分，
    再按 (基金,期,申万行业) 累加。"""
    sw = pd.read_csv(D("L2_持仓偏离层", "申万一级行业分类.csv"), encoding="utf-8-sig")
    valid = set(sw["行业名称"].tolist())
    df = pd.read_csv(D("L2_持仓偏离层", "基金行业配置_全量.csv"), encoding="utf-8-sig")
    df["w"] = pd.to_numeric(df["占净值比例"], errors="coerce").fillna(0) / 100.0
    df["report_date"] = to_panel_date(df["截止时间"])
    rows, unmapped = [], set()
    for _, r in df.iterrows():
        labs = SW31_MAP.get(r["行业类别"])
        if labs is None:
            unmapped.add(r["行业类别"])
            continue
        share = r["w"] / len(labs)
        for sw31 in labs:
            if sw31 in valid:
                rows.append((r["fund_code"], r["report_date"], sw31, share))
    if unmapped:
        print("  [行业归一] 未匹配标签(已丢弃权重):", sorted(unmapped))
    out = pd.DataFrame(rows, columns=["fund_code", "report_date", "sw31", "w"])
    out = out.groupby(["fund_code", "report_date", "sw31"])["w"].sum().reset_index()
    return out


# ============================================================================
# L2 行业集中度（ICI / industry_hhi）—— 股票级持仓 → 申万31 聚合（推荐口径）
# ----------------------------------------------------------------------------
# 数据源：data/L2_持仓偏离层/行业集中度HHI_申万31.csv
#   由用户经 AKShare 下载的 stock_code→申万一级映射（股票行业映射.csv，5203只，覆盖99.2%）
#   对 基金持仓明细_全量修正版_v3.csv（股票级 hold_ratio）按股票聚到申万31 后计算，
#   含 4 个口径：industry_hhi(原始NAV权重) / hhi_normalized(权重归一化Σ=1) /
#                ICI(原始) / ICI_normalized(归一化)。
# 日期对齐：文件仅含 (fund_code, year, quarter)，用持仓文件 (fund_code,year,quarter)
#           → report_date(+1天) 还原，保证与骨架/面板完全对齐。
# 采用口径：industry_hhi / ICI 取「归一化」版本（Σ权重=1，消除基金股票仓位高低
#           对集中度的机械干扰，更贴近原面板 0.26 量纲）；原始版本并列保留供复核。
# 旧 _norm_industry()（82混标→申万31等权）已废弃，见底部 deprecated 段。
# ============================================================================
def _load_hhi_merged():
    """读取申万31行业集中度成品，并用持仓文件还原 report_date(面板+1天约定)。"""
    hhi = pd.read_csv(D("L2_持仓偏离层", "行业集中度HHI_申万31.csv"), encoding="utf-8-sig")
    h = pd.read_csv(D("L2_持仓偏离层", "基金持仓明细_全量修正版_v3.csv"),
                    usecols=["fund_code", "report_date", "year", "quarter"], low_memory=False)
    h["report_date"] = to_panel_date(h["report_date"])
    key = h[["fund_code", "year", "quarter", "report_date"]].drop_duplicates()
    out = hhi.merge(key, on=["fund_code", "year", "quarter"], how="left")
    return out


def calc_industry_hhi():
    """industry_hhi = hhi_normalized（行业权重归一化到 Σ=1 的申万31 HHI），口径推荐。"""
    df = _load_hhi_merged()
    return df[["fund_code", "report_date", "hhi_normalized"]].rename(
        columns={"hhi_normalized": "industry_hhi"}).dropna(subset=["report_date"])


def calc_industry_hhi_raw():
    """industry_hhi_raw = 原始 NAV 权重 HHI（Σw<1），并列保留供复核。"""
    df = _load_hhi_merged()
    return df[["fund_code", "report_date", "industry_hhi"]].rename(
        columns={"industry_hhi": "industry_hhi_raw"}).dropna(subset=["report_date"])


def calc_ici():
    """ICI = ICI_normalized（归一化权重的行业偏离平方和），口径推荐。"""
    df = _load_hhi_merged()
    return df[["fund_code", "report_date", "ICI_normalized"]].rename(
        columns={"ICI_normalized": "ICI"}).dropna(subset=["report_date"])


def calc_ici_raw():
    """ICI_raw = 原始权重行业偏离平方和，并列保留供复核。"""
    df = _load_hhi_merged()
    return df[["fund_code", "report_date", "ICI"]].rename(
        columns={"ICI": "ICI_raw"}).dropna(subset=["report_date"])


def calc_isdi():
    """ISDI(行业风格漂移) = 相邻报告期 高/中/低beta行业组 权重向量的曼哈顿距离。
    分组：31个申万一级行业按Beta（行业与市场涨跌幅相关性/弹性评分）三分
    （高弹性11个/中弹性10个/低弹性10个），数据源 backups/行业弹性/申万一级行业弹性评分_20260809.xlsx。
    构建路径：持仓明细(重仓股) → 股票行业映射 → 弹性组 → 组权重归一化 → 相邻期|Δw|之和。
    与SDI互补：SDI基于净值回归看"结果风格"，ISDI基于实际持仓看"配置行为"（两者相关性≈-0.05）。
    结果缓存于 data/L2_持仓偏离层/行业风格漂移ISDI.csv（report_date已按面板口径=期末+1天）。"""
    import pandas as _pd
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cache = D("L2_持仓偏离层", "行业风格漂移ISDI.csv")
    if os.path.exists(cache):
        out = _pd.read_csv(cache, encoding="utf-8-sig")
        out["report_date"] = pd.to_datetime(out["report_date"], errors="coerce")
        return out

    el = _pd.read_excel(os.path.join(root, "backups", "行业弹性",
                                     "申万一级行业弹性评分_20260809.xlsx"))[["行业", "弹性等级"]]
    grp_map = dict(zip(el["行业"], el["弹性等级"]))
    grp_order = ["高弹性", "中弹性", "低弹性"]

    h = pd.read_csv(D("L2_持仓偏离层", "基金持仓明细_全量修正版_v3.csv"),
                    encoding="utf-8-sig", low_memory=False)
    h["stock_code"] = h["stock_code"].astype(str).str.zfill(6)
    h["w"] = pd.to_numeric(h["hold_ratio"], errors="coerce").fillna(0) / 100.0

    m = pd.read_csv(D("L2_持仓偏离层", "股票行业映射.csv"), encoding="utf-8-sig")
    m["stock_code"] = m["stock_code"].astype(str).str.zfill(6)
    stock2grp = dict(zip(m["stock_code"], m["sw31_industry"].map(grp_map)))
    h["grp"] = h["stock_code"].map(stock2grp)
    h = h.dropna(subset=["grp"])

    pv = h.pivot_table(index=["fund_code", "report_date"], columns="grp",
                       values="w", aggfunc="sum").fillna(0.0)
    pv = pv.reindex(columns=grp_order)
    pv = pv.div(pv.sum(axis=1).replace(0, np.nan), axis=0).dropna()

    rows = []
    for fund, g in pv.groupby(level=0):
        g = g.sort_index(level=1)
        W, dates = g.values, g.index.get_level_values(1)
        for i in range(1, len(W)):
            rows.append((fund, dates[i], np.abs(W[i] - W[i - 1]).sum()))
    out = pd.DataFrame(rows, columns=["fund_code", "report_date", "ISDI"])
    out["report_date"] = pd.to_datetime(out["report_date"], errors="coerce") + pd.Timedelta(days=1)
    out.to_csv(cache, index=False, encoding="utf-8-sig")
    return out.sort_values(["fund_code", "report_date"])


# ============================================================
# L3 交易执行
# ============================================================
def _parse_quarter(cn):
    """'2023年4季度累计买入股票明细' → (2023, 4)。"""
    y = re.search(r"(\d{4})年", str(cn))
    q = re.search(r"(\d)季度", str(cn))
    if not (y and q):
        return None, None
    return int(y.group(1)), int(q.group(1))


def _quarter_end(y, q):
    return pd.Period(year=y, quarter=q, freq="Q").end_time.normalize()


def calc_turnover_two_sided():
    """双边换手率（真·含卖出侧）——本仓库换手率唯一主变量（自 2026-08-12 起移除单边口径）。
    数据源：data/L3_交易行为层/基金换手率_双边_含卖出.csv
    （原项目 数据/无用数据/基金换手率_计算值.csv，曾被误归为“无用数据”）。
    列：total_buy, total_sell, avg_aum, turnover_rate。
    校验：turnover_rate == (total_buy+total_sell)/(2*avg_aum)，最大误差≈0（标准双边换手率）。
    公式：TO_two_sided = (total_buy + total_sell) / (2 * avg_aum)。
    覆盖：200 只基金、2020H2–2024H2（半年频，9 个快照，面板 report_date +1 天后为 2021Q1–2025Q1），
          约骨架 33.3%。缺失季度为 NaN，论文以该双边子集为分析样本并说明口径限制。
    返回：fund_code, report_date(+1天对齐面板), TO_two_sided, OCI_two_sided,
          total_buy, total_sell, avg_aum。"""
    f = D("L3_交易行为层", "基金换手率_双边_含卖出.csv")
    df = pd.read_csv(f, encoding="utf-8-sig")
    df["report_date"] = pd.to_datetime(df["report_date"], errors="coerce")
    df["report_date"] = df["report_date"].apply(to_panel_date)  # +1天对齐面板约定
    # avg_aum 现统一取自「基金规模历史_批量.csv」的 net_asset（亿元，公开披露口径，已与基金详情校验）。
    # TO_two_sided / OCI_two_sided 为预先在原始换手率文件内、以「(买入+卖出)/(2×平均净资产)」一致口径
    # 算出的比率，存于源文件；不再用 scale 版 avg_aum 重算（否则量级失真导致换手率虚高）。
    if "TO_two_sided" not in df.columns or df["TO_two_sided"].isna().all():
        df["TO_two_sided"] = (df["total_buy"] + df["total_sell"]) / (2.0 * df["avg_aum"].replace(0, np.nan))
    if "OCI_two_sided" not in df.columns or df["OCI_two_sided"].isna().all():
        g = df.groupby("fund_code")["TO_two_sided"]
        df["OCI_two_sided"] = (df["TO_two_sided"] - g.transform("mean")) / g.transform("std")
    df["avg_aum"] = df["avg_aum"].astype(float)
    return df[["fund_code", "report_date", "TO_two_sided", "OCI_two_sided",
               "total_buy", "total_sell", "avg_aum"]].sort_values(
        ["fund_code", "report_date"])


def calc_avg_aum():
    """基金规模控制变量（avg_aum）取自「基金规模历史_批量.csv」的 net_asset（亿元，公开披露口径）。

    与换手率(TO)的 200 只子集**解耦**：avg_aum 覆盖全部 400 只基金 × 全季度，
    而 TO/OCI/total_buy/total_sell 仅 200 只（源文件半年频）。这样规模控制变量可扩至
    全样本（~98%），使“不含 TO”的回归突破 200 基金上限，而“含 TO”的回归自然受 TO 覆盖约束。

    实现：net_asset 按 (fund_code, year, quarter) 聚合取均值（亿元），再经骨架的
    (year, quarter) -> report_date 唯一映射并入面板。

    返回：fund_code, report_date, avg_aum。"""
    f = D("L1_背景特征层", "基金规模历史_批量.csv")
    s = pd.read_csv(f, encoding="utf-8-sig")
    s = s.dropna(subset=["fund_code", "year", "quarter", "net_asset"])
    s["fund_code"] = pd.to_numeric(s["fund_code"], errors="coerce").astype("int64")
    s["year"] = s["year"].astype(int)
    s["quarter"] = s["quarter"].astype(int)
    agg = s.groupby(["fund_code", "year", "quarter"], as_index=False)["net_asset"].mean()
    agg = agg.rename(columns={"net_asset": "avg_aum"})
    # 数据严谨性（2026-08-14 修复）：源文件 net_asset<=0 为「缺报占位 0.0」而非真实规模
    # （如基金 1407/2163 多季为 0）。若保留 0，log_aum=log(clip(0,1))=0 会把这些行
    # 误当作「1 亿规模」纳入回归，造成隐蔽偏差。故置 NaN，使其在回归中自然剔除。
    agg.loc[agg["avg_aum"] <= 0, "avg_aum"] = np.nan
    # (year, quarter) -> report_date 唯一映射（取自骨架）
    sk = load_skeleton()[["year", "quarter", "report_date"]].drop_duplicates()
    sk["year"] = sk["year"].astype(int)
    sk["quarter"] = sk["quarter"].astype(int)
    agg = agg.merge(sk, on=["year", "quarter"], how="left")
    agg["report_date"] = pd.to_datetime(agg["report_date"], errors="coerce")
    return agg[["fund_code", "report_date", "avg_aum"]]


def calc_sdi(window=8):
    """SDI = 滚动OLS(基金季收益 ~ 4风格指数)后相邻权重向量的曼哈顿距离。
    输入：基金净值历史_全量.csv(算基金季收益) + 风格指数季度收益.csv(4风格:399372/3/6/7，标准大盘成长/大盘价值/小盘成长/小盘价值四宫格)。
    窗口=8（2026-08-12 由12改为8；2026-08-25 修正399374→399372为正确大盘成长角）：
    暖机期从12季降到8季，SDI首次可用提前到2022Q2，有效跨度≈4.5年、覆盖提升；权重估计用8期仍稳健。
    注：研究基金净值历史多始于2020Q2附近，无样本外历史可借（方案B不成立），故用缩短窗口拉长时间跨度。"""
    nav = pd.read_csv(D("L4_风险应对层", "基金净值历史_全量.csv"), encoding="utf-8-sig")
    nav["date"] = pd.to_datetime(nav["date"], errors="coerce")
    nav = nav.dropna(subset=["date"]).sort_values(["fund_code", "date"])
    nav["ret"] = pd.to_numeric(nav["daily_return"], errors="coerce") / 100.0
    nav["q"] = nav["date"].dt.to_period("Q")
    fr = nav.groupby(["fund_code", "q"])["ret"].apply(lambda s: (1 + s).prod() - 1).reset_index()
    fr["report_date"] = fr["q"].apply(lambda p: to_panel_date(p.end_time.normalize()))

    st = pd.read_csv(D("L2_持仓偏离层", "风格指数季度收益.csv"), encoding="utf-8-sig")
    scols = [c for c in st.columns if re.fullmatch(r"39937[0-9]_q_return", c)]
    style_names = [c[:6] for c in scols]                    # 399373_q_return -> 399373
    st = st.rename(columns={c: c[:6] for c in scols})
    st["q"] = pd.to_datetime(st["year"].astype(str) + "Q" + st["quarter"].astype(str)).dt.to_period("Q")
    st = st.set_index("q")[style_names]
    rows = []
    for fund, g in fr.groupby("fund_code"):
        g = g.sort_values("q").reset_index(drop=True)
        merged = g.merge(st, left_on="q", right_index=True, how="inner")
        if len(merged) < window + 1:
            continue
        w_hist = []
        X_all = merged[style_names].values
        y_all = merged["ret"].values
        for i in range(window, len(merged)):
            X = np.column_stack([np.ones(window), X_all[i - window:i]])
            y = y_all[i - window:i]
            try:
                beta, *_ = np.linalg.lstsq(X, y, rcond=None)
            except Exception:
                continue
            w = np.maximum(beta[1:], 0)
            if w.sum() > 0:
                w = w / w.sum()
            w_hist.append((merged.iloc[i]["report_date"], w))
        for i in range(1, len(w_hist)):
            sdi = np.abs(w_hist[i][1] - w_hist[i - 1][1]).sum()
            rows.append((fund, w_hist[i][0], sdi))
    out = pd.DataFrame(rows, columns=["fund_code", "report_date", "SDI"])
    return out.sort_values(["fund_code", "report_date"])


# ============================================================
# L4 风险应对
# ============================================================
def calc_arg():
    """ARG = Σ_t|RG_t|（季度内 3 个月 RG 绝对值之和）；RG_t = R_fund,t − Σ w_i·R_i,t。
    输入：基金净值历史_全量.csv + 基金持仓明细_全量修正版_v3.csv + 个股月收益率_全量.csv。"""
    nav = pd.read_csv(D("L4_风险应对层", "基金净值历史_全量.csv"), encoding="utf-8-sig")
    nav["date"] = pd.to_datetime(nav["date"], errors="coerce")
    nav["ret"] = pd.to_numeric(nav["daily_return"], errors="coerce") / 100.0
    nav = nav.dropna(subset=["date"]).sort_values(["fund_code", "date"])
    nav["month"] = nav["date"].dt.to_period("M")
    fr = nav.groupby(["fund_code", "month"])["ret"].apply(lambda s: (1 + s).prod() - 1).reset_index()

    h = pd.read_csv(D("L2_持仓偏离层", "基金持仓明细_全量修正版_v3.csv"), encoding="utf-8-sig")
    h["w"] = pd.to_numeric(h["hold_ratio"], errors="coerce").fillna(0) / 100.0
    h["rd"] = pd.to_datetime(h["report_date"], errors="coerce")
    h["month"] = h["rd"].dt.to_period("M")
    h["stock_code"] = h["stock_code"].astype(str).str.zfill(6)

    sm = pd.read_csv(D("股价行情", "个股月收益率_全量.csv"), encoding="utf-8-sig")
    sm["date"] = pd.to_datetime(sm["date"], errors="coerce")
    sm["month"] = sm["date"].dt.to_period("M")
    sm = sm.dropna(subset=["month"])
    sm["stock_code"] = sm["stock_code"].astype(str).str.zfill(6)
    sm_wide = sm.pivot_table(index="month", columns="stock_code", values="monthly_return")

    smw_cols = set(sm_wide.columns)
    # 预建 月 → {股票: 月收益} 字典
    ret_dict = {m: sm_wide.loc[m].dropna().to_dict() for m in sm_wide.index}
    # 预分组：基金 → 持仓快照列表
    h = h.sort_values(["fund_code", "month"])
    h_groups = {k: g for k, g in h.groupby("fund_code")}

    rows = []
    for fund, gf in fr.groupby("fund_code"):
        hf = h_groups.get(fund)
        if hf is None or hf.empty:
            continue
        # 该基金所有持仓快照月份 + 对应 {股票: 权重}
        snap_months = sorted(hf["month"].unique())
        snap_map = {}
        for sm_ in snap_months:
            sub = hf[hf["month"] == sm_]
            snap_map[sm_] = {c: w for c, w in zip(sub["stock_code"], sub["w"]) if c in smw_cols}
        months_arr = np.array(snap_months)
        for _, r in gf[["month", "ret"]].iterrows():
            m, ret = r["month"], r["ret"]
            j = np.searchsorted(months_arr, m) - 1          # 最近一次 ≤ m 的快照
            if j < 0:
                continue
            d = snap_map[months_arr[j]]
            if not d:
                continue
            rd = ret_dict.get(m, {})
            codes = list(d.keys())
            w_i = np.array([d[c] for c in codes])
            r_i = np.array([rd.get(c, np.nan) for c in codes])
            wsum = w_i.sum()
            if not wsum or np.isnan(wsum):
                continue
            rows.append((fund, m, ret - np.nansum(w_i * r_i) / wsum))
    rg_df = pd.DataFrame(rows, columns=["fund_code", "month", "rg"])
    rg_df["rg_abs"] = rg_df["rg"].abs()
    rg_df["q"] = rg_df["month"].astype("period[Q]")
    arg = rg_df.groupby(["fund_code", "q"])["rg_abs"].sum().reset_index().rename(columns={"rg_abs": "ARG"})
    arg["report_date"] = arg["q"].apply(lambda p: to_panel_date(p.end_time.normalize()))
    return arg[["fund_code", "report_date", "ARG"]].sort_values(["fund_code", "report_date"])


def calc_return_volatility():
    """return_volatility = 季度收益滚动 8 期标准差。输入：基金季度收益.csv。"""
    f = D("L4_风险应对层", "基金季度收益.csv")
    df = pd.read_csv(f, encoding="utf-8-sig")
    df["report_date"] = to_panel_date(df["report_date"])
    df = df.sort_values(["fund_code", "report_date"])
    df["return_volatility"] = df.groupby("fund_code")["quarter_return"].transform(
        lambda s: s.rolling(8, min_periods=3).std())
    return df[["fund_code", "report_date", "return_volatility"]]


# ============================================================
# L5 认知偏差
# ============================================================
def calc_de(only_612=True):
    """de = PGR − PLR（Odean 1998 持仓快照法）。输入：基金持仓明细 + 个股月收益率。
    性能：预先把个股月收益建成 {股票: (日期数组, 收益数组)} 字典，避免对全表逐股过滤。"""
    h = pd.read_csv(D("L2_持仓偏离层", "基金持仓明细_全量修正版_v3.csv"), encoding="utf-8-sig")
    h["report_date"] = pd.to_datetime(h["report_date"], errors="coerce")
    if only_612:
        h = h[h["report_date"].dt.month.isin([6, 12])]
    sm = pd.read_csv(D("股价行情", "个股月收益率_全量.csv"), encoding="utf-8-sig")
    sm["date"] = pd.to_datetime(sm["date"], errors="coerce")
    sm = sm.dropna(subset=["date"]).sort_values(["stock_code", "date"])
    # 每只股票 -> (日期ndarray, 收益ndarray)
    stock_dict = {}
    for code, g in sm.groupby("stock_code"):
        stock_dict[code] = (g["date"].values, g["monthly_return"].values)

    def period_ret(code, t0, t1):
        if code not in stock_dict:
            return np.nan
        ds, rs = stock_dict[code]
        mask = (ds > t0) & (ds <= t1)
        sub = rs[mask]
        return float(sub.sum()) if len(sub) else np.nan

    rows = []
    for fund, fdf in h.groupby("fund_code"):
        fdf = fdf.sort_values("report_date")
        dates = fdf["report_date"].unique()
        for i in range(1, len(dates)):
            t0, t1 = dates[i - 1], dates[i]
            prev = set(fdf[fdf["report_date"] == t0]["stock_code"])
            cur = set(fdf[fdf["report_date"] == t1]["stock_code"])
            sold, held = prev - cur, prev & cur
            gs = gh = ls = lh = 0
            for c in sold:
                r = period_ret(c, t0, t1)
                if pd.isna(r):
                    continue
                if r > 0:
                    gs += 1
                else:
                    ls += 1
            for c in held:
                r = period_ret(c, t0, t1)
                if pd.isna(r):
                    continue
                if r > 0:
                    gh += 1
                else:
                    lh += 1
            dg, dl = gs + gh, ls + lh
            pgr = gs / dg if dg else np.nan
            plr = ls / dl if dl else np.nan
            de = pgr - plr if (dg and dl) else np.nan
            rows.append((fund, to_panel_date(t1), de, pgr, plr, gs, gh, ls, lh))
    out = pd.DataFrame(rows, columns=["fund_code", "report_date", "de", "pgr", "plr",
                                      "gains_sold", "gains_held", "losses_sold", "losses_held"])
    return out.sort_values(["fund_code", "report_date"])


def calc_lsv():
    """lsv = |p_i − p̄_t| − AF（LSV 1992 横截面趋同度，基金层面）。

    ⚠️ 重要数据限制：本仓库只有「累计买入股票明细」(买入侧)文件，没有买卖双向记录，
    因此无法用真实逐笔成交方向算 LSV。这里用**持仓变动方向**作为买卖方向代理：
    对每只股票 i，在相邻两次持仓快照之间，统计全市场「增持基金数 B」与「减持基金数 S」，
    采用 **LSV(1992) 教科书口径的买入占比** p_i = B/(B+S) ∈ [0,1]
    （在交易该股票的所有基金中，选择增持（净买入）的基金占比；与文稿/make_report 的 p_j 定义一致）；
    p̄_t = 期内各股票 p_i 的横截面均值（市场整体净买入倾向基准）；
    AF = LSV(1992) 二项式调整因子 sqrt(2/π)·sqrt(p̄_t·(1−p̄_t)/n_i)。
    股票层面 H_i = |p_i − p̄_t| − AF；基金层面 lsv_f = 对其交易过的股票取 H_i 的均值。
    说明：p_i 取买入占比（可正可负，样本反向交易时整体为负）才能恢复 LSV 原意的"反向交易"；
    与原面板 lsv（均值≈−0.23，基于真实买卖方向）口径仍有差异，仅作可计算代理，详见 README「已知差异」第 8 条。
    输入：L2_持仓偏离层/基金持仓明细_全量修正版_v3.csv（持仓快照 → 增减方向）。"""
    h = pd.read_csv(D("L2_持仓偏离层", "基金持仓明细_全量修正版_v3.csv"), encoding="utf-8-sig")
    h["w"] = pd.to_numeric(h["hold_ratio"], errors="coerce").fillna(0) / 100.0
    h["rd"] = to_panel_date(h["report_date"])               # 对齐面板 +1 天约定
    h = h.sort_values(["fund_code", "stock_code", "rd"])
    # 相邻快照的持仓变化方向（+1 增持 / −1 减持 / 0 不变）
    h["prev_w"] = h.groupby(["fund_code", "stock_code"])["w"].shift(1)
    h["dir"] = np.sign(h["w"] - h["prev_w"])
    h = h.dropna(subset=["dir"])                            # 仅保留有「上一期」的快照边
    h = h[h["dir"] != 0]                                    # 剔除未变动
    if h.empty:
        return pd.DataFrame(columns=["fund_code", "report_date", "lsv"])
    # 市场层面（按 期×股票）：B=增持基金数, S=减持基金数
    mkt = h.groupby(["rd", "stock_code"])["dir"].agg(
        B=lambda s: int((s == 1).sum()),
        S=lambda s: int((s == -1).sum()),
        n=lambda s: int(s.count())).reset_index()
    mkt["p_i"] = mkt["B"] / (mkt["B"] + mkt["S"])   # LSV1992 教科书口径：买入占比 ∈ [0,1]
    pbar = mkt.groupby("rd")["p_i"].mean().rename("p_t")
    mkt = mkt.merge(pbar, on="rd")
    mkt["AF"] = np.sqrt(2.0 / np.pi) * np.sqrt(
        (mkt["p_t"] * (1.0 - mkt["p_t"])).clip(lower=0) / mkt["n"])
    mkt["H_i"] = (mkt["p_i"] - mkt["p_t"]).abs() - mkt["AF"]
    # 基金层面：对其在本期有方向的股票取 H_i 均值
    res = h[["fund_code", "rd", "stock_code"]].merge(
        mkt[["rd", "stock_code", "H_i"]], on=["rd", "stock_code"])
    fund_lsv = res.groupby(["fund_code", "rd"])["H_i"].mean().reset_index().rename(
        columns={"rd": "report_date", "H_i": "lsv"})
    return fund_lsv.sort_values(["fund_code", "report_date"])


def calc_risk_asym(window=8, min_periods=4):
    """risk_asym = σ(盈利期收益) − σ(亏损期收益)，**逐期滚动窗口**计算（2026-08-12 由基金级常量改为时变）。

    文献依据：风险不对称/杠杆效应（leverage effect, Black 1976 / Christie 1982 / Bekaert & Wu 2000）
    在基金层面的实现常以『盈利期波动 − 亏损期波动』衡量；原实现按基金全历史取一个常量，
    在基金固定效应面板回归中变异为 0 无法识别。此处改为滚动窗口逐期计算，使其具备基金内
    跨期变异（window=8 季度、min_periods=4），与 return_volatility 的滚动口径一致。

    输入：基金季度收益.csv（L4_风险应对层）。
    输出：fund_code, report_date, risk_asym, n_gain, n_loss（n_gain/n_loss 改为该窗口内盈利/亏损期数）。"""
    f = D("L4_风险应对层", "基金季度收益.csv")
    df = pd.read_csv(f, encoding="utf-8-sig")
    df["report_date"] = to_panel_date(df["report_date"])
    df = df.sort_values(["fund_code", "report_date"]).reset_index(drop=True)

    def _roll_ra(g):
        r = g["quarter_return"].values
        n = len(r)
        ra = np.full(n, np.nan)
        ng = np.full(n, np.nan)
        nl = np.full(n, np.nan)
        for i in range(n):
            lo = max(0, i - window + 1)
            seg = r[lo:i + 1]
            if len(seg) < min_periods:
                continue
            gain = seg[seg > 0]
            loss = seg[seg <= 0]
            sg = gain.std() if len(gain) > 1 else np.nan
            sl = loss.std() if len(loss) > 1 else np.nan
            if np.isnan(sg) or np.isnan(sl):
                continue
            ra[i] = sg - sl
            ng[i] = len(gain)
            nl[i] = len(loss)
        out = g.copy()
        out["risk_asym"] = ra
        out["n_gain"] = ng
        out["n_loss"] = nl
        return out

    parts = []
    for fund, g in df.groupby("fund_code"):
        g = g.sort_values("report_date")
        res = _roll_ra(g)
        res["fund_code"] = fund
        parts.append(res)
    out = pd.concat(parts, ignore_index=True)
    return out[["fund_code", "report_date", "risk_asym", "n_gain", "n_loss"]].sort_values(
        ["fund_code", "report_date"]).reset_index(drop=True)


# ============================================================
# 面板骨架（观测索引）：来自主面板的关键列 fund_code/year/quarter/report_date
# ============================================================
def load_skeleton():
    """观测索引（fund_code, year, quarter, report_date）由**原始净值数据覆盖**派生，
    彻底脱离论文原始面板（元面板）。做法：对 基金净值历史_全量.csv 按 (基金×季度) 计算
    季度收益，凡能算出季度收益的 (基金,季度) 即纳入研究样本；report_date = 季度末 +1 天
    （面板约定，见 to_panel_date）。

    **未来季度剔除（2026-08-13 修复）**：净值历史最大日期为 max_date，凡
    `季度末 > max_date` 的季度是尚未结束、收益残缺的「未来季度」，绝不能当成完整
    季度纳入面板（会造成样本内未来数据泄漏）。仅保留 `季度末 ≤ max_date` 的季度。
    例如净值截至 2026-08-07 时，2026Q3(季度末 09-30) 被自动剔除，样本止于 2026Q2。"""
    nav = pd.read_csv(D("L4_风险应对层", "基金净值历史_全量.csv"), encoding="utf-8-sig")
    nav["date"] = pd.to_datetime(nav["date"], errors="coerce")
    nav = nav.dropna(subset=["date"]).sort_values(["fund_code", "date"])
    max_date = nav["date"].max()  # 净值数据实际覆盖末尾，用于剔除未来季度
    nav["nav"] = pd.to_numeric(nav["nav"], errors="coerce")
    nav["daily_return"] = pd.to_numeric(nav["daily_return"], errors="coerce")
    # ── 口径统一(2026-08-13) ──────────────────────────────────────────────
    # 经验证：该文件 400 只基金中仅 200 只有 daily_return，另 200 只仅有 nav
    # （daily_return 全部缺失）；而这 200 只的 daily_return 与 nav 的 pct_change 中位差仅
    # 0.0022%，即 daily_return 本就由 nav 派生。为消除「流水线 200 只 / 面板 400 只」的
    # 口径风险，这里统一由 nav 派生日收益：缺失 daily_return 的基金用 nav.pct_change 补齐，
    # 已有 daily_return 的基金保留原值（覆盖更准）。补齐后全部 400 只基金均可派生季度收益，
    # 与 00 骨架 400 只口径对齐（原模拟占位面板主分析面板_修正版.csv 已于 2026-08-14 隔离删除）；未来季度剔除逻辑保持不变。
    nav["ret"] = nav.groupby("fund_code")["nav"].pct_change()
    has_dr = nav["daily_return"].notna()
    nav.loc[has_dr, "ret"] = nav.loc[has_dr, "daily_return"] / 100.0
    nav = nav.dropna(subset=["ret"])
    nav["q"] = nav["date"].dt.to_period("Q")
    fr = nav.groupby(["fund_code", "q"])["ret"].apply(lambda s: (1 + s).prod() - 1).reset_index()
    fr["report_date"] = fr["q"].apply(lambda p: to_panel_date(p.end_time.normalize()))
    fr["year"] = fr["q"].dt.year
    fr["quarter"] = fr["q"].dt.quarter
    # 仅保留季度末（report_date - 1天）≤ 净值最大日期的季度，剔除残缺未来季
    fr["q_end"] = fr["report_date"] - pd.Timedelta(days=1)
    fr = fr[fr["q_end"] <= max_date].drop(columns=["q_end"])
    sk = (fr[["fund_code", "year", "quarter", "report_date"]]
          .drop_duplicates()
          .sort_values(["fund_code", "report_date"])
          .reset_index(drop=True))
    return sk


if __name__ == "__main__":
    print("lib_metrics 自检：")
    sk = load_skeleton()
    print("骨架观测数:", len(sk))
    print("AS_improved 首行:", calc_active_share().head(1).to_dict("records"))
    print("ICI 首行:", calc_ici().head(1).to_dict("records"))
    print("industry_hhi 首行:", calc_industry_hhi().head(1).to_dict("records"))
    print("TO_two_sided 首行:", calc_turnover_two_sided().head(1).to_dict("records"))
    print("SDI 首行:", calc_sdi().head(1).to_dict("records"))
    print("ARG 首行:", calc_arg().head(1).to_dict("records"))
    print("return_volatility 首行:", calc_return_volatility().head(1).to_dict("records"))
    print("de 首行:", calc_de().head(1).to_dict("records"))
    print("lsv 首行:", calc_lsv().head(1).to_dict("records"))
    print("risk_asym 首行:", calc_risk_asym().head(1).to_dict("records"))
    print("mgr_total_tenure_v2 首行:", calc_manager_tenure(sk).head(1).to_dict("records"))
    print("log_fund_age 首行:", calc_fund_age(sk).head(1).to_dict("records"))
    print("控制变量 首行:", calc_control_vars(sk).head(1).to_dict("records"))
