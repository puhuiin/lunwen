import warnings, numpy as np, pandas as pd
from statsmodels.stats.outliers_influence import variance_inflation_factor as vf
warnings.filterwarnings("ignore")
df = pd.read_csv(r"指标计算流水线/output/主分析面板_重建_含TOwind.csv")
L5=["de","lsv","risk_asym"]
df["log_aum"]=np.log(df["avg_aum"].clip(lower=1e-9))
df["ff5_adj_return"]=pd.to_numeric(df["ff5_adj_return"],errors="coerce")
ALL=["log_aum","ff5_MKT_excess","ff5_SMB","ff5_HML","ff5_RMW","ff5_CMA","log_fund_age","mgr_total_tenure_v2","AS_improved","ICI","industry_hhi","SDI","TO_wind","ARG","return_volatility"]+L5
def rep(tag, dd):
    X=dd[L5].copy(); X.insert(0,"const",1.0)
    v={L5[i-1]:round(vf(X.values,i),3) for i in range(1,4)}
    c=dd[L5].corr(); od=[round(c.iloc[0,1],4),round(c.iloc[0,2],4),round(c.iloc[1,2],4)]
    print(f"{tag:<26} N={len(dd):>5} VIFmax={max(v.values()):.3f} {v}  max|r|={max(abs(x) for x in od):.4f}  pairs(de-lsv,de-ra,lsv-ra)={od}")
rep("未缩尾/L5可用", df.dropna(subset=L5))
rep("未缩尾/M4样本", df.dropna(subset=ALL+["ff5_adj_return"]))
d=df.dropna(subset=L5).copy()
for v in L5:
    lo,hi=d[v].quantile(0.01),d[v].quantile(0.99); d[v]=d[v].clip(lo,hi)
rep("子样本内缩尾/L5可用", d)
print()
print("--- 覆盖率复核（全面板 9974）---")
for v in L5:
    s=df[v].notna(); print(f"  {v:<12} 非缺失={s.sum():>5} 覆盖率={s.mean()*100:.1f}% 基金数={df.loc[s,'fund_code'].nunique():>4} 均值={df.loc[s,v].mean():.4f} 标准差={df.loc[s,v].std():.4f}")
b=df[L5].notna().all(axis=1)
print(f"  三指标同时可用={b.sum()} 占比={b.mean()*100:.1f}% 基金数={df.loc[b,'fund_code'].nunique()}")
print(f"  总观测={len(df)} 总基金={df['fund_code'].nunique()}")
