# -*- coding: utf-8 -*-
"""_deep_upgrade_main.py — 深度优化实证总结报告（主执行：锚点替换 + 校验）"""
import os, re, shutil, sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
from _deep_upgrade_p1 import S0_GUIDE, S1_BLOCK
from _deep_upgrade_p2 import S2_NEW

TARGET = os.path.join(HERE, "实证总结报告_文献综述回归解读与SDI诊断_2026-08-19.html")
BKDIR = os.path.join(HERE, "备份_报告升级前_20260819")
os.makedirs(BKDIR, exist_ok=True)
shutil.copy2(TARGET, os.path.join(BKDIR, "实证总结报告_文献综述回归解读与SDI诊断_2026-08-19.html"))

html = open(TARGET, encoding="utf-8").read()
orig_len = len(html)
edits = []

def must_find(s, anchor, what):
    i = s.find(anchor)
    assert i >= 0, "锚点未找到: " + what
    return i

# ---- 1. §0 导师导览：插入在 <h2 id="s0">…</h2> 之后 ----
a0 = '<h2 id="s0">§0 摘要：一页看懂全部结论</h2>'
i0 = must_find(html, a0, "§0 标题")
ins = i0 + len(a0)
html = html[:ins] + "\n" + S0_GUIDE + html[ins:]
edits.append("§0 导师导览 +9 块")

# ---- 2. §1 框架 + M0-M4：插入在 lead 段（主动股基画像…）之后 ----
k = must_find(html, "主动股基画像", "§1 lead 段")
j = html.find("</p>", k)
assert j > 0
j_end = j + len("</p>")
S1_FULL = S1_BLOCK + "\n<h3>1.3 数据与变量覆盖率</h3>\n"
html = html[:j_end] + "\n" + S1_FULL + html[j_end:]
edits.append("§1 新增 1.1 框架 / 1.2 M0-M4 / 1.3 覆盖率标题")

# ---- 3. §2 整体替换 ----
i_s2 = must_find(html, '<h2 id="s2">', "§2 开始")
i_s3 = must_find(html, '<h2 id="s3">', "§3 开始")
assert i_s3 > i_s2
old_s2 = html[i_s2:i_s3]
html = html[:i_s2] + S2_NEW + html[i_s3:]
edits.append("§2 整体替换（旧 %d 字符 → 新 %d 字符）" % (len(old_s2), len(S2_NEW)))

# ---- 4. TOC §2 标题更新 ----
old_toc = '<a href="#s2">§2 文献综述：从前景理论到中国证据</a>'
new_toc = '<a href="#s2">§2 文献综述：三支文献的接力与中国缺口</a>'
if old_toc in html:
    html = html.replace(old_toc, new_toc, 1)
    edits.append("TOC §2 标题更新")

# ---- 5. header meta 版本行 ----
old_meta = "生成日期：2026-08-19 · 由 <code>_gen_summary_report_2026-08-19.py</code> 可复现生成"
new_meta = old_meta + "<br>深度优化版（2026-08-19 晚）：新增 §0 导师导览 · §1.1 框架一览与 §1.2 M0–M4 详解 · §2 完整文献综述重写（叙事型，数值全部对齐 v4 基准）"
if old_meta in html:
    html = html.replace(old_meta, new_meta, 1)
    edits.append("header meta 版本行")

# ---- 6. 校验：标签平衡 ----
def balance(s):
    problems = []
    for tag in ["div", "table", "thead", "tbody", "tr", "td", "th", "h2", "h3", "h4",
                "p", "span", "b", "svg", "ul", "ol", "li", "code", "header", "a", "i", "em", "strong"]:
        o = len(re.findall(r"<%s(\s|>)" % tag, s))
        c = len(re.findall(r"</%s>" % tag, s))
        if o != c:
            problems.append("%s %d/%d" % (tag, o, c))
    return problems

probs = balance(html)
assert not probs, "标签失衡: " + ", ".join(probs)
assert html.count('id="s2"') == 1, "id=s2 不唯一"
for bad in ["五条主线", "从前景理论到中国证据</h2>"]:
    assert bad not in html, "旧 §2 残留: " + bad
# 新增关键内容落位检查
for key in ["给导师的三分钟导览", "M0–M4：五个嵌套模型", "1.1 研究框架一览", "2.1 第一支文献", "张学勇、吴雨玲、陈锐", "四大缺口与本研究的位置", "1.3 数据与变量覆盖率"]:
    assert key in html, "新增内容缺失: " + key

open(TARGET, "w", encoding="utf-8").write(html)
print("OK 全部编辑完成:")
for e in edits:
    print("  -", e)
print("字符数: %d → %d (+%.1f%%)" % (orig_len, len(html), (len(html) / orig_len - 1) * 100))
print("标签平衡: 通过（div/table/tr/p/span/b 等 23 类全部配对）")
print("备份: " + os.path.join(BKDIR, "实证总结报告_文献综述回归解读与SDI诊断_2026-08-19.html"))
