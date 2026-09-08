# -*- coding: utf-8 -*-
"""体系 A 卡片墙改造（2026-08-30）

把根目录《基金经理能力画像与业绩评价.html》的案例卡片墙，由
  旧六维（行业配置力/风险应对力/主动收益力/投资纪律性/风险转化力/成本控制力）
  + 六位文献案例经理（张坤/朱少醒/葛兰/蔡嵩松/巴菲特/林奇，均不在样本内、数值为 1-5 定性序数）
改为体系 B 最新口径：
  新六维（基本面优势/认知能力/配置选择/风险应对/风险转化/交易执行）
  + 论文图 3 的六个样本内真实案例（取自 画像_典型经理_2026-08-26.csv）
  + 数值为 362 只样本基金中的实测百分位（0-100），非定性估计。

说明：页面其余部分（L1–L5 五层雷达图等）口径不同，本脚本不改，仅在卡片墙前加口径说明。
"""
import io
import os
import re

import pandas as pd

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HTML = os.path.join(BASE, '基金经理能力画像与业绩评价.html')
CSV = os.path.join(BASE, 'output', '画像_全样本能力表_2026-08-26.csv')
TYP = os.path.join(BASE, 'output', '画像_典型经理_2026-08-26.csv')

DIM = ['基本面优势', '认知能力', '配置选择能力', '风险应对能力', '风险转化能力', '交易执行能力']
SHORT = ['基本面优势', '认知能力', '配置选择', '风险应对', '风险转化', '交易执行']
NL = chr(10)


def rd(p):
    with io.open(p, encoding='utf-8') as f:
        return f.read()


def wr(p, s):
    with io.open(p, 'w', encoding='utf-8') as f:
        f.write(s)


def find_block(s, start_tag):
    """从 start_tag 起，按 <div> / </div> 配平找到块结束位置（返回 end 索引）。"""
    i = s.find(start_tag)
    if i < 0:
        return -1, -1
    depth = 0
    pos = i
    tag_re = re.compile(r'<div\b|</div>')
    while True:
        m = tag_re.search(s, pos)
        if not m:
            return i, -1
        if m.group(0) == '</div>':
            depth -= 1
            if depth == 0:
                return i, m.end()
        else:
            depth += 1
        pos = m.end()


def main():
    t = rd(HTML)
    colors = re.findall(r'<div class="mcard" style="border-top:4px solid (#[0-9A-Fa-f]{6})">', t)
    if len(colors) != 6:
        print('[FAIL] 期望 6 张卡片配色，实得 %d，中止' % len(colors))
        return 2

    df = pd.read_csv(CSV, encoding='utf-8-sig')
    typ = pd.read_csv(TYP, encoding='utf-8-sig')
    pct = df.set_index('fund_code')[DIM].rank(pct=True) * 100
    info = df.set_index('fund_code')[['基金简称', '基金经理人']]

    # ---------------- 生成新卡片墙 ----------------
    rows = ['<div class="mcard-grid">']
    for i, r in typ.iterrows():
        code = r['fund_code']
        c = colors[i]
        tag = str(r['标签']).split('：')[0]
        mgr = info.loc[code, '基金经理人']
        fund = info.loc[code, '基金简称']
        rows.append('<div class="mcard" style="border-top:4px solid %s">' % c)
        rows.append('      <div class="mcard-head"><span class="mcard-name" style="color:%s">%s</span>'
                    '<span class="mcard-tag">%s</span></div>' % (c, mgr, tag))
        rows.append('      <div class="msig">')
        for d, sname in zip(DIM, SHORT):
            v = pct.loc[code, d]
            w = max(2.0, min(100.0, v))
            rows.append(
                '<div class="msig-row"><span class="msig-lab">%s</span>'
                '<span class="msig-track"><span class="msig-fill" style="width:%.1f%%;background:%s">'
                '</span></span><span class="msig-val">%d</span></div>' % (sname, w, c, round(v)))
        rows.append('</div>')
        rows.append('      <div class="mcard-foot" style="font-size:11.5px;color:#64748b;'
                    'margin-top:6px">%s　综合能力分位 %d</div>'
                    % (fund, round(float(r['综合能力分位']) * 100)))
        rows.append('</div>')
    rows.append('</div>')
    new_grid = NL.join(rows)

    # ---------------- 替换卡片墙 ----------------
    i0, i1 = find_block(t, '<div class="mcard-grid">')
    if i0 < 0 or i1 < 0:
        print('[FAIL] 未定位到 mcard-grid 块，中止')
        return 2
    t = t[:i0] + new_grid + t[i1:]
    print('[OK] 卡片墙已替换（%d 字符）' % len(new_grid))

    # ---------------- 替换说明文字 ----------------
    # 页面有多处 <p class="lead">，只替换卡片墙之前最近的那一个
    gi = t.find('<div class="mcard-grid">')
    ms = list(re.compile(r'<p class="lead">.*?</p>', re.S).finditer(t[:gi]))
    if not ms:
        print('[FAIL] 卡片墙前未找到 lead 段落，中止')
        return 2
    m = ms[-1]
    new_lead = ('下方按论文最新口径，从样本内 400 只基金中选出<b>六个典型投资经理</b>'
                '（与论文图 3 一致），按体系 B 六维——'
                '基本面优势、认知能力、配置选择、风险应对、风险转化、交易执行——'
                '展示各自在 <b>362 只样本基金中的实测百分位</b>（0–100，越高越强）。'
                '此处数值为复合得分的实测分位，非定性估计；'
                '案例依综合能力由高到低排列，末位为反例。')
    t = t[:m.start()] + '<p class="lead">' + new_lead + '</p>' + t[m.end():]
    print('[OK] 说明文字已替换（卡片墙前共 %d 个 lead，取最后一个）' % len(ms))

    # 标题同步：序数画像速览 -> 实测分位速览
    t = t.replace('经理行为画像卡片墙（六位案例 · 序数画像速览）',
                  '经理行为画像卡片墙（六个样本内案例 · 六维实测分位）', 1)
    print('[OK] 标题已同步')

    # ---------------- 插入口径说明 ----------------
    notice = NL.join([
        '<div style="background:#fff7ed;border-left:4px solid #d97706;padding:10px 14px;',
        'margin:10px 0 14px;border-radius:6px;font-size:13px;line-height:1.7">',
        '<b>口径说明（2026-08-30 更新）</b>：本卡片墙已改为论文体系 B 的最新六维口径，',
        '案例为样本内真实基金、数值为实测百分位。',
        '本页其余部分（如 L1–L5 五层关联强度雷达图）沿用早期的展示口径，',
        '其“五层”与体系 B 的“六维”不是同一套划分，请勿直接对照。</div>',
    ])
    anchor = '<h3 class="cw-title">经理行为画像卡片墙（六个样本内案例 · 六维实测分位）</h3>'
    if anchor in t and '口径说明（2026-08-30 更新）' not in t:
        t = t.replace(anchor, notice + anchor, 1)
        print('[OK] 已插入口径说明')

    wr(HTML + '.bak_20260830', rd(HTML))
    wr(HTML, t)
    print('[DONE] 已写入 %s（备份 .bak_20260830）' % os.path.basename(HTML))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
