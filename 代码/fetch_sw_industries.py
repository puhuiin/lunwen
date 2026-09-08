# -*- coding: utf-8 -*-
"""用 akshare 申万指数专用接口(index_hist_sw)获取全部31个申万一级行业月度收益率。
避开 East Money push2 代理问题（走申万官网源）。用于 RA 构念纯化：基金行业 beta。"""
import akshare as ak
import pandas as pd
import os

OUT_DIR = r"D:\Desktop\基金经理行为分析研究\数据\外部数据"
os.makedirs(OUT_DIR, exist_ok=True)

# 申万一级行业(2021版) 代码->名称
SW_L1 = {
    "801010": "农林牧渔", "801030": "基础化工", "801040": "钢铁", "801050": "有色金属",
    "801080": "电子", "801110": "家用电器", "801120": "食品饮料", "801130": "纺织服饰",
    "801140": "轻工制造", "801150": "医药生物", "801160": "公用事业", "801170": "交通运输",
    "801180": "房地产", "801200": "商贸零售", "801210": "社会服务", "801230": "综合",
    "801710": "建筑材料", "801720": "建筑装饰", "801730": "电力设备", "801740": "国防军工",
    "801750": "计算机", "801760": "传媒", "801770": "通信", "801780": "银行",
    "801790": "非银金融", "801880": "汽车", "801890": "机械设备", "801950": "煤炭",
    "801960": "石油石化", "801970": "环保", "801980": "美容护理",
}

all_rows = []
fail = []
for code, name in SW_L1.items():
    try:
        df = ak.index_hist_sw(symbol=code, period="month")
        df = df[["日期", "收盘"]].copy()
        df["industry_code"] = code
        df["industry_name"] = name
        df["日期"] = pd.to_datetime(df["日期"])
        df = df.sort_values("日期")
        df["monthly_return"] = df["收盘"].pct_change()
        df = df.dropna(subset=["monthly_return"])
        df = df.rename(columns={"日期": "date", "收盘": "close"})
        all_rows.append(df[["date", "industry_code", "industry_name", "close", "monthly_return"]])
        print(f"  {code} {name}: {len(df)} 个月度观测")
    except Exception as e:
        fail.append((code, name, str(e)[:80]))
        print(f"  {code} {name} 失败: {str(e)[:80]}")

if all_rows:
    out = pd.concat(all_rows, ignore_index=True)
    out_path = os.path.join(OUT_DIR, "sw_all_industry_monthly.csv")
    out.to_csv(out_path, index=False, encoding="utf-8-sig")
    print(f"\n已保存: {out_path}")
    print(f"  总行数: {len(out)}, 行业数: {out.industry_name.nunique()}")
    print(f"  日期范围: {out.date.min().date()} ~ {out.date.max().date()}")
    if fail:
        print(f"  失败行业: {fail}")
else:
    print("未获取到任何行业数据")
