# -*- coding: utf-8 -*-
"""
L3 (交易执行层) 与 L1 (背景特征层) 回归重算 — 2026-08-14 (修正版)
关键修正：
  - L3 的 DV 必须是基金内随时变的业绩指标。ff5_adj_return 是基金层 FF5 alpha
    （组内 std≈0），做 fund FE 会被完全吸收 → 系数塌缩为 0（已验证，见 14_组内FE回归.py）。
    故 L3 主 DV 采用 quarter_return（季度原始收益），备选 excess_return，二者均 100% 组内变异。
  - FE 方法复刻 14_组内FE回归.py：对 fund_code + year 双向去均值，基金层面聚类稳健标准误
    （等价于双向 FE 的聚类推断）。
  - L1 用 ff5_adj_return（基金层 alpha）做横截面 OLS + HC1，本就是正确口径。

目的（2026-08-14 纠正后，模拟占位列 SDI_hc/OCI_hc/TO_calc/SDI_original 已删除）：
  1. 换手覆盖澄清：真实换手仅 TO_two_sided（授权双边，18%/200只）；旧称"高覆盖 TO_calc"
     系模拟占位面板 mvp_panel_v22 的产物，已删除，不再使用。
  2. L3 诚实回归：统一使用管线真算行为 RHS —— SDI(风格漂移)、TO_two_sided(双边换手)、
     OCI_two_sided(订单主动性)。模拟占位列 SDI_hc/OCI_hc/TO_calc 一律作废。
  3. L1 显著性扫描：背景特征中真正显著的变量（不变）。
"""
import pandas as pd, numpy as np, statsmodels.api as sm, statsmodels.formula.api as smf, warnings
warnings.filterwarnings('ignore')

PANEL = "指标计算流水线/output/主分析面板_重建.csv"
panel = pd.read_csv(PANEL, dtype={"fund_code": str})
panel['report_date'] = panel['report_date'].astype(str)
panel['year'] = panel['report_date'].str[:4].astype(int)

def wins(s, lo=0.01, hi=0.99):
    s = s.astype(float); a, b = s.quantile(lo), s.quantile(hi); return s.clip(a, b)

panel['log_aum'] = np.log(panel['avg_aum'].clip(lower=1e-6))
# 仅对真算列缩尾；模拟占位列 SDI_hc/OCI_hc/TO_calc 已删除，自动跳过
for c in ['quarter_return','excess_return','SDI','TO_two_sided','OCI_two_sided',
          'log_aum','log_fund_age','mgr_total_tenure_v2','return_volatility','RG','ARG']:
    if c in panel.columns:
        panel[c] = wins(panel[c])

panel['gender_m'] = panel['gender'].astype(str).str.contains('男').astype(float)
panel['cfa_d']    = panel['CFA'].astype(str).str.contains('Y|是|1', case=False, na=False).astype(float)
panel['edu_postgrad'] = panel['education'].astype(str).str.contains('硕士|博士|MBA|研究生', case=False, na=False).astype(float)

