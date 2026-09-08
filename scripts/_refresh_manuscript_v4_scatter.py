# -*- coding: utf-8 -*-
"""v4 散引刷新（修正版）：将 merged_manuscript.html 中所有 L5 M4 散引 t/p 值
刷新为权威双向聚类真值。

权威锚点（来自 _repro_M4_authoritative_v4_2026-08-16.py 实跑 + _v4_robust.json）：
  de        β=-0.00606  t=-2.99  p=0.003  (***)
  lsv       β=+0.01548  t=+0.77  p=0.441  (n.s.)
  risk_asym β=+0.07311  t=+3.57  p≈0.000 (***)
  置换 p (two-way): RA 0.02 / DE 0.047 / LSV 0.51
  WCB   p (two-way, 修正H0): RA 0.000 / DE 0.014 / LSV 0.229

注：文件内中文引号使用直引号 "，叙事字符串须用直引号匹配。
"""
import io, sys

PATH = r"D:\Desktop\基金经理行为分析研究\merged_manuscript.html"

# 唯一匹配项：(old, new)，断言全文件恰好出现 1 次
UNIQ = [
    # ---- §4.4.1 安慰剂置换表 (L775-777) ----
    ('<tr class="signif"><td>RiskAsym</td><td>+4.53</td><td>0.00</td><td>0.2%</td><td class="stars">✓ 显著</td></tr>',
     '<tr class="signif"><td>RiskAsym</td><td>+3.57</td><td>0.00</td><td>2.0%</td><td class="stars">✓ 显著</td></tr>'),
    ('<tr><td>LSV</td><td>+1.23</td><td>0.00</td><td>22.0%</td><td>✗ 不显著</td></tr>',
     '<tr><td>LSV</td><td>+0.77</td><td>0.00</td><td>51.0%</td><td>✗ 不显著</td></tr>'),
    ('<tr class="signif"><td>DE</td><td>-2.50</td><td>0.00</td><td>1.2%</td><td class="stars">✓ 显著</td></tr>',
     '<tr class="signif"><td>DE</td><td>-2.99</td><td>0.00</td><td>4.7%</td><td class="stars">✓ 显著</td></tr>'),
    # ---- §4.4.1 叙事 (L780) —— 用直引号 ----
    ('RiskAsym（t=4.53, p=0.002）和DE（t=-2.50, p=0.012）的真实t值位于置换分布的前0.2%和1.2%分位，强烈拒绝伪相关假设；其中DE在5%水平下显著、在1%水平下不显著（边际-显著）。LSV的真实t值（t=1.23, p=0.22）位于置换分布的第22%分位，远未达显著，与其在M4完整模型中失去显著性的结论完全一致——置换检验进一步确认LSV的关联在控制全部L1-L4变量后并非稳健的伪相关排除对象，故维持其"选择敏感描述性证据"定位。',
     'RiskAsym（t=+3.57, p=0.02）和DE（t=-2.99, p=0.047）的真实t值位于置换分布的前2.0%和4.7%分位，均在5%水平拒绝伪相关假设（DE为边界显著）；LSV的真实t值（t=+0.77, p=0.51）位于置换分布的第51%分位，远未达显著，与其在M4完整模型中失去显著性的结论完全一致——置换检验进一步确认LSV的关联在控制全部L1-L4变量后并非稳健的伪相关排除对象，故维持其"选择敏感描述性证据"定位。'),
    # ---- §4.7 WCB-S 表 (L924-926) ----
    ('<tr class="signif"><td>risk_asym</td><td>+4.53</td><td><strong>0.049</strong></td><td>0.000</td><td>边界(10%边际)</td></tr>',
     '<tr class="signif"><td>risk_asym</td><td>+3.57</td><td><strong>0.000</strong></td><td>0.000</td><td class="stars">✓ 显著</td></tr>'),
    ('<tr><td>lsv</td><td>+1.23</td><td>0.343</td><td>0.219</td><td class="stars">一致(均不显著)</td></tr>',
     '<tr><td>lsv</td><td>+0.77</td><td>0.229</td><td>0.441</td><td class="stars">一致(均不显著)</td></tr>'),
    ('<tr><td>de</td><td>-2.50</td><td><strong>0.188</strong></td><td>0.013</td><td class="bad">WCB下不显著</td></tr>',
     '<tr class="signif"><td>de</td><td>-2.99</td><td><strong>0.014</strong></td><td>0.003</td><td class="stars">✓ WCB下仍显著</td></tr>'),
    # ---- §4.7 WCB-S 叙事 (L930) —— 用直引号 ----
    ('WCB-S结果与渐近聚类SE<strong>出现分野</strong>，这是诚实面板下的关键警示。RiskAsym在WCB下处于边界（p=0.049，刚好高于5%），仍可视为10%水平的边际显著，与渐近推断（p&lt;0.001）方向一致但量级的精确性被削弱。LSV在WCB与渐近下均不显著（p=0.343 vs 0.219），完全一致。但<strong>DE在WCB下不再显著（p=0.188），与渐近聚类SE给出的p=0.013（**）形成反转</strong>——考虑到M4聚类数已达348（远超经验阈值30）、渐近推断本应可靠，WCB的保守性在此反而提示DE的显著性对聚类推断方法高度敏感，可能源于少数基金的杠杆效应。综合判断：在诚实面板下，<strong>仅RiskAsym的关联在WCB边界上仍成立，LSV与DE的显著性在WCB下均不被支持</strong>，这进一步说明二者（尤其DE）的证据强度有限；核心稳健结论应锚定RiskAsym，并将DE/LSV定位为"方向一致但推断敏感性高"的辅助证据（详见§6.4.1的证据分级）。',
     'WCB-S结果与渐近聚类SE<strong>高度一致</strong>（双向聚类口径下），这进一步确认了诚实面板下核心结论的稳健性。RiskAsym在WCB下高度显著（p=0.000），与渐近推断（p&lt;0.001）方向一致且精确性得到交叉验证。LSV在WCB与渐近下均不显著（p=0.229 vs 0.441），完全一致。值得注意的是，<strong>DE在WCB下仍显著（p=0.014），与渐近聚类SE给出的p=0.003（***）一致</strong>——WCB的精确推断不仅未推翻DE的显著性，反而支持其稳健性，说明DE的关联并非由少数基金驱动的假象。综合判断：在诚实面板双向聚类口径下，<strong>RiskAsym与DE的关联在WCB下均显著（p=0.000/p=0.014），仅LSV不显著（p=0.229）</strong>，三指标推断结论在WCB与渐近间高度一致；核心稳健结论应锚定RiskAsym与DE，并将LSV定位为"方向一致但推断不显著"的辅助证据（详见§6.4.1的证据分级）。'),
    # ---- §4.12 效应量与功效 表 LSV (L1015) ----
    ('<tr><td>lsv</td><td>≈0（n.s.）</td><td>—</td><td>不足（t=1.23, p=0.219）</td><td>⚠ 不显著</td></tr>',
     '<tr><td>lsv</td><td>≈0（n.s.）</td><td>—</td><td>不足（t=+0.77, p=0.441）</td><td>⚠ 不显著</td></tr>'),
    # ---- §4.12 叙事 DE 功效表述修正 (L1019) ----
    ('DE在部分设定下不显著的主要原因是功效不足而非效应不存在',
     'DE在部分子样本（如熊市）下失去显著性的主要原因是功效不足而非效应不存在'),
    # ---- §4.11 证据矩阵 置换 (L1334) ----
    ('<tr><td>安慰剂检验（500次置换）</td><td>DE p=0.012** / LSV p=0.220（不显著） / RiskAsym p=0.002***</td><td class="stars">DE与RiskAsym通过，LSV不显著</td></tr>',
     '<tr><td>安慰剂检验（500次置换）</td><td>DE p=0.047* / LSV p=0.51（不显著） / RiskAsym p=0.02*</td><td class="stars">DE与RiskAsym通过(均p&lt;0.05)，LSV不显著</td></tr>'),
    # ---- §4.11 证据矩阵 WCB (L1339) ----
    ('<tr><td>WCB-S小样本推断</td><td>RiskAsym p=0.049（10%边际） / DE p=0.188（不显著） / LSV p=0.343（不显著）</td><td class="stars">仅RiskAsym边际，DE/LSV反转</td></tr>',
     '<tr><td>WCB-S小样本推断</td><td>RiskAsym p=0.000（***） / DE p=0.014（**） / LSV p=0.229（不显著）</td><td class="stars">RA与DE均显著，仅LSV不显著</td></tr>'),
    # ---- §4.11 效应矩阵 LSV (L1078) ----
    ('<tr><td>效应量 f² / 功效</td><td>0.053 (中) / ~100%</td><td>n.s.（t=1.23，功效不足）</td><td>0.003 (小) / 64.8%</td></tr>',
     '<tr><td>效应量 f² / 功效</td><td>0.053 (中) / ~100%</td><td>n.s.（t=+0.77，p=0.441，功效不足）</td><td>0.003 (小) / 64.8%</td></tr>'),
    # ---- §4.11 叙事 WCB 反转 + LSV t (L1067) ----
    ('WCB-S下DE与LSV不再显著（仅RiskAsym边际）',
     'WCB-S下DE与RiskAsym均显著（仅LSV不显著）'),
    ('LSV在诚实面板下不显著（t=1.23）、DE功效不足（64.8%）是其不稳定的主因。',
     'LSV在诚实面板下不显著（t=+0.77）、DE功效不足（64.8%）是其不稳定的主因。'),
    # ---- §6.1.2 RA / DE (L1324) ----
    ('RiskAsym正向关联最强且高度显著（β=0.07311, t=4.53, p&lt;0.001）',
     'RiskAsym正向关联最强且高度显著（β=0.07311, t=+3.57, p&lt;0.001）'),
    ('DE负向关联且显著（β=-0.00606, t=-2.50, p=0.013）',
     'DE负向关联且显著（β=-0.00606, t=-2.99, p=0.003）'),
    # ---- §6.1.2 LSV 叙事 (L1325) ----
    ('LSV在诚实面板下不显著（t=1.23, p=0.219）',
     'LSV在诚实面板下不显著（t=+0.77, p=0.441）'),
    # ---- §6.2.2 DE / RA (L1365, L1367) ----
    ('DE负向系数（β=-0.00606, t=-2.50**）',
     'DE负向系数（β=-0.00606, t=-2.99***）'),
    ('RiskAsym正向系数（β=0.07311, t=4.53***）',
     'RiskAsym正向系数（β=0.07311, t=+3.57***）'),
]

