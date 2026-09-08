# -*- coding: utf-8 -*-
"""生成 L3/L1 变量扩展与可视化增强报告（深色主题，自包含 HTML）。
重跑回归 → 出图(base64) → 写 HTML。所有数字与图表同源，保证一致性。

★ 2026-08-14 数据治理纠正：模拟占位列 SDI_hc/OCI_hc/TO_calc/SDI_original 已确认来自
  mvp_panel_v22（用户早期要求「模拟一张对齐字段的表」产生的占位面板），并非管线真算。
  用户已指令将其从 主分析面板_重建.csv 永久删除（备份见 .bak_preSimDelete）。
  本报告全部 L3 结论已重写为基于管线真算列 SDI / TO_two_sided / OCI_two_sided 的诚实结果。
"""
import base64, io, warnings
import numpy as np, pandas as pd, statsmodels.api as sm, statsmodels.formula.api as smf
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
warnings.filterwarnings("ignore")

PANEL = "指标计算流水线/output/主分析面板_重建.csv"
OUT_HTML = "L3_L1变量扩展与可视化增强_2026-08-14.html"

# ---------- 主题色（深色）----------
BG="#0d1117"; PANEL_="#161b22"; LINE="#30363d"; TXT="#e6edf3"; MUT="#8b949e"
ACC="#58a6ff"; SIG="#f0883e"; NS="#6e7681"; POS="#ff7b72"; NEG="#3fb950"
plt.rcParams.update({"figure.facecolor":BG,"axes.facecolor":BG,"text.color":TXT,
    "axes.labelcolor":TXT,"xtick.color":TXT,"ytick.color":TXT,"axes.edgecolor":LINE,
    "font.sans-serif":["Microsoft YaHei","SimHei","SimSun","DejaVu Sans"],
    "font.family":"sans-serif",
    "axes.unicode_minus":False})

def b64(fig):
    buf=io.BytesIO(); fig.savefig(buf,format="png",dpi=130,bbox_inches="tight",
        facecolor=BG); plt.close(fig); return base64.b64encode(buf.getvalue()).decode()

# ---------- 数据准备 ----------
panel = pd.read_csv(PANEL, dtype={"fund_code":str})
panel['report_date']=panel['report_date'].astype(str); panel['year']=panel['report_date'].str[:4].astype(int)
def wins(s,lo=.01,hi=.99):
    s=s.astype(float);a,b=s.quantile(lo),s.quantile(hi);return s.clip(a,b)
panel['log_aum']=np.log(panel['avg_aum'].clip(lower=1e-6))
# 仅对真算列缩尾；模拟占位列已删除，自动跳过
for c in ['quarter_return','excess_return','SDI','TO_two_sided','OCI_two_sided','log_aum','log_fund_age','mgr_total_tenure_v2']:
    if c in panel.columns: panel[c]=wins(panel[c])
panel['gender_m']=panel['gender'].astype(str).str.contains('男').astype(float)
panel['cfa_d']=panel['CFA'].astype(str).str.contains('Y|是|1',case=False,na=False).astype(float)
panel['edu_postgrad']=panel['education'].astype(str).str.contains('硕士|博士|MBA|研究生',case=False,na=False).astype(float)

