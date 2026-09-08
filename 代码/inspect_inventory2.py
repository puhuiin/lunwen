import pandas as pd, os, glob

DATA = r"D:\Desktop\基金经理行为分析研究\数据"

def try_read(path, **kw):
    for enc in ("utf-8-sig", "utf-8", "gbk"):
        try:
            return pd.read_csv(path, encoding=enc, **kw)
        except (UnicodeDecodeError, LookupError):
            continue
    return pd.read_csv(path, **kw)

print("="*70)
print("A) fund_holdings_full_v2 : report_date 分布 (是否混入3/9月季报)")
print("="*70)
df = try_read(os.path.join(DATA, "L2_持仓偏离层", "基金持仓明细_全量修正版.csv"), low_memory=False)
rd = df["report_date"].astype(str)
# 提取月
month = rd.str[5:7]
print("各月份期数 (MM):")
print(month.value_counts().sort_index().to_dict())
# 半年报/年报 vs 季报
full_mask = month.isin(["06","12"])
q_mask = month.isin(["03","09"])
print("06/12(全持仓) 行数:", int(full_mask.sum()), " 03/09(季报前十大) 行数:", int(q_mask.sum()))
print("唯一 report_date 样例:", sorted(rd.unique())[:8], "... 共", rd.nunique())

print("\n"+"="*70)
print("B) l5_de_v22 : report_date 是否只含06/12")
print("="*70)
de = try_read(os.path.join(DATA, "L5_认知行为层", "处置效应DE指标_修正版.csv"), low_memory=False)
drd = de["report_date"].astype(str)
print("l5_de report_date 月份分布:", drd.str[5:7].value_counts().sort_index().to_dict())
print("l5_de 行数:", len(de), " 唯一基金数:", de["fund_code"].nunique())

print("\n"+"="*70)
print("C) 面板 de/pgr/plr 是否与修正版一致")
print("="*70)
# 〔2026-08-14 治理〕主分析面板_修正版.csv（模拟占位）已删除，改读真实 DE 修正版做对照。
_de_path = os.path.join(DATA, "L5_认知行为层", "处置效应DE指标_修正版.csv")
if os.path.exists(_de_path):
    pan = try_read(_de_path, usecols=["fund_code","de","pgr","plr"], low_memory=False)
    print("面板行数:", len(pan))
    print(pan[["de","pgr","plr"]].describe().loc[["mean","min","max"]])
else:
    print("（跳过）真实 DE 文件不存在")

print("\n"+"="*70)
print("D) 定位 FF 因子文件")
print("="*70)
# 列出 数据\ 下所有含 FF 的路径
hits = []
for root, _, files in os.walk(DATA):
    for f in files:
        if "ff" in f.lower() or "因子" in f or "factor" in f.lower():
            hits.append(os.path.join(root, f))
print("含 FF/因子/factor 的文件数:", len(hits))
for h in sorted(hits)[:15]:
    print("  ", os.path.relpath(h, DATA))
# 单独看 数据\ 子目录
print("\n数据\\ 一级子目录:")
for d in sorted(os.listdir(DATA)):
    p = os.path.join(DATA, d)
    if os.path.isdir(p):
        print("  ", d, "->", len(os.listdir(p)), "项")