# ---- school 层级分类（复刻 req1_school_tier.py）----
c9 = {"北京大学","清华大学","复旦大学","上海交通大学","南京大学","浙江大学","中国科学技术大学","哈尔滨工业大学","西安交通大学"}
set985 = c9 | {"中国人民大学","武汉大学","中山大学","南开大学","华中科技大学","同济大学","北京航空航天大学","吉林大学","天津大学","四川大学","北京师范大学","厦门大学","东南大学","山东大学","中南大学","大连理工大学","华南理工大学","重庆大学","湖南大学","西北工业大学","中国农业大学","兰州大学","中央民族大学","西北农林科技大学","华东师范大学","东北大学","北京理工大学","中国海洋大学","电子科技大学"}
set211 = set985 | {"上海财经大学","中央财经大学","对外经济贸易大学","西南财经大学","中南财经政法大学","北京邮电大学","苏州大学","武汉理工大学","上海大学","河海大学","南京航空航天大学","北京交通大学","华东理工大学","南京理工大学","中国传媒大学","北京科技大学","华中师范大学","陕西师范大学","西南交通大学","北京工业大学","暨南大学","东华大学","南京师范大学","哈尔滨工程大学","郑州大学","安徽大学","合肥工业大学","中国政法大学","北京外国语大学","上海外国语大学","中央音乐学院","北京中医药大学","中国药科大学","长安大学","北京化工大学","华北电力大学","中国矿业大学","中国石油大学","江南大学","福州大学","南昌大学","广西大学","云南大学","贵州大学","海南大学","内蒙古大学","新疆大学","宁夏大学","青海大学","西藏大学","石河子大学","大连海事大学","辽宁大学","延边大学","东北师范大学","东北农业大学","东北林业大学","哈尔滨医科大学","南京农业大学","南京中医药大学","安徽师范大学","华南师范大学","华南农业大学","广州中医药大学","西南大学","四川农业大学","云南师范大学","陕西科技大学","西安电子科技大学","西北大学","西南财经大学"}
aliases = [("北大","北京大学"),("清华","清华大学"),("复旦","复旦大学"),("上海交大","上海交通大学"),("南大","南京大学"),("浙大","浙江大学"),("中科大","中国科学技术大学"),("中国科大","中国科学技术大学"),("哈工大","哈尔滨工业大学"),("西交大","西安交通大学"),("人大","中国人民大学"),("武大","武汉大学"),("南开","南开大学"),("华中科技","华中科技大学"),("同济","同济大学"),("北航","北京航空航天大学"),("北师大","北京师范大学"),("华东师范","华东师范大学"),("华东师大","华东师范大学"),("上海财经","上海财经大学"),("中央财经","中央财经大学"),("对外经济贸易","对外经济贸易大学"),("西南财经","西南财经大学"),("中南财经政法","中南财经政法大学"),("中南财经","中南财经政法大学")]
overseas_markers = ["美国","德国","英国","法国","加拿大","新加坡","澳大利亚","日本","香港","澳门","台湾","瑞士","荷兰","瑞典","丹麦","比利时","奥地利","新西兰","韩国","俄罗斯","意大利","西班牙","爱尔兰","牛津","剑桥","伦敦","帝国理工","哥伦比亚","哈佛","斯坦福","耶鲁","芝加哥","康奈尔","普林斯顿","宾夕法尼亚","麻省","加州","卡内基","东京","早稻田","京都","新加坡国立","南洋","多伦多","滑铁卢","麦吉尔","墨尔本","悉尼","新南威尔士","昆士兰","苏黎世","洛桑","慕尼黑","海德堡","巴黎","斯特拉斯克莱德","爱丁堡","曼彻斯特","华威","柏林","首尔","高丽","延世","莫斯科","圣彼得堡","奥克兰"]

def classify(raw):
    if not isinstance(raw,str) or raw.strip()=="": return "missing"
    s=raw.strip()
    for m in overseas_markers:
        if m in s: return "overseas"
    for sub,canon in aliases:
        if sub in s:
            if canon in c9: return "C9"
            if canon in set985: return "985"
            if canon in set211: return "211"
            return "other_domestic"
    return "other_domestic"

panel['school_tier'] = panel['school'].apply(classify)
panel['is_C9']   = (panel['school_tier']=='C9').astype(float)
panel['is_985']  = (panel['school_tier']=='985').astype(float)
panel['is_211']  = (panel['school_tier']=='211').astype(float)
panel['is_overseas'] = (panel['school_tier']=='overseas').astype(float)

# ============ L3：双向 FE + 基金聚类稳健 SE（复刻 14） ============
def fe_report(df, dv, ivs, label, by="fund_code"):
    need = [dv] + ivs + [by, "year"]
    sub = df[[c for c in need if c in df.columns]].dropna(subset=[dv]+ivs).copy().reset_index(drop=True)
    if len(sub) < len(ivs)*20:
        return None
    yr = pd.get_dummies(sub["year"], prefix="yr", drop_first=True).astype(float)
    sub = pd.concat([sub, yr], axis=1)
    all_x = ivs + list(yr.columns)
    g = sub.groupby(by)
    Xdm = sub[all_x] - g[all_x].transform("mean")
    ydm = (sub[dv] - g[dv].transform("mean")).values
    X = Xdm[all_x].values
    res = sm.OLS(ydm, X).fit(cov_type="cluster", cov_kwds={"groups": sub[by].values})
    out = {"spec": label, "DV": dv, "N": int(len(sub)), "rows": []}
    for j, v in enumerate(ivs):
        t=float(res.tvalues[j]); b=float(res.params[j]); p=float(res.pvalues[j])
        star="" if p>0.10 else ("*" if p>0.05 else ("**" if p>0.01 else "***"))
        out["rows"].append((v, b, t, p, star))
    return out

CONTROLS = ["log_aum","log_fund_age","mgr_total_tenure_v2","gender_m","cfa_d","edu_postgrad"]

