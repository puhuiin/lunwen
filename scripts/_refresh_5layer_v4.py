# -*- coding: utf-8 -*-
"""
刷新 5层架构完整研究方案.html 实证更正章节至 v4 双向聚类权威值。
方法：子串级精确替换 + 每处出现次数断言（必须 ==1，否则 loud fail）。
来源：merged_manuscript.html 已锁定的 v4 双向聚类（CGM2011）权威值：
  de  β=−0.00606  t=−2.99  p=0.003***
  lsv β=+0.01548 t=+0.77  p=0.441 n.s.
  risk_asym β=+0.07311 t=+3.57 p≈0.000***
WCB (two-way, 修正H₀): DE 0.014** / LSV 0.229 / RA 0.000***
置换 (two-way): DE 0.047* / LSV 0.51 / RA 0.02*
"""
import io, shutil, datetime, sys

SRC = r"D:\Desktop\基金经理行为分析研究\5层架构完整研究方案\5层架构完整研究方案.html"
BAK = SRC + ".bak_v4pre_" + datetime.date.today().strftime("%Y%m%d") + ".html"

s = io.open(SRC, encoding="utf-8").read()

# (old, new) —— 每个 old 必须在全文中恰好出现 1 次
REPL = [
    # --- 顶部 meta 行 (L216) ---
    ("v20-era 快照，未更新至 v3",
     "v20-era 快照，未更新至 v3/v4"),
    ("已被 v3 诚实重分析推翻，见顶部《v3 诚实重分析更正对照总表》。权威 v3 结果",
     "已被 v3/v4 诚实重分析推翻，见顶部《v3/v4 诚实重分析更正对照总表》。权威 v4 结果"),

    # --- 版本状态声明列表项 ---
    ("LSV 在诚实 M4 中不再显著</strong>（t=1.23，p=0.22）",
     "LSV 在诚实 M4 中仍不显著</strong>（双向聚类 t=+0.77，p=0.441）"),
    ("WCB-S 仅 RiskAsym 边际显著</strong>（p=0.049，10% 水平）；de / lsv 均不显著。",
     "WCB-S（双向聚类+修正H₀）下 DE 与 RiskAsym 均显著</strong>（DE p=0.014**、RA p=0.000***），仅 LSV 不显著（p=0.229）；原 v3 单维口径误判 DE 不显著（p=0.188）已修正。"),

    # --- 权威来源 (L237) ---
    ("权威 v3 来源",
     "权威 v4 来源"),
    ("（已全量刷新至 v3）、",
     "（已全量刷新至 v4 双向聚类权威值）、<code>_repro_M4_authoritative_v4_2026-08-16.py</code>、<code>_v4_robust.json</code>、"),

    # --- 总表标题 (L243) ---
    ("零、v3 诚实重分析更正对照总表",
     "零、v3/v4 诚实重分析更正对照总表"),

    # --- M4 L5 系数行 (L247 总表，整行唯一) ---
    ("<tr><td>M4 核心模型 L5 系数</td><td>de t=−2.22** / lsv t=3.88*** / risk_asym t=5.49***（三指标全显著）</td><td>de β=−0.00606 t=−2.50** / lsv β=0.01548 t=1.23（<strong>不显著</strong>）/ risk_asym β=0.07311 t=4.53***</td><td><span class=\"tag tag-problem\">LSV 不显著</span></td></tr>",
     "<tr><td>M4 核心模型 L5 系数（双向聚类 SE）</td><td>de t=−2.22** / lsv t=3.88*** / risk_asym t=5.49***（三指标全显著）</td><td>de β=−0.00606 t=−2.99*** / lsv β=+0.01548 t=+0.77（<strong>不显著</strong>）/ risk_asym β=+0.07311 t=+3.57***</td><td><span class=\"tag tag-problem\">LSV 不显著</span></td></tr>"),
    # --- 7.12.1 M0-M4 更正框（v3 单维 -> v4 双向聚类）---
    ("v3 诚实 M4（N=2,264 / 348 基金）下三指标<strong>并未全显著</strong>：de β=−0.00606 t=−2.50**（**）、lsv β=0.01548 t=1.23（<strong>不显著</strong>）、risk_asym β=0.07311 t=4.53***；",
     "v4 双向聚类诚实 M4（N=2,264 / 348 基金）下三指标<strong>并未全显著</strong>：de β=−0.00606 t=−2.99***（***）、lsv β=+0.01548 t=+0.77（<strong>不显著</strong>）、risk_asym β=+0.07311 t=+3.57***；"),

    # --- WCB-S 行 (L251) ---
    ("WCB-S p：de 0.188 / lsv 0.343 / risk_asym 0.049（仅 RA 边际显著 10%）",
     "WCB-S p：DE 0.014** / LSV 0.229 / RiskAsym 0.000***（DE 与 RA 均显著，仅 LSV 不显著）"),

    # --- 统计功效行 (L254) ---
    ("DE 在 M4 中 t=−2.50** 仍显著，LSV 不显著",
     "DE 在 M4 中双向聚类 t=−2.99*** 仍显著，LSV 不显著（t=+0.77, p=0.441）"),
]

