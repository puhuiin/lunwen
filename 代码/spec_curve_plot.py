# -*- coding: utf-8 -*-
"""规范曲线图：每个L5指标一个面板，52个设定按系数排序，95%CI，显著性着色，家族分区"""
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import os

outdir = r'D:\Desktop\基金经理行为分析研究\figures'
os.makedirs(outdir, exist_ok=True)

# v3 诚实面板重算结果（spec_curve.py 输出）
r = pd.read_csv(outdir + r'\spec_curve_results.csv')
fam_order = {'cross_section': 0, 'forward': 1, 'within': 2}
fam_label = {'cross_section': 'Cross-section',
             'forward': 'Forward prediction', 'within': 'Within (two-way FE)'}
r['fam_o'] = r['family'].map(fam_order)

panels = [('risk_asym', 'RiskAsym'), ('lsv', 'LSV'), ('de', 'DE')]
fig, axes = plt.subplots(3, 1, figsize=(10, 9), sharex=True)

for ax, (k, lab) in zip(axes, panels):
    d = r.sort_values(['fam_o', f'b_{k}']).reset_index(drop=True)
    # CI from t and p: se = |b/t|
    b = d[f'b_{k}'].values
    t = d[f't_{k}'].values
    se = np.where(np.abs(t) > 1e-9, np.abs(b) / np.abs(t), np.nan)
    lo, hi = b - 1.96 * se, b + 1.96 * se
    sig = d[f'p_{k}'].values < 0.05
    x = np.arange(len(d))
    # family shading + separators
    starts = d.groupby('fam_o', observed=True).apply(lambda g: g.index.min())
    ends = d.groupby('fam_o', observed=True).apply(lambda g: g.index.max())
    colors_bg = ['#f2f6fc', '#fdf6ec', '#f0f7f0']
    for i, (fo, st) in enumerate(starts.items()):
        ax.axvspan(st - 0.5, ends[fo] + 0.5, color=colors_bg[int(fo)], zorder=0)
        if i > 0:
            ax.axvline(st - 0.5, color='#888', lw=0.8, ls='--', zorder=1)
    # CIs
    for xi, l, h, s in zip(x, lo, hi, sig):
        ax.plot([xi, xi], [l, h], color=('#1f77b4' if s else '#bbbbbb'), lw=0.8, alpha=0.85, zorder=2)
    # points
    ax.scatter(x[sig], b[sig], s=14, color='#d62728', zorder=4, label='p < 0.05')
    ax.scatter(x[~sig], b[~sig], s=14, color='#7f7f7f', zorder=3, label='p >= 0.05')
    ax.axhline(0, color='k', lw=0.9, zorder=1)
    m = np.nanmedian(b)
    ax.axhline(m, color='#1f77b4', lw=1.0, ls=':', zorder=1)
    ax.text(len(d) - 0.5, m, f' median={m:+.4f}', va='bottom', fontsize=8, color='#1f77b4')
    # family x labels at centers
    for fo, st in starts.items():
        ax.text((st + ends[fo]) / 2, ax.get_ylim()[0], '', ha='center')
    ax.set_ylabel('Coefficient')
    n_tot = len(d)
    ax.set_title(f'{lab}: {int(sig.sum())}/{n_tot} significant  |  '
                 f'{int((np.sign(b) == np.sign(np.nanmedian(b))).sum())}/{n_tot} same sign as median',
                 fontsize=10)
    ax.legend(loc='upper left', fontsize=8, framealpha=0.6)

# x-axis family labels
axb = axes[-1]
axb.set_xlabel('Specifications (sorted within each family)')
ticks, ticklabs = [], []
for fo, st in starts.items():
    ticks.append((st + ends[fo]) / 2)
    ticklabs.append({'cross_section': 'Cross-section',
                     'forward': 'Forward', 'within': 'Within'}[d.loc[st, 'family']])
axb.set_xticks(ticks)
axb.set_xticklabels(ticklabs, fontsize=9, rotation=0)
axb.set_xlim(-0.5, len(r) - 0.5)

fig.suptitle('Specification Curve: 60 Justifiable Specifications across Three Identification Families',
             fontsize=11, y=0.995)
fig.tight_layout(rect=[0, 0, 1, 0.985])
fig.savefig(outdir + r'\spec_curve.png', dpi=150)
print('saved', outdir + r'\spec_curve.png')
