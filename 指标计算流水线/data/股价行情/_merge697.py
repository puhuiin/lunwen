import sys
base = r"em_parsed\q4_b010.csv"
fix = r"em_parsed\_q4_697_fix.csv"
out = r"em_parsed\q4_b010.csv"
cb = set()
rows = []
for line in open(base, encoding="utf-8"):
    line = line.rstrip("\n")
    if not line:
        continue
    code = line.split(",")[0]
    if code == "000697":
        continue
    rows.append(line)
    cb.add(code)
cnt = 0
for line in open(fix, encoding="utf-8"):
    line = line.rstrip("\n")
    if not line:
        continue
    rows.append(line)
    cnt += 1
rows.sort()
open(out, "w", encoding="utf-8").write("\n".join(rows) + "\n")
print("removed old 000697, added", cnt, "rows; codes:", len(cb))