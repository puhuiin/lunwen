# -*- coding: utf-8 -*-
"""导出指标总表（层 / 指标 / 计算方式 / 含义）到 CSV 与 Excel。
UTF-8-SIG CSV 保证中文 Excel 正常打开；Excel 尝试 openpyxl / xlsxwriter。
"""
import csv
import os

ROWS = [
    ("L1 基本面层", "从业年限", "观测日 − 首次任职日（天数）", "管理经验的积累程度；也为判断老经理是否形成思维定式提供基础"),
    ("L1 基本面层", "基金年龄", "ln(基金存续月数)", "基金经受市场检验的时间；老基金有'幸存者溢价'，也可能受规模膨胀侵蚀"),
    ("L1 基本面层", "学历/院校/CFA", "akshare 直接下载的分类变量", "专业训练背景与资质认证（仅作控制变量，未做独立检验）"),
    ("L2 认知层", "风险承担不对称 RA", "σ(盈利季收益) − σ(亏损季收益)，滚动8季窗口", "盈利后风险偏好与亏损后风险偏好的差异，度量'赌资效应'强度"),
    ("L2 认知层", "处置效应 DE", "PGR − PLR；PGR=盈利股中已实现卖出比例，PLR=亏损股中已实现卖出比例（Odean 1998）", "持有亏损股过久、过早卖出盈利股的倾向；值越负越果断止损"),
    ("L2 认知层", "羊群效应 LSV", "|p_j − p̄_t| − E[|p_j − p̄_t|]（LSV1992 含小样本修正项）", "与同行协同买卖的程度，度量从众行为"),
    ("L3 选择层", "改进主动份额 AS", "½ × Σ_i |w_基金,i − w_基准,i|，基准=沪深300+中证500合并成分股", "组合偏离基准的程度，区分'真主动选股'与'复制指数'"),
    ("L3 选择层", "行业集中度 ICI", "Σ_i (w_行业,i − w_市场,i)²，w_市场为全市场行业权重", "在行业层面相对市场的方向性押注强度"),
    ("L3 选择层", "行业分散度 HHI", "Σ_i w_i²（各行业权重平方和）", "行业配置的绝对集中水平，密集投资还是广泛撒网"),
    ("L4 执行风控层", "风格漂移 SDI", "净值对规模×价值/成长四宫格指数滚动回归 → 相邻期风格权重的曼哈顿距离", "投资风格跨期变化的幅度，策略稳定性的度量"),
    ("L4 执行风控层", "换手率 TO", "(买入额 + 卖出额) / (2 × 平均净资产)，双边口径", "交易频繁度，直接影响佣金、印花税与冲击成本"),
    ("L4 执行风控层", "过度交易指数 OCI", "(TO − 经理自身历史均值) / 自身标准差", "剔除策略性高换手后的'行为性过度交易'，经理间可比"),
    ("L4 执行风控层", "调仓收益 ARG", "Σ_t |RG_t|，RG_t = 当期实际净值收益 − 上期披露持仓的模拟收益", "净值超出披露持仓可解释部分的累计强度 = 未观测主动行动（调仓/隐性交易）的密度"),
    ("L4 执行风控层", "收益波动率 RV", "季度收益滚动8期标准差", "选股、择时、仓位共同作用的综合风险结果"),
]
HEADER = ["层", "指标", "指标计算", "代表含义"]

# ---- CSV（UTF-8-SIG 带 BOM，Excel 直接打开不乱码）----
csv_path = "指标总表_计算方式与含义.csv"
with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(HEADER)
    w.writerows(ROWS)
print("csv saved:", os.path.abspath(csv_path))

# ---- Excel ----
xlsx_path = "指标总表_计算方式与含义.xlsx"
err = None
try:
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font, Alignment, PatternFill
        wb = Workbook(); ws = wb.active; ws.title = "指标总表"
        ws.append(HEADER)
        for r in ROWS: ws.append(list(r))
        # 样式：表头加粗居中灰底，列宽自适应，自动换行
        head_fill = PatternFill("solid", start_color="D9D9D9")
        for c in ws[1]:
            c.font = Font(bold=True); c.fill = head_fill
            c.alignment = Alignment(horizontal="center", vertical="center")
        widths = [14, 18, 52, 52]
        for i, wd in enumerate(widths, 1):
            ws.column_dimensions[chr(64 + i)].width = wd
        for row in ws.iter_rows(min_row=2):
            for c in row:
                c.alignment = Alignment(vertical="center", wrap_text=True)
        wb.save(xlsx_path)
        print("xlsx saved (openpyxl):", os.path.abspath(xlsx_path))
    except ImportError:
        import pandas as pd
        df = pd.DataFrame(ROWS, columns=HEADER)
        df.to_excel(xlsx_path, index=False)
        print("xlsx saved (pandas):", os.path.abspath(xlsx_path))
except Exception as e:
    err = e
    print("xlsx 导出失败：", e)

print("DONE")