# (anchor, block) —— 在 anchor 后插入 block；anchor 必须恰好出现 1 次
V4_LOCK_LI = ('</li>\n      <li><strong>中介效应仅 RA_RV、DE_RV 显著</strong>；LSV_RV 与全部 TO 路径均不显著。</li>',
    '</li>\n      <li><strong>中介效应仅 RA_RV、DE_RV 显著</strong>；LSV_RV 与全部 TO 路径均不显著。</li>\n'
    '      <li><strong>v4 双向聚类权威锁定</strong>：主回归聚类 SE 由单维基金聚类升级为基金×年份双向聚类（CGM 2011），并修正 WCB-S 零假设（H₀:β_L5=0 下对受限残差重抽样）。最终：RiskAsym（t=+3.57***）与 DE（t=−2.99***）在渐近 / WCB / 置换三种推断口径下均稳健显著；LSV（t=+0.77, p=0.441）始终不显著。</li>')

WCB_V4_BOX = ('WCB-S进一步确认了推断的稳健性。</p>',
    'WCB-S进一步确认了推断的稳健性。</p>\n'
    '<div class="callout danger"><p><strong>⚠️ v4 更正（WCB-S / 7.9.7）</strong>：v4 将主回归聚类标准误升级为基金×年份'
    '<strong>双向聚类</strong>（Cameron-Gelbach-Miller 2011），并<strong>修正 WCB-S 零假设</strong>——在 H₀:β_L5=0 下对受限模型残差施加 '
    'Rademacher 符号重抽样（1999 次），而非在备择假设下重抽样。结果：DE p=<strong>0.014**</strong>（显著）、'
    'RiskAsym p=<strong>0.000***</strong>、LSV p=0.229（不显著）。原 v3 单维口径误判 DE 不显著（p=0.188）已被修正——'
    'DE 在 WCB-S 下确显著，与渐近 t（DE −2.99*** / RA +3.57*** / LSV +0.77 n.s.）及置换检验（DE 0.047* / RA 0.02* / LSV 0.51）三方一致。</p></div>')

INSERTS = [V4_LOCK_LI, WCB_V4_BOX]

# ---- 断言 + 执行 ----
failed = False
for i, (old, new) in enumerate(REPL, 1):
    c = s.count(old)
    if c != 1:
        failed = True
        print(f"[FAIL] REPL#{i} count={c} (expected 1)")
        a = s.find(old)
        if a >= 0:
            print("  ctx:", repr(s[max(0,a-25):a+len(old)+25]))
        else:
            print("  (old not found)")

for i, (anchor, block) in enumerate(INSERTS, 1):
    c = s.count(anchor)
    if c != 1:
        failed = True
        print(f"[FAIL] INSERT#{i} count={c} (expected 1)")
        a = s.find(anchor)
        if a >= 0:
            print("  ctx:", repr(s[max(0,a-25):a+len(anchor)+25]))
        else:
            print("  (anchor not found)")

if failed:
    print("ABORTED: 断言失败，未做任何修改。")
    sys.exit(1)

# 全部通过 -> 备份 + 应用
shutil.copyfile(SRC, BAK)
print("backup ->", BAK)

for old, new in REPL:
    s = s.replace(old, new)
for anchor, block in INSERTS:
    s = s.replace(anchor, anchor + block)

io.open(SRC, "w", encoding="utf-8").write(s)
print(f"OK: 应用 {len(REPL)} 处替换 + {len(INSERTS)} 处插入，已写回。")
