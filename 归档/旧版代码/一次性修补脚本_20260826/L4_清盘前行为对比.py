#_encoding: utf-8
# L4 清盘前行为对比：把清盘人口(183只)的行为指标与主样本存续200只做同口径对照
# 输入(L4_风险应对层)：清盘基金基础信息.csv / 清盘基金持仓明细_iFinD.csv /
#                      清盘基金交易方向_akshare.csv / 清盘基金净值_iFinD合并.csv
# 输入(主面板)：output/主分析面板_重建.csv  (存续200只同口径指标，作对照组)
# 输入(股价行情)：个股月收益率_全量.csv  (DE/PGR/PLR 用，缺失则跳过并报告)
import os, re, json, warnings
import numpy as np
import pandas as pd
warnings.simplefilter("ignore")

PIPE = r"D:\Desktop\基金经理行为分析研究\指标计算流水线"
L4   = r"D:\Desktop\基金经理行为分析研究\数据\L4_风险应对层"
OUT  = os.path.join(PIPE, "output", "L4_清盘前行为对比")
os.makedirs(OUT, exist_ok=True)

def D(layer, name):
    return os.path.join(PIPE, "data", layer, name)

def q_end(year, q):
    return pd.Period(year=int(year), quarter=int(q), freq="Q").end_time.normalize()

# ---------- 载入 L4 原始 ----------
info   = pd.read_csv(os.path.join(L4, "清盘基金基础信息.csv"), encoding="utf-8-sig")
hold   = pd.read_csv(os.path.join(L4, "清盘基金持仓明细_iFinD.csv"), encoding="utf-8-sig")
trade  = pd.read_csv(os.path.join(L4, "清盘基金交易方向_akshare.csv"), encoding="utf-8-sig")
nav    = pd.read_csv(os.path.join(L4, "清盘基金净值_iFinD合并.csv"), encoding="utf-8-sig")

print("载入: 基础信息 %d 基金 | 持仓 %d 行/%d 基金 | 交易 %d 行/%d 基金 | 净值 %d 行"
      % (info['fund_code'].nunique(), len(hold), hold['fund_code'].nunique(),
         len(trade), trade['fund_code'].nunique(), len(nav)))

# 注：行为基金(持仓/交易/净值)的清盘日不在 183-list 的「清盘基金基础信息.csv」里，
# 实际清盘日改从净值文件自身的「清盘日期」列取（见下方第3节 nav 处理处 liq_map）。
liq_map = {}

# ================= 1) 双边换手率(来自真实买卖数据，非快照) =================
m = re.compile(r"(\d{4})年(\d)季度")
def parse_period(s):
    mm = m.search(str(s))
    if not mm: return pd.NaT
    return q_end(mm.group(1), mm.group(2))
trade['rd'] = trade['报告期'].apply(parse_period)
trade['pct'] = pd.to_numeric(trade['占净值比例_%'], errors='coerce') / 100.0
buy  = trade[trade['direction'] == '买入'].groupby(['fund_code','rd'])['pct'].sum()
sell = trade[trade['direction'] == '卖出'].groupby(['fund_code','rd'])['pct'].sum()
to = pd.concat([buy.rename('buy'), sell.rename('sell')], axis=1).fillna(0)
to['TO_bilateral'] = (to['buy'] + to['sell']) / 2.0      # 双边=(买入+卖出)/(2×NAV)
to = to.reset_index()[['fund_code','rd','TO_bilateral']].rename(columns={'rd':'report_date'})
print("换手率(真实买卖): %d 基金-期" % to['fund_code'].nunique())

# ================= 2) LSV + 个股集中度HHI(来自持仓快照变动方向) =================
hold['rd'] = pd.to_datetime(hold['report_date'], format="%Y%m%d", errors='coerce')
g = hold.groupby(['fund_code','rd'])['hold_value'].transform('sum')
hold['w'] = hold['hold_value'] / g
hold = hold.sort_values(['fund_code','stock_code','rd'])
hold['prev_w'] = hold.groupby(['fund_code','stock_code'])['w'].shift(1)
hold['dir'] = np.sign(hold['w'] - hold['prev_w'])
hold = hold.dropna(subset=['dir'])
hold = hold[hold['dir'] != 0]
if len(hold):
    mkt = hold.groupby(['rd','stock_code'])['dir'].agg(
        B=lambda s: int((s==1).sum()), S=lambda s: int((s==-1).sum()),
        n=lambda s: int(s.count())).reset_index()
    mkt['p_i'] = mkt['B'] / (mkt['B'] + mkt['S'])
    pbar = mkt.groupby('rd')['p_i'].mean().rename('p_t')
    mkt = mkt.merge(pbar, on='rd')
    mkt['AF'] = np.sqrt(2.0/np.pi) * np.sqrt((mkt['p_t']*(1-mkt['p_t'])).clip(lower=0)/mkt['n'])
    mkt['H_i'] = (mkt['p_i'] - mkt['p_t']).abs() - mkt['AF']
    res = hold[['fund_code','rd','stock_code']].merge(mkt[['rd','stock_code','H_i']], on=['rd','stock_code'])
    lsv = res.groupby(['fund_code','rd'])['H_i'].mean().reset_index().rename(columns={'rd':'report_date','H_i':'lsv'})
    hhi = hold.groupby(['fund_code','rd'])['w'].apply(lambda s: float((s**2).sum())).reset_index().rename(columns={'w':'hhi_stock','rd':'report_date'})
    print("LSV/HHI(持仓快照): %d 基金-期" % lsv['fund_code'].nunique())
