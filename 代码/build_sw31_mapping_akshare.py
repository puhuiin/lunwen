# -*- coding: utf-8 -*-
"""
免费修复脚本 2：用 akshare 获取【股票 -> 申万一级行业】映射（全 A 股 31 个一级）。

解决的问题：
  - 当前 ICI / industry_hhi 只能靠 基金行业配置_全量.csv（82 个混标）映射到申万31，
    重建值 0.053/0.014 与原面板 0.26/0.071 严重不符，且无法复现。
  - 拿到股票->申万一级映射后，可直接【从持仓明细重聚行业权重】，与 AS 等用同一数据源，
    口径自洽、可复现。

用法（需联网 + 安装 akshare）：
  pip install akshare
  python build_sw31_mapping_akshare.py

输出：
  data/L2_持仓偏离层/stock_sw31_map.csv
  字段：stock_code, sw31  （sw31 为申万一级行业名称，与流水线 SW31_MAP 的 value 对齐）

说明：
  - 申万一级代码 801010~801980（31 个），下方 SW31 字典已列全。
  - akshare 的 sw_index_cons 可能改名，若报错请查 akshare 文档替换为等价接口
    （如 index_stock_cons_csindex / stock_board_industry_cons_em）。
"""
import os
import akshare as ak
import pandas as pd

OUT = r"D:\Desktop\基金经理行为分析研究\数据\L2_持仓偏离层\stock_sw31_map.csv"

# 申万一级行业代码 -> 名称（共 31 个，与流水线 SW31_MAP 的映射目标一致）
SW31 = {
    "801010": "农林牧渔", "801030": "基础化工", "801040": "钢铁", "801050": "有色金属",
    "801080": "电子", "801110": "家用电器", "801120": "食品饮料", "801130": "纺织服饰",
    "801140": "轻工制造", "801150": "医药生物", "801160": "公用事业", "801170": "交通运输",
    "801180": "房地产", "801200": "商贸零售", "801210": "社会服务", "801230": "综合",
    "801710": "建筑材料", "801720": "建筑装饰", "801730": "电力设备", "801740": "国防军工",
    "801750": "计算机", "801760": "传媒", "801770": "通信", "801780": "银行",
    "801790": "非银金融", "801880": "汽车", "801890": "机械设备", "801950": "煤炭",
    "801960": "石油石化", "801970": "环保", "801980": "美容护理",
}


def main():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    frames = []
    for code, name in SW31.items():
        try:
            cons = ak.sw_index_cons(symbol=code)
            if cons is None or cons.empty:
                continue
            # 不同版本列名可能为 股票代码 / 证券代码 / code
            col = next((c for c in cons.columns if "代码" in c or c.lower() == "code"), None)
            if col is None:
                print(f"  [{name}] 未找到股票代码列，跳过。列={list(cons.columns)}")
                continue
            sub = pd.DataFrame({"stock_code": cons[col].astype(str).str.zfill(6),
                                "sw31": name})
            frames.append(sub)
            print(f"  {name}: {len(sub)} 只")
        except Exception as e:
            print(f"  [{name}] 失败: {e}")
            continue
    if not frames:
        print("未获取到任何映射，请检查 akshare 版本与网络。")
        return
    out = pd.concat(frames, ignore_index=True).drop_duplicates("stock_code")
    out.to_csv(OUT, index=False, encoding="utf-8-sig")
    print("写出:", OUT, out.shape, " 映射股票数:", out["stock_code"].nunique())


if __name__ == "__main__":
    main()
