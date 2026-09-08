#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""批量修复 slide-main 的 grid-template-rows 混用问题"""
import os
import re

pages_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
    '..', '..', 'AI', '灵犀', '20260804-10-37-31-846', 'ppt_project', 'pages')

# 更直接的路径
pages_dir = r'D:\Desktop\AI\灵犀\20260804-10-37-31-846\ppt_project\pages'

fixed = 0
for fname in sorted(os.listdir(pages_dir)):
    if not fname.endswith('.html') or fname == 'slide_01.html':
        continue
    
    fpath = os.path.join(pages_dir, fname)
    with open(fpath, 'r', encoding='utf-8') as f:
        html = f.read()
    
    original = html
    
    # 修复模式1: grid-template-rows:auto 1fr; -> 去掉grid-template-rows, 保留align-content
    # 修复模式2: grid-template-rows:auto 1fr auto; -> 同上
    
    # 替换 .slide-main 中的 grid-template-rows: auto 1fr; 或 auto 1fr auto;
    html = re.sub(
        r'(\.slide-main\s*\{[^}]*?)grid-template-rows:\s*auto\s+1fr\s*(?:auto\s*)?;',
        r'\1',
        html
    )
    
    if html != original:
        with open(fpath, 'w', encoding='utf-8') as f:
            f.write(html)
        fixed += 1
        print(f"[修复] {fname}")

print(f"\n共修复 {fixed} 个文件")