else:
    lsv = pd.DataFrame(columns=['fund_code','report_date','lsv'])
    hhi = pd.DataFrame(columns=['fund_code','report_date','hhi_stock'])

# ================= 3) RA + 收益波动(来自日度净值) =================
nav['date'] = pd.to_datetime(nav['净值日期'], errors='coerce')
nav['ret']  = pd.to_numeric(nav['净值增长率%'], errors='coerce') / 100.0
nav = nav.dropna(subset=['date','ret']).sort_values(['基金代码','date'])
nav['fund_code'] = nav['基金代码'].astype(str).str.replace('.OF','',regex=False)
# 清盘日来自净值文件自身的「清盘日期」列（行为基金的清盘日不在 183-list 基础信息里）
_nav_liq = nav.groupby('fund_code')['清盘日期'].apply(lambda s: pd.to_datetime(s.dropna().max(), errors='coerce')).dropna()
liq_map = {str(k).zfill(6): v for k, v in _nav_liq.to_dict().items()}
nav['q'] = nav['date'].dt.to_period('Q')
qr = nav.groupby(['fund_code','q'])['ret'].apply(lambda s: float((1+s).prod()-1)).reset_index()
qr['report_date'] = qr['q'].apply(lambda p: p.end_time.normalize())
qr = qr.sort_values(['fund_code','report_date'])
qr['return_volatility'] = qr.groupby('fund_code')['ret'].transform(lambda s: s.rolling(8, min_periods=3).std())
def ra_group(df):
    arr = df['ret'].values; out=[]
    for i in range(len(arr)):
        seg = arr[max(0,i-7):i+1]; g = seg[seg>0]; l = seg[seg<=0]
        out.append((float(g.std()-l.std())) if (len(g)>0 and len(l)>0) else np.nan)
    df = df.copy(); df['risk_asym'] = out; return df
ra_list=[]
for _fc, gdf in qr.groupby('fund_code'):
    arr = gdf['ret'].values; out=[]
    for i in range(len(arr)):
        seg = arr[max(0,i-7):i+1]; gg = seg[seg>0]; ll = seg[seg<=0]
        out.append((float(gg.std()-ll.std())) if (len(gg)>0 and len(ll)>0) else np.nan)
    ra_list.extend(out)
qr['risk_asym'] = ra_list
ra = qr[['fund_code','report_date','risk_asym','return_volatility']]
print("RA/收益波动(净值): %d 基金 / %d 期" % (ra['fund_code'].nunique(), len(ra)))

# ================= 4) DE/PGR/PLR(处置效应，来自持仓+个股收益，缺失则跳过) =================
de = pd.DataFrame(columns=['fund_code','report_date','de','pgr','plr'])
try:
    sm = pd.read_csv(D("股价行情","个股月收益率_全量.csv"), encoding="utf-8-sig")
    sm['date'] = pd.to_datetime(sm['date'], errors='coerce')
    sm = sm.dropna(subset=['date']).sort_values(['stock_code','date'])
    sd = {c:(g['date'].values, g['monthly_return'].values) for c,g in sm.groupby('stock_code')}
    def pret(code,t0,t1):
        if code not in sd: return np.nan
        ds,rs = sd[code]; mask=(ds>t0)&(ds<=t1); sub=rs[mask]
        return float(sub.sum()) if len(sub) else np.nan
    rows=[]
    for fund,fdf in hold.groupby('fund_code'):
        fdf=fdf.sort_values('rd'); dates=fdf['rd'].unique()
        for i in range(1,len(dates)):
            t0,t1=dates[i-1],dates[i]
            prev=set(fdf[fdf['rd']==t0]['stock_code']); cur=set(fdf[fdf['rd']==t1]['stock_code'])
            sold=prev-cur; held=prev&cur; gs=gh=ls=ll=0
            for c in sold:
                r=pret(c,t0,t1)
                if pd.isna(r): continue
                if r>0: gs+=1
                else: ll+=1
            for c in held:
                r=pret(c,t0,t1)
                if pd.isna(r): continue
                if r>0: gh+=1
                else: ll+=1
            dg,dl=gs+gh,ll+ls
            pgr=gs/dg if dg else np.nan; plr=ll/dl if dl else np.nan
            de_=pgr-plr if (dg and dl) else np.nan
            rows.append((fund, t1, de_, pgr, plr))
    de=pd.DataFrame(rows, columns=['fund_code','report_date','de','pgr','plr'])
    print("DE/PGR/PLR(处置效应): %d 基金-期" % de['fund_code'].nunique())
