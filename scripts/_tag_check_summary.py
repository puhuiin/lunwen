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
            names = [t for t, _ in self.stack]
            if tag in names:
                idx = len(names) - 1 - names[::-1].index(tag)
                for t, pos in self.stack[idx+1:]:
                    self.errors.append(f"line {pos[0]}: <{t}> never closed (closed by </{tag}> at line {self.getpos()[0]})")
                del self.stack[idx:]
            else:
                self.errors.append(f"line {self.getpos()[0]}: stray closing </{tag}>")

f = r"d:\Desktop\基金经理行为分析研究\reports\修改说明与自评_2026-08-25.html"
src = open(f, encoding="utf-8").read()
c = Checker()
c.feed(src)
for t, pos in c.stack:
    c.errors.append(f"line {pos[0]}: <{t}> unclosed at EOF")
print("TAG BALANCE OK" if not c.errors else "\n".join(c.errors[:30]))
sys.exit(0 if not c.errors else 1)
