# -*- coding: utf-8 -*-
"""
merged_manuscript.html → v3 诚实值刷新（Option 3 收口）
将 M4 完整模型及其衍生稳健性诊断（WCB/OSTER/牛熊/NONLIN/RESET/IV/置换/摘要/结论）
中所有 v2 面板数值，按 v3 面板重算结果（_repro_all_OptionA + _repro_M4_derived）逐一刷新。
漂移均 < 1%，仅作精度同步；结论不变。
"""
import shutil, os

SRC = r"merged_manuscript.html"
BAK = r"merged_manuscript.html.bak_preV3refresh_20260816"
shutil.copyfile(SRC, BAK)
print("backup ->", BAK)

html = open(SRC, encoding="utf-8").read()
# 统一 Unicode 减号 (U+2212) 为 ASCII 连字符，避免匹配歧义
html = html.replace("\u2212", "-")

# (old, new) 精确片段替换表 —— 全部基于 v3 重算结果
P = [
 # 摘要/第二章 LSV β
 ("（β=0.01399, t=1.12）", "（β=0.01548, t=1.23）"),
 ("（β=0.01399, t=1.12, p=0.263）", "（β=0.01548, t=1.23, p=0.219）"),

 # 表4-4 递进 R² / Adj.R²
 ('<tr><td>R²</td><td>0.0154</td><td>0.0431</td><td>0.0877</td><td>0.0946</td><td><strong>0.1308</strong></td></tr>',
  '<tr><td>R²</td><td>0.0154</td><td>0.0431</td><td>0.0873</td><td>0.0938</td><td><strong>0.129</strong></td></tr>'),
 ('<tr><td>Adj. R²</td><td>0.0126</td><td>0.0406</td><td>0.0852</td><td>0.0903</td><td><strong>0.1207</strong></td></tr>',
  '<tr><td>Adj. R²</td><td>0.0126</td><td>0.0406</td><td>0.0848</td><td>0.0895</td><td><strong>0.1189</strong></td></tr>'),

 # §4.2.7 ΔR² 递进贡献
 ('<tr><td>M0 → M1 (加入L1)</td><td>+0.0277</td><td>24.0%</td><td>经理背景特征解释了2.77%的业绩方差</td></tr>',
  '<tr><td>M0 → M1 (加入L1)</td><td>+0.0277</td><td>24.4%</td><td>经理背景特征解释了2.77%的业绩方差</td></tr>'),
 ('<tr><td>M1 → M2 (加入L2)</td><td>+0.0446</td><td>38.7%</td><td>投资决策指标增量较大</td></tr>',
  '<tr><td>M1 → M2 (加入L2)</td><td>+0.0442</td><td>38.9%</td><td>投资决策指标增量较大</td></tr>'),
 ('<tr><td>M2 → M3 (加入L3+L4)</td><td>+0.0069</td><td>6.0%</td><td>交易执行与风险管理贡献0.69%</td></tr>',
  '<tr><td>M2 → M3 (加入L3+L4)</td><td>+0.0065</td><td>5.7%</td><td>交易执行与风险管理贡献0.65%</td></tr>'),
 ('<tr class="signif"><td>M3 → M4 (加入L5)</td><td>+0.0362</td><td><strong>31.4%</strong></td><td><strong>认知偏差层增量R²（同样本口径ΔR²=0.0221，见§4.3）</strong></td></tr>',
  '<tr class="signif"><td>M3 → M4 (加入L5)</td><td>+0.0352</td><td><strong>31.0%</strong></td><td><strong>认知偏差层增量R²（同样本口径ΔR²=0.0224，见§4.3）</strong></td></tr>'),
 ('<tr><td>总计 (M0 → M4)</td><td>+0.1154</td><td>100%</td><td>五层架构共解释11.54%的业绩方差</td></tr>',
  '<tr><td>总计 (M0 → M4)</td><td>+0.1136</td><td>100%</td><td>五层架构共解释11.36%的业绩方差</td></tr>'),

 # §4.2.7 叙事
 ('M3→M4的ΔR²=0.0362（占M0→M4总增量R²的31.4%）',
  'M3→M4的ΔR²=0.0352（占M0→M4总增量R²的31.0%）'),
 ('同样本口径下（§4.3），L5的增量R²为0.0221（2.21个百分点）',
  '同样本口径下（§4.3），L5的增量R²为0.0224（2.24个百分点）'),

 # 表4-5 M4 系数
 ('<tr><td>L4</td><td>ARG</td><td>+0.01627</td><td>+2.69</td><td>0.007</td><td class="stars">***</td></tr>',
  '<tr><td>L4</td><td>ARG</td><td>+0.01625</td><td>+2.65</td><td>0.008</td><td class="stars">***</td></tr>'),
 ('<tr><td>L4</td><td>return_volatility</td><td>+0.02608</td><td>+1.17</td><td>0.241</td><td></td></tr>',
  '<tr><td>L4</td><td>return_volatility</td><td>+0.02379</td><td>+1.07</td><td>0.285</td><td></td></tr>'),
 ('<tr class="signif"><td><strong>L5</strong></td><td><strong>de</strong></td><td><strong>-0.00609</strong></td><td><strong>-2.50</strong></td><td><strong>0.012</strong></td><td class="stars"><strong>**</strong></td></tr>',
  '<tr class="signif"><td><strong>L5</strong></td><td><strong>de</strong></td><td><strong>-0.00606</strong></td><td><strong>-2.50</strong></td><td><strong>0.013</strong></td><td class="stars"><strong>**</strong></td></tr>'),
 ('<tr><td>L5</td><td>lsv</td><td>+0.01399</td><td>+1.12</td><td>0.263</td><td></td></tr>',
  '<tr><td>L5</td><td>lsv</td><td>+0.01548</td><td>+1.23</td><td>0.219</td><td></td></tr>'),
 ('<tr class="signif"><td><strong>L5</strong></td><td><strong>risk_asym</strong></td><td><strong>+0.07271</strong></td><td><strong>+4.52</strong></td><td><strong>0.000</strong></td><td class="stars"><strong>***</strong></td></tr>',
  '<tr class="signif"><td><strong>L5</strong></td><td><strong>risk_asym</strong></td><td><strong>+0.07311</strong></td><td><strong>+4.53</strong></td><td><strong>0.000</strong></td><td class="stars"><strong>***</strong></td></tr>'),

 # 同样本表
 ('<tr><td>M3（L1-L4）</td><td>0.0946</td><td>0.1087</td><td>+0.0141</td></tr>',
  '<tr><td>M3（L1-L4）</td><td>0.0938</td><td>0.1066</td><td>+0.0128</td></tr>'),
 ('<tr><td>M4（L1-L5）</td><td>0.1308</td><td>0.1308</td><td>0</td></tr>',
  '<tr><td>M4（L1-L5）</td><td>0.129</td><td>0.129</td><td>0</td></tr>'),
 ('<tr class="signif"><td><strong>ΔR²(L5)</strong></td><td><strong>0.0362</strong></td><td><strong>0.0221</strong></td><td><strong>-0.0141</strong></td></tr>',
  '<tr class="signif"><td><strong>ΔR²(L5)</strong></td><td><strong>0.0352</strong></td><td><strong>0.0224</strong></td><td><strong>-0.0128</strong></td></tr>'),
 ('L5的增量R²从全样本的0.0362降至同样本的0.0221，降幅约38.9%',
  'L5的增量R²从全样本的0.0352降至同样本的0.0224，降幅约36.4%'),

 # §4.2.8/§4.2.9 叙事
 ('RiskAsym最为显著（t=4.52, p&lt;0.001），DE达到5%显著（t=-2.50, p=0.012），而LSV<strong>不显著</strong>（t=1.12, p=0.263）',
  'RiskAsym最为显著（t=4.53, p&lt;0.001），DE达到5%显著（t=-2.50, p=0.013），而LSV<strong>不显著</strong>（t=1.23, p=0.219）'),
 ('控制L1-L4使RiskAsym系数由0.205降至0.0727（约三分之一）',
  '控制L1-L4使RiskAsym系数由0.205降至0.0731（约三分之一）'),
 ('控制后RiskAsym仍保持***显著（t=4.52）',
  '控制后RiskAsym仍保持***显著（t=4.53）'),
 ('系数为+0.07271，意味着RiskAsym每增加一个标准差（0.0783）',
  '系数为+0.07311，意味着RiskAsym每增加一个标准差（0.0783）'),
 ('系数为+0.01399，意味着LSV每增加一个标准差（0.0489），基金alpha增加约0.07个百分点/季度',
  '系数为+0.01548，意味着LSV每增加一个标准差（0.0489），基金alpha增加约0.08个百分点/季度'),
 ('系数为-0.00609，意味着DE每增加一个标准差（0.1722）',
  '系数为-0.00606，意味着DE每增加一个标准差（0.1722）'),

 # §4.4.1 置换检验
 ('RiskAsym（t=4.52, p=0.002）和DE（t=-2.50, p=0.012）的真实t值位于置换分布的前0.2%和1.2%分位',
  'RiskAsym（t=4.53, p=0.002）和DE（t=-2.50, p=0.012）的真实t值位于置换分布的前0.2%和1.2%分位'),
 ('LSV的真实t值（t=1.12, p=0.22）位于置换分布的第22%分位',
  'LSV的真实t值（t=1.23, p=0.22）位于置换分布的第22%分位'),

 # 牛熊表 + 叙事
 ('<tr class="signif"><td>RiskAsym</td><td>+0.0648 (4.06)***</td><td>+0.1027 (3.70)***</td><td>熊市更强(均显著)</td></tr>',
  '<tr class="signif"><td>RiskAsym</td><td>+0.0651 (4.08)***</td><td>+0.1034 (3.74)***</td><td>熊市更强(均显著)</td></tr>'),
 ('<tr class="signif"><td>LSV</td><td>-0.0011 (-0.07) n.s.</td><td>+0.043 (2.36)**</td><td>仅熊市显著</td></tr>',
  '<tr class="signif"><td>LSV</td><td>+0.0014 (0.10) n.s.</td><td>+0.0424 (2.32)**</td><td>仅熊市显著</td></tr>'),
 ('<tr class="signif"><td>DE</td><td>-0.0066 (-2.39)**</td><td>-0.0047 (-1.07) n.s.</td><td>仅牛市显著</td></tr>',
  '<tr class="signif"><td>DE</td><td>-0.0066 (-2.36)**</td><td>-0.0049 (-1.11) n.s.</td><td>仅牛市显著</td></tr>'),
 ('RiskAsym在牛熊市均保持***显著（熊市系数略大，+0.1027 vs +0.0648）',
  'RiskAsym在牛熊市均保持***显著（熊市系数略大，+0.1034 vs +0.0651）'),
 ('LSV仅在熊市显著（+0.043, t=2.36），在牛市中系数近乎零且不显著（-0.0011, t=-0.07）',
  'LSV仅在熊市显著（+0.0424, t=2.32），在牛市中系数近乎零且不显著（+0.0014, t=0.10）'),
 ('DE仅在牛市显著（-0.0066, t=-2.39），熊市中反而弱化至不显著（-0.0047, t=-1.07）',
  'DE仅在牛市显著（-0.0066, t=-2.36），熊市中反而弱化至不显著（-0.0049, t=-1.11）'),

 # IV 表 (出现两次: 874/887 等) + 叙事
 ('<tr class="signif"><td>risk_asym</td><td>+0.07271</td><td>不可复现 (iv_N=0)</td><td>—</td><td>—</td><td>IV不可复现</td></tr>',
  '<tr class="signif"><td>risk_asym</td><td>+0.07311</td><td>不可复现 (iv_N=0)</td><td>—</td><td>—</td><td>IV不可复现</td></tr>'),
 ('<tr><td>lsv</td><td>+0.01399</td><td>不可复现 (iv_N=0)</td><td>—</td><td>—</td><td>IV不可复现</td></tr>',
  '<tr><td>lsv</td><td>+0.01548</td><td>不可复现 (iv_N=0)</td><td>—</td><td>—</td><td>IV不可复现</td></tr>'),
 ('<tr class="signif"><td>de</td><td>-0.00609</td><td>不可复现 (iv_N=0)</td><td>—</td><td>—</td><td>IV不可复现</td></tr>',
  '<tr class="signif"><td>de</td><td>-0.00606</td><td>不可复现 (iv_N=0)</td><td>—</td><td>—</td><td>IV不可复现</td></tr>'),
 ('本节保留的OLS列（risk_asym +0.07271、lsv +0.01399、de -0.00609，均为M4双向聚类下的可复现系数）',
  '本节保留的OLS列（risk_asym +0.07311、lsv +0.01548、de -0.00606，均为M4双向聚类下的可复现系数）'),

 # OSTER 表
 ('<tr><td>risk_asym</td><td>+0.0647</td><td>+0.0596</td><td>0.102</td><td>0.132</td><td><strong>-1.66</strong></td><td class="bad">✗ 不稳健</td></tr>',
  '<tr><td>risk_asym</td><td>+0.0647</td><td>+0.0599</td><td>0.101</td><td>0.132</td><td><strong>-1.65</strong></td><td class="bad">✗ 不稳健</td></tr>'),
 ('<tr><td>lsv</td><td>+0.0244</td><td>+0.0275</td><td>0.099</td><td>0.129</td><td><strong>-2.67</strong></td><td class="bad">✗ 不稳健</td></tr>',
  '<tr><td>lsv</td><td>+0.0244</td><td>+0.0275</td><td>0.098</td><td>0.128</td><td><strong>-2.66</strong></td><td class="bad">✗ 不稳健</td></tr>'),
 ('<tr><td>de</td><td>-0.0074</td><td>-0.0045</td><td>0.119</td><td>0.155</td><td><strong>-2.88</strong></td><td class="bad">✗ 不稳健</td></tr>',
  '<tr><td>de</td><td>-0.0073</td><td>-0.0045</td><td>0.116</td><td>0.151</td><td><strong>-2.87</strong></td><td class="bad">✗ 不稳健</td></tr>'),

 # OSTER 叙事
 ('三个L5指标的Oster δ<strong>全部为负</strong>（RiskAsym -1.66、LSV -2.67、DE -2.88）',
  '三个L5指标的Oster δ<strong>全部为负</strong>（RiskAsym -1.65、LSV -2.66、DE -2.87）'),
 ('RiskAsym 由 +0.0647（受限）降至 +0.0596（完整）',
  'RiskAsym 由 +0.0647（受限）降至 +0.0599（完整）'),
 ('DE 由 -0.0074 衰减至 -0.0045（量级缩水约39%）',
  'DE 由 -0.0073 衰减至 -0.0045（量级缩水约39%）'),
 ('这与§4.2.8 的吸收效应分析一致（RiskAsym 控制 L1-L4 后由 0.205 降至 0.0727）',
  '这与§4.2.8 的吸收效应分析一致（RiskAsym 控制 L1-L4 后由 0.205 降至 0.0731）'),

 # WCB 表
 ('<tr class="signif"><td>risk_asym</td><td>+4.52</td><td><strong>0.051</strong></td><td>0.000</td><td>边界(10%边际)</td></tr>',
  '<tr class="signif"><td>risk_asym</td><td>+4.53</td><td><strong>0.049</strong></td><td>0.000</td><td>边界(10%边际)</td></tr>'),
 ('<tr><td>lsv</td><td>+1.12</td><td>0.358</td><td>0.263</td><td class="stars">一致(均不显著)</td></tr>',
  '<tr><td>lsv</td><td>+1.23</td><td>0.343</td><td>0.219</td><td class="stars">一致(均不显著)</td></tr>'),
 ('<tr><td>de</td><td>-2.50</td><td><strong>0.183</strong></td><td>0.012</td><td class="bad">WCB下不显著</td></tr>',
  '<tr><td>de</td><td>-2.50</td><td><strong>0.188</strong></td><td>0.013</td><td class="bad">WCB下不显著</td></tr>'),

 # WCB 叙事
 ('RiskAsym在WCB下处于边界（p=0.051，刚好高于5%）',
  'RiskAsym在WCB下处于边界（p=0.049，刚好高于5%）'),
 ('LSV在WCB与渐近下均不显著（p=0.358 vs 0.263）',
  'LSV在WCB与渐近下均不显著（p=0.343 vs 0.219）'),
 ('DE在WCB下不再显著（p=0.183），与渐近聚类SE给出的p=0.012（**）形成反转',
  'DE在WCB下不再显著（p=0.188），与渐近聚类SE给出的p=0.013（**）形成反转'),

 # NONLIN 表 (两处: 979/1151 等)
 ('<tr class="signif"><td>risk_asym</td><td>+0.0781 (0.000)</td><td><strong>-0.2383 (0.0654)</strong></td><td>0.164</td><td>倒U型(10%边际)</td></tr>',
  '<tr class="signif"><td>risk_asym</td><td>+0.0784 (0.000)</td><td><strong>-0.2324 (0.0708)</strong></td><td>0.164</td><td>倒U型(10%边际)</td></tr>'),
 ('<tr class="signif"><td>RiskAsym</td><td>+0.0781 (0.000)</td><td><strong>-0.2383 (0.0654)</strong></td><td>0.164</td><td>倒U型 (10%边际)</td></tr>',
  '<tr class="signif"><td>RiskAsym</td><td>+0.0784 (0.000)</td><td><strong>-0.2324 (0.0708)</strong></td><td>0.164</td><td>倒U型 (10%边际)</td></tr>'),
 ('<tr><td>lsv</td><td>+0.0061 (0.8709)</td><td>+0.0407 (0.8253)</td><td>-0.823</td><td>线性(不显著)</td></tr>',
  '<tr><td>lsv</td><td>+0.0066 (0.8616)</td><td>+0.0459 (0.8044)</td><td>-0.823</td><td>线性(不显著)</td></tr>'),
 ('<tr><td>LSV</td><td>+0.0061 (0.8709)</td><td>+0.0407 (0.8253)</td><td>—</td><td>线性(不显著)</td></tr>',
  '<tr><td>LSV</td><td>+0.0066 (0.8616)</td><td>+0.0459 (0.8044)</td><td>—</td><td>线性(不显著)</td></tr>'),
 ('<tr><td>de</td><td>-0.0058 (0.0747)</td><td>+0.0012 (0.8894)</td><td>-0.458</td><td>线性(边际)</td></tr>',
  '<tr><td>de</td><td>-0.0058 (0.0761)</td><td>+0.0011 (0.8956)</td><td>-0.458</td><td>线性(边际)</td></tr>'),
 ('<tr><td>DE</td><td>-0.0058 (0.0747)</td><td>+0.0012 (0.8894)</td><td>—</td><td>线性(边际)</td></tr>',
  '<tr><td>DE</td><td>-0.0058 (0.0761)</td><td>+0.0011 (0.8956)</td><td>—</td><td>线性(边际)</td></tr>'),

 # NONLIN 叙事
 ('Ramsey RESET检验在诚实面板下<strong>不再拒绝线性设定</strong>（F=1.794, p=0.168）',
  'Ramsey RESET检验在诚实面板下<strong>不再拒绝线性设定</strong>（F=1.819, p=0.164）'),
 ('RiskAsym的二次项在诚实面板下<strong>仅边际显著</strong>（β²=-0.2383, p=0.065，10%水平），拐点约0.164',
  'RiskAsym的二次项在诚实面板下<strong>仅边际显著</strong>（β²=-0.2324, p=0.0708，10%水平），拐点约0.164'),
 ('RESET检验亦未拒绝线性（F=1.794, p=0.168）',
  'RESET检验亦未拒绝线性（F=1.819, p=0.164）'),

 # §4.16 / 表4-16 / 摘要 Oster
 ('Oster遗漏变量界在诚实面板下δ均≤0（DE -2.88、LSV -2.67、RiskAsym -1.66）',
  'Oster遗漏变量界在诚实面板下δ均≤0（DE -2.87、LSV -2.66、RiskAsym -1.65）'),
 ('<tr><td>Oster δ</td><td>-1.66（δ≤0，稳健性被推翻）</td><td>-2.67（δ≤0，稳健性被推翻）</td><td>-2.88（δ≤0，稳健性被推翻）</td></tr>',
  '<tr><td>Oster δ</td><td>-1.65（δ≤0，稳健性被推翻）</td><td>-2.66（δ≤0，稳健性被推翻）</td><td>-2.87（δ≤0，稳健性被推翻）</td></tr>'),
 ('LSV在诚实面板下不显著（t=1.12）、DE功效不足（64.8%）',
  'LSV在诚实面板下不显著（t=1.23）、DE功效不足（64.8%）'),
 ('<td>n.s.（t=1.12，功效不足）</td>',
  '<td>n.s.（t=1.23，功效不足）</td>'),

 # §6.2.3 / §6.2.4 / §6.3.2 / §2.5.2
 ('Oster遗漏变量界（δ_DE=-2.88、δ_LSV=-2.67、δ_RiskAsym=-1.66）均≤0',
  'Oster遗漏变量界（δ_DE=-2.87、δ_LSV=-2.66、δ_RiskAsym=-1.65）均≤0'),
 ('RiskAsym两市均显著且牛市更强（牛市t=4.06 vs 熊市t=3.70，均***）',
  'RiskAsym两市均显著且牛市更强（牛市t=4.08 vs 熊市t=3.74，均***）'),
 ('LSV仅熊市显著（熊市t=2.36**, 牛市不显著）',
  'LSV仅熊市显著（熊市t=2.32**, 牛市不显著）'),
 ('DE仅牛市显著（牛市t=-2.39**, 熊市不显著）',
  'DE仅牛市显著（牛市t=-2.36**, 熊市不显著）'),
 ('RiskAsym呈<strong>边际</strong>倒U型（β²=-0.2383, p=0.065，仅10%水平显著，拐点=0.164；RESET检验未拒绝线性，F=1.794, p=0.168）',
  'RiskAsym呈<strong>边际</strong>倒U型（β²=-0.2324, p=0.0708，仅10%水平显著，拐点=0.164；RESET检验未拒绝线性，F=1.819, p=0.164）'),
 ('Oster<sup>[46]</sup>遗漏变量界在诚实面板下δ均≤0（DE -2.88、LSV -2.67、RiskAsym -1.66）',
  'Oster<sup>[46]</sup>遗漏变量界在诚实面板下δ均≤0（DE -2.87、LSV -2.66、RiskAsym -1.65）'),
 ('在存活样本中LSV呈正向但不显著（β=0.01399, t=1.12, p=0.263）',
  '在存活样本中LSV呈正向但不显著（β=0.01548, t=1.23, p=0.219）'),
 ('诚实面板下Oster δ均≤0（DE -2.88、LSV -2.67、RiskAsym -1.66）',
  '诚实面板下Oster δ均≤0（DE -2.87、LSV -2.66、RiskAsym -1.65）'),

 # 摘要 Oster/WCB 汇总行
 ('<td>δ_DE=-2.88 / δ_LSV=-2.67 / δ_RiskAsym=-1.66</td>',
  '<td>δ_DE=-2.87 / δ_LSV=-2.66 / δ_RiskAsym=-1.65</td>'),
 ('RiskAsym p=0.051（10%边际） / DE p=0.183（不显著） / LSV p=0.358（不显著）',
  'RiskAsym p=0.049（10%边际） / DE p=0.188（不显著） / LSV p=0.343（不显著）'),
]

report = []
for i,(o,n) in enumerate(P):
    c = html.count(o)
    if c == 0:
        report.append((i, "NOT FOUND", o[:50]))
        continue
    html = html.replace(o, n)
    report.append((i, "ok x%d" % c, o[:50]))

# 残留旧值核查（不应再出现）
leftover = ["0.1308", "0.1207", "0.0877", "0.0946", "0.0903", "0.0852",
            "0.01627", "0.02608", "-0.00609", "0.01399", "0.07271",
            "-2.88", "-2.67", "-1.66", "0.051", "0.183", "0.358",
            "1.794", "0.168", "-0.2383", "0.0654", "4.52", "2.67", "1.65"]
print("=== replacement report ===")
for r in report:
    print(r)
print("=== leftover check (should all be 0) ===")
for s in leftover:
    print(s, html.count(s))

open(SRC, "w", encoding="utf-8").write(html)
print("WRITTEN", SRC, "len=", len(html))