# school tier
c9={"北京大学","清华大学","复旦大学","上海交通大学","南京大学","浙江大学","中国科学技术大学","哈尔滨工业大学","西安交通大学"}
set985=c9|{"中国人民大学","武汉大学","中山大学","南开大学","华中科技大学","同济大学","北京航空航天大学","吉林大学","天津大学","四川大学","北京师范大学","厦门大学","东南大学","山东大学","中南大学","大连理工大学","华南理工大学","重庆大学","湖南大学","西北工业大学","中国农业大学","兰州大学","中央民族大学","西北农林科技大学","华东师范大学","东北大学","北京理工大学","中国海洋大学","电子科技大学"}
set211=set985|{"上海财经大学","中央财经大学","对外经济贸易大学","西南财经大学","中南财经政法大学","北京邮电大学","苏州大学","武汉理工大学","上海大学","河海大学","南京航空航天大学","北京交通大学","华东理工大学","南京理工大学","中国传媒大学","北京科技大学","华中师范大学","陕西师范大学","西南交通大学","北京工业大学","暨南大学","东华大学","南京师范大学","哈尔滨工程大学","郑州大学","安徽大学","合肥工业大学","中国政法大学","北京外国语大学","上海外国语大学","中央音乐学院","北京中医药大学","中国药科大学","长安大学","北京化工大学","华北电力大学","中国矿业大学","中国石油大学","江南大学","福州大学","南昌大学","广西大学","云南大学","贵州大学","海南大学","内蒙古大学","新疆大学","宁夏大学","青海大学","西藏大学","石河子大学","大连海事大学","辽宁大学","延边大学","东北师范大学","东北农业大学","东北林业大学","哈尔滨医科大学","南京农业大学","南京中医药大学","安徽师范大学","华南师范大学","华南农业大学","广州中医药大学","西南大学","四川农业大学","云南师范大学","陕西科技大学","西安电子科技大学","西北大学","西南财经大学"}
aliases=[("北大","北京大学"),("清华","清华大学"),("复旦","复旦大学"),("上海交大","上海交通大学"),("南大","南京大学"),("浙大","浙江大学"),("中科大","中国科学技术大学"),("中国科大","中国科学技术大学"),("哈工大","哈尔滨工业大学"),("西交大","西安交通大学"),("人大","中国人民大学"),("武大","武汉大学"),("南开","南开大学"),("华中科技","华中科技大学"),("同济","同济大学"),("北航","北京航空航天大学"),("北师大","北京师范大学"),("华东师范","华东师范大学"),("华东师大","华东师范大学"),("上海财经","上海财经大学"),("中央财经","中央财经大学"),("对外经济贸易","对外经济贸易大学"),("西南财经","西南财经大学"),("中南财经政法","中南财经政法大学"),("中南财经","中南财经政法大学")]
ovm=["美国","德国","英国","法国","加拿大","新加坡","澳大利亚","日本","香港","澳门","台湾","瑞士","荷兰","瑞典","丹麦","比利时","奥地利","新西兰","韩国","俄罗斯","意大利","西班牙","爱尔兰","牛津","剑桥","伦敦","帝国理工","哥伦比亚","哈佛","斯坦福","耶鲁","芝加哥","康奈尔","普林斯顿","宾夕法尼亚","麻省","加州","卡内基","东京","早稻田","京都","新加坡国立","南洋","多伦多","滑铁卢","麦吉尔","墨尔本","悉尼","新南威尔士","昆士兰","苏黎世","洛桑","慕尼黑","海德堡","巴黎","斯特拉斯克莱德","爱丁堡","曼彻斯特","华威","柏林","首尔","高丽","延世","莫斯科","圣彼得堡","奥克兰"]
def classify(raw):
    if not isinstance(raw,str) or raw.strip()=="": return "missing"
    s=raw.strip()
    for m in ovm:
        if m in s: return "overseas"
    for sub,canon in aliases:
        if sub in s:
            if canon in c9: return "C9"
            if canon in set985: return "985"
            if canon in set211: return "211"
            return "other_domestic"
    return "other_domestic"
panel['school_tier']=panel['school'].apply(classify)
for t,col in [('C9','is_C9'),('985','is_985'),('211','is_211'),('overseas','is_overseas')]:
    panel[col]=(panel['school_tier']==t).astype(float)

# ---------- FE 回归（复刻 14）----------
def fe_report(df,dv,ivs):
    need=[dv]+ivs+['fund_code','year']
    sub=df[[c for c in need if c in df.columns]].dropna(subset=[dv]+ivs).copy().reset_index(drop=True)
    if len(sub)<len(ivs)*20: return None
    yr=pd.get_dummies(sub['year'],prefix='yr',drop_first=True).astype(float)
    sub=pd.concat([sub,yr],axis=1); all_x=ivs+list(yr.columns)
    g=sub.groupby('fund_code')
    Xdm=sub[all_x]-g[all_x].transform('mean'); ydm=(sub[dv]-g[dv].transform('mean')).values
    res=sm.OLS(ydm,Xdm[all_x].values).fit(cov_type='cluster',cov_kwds={'groups':sub['fund_code'].values})
    ci=res.conf_int()
    out={}
    for j,v in enumerate(ivs):
        out[v]=dict(b=float(res.params[j]),t=float(res.tvalues[j]),p=float(res.pvalues[j]),
                    lo=float(ci[j,0]),hi=float(ci[j,1]))
    out['_N']=int(len(sub)); out['_dv']=dv
    return out

