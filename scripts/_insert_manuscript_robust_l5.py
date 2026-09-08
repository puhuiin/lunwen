# -*- coding: utf-8 -*-
"""在 merged_manuscript.html 的 §4.4 稳健性检验章插入两节 L5 指标稳健性专门诊断：
   §4.4.8 LSV 脆弱性诊断（11 规格电池）
   §4.4.9 DE 选择性子样本审计（6 规格敏感性）
插入锚点：<h2>4.5 内生性讨论与因果推断的边界</h2> 之前。
所有数值来自 output/lsv_脆弱性诊断电池_2026-08-16.csv 与 output/de_选择性审计_2026-08-16.csv（CGM2011 双向聚类，MD5=bc0942ce 面板）。
"""
import io

P = r"D:/Desktop/基金经理行为分析研究/merged_manuscript.html"
s = io.open(P, encoding="utf-8").read()

ANCHOR = "<h2>4.5 内生性讨论与因果推断的边界</h2>"
assert s.count(ANCHOR) == 1, "anchor 出现次数应为 1，实际 %d" % s.count(ANCHOR)

BLOCK = """
<h3>4.4.8 LSV（注意力偏差）稳健性诊断：推断脆弱性的来源</h3>
<p>LSV（LSV, 1992 式羊群/注意力偏差代理）在 §4.2.8 主表中以 t=+0.77（p=0.441）不显著，且在前向（§4.2.3）、组内（§4.2.4）、截面（§4.4.6）等多口径下结论高度不一致——它是 L5 三指标中唯一在 M4 与画像文档（独立口径）均不稳的指标。为厘清其脆弱性来源（而非简单丢弃），本节在 M4 面板（含 TO_wind，MD5=bc0942ce）上复用 §4.7 的 CGM2011 双向聚类（基金×年份），做共线性诊断 + 11 规格稳健性电池。</p>
<p><strong>诊断一·非共线性：</strong>LSV 对 RHS 其余变量的方差膨胀因子 VIF=1.15（仅被其余 RHS 解释约 13%），与 TO_wind、SDI、ICI 等的最大 |相关系数| 仅 0.11。说明 LSV 的"不显著"并非被同层或 L1–L4 变量吸收所致。</p>
<div class="table-wrap">
<table>
<tr><th>规格（双向聚类 CGM2011）</th><th>lsv 系数</th><th>t 值</th><th>p 值</th><th>显著性</th></tr>
<tr><td>A 基准（1%/99% 全模型）</td><td>0.01548</td><td>0.77</td><td>0.441</td><td>ns</td></tr>
<tr><td>B 无缩尾</td><td>0.01457</td><td>0.72</td><td>0.475</td><td>ns</td></tr>
<tr><td>C 5%/95% 缩尾</td><td>0.01660</td><td>0.84</td><td>0.404</td><td>ns</td></tr>
<tr><td>D 0.5%/99.5% 缩尾</td><td>0.01455</td><td>0.72</td><td>0.474</td><td>ns</td></tr>
<tr><td>E 删 lsv 极端 1%</td><td>0.02039</td><td>1.12</td><td>0.261</td><td>ns</td></tr>
<tr><td>F +lsv²（非线性）</td><td>0.00663</td><td>0.24</td><td>0.808</td><td>ns</td></tr>
<tr class="signif"><td>G 2022+ 子样本</td><td>0.02542</td><td>2.03</td><td>0.043</td><td class="stars">**</td></tr>
<tr><td>H 2022 前子样本</td><td>-0.03740</td><td>-1.20</td><td>0.230</td><td>ns</td></tr>
<tr><td>I AUM 三分位（小/中/大）</td><td>-0.01185 / 0.01769 / 0.02709</td><td>-0.64 / 0.91 / 1.29</td><td>0.520 / 0.364 / 0.199</td><td>ns</td></tr>
<tr class="signif"><td>J 去其他 L5（隔离 de、risk_asym）</td><td>0.02748</td><td>2.78</td><td>0.005</td><td class="stars">***</td></tr>
<tr><td>K 去 L3（SDI/TO_wind）</td><td>0.01530</td><td>0.86</td><td>0.389</td><td>ns</td></tr>
</table>
</div>
<p class="footnote">注：规格 A 为 §4.2.8 主表口径（N=2,264/348）。规格 J 隔离同层强信号后样本扩至 N=4,873/354（de、risk_asym 亦为部分缺失，剔除后并入更多观测）。规格 G/H 为时期子样本（2022+ N=1,945/348；2022前 N=319/56）。所有 t 值基于 CGM2011 双向聚类标准误。</p>
<p><strong>诊断二·非数据处理假象：</strong>规格 B–F 逐一改变缩尾/去极值/非线性处理——无缩尾（β=0.0146, t=0.72）、5%/95% 缩尾（0.0166, t=0.84）、0.5%/99.5% 缩尾（0.0146, t=0.72）、删 lsv 极端 1%（0.0204, t=1.12）、加 lsv² 非线性项（0.0066, t=0.24）——系数均稳定在 0.015 附近且一律不显著，排除缩尾/异常值/非线性误设所致。</p>
<p><strong>诊断三·机制 = 被同层兄弟指标（DE、RiskAsym）掩盖：</strong>规格 J 将 L5 中的 de 与 risk_asym 一并剔除、仅留 lsv 单独进入模型，lsv 立即转为显著为正（β=+0.0275, t=+2.78***）；规格 K 仅剔除 L3 交易层（SDI/TO_wind）则仍不显著（0.0153, t=0.86）。这说明 LSV 的边际信息被同层更强的 DE、RiskAsym 部分重叠吸收，属块内（L5）信息竞争，而非与 L1–L4 共线。</p>
<p><strong>诊断四·时期依存：</strong>规格 G 仅取 2022+ 子样本，lsv 显著为正（β=+0.0254, t=+2.03**）；规格 H 仅取 2022 前则系数为负且不显著（−0.0374, t=−1.20）。规格 I 按基金规模三分位，lsv 系数由小盘 −0.0119 单调升至大盘 +0.0271，但三组均不显著。这提示 LSV 的截面溢价是中国公募近年的结构性现象（与 SDI 有效窗口 2022+ 一致）。</p>
<div class="callout">
<p><strong>LSV 稳健性结论（重新定性）：</strong>LSV 不是"失败的变量"，而是<strong>时期依存 + 被同层强信号掩盖</strong>的指标：① 其不显著在双向聚类下稳健，不因缩尾/异常值/非线性而改变；② 一旦隔离同层 DE、RiskAsym，或聚焦 2022+ 子样本，LSV 显著为正；③ 故 M4 主表仍以 ns 报告，本节仅解释"为何 ns、何时显著"，不改变主表结论。这与 §4.4.1 置换检验（LSV p=0.51）、§4.7 WCB-S（p=0.229）、§4.4.6 因子口径（均不显著）的定位一致，进一步支持将 LSV 列为"方向一致但推断不显著"的辅助证据。</p>
</div>

<h3>4.4.9 DE（处置效应）选择性子样本审计：内部稳健与外部效度边界</h3>
<p>DE（处置效应/快速止损，由半年报 PGR/PLR 构造）是 M4 中 headline 显著负向信号（β=−0.00606, t=−2.99***，§4.2.8），但其仅覆盖约 46.6% 的观测——缺失源于半年报全持仓快照的结构性可得性（2006–2015 近乎为零、2016+ 稳定在 45% 左右），属非随机缺失。由于"是否有全持仓数据"本身构成样本选择，DE 估计样本的可靠外推性比 LSV 更值得审计，本节专门检验其选择性偏差。</p>
<p><strong>组间可比性：</strong>以 DE 有值/缺失划分两组，比较结果变量与各 RHS。结果变量 ff5_adj_return 两组均衡（标准化均值差 SMD=−0.043，Welch t=−2.13, p=0.033）；但 L2 持仓特征显著失衡——主动份额 AS_improved（SMD=+1.502）、行业集中度 industry_hhi（SMD=−1.119）、行业集中度反比 ICI（SMD=−0.292）、基金年龄（SMD=+0.306）、经理任期（SMD=+0.131）。即 DE 估计样本是<strong>高主动份额、低行业集中、较老</strong>基金的子群，失衡集中在持仓结构而非行为 L3/L4/L5 或业绩结果本身。</p>
<div class="table-wrap">
<table>
<tr><th>敏感性规格（双向聚类 CGM2011）</th><th>de 系数</th><th>t 值</th><th>p 值</th><th>显著性</th><th>备注</th></tr>
<tr class="signif"><td>A 基线（de-present only）</td><td>-0.00606</td><td>-2.99</td><td>0.003</td><td class="stars">***</td><td>对照 t=−2.99</td></tr>
<tr class="signif"><td>B 均值插补 + de_avail 控制</td><td>-0.00712</td><td>-2.87</td><td>0.004</td><td class="stars">***</td><td>de_avail β=+0.0050 (t=2.36**)</td></tr>
<tr class="signif"><td>C 最坏·低 de（mean−2σ 插补）</td><td>-0.00712</td><td>-2.87</td><td>0.004</td><td class="stars">***</td><td>同 B（常数插补不改斜率）</td></tr>
<tr class="signif"><td>D 最坏·高 de（mean+2σ 插补）</td><td>-0.00712</td><td>-2.87</td><td>0.004</td><td class="stars">***</td><td>同 B</td></tr>
<tr><td>E de_avail 仅（不放 de）</td><td>—</td><td>2.18</td><td>0.030</td><td class="stars">**</td><td>de_avail β=+0.0048 (t=2.18**)</td></tr>
<tr class="signif"><td>F 仅 2016+ de-present</td><td>-0.00606</td><td>-2.99</td><td>0.003</td><td class="stars">***</td><td>隔离 2006–2015 缺失主导期</td></tr>
</table>
</div>
<p><strong>内部效度稳健：</strong>DE 的显著负向对缺失机制高度不敏感——均值插补并显式控制"数据可用性"（规格 B）后 de β=−0.00712（t=−2.87***）；仅取 2016+ 子样本（规格 F）仍 t=−2.99***；与基线（−0.00606）一致。即便在模型中放入 de_avail 指示变量，de 自身的负向与显著性仍然保留，<strong>说明 DE 不是"数据可用性"的代理</strong>。</p>
<p><strong>但存在选择偏倚信号（效度边界）：</strong>在控制全部可观测 RHS 后，<strong>de_avail 仍独立预测 alpha（+0.0048, t=+2.18**）</strong>，即"拥有全持仓数据"这一特征本身就与更高 alpha 相关。结合组间可比性，DE 的估计样本是<strong>正向选择的子群</strong>（高主动份额、低集中度、较老基金）。因此，DE 的显著负向结论<strong>不外推至全样本</strong>，其有效度边界 = 拥有全持仓数据的约 46.6% 子群。这与 §4.2.4 组内效应（DE 双向 FE t=−3.64***）一致：DE 的证据在"有数据的基金内部"最干净，但外推需谨慎。</p>
<div class="callout-warn">
<p><strong>诚实局限：</strong>规格 C/D 的最坏情形采用常数插补，OLS 斜率由有值组的变异识别、不改变系数，故未能构成真正的效应边界（这一点如实披露）。更严谨的边界需引入回归插补 + 偏差调整（如 Heckman 选择模型），留待后续扩展。综上，DE 与 LSV 的稳健性性质不同：<strong>LSV = 推断脆弱（口径依赖/被同层掩盖）；DE = 内部显著、外部效度受限（选择偏倚）</strong>——两者均已从"弱点"转化为可诚实披露的方法洞见。</p>
</div>

"""

assert BLOCK.count("<h3>4.4.8") == 1
assert BLOCK.count("<h3>4.4.9") == 1

new_s = s.replace(ANCHOR, BLOCK + ANCHOR, 1)
assert new_s != s, "未插入"
io.open(P, "w", encoding="utf-8").write(new_s)
print("插入成功：新增 §4.4.8 + §4.4.9，文件长度 %d -> %d" % (len(s), len(new_s)))
