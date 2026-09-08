# -*- coding: utf-8 -*-
"""按用户要求删除两处句子：
(1) 画像/报告 中"持仓快照能否增加 school 覆盖"的句子（用户原问的是 TO 覆盖，非 school）；
(2) 画像 L3 中"换手采用单边来提高覆盖率再回归"的用户问题 + 单边覆盖率诊断 + 买卖分解回归（只用双边 TO）。
持仓快照"能否扩大 TO 覆盖"的正确结论保留。
"""
base="D:/Desktop/基金经理行为分析研究/"

def slice_del(html, start_marker, end_marker, label, consume_nl=True):
    s=html.find(start_marker)
    if s<0:
        print("FAIL start:",label); return html,False
    e=html.find(end_marker,s)
    if e<0:
        print("FAIL end:",label); return html,False
    e+=len(end_marker)
    if consume_nl and html[e:e+1]=="\n": e+=1
    html=html[:s]+html[e:]
    return html,True

# ===== 画像 HTML =====
F=base+"基金经理能力画像与业绩评价.html"
h=open(F,encoding="utf-8").read()
ok=True

# (1) school 覆盖 li
h,o1=slice_del(h,'<li><b>持仓快照能增加 school 覆盖吗？——不能。</b>',
              '即"覆盖上限"规划项。</li>',"profile-school-li")
ok&=o1

# (2a) 用户问题 + 单边覆盖率诊断 + 做了一次回归 para
h,o2=slice_del(h,'<h3>用户问题：换手能不能"采用单边"来提高覆盖率，然后做一次回归？</h3>',
              '买卖不对称：</p>',"profile-unilateral-q")
ok&=o2

# (2b) ③ 回归设定 分解 行
import re
h2=re.sub(r'<span class="lbl">分解:</span>.*?\n','',h,count=1)
if h2!=h:
    h=h2
else:
    print("FAIL 分解行未匹配")

# (2c) ③ 回归设定 heading
h=h.replace('③ 回归设定（L3 截面基准 + 买卖分解）','③ 回归设定（L3 截面基准）')

# (2d) ③-b 表 TO_buy / TO_sell 行
h=h.replace('<tr><td>买侧换手<br><code>TO_buy</code></td><td>买入活跃度</td><td>total_buy/aum</td><td>单边买入额÷aum</td><td>比值</td><td>分解买卖不对称</td><td class="num">≈0 (2.01)**</td><td><span class="sigx">正、量级极小</span></td></tr>\n','')
h=h.replace('<tr><td>卖侧换手<br><code>TO_sell</code></td><td>卖出活跃度</td><td>total_sell/aum</td><td>单边卖出额÷aum</td><td>比值</td><td>分解买卖不对称</td><td class="num">≈0 (−2.15)**</td><td><span class="sign">负、量级极小</span></td></tr>\n','')

# (2e) 买卖分解洞见 box
i=h.find('<b>买卖分解的洞见：</b>')
if i>=0:
    div_start=h.rfind('<div class="box note">',0,i)
    end_marker='更有解释力。\n</div>'
    e=h.find(end_marker,i)
    if e>=0:
        e+=len(end_marker)
        if h[e:e+1]=="\n": e+=1
        h=h[:div_start]+h[e:]
    else:
        print("FAIL 买卖分解洞见 end")
else:
    print("FAIL 买卖分解洞见 start")

open(F,"w",encoding="utf-8").write(h)
print("PROFILE ok=%s len=%d"%(ok,len(h)))

# ===== 报告 HTML =====
F2=base+"实证结果完整报告与论文写作指南.html"
h2=open(F2,encoding="utf-8").read()
h2,o3=slice_del(h2,'<b>持仓快照不能增加 school 覆盖</b>',
                '即"覆盖上限"规划项）。',"report-school-sentence")
ok2=o3
open(F2,"w",encoding="utf-8").write(h2)
print("REPORT ok=%s len=%d"%(ok2,len(h2)))
