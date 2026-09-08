# -*- coding: utf-8 -*-
"""主稿系统性数字 QA（2026-08-22）：
提取 merged_manuscript.html 中六指标（RA/DE/LSV/ICI/AS/ARG）相关的所有
"t=±X.XX"数值声明，与 v4 权威基准比对，标记可疑值。
v4 权威（M4 双向聚类，N=2,264/348，R²=0.129）：
  RA +0.07311 t+3.57 / DE -0.00606 t-2.99 / LSV +0.01548 t+0.77
  ICI +0.01804 t+3.74 / AS -0.02982 t-2.81 / ARG +0.01625 t+2.98
其他锚点：TO_wind t+1.07；log_fund_age -0.0042 t-2.53；HHI t+0.19；RV t+0.81；
组内FE DE t-3.64；前向4Q DE t-7.11、RA t+10.51；截面N=200 RA t4.55；
日频子样本 RA+3.22/ICI+2.84/ARG+2.27；选股α RA+5.12/DE-3.03；HM +3.45/-3.42。
"""
import io, re

h = io.open("merged_manuscript.html", encoding="utf-8").read()

# 指标名变体 -> 允许的 t 值集合（含各合法口径）
ALLOWED = {
    "risk_asym|RiskAsym|风险不对称": {3.57, 3.22, 3.29, 3.30, 5.12, 3.45, 4.55, 10.51, 5.77, 6.26, 4.27, 2.87, 2.44, 2.75, 2.50, 2.18, 2.61, 3.23},
    "de|DE|处置效应": {2.99, 3.03, 3.42, 3.64, 7.11, 4.81, 3.28, 4.23, 2.68, 2.87, 2.99},
    "lsv|LSV|羊群": {0.77, 2.78, 2.03, 4.21, 4.07, 3.42, 2.06, 0.06},
    "ICI|行业偏离": {3.74, 2.84, 2.09, 2.49, 2.72, 2.78, 2.53, 1.55, 4.46, 1.24},
    "AS_improved|主动份额|主动持股": {2.81, 2.87, 2.75, 3.85, 4.23, 1.23},
    "ARG|调仓收益缺口|主动风险": {2.98, 2.27, 2.28, 2.36, 3.53, 8.59, 2.66, 0.68, 3.57},
}
TOL = 0.06

flags = []
for m in re.finditer(r"(risk_asym|RiskAsym|风险不对称|\bDE\b|处置效应|\bLSV\b|羊群|\bICI\b|行业偏离|AS_improved|主动份额|主动持股|\bARG\b|调仓收益缺口|主动风险)", h):
    name = m.group(1)
    # 向后看 220 字符内的第一个 t= 值
    tail = h[m.end():m.end()+220]
    tm = re.search(r"[tT][≈=]\s*[+−-]?(\d+\.\d+)", tail)
    if not tm:
        continue
    val = float(tm.group(1))
    # 找到该名对应的允许集合
    for pat, allowed in ALLOWED.items():
        if re.fullmatch(pat, name):
            if not any(abs(val - a) <= TOL for a in allowed):
                ctx = h[max(0, m.start()-60):m.end()+80].replace("\n", " ")
                flags.append((name, val, sorted(allowed), ctx[:130]))
            break

seen = set()
print(f"扫描完成，可疑 t 值 {len(flags)} 处：")
for name, val, allowed, ctx in flags:
    key = (name, val, ctx[:60])
    if key in seen:
        continue
    seen.add(key)
    print(f"  [{name}] t={val}  允许={allowed}\n      …{ctx}…\n")
