# -*- coding: utf-8 -*-
"""论文核心配图（2026-08-26 数据 · 2026-08-31 第二轮精修版）
================================================================================
图 1  综合能力五分组的 FF5 alpha —— 单色蓝渐变 + 横排统计条
图 2  六维相关热力图 —— 弱化对角线 + 紧凑 colorbar
图 3  五名正向典型 + 反例雷达 —— 统一刻度角 + α 正负色点 + 紧凑排版

第二轮精修（在第一轮学术风格基础上）：
  · 图 1：统计注释改为标题下横排一行；去 y 轴刻度线；柱内加极淡垂直渐变
  · 图 2：对角线弱化为描边样式；colorbar 收窄；注释行加引导符
  · 图 3：径向刻度统一角度；α 正负用色点区分；网格减淡；hspace 收紧
数据源只读不重算，与 2026-08-26 定稿 JSON 完全一致。
"""
import json
import os
import io
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.lines import Line2D

BASE = r'd:\Desktop\基金经理行为分析研究'
OUT = os.path.join(BASE, 'output')
FIG = os.path.join(BASE, 'figures')
TODAY = '2026-08-26'
os.makedirs(FIG, exist_ok=True)

# ---------- 统一设计系统 ----------
PRIMARY = '#1f4e79'
ACCENT = '#c9a227'
NEG = '#b0413e'          # 负 α 用红棕
GRID = '#e8edf3'
TEXT_DARK = '#1e293b'
TEXT_MUTED = '#64748b'

plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei']
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['font.size'] = 10.5
plt.rcParams['axes.edgecolor'] = TEXT_MUTED
plt.rcParams['axes.linewidth'] = 0.8
plt.rcParams['xtick.color'] = TEXT_DARK
plt.rcParams['ytick.color'] = TEXT_DARK
plt.rcParams['text.color'] = TEXT_DARK
plt.rcParams['axes.labelcolor'] = TEXT_DARK


def rj(name):
    with io.open(os.path.join(OUT, name), encoding='utf-8') as f:
        return json.load(f)


CP = rj(f'六维复合定稿验证_含L1_{TODAY}.json')
PT = rj(f'画像_群体与典型_{TODAY}.json')
S4 = CP['S4_分组']
DIMS = ['基本面优势', '认知能力', '配置选择能力', '风险应对能力',
        '风险转化能力', '交易执行能力']
SHORT = {'基本面优势': 'L1\n基本面特征', '认知能力': 'L2\n认知', '配置选择能力': 'L3\n配置选择',
         '风险应对能力': 'L4a\n风险应对', '风险转化能力': 'L4b\n风险转化',
         '交易执行能力': 'L5\n交易执行'}

# ============================== 图 1 ==============================
g = ['Q1最低', 'Q2', 'Q3', 'Q4', 'Q5最高']
vals = [S4['alpha均值'][k] * 100 for k in g]
labels = ['Q1\n最低', 'Q2', 'Q3', 'Q4', 'Q5\n最高']

grad = ['#c5d5e8', '#9cb8d6', '#6f99c4', '#4179b3', '#1f4e79']

fig, ax = plt.subplots(figsize=(7.4, 4.5))
fig.patch.set_facecolor('white')
ax.set_facecolor('white')

# 柱体：纯色 + 内嵌高亮（精确对齐柱体，右侧留 8% 渐变感）
bars = ax.bar(labels, vals, color=grad, width=0.60, edgecolor='none', zorder=3)
for b, v in zip(bars, vals):
    ax.bar(b.get_x() + b.get_width() * 0.08, v * 0.92,
           width=b.get_width() * 0.92,
           color='white', alpha=0.10, edgecolor='none', zorder=4)
bars[-1].set_edgecolor(ACCENT)
bars[-1].set_linewidth(1.6)

for b, v in zip(bars, vals):
    ax.text(b.get_x() + b.get_width() / 2, v + 0.07, f'{v:.2f}%',
            ha='center', va='bottom', fontsize=10.5, fontweight='bold',
            color=PRIMARY)

