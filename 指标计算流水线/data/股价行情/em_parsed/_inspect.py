import re
t = open("raw_q4_010.json", encoding="utf-8").read()
m = re.search(r'炼石航空\(000697\.SZ\)",(.*?)\]\,', t)
seg = m.group(1)
vals = seg.split(",")
print("count in raw:", len(vals))
print(vals[:3], "...", vals[-3:] if len(vals) > 3 else [])