# -*- coding: utf-8 -*-
"""论文正文补丁（2026-08-30）· 第十七轮：把外部效度检验写进论文

注意：脚本本身不做 f-string 替换——把要插入的字面量写成字符串，用占位符 {EXT_xxx}
由 docx 脚本运行时从 EXT dict 取值。
"""
import io

P = 'scripts/_draft_docx_20260826.py'
s = io.open(P, encoding='utf-8').read()

# ---------- 1) 加载 EXT JSON ----------
add_load = (
    "# 外部效度检验（2026-08-30 第十七轮）：33 只论文样本外基金的 ISDI / SDI 论文口径复核\n"
    "EXT = json.loads((OUT / '外部效度检验_论文口径_2026-08-30.json').read_text(encoding='utf-8'))"
)
if 'EXT = json.loads' not in s:
    anchor = "# 负号排版统一：全文用 U+2212（−），而 Python 的 {:+.3f} 产出 ASCII 减号，故预先转好。"
    if anchor in s:
        s = s.replace(anchor, add_load + '\n' + anchor, 1)
        print('[1] 已加载 EXT 外部效度 JSON')
    else:
        print('[1] MISS: 未找到加载锚点')
else:
    print('[1] EXT 已存在，跳过')

# ---------- 2) 在 §5 第四点末尾追加"外部效度"小段 ----------
# 用占位符方式：把 EXT[...] 写在 f-string 里，但补丁脚本里只用字符串拼接
anchor_4 = "          '最能拉开差距的行为是市场下跌时是否主动收缩暴露。')"

# 直接用 f-string 字面量（Python 脚本本身没问题，是 print 时报错——现在 print 也不输出它）
add_ext_para = (
    "para(doc,\n"
    "    f\"<b>外部效度</b>。前述结论主要建立在样本内证据之上，\"\n"
    "    f\"另以 {EXT['样本量'].split('，')[0]}（绩优 18 / 绩差 15，\"\n"
    "    f\"按近 3 年收益分组的<u>已知群体效度检验</u>）做样本外佐证。\"\n"
    "    f\"指标按论文原始口径计算：L3 行业风格漂移（ISDI）按 31 个申万一级行业\"\n"
    "    f\"Beta 评分分高/中/低弹性三组、前十大重仓股归组、相邻期组权重向量曼哈顿距离；\"\n"
    "    f\"L5 策略偏离（SDI）按基金季收益对规模×价值/成长四宫格\"\n"
    "    f\"（399372/399373/399376/399377）8 季滚动 OLS、相邻期权重曼哈顿距离。\"\n"
    "    f\"结果：ISDI 绩优 {EXT['ISDI_论文口径']['mean_good']:.4f} \"\n"
    "    f\"vs 绩差 {EXT['ISDI_论文口径']['mean_bad']:.4f}\"\n"
    "    f\"（t={EXT['ISDI_论文口径']['t']:+.2f}***，\"\n"
    "    f\"Spearman ρ={EXT['ISDI_论文口径']['spearman_rho']:+.3f}，\"\n"
    "    f\"p={EXT['ISDI_论文口径']['spearman_p']:.4f}，\"\n"
    "    f\"控制年化波动后偏相关 {EXT['ISDI_论文口径']['partial_after_vol']:+.3f}），\"\n"
    "    f\"方向、显著性、效应量均与论文一致，是本文拿到的最稳健的外部支持。\"\n"
    "    f\"SDI 论文口径方向亦正确（绩优 {EXT['SDI_论文口径']['mean_good']:.4f} \"\n"
    "    f\"vs 绩差 {EXT['SDI_论文口径']['mean_bad']:.4f}，t={EXT['SDI_论文口径']['t']:+.2f} n.s.，\"\n"
    "    f\"ρ={EXT['SDI_论文口径']['spearman_rho']:+.3f}），\"\n"
    "    f\"但样本量下不构成强证据；其与样本内简化的反方向结果差异源于口径误用\"\n"
    "    f\"（简化版以 FF5 SMB+HML 两因子替代四宫格），详见配套外部效度报告。\"\n"
    "    f\"窗口敏感性（基准／去 2025–26／去 2019／2022 后）共 4 套窗口下，\"\n"
    "    f\"ISDI 方向全部正确，SDI 方向全部正确但均 n.s.。\"\n"
    "    f\"<b>外部不支持的</b>：L4a 下行保护系数 timing 在外部 33 只样本上 ρ=+0.130（n.s.），\"\n"
    "    f\"控制波动后仅 −0.009——\"\n"
    "    f\"说明样本内该指标的强区分力依赖特定的回归设定或控制变量组合，\"\n"
    "    f\"<b>是论文主张须如实披露的负面外部证据</b>。\"\n"
    "    f\"进一步细分见配套《外部效度检验》两份报告。\")\n"
)
if "EXT['样本量']" not in s:
    if anchor_4 in s:
        s = s.replace(anchor_4, anchor_4 + '\n' + add_ext_para, 1)
        print('[2] 外部效度段已追加')
    else:
        print('[2] MISS: 第四点锚点')
else:
    print('[2] 外部效度段已存在，跳过')

io.open(P, 'w', encoding='utf-8').write(s)
print('补丁已写入', P)