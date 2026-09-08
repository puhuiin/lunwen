# Generate redesigned 6-axis behavior radar SVG for the literature-review case study.
# Fixes: replace redundant "行业聚焦"(约等于集中度) with "主动份额 AS" (distinct, canonical).
# 6 distinct manager colors; ordinal 1-5; explicit collinearity/honesty note added in HTML.

import math

# axes (clockwise from top)
axes = ["集中度", "行业偏离", "主动份额", "换手率", "持股周期", "风险偏好"]
n = len(axes)
R = 64  # outer radius

# per-manager centers: top row y=118, bottom row y=353
managers = [
    # name, color, cx, cy, [v1..v6]
    ("张坤",   "#2e7d8a", 120, 118, [4,4,4,2,5,4]),
    ("朱少醒", "#1f6b3a", 340, 118, [3,2,5,1,5,3]),
    ("葛兰",   "#9a3412", 560, 118, [5,5,5,3,3,5]),
    ("蔡嵩松", "#7c3aed", 120, 353, [4,5,5,5,2,5]),
    ("巴菲特", "#1f4e79", 340, 353, [5,3,5,1,5,2]),
    ("林奇",   "#be123c", 560, 353, [1,1,1,4,2,4]),
]

def axis_vec(i):
    ang = math.radians(-90 + i*60)
    return math.cos(ang), math.sin(ang)

def pt(cx, cy, i, v):
    dx, dy = axis_vec(i)
    r = R * v / 5.0
    return (cx + r*dx, cy + r*dy)

svg = []
svg.append('<svg viewBox="0 0 680 470" width="100%" xmlns="http://www.w3.org/2000/svg" font-family="Segoe UI,PingFang SC,Microsoft YaHei,sans-serif">')

for name, color, cx, cy, vals in managers:
    # grid hexagons at 1/5..5/5
    for k in range(1,6):
        rr = R*k/5.0
        pts = []
        for i in range(n):
            dx, dy = axis_vec(i)
            pts.append(f"{cx+rr*dx:.1f},{cy+rr*dy:.1f}")
        stroke = "#cbd5e1" if k==5 else "#e3e8ef"
        svg.append(f'<polygon points="{" ".join(pts)}" fill="none" stroke="{stroke}" stroke-width="1"/>')
    # axis spokes + labels
    label_off = R + 16
    for i in range(n):
        dx, dy = axis_vec(i)
        ex, ey = cx+label_off*dx, cy+label_off*dy
        svg.append(f'<line x1="{cx}" y1="{cy}" x2="{cx+R*dx:.1f}" y2="{cy+R*dy:.1f}" stroke="#dde3ea" stroke-width="1"/>')
        if i==0:
            anc="middle"; tx,ty = ex, ey-4
        elif i==3:
            anc="middle"; tx,ty = ex, ey+14
        elif i in (1,2):
            anc="start"; tx,ty = ex+4, ey
        else:
            anc="end"; tx,ty = ex-4, ey
        svg.append(f'<text x="{tx:.1f}" y="{ty:.1f}" font-size="10.5" fill="#5b6b7b" text-anchor="{anc}" dominant-baseline="auto">{axes[i]}</text>')
    # data polygon
    dpts=[]
    for i in range(n):
        x,y = pt(cx,cy,i,vals[i])
        dpts.append(f"{x:.1f},{y:.1f}")
    svg.append(f'<polygon points="{" ".join(dpts)}" fill="{color}33" stroke="{color}" stroke-width="2"/>')
    for i in range(n):
        x,y = pt(cx,cy,i,vals[i])
        svg.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2.6" fill="{color}"/>')
    # name label
    svg.append(f'<text x="{cx}" y="{cy-R-30:.1f}" font-size="13.5" font-weight="700" fill="{color}" text-anchor="middle">[{name}]</text>')

svg.append('</svg>')
out = "\n".join(svg)
with open(r"D:\Desktop\基金经理行为分析研究\_radar_svg.txt","w",encoding="utf-8") as f:
    f.write(out)
print(out)
print("\n--- length:", len(out))
