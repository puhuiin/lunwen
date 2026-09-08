import os
DATA = r"D:\Desktop\基金经理行为分析研究\数据"
files = [f for f in os.listdir(DATA) if os.path.isfile(os.path.join(DATA,f))]
files.sort()
def h(n):
    for u in ("B","KB","MB","GB"):
        if n<1024: return f"{n:.0f}{u}"
        n/=1024
    return f"{n:.1f}TB"
print(f"数据\\ 根目录文件数={len(files)}")
for f in files:
    print(f"{h(os.path.getsize(os.path.join(DATA,f))):>8}  {f}")
