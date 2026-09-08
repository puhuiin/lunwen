# -*- coding: utf-8 -*-
"""构建基金经理能力打分 + 分型可视化（Req1）。
权重 = 各维度对 fut4q 的前向预测系数（forward-validated）；z 标准化后加权求和。
分型 = 基于 z 分数的 4 原型规则（优先级匹配）。
输出：scoring_results.json（数字，供 HTML 叙事）+ scoring_heatmap.svg + scoring_typebar.svg（嵌入）。
"""
import pandas as pd, numpy as np, json, os
base="D:/Desktop/基金经理行为分析研究/"
panel=pd.read_csv(base+"指标计算流水线/output/主分析面板_重建.csv",dtype={"fund_code":str})

# 各维度前向预测系数（来自 forward_scan.py 的真实 t 检验），符号=对业绩的方向
FW={
 "AS_improved":0.090,"ICI":0.030,"TO_two_sided":0.020,"ARG":0.154,
 "return_volatility":0.487,"RG":0.037,"risk_asym":0.642,
 "de":-0.090,"lsv":-0.050,"pgr":-0.019,"plr":0.055,"industry_hhi":-0.063,
}
dim_order=["AS_improved","ICI","TO_two_sided","ARG","return_volatility","RG","risk_asym","de","lsv","pgr","plr","industry_hhi"]
labels={"AS_improved":"主动份额AS","ICI":"行业集中度ICI","TO_two_sided":"换手TO","ARG":"主动收益ARG",
 "return_volatility":"收益波动RV","RG":"主动收益RG","risk_asym":"风险不对称RA","de":"处置效应DE",
 "lsv":"羊群LSV","pgr":"追涨PGR","plr":"杀跌PLR","industry_hhi":"行业HHI"}

# 基金层均值
agg=panel.groupby("fund_code").agg({d:"mean" for d in dim_order}).dropna(how="all")
# z 标准化
Z=agg.copy()
for d in dim_order:
    Z[d]=(agg[d]-agg[d].mean())/agg[d].std()

# 综合得分：可用维度上，权重=前向系数/|系数|和，加权 z 求和
W=pd.Series(FW)
def comp(row):
    avail=[d for d in dim_order if pd.notna(row[d])]
    if not avail: return np.nan
    w=W[avail]; w=w/w.abs().sum()
    return float(sum(w[d]*row[d] for d in avail))
agg["score"]=Z.apply(comp,axis=1)
agg["score"]=(agg["score"]-agg["score"].mean())/agg["score"].std()  # 再标准化便于读

# 分型（基于 z 的规则，优先级匹配）
def classify(r):
    ra=Z.loc[r.name,"risk_asym"] if pd.notna(Z.loc[r.name,"risk_asym"]) else np.nan
    arg=Z.loc[r.name,"ARG"] if pd.notna(Z.loc[r.name,"ARG"]) else np.nan
    de=Z.loc[r.name,"de"] if pd.notna(Z.loc[r.name,"de"]) else np.nan
    ic=Z.loc[r.name,"ICI"] if pd.notna(Z.loc[r.name,"ICI"]) else np.nan
    as_=Z.loc[r.name,"AS_improved"] if pd.notna(Z.loc[r.name,"AS_improved"]) else np.nan
    lsv=Z.loc[r.name,"lsv"] if pd.notna(Z.loc[r.name,"lsv"]) else np.nan
    to=Z.loc[r.name,"TO_two_sided"] if pd.notna(Z.loc[r.name,"TO_two_sided"]) else np.nan
    if pd.notna(ra) and pd.notna(arg) and ra>=0.5 and arg>=0.5 and (pd.isna(de) or de<=0.3):
        return "风控择股型(赢家)"
    if pd.notna(ic) and pd.notna(as_) and ic>=0.5 and as_<=0.3:
        return "行业集中下注型"
    if pd.notna(de) and de<=-0.5 and (pd.isna(lsv) or abs(lsv)<=0.5):
        return "低偏误纪律型"
    if pd.notna(to) and pd.notna(ra) and to>=0.5 and ra<=0:
        return "高换手噪声型(输家)"
    return "均衡型(其他)"
agg["type"]=agg.apply(classify,axis=1)

counts=agg["type"].value_counts().to_dict()
print("=== 分型分布（基金数）===")
for k,v in counts.items(): print(f"  {k}: {v}")
print("\n=== 综合得分 top15 / bottom15 ===")
top=agg.sort_values("score",ascending=False).head(15)
bot=agg.sort_values("score").head(15)
print("TOP:",list(top.index.astype(str)))
print("BOT:",list(bot.index.astype(str)))

