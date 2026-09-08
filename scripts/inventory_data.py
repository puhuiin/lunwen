# -*- coding: utf-8 -*-
"""数据目录系统盘点脚本：递归遍历 数据\ 各层，输出文件清单与统计。"""
import os, json, hashlib
from pathlib import Path

BASE = r"D:\Desktop\基金经理行为分析研究\数据"
SKIP_LAYERS = set()  # 全部纳入

rows = []
layer_summary = {}
for root, dirs, files in os.walk(BASE):
    rel_root = os.path.relpath(root, BASE)
    top = rel_root.split(os.sep)[0] if rel_root != "." else "(root)"
    for f in files:
        fp = os.path.join(root, f)
        try:
            sz = os.path.getsize(fp)
        except OSError:
            sz = -1
        ext = os.path.splitext(f)[1].lower()
        rows.append({
            "layer": top,
            "rel": rel_root,
            "name": f,
            "ext": ext,
            "size_kb": round(sz / 1024, 2) if sz >= 0 else None,
        })

# 按层聚合
from collections import defaultdict, OrderedDict
layers = OrderedDict()
for r in rows:
    L = r["layer"]
    if L not in layers:
        layers[L] = {"n_files": 0, "total_kb": 0.0, "exts": defaultdict(int)}
    layers[L]["n_files"] += 1
    if r["size_kb"] is not None:
        layers[L]["total_kb"] += r["size_kb"]
    layers[L]["exts"][r["ext"]] += 1

print("="*70)
print(f"数据目录总文件数: {len(rows)}")
print(f"顶层分组数: {len(layers)}")
print("="*70)
for L, s in layers.items():
    ext_str = ", ".join(f"{k}:{v}" for k, v in sorted(s["exts"].items(), key=lambda x:-x[1]))
    print(f"\n[{L}]  文件={s['n_files']}  总大小={s['total_kb']:.1f} KB")
    print(f"    类型: {ext_str}")

# CSV 文件明细（核心数据集候选）
print("\n" + "="*70)
print("CSV 文件明细（按层）：")
print("="*70)
csv_rows = [r for r in rows if r["ext"] == ".csv"]
csv_rows.sort(key=lambda r:(r["layer"], - (r["size_kb"] or 0)))
for r in csv_rows:
    print(f"  {r['layer']:<14} {r['name']:<45} {r['size_kb']:>10.1f} KB")

# 保存清单
out = {
    "base": BASE,
    "total_files": len(rows),
    "layers": {L: {"n_files": s["n_files"], "total_kb": round(s["total_kb"],2),
                   "exts": dict(s["exts"])} for L, s in layers.items()},
    "files": rows,
}
with open(r"D:\Desktop\基金经理行为分析研究\data_inventory.json", "w", encoding="utf-8") as fh:
    json.dump(out, fh, ensure_ascii=False, indent=2)
print(f"\n清单已保存: data_inventory.json ({len(rows)} 文件)")