# 全局替换项：(old, new, expected_count)
GLOBAL = [
    # LSV β 短语全文 4 处（L1019/L1324/L1366/L1394）目标一致，统一替换
    ('β=0.01548, t=1.23, p=0.219', 'β=0.01548, t=+0.77, p=0.441', 4),
]

def main():
    with io.open(PATH, 'r', encoding='utf-8') as f:
        s = f.read()
    fail = 0
    for i, (old, new) in enumerate(UNIQ, 1):
        cnt = s.count(old)
        if cnt != 1:
            print(f"[FAIL] UNIQ#{i} count={cnt} (期望1)")
            idx = s.find(old[:30])
            print("   上下文:", s[max(0,idx-40):idx+90].replace('\n',' '))
            fail += 1
        else:
            s = s.replace(old, new, 1)
    for i, (old, new, exp) in enumerate(GLOBAL, 1):
        cnt = s.count(old)
        if cnt != exp:
            print(f"[FAIL] GLOBAL#{i} count={cnt} (期望{exp})")
            print("   上下文:", s[max(0,s.find(old)-40):s.find(old)+90].replace('\n',' '))
            fail += 1
        else:
            s = s.replace(old, new)
    if fail:
        print(f"\n中止：{fail} 处替换失败，未写入文件。")
        sys.exit(1)
    with io.open(PATH, 'w', encoding='utf-8') as f:
        f.write(s)
    print(f"OK：成功应用 {len(UNIQ)} 处唯一替换 + {len(GLOBAL)} 处全局替换，已写回文件。")

if __name__ == '__main__':
    main()
