# -*- coding: utf-8 -*-
"""论文正文补丁（2026-08-29）：
1) 加载构建链条诊断 CH（供成分级相关引用）
2) 精简 AS 六道检验的非线性/条件效应细节，腾出篇幅
3) 在 §3.4 补入成分级相关 SDI×ARG = -0.84
"""
import io

P = 'scripts/_draft_docx_20260826.py'
s = io.open(P, encoding='utf-8').read()

# ---------- 1) 加载 CH ----------
anchor_hom = ("HOM = json.loads((OUT / 'L4a同源诊断_2026-08-29.json').read_text(encoding='utf-8'))")
add_ch = anchor_hom + (
    "\n# 构建链条诊断（2026-08-29 补做）：成分级跨层相关"
    "\nCH = json.loads((OUT / '构建链条诊断_2026-08-29.json').read_text(encoding='utf-8'))")
if s.count(anchor_hom) == 1 and 'CH = json.loads' not in s:
    s = s.replace(anchor_hom, add_ch)
    print('[1] 已加载 CH')
elif 'CH = json.loads' in s:
    print('[1] CH 已存在，跳过')
else:
    print('[1] MISS: 未找到 HOM 锚点')

# ---------- 2) 精简 AS 段落 ----------
old1 = ("          '补充的非线性与条件效应检验同样不支持：二次项在仅控制变量口径下显著'\n"
        "          '（t=+2.49／+2.77），加入全部行为指标后失去显著性（t=+0.53／−0.40）；'\n"
        "          '与行业集中度的交互项两个口径均不显著（t=−0.89／+1.27）。'")
new1 = ("          '补充的非线性与条件效应检验同样不支持'\n"
        "          '（加入全部行为指标后，二次项与交互项均失去显著性）。'")
if s.count(old1) == 1:
    s = s.replace(old1, new1)
    print('[2] AS 段落已精简（净 %+d 字）' % (len(new1) - len(old1)))
else:
    print('[2] MISS(%d): AS 段落' % s.count(old1))

# ---------- 3) 补入成分级相关 ----------
old2 = ('          f\'其与 L4 过程应对相关 '
        '{CP["S2_维度相关"]["交易执行能力"]["风险应对能力"]:.3f}，信息被吸收；\'')
new2 = ('          f\'其与 L4 过程应对维度相关 '
        '{CP["S2_维度相关"]["交易执行能力"]["风险应对能力"]:.3f}、\'\n'
        '          f\'成分层面 SDI 与 ARG 相关达 {CH["关键跨层相关"]["ARG_x_SDI"]:+.2f}，信息被吸收；\'')
if s.count(old2) == 1:
    s = s.replace(old2, new2)
    print('[3] 已补入成分级相关（净 %+d 字）' % (len(new2) - len(old2)))
else:
    print('[3] MISS(%d): 成分级相关' % s.count(old2))

io.open(P, 'w', encoding='utf-8').write(s)
print('\n补丁已写入', P)