ax.axhline(0, color=TEXT_MUTED, lw=0.8, zorder=2)
ax.set_ylabel('FF5 超额收益（%／季）', fontsize=11)
ax.set_ylim(0, max(vals) * 1.30)
ax.spines[['top', 'right', 'left']].set_visible(False)
ax.spines['bottom'].set_color(TEXT_MUTED)
ax.tick_params(axis='y', length=0, labelsize=10)
ax.tick_params(axis='x', length=0, labelsize=10.5)
ax.yaxis.grid(True, color=GRID, lw=0.8, zorder=0)
ax.set_axisbelow(True)

# 标题与统计条均用 fig.text 绝对定位，互不遮挡
fig.text(0.5, 0.955,
         '按综合能力五等分的组合超额收益（全样本 %d 只基金）'
         % sum(S4['规模'][k] for k in g),
         ha='center', fontsize=13, fontweight='bold', color=TEXT_DARK)
fig.text(0.5, 0.868,
         f'Q5−Q1 = {S4["Q5_Q1"]*100:.2f} 个百分点／季   ·   t = {S4["t"]:.2f}   ·   p < 0.001   ·   逐组严格单调递增',
         ha='center', fontsize=10, color=PRIMARY,
         bbox=dict(boxstyle='round,pad=0.42', fc='#fffaf0', ec=ACCENT, lw=0.9))

fig.subplots_adjust(top=0.80, left=0.10, right=0.97, bottom=0.10)
p1 = os.path.join(FIG, '论文图1_五分组alpha.png')
fig.savefig(p1, dpi=300, facecolor='white')
plt.close(fig)
print('saved:', p1)

# ============================== 图 2 ==============================
S2 = CP['S2_维度相关']
M = np.array([[S2[a][b] for b in DIMS] for a in DIMS])
short = [SHORT[d] for d in DIMS]

fig, ax = plt.subplots(figsize=(7.0, 5.8))
fig.patch.set_facecolor('white')

im = ax.imshow(np.where(M == 1, np.nan, M), cmap='Blues', vmin=0, vmax=0.8,
               aspect='equal')
# 对角线单元格单独画成描边样式（弱化为"结构"而非"数据"）
for k in range(6):
    ax.add_patch(plt.Rectangle((k - 0.5, k - 0.5), 1, 1, fill=False,
                               edgecolor=PRIMARY, linewidth=1.4, alpha=0.55))

ax.set_xticks(range(6))
ax.set_xticklabels(short, fontsize=9.5, linespacing=1.4)
ax.set_yticks(range(6))
ax.set_yticklabels(short, fontsize=9.5, linespacing=1.4)
ax.tick_params(length=0)

ax.set_xticks(np.arange(-0.5, 6, 1), minor=True)
ax.set_yticks(np.arange(-0.5, 6, 1), minor=True)
ax.grid(which='minor', color='white', linewidth=1.6)
ax.tick_params(which='minor', length=0)

for i in range(6):
    for j in range(6):
        v = M[i, j]
        if v == 1:
            ax.text(j, i, '1', ha='center', va='center', fontsize=10,
                    color=PRIMARY, alpha=0.55)
        else:
            ax.text(j, i, f'{v:.3f}'.rstrip('0').rstrip('.'),
                    ha='center', va='center', fontsize=10,
                    color='white' if v > 0.45 else PRIMARY,
                    fontweight='bold' if v > 0.50 else 'normal')

ax.set_title('六个计分维度的两两相关（基金层，N=362）',
             fontsize=13, pad=14, fontweight='bold', color=TEXT_DARK)

cbar = fig.colorbar(im, ax=ax, shrink=0.72, pad=0.025, aspect=24)
cbar.set_label('相关系数', fontsize=10)
cbar.ax.tick_params(labelsize=9)
cbar.outline.set_linewidth(0.6)
cbar.outline.set_edgecolor(TEXT_MUTED)

fig.text(0.13, 0.015,
         '■ 非对角线最大 0.629（风险应对与认知能力，远低于 0.8 共线警戒）；L4a×L4b 仅 0.418 —— 两职能分开计分的直接依据；□ 描边格为对角线',
         fontsize=8.8, color=TEXT_MUTED, ha='left')

fig.tight_layout(rect=[0, 0.045, 1, 1])
p2 = os.path.join(FIG, '论文图2_维度相关热力图.png')
fig.savefig(p2, dpi=300, facecolor='white', bbox_inches='tight')
plt.close(fig)
print('saved:', p2)