except Exception as e:
    print("DE/PGR/PLR 跳过(个股收益缺失):", e)

# ================= 合并 L4 面板 =================
panels=[to, lsv, hhi, ra, de]
for p in panels:
    if p is not None and len(p):
        p['fund_code'] = p['fund_code'].astype(str).str.zfill(6)
L4p = None
for p in panels:
    if p is None or len(p)==0: continue
    L4p = p if L4p is None else L4p.merge(p, on=['fund_code','report_date'], how='outer')
L4p['years_to_liq'] = L4p['fund_code'].map(liq_map)
L4p['years_to_liq'] = (L4p['years_to_liq'] - L4p['report_date']).dt.days / 365.25
def bucket(y):
    if pd.isna(y): return "未知"
    if y < 1:  return "到期清算前1年内(<1y)"
    if y < 2:  return "1-2年"
    if y < 3:  return "2-3年"
    if y < 4:  return "3-4年"
    return "4年以上"
L4p['bucket'] = L4p['years_to_liq'].apply(bucket)
L4p = L4p.sort_values(['fund_code','report_date'])
L4p.to_csv(os.path.join(OUT,"L4_行为指标面板.csv"), index=False, encoding="utf-8-sig")
print("L4 面板写出: %d 行, %d 基金" % (len(L4p), L4p['fund_code'].nunique()))

# ================= 对照：存续200只(主面板) =================
# 存续面板列名 → L4 面板列名 的映射（同名直接对应，换手率/集中度口径不同但同义）
pair_map = {
    'lsv':'lsv',
    'risk_asym':'risk_asym',
    'return_volatility':'return_volatility',
    'de':'de', 'pgr':'pgr', 'plr':'plr',
    'TO_two_sided':'TO_bilateral',     # 存续=报告双边换手；L4=真实买卖累计折算双边
    'industry_hhi':'hhi_stock',        # 存续=行业集中度；L4=前十大个股权重集中度(代理)
}
surv = pd.read_csv(os.path.join(PIPE,"output","主分析面板_重建.csv"), encoding="utf-8-sig")
surv_cols = [c for c in list(pair_map.keys())+['fund_code'] if c in surv.columns]
surv = surv[surv_cols]
surv_fund = surv.groupby('fund_code')[[c for c in pair_map if c in surv]].mean(numeric_only=True)
L4_fund   = L4p.groupby('fund_code')[[c for c in pair_map.values() if c in L4p]].mean(numeric_only=True)
summary=[]
for sc, lc in pair_map.items():
    s_mean = surv_fund[sc].mean() if (sc in surv_fund) else np.nan
    l_mean = L4_fund[lc].mean() if (lc in L4_fund) else np.nan
    s_n = surv_fund[sc].notna().sum() if sc in surv_fund else 0
    l_n = L4_fund[lc].notna().sum() if lc in L4_fund else 0
    summary.append({'指标(存续→L4)':f"{sc} → {lc}",'存续200只_均值':round(s_mean,4) if pd.notna(s_mean) else np.nan,
                    '存续_基金数':int(s_n),'清盘_均值':round(l_mean,4) if pd.notna(l_mean) else np.nan,
                    '清盘_基金数':int(l_n),'差异(清盘-存续)':round(l_mean-s_mean,4) if (pd.notna(l_mean) and pd.notna(s_mean)) else np.nan})
sumdf=pd.DataFrame(summary)
sumdf.to_csv(os.path.join(OUT,"L4_vs_存续对比.csv"), index=False, encoding="utf-8-sig")
print("\n=== L4(清盘) vs 存续200只 均值对比 ===")
print(sumdf.to_string(index=False))

# ================= 清盘前轨迹(按距清盘年数分桶) =================
l4_metric_cols = [c for c in ['TO_bilateral','lsv','hhi_stock','risk_asym','return_volatility','de','pgr','plr'] if c in L4p]
traj = L4p.groupby('bucket')[l4_metric_cols].mean(numeric_only=True).round(4)
traj = traj.reindex(["到期清算前1年内(<1y)","1-2年","2-3年","3-4年","4年以上","未知"]).dropna(how='all')
traj.to_csv(os.path.join(OUT,"L4_清盘前轨迹.csv"), encoding="utf-8-sig")
print("\n=== 清盘前行为轨迹(按距清盘年数) ===")
print(traj.to_string())

# 覆盖率
cov = L4p.groupby('bucket')[['TO_bilateral','lsv','hhi_stock','risk_asym','return_volatility','de']].apply(lambda d: d.notna().mean()*100).round(1)
cov.to_csv(os.path.join(OUT,"L4_各桶覆盖率%.csv"), encoding="utf-8-sig")
print("\n完成。输出目录:", OUT)
