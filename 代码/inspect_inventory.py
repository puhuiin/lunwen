import pandas as pd, os, glob, sys

DATA = r"D:\Desktop\基金经理行为分析研究\数据"

def try_read(path, **kw):
    for enc in ("utf-8-sig", "utf-8", "gbk"):
        try:
            return pd.read_csv(path, encoding=enc, **kw)
        except (UnicodeDecodeError, LookupError):
            continue
    return pd.read_csv(path, **kw)

print("="*70)
print("1) fund_holdings_full_v2.csv  (DE 修复所需全持仓)")
print("="*70)
hp = os.path.join(DATA, "L2_持仓偏离层", "基金持仓明细_全量修正版.csv")
h = try_read(hp, nrows=0, low_memory=False)
print("columns:", list(h.columns))
# 全量读取以统计规模（40MB 可控）
df = try_read(hp, low_memory=False)
print("shape:", df.shape)
# 推断关键列名
cols = list(df.columns)
def find(sub, cands):
    for c in cands:
        if sub in c: return c
    return None
fund_col = find("基金", cols) or find("code", [c.lower() for c in cols]) or cols[0]
# 用更稳妥的方式：找含 代码/基金/stock 的列
for kw in ["基金代码","代码","fund","code"]:
    fc = [c for c in cols if kw.lower() in c.lower()]
    if fc:
        fund_col = fc[0]; break
period_col = None
for kw in ["报告期","日期","period","date","report"]:
    pc = [c for c in cols if kw.lower() in c.lower()]
    if pc:
        period_col = pc[0]; break
stock_col = None
for kw in ["股票代码","股票","stock","secu"]:
    sc = [c for c in cols if kw.lower() in c.lower()]
    if sc:
        stock_col = sc[0]; break
print("inferred -> fund:", fund_col, "| period:", period_col, "| stock:", stock_col)
print("nunique funds:", df[fund_col].nunique())
print("nunique periods:", df[period_col].nunique() if period_col else "N/A")
if period_col and stock_col:
    gp = df.groupby([fund_col, period_col])[stock_col].nunique()
    print("stocks-per-fund-period: min/median/max =", int(gp.min()), int(gp.median()), int(gp.max()))
    print("-> 若 median 远大于10，说明是全持仓(非前十大)")

print("\n"+"="*70)
print("2) l5_de_v22.csv  (当前 DE 指标)")
print("="*70)
dp = os.path.join(DATA, "L5_认知行为层", "处置效应DE指标_修正版.csv")
de = try_read(dp, nrows=10, low_memory=False)
print("columns:", list(de.columns))
de_full = try_read(dp, low_memory=False)
print("rows:", len(de_full))
# 找 PGR/PLR 类列
pgr_cols = [c for c in de_full.columns if any(k in c.lower() for k in ["pgr","plr","gain","loss","de","disp","prop"])]
print("PGR/PLR候选列:", pgr_cols)
for c in pgr_cols[:6]:
    print(f"  {c}: mean={de_full[c].mean():.3f}  min={de_full[c].min():.3f}  max={de_full[c].max():.3f}")

print("\n"+"="*70)
print("3) 主分析面板_重建.csv  (真实主面板 header)")
print("="*70)
# 〔2026-08-14 治理〕主分析面板_修正版.csv（模拟占位）已删除，改读真实重建面板。
pp = os.path.join("..", "指标计算流水线", "output", "主分析面板_重建.csv")
ph = try_read(pp, nrows=0, low_memory=False)
allcols = list(ph.columns)
rel = [c for c in allcols if any(k in c.lower() for k in ["de","dispo","l5","lsv","risk","asym","herd","pgr","plr"])]
print("total cols:", len(allcols))
print("DE/L5相关列:", rel)

print("\n"+"="*70)
print("4) FF因子目录")
print("="*70)
ff = glob.glob(os.path.join(DATA, "FF因子_GitHub_*", "*.csv"))
print("FF csv 文件数:", len(ff))
for f in sorted(ff)[:5]:
    print("  ", os.path.basename(f))
