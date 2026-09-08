# -*- coding: utf-8 -*-
# 生成「经理行为画像卡片墙」HTML 片段（6 位案例经理，基于文献综述雷达序数数据）。
# 轴序: [集中度, 行业偏离, 主动份额AS, 换手率, 持股周期, 风险偏好]  (1=低 .. 5=极高)
MGR = [
    ("张坤",   "#2e7d8a", [4,4,4,2,5,4], "深度价值·蓝筹集中", "高集中度+高行业偏离+长持股+低换手，均衡偏防守；典型'少而精'长期持有型。"),
    ("朱少醒", "#1f6b3a", [3,2,5,1,5,3], "长期自下而上", "低行业偏离+极高主动份额+极低换手+长持股，分散均衡的选股型。"),
    ("葛兰",   "#9a3412", [5,5,5,3,3,5], "赛道集中·高信念", "医药赛道高集中+高偏离+中换手，高信念高波动的成长型。"),
    ("蔡嵩松", "#7c3aed", [4,5,5,5,2,5], "科技轮动·高频", "极高行业偏离+高主动份额+高换手+短持股，赛道高频轮动型。"),
    ("巴菲特", "#1f4e79", [5,3,5,1,5,2], "价值集中·超长持", "高集中度+高主动份额+极低换手+超长持股+低风险，经典价值型。"),
    ("林奇",   "#be123c", [1,1,1,4,2,4], "分散灵活·多策略", "低集中+低偏离+高换手+短持股，分散灵活的多策略型。"),
]
AXES = ["集中度","行业偏离","主动份额","换手率","持股周期","风险偏好"]
cards = []
for name, color, vals, tag, desc in MGR:
    rows = ""
    for v_i, v in enumerate(vals):
        pct = v/5*100
        rows += (f'<div class="msig-row"><span class="msig-lab">{AXES[v_i]}</span>'
                 f'<span class="msig-track"><span class="msig-fill" style="width:{pct:.0f}%;background:{color}"></span></span>'
                 f'<span class="msig-val">{v}</span></div>')
    cards.append(f'''<div class="mcard" style="border-top:4px solid {color}">
      <div class="mcard-head"><span class="mcard-name" style="color:{color}">{name}</span><span class="mcard-tag">{tag}</span></div>
      <div class="msig">{rows}</div>
      <p class="mcard-desc">{desc}</p>
    </div>''')

html = f'''<h3 class="cw-title">经理行为画像卡片墙（六位案例 · 序数画像速览）</h3>
<p class="lead">下方把文献综述中的六位案例经理，按「集中度 / 行业偏离 / 主动份额 / 换手率 / 持股周期 / 风险偏好」六轴序数（1=低 → 5=极高，基于公开披露定性映射，非精确度量）做成可一眼比较的画像卡片。卡片越长表示该维度行为越突出；颜色对应各经理专属配色，与文献综述雷达一致。</p>
<div class="mcard-grid">
{''.join(cards)}
</div>
<div class="box note" style="margin-top:16px">
<b>读法：</b>横向比卡片，能立刻看出经理"行为家族"差异——<b>张坤/巴菲特</b>是"集中+长持+低换手"的价值派；<b>蔡嵩松/葛兰</b>是"高偏离+高换手+高波动"的赛道派；<b>林奇</b>则是"分散+高换手"的灵活派。这与第 7 章雷达图（L2 持仓偏离 / L3 交易执行 / L5 认知偏差）的维度口径一致，可作为"画像分型"的直观入口。序数刻画仅为定性画像载体，精确数值请以面板回归证据为准。
</div>'''

with open(r"D:/Desktop/基金经理行为分析研究/_cards_out.html", "w", encoding="utf-8") as f:
    f.write(html)
print("cards written, bytes:", len(html))
