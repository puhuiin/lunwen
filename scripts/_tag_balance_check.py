import re, sys
from html.parser import HTMLParser

VOID = {"br","hr","img","input","meta","link","area","base","col","embed","source","track","wbr"}

class Checker(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.errors = []
    def handle_starttag(self, tag, attrs):
        if tag not in VOID:
            self.stack.append((tag, self.getpos()))
    def handle_endtag(self, tag):
        if tag in VOID:
            return
        if not self.stack:
            self.errors.append(f"line {self.getpos()[0]}: closing </{tag}> with empty stack")
            return
        if self.stack[-1][0] == tag:
            self.stack.pop()
        else:
            # search for match (unclosed inner tags)
            names = [t for t, _ in self.stack]
            if tag in names:
                idx = len(names) - 1 - names[::-1].index(tag)
                for t, pos in self.stack[idx+1:]:
                    self.errors.append(f"line {pos[0]}: <{t}> never closed (closed by </{tag}> at line {self.getpos()[0]})")
                del self.stack[idx:]
            else:
                self.errors.append(f"line {self.getpos()[0]}: stray closing </{tag}> (top of stack: <{self.stack[-1][0]}> from line {self.stack[-1][1][0]})")

files = [
    r"d:\Desktop\基金经理行为分析研究\指标总表_五层框架.html",
    r"d:\Desktop\基金经理行为分析研究\reports\基金经理能力画像与业绩评价.html",
    r"d:\Desktop\基金经理行为分析研究\reports\修改说明与自评_2026-08-25.html",
]
ok = True
for f in files:
    src = open(f, encoding="utf-8").read()
    # strip svg blocks (self-contained, xml-style tags confuse html parser minimally but fine to keep)
    c = Checker()
    c.feed(src)
    for t, pos in c.stack:
        c.errors.append(f"line {pos[0]}: <{t}> left unclosed at EOF")
    print(f"=== {f.split(chr(92))[-1]} ===")
    if c.errors:
        ok = False
        for e in c.errors[:30]:
            print("  ERR:", e)
        print(f"  total errors: {len(c.errors)}")
    else:
        print("  TAG BALANCE OK")
sys.exit(0 if ok else 1)
