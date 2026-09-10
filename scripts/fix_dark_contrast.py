# -*- coding: utf-8 -*-
"""
批量修复「黑底黑字」：深色主题下 --text-muted 系变量沿用了浅底弱化灰 #6C6353，
对比度仅 3.0（WCAG AA 要求 4.5）。静态页内联 CSS 优先级高于外部样式表，
故必须逐个页面同步修改。

修三类问题：
  1. 变量值：深色 #6C6353 -> #948A76；浅色 #8B8168 -> #6F6653（浅底上 3.25 -> 4.77）
  2. 叠透明度：颜色已达标却又 opacity 压暗，导致实际对比度腰斩
  3. 硬编码色：热点标签红、苹果页金色，改用随主题反转的变量
"""
import glob
import re
import sys

DARK_NEW = '#948A76'
LIGHT_NEW = '#6F6653'

# 1) 变量值替换
PAT_DARK = re.compile(r'(--(?:text-muted|text-muted-new|tx-3):\s*)#6C6353\b', re.I)
PAT_LIGHT = re.compile(r'(--(?:text-muted|text-muted-new|tx-3):\s*)#8B8168\b', re.I)

# 2) 需要去掉 opacity 的选择器（这些元素颜色本身已达标，叠透明度反而看不清）
OPACITY_SELECTORS = [
    r'\.footer-legal',
    r'\.breadcrumb\s+\.sep',
    r'\.footer-info-row\s+\.sep',
    r'\.nav-clock',
    r'\.update-time',
]

# 3) 硬编码色 -> 主题变量
PAT_HOT = re.compile(r'(\.news-tag\.hot\s*\{[^}]*?color:\s*)#dc2626\b', re.I)
PAT_GOLD = re.compile(r'(color:\s*)#c9a84c\b', re.I)


def drop_opacity(css, selector):
    pat = re.compile(r'(' + selector + r'\s*\{[^}]*?)opacity:\s*\.?\d+\s*;', re.I)
    n = len(pat.findall(css))
    return pat.sub(lambda m: m.group(1), css), n


def process(path, apply=True):
    src = open(path, encoding='utf-8', errors='ignore').read()
    out = src
    stat = {}

    out, stat['dark_var'] = PAT_DARK.subn(lambda m: m.group(1) + DARK_NEW, out)
    out, stat['light_var'] = PAT_LIGHT.subn(lambda m: m.group(1) + LIGHT_NEW, out)

    total_op = 0
    for sel in OPACITY_SELECTORS:
        out, n = drop_opacity(out, sel)
        total_op += n
    stat['opacity'] = total_op

    out, stat['hot'] = PAT_HOT.subn(lambda m: m.group(1) + 'var(--tag-hot)', out)
    out, stat['gold'] = PAT_GOLD.subn(lambda m: m.group(1) + 'var(--gold)', out)

    changed = out != src
    if changed and apply:
        open(path, 'w', encoding='utf-8').write(out)
    return stat, changed


def main():
    apply = '--dry' not in sys.argv
    targets = sorted(glob.glob('static/*.html'))
    targets += ['static/css/style.css', 'layouts/partials/head.html']

    agg = {}
    touched = 0
    for p in targets:
        try:
            stat, changed = process(p, apply)
        except Exception as e:  # noqa: BLE001
            print('ERR', p, e)
            continue
        if any(stat.values()):
            touched += 1
            for k, v in stat.items():
                agg[k] = agg.get(k, 0) + v

    print('模式:', '写入' if apply else '演练(不改文件)')
    print('改动文件数:', touched, '/', len(targets))
    for k in ('dark_var', 'light_var', 'opacity', 'hot', 'gold'):
        print(f'  {k:10s}: {agg.get(k, 0)}')


if __name__ == '__main__':
    main()
