import re
import sys

sys.stdout.reconfigure(encoding="utf-8")

txt = open("merged_manuscript.html", encoding="utf-8").read()

# 提取所有表格（含 caption）
tables = []
for m in re.finditer(r"<table[^>]*>(.*?)</table>", txt, re.S):
    body = m.group(1)
    cap = re.search(r"<caption>\s*(表\d+-\d+)", body)
    label = cap.group(1) if cap else "(无编号)"
    tables.append((label, body))

def strip(s):
    s = re.sub(r"<[^>]+>", "", s)
    return s.replace("&gt;", ">").replace("&lt;", "<").replace("&amp;", "&").strip()

def cells(row_html):
    return [strip(c) for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row_html, re.S)]

def to_num(s):
    s = s.replace(",", "").replace("−", "-")
    m = re.search(r"-?\d+(?:\.\d+)?%?", s)
    if not m:
        return None
    v = m.group(0)
    if v.endswith("%"):
        try:
            return float(v[:-1]), True
        except ValueError:
            return None
    try:
        return float(v), False
    except ValueError:
        return None

print(f"共 {len(tables)} 张表")

# ---------- 校验 1: 表4-12 增量R²三模式（下界<=基线<=上界; 排序） ----------
print("\n=== 表4-12 三模式单调性 ===")
for label, body in tables:
    if label != "表4-12":
        continue
    rows = re.findall(r"<tr[^>]*>(.*?)</tr>", body, re.S)
    for r in rows:
        cs = cells(r)
        if len(cs) >= 5 and cs[0].startswith(("L1", "L2", "L3+L4", "L5")):
            nums = []
            for c in cs[1:4]:
                p = to_num(c)
                nums.append(p[0] if p else None)
            if all(n is not None for n in nums):
                seq, lo, hi = nums   # 列序: 逐层(基准) 最后加入(下界) 单独加入(上界)
                ok = lo <= seq <= hi + 1e-9
                print(f"  {cs[0]:<6} last-in={lo} seq={seq} alone={hi} -> {'OK' if ok else '!!违反下<=中<=上'}")

# ---------- 校验 2: 表4-32 规范曲线行内加总 ----------
print("\n=== 表4-32 计数加总 (截面+组内+日频=总数) ===")
for label, body in tables:
    if label != "表4-32":
        continue
    rows = re.findall(r"<tr[^>]*>(.*?)</tr>", body, re.S)
    for r in rows:
        cs = cells(r)
        if not cs:
            continue
        joined = "|".join(cs)
        m = re.search(r"(\d+)/36\|?(\d+)/16\|?(\d+)/8\|?(\d+)/60", joined)
        if not m:
            m2 = re.search(r"(\d+)/36.*?(\d+)/16.*?(\d+)/8.*?(\d+)/60", joined)
            if m2 and cs[0] in ("RiskAsym", "risk_asym", "LSV", "lsv", "DE", "de"):
                m = m2
        if m:
            a, b, c, tot = map(int, m.groups())
            ok = a + b + c == tot
            print(f"  {cs[0]}: {a}+{b}+{c}={a+b+c} vs {tot} {'OK' if ok else '!!加总不符'}")

# ---------- 校验 3: 全文 Q5-Q1 / 差值一致性（样本外 1.28 = 1.96 - 0.48 等） ----------
print("\n=== 样本内外 PS 分位差值 ===")
checks = [
    ("样本内", "1.96", "0.48", "1.48"),
    ("样本外", None, None, "1.28"),
]
txt_plain = re.sub(r"<[^>]+>", "", txt)
m = re.findall(r"Q5(?:季度alpha|收益)[为约]?\s*([\d.]+)%.*?Q1[为约]?\s*([\d.]+)%.*?差距\s*([\d.]+)%", txt_plain)
seen = set()
for a, b, d in m:
    calc = round(float(a) - float(b), 2)
    ok = abs(calc - float(d)) < 0.005
    key = (a, b, d)
    if key in seen:
        continue
    seen.add(key)
    print(f"  Q5={a}% Q1={b}% 差={d}% 计算={calc} {'OK' if ok else '!!不符'}")

# ---------- 校验 4: 占比类数字抽查（覆盖率） ----------
print("\n=== 覆盖率数值自检 ===")
cov = [
    ("DE 观测层", 4650, 9974, "46.6"),
    ("TO_wind 覆盖", None, None, "86.6"),
    ("RiskAsym 覆盖", None, None, "72.0"),
]
r = 4650 / 9974 * 100
print(f"  DE: 4650/9974 = {r:.2f}% (文中 46.6%) {'OK' if abs(r - 46.62) < 0.05 else '!!'}")
