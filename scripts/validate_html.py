"""自定义 HTML 结构校验器：VOID 标签集 + 栈式匹配，检测未闭合/错配标签。"""
from html.parser import HTMLParser
import sys

VOID = {"area","base","br","col","embed","hr","img","input","link",
        "meta","param","source","track","wbr"}

class Checker(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.errors = []

    def handle_starttag(self, tag, attrs):
        if tag in VOID:
            return
        self.stack.append((tag, self.getpos()))

    def handle_endtag(self, tag):
        if tag in VOID:
            return
        if not self.stack:
            self.errors.append(f"多余闭合 </{tag}> @ {self.getpos()}")
            return
        top_tag, top_pos = self.stack[-1]
        if top_tag == tag:
            self.stack.pop()
        else:
            # 尝试在栈中向上查找匹配（容错），否则报错
            for i in range(len(self.stack)-1, -1, -1):
                if self.stack[i][0] == tag:
                    unclosed = [t for t,_ in self.stack[i+1:]]
                    self.errors.append(
                        f"</{tag}> @ {self.getpos()} 错配：中间未闭合 {unclosed} "
                        f"（起始 {self.stack[i][1]}）")
                    del self.stack[i:]
                    break
            else:
                self.errors.append(f"未找到匹配开标签的 </{tag}> @ {self.getpos()}")

def validate(path):
    with open(path, encoding="utf-8") as f:
        html = f.read()
    c = Checker()
    c.feed(html)
    # 闭合后剩余未闭合标签
    for tag, pos in c.stack:
        c.errors.append(f"未闭合 <{tag}> 起始 @ {pos}")
    return c.errors, len(html)

if __name__ == "__main__":
    files = [
        "基金经理能力画像与业绩评价.html",
        "实证结果完整报告与论文写作指南.html",
    ]
    base = "D:/Desktop/基金经理行为分析研究/"
    all_ok = True
    for fn in files:
        p = base + fn
        errs, size = validate(p)
        print(f"\n=== {fn} (size={size}) ===")
        if not errs:
            print("  OK: 结构完整，无未闭合/错配标签")
        else:
            all_ok = False
            print(f"  ERRORS ({len(errs)}):")
            for e in errs[:50]:
                print("   -", e)
    print("\nRESULT:", "ALL_OK" if all_ok else "HAS_ERRORS")
    sys.exit(0 if all_ok else 1)
