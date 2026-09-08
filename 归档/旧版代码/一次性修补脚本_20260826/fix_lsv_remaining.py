# -*- coding: utf-8 -*-
"""
fix_lsv_remaining.py
完成 Option A 清理中脚本因「前缀/顺序」问题失败的 5 处替换。
策略：直接从文件切出当前真实字节（old 由 html[s:e] 取得），彻底规避隐藏字符/截断问题。
"""
import shutil

SRC = r"d:\Desktop\基金经理行为分析研究\merged_manuscript.html"
BAK = SRC + ".bak_lsvfix"
shutil.copy(SRC, BAK)
print("已备份 ->", BAK)

html = open(SRC, encoding="utf-8").read()
orig_len = len(html)

def slice_replace(start_anchor, end_anchor, new, label):
    global html
    s = html.find(start_anchor)
    if s < 0:
        raise SystemExit(f"[FAIL] 起始锚未找到: {label}")
    e = html.find(end_anchor, s)
    if e < 0:
        raise SystemExit(f"[FAIL] 结束锚未找到: {label}")
    e += len(end_anchor)
    old = html[s:e]
    if html.count(old) != 1:
        raise SystemExit(f"[FAIL] old 非唯一 ({html.count(old)}次): {label}")
    html = html[:s] + new + html[e:]
    print(f"[OK] {label}  替换长度 {len(old)} -> {len(new)}")

# ---------- #1 §4.2.2 bootstrap 脚注 (642) ----------
slice_replace(
    '<p class="footnote">稳健性：对297只基金做2,000次有放回重抽样重估截面回归',
    '</p>',
    '<p class="footnote">稳健性：对 N=200 只基金做 2,000 次有放回重抽样重估截面回归，RiskAsym 的 bootstrap 显著性稳健（mean|t|≈4.6，96.6% 的 bootstrap |t|&gt;2.58）；LSV 的 bootstrap 不显著（mean|t|≈0.8，仅 6.1% |t|&gt;1.96），印证其“选择敏感”定位；DE 在截面 bootstrap 下仍显著（mean|t|≈3.4，74.7% |t|&gt;2.58），与其在组内、前向维度的一致显著相呼应（见§4.2.3、§4.2.4）。</p>',
    "bootstrap脚注",
)

# ---------- #2 §4.16 证据表 DE 列 (1052) ----------
if html.count('选择敏感（修正面板下不稳健）</td><td>不显著</td></tr>') != 1:
    raise SystemExit("[FAIL] 证据表 DE 列锚点计数异常")
html = html.replace(
    '选择敏感（修正面板下不稳健）</td><td>不显著</td></tr>',
    '选择敏感（修正面板下不稳健）</td><td class="stars">*** (4Q t=-7.11; 1Q t=-4.81)</td></tr>',
    1,
)
print("[OK] 证据表DE列")

# ---------- #3 文献综述 -0.168 (200) ----------
slice_replace(
    '中国基金整体LSV均值为-0.168',
    '基金业绩更好',
    '中国基金整体LSV均值为+0.096（标准LSV1992非负羊群强度，基金层均值恒为非负），呈现正向羊群特征——与早期“显著羊群”的结论方向一致；同时本研究发现LSV系数为正，即更贴近市场共识（羊群强度更高）的基金业绩更好',
    "文献综述-0.168",
)

# ---------- #4 §3.3 ICI↔HHI (298) ----------
slice_replace(
    '诚实截面（N=297）上 ICI 与 HHI 的相关系数仅 0.20',
    '均予保留。',
    'ICI 与 HHI 在基金层相关系数高达 +0.84（面板级 +0.70），二者高度共线（VIF 约 1.9–3.4，虽低于 10 警戒线但远非正交）——ICI 与 HHI 均由行业权重导出（ICI = HHI_基金 − 2·Σ_i w_i·W_i + 常数），实为同一“行业集中”维度的两种表达；故实证中以 HHI 为主、ICI 仅作描述性对照，避免对同一维度的重复计数。',
    "ICI-HHI相关性",
)

# ---------- #5 §6.6 结论（被 line29 前缀替换破坏） ----------
slice_replace(
    'RiskAsym（条件波动率不对称）与LSV（羊群效应）的证据定位不同：',
    '预测力不能被上行市场择时能力吸收。',
    'RiskAsym（条件波动率不对称）与LSV（羊群效应）的证据定位不同：RiskAsym在诚实的N=200截面回归中高度显著（t=4.55），并能显著预测未来4季度业绩（t=10.51），预测力不能被上行市场择时能力吸收；LSV则对样本/控制选择高度敏感（含规模口径不显著，t=0.06），不属稳健预测因子。',
    "结论段落",
)

open(SRC, "w", encoding="utf-8").write(html)
print(f"\n完成。长度变化 {orig_len} -> {len(html)} (Δ{len(html)-orig_len})")
