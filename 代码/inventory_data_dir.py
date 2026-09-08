import os, sys

DATA = r"D:\Desktop\基金经理行为分析研究\数据"

def hsize(n):
    for u in ("B","KB","MB","GB","TB"):
        if n < 1024: return f"{n:.1f}{u}"
        n /= 1024
    return f"{n:.1f}PB"

print("="*78)
print("数据\\ 全量盘点（按子目录）")
print("="*78)
total_files = 0
total_bytes = 0
for root, dirs, files in os.walk(DATA):
    if not files: continue
    rel = os.path.relpath(root, DATA)
    sz = sum(os.path.getsize(os.path.join(root,f)) for f in files)
    total_files += len(files); total_bytes += sz
    print(f"\n[{rel}]  文件数={len(files)}  总大小={hsize(sz)}")
    # 列出（大目录只列前若干+统计）
    if len(files) > 25:
        for f in sorted(files)[:8]:
            p=os.path.join(root,f); print(f"    {hsize(os.path.getsize(p)):>8}  {f}")
        print(f"    ... 其余 {len(files)-8} 个")
    else:
        for f in sorted(files):
            p=os.path.join(root,f); print(f"    {hsize(os.path.getsize(p)):>8}  {f}")

print("\n"+"="*78)
print(f"合计：{total_files} 个文件，{hsize(total_bytes)}")
