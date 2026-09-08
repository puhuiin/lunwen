# -*- coding: utf-8 -*-
"""第四轮微压（2026-09-03）：最后 47 字。"""
import io, os

P = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                 'scripts', '_draft_docx_20260826.py')
src = io.open(P, encoding='utf-8').read()
saved = 0

def rep(old, new):
    global src, saved
    n = src.count(old)
    assert n == 1, f'count={n}: {old[:36]!r}'
    saved += len(old) - len(new)
    src = src.replace(old, new)

rep("'检验依次使用三种因变量：基金季度收益减沪深 300 收益的简单超额、'\n"
    "          'FF3 三因子调整 alpha、以及主口径 FF5 五因子调整 alpha[19]——'",
    "'三种因变量依次为：相对沪深 300 的简单超额、FF3 alpha、'\n"
    "          '主口径 FF5 alpha[19]——'")
rep("f\"（按层加权替代方案的得分 Spearman 相关 \"",
    "f\"（按层加权 Spearman 相关 \"")
rep("f\"{MG['④_秩相关']['相关']['综合_A_vs_综合_B']['spearman']:.4f}，排序结论不变）。\"",
    "f\"{MG['④_秩相关']['相关']['综合_A_vs_综合_B']['spearman']:.4f}，排序不变）。\"")
rep("'其余指标因相互吸收而回落——归并维度时以单变量方向为准、以联立净效应为辅（见本部分之三）。'",
    "'其余指标因相互吸收而回落——归并以单变量方向为准、联立净效应为辅（见本部分之三）。'")
rep("'（N≈352–362）。简单超额不剔除任何因子、风格暴露留在残差中，仅作参照。'",
    "'（N≈352–362）。简单超额不剔因子、风格暴露留在残差，仅作参照。'")
rep("'换手率为 Wind 单边年化口径（半年频），观测层 1%/99% 缩尾后聚合，'",
    "'换手率为 Wind 单边年化（半年频），观测层 1%/99% 缩尾后聚合，'")

io.open(P, 'w', encoding='utf-8').write(src)
print(f'第四轮微压约 {saved} 字符')