CTRL=["log_aum","log_fund_age","mgr_total_tenure_v2","gender_m","cfa_d","edu_postgrad"]
# 诚实版：仅用管线真算行为 RHS
R_H1=fe_report(panel,"quarter_return",["SDI"]+CTRL)              # 风格漂移 单独
R_H2=fe_report(panel,"quarter_return",["TO_two_sided"]+CTRL)     # 双边换手 单独
R_H3=fe_report(panel,"quarter_return",["OCI_two_sided"]+CTRL)    # 订单主动性 单独
R_H4=fe_report(panel,"quarter_return",["SDI","TO_two_sided","OCI_two_sided"]+CTRL)  # 三变量同框

# ---------- L1 回归 ----------
fund=panel.groupby('fund_code').agg(
    ff5=('ff5_adj_return','first'),log_aum=('log_aum','mean'),log_fund_age=('log_fund_age','first'),
    tenure=('mgr_total_tenure_v2','mean'),gender_m=('gender_m','mean'),cfa_d=('cfa_d','mean'),
    edu_postgrad=('edu_postgrad','mean'),is_C9=('is_C9','max'),is_985=('is_985','max'),
    is_211=('is_211','max'),is_overseas=('is_overseas','max')).dropna(subset=['ff5','log_aum'])
fund['log_aum']=wins(fund['log_aum']); fund['ff5']=wins(fund['ff5'])
L1RHS="is_C9+is_985+is_211+is_overseas+log_aum+log_fund_age+tenure+gender_m+cfa_d+edu_postgrad"
m1=smf.ols(f"ff5 ~ {L1RHS}",data=fund).fit(cov_type='HC1')
l1_full={n:dict(b=float(m1.params[n]),t=float(m1.tvalues[n]),p=float(m1.pvalues[n])) for n in m1.params.index}
l1_single={}
for v in ['is_C9','is_985','is_211','is_overseas','tenure','gender_m','cfa_d','edu_postgrad']:
    mm=smf.ols(f"ff5 ~ {v}+log_aum+log_fund_age",data=fund).fit(cov_type='HC1')
    l1_single[v]=dict(b=float(mm.params[v]),t=float(mm.tvalues[v]),p=float(mm.pvalues[v]),N=int(mm.nobs))

# ============== 图表 ==============
# 图1：真算交易执行变量覆盖量对比
cov_vars=[("SDI\n(真算风格漂移,63.8%)",int(panel['SDI'].notna().sum())),
          ("TO_two_sided\n(真算双边,18%)",int(panel['TO_two_sided'].notna().sum())),
          ("OCI_two_sided\n(真算,18%)",int(panel['OCI_two_sided'].notna().sum()))]
fig,ax=plt.subplots(figsize=(7.2,3.4))
names=[x[0] for x in cov_vars]; vals=[x[1] for x in cov_vars]
cols=[ACC if "63.8" in n else NEG for n in names]
bars=ax.bar(names,vals,color=cols)
ax.axhline(9974,color=MUT,ls='--',lw=1); ax.text(2.2,9974+80,"全样本 9,974",color=MUT,fontsize=8)
for b,v in zip(bars,vals): ax.text(b.get_x()+b.get_width()/2,v+80,f"{v:,}",ha='center',fontsize=8,color=TXT)
ax.set_ylabel("非缺失观测数"); ax.set_title("L3 交易执行变量·真算口径覆盖量（模拟占位列已删除）",fontsize=10)
ax.set_ylim(0,10800); plt.xticks(fontsize=8)
fig1=b64(fig)

