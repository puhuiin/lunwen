# -*- coding: utf-8 -*-
"""
为 14 个指定变量，从源文献 PDF 中定位「变量说明/计算」所在页，
截取该区域为 PNG（全宽、围绕关键词的纵向条带），并输出 meta JSON。
最终由 build_consolidated.py 以 base64 内联嵌入 HTML。
"""
import os, json, fitz

BASE = r"D:/Desktop/基金经理行为分析研究/参考文献"
OUT = os.path.join(BASE, "shots")
os.makedirs(OUT, exist_ok=True)

# key -> 配置
# rel: 源 PDF（相对 BASE）；terms: 按优先级搜索词；pt/pb: 关键词上/下留白(pt)；zoom
VAR_MAP = {
    # ---------------- L1 背景特征层 ----------------
    "tenure": dict(rel="L1_背景特征层/04_Li_Li_2018_China_Manager_Characteristics.pdf",
                   terms=["tenure", "years of experience", "experience"], pt=110, pb=230, zoom=2.6,
                   fb=["L1_背景特征层/01_Chevalier_Ellison_1999_Career_Concerns_QJE.pdf",
                       "L1_背景特征层/07_赵秀娟_2010_个人特征实证.pdf"]),
    "fund_age": dict(rel="L1_背景特征层/04_Li_Li_2018_China_Manager_Characteristics.pdf",
                     terms=["age of the fund", "fund age", "fund's age", "age of fund"], pt=110, pb=230, zoom=2.6,
                     fb=["L1_背景特征层/14_基金经理在多大程度上影响了基金业绩_——业绩与个人特征的实证检验.pdf",
                         "L1_背景特征层/基金经理从业经验对我国公募基金业绩的影响研究.pdf"]),
    "education": dict(rel="L1_背景特征层/05_吴栩_2017_个人特征与业绩.pdf",
                      terms=["学历", "硕士", "博士", "学士"], pt=110, pb=230, zoom=2.6,
                      fb=["L1_背景特征层/08_L1_CFA_MBA_Mutual_Fund_Performance_2017.pdf",
                          "L1_背景特征层/06_于静_2013_个性特征与盈利能力.pdf"]),
    "age": dict(rel="L1_背景特征层/05_吴栩_2017_个人特征与业绩.pdf",
                terms=["年龄", "age"], pt=110, pb=230, zoom=2.6,
                fb=["L1_背景特征层/01_Chevalier_Ellison_1999_Career_Concerns_QJE.pdf",
                    "L1_背景特征层/04_Li_Li_2018_China_Manager_Characteristics.pdf"]),
    "cert": dict(rel="L1_背景特征层/08_L1_CFA_MBA_Mutual_Fund_Performance_2017.pdf",
                 terms=["CFA", "MBA", "certification", "designation"], pt=110, pb=230, zoom=2.6,
                 fb=["L1_背景特征层/05_吴栩_2017_个人特征与业绩.pdf",
                     "L1_背景特征层/12_L1_Mutual_Fund_Managers_Paid_Investment_Skill_2020.pdf"]),
    # ---------------- L2 持仓偏离层 ----------------
    "active_share": dict(rel="L2_持仓偏离层/01_Cremers_Petajisto_2009_ActiveShare_RFS.pdf",
                         terms=["Active Share", "active share"], pt=120, pb=280, zoom=2.6,
                         fb=["L2_持仓偏离层/04_Petajisto_2013_ActiveShare_FAJ.pdf",
                             "L2_持仓偏离层/02_Cremers_Petajisto_2009_ActiveShare_技术说明.pdf"]),
    "ici": dict(rel="L2_持仓偏离层/03_Kacperczyk_2005_ICI_JF.pdf",
                terms=["Industry Concentration Index", "industry concentration index", "ICI"], pt=120, pb=260, zoom=2.6,
                fb=[]),
    "hhi": dict(rel="L2_持仓偏离层/03_Kacperczyk_2005_ICI_JF.pdf",
                terms=["Herfindahl", "HHI", "herfindahl"], pt=120, pb=260, zoom=2.6,
                fb=[]),
    # ---------------- L3 交易行为层 ----------------
    "turnover": dict(rel="L3_交易行为层/01_Kacperczyk_2008_UnobservedActions_RFS.pdf",
                     terms=["turnover", "portfolio turnover", "Turnover"], pt=120, pb=260, zoom=2.6,
                     fb=["L3_交易行为层/06_Lan_2015_HoldingHorizon_CFR.pdf",
                         "L3_交易行为层/10_L3_Kacperczyk_Sialm_Zheng_2005_Unobserved_Actions_NBERw11363.pdf"]),
    "oci": dict(rel="L4_风险应对层/02_The_impact_of_experience_on_risk_taking,_overconfidence,_and_herding_of_fund_man_2006.pdf",
                terms=["overconfidence", "overconfident", "self-attribution"], pt=120, pb=300, zoom=2.6,
                fb=[]),
    "style_drift": dict(rel="L4_风险应对层/01_寇宗来_2020_风格漂移_金融学季刊.pdf",
                        terms=["风格漂移", "Fsds", "SDS", "漂移"], pt=120, pb=280, zoom=2.6,
                        fb=["L4_风险应对层/业绩排名对投资风格影响研究——来自开放式基金的证据.pdf",
                            "L4_风险应对层/业绩排名对基金风格漂移的影响研究.pdf"]),
    # ---------------- L4 风险应对层 ----------------
    "return_gap": dict(rel="L3_交易行为层/01_Kacperczyk_2008_UnobservedActions_RFS.pdf",
                       terms=["return gap", "Return Gap", "return-gap"], pt=120, pb=300, zoom=2.6,
                       fb=["L3_交易行为层/02_申宇_2013_隐形交易_管理世界.pdf"]),
    "arg": dict(rel="L3_交易行为层/02_申宇_2013_隐形交易_管理世界.pdf",
                terms=["隐形交易", "风险调整幅度", "ARG", "R ?(RH"], pt=120, pb=300, zoom=2.6,
                fb=["L3_交易行为层/03_周少甫_2009_不可观测行为.pdf",
                    "L3_交易行为层/16_基金未公开的信息_隐形交易与投资业绩.pdf"]),
    "return_vol": dict(rel="L4_风险应对层/04_Ang_Chen_Xing_2006_DownsideRisk_RFS.pdf",
                       terms=["volatility", "standard deviation", "return volatility", "idiosyncratic volatility"], pt=120, pb=300, zoom=2.6,
                       fb=["L1_背景特征层/业绩波动率、投资者资金流与基金经理冒险行为.pdf"]),
}

