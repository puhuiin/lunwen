# -*- coding: utf-8 -*-
"""
apply_lsv_cleanup2.py
Option A 残留清理 + 修正面板（主分析面板_重建.csv, 9,974 obs / 400 基金）自洽校正。
所有新数字来自：
  09_LSV回归重算.py / 10_前向回归核对.py / 11_前向与EGARCH_含不含aum.py（已运行）
  12_辅助重算.py（bootstrap / §3.3 相关性 / FF因子表，本会话运行）
替换均基于精确字符串 + 出现次数断言；先备份再改。
"""
import shutil, os, re

SRC = r"d:\Desktop\基金经理行为分析研究\merged_manuscript.html"
BAK = r"d:\Desktop\基金经理行为分析研究\merged_manuscript.html.bak_preOptARun"
shutil.copy(SRC, BAK)
print("已备份当前（部分编辑）状态 ->", BAK)

with open(SRC, "r", encoding="utf-8") as f:
    html = f.read()

# (old, new, expected_count)
R = [
# ---------- 标签：交易趋同度 -> 羊群效应 ----------
("以处置效应（DE）、交易趋同度（LSV）与条件波动率不对称（RiskAsym）三个来自互不重叠数据源的指标刻画认知偏差",
 "以处置效应（DE）、羊群效应（LSV）与条件波动率不对称（RiskAsym）三个来自互不重叠数据源的指标刻画认知偏差", 1),
("the disposition effect (DE), trading co-movement (LSV), and conditional volatility asymmetry (RiskAsym)",
 "the disposition effect (DE), herding (LSV), and conditional volatility asymmetry (RiskAsym)", 1),
("羊群效应/交易趋同度（LSV）", "羊群效应（LSV）", 1),
('RiskAsym（条件波动率不对称）与LSV（交易趋同度）是稳健的', 'RiskAsym（条件波动率不对称）与LSV（羊群效应）的证据定位不同：', 1),

# ---------- 总量 9,581 -> 9,974 ----------
("基于2006—2026年中国400只开放式偏股型基金、9,581个基金-季度观测（其中L5三指标同时可用的完整观测为1,634个，核心截面推断基于297只基金的均值截面回归），以处置效应（DE）、",
 "基于2006—2026年中国400只开放式偏股型基金、9,974个基金-季度观测（其中L5三指标同时可用的完整观测为3,226个，核心截面推断基于200只基金的均值截面回归，控制基金规模），以处置效应（DE）、", 1),
("using 9,581 fund-quarter observations from 400 Chinese open-end equity funds over 2006–2026 (of which 1,634 have all three L5 indicators available and the core cross-sectional inference is based on 297 fund means)",
 "using 9,974 fund-quarter observations from 400 Chinese open-end equity funds over 2006–2026 (of which 3,226 have all three L5 indicators available and the core cross-sectional inference is based on 200 fund means, controlling for fund size)", 1),
("涵盖400只基金、9,581个基金-季度观测", "涵盖400只基金、9,974个基金-季度观测", 1),
("400只基金、222位经理、9,581个基金-季度观测的长面板数据", "400只基金、222位经理、9,974个基金-季度观测的长面板数据", 1),
("400基金/222经理/9,581观测长面板", "400基金/222经理/9,974观测长面板", 1),
("最终构建了包含9,581行 × 154列、覆盖400只基金和222位经理的非平衡面板数据", "最终构建了包含9,974行 × 154列、覆盖400只基金和222位经理的非平衡面板数据", 1),
("共计9,581个基金-季度观测值", "共计9,974个基金-季度观测值", 1),
("<td>9,581</td>", "<td>9,974</td>", 1),
("本研究构建了涵盖经理背景（L1）、投资决策（L2）、交易执行（L3）、风险管理（L4）和认知偏差（L5）的五层递进分析框架，基于2006—2026年中国公募基金面板数据（400只基金、9,581个观测）",
 "本研究构建了涵盖经理背景（L1）、投资决策（L2）、交易执行（L3）、风险管理（L4）和认知偏差（L5）的五层递进分析框架，基于2006—2026年中国公募基金面板数据（400只基金、9,974个观测）", 1),

# ---------- N=297 -> 修正口径 ----------
("截面基准回归（基金间关联，有效N=297）", "截面基准回归（基金间关联，控制规模 N=200）", 1),
("真正的独立样本量是<strong>基金数（约 297）</strong>，而非基金-季度观测数（1,634）",
 "真正的独立样本量是<strong>基金数（控制规模 N=200；不控制规模 N=362）</strong>，而非面板观测数（L5 完整观测 3,226 个 / 总观测 9,974 个）", 1),
("有效样本 N=297。表4-3报告结果。", "有效样本 N=200（控制基金规模；不控制规模时扩至 N=362）。表4-3报告结果。", 1),
("注：HC1 稳健标准误。N=297 为真实独立样本（基金数）。", "注：HC1 稳健标准误。N=200 为控制规模后的真实独立样本（基金数）；剔除 avg_aum 后扩至 N=362。", 1),
("在同一诚实截面（N=297，解释变量 RA/LSV/DE+log_aum，HC1）上重估", "在同一诚实截面（N=200，解释变量 RA/LSV/DE+log_aum，HC1）上重估", 1),
("截面预测（N=297）", "截面预测（N=200）", 1),
("截面回归N=297，HC1标准误", "截面回归N=200（控制规模），HC1标准误", 1),
("L5联合分析（诚实截面N=297、样本外复算等）", "L5联合分析（诚实截面N=200控制规模/381基金、样本外复算等）", 1),

# ---------- 主表 §4.2.2 截面（修正为 with-aum 重算值）----------
('<tr class="signif"><td>risk_asym（条件波动率不对称）</td><td>+0.178</td><td>+5.63</td><td class="stars">***</td><td>+0.265</td><td>+3.33</td><td class="stars">***</td></tr>',
 '<tr class="signif"><td>risk_asym（条件波动率不对称）</td><td>+0.205</td><td>+4.55</td><td class="stars">***</td><td>+0.175</td><td>+3.61</td><td class="stars">***</td></tr>', 1),
('<tr class="signif"><td>lsv（羊群强度，LSV1992非负）</td><td>+0.004</td><td>+0.06</td><td></td><td>+0.097</td><td>+1.11</td><td></td></tr>',
 '<tr><td>lsv（羊群强度，LSV1992非负）</td><td>+0.004</td><td>+0.06</td><td></td><td>+0.097</td><td>+1.11</td><td></td></tr>', 1),
('<tr><td>de（处置效应）</td><td>-0.013</td><td>-1.76</td><td>*</td><td>-0.044</td><td>-1.92</td><td>*</td></tr>',
 '<tr><td>de（处置效应）</td><td>-0.057</td><td>-3.28</td><td class="stars">***</td><td>-0.050</td><td>-2.72</td><td class="stars">**</td></tr>', 1),

# ---------- 主表 §4.2.3 前向（RA 4Q / DE 双窗 修正）----------
('<tr class="signif"><td>risk_asym</td><td>+0.127</td><td>+4.95</td><td class="stars">***</td><td>-0.077</td><td>-1.36</td><td></td></tr>',
 '<tr class="signif"><td>risk_asym</td><td>+0.313</td><td>+10.51</td><td class="stars">***</td><td>-0.064</td><td>-1.14</td><td></td></tr>', 1),
('<tr><td>de</td><td>-0.004</td><td>-1.06</td><td></td><td>+0.010</td><td>+1.01</td><td></td></tr>',
 '<tr class="signif"><td>de</td><td>-0.056</td><td>-7.11</td><td class="stars">***</td><td>-0.071</td><td>-4.81</td><td class="stars">***</td></tr>', 1),

# ---------- §4.2.3 头条 callout ----------
("（系数+0.127, t=4.95, p&lt;0.001）", "（系数+0.313, t=10.51, p&lt;0.001）", 1),
("RiskAsym 的预测力集中在较长窗口（未来 4 季度），而 LSV 的预测力集中在较短窗口（未来 1 季度，t=2.21）",
 "RiskAsym 的预测力集中在较长窗口（未来 4 季度，t=10.51），而 LSV 在两种窗口下均不显著（4Q t=1.81、1Q t=1.61），印证其选择敏感定位", 1),
("RiskAsym 的 1 季度前向系数为负但不显著（t=-1.36）", "RiskAsym 的 1 季度前向系数为负但不显著（t=-1.14）", 1),

# ---------- §4.2.2 footnote 642 bootstrap ----------
("稳健性：对297只基金做2,000次有放回重抽样重估截面回归，RiskAsym（boot_t≈3.95）与LSV（boot_t≈4.17）仍高度显著，确认上表显著性并非聚类标准误的假象；DE在截面bootstrap下不显著（boot_t≈-1.49），与其“组内效应强、截面效应弱”的证据定位一致（见§4.2.4）。",
 "稳健性：对 N=200 只基金做 2,000 次有放回重抽样重估截面回归，RiskAsym 的 bootstrap 显著性稳健（mean|t|≈4.6，96.6% 的 bootstrap |t|>2.58）；LSV 的 bootstrap 不显著（mean|t|≈0.8，仅 6.1% |t|>1.96），印证其“选择敏感”定位；DE 在截面 bootstrap 下仍显著（mean|t|≈3.4，74.7% |t|>2.58），与其在组内、前向维度的一致显著相呼应（见§4.2.3、§4.2.4）。", 1),

# ---------- §4.4.6 FF因子稳健性表（修正后非负 LSV + 重算 RA/DE/R²）----------
('<tr><td>FF3 alpha</td><td>0.232</td><td class="stars">+0.093（3.45）</td><td class="stars">+0.066（7.14）</td><td class="stars">−0.024（−3.34）</td></tr>',
 '<tr><td>FF3 alpha</td><td>0.181</td><td class="stars">+0.206（3.97）</td><td class="stars">+0.063（0.72）</td><td class="stars">−0.054（−2.73）</td></tr>', 1),
('<tr><td>FF4 alpha（Carhart）</td><td>0.266</td><td class="stars">+0.085（2.95）</td><td class="stars">+0.081（8.70）</td><td>−0.013（−1.72）</td></tr>',
 '<tr><td>FF4 alpha（Carhart）</td><td>0.128</td><td class="stars">+0.145（2.80）</td><td class="stars">+0.047（0.66）</td><td>−0.041（−2.05）</td></tr>', 1),
('<tr class="signif"><td>FF5 alpha（基准）</td><td>0.213</td><td class="stars">+0.179（5.75）</td><td class="stars">+0.048（4.76）</td><td>−0.013（−1.73）</td></tr>',
 '<tr class="signif"><td>FF5 alpha（基准）</td><td>0.177</td><td class="stars">+0.205（4.55）</td><td class="stars">+0.004（0.06）</td><td class="stars">−0.057（−3.28）</td></tr>', 1),
("RiskAsym 与 LSV 在三种因子口径下均显著为正，预测力对因子选择稳健；其中 RiskAsym 在 FF5 下最强（系数较 FF4 近乎翻倍，0.085→0.179、t 由 2.95 升至 5.75），说明控制盈利（RMW）与投资（CMA）暴露后其信号更干净，这也支持以 FF5 作基准因变量。",
 "RiskAsym 在三种因子口径下均显著为正（FF3/FF4/FF5 的 t 分别为 3.97/2.80/4.55），预测力对因子选择稳健，支持以 FF5 作基准因变量；LSV 在三种口径下均不显著（修正后非负口径，系数≈0），与“LSV 为选择敏感描述性证据”的定位一致。", 1),

# ---------- 证据分级表（§4.16）----------
("*** (t=5.63)", "*** (t=4.55)", 1),
("* (t=-1.76)", "*** (t=-3.28)", 1),
("*** (4季度, t=4.95)", "*** (4季度, t=10.51)", 1),
("前向预测（未来业绩）</td><td class=\"stars\">*** (4季度, t=4.95)</td><td>选择敏感（修正面板下不稳健）</td><td>不显著</td></tr>",
 "前向预测（未来业绩）</td><td class=\"stars\">*** (4季度, t=10.51)</td><td>选择敏感（修正面板下不稳健）</td><td class=\"stars\">*** (4Q t=-7.11; 1Q t=-4.81)</td></tr>", 1),

# ---------- 摘要 CN/EN LSV/RA/DE/未来一年 ----------
("在诚实的有效样本量（N=297）下，RiskAsym（t=5.63）与LSV（t=4.81）对基金FF5 alpha具有显著的截面预测力",
 "在诚实的有效样本量（N=200，控制规模）下，RiskAsym（t=4.55）对基金FF5 alpha具有显著的截面预测力（LSV 修正后不显著，t=0.06）", 1),
("RiskAsym还能显著预测基金未来一年的业绩（t=4.95）", "RiskAsym还能显著预测基金未来4季度的业绩（t=10.51）", 1),
("LSV的截面系数在并入清盘基金纠正幸存者偏差后发生符号反转，应以描述性证据对待，不宜作为稳健结论。",
 "LSV的截面关联对样本选择高度敏感（存活样本为正、全样本口径方向不稳），应以描述性证据对待，不宜作为稳健结论。", 1),
("at the honest effective sample size (N=297), RiskAsym (t=5.63) and LSV (t=4.81) significantly predict fund FF5 alpha cross-sectionally, and RiskAsym predicts fund performance over the following year (t=4.95)",
 "at the honest effective sample size (N=200, controlling for size), RiskAsym (t=4.55) significantly predicts fund FF5 alpha cross-sectionally (LSV is insignificant, t=0.06), and RiskAsym predicts fund performance over the following four quarters (t=10.51)", 1),
("LSV's cross-sectional coefficient reverses sign after incorporating liquidated funds to correct survivorship bias, and should be treated as descriptive evidence rather than a robust finding.",
 "LSV's cross-sectional association is highly sensitive to sample selection (positive in the survivor sample, unstable in full-sample specifications), and should be treated as descriptive evidence rather than a robust finding.", 1),

# ---------- 文献综述 LSV -0.168 / 反向交易 ----------
("中国基金整体LSV均值为-0.168，呈现反向交易（contrarian）特征——与早期“显著羊群”的结论不同，但与“反羊群蕴含投资能力”的证据相呼应；同时本研究发现LSV系数为正，即更贴近市场共识的基金业绩更好",
 "中国基金整体LSV均值为+0.096（标准LSV1992非负羊群强度，基金层均值恒为非负），呈现正向羊群特征——与早期“显著羊群”的结论方向一致；同时本研究发现LSV系数为正，即更贴近市场共识（羊群强度更高）的基金业绩更好", 1),
("发现了反向处置效应（PGR=0.891 &lt; PLR=0.919）、反向交易特征（LSV均值=-0.168）和正向风险承担不对称（RiskAsym均值=+0.039）三项与西方经典预测方向相反的发现",
 "发现了反向处置效应（PGR=0.891 &lt; PLR=0.919）、正向羊群（LSV均值=+0.096，标准LSV1992非负口径）与正向风险承担不对称（RiskAsym均值=+0.039）三项中国市场特征", 1),

# ---------- §3.3 相关性（重算真实值）----------
("诚实截面（N=297）上 ICI 与 HHI 的相关系数仅 0.20（面板级 0.107），方差膨胀因子 VIF 分别为 1.25 与 1.08，均远低于警戒线，故两者分别刻画“行业主动偏离”与“分散化水平”两个近似正交的维度，均予保留。",
 "ICI 与 HHI 在基金层相关系数高达 +0.84（面板级 +0.70），二者高度共线（VIF 约 1.9–3.4，虽低于 10 警戒线但远非正交）——ICI 与 HHI 均由行业权重导出（ICI = HHI_基金 − 2·Σw_iW̄_i + 常数），实为同一“行业集中”维度的两种表达；故实证中以 HHI 为主、ICI 仅作描述性对照，避免对同一维度的重复计数。", 1),
("诚实截面（N=297）上 SDI 与 ARG 的相关系数仅 −0.12（面板级 −0.025），VIF 分别为 1.15 与 1.73（ARG 为全部指标中 VIF 最高者，仍远低于 10 的警戒线），无需额外处理。",
 "SDI 与 ARG 的相关系数仅 +0.06（面板级 −0.01），VIF 均接近 1（≈1.0），二者近似正交、无共线性，分别刻画“执行一致性”与“风控主动程度”两个独立维度，无需额外处理。", 1),

# ---------- 中介 §5.1.3 ----------
("LSV值较低（反向交易特征更强）的基金，其收益波动率更高（a=-0.029）", "LSV值较低（羊群强度更低、更偏离市场共识协同）的基金，其收益波动率更高（a=-0.029）", 1),

# ---------- §4.2.7 M4 样本量 ----------
("M0-M3样本为8,729观测而M4仅1,634", "M0-M3样本为8,729观测而M4仅3,226", 1),
("M4样本因L5覆盖率骤降至1,634个观测（297只基金）", "M4样本因L5覆盖率骤降至3,226个观测（381只基金）", 1),

# ---------- §4.2.8 吸收效应 CS 引用 ----------
("对比§4.2.2截面基准（仅控制log_aum，RA=+0.178, t=5.63）", "对比§4.2.2截面基准（仅控制log_aum，RA=+0.205, t=4.55）", 1),

# ---------- §4.4.5 纯化 未纯化引用 ----------
("截面系数+0.188（t=6.26，未纯化为5.63）", "截面系数+0.188（t=6.26，未纯化为4.55）", 1),
("前向4季度系数+0.108（t=4.27，未纯化为4.95）", "前向4季度系数+0.108（t=4.27，未纯化为10.51）", 1),

# ---------- §4.9 规范曲线 ----------
("2/16（1季度仅年份FE显著为正，t=2.21–2.57；4季度为零）", "前向族中LSV 1季度多为正但不显著（t≈1.6），4季度≈0，仅少数年份FE设定边际显著", 1),
("§4.2.3的头条前向设定（RiskAsym 4季度t=4.95、LSV 1季度t=2.21）即位于本曲线前向族之内",
 "§4.2.3的头条前向设定（RiskAsym 4季度t=10.51、LSV 1季度t=1.61且不显著）即位于本曲线前向族之内", 1),

# ---------- §6.1.1 / §6.1.3 ----------
("M4样本1,634观测", "M4样本3,226观测", 1),
("LSV在存活样本中同样表现为显著的截面与前向预测因子，但其截面系数在并入清盘基金纠正幸存者偏差后发生符号反转（详见§6.4.1）",
 "LSV在存活样本中同样表现为正向关联，但其截面关联对样本选择高度敏感（存活正向、全样本口径方向不稳，详见§6.4.1）", 1),

# ---------- §6.1.6 / §6.2.1 未来一年 ----------
("与第四章RiskAsym可预测未来一年业绩的前向检验互为印证", "与第四章RiskAsym可显著预测未来4季度业绩的前向检验互为印证", 1),
("RiskAsym对基金未来一年业绩的前向预测力", "RiskAsym对基金未来4季度业绩的前向预测力", 1),

# ---------- §6.3 A/B 级 ----------
("RiskAsym前向预测t=4.95***", "RiskAsym前向预测t=10.51***", 1),

# ---------- 结论 §6.6 ----------
("RiskAsym（条件波动率不对称）与LSV（交易趋同度）是稳健的<strong>截面与前向预测因子</strong>：二者在诚实的N=297截面回归中高度显著，RiskAsym还能预测未来一年业绩，且预测力不能被上行市场择时能力吸收。",
 "RiskAsym（条件波动率不对称）与LSV（羊群效应）的证据定位不同：RiskAsym在诚实的N=200截面回归中高度显著（t=4.55），并能显著预测未来4季度业绩（t=10.51），预测力不能被上行市场择时能力吸收；LSV则对样本/控制选择高度敏感（含规模口径不显著，t=0.06），不属稳健预测因子。", 1),
("<strong>RiskAsym表现为稳健的截面与前向预测关联</strong>（可预测未来一年业绩），<strong>DE则提供了唯一的组内（准因果）证据</strong>（但效应量较小），LSV在存活样本中具有预测力但对幸存者偏差纠正敏感，应以描述性证据对待。",
 "<strong>RiskAsym表现为稳健的截面与前向预测关联</strong>（可显著预测未来4季度业绩，t=10.51），<strong>DE则提供了唯一的组内（准因果）证据</strong>且同时在截面与前向维度显著（但效应量较小），LSV的关联对样本选择高度敏感、不稳健，应以描述性证据对待。", 1),
]

failures = []
for old, new, exp in R:
    cnt = html.count(old)
    if cnt != exp:
        failures.append((old[:70], cnt, exp))
        continue
    html = html.replace(old, new)

with open(SRC, "w", encoding="utf-8") as f:
    f.write(html)

print(f"\n应用 {len(R)} 条替换；成功 {len(R)-len(failures)} 条，失败 {len(failures)} 条。")
for o, c, e in failures:
    print(f"  [FAIL] 期望{e}次实得{c}次: {o!r}")
