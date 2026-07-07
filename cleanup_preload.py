#!/usr/bin/env python3
"""清理重复的CSS preload行——旧的裸preload已被critical-css方案替代"""
import os
import re
import glob

STATIC_DIR = "/Users/chenjinlong/陈金龙/代码与脚本/个人知识网站/hugo-site/static"

def cleanup_html(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    original = content

    # 删除旧的裸 preload 行（不带 onload 的那行）
    # 匹配: <link rel="preload" href="...style.css?v=XXXX" as="style">
    # 但不匹配带 onload 的那行
    lines = content.split('\n')
    new_lines = []
    skip_next_blank = False

    for i, line in enumerate(lines):
        # 检查是否是旧的裸 preload（有 style.css preload 但没有 onload）
        if 'rel="preload"' in line and 'style.css' in line and 'as="style"' in line and 'onload' not in line:
            skip_next_blank = True
            continue
        if skip_next_blank and line.strip() == '':
            skip_next_blank = False
            continue
        skip_next_blank = False
        new_lines.append(line)

    content = '\n'.join(new_lines)

    if content != original:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    return False

html_files = glob.glob(os.path.join(STATIC_DIR, "**", "*.html"), recursive=True)
count = 0
for f in sorted(html_files):
    if cleanup_html(f):
        count += 1

print(f"Cleaned up {count} files")