# 保存数字
res={"type_counts":counts,
     "n_funds":int(len(agg)),
     "top":[{"fund":str(f),"score":round(agg.loc[f,"score"],3)} for f in top.index],
     "bottom":[{"fund":str(f),"score":round(agg.loc[f,"score"],3)} for f in bot.index],
     "fw":FW}
with open(base+"scoring_results.json","w",encoding="utf-8") as f:
    json.dump(res,f,ensure_ascii=False,indent=2)

# ---------- SVG 热力图（top25 基金 × 8 维，红=有利业绩）----------
heat_dims=["AS_improved","ICI","TO_two_sided","ARG","return_volatility","risk_asym","de","lsv"]
hlab=[labels[d] for d in heat_dims]
top25=agg.sort_values("score",ascending=False).head(25)
W2=pd.Series(FW); wnorm=W2[heat_dims]/W2[heat_dims].abs().sum()
cw,ch,padL,padT=92,22,150,46
Wsvg=padL+cw*len(heat_dims)+20
Hsvg=padT+ch*len(top25)+30
def color(v):  # v 已按权重方向定向（红=好）
    v=max(-3,min(3,v))
    if v>=0:
        g=int(255-90*v); b=int(255-150*v); r=235
        r=min(255,r+20*v)
    else:
        r=int(255+90*v); g=int(255+40*v); b=235
        r=max(0,r); b=min(255,b+10*(-v))
    r=max(0,min(255,r));g=max(0,min(255,g));b=max(0,min(255,b))
    return f"rgb({int(r)},{int(g)},{int(b)})"
svg=[f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {Wsvg} {Hsvg}" font-family="system-ui,Segoe UI,Arial" font-size="11">']
svg.append(f'<rect width="{Wsvg}" height="{Hsvg}" fill="#fff"/>')
svg.append(f'<text x="10" y="24" font-size="13" font-weight="700" fill="#1f2937">基金经理能力热力图（Top25 by 综合得分，红=有利未来业绩，蓝=不利）</text>')
# 列头
for j,d in enumerate(heat_dims):
    x=padL+cw*j+cw/2
    svg.append(f'<text x="{x}" y="{padT-8}" text-anchor="middle" fill="#374151">{hlab[j]}</text>')
# 行
for i,f in enumerate(top25.index):
    y=padT+ch*i
    fc=str(f)
    svg.append(f'<text x="6" y="{y+ch/2+4}" font-size="10" fill="#111827">{fc}</text>')
    svg.append(f'<text x="128" y="{y+ch/2+4}" font-size="10" font-weight="700" fill="#b91c1c">{agg.loc[f,"score"]:+.2f}</text>')
    for j,d in enumerate(heat_dims):
        zv=Z.loc[f,d] if pd.notna(Z.loc[f,d]) else 0
        orient=zv*(1 if FW[d]>0 else -1)  # 定向：红=好
        x=padL+cw*j
        svg.append(f'<rect x="{x}" y="{y+2}" width="{cw-3}" height="{ch-5}" fill="{color(orient)}" stroke="#e5e7eb" stroke-width="0.5"/>')
svg.append('</svg>')
open(base+"scoring_heatmap.svg","w",encoding="utf-8").write("\n".join(svg))

# ---------- 分型分布条形 ----------
tc=counts
maxv=max(tc.values()) if tc else 1
bw=520; bh=30; padT2=46; W2svg=620; H2svg=padT2+bh*len(tc)+20
colors={"风控择股型(赢家)":"#16a34a","行业集中下注型":"#d97706","低偏误纪律型":"#0891b2","高换手噪声型(输家)":"#dc2626","均衡型(其他)":"#6b7280"}
svg2=[f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W2svg} {H2svg}" font-family="system-ui,Segoe UI,Arial" font-size="12">']
svg2.append(f'<rect width="{W2svg}" height="{H2svg}" fill="#fff"/>')
svg2.append(f'<text x="10" y="24" font-size="13" font-weight="700" fill="#1f2937">基金经理分型分布（基于 z 分数规则的 4 原型 + 均衡型）</text>')
for i,(k,v) in enumerate(tc.items()):
    y=padT2+bh*i
    w=bw*v/maxv
    svg2.append(f'<rect x="170" y="{y+4}" width="{w}" height="{bh-10}" fill="{colors.get(k,"#6b7280")}" rx="3"/>')
    svg2.append(f'<text x="166" y="{y+bh/2+4}" text-anchor="end" fill="#374151">{k}</text>')
    svg2.append(f'<text x="{170+w+6}" y="{y+bh/2+4}" fill="#111827">{v}</text>')
svg2.append('</svg>')
open(base+"scoring_typebar.svg","w",encoding="utf-8").write("\n".join(svg2))
print("\nSVG 已写出: scoring_heatmap.svg, scoring_typebar.svg, scoring_results.json")
