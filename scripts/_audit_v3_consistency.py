# -*- coding: utf-8 -*-
"""
v3 一致性深度审计脚本 (2026-08-16)
扫描项目内所有「报告级」交付物 (.html/.md)，排除原始数据与流水线目录，
捕获四类风险：
  A. 未来日期泄漏 (>=2026Q3)            -- 硬性红线
  B. 残留 v20 陈旧实证token (危险值)     -- 须刷新
  C. 编造/占位/模拟数据引用             -- 须隔离/披露
  D. 样本量/N/基金数跨文档不一致        -- 须对齐 v3
已刷新文件 (merged_manuscript.html, 5层架构) 内若含陈旧token，多为诚实引用(更正框)，
脚本会标记文件是否含 "v3" 更正标记，便于人工区分「诚实引用」vs「活陈旧主张」。
"""
import os, re, json

ROOT = r"D:/Desktop/基金经理行为分析研究"
EXCLUDE_DIRS = {"数据", "参考文献", "代码", "__pycache__", "模拟数据隔离区",
                ".workbuddy", "指标计算流水线"}
# 已刷新/已知覆盖文件：仅作信息性统计，不计入「活泄漏」严重级
COVERED = {"merged_manuscript.html", "5层架构完整研究方案.html",
           "5层架构完整研究方案.bak_v20_20260816.html"}

# ---- A. 未来日期 ----
future_patterns = [
    (r'2026[Qq][34]', '2026Q3/4'),
    (r'2026-0[9]', '2026-09'),
    (r'2026-1[0-2]', '2026-10/11/12'),
    (r'2027', '2027+'),
    (r'2028', '2028+'),
    (r'2026年(第三|第四|三|四)季度', '2026 Q3/4(中)'),
]

# ---- B. 危险陈旧token (暗示活 v20 错误值) ----
v20_danger = [
    (r'δ\s*=\s*41\.?84', 'Oster δ=41.84'),
    (r'94\.4%', '94.4%'),
    (r'34\.9%', '34.9%'),
    (r'64\.8%', '64.8%'),
    (r'0?\.0728', 'ΔR²=0.0728(伪)'),
    (r'TO_calc', 'TO_calc'),
    (r'F\s*>\s*240', 'F>240'),
    (r'F\s*=\s*240', 'F=240'),
    (r'全显著', '全显著'),
    (r'十项全|十项达标|十项', '十项'),
    (r'七项', '七项'),
    (r'100%显著|100%.*显著', '100%显著'),
    (r'规范曲线.{0,6}100%|100%.{0,6}规范', '规范曲线100%'),
    (r'9,?581', '9581观测(v20)'),
    (r'222 ?(名|个)?基金经理|222 ?经理', '222经理(v20)'),
]
# 方法名级(v20也可能正确引用，仅信息性)
v20_method = [
    (r'Oster', 'Oster(方法)'),
    (r'WCB', 'WCB(方法)'),
    (r'2SLS', '2SLS(方法)'),
    (r'Heckman', 'Heckman(方法)'),
    (r'IV ', 'IV(方法)'),
]

# ---- C. 编造/占位/模拟 ----
fab_patterns = [
    (r'模拟', '模拟'),
    (r'simulated', 'simulated'),
    (r'placeholder', 'placeholder'),
    (r'SDI_hc', 'SDI_hc'),
    (r'OCI_hc', 'OCI_hc'),
    (r'TO_calc', 'TO_calc(占位)'),
    (r'占位', '占位'),
]

# ---- D. 样本量 ----
sample_patterns = [
    (r'9,?974', '9974观测(主面板)'),
    (r'2,?264', '2264(M4 v3)'),
    (r'348 ?(只|个)?基金', '348基金(M4 v3)'),
    (r'400 ?(只|个)?基金', '400基金(主面板)'),
    (r'358 ?(只|个)?基金', '358基金(截面)'),
    (r'R\^?2\s*=\s*0?\.129', 'R²=0.129(M4)'),
    (r'R\^?2\s*=\s*0?\.1308', 'R²=0.1308'),
]

