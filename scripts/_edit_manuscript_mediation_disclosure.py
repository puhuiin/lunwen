# -*- coding: utf-8 -*-
"""统一编辑 merged_manuscript.html：
(1) 重写脱节的"待重算项"披露(429-431) -> 准确 v3 重算状态；
(2) 回填 §4.11/§5.1 中介表+脚注+叙述到 v3 口径(对齐 _recompute_mediation_v3.json / v3 JSON E_mediation)。
备份 + 替换报告 + 残留核查。
"""
import shutil, re
F="merged_manuscript.html"
shutil.copy(F, F+".bak_meddisc_20260816")
h=open(F,encoding="utf-8").read()

reps=[]

# ---------- (1) 披露重写 ----------
old_disc=('<p><strong>待重算项（须在提交前完成，避免审稿人穿透）：</strong>第四章中引用旧带符号 LSV 口径的全部稳健性检验——\n'
 'Fama-MacBeth（§4.7）、bootstrap 置换（§4.8）、Oster 遗漏变量界（§4.10）、WCB-S（§4.9）、安慰剂置换（§4.9）、规范曲线（§4.9）、\n'
 '中介效应（§4.11）、八分类画像（§4.13）——其 LSV 相关 t 值均为旧口径结果，须在同一修正面板上重跑；本章证据表（表4-16）相应单元格已标注"待重算/选择敏感"。RiskAsym、DE 相关结果在修正面板下保持稳健，可直接沿用。</p>')
new_disc=('<p><strong>v3 面板 + 修正 LSV 口径重算状态（截至 2026-08-16）：</strong>主模型 M4 与递进回归、Oster 遗漏变量界（§4.6）、WCB-S（§4.7）、'
 '置换检验（§4.4.1）、牛熊市子样本（§4.4.2）、非线性与 RESET（§4.10）均已在同一 v3 诚实面板（含 TO_wind、修正非负 LSV）上重算并刷新；'
 '中介效应（§4.11/§5.1）本轮回填至 v3 口径（LSV→RV 间接效应在 v3 上不再显著，仅 RiskAsym、DE 两路径显著）。'
 '<strong>仍须提交前核验/重算的项</strong>：(1) Fama-MacBeth（§4.4.3）——其 LSV 系数 +0.0253 已为修正口径，但 NW t 值须在 v3 上复核；'
 '(2) 规范曲线分析（§4.9）——其唯一可用脚本 spec_curve.py 读取<strong>模拟占位面板</strong>（mvp_panel_v20，已隔离），当前 §4.9 的 36/36、29/36 等显著性计数'
 '<strong>可能基于模拟数据</strong>，须在真实 v3 面板上重算并替换（重算已完成，见 §4.9 更新）；'
 '(3) 八分类画像（§5.7）与 §4.2.2 截面 bootstrap 脚注须在 v3 上复核。RiskAsym、DE 相关结果在 v3 下保持稳健。</p>')
reps.append(("披露重写", old_disc, new_disc))

# ---------- (2) §4.11 表 (993-998) ----------
reps.append(("411-LSV_RV",
 '<tr class="signif"><td>LSV → return_vol → 业绩</td><td>0.0255</td><td>0.0296</td><td>0.00075</td><td>[-0.00004, 0.00191]</td><td class="stars">✓**</td></tr>',
 '<tr><td>LSV → return_vol → 业绩</td><td>0.0199</td><td>0.028</td><td>0.00056</td><td>[-0.00016, 0.00153]</td><td>✗</td></tr>'))
reps.append(("411-LSV_TO",
 '<td>LSV → TO_wind → 业绩</td><td>-8121.23</td><td>≈0.000</td><td>0.00198</td><td>[-0.05316, 0.00773]</td>',
 '<td>LSV → TO_wind → 业绩</td><td>-7875.58</td><td>≈0.000</td><td>0.00185</td><td>[-0.0516, 0.00725]</td>'))
reps.append(("411-RA_TO",
 '<td>RiskAsym → TO_wind → 业绩</td><td>-11532.95</td><td>≈0.000</td><td>0.00281</td><td>[-0.07817, 0.01131]</td>',
 '<td>RiskAsym → TO_wind → 业绩</td><td>-11532.95</td><td>≈0.000</td><td>0.00272</td><td>[-0.07885, 0.01099]</td>'))
reps.append(("411-DE_RV",
 '<tr class="signif"><td>DE → return_vol → 业绩</td><td>-0.0524</td><td>0.0296</td><td>-0.00155</td><td>[-0.00296, -0.00038]</td><td class="stars">✓**</td></tr>',
 '<tr class="signif"><td>DE → return_vol → 业绩</td><td>-0.0563</td><td>0.028</td><td>-0.00157</td><td>[-0.00302, -0.00026]</td><td class="stars">✓**</td></tr>'))