# ============================== 图 3 ==============================
# 第六轮重设计：标签全部外移圆外 + 白底阴影卡片 + 类型彩色芯片 + 大留白
from matplotlib.patches import FancyBboxPatch, Patch
from matplotlib.colors import to_rgba

ARCH = PT['典型画像']
tag_short = [c['标签'].split('：')[0] for c in ARCH]
n = len(DIMS)
theta = np.linspace(0, 2 * np.pi, n, endpoint=False)
theta_c = np.concatenate([theta, theta[:1]])
degs = np.degrees(theta)

# 六类画像主题色（区分类型，和谐色板）
TYPE_COLORS = ['#2563eb',  # 全能型·蓝
               '#0891b2',  # 风险定价型·青
               '#0d9488',  # 认知纪律型·teal
               '#d97706',  # 攻守转换型·琥珀
               '#7c3aed',  # 基本面优势型·紫
               '#94a3b8']  # 反例·石板灰
POS_GREEN = '#16a34a'
NEG_RED = '#dc2626'
CARD_BG = '#ffffff'
CARD_EDGE = '#e3e9f2'
SHADOW = '#e9eef5'
RING_GRID = '#e9eff6'
SPOKE_GRID = '#f0f4f9'

DIM_NAMES = ['基本面', '认知', '配置选择', '风险应对', '风险转化', '交易执行']


def label_anchor(deg):
    """极坐标角度（北=0，顺时针）→ 圆外标签对齐方式。"""
    if deg == 0:
        return 'center', 'bottom'
    if deg == 180:
        return 'center', 'top'
    return ('left' if 0 < deg < 180 else 'right'), 'center'


fig = plt.figure(figsize=(13.4, 11.8))
fig.patch.set_facecolor('white')

# ---- 手工布局：卡片与雷达轴精确几何，保证标签落在卡内留白区 ----
CARD_W, CARD_H = 0.296, 0.332
CARD_X = [0.034, 0.352, 0.670]    # 三列卡片左缘
CARD_Y = [0.540, 0.148]           # 上行 / 下行卡片底缘
AX_SIDE = 0.172                   # 雷达轴边长（正方形）
R_LABEL = 1.135                   # 维度标签半径（圆外）

