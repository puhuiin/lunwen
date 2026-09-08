# -*- coding: utf-8 -*-
"""内联辅助: 从MCP输出临时文件直接解析生成CSV, 避免手动复制长文本
用法: python _em_go.py <mcp_output_txt> <out_csv> <codes_csv_line>
mcp_output_txt 形如 "The MCP server responded with: [...原始text...]"
"""
import sys, re, os
import _em_parse as P

def main():
    src, out_csv, codes_line = sys.argv[1], sys.argv[2], sys.argv[3]
    with open(src, encoding="utf-8") as f:
        txt = f.read()
    # 去掉 "The MCP server responded with: " 前缀
    m = re.search(r'responded with:\s*(.*)', txt, re.S)
    body = m.group(1).strip() if m else txt.strip()
    expect = codes_line.split(",")
    rows, missing, err = P.parse(body, expect)
    if err:
        print(f"错误: {err}")
        sys.exit(2)
    with open(out_csv, "w", encoding="utf-8", newline="") as f:
        f.write("\n".join(rows) + ("\n" if rows else ""))
    print(f"写出 {out_csv}: {len(rows)} 行, 覆盖 {len(expect)-len(missing)}/{len(expect)}")
    if missing:
        miss_path = out_csv.replace(".csv", "_missing.txt")
        with open(miss_path, "w", encoding="utf-8") as f:
            f.write("\n".join(missing))
        print(f"缺失: {missing} -> {miss_path}")
    return 0

if __name__ == "__main__":
    sys.exit(main())