print("="*72)
print("L3 层：双向 FE（fund+year）+ 基金聚类稳健 SE，DV=quarter_return")
print("="*72)
l3_specs = {
 "H1 SDI(真算风格漂移)":        ["SDI"]+CONTROLS,
 "H2 TO_two_sided(真算双边)":   ["TO_two_sided"]+CONTROLS,
 "H3 OCI_two_sided(真算)":      ["OCI_two_sided"]+CONTROLS,
 "H4 SDI+TO+OCI(真算联合)":     ["SDI","TO_two_sided","OCI_two_sided"]+CONTROLS,
}
results={}
for name, ivs in l3_specs.items():
    r = fe_report(panel, "quarter_return", ivs, name)
    results[name]=r
    if r is None:
        print(f"\n[{name}] 样本不足，跳过"); continue
    print(f"\n[{name}]  DV=quarter_return  N={r['N']}")
    for v,b,t,p,s in r["rows"]:
        if v in ["SDI","TO_two_sided","OCI_two_sided","log_aum","log_fund_age"]:
            print(f"   {v:16s} β={b:+.5f}  t={t:+.2f}  p={p:.3f}{s}")

# 备选 DV = excess_return（简要，诚实口径）
r2 = fe_report(panel, "excess_return", ["SDI","TO_two_sided","OCI_two_sided"]+CONTROLS, "H4-excess")
if r2:
    print(f"\n[H4-excess] DV=excess_return N={r2['N']}")
    for v,b,t,p,s in r2["rows"]:
        if v in ["SDI","TO_two_sided","OCI_two_sided"]:
            print(f"   {v:16s} β={b:+.5f}  t={t:+.2f}  p={p:.3f}{s}")

# ============ L1：基金层 alpha(ff5_adj_return) 横截面 OLS + HC1 ============
print("\n"+"="*72)
print("L1 层：ff5_adj_return(基金层 FF5 alpha) ~ 背景特征，横截面 OLS + HC1")
print("="*72)
fund = panel.groupby('fund_code').agg(
    ff5=('ff5_adj_return','first'), log_aum=('log_aum','mean'),
    log_fund_age=('log_fund_age','first'), tenure=('mgr_total_tenure_v2','mean'),
    gender_m=('gender_m','mean'), cfa_d=('cfa_d','mean'), edu_postgrad=('edu_postgrad','mean'),
    is_C9=('is_C9','max'), is_985=('is_985','max'), is_211=('is_211','max'),
    is_overseas=('is_overseas','max'), school_tier=('school_tier','first')).dropna(subset=['ff5','log_aum'])
fund['log_aum']=wins(fund['log_aum']); fund['ff5']=wins(fund['ff5'])
print(f"基金样本 N={len(fund)}")

# 全模型
l1_rhs = "is_C9+is_985+is_211+is_overseas+log_aum+log_fund_age+tenure+gender_m+cfa_d+edu_postgrad"
m1 = smf.ols(f"ff5 ~ {l1_rhs}", data=fund).fit(cov_type='HC1')
print(f"\n[L1 全模型] R2={m1.rsquared:.3f}")
for n in ['is_C9','is_985','is_211','is_overseas','log_aum','log_fund_age','tenure','gender_m','cfa_d','edu_postgrad']:
    b=m1.params[n]; t=m1.tvalues[n]; p=m1.pvalues[n]
    star="" if p>0.10 else ("*" if p>0.05 else ("**" if p>0.01 else "***"))
    print(f"   {n:14s} β={b:+.5f}  t={t:+.2f}  p={p:.3f}{star}")

# 单变量扫描（控制规模+年龄）
print("\n[L1 单变量扫描，各自控制 log_aum+log_fund_age]")
for v in ['is_C9','is_985','is_211','is_overseas','tenure','gender_m','cfa_d','edu_postgrad']:
    mm = smf.ols(f"ff5 ~ {v}+log_aum+log_fund_age", data=fund).fit(cov_type='HC1')
    b=mm.params[v]; t=mm.tvalues[v]; p=mm.pvalues[v]
    star="" if p>0.10 else ("*" if p>0.05 else ("**" if p>0.01 else "***"))
    print(f"   {v:14s} β={b:+.5f}  t={t:+.2f}  p={p:.3f}{star}  (N={int(mm.nobs)})")

# school tier 描述
print("\n[school tier 分布与基金平均 ff5 alpha]")
tt = fund.groupby('school_tier')['ff5'].agg(['count','mean']).round(4)
print(tt.to_string())