for idx, (c, tg, col) in enumerate(zip(ARCH, tag_short, TYPE_COLORS)):
    row, colx = divmod(idx, 3)
    x0, y0 = CARD_X[colx], CARD_Y[row]
    cx, cy1 = x0 + CARD_W / 2, y0 + CARD_H

    # --- 卡片：柔影 + 白底圆角 ---
    fig.patches.append(FancyBboxPatch(
        (x0 + 0.004, y0 - 0.004), CARD_W, CARD_H,
        boxstyle='round,pad=0.006,rounding_size=0.018',
        transform=fig.transFigure, facecolor=SHADOW, edgecolor='none',
        zorder=0, clip_on=False))
    fig.patches.append(FancyBboxPatch(
        (x0, y0), CARD_W, CARD_H,
        boxstyle='round,pad=0.006,rounding_size=0.018',
        transform=fig.transFigure, facecolor=CARD_BG, edgecolor=CARD_EDGE,
        linewidth=1.2, zorder=1, clip_on=False))

    # --- 雷达轴（卡片中下区）---
    ax = fig.add_axes([cx - AX_SIDE / 2, y0 + 0.036, AX_SIDE, AX_SIDE],
                      polar=True, zorder=2)
    ax.set_facecolor('none')
    ax.set_theta_zero_location('N')
    ax.set_theta_direction(-1)
    ax.set_thetagrids(degs, [''] * n)
    ax.set_ylim(0, 1.0)
    ax.set_yticks([0.25, 0.50, 0.75, 1.00])
    ax.set_yticklabels([])
    ax.tick_params(length=0)
    ax.yaxis.grid(True, color=RING_GRID, lw=0.9)
    ax.xaxis.grid(True, color=SPOKE_GRID, lw=0.9)
    ax.spines['polar'].set_color('#d7dfe9')
    ax.spines['polar'].set_linewidth(1.1)

    vals = [max(c['六维分位'].get(d) or 0.0, 0.0) for d in DIMS]
    vals_c = vals + vals[:1]

    # 50% 中位参考环
    ax.plot(np.linspace(0, 2 * np.pi, 200), [0.5] * 200,
            color=ACCENT, lw=1.4, ls=(0, (4, 3)), alpha=0.65, zorder=1)

    # 主多边形：白描边浮起 + 主题色描边 + 淡填充
    ax.plot(theta_c, vals_c, color='white', lw=5.5, zorder=3,
            solid_joinstyle='round')
    ax.plot(theta_c, vals_c, color=col, lw=2.6, zorder=3.2,
            solid_joinstyle='round')
    ax.fill(theta_c, vals_c, color=col, alpha=0.15, zorder=2.5)

    # 顶点圆点（低分顶点省略，避免圆心墨团）
    for ang, v in zip(theta, vals):
        if v >= 0.12:
            ax.scatter([ang], [v], s=46, color=col, zorder=4,
                       edgecolors='white', linewidths=1.4)

    # 维度标签：圆外，单行深色，不再与图形压盖
    for deg, name in zip(degs, DIM_NAMES):
        ha, va = label_anchor(deg)
        ax.text(np.radians(deg), R_LABEL, name, ha=ha, va=va, fontsize=12.5,
                color=TEXT_DARK, clip_on=False, zorder=6)

    # --- 卡内标题区：类型芯片 / 基金名 / α 行 ---
    fig.text(cx, cy1 - 0.026, tg, ha='center', va='center', fontsize=13.5,
             fontweight='bold', color=col, zorder=6,
             bbox=dict(boxstyle='round,pad=0.50',
                       fc=to_rgba(col, 0.12), ec=to_rgba(col, 0.45),
                       lw=1.1))
    fname = c['基金简称']
    if len(fname) > 13:
        fname = fname[:12] + '…'
    fig.text(cx, cy1 - 0.056, fname, ha='center', va='center', fontsize=12.5,
             fontweight='bold', color=TEXT_DARK, zorder=6)
    alpha_val = c['ff5_alpha']
    a_col = POS_GREEN if alpha_val > 0 else NEG_RED
    pct = c.get('综合能力分位')
    a_line = f'α = {alpha_val:+.2%}'
    if pct is not None:
        a_line += f'　·　综合分位 {pct:.0%}'
    fig.text(cx, cy1 - 0.082, a_line, ha='center', va='center', fontsize=12,
             fontweight='bold', color=a_col, zorder=6)

# ---- 页眉：主标题 + 金色短饰线 + 副题（与卡片拉开间距）----
fig.text(0.5, 0.978, '典型投资经理的六维能力雷达图',
         ha='center', va='top', fontsize=19, fontweight='bold',
         color=TEXT_DARK)
fig.add_artist(Line2D([0.470, 0.530], [0.949, 0.949],
                      color=ACCENT, lw=2.2, transform=fig.transFigure))
fig.text(0.5, 0.928, '数值为全样本百分位；金色虚线为 50% 中位参考环',
         ha='center', va='top', fontsize=11.5, color=TEXT_MUTED)

# ---- 页脚图例 ----
legend_elems = [
    Line2D([0], [0], marker='o', color='none', markerfacecolor=POS_GREEN,
           markersize=9, label='α > 0（正超额）'),
    Line2D([0], [0], marker='o', color='none', markerfacecolor=NEG_RED,
           markersize=9, label='α < 0（负超额）'),
    Line2D([0], [0], color=ACCENT, lw=1.6, ls=(0, (4, 3)),
           label='50% 中位参考环'),
    Patch(facecolor=to_rgba('#64748b', 0.18), edgecolor='#64748b',
          linewidth=1.6, label='经理六维能力轮廓（百分位）'),
]
fig.legend(handles=legend_elems, loc='lower center', ncol=4,
           fontsize=11, frameon=False, bbox_to_anchor=(0.5, 0.055),
           columnspacing=2.0, handlelength=1.8, handletextpad=0.6)

p3 = os.path.join(FIG, '论文图3_典型经理雷达图.png')
fig.savefig(p3, dpi=300, facecolor='white')
plt.close(fig)
print('saved:', p3)
print('三张论文配图完成（第六轮：标签外移 + 白底阴影卡片重设计）')