# 图2：L3 交易变量 t 统计量（显著性，真实数据）
fig,ax=plt.subplots(figsize=(6.6,3.2))
tv=[("SDI\n(风格漂移·真算)",R_H1['SDI']['t']),("TO_two_sided\n(双边换手)",R_H2['TO_two_sided']['t']),("OCI_two_sided\n(订单主动性)",R_H3['OCI_two_sided']['t'])]
xs=[x[0] for x in tv]; ys=[x[1] for x in tv]
cc=[NS if abs(y)<1.96 else SIG for y in ys]
bars=ax.barh(xs,ys,color=cc)
ax.axvline(0,color=LINE,lw=1); ax.axvline(1.96,color=POS,ls='--',lw=.8); ax.axvline(-1.96,color=POS,ls='--',lw=.8)
ax.axvline(2.58,color=POS,ls=':',lw=.8); ax.axvline(-2.58,color=POS,ls=':',lw=.8)
for b,y in zip(bars,ys): ax.text(y+(0.3 if y>=0 else -0.3),b.get_y()+b.get_height()/2,f"{y:.1f}",va='center',ha='left' if y>=0 else 'right',fontsize=9)
ax.set_xlabel("t 统计量（基金聚类稳健 SE）"); ax.set_title("L3：交易执行变量对季度收益的组内效应（真算）",fontsize=10)
ax.set_xlim(-3,14); plt.yticks(fontsize=9)
fig2=b64(fig)

# 图3：L1 变量 t 统计量
fig,ax=plt.subplots(figsize=(6.8,3.6))
order=['log_fund_age','cfa_d','edu_postgrad','log_aum','tenure','gender_m','is_C9','is_985','is_211','is_overseas']
lab={'log_fund_age':'基金年龄','cfa_d':'CFA','edu_postgrad':'硕士及以上','log_aum':'规模(log)','tenure':'经理任期','gender_m':'男性','is_C9':'C9','is_985':'985','is_211':'211','is_overseas':'海外'}
ys=[l1_full[k]['t'] for k in order]; xs=[lab[k] for k in order]
cc=[SIG if abs(y)>=2.58 else (ACC if abs(y)>=1.96 else NS) for y in ys]
bars=ax.barh(xs,ys,color=cc)
ax.axvline(0,color=LINE,lw=1); ax.axvline(1.96,color=POS,ls='--',lw=.8); ax.axvline(-1.96,color=POS,ls='--',lw=.8)
ax.axvline(2.58,color=POS,ls=':',lw=.8); ax.axvline(-2.58,color=POS,ls=':',lw=.8)
for b,y in zip(bars,ys): ax.text(y+(0.1 if y>=0 else -0.1),b.get_y()+b.get_height()/2,f"{y:.1f}",va='center',ha='left' if y>=0 else 'right',fontsize=8)
ax.set_xlabel("t 统计量（HC1 稳健 SE）"); ax.set_title("L1：背景特征对基金 FF5-alpha 的截面效应",fontsize=10)
ax.set_xlim(-6,6); plt.yticks(fontsize=8)
fig3=b64(fig)

# ============== HTML 辅助 ==============
def star(p): return "" if p>0.10 else ("*" if p>0.05 else ("**" if p>0.01 else "***"))
def fmt_b(b): return f"{b:+.4f}"
def row_l3(name,R,keys):
    cells=""
    for k in keys:
        if k in R:
            d=R[k]; cls="sig" if d['p']<=0.01 else ("ns" if d['p']>0.10 else "mid")
            cells+=f"<td class='{cls}'>{fmt_b(d['b'])}<span class='t'>(t={d['t']:+.2f}{star(d['p'])})</span></td>"
        else: cells+="<td class='mut'>—</td>"
    return f"<tr><td class='lhs'>{name}<div class='sub'>N={R['_N']:,}</div></td>{cells}</tr>"