reps.append(("411-DE_TO",
 '<td>DE → TO_wind → 业绩</td><td>-5983.43</td><td>≈0.000</td><td>0.00146</td><td>[-0.03646, 0.00643]</td>',
 '<td>DE → TO_wind → 业绩</td><td>-7018.43</td><td>≈0.000</td><td>0.00165</td><td>[-0.03563, 0.00817]</td>'))
reps.append(("411-RA_RV",
 '<tr class="signif"><td>RiskAsym → return_vol → 业绩</td><td>0.5662</td><td>0.0296</td><td>0.01676</td><td>[0.00380, 0.02921]</td><td class="stars">✓**</td></tr>',
 '<tr class="signif"><td>RiskAsym → return_vol → 业绩</td><td>0.5662</td><td>0.028</td><td>0.01585</td><td>[0.00278, 0.02827]</td><td class="stars">✓**</td></tr>'))

# ---------- (2b) §4.11 脚注 + 叙述 ----------
reps.append(("411-foot",
 'b 路径（TO_wind→业绩）不显著（b_t=-0.728），故换手率渠道非显著中介。return_volatility 的 b 路径均显著（b=0.0296, t=2.57）。Bootstrap 500 次重抽样。',
 'b 路径（TO_wind→业绩）不显著（b_t=-0.702），故换手率渠道非显著中介。return_volatility 的 b 路径均显著（b=0.028, t=2.42）。Bootstrap 500 次重抽样。'))
reps.append(("411-callout",
 '收益波动率（return_volatility）渠道三条路径全部显著</strong>（均在 5% 水平）：',
 '收益波动率渠道中 <strong>RiskAsym 与 DE 两条路径显著（5% 水平），LSV 路径在 v3 诚实面板上不再显著</strong>（间接效应 CI 含零，p=0.16）：'))
reps.append(("411-narr1",
 '<strong>(1) LSV → 收益波动率 → 业绩</strong>（间接效应=+0.00075, p&lt;0.05）：羊群较低的基金波动率相对更高，而收益波动率与业绩在本样本中呈<b>正向</b>关联（b=+0.0296, t=2.57）',
 '<strong>(1) LSV → 收益波动率 → 业绩</strong>（间接效应=+0.00056, 不显著 p=0.16）：羊群较低的基金波动率相对更高，而收益波动率与业绩在本样本中呈<b>正向</b>关联（b=+0.028, t=2.42）'))
reps.append(("411-narr2",
 '<strong>(2) RiskAsym → 收益波动率 → 业绩</strong>（间接效应=+0.01676, p&lt;0.05）',
 '<strong>(2) RiskAsym → 收益波动率 → 业绩</strong>（间接效应=+0.01585, p=0.012）'))
reps.append(("411-narr3",
 '<strong>(3) DE → 收益波动率 → 业绩</strong>（间接效应=-0.00155, p&lt;0.05）',
 '<strong>(3) DE → 收益波动率 → 业绩</strong>（间接效应=-0.00157, p=0.008）'))
reps.append(("411-narr4",
 '中介检验使用简化设定（仅 X + M + 控制），return_volatility 的 b 路径在简化设定下显著（t=2.57），说明波动率渠道在部分设定下成立、在完整控制集下被吸收',
 '中介检验的 b 路径采用与 M4 同控制集设定（含全部 M4 控制变量），return_volatility 的 b 路径显著（t=2.42）；而在 M4 完整模型中 RV 自身系数（含全部三个 L5）不显著（t=1.07），说明 RV 渠道在部分设定下成立、在完整控制集下被吸收'))

# ---------- (2c) §5.1 表 (1111-1116) ----------
reps.append(("51-LSV_RV",
 '<tr class="signif"><td>LSV → 收益波动率 → 业绩</td><td>0.0255</td><td>0.0296</td><td>0.00075</td><td>[-0.00004, 0.00190]</td><td>0.068</td><td class="stars">✓ **(边际)</td>',
 '<tr><td>LSV → 收益波动率 → 业绩</td><td>0.0199</td><td>0.028</td><td>0.00056</td><td>[-0.00016, 0.00153]</td><td>0.16</td><td>✗</td>'))
reps.append(("51-LSV_TO",
 '<td>LSV → TO_wind → 业绩</td><td>-8121.23</td><td>≈0.000</td><td>0.00191</td><td>[-0.05242, 0.00756]</td><td>0.680</td>',
 '<td>LSV → TO_wind → 业绩</td><td>-7875.58</td><td>≈0.000</td><td>0.00185</td><td>[-0.0516, 0.00725]</td><td>0.692</td>'))
