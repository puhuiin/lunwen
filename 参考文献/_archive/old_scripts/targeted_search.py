# -*- coding: utf-8 -*-
import fitz, os

REF = r"D:/Desktop/基金经理行为分析研究/参考文献"

# (var, [candidate pdfs], [keywords])
TARGETS = [
 ("ici",       ["L2_持仓偏离层/03_Kacperczyk_2005_ICI_JF.pdf"], ["industry concentration", "ICI", "concentration index", "Herfindahl", "HHI"]),
 ("hhi",       ["L2_持仓偏离层/03_Kacperczyk_2005_ICI_JF.pdf"], ["Herfindahl", "HHI", "sum of squared"]),
 ("turnover",  ["L3_交易行为层/06_Lan_2015_HoldingHorizon_CFR.pdf",
                "L3_交易行为层/01_Kacperczyk_2008_UnobservedActions_RFS.pdf",
                "文献/共同基金流量与业绩文献包/Carhart_1997_Persistence_JF.pdf"],
               ["portfolio turnover", "turnover", "换手", "trading volume"]),
 ("oci",       ["L4_风险应对层/02_The_impact_of_experience_on_risk_taking,_overconfidence,_and_herding_of_fund_man_2006.pdf",
                "L3_交易行为层/01_Kacperczyk_2008_UnobservedActions_RFS.pdf"],
               ["overconfidence", "overconfident", "self-attribution", "过度自信"]),
 ("style_drift",["L4_风险应对层/01_寇宗来_2020_风格漂移_金融学季刊.pdf"],
               ["style drift", "风格漂移", "SDI", "style persistence", "Fsds"]),
 ("return_gap",["L3_交易行为层/01_Kacperczyk_2008_UnobservedActions_RFS.pdf",
                "L3_交易行为层/02_申宇_2013_隐形交易_管理世界.pdf"],
               ["Return Gap", "return gap", "unobserved action"]),
 ("arg",       ["L3_交易行为层/02_申宇_2013_隐形交易_管理世界.pdf"],
               ["隐形交易", "ARG", "修正隐形", "risk adjustment"]),
 ("return_vol",["L4_风险应对层/03_Brown_Harlow_Starks_1996_Tournaments_JF.pdf",
                "文献/风险与波动率文献/Ang_2006_DownsideRisk_RFS.pdf"],
               ["standard deviation", "volatility", "return", "波动率", "risk"]),
]

def search(pdf, kws):
    try:
        doc = fitz.open(pdf)
    except Exception as e:
        return [], str(e)
    res = []
    for pno in range(min(len(doc), 60)):
        try:
            t = doc[pno].get_text().lower()
        except Exception:
            continue
        c = sum(t.count(k.lower()) for k in kws)
        if c > 0:
            res.append((pno, c))
    doc.close()
    return res, None

for var, pdfs, kws in TARGETS:
    print("\n===== %s =====" % var)
    for pdf in pdfs:
        full = os.path.join(REF, pdf)
        if not os.path.exists(full):
            print("  [缺失] %s" % pdf); continue
        res, err = search(full, kws)
        if err:
            print("  [错误] %s -> %s" % (pdf, err)); continue
        res.sort(key=lambda x: -x[1])
        for pno, c in res[:3]:
            print("  %3d  p%-3d  %s" % (c, pno + 1, pdf))