def read_text(p):
    for enc in ("utf-8", "gbk", "utf-8-sig"):
        try:
            with open(p, "r", encoding=enc, errors="strict") as f:
                return f.read()
        except Exception:
            continue
    try:
        with open(p, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except Exception:
        return ""

def scan_group(text, patterns):
    """返回 {label: [(lineno, snippet)]}"""
    res = {}
    lines = text.split("\n")
    for pat, label in patterns:
        try:
            rx = re.compile(pat)
        except re.error:
            continue
        hits = []
        for i, ln in enumerate(lines, 1):
            if rx.search(ln):
                snip = ln.strip()[:160]
                hits.append((i, snip))
        if hits:
            res[label] = hits
    return res

def main():
    report = {}
    for dirpath, dirnames, filenames in os.walk(ROOT):
        # 剪枝
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
        for fn in filenames:
            if not (fn.lower().endswith(".html") or fn.lower().endswith(".md")):
                continue
            if fn.lower().endswith(".bak") or fn.endswith(".bak_v20_20260816.html"):
                continue
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, ROOT)
            text = read_text(full)
            if not text:
                continue
            has_v3 = ("v3 更正" in text) or ("v3 诚实" in text) or ("v3诚实" in text)
            fut = scan_group(text, future_patterns)
            vd = scan_group(text, v20_danger)
            vm = scan_group(text, v20_method)
            fab = scan_group(text, fab_patterns)
            samp = scan_group(text, sample_patterns)
            # 仅当任一风险类有命中才记录
            if fut or vd or fab or samp:
                report[rel] = {
                    "covered": fn in COVERED,
                    "has_v3_marker": has_v3,
                    "future": {k: v[:3] for k, v in fut.items()},
                    "v20_danger": {k: v[:3] for k, v in vd.items()},
                    "v20_method": {k: len(v) for k, v in vm.items()},
                    "fabrication": {k: v[:3] for k, v in fab.items()},
                    "sample": {k: len(v) for k, v in samp.items()},
                }
    # 输出
    out_json = os.path.join(ROOT, "_audit_v3_report.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    # 文本摘要
    lines_out = []
    lines_out.append("="*70)
    lines_out.append("v3 一致性深度审计报告  %d 个文件命中" % len(report))
    lines_out.append("="*70)
    for rel, d in sorted(report.items()):
        tag = []
        if d["covered"]:
            tag.append("已覆盖")
        if d["has_v3_marker"]:
            tag.append("含v3更正")
        lines_out.append("\n### %s   [%s]" % (rel, "/".join(tag) if tag else "未标记"))
        if d["future"]:
            lines_out.append("  [A 未来日期] " + ", ".join("%s×%d" % (k, len(v)) for k, v in d["future"].items()))
            for k, v in d["future"].items():
                for ln, sn in v:
                    lines_out.append("      L%d %s" % (ln, sn))
        if d["v20_danger"]:
            lines_out.append("  [B 危险陈旧] " + ", ".join("%s×%d" % (k, len(v)) for k, v in d["v20_danger"].items()))
            for k, v in d["v20_danger"].items():
                for ln, sn in v:
                    lines_out.append("      L%d %s" % (ln, sn))
        if d["fabrication"]:
            lines_out.append("  [C 编造/占位] " + ", ".join("%s×%d" % (k, len(v)) for k, v in d["fabrication"].items()))
            for k, v in d["fabrication"].items():
                for ln, sn in v:
                    lines_out.append("      L%d %s" % (ln, sn))
        if d["sample"]:
            lines_out.append("  [D 样本量] " + ", ".join("%s×%d" % (k, v) for k, v in d["sample"].items()))
        if d["v20_method"]:
            lines_out.append("  [方法名] " + ", ".join("%s×%d" % (k, v) for k, v in d["v20_method"].items()))
    txt = "\n".join(lines_out)
    out_txt = os.path.join(ROOT, "_audit_v3_report.txt")
    with open(out_txt, "w", encoding="utf-8") as f:
        f.write(txt)
    print(txt)
    print("\n[written] %s\n[written] %s" % (out_json, out_txt))

if __name__ == "__main__":
    main()