reps.append(("51-RA_TO",
 '<td>RiskAsym → TO_wind → 业绩</td><td>-11532.95</td><td>≈0.000</td><td>0.00271</td><td>[-0.07898, 0.01114]</td><td>0.672</td>',
 '<td>RiskAsym → TO_wind → 业绩</td><td>-11532.95</td><td>≈0.000</td><td>0.00272</td><td>[-0.07885, 0.01099]</td><td>0.676</td>'))
reps.append(("51-DE_RV",
 '<tr class="signif"><td>DE → 收益波动率 → 业绩</td><td>-0.0524</td><td>0.0296</td><td>-0.00155</td><td>[-0.00306, -0.00028]</td><td>0.016</td><td class="stars">✓ **</td>',
 '<tr class="signif"><td>DE → 收益波动率 → 业绩</td><td>-0.0563</td><td>0.028</td><td>-0.00157</td><td>[-0.00302, -0.00026]</td><td>0.008</td><td class="stars">✓ **</td>'))
reps.append(("51-DE_TO",
 '<td>DE → TO_wind → 业绩</td><td>-5983.43</td><td>≈0.000</td><td>0.00141</td><td>[-0.03627, 0.00634]</td><td>0.640</td>',
 '<td>DE → TO_wind → 业绩</td><td>-7018.43</td><td>≈0.000</td><td>0.00165</td><td>[-0.03563, 0.00817]</td><td>0.608</td>'))
reps.append(("51-RA_RV",
 '<tr class="signif"><td>RiskAsym → 收益波动率 → 业绩</td><td>0.5662</td><td>0.0296</td><td>0.01676</td><td>[0.00304, 0.03025]</td><td>0.012</td><td class="stars">✓ **</td>',
 '<tr class="signif"><td>RiskAsym → 收益波动率 → 业绩</td><td>0.5662</td><td>0.028</td><td>0.01585</td><td>[0.00278, 0.02827]</td><td>0.012</td><td class="stars">✓ **</td>'))

# ---------- (2d) §5.1 脚注 + 叙述 ----------
reps.append(("51-foot",
 'b 路径（TO_wind→业绩）不显著（b_t≈-0.69），故换手率渠道非显著中介。收益波动率 b 路径显著（b=0.0296, t≈2.52）。CI不包含零则间接效应显著。',
 'b 路径（TO_wind→业绩）不显著（b_t≈-0.70），故换手率渠道非显著中介。收益波动率 b 路径显著（b=0.028, t≈2.42）。CI不包含零则间接效应显著。'))
reps.append(("51-lead",
 '仅收益波动率渠道在部分设定下显著。',
 '仅收益波动率渠道中 RiskAsym 与 DE 两条路径在部分设定下显著（LSV 路径不显著）。'))
reps.append(("51-narr1",
 '路径一：LSV → 收益波动率 → 业绩（间接效应=+0.00075, p=0.068，10%边际）</strong>。羊群较低的基金波动率相对更高（a=0.0255），而收益波动率与业绩在本样本中呈正向关联（b=0.0296, t≈2.52）',
 '路径一：LSV → 收益波动率 → 业绩（间接效应=+0.00056, p=0.16，不显著）</strong>。羊群较低的基金波动率相对更高（a=0.0199），而收益波动率与业绩在本样本中呈正向关联（b=0.028, t≈2.42）'))
reps.append(("51-narr2",
 '路径二：DE → 收益波动率 → 业绩（间接效应=-0.00155, p=0.016）',
 '路径二：DE → 收益波动率 → 业绩（间接效应=-0.00157, p=0.008）'))
reps.append(("51-narr3",
 '路径三：RiskAsym → 收益波动率 → 业绩（间接效应=+0.01676, p=0.012）',
 '路径三：RiskAsym → 收益波动率 → 业绩（间接效应=+0.01585, p=0.012）'))
reps.append(("51-narr4",
 '间接效应置信区间均跨越零（p≈0.64–0.68）',
 '间接效应置信区间均跨越零（p≈0.61–0.69）'))

# ---------- 执行 ----------
miss=0
for name,o,n in reps:
    if o in h:
        h=h.replace(o,n,1); print(f"[OK] {name}")
    else:
        miss+=1; print(f"[MISS] {name}")
open(F,"w",encoding="utf-8").write(h)

# ---------- 残留核查 ----------
chk=["0.0296","t=2.57","t≈2.52","b_t=-0.728","b_t≈-0.69","0.0255","p=0.068","待重算项","§4.7）、","§4.10）、","§4.13）——","bootstrap 置换（§4.8）"]
print("\n=== 残留核查 (应全为 0) ===")
bad=0
for c in chk:
    k=h.count(c); 
    if k: bad+=1
    print(f"  {c:>22} {k}")
print(f"\n替换未命中={miss}  残留非零={bad}")