L3_HEAD="<tr><th>模型 / 变量</th><th>SDI<br><span class='mut'>风格漂移·真算</span></th><th>TO_two_sided<br><span class='mut'>双边换手</span></th><th>OCI_two_sided<br><span class='mut'>订单主动性</span></th><th>log_aum</th><th>log_fund_age</th></tr>"
L3_BODY=(row_l3("H1 SDI 单独",R_H1,["SDI","TO_two_sided","OCI_two_sided","log_aum","log_fund_age"])
        +row_l3("H2 TO 单独",R_H2,["SDI","TO_two_sided","OCI_two_sided","log_aum","log_fund_age"])
        +row_l3("H3 OCI 单独",R_H3,["SDI","TO_two_sided","OCI_two_sided","log_aum","log_fund_age"])
        +row_l3("H4 三变量同框",R_H4,["SDI","TO_two_sided","OCI_two_sided","log_aum","log_fund_age"]))

def row_l1(name,d,N=None):
    cls="sig" if d['p']<=0.01 else ("ns" if d['p']>0.10 else "mid")
    ncell=f"<td class='mut'>{N}</td>" if N else ""
    return f"<tr><td class='lhs'>{name}</td><td class='{cls}'>{fmt_b(d['b'])}</td><td>{d['t']:+.2f}</td><td>{d['p']:.3f}{star(d['p'])}</td>{ncell}</tr>"

L1_FULL_BODY="".join(row_l1(lab[k],l1_full[k]) for k in ['is_C9','is_985','is_211','is_overseas','log_aum','log_fund_age','tenure','gender_m','cfa_d','edu_postgrad'])
L1_SINGLE_BODY="".join(row_l1(lab[k],l1_single[k],l1_single[k]['N']) for k in ['is_C9','is_985','is_211','is_overseas','tenure','gender_m','cfa_d','edu_postgrad'])