def open_doc(rel):
    path = os.path.join(BASE, rel)
    if not os.path.exists(path):
        return None
    try:
        return fitz.open(path)
    except Exception:
        return None

def best_page(doc, terms):
    """返回 (page_idx, matched_term, score) 最优页"""
    best = None
    for pno in range(len(doc)):
        txt = doc[pno].get_text("text").lower()
        if not txt:
            continue
        hits = 0
        mt = None
        for t in terms:
            c = txt.count(t.lower())
            if c:
                hits += c
                if mt is None:
                    mt = t
        if hits and (best is None or hits > best[2]):
            best = (pno, mt, hits)
    return best

def crop_render(doc, pno, term, pt, pb, zoom, key):
    page = doc[pno]
    rects = page.search_for(term)
    if not rects:
        # 退而求其次：用正文定位（search_for 对带符号词可能失败）
        return None
    r0 = rects[0]
    clip = fitz.Rect(20, max(0, r0.y0 - pt),
                     page.rect.width - 20, min(page.rect.height, r0.y1 + pb))
    if clip.height < 90:
        clip = fitz.Rect(20, max(0, r0.y0 - pt), page.rect.width - 20,
                         min(page.rect.height, r0.y1 + pb + 120))
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat, clip=clip)
    out = os.path.join(OUT, key + ".png")
    pix.save(out)
    return out

meta = {}
for key, cfg in VAR_MAP.items():
    rel = cfg["rel"]
    doc = open_doc(rel)
    chosen = None
    if doc:
        chosen = best_page(doc, cfg["terms"])
    if not chosen and cfg.get("fb"):
        for fbrel in cfg["fb"]:
            if chosen:
                break
            d2 = open_doc(fbrel)
            if d2:
                b = best_page(d2, cfg["terms"])
                if b:
                    chosen = b; rel = fbrel; doc = d2
    if not chosen:
        meta[key] = {"status": "NOT_FOUND", "rel": rel}
        print("✗ %-12s 未找到定义页 (%s)" % (key, rel))
        continue
    pno, mt, score = chosen
    out = crop_render(doc, pno, mt, cfg["pt"], cfg["pb"], cfg["zoom"], key)
    if out is None:
        # search_for 失败，再试其他 term
        for t in cfg["terms"]:
            out = crop_render(doc, pno, t, cfg["pt"], cfg["pb"], cfg["zoom"], key)
            if out:
                mt = t
                break
    if out is None:
        meta[key] = {"status": "CROP_FAIL", "rel": rel, "page": pno + 1}
        print("⚠ %-12s 裁剪失败 (%s p%d)" % (key, rel, pno + 1))
        continue
    snippet = doc[pno].get_text("text")
    # 取关键词附近片段
    idx = snippet.lower().find(mt.lower())
    snip = snippet[max(0, idx - 60): idx + 220].replace("\n", " ") if idx >= 0 else snippet[:200]
    meta[key] = {"status": "OK", "rel": rel, "page": pno + 1, "term": mt,
                 "score": score, "png": os.path.basename(out), "snippet": snip}
    print("✓ %-12s %-55s p%-3d term=%-18s -> %s" % (key, rel.split("/")[-1], pno + 1, mt, os.path.basename(out)))

with open(os.path.join(BASE, "shots_meta.json"), "w", encoding="utf-8") as f:
    json.dump(meta, f, ensure_ascii=False, indent=2)
print("\n共 %d 个变量，成功 %d，写出 shots_meta.json" %
      (len(VAR_MAP), sum(1 for v in meta.values() if v.get("status") == "OK")))