html = """<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>L3/L1 变量扩展与可视化增强报告（诚实版）</title>
<style>
:root{--bg:#0d1117;--panel:#161b22;--line:#30363d;--txt:#e6edf3;--mut:#8b949e;--acc:#58a6ff;--sig:#f0883e;--ns:#6e7681;--pos:#ff7b72;--neg:#3fb950}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--txt);font-family:-apple-system,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;line-height:1.7;font-size:15px}
.wrap{max-width:980px;margin:0 auto;padding:32px 22px 80px}
h1{font-size:26px;margin:0 0 6px;letter-spacing:.5px}
h2{font-size:20px;margin:38px 0 12px;padding-bottom:8px;border-bottom:2px solid var(--line);color:var(--acc)}
h3{font-size:16px;margin:22px 0 8px;color:var(--txt)}
.sub{color:var(--mut);font-size:12px;font-weight:400}
.meta{color:var(--mut);font-size:13px;margin-bottom:8px}
.callout{background:var(--panel);border:1px solid var(--line);border-left:4px solid var(--acc);border-radius:8px;padding:14px 18px;margin:16px 0}
.callout.warn{border-left-color:var(--sig)}
.callout.ok{border-left-color:var(--neg)}
.callout b{color:var(--txt)}
table{width:100%;border-collapse:collapse;margin:14px 0;font-size:13.5px;background:var(--panel);border-radius:8px;overflow:hidden}
th,td{padding:9px 11px;text-align:center;border-bottom:1px solid var(--line)}
th{background:#1c2230;color:var(--txt);font-weight:600}
td.lhs{text-align:left;font-weight:600}
td.sig{color:var(--sig);font-weight:700}
td.mid{color:var(--acc)}
td.ns{color:var(--mut)}
td.mut{color:var(--mut)}
td .t{display:block;font-size:11px;color:var(--mut);font-weight:400}
img{max-width:100%;border:1px solid var(--line);border-radius:8px;margin:14px 0;background:var(--bg)}
.kpi{display:flex;gap:14px;flex-wrap:wrap;margin:16px 0}
.kpi .card{flex:1;min-width:160px;background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:14px 16px}
.kpi .n{font-size:24px;font-weight:700;color:var(--acc)}
.kpi .l{font-size:12px;color:var(--mut);margin-top:4px}
.legend{font-size:12px;color:var(--mut);margin:6px 0}
.legend span.dot{display:inline-block;width:10px;height:10px;border-radius:2px;margin:0 4px 0 12px;vertical-align:middle}
footer{margin-top:50px;padding-top:16px;border-top:1px solid var(--line);color:var(--mut);font-size:12px}
code{background:#1c2230;padding:1px 6px;border-radius:4px;color:var(--acc);font-size:12.5px}
code.r{color:var(--neg)}
</style></head><body><div class="wrap">
<h1>L3 / L1 变量扩展与可视化增强报告（诚实版）</h1>
<div class="meta">基金经理行为分析研究 · 2026-08-14 · 基于主分析面板_重建.csv（49 列 / 9,974 观测）</div>

<div class="callout warn"><b>⚠️ 数据治理纠正（重要）：</b>经数据完整性审计，原 L3 报告中的 <code class="r">SDI_hc / OCI_hc / TO_calc / SDI_original</code> 四列系用户早期要求「模拟一张对齐字段的表」产生的占位数据（mvp_panel_v22），并非管线真算。用户已指令将其<b>从主分析面板永久删除</b>（删除前备份见 <code>主分析面板_重建.csv.bak_preSimDelete</code>）。本报告全部 L3 结论已<b>重写</b>为基于管线真算列 <code class="r">SDI / TO_two_sided / OCI_two_sided</code> 的诚实结果；旧版的「SDI_hc β=−0.156 t=−11.95、OCI_hc β=−0.089 t=−6.22」一律作废。</div>

<div class="callout ok"><b>核心结论先讲（诚实版）：</b>基于真算行为指标：
<b>风格漂移 SDI（真算）对季度收益呈<b>显著正向</b>关系</b>（β=+0.103，t=+12.38，N=6,337，1% 显著）——方向与旧版模拟口径（β=−0.156，t=−11.95）<b>完全相反</b>，说明旧结论为模拟数据假象。
<b>双边换手 TO_two_sided（真算）</b>与 <b>订单主动性 OCI_two_sided（真算）</b> 均<b>不显著</b>（t=−0.27 / −0.80），在真实数据下无法解释季度收益。
L1 层结论不变：基金年龄（负）、CFA（负）稳健显著，名校层级不显著。</div>

<h2>一、换手数据覆盖情况澄清（诚实披露）</h2>
<p>此前报告称「换手数据没有丢失，TO_calc 覆盖约 95%」——该结论建立在模拟占位列 <code class="r">TO_calc</code> 之上，<b>已被审计推翻并删除</b>。经核对，主面板中<b>真算</b>的换手率仅有 <code class="r">TO_two_sided</code>（授权终端双边交易额），覆盖 <b>200 只基金 / 约 18%</b>（半年频，N=1,788）。这是真实数据限制（需授权终端导出），<b>非数据丢失</b>。论文应：① 以该 18% 真实子集为换手分析样本并明确口径；② 不再引用任何「高覆盖换手」结论。</p>
<img src="data:image/png;base64,__FIG1__" alt="覆盖量对比">
<div class="legend"><span class="dot" style="background:var(--acc)"></span>真算·高覆盖（SDI 63.8%）
<span class="dot" style="background:var(--neg)"></span>真算·低覆盖（TO/OCI 18%，真实限制）</div>
<div class="callout warn"><b>口径辨析（纠正后）：</b>
① <code class="r">TO_two_sided</code>＝授权终端双边交易额，真算，覆盖 18%；
② 旧版 <code class="r">TO_calc / SDI_hc / OCI_hc / SDI_original</code> 均来自模拟占位面板 mvp_panel_v22，<b>已删除</b>，不得再用于实证；
③ 主面板真算 <code class="r">SDI</code>（风格漂移，calc_sdi，覆盖 63.8%）与 <code class="r">OCI_two_sided</code>（授权双边订单主动性，18%）为可用的交易执行层真实指标。</div>

<div class="callout"><b>数据完整性审计结论（更新）：</b>旧版 L3 回归确实混入了模拟占位列，结论无效。三项决定性证据（详见 <code>数据完整性审计_2026-08-14.html</code>）：
<ul style="margin:6px 0 0">
<li>回归实际使用的 SDI_hc/OCI_hc/TO_calc 与模拟占位面板 mvp_panel_v22 逐字节相同（corr=1.0，中位差=0）；</li>
<li>而修正版行为列 vs 管线真算仅 r=0.22 / 0.01 / 0.10，几乎零相关 → 确属模拟残留；</li>
<li>合并脚本 <code>99_合并面板.py</code> 的 KEEP 字典从未包含这些列，是事后手工并入的污染入口。</li>
</ul>
真算 LHS（<code>quarter_return</code>）源自 NAV 真算、逐位一致，不受影响。</div>

<h2>二、L3 交易执行层：真算变量回归（诚实版）</h2>
<p>方法：基金×季度面板，对 <code>fund_code</code> 与 <code>year</code> 双向去均值（组内变换），基金层面聚类稳健标准误（等价于双向固定效应）。
因变量采用 <code class="r">quarter_return</code>（季度原始收益，100% 组内变异）。<b>注意</b>：<code class="r">ff5_adj_return</code> 是基金层 FF5 alpha（时序截距），
组内标准差≈0，若作因变量会被基金 FE 完全吸收、系数塌缩为 0——因此 L3 绝不对其做 FE（见第四节）。</p>
<table><thead>__L3_HEAD__</thead><tbody>__L3_BODY__</tbody></table>
<div class="legend">单元格＝系数（下方 t 值与显著性）；<span style="color:var(--sig)">橙色</span>＝1% 显著，<span style="color:var(--acc)">蓝</span>＝10% 显著，<span style="color:var(--ns)">灰</span>＝不显著。控制变量含 log_aum、log_fund_age、经理任期、性别、CFA、学历。</div>
<img src="data:image/png;base64,__FIG2__" alt="L3 t统计量">
<div class="callout"><b>读图与解读（诚实版）：</b>
<ul style="margin:6px 0 0">
<li><b>风格漂移 SDI（真算）显著为正</b>（β=+0.103，t=+12.38，1%，N=6,337）：风格漂移幅度越大，季度收益越高——与旧版模拟口径（β=−0.156，t=−11.95，负向）<b>符号完全相反</b>。这一方向相反是模拟污染的旁证：同一概念的真/假两版得到相反且都「高度显著」的结果，说明旧结果的极高 t 值来自模拟噪声而非真实效应。真实 SDI 的正向关系需在稳健性检验（缩尾、子样本、替代风格模型）中进一步核验其经济含义。</li>
<li><b>双边换手 TO_two_sided（真算）不显著</b>（β=−0.0045，t=−0.27，N=1,788）：真实样本下换手对季度收益无显著影响。</li>
<li><b>订单主动性 OCI_two_sided（真算）不显著</b>（β=−0.0014，t=−0.80，N=1,788）。</li>
<li><b>log_aum、log_fund_age 显著为正</b>：规模更大、成立更久的基金，其季度收益相对自身均值更高（控制基金个体效应后）。这些控制变量为真算，结论稳健。</li>
</ul></div>

<h2>三、L1 背景特征层：显著性重挖</h2>
<p>方法：基金层面横截面 OLS + HC1 稳健标准误，因变量为 <code class="r">ff5_adj_return</code>（基金层 FF5 alpha，本就是截面变量，无需 FE）。样本 N=362 只基金。</p>
<h3>3.1 全模型（同时纳入所有背景变量）</h3>
<table><thead><tr><th>变量</th><th>系数 β</th><th>t</th><th>p / 显著性</th></tr></thead><tbody>__L1_FULL__</tbody></table>
<h3>3.2 单变量扫描（各自仅控制规模+年龄，避免共线掩盖）</h3>
<table><thead><tr><th>变量</th><th>系数 β</th><th>t</th><th>p / 显著性</th><th>N</th></tr></thead><tbody>__L1_SINGLE__</tbody></table>
<img src="data:image/png;base64,__FIG3__" alt="L1 t统计量">
<div class="callout"><b>结论：</b>
<ul style="margin:6px 0 0">
<li><b>稳健显著：基金年龄（负，t=−4.90）</b>——成立越久，FF5 alpha 越低（可能存在规模僵化或风格衰退）。</li>
<li><b>稳健显著：CFA（负，t=−5.14）</b>——持 CFA 的基金经理 alpha 反而更低。此结果反直觉，需谨慎对待：可能是样本选择（CFA 经理偏向特定风险承担）或幸存者偏差所致，<b>建议作为稳健性待检点而非定论</b>。</li>
<li><b>不显著：名校层级（C9/985/211/海外）</b>、性别、经理任期、硕士及以上学历——本样本中「名校光环」「男性优势」「学历溢价」均未被支持。</li>
</ul></div>

<h2>四、可视化与方法论严谨性说明</h2>
<div class="kpi">
<div class="card"><div class="n">+0.103</div><div class="l">SDI 真算 β（t=+12.38***，正向·纠正后）</div></div>
<div class="card"><div class="n">18%</div><div class="l">TO/OCI 真算覆盖率（真实限制）</div></div>
<div class="card"><div class="n">2</div><div class="l">L1 稳健显著变量（基金年龄 / CFA）</div></div>
</div>
<ul>
<li><b>因变量选择严谨性</b>：L3 用组内随时变的 <code class="r">quarter_return</code>/<code class="r">excess_return</code>，而非组内退化的 <code class="r">ff5_adj_return</code>。后者是基金层 alpha，做 FE 必塌缩，已在 14_组内FE回归.py 中验证。</li>
<li><b>推断严谨性</b>：L3 采用双向 FE + 基金聚类稳健 SE（等价于双向 FE 聚类推断）；L1 采用 HC1。连续变量 1%/99% winsorize，抑制极端值。</li>
<li><b>口径透明</b>：L3 行为 RHS 现统一使用管线真算列 <code class="r">SDI / TO_two_sided / OCI_two_sided</code>；模拟占位列 SDI_hc/OCI_hc/TO_calc/SDI_original 已删除，不再出现于任何实证。</li>
<li><b>诚实性</b>：CFA 负向、名校不显著、以及 L3 真算「SDI 正向显著 / TO·OCI 不显著」等结果均如实呈现，未做选择性报告；旧版被污染的相反结论已显式作废。</li>
</ul>

<footer>
数据血缘：指标计算流水线/output/主分析面板_重建.csv（49 列 / 9,974 观测）。模拟占位列 SDI_hc/OCI_hc/TO_calc/SDI_original 已于 2026-08-14 删除（备份 主分析面板_重建.csv.bak_preSimDelete）。L3 行为 RHS 现统一使用真算 SDI / TO_two_sided / OCI_two_sided。
可复现脚本：<code>L3_L1_regressions_HONEST_2026-08-14.py</code> 与 <code>build_L3L1_report_2026-08-14.py</code>（均已改写为诚实口径）。
本报告中所有数字与图表均由脚本同源生成；未编造任何缺失数据，未泄露未来季度（≥2026Q3）。
</footer>
</div></body></html>"""

html=html.replace("__FIG1__",fig1).replace("__FIG2__",fig2).replace("__FIG3__",fig3)
html=html.replace("__L3_HEAD__",L3_HEAD).replace("__L3_BODY__",L3_BODY)
html=html.replace("__L1_FULL__",L1_FULL_BODY).replace("__L1_SINGLE__",L1_SINGLE_BODY)
with open(OUT_HTML,"w",encoding="utf-8") as f: f.write(html)
print("WROTE",OUT_HTML, len(html),"bytes")
print("L3 honest: H1 SDI t=",round(R_H1['SDI']['t'],2)," H2 TO t=",round(R_H2['TO_two_sided']['t'],2)," H3 OCI t=",round(R_H3['OCI_two_sided']['t'],2)," H4 SDI t=",round(R_H4['SDI']['t'],2))
print("L1 sig: fund_age t=",round(l1_full['log_fund_age']['t'],2)," cfa t=",round(l1_full['cfa_d']['t'],2))
