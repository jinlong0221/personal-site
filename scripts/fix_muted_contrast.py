# -*- coding: utf-8 -*-
"""
修复「黑底黑字」：各主题块里的 --text-muted 系变量沿用了为另一种底色设计的弱化灰，
在深色背景上对比度只有 3.0~3.5（WCAG AA 要求 4.5）。

难点：站点存在多套配色体系（国风黑金 #12100C 底、中性黑灰 #0f0f0f 底、昼白米色底…），
muted 值各不相同，不能一刀切替换成固定色。

做法：逐个解析每个主题块，读出该块的真实底色，按 WCAG 公式反解出「刚好达标且保持
原色相」的颜色——只调亮度（HSL 的 L），不动色相与饱和度，避免暖灰变冷灰或反之。
"""
import glob
import re
import sys

TARGET_VARS = ('--text-muted', '--text-muted-new', '--tx-3')
# 块内可能的底色来源
BG_VARS = ('--bg', '--bg-secondary', '--card', '--card-hover', '--bg-card',
           '--bg-section', '--dark-tile', '--ink', '--ink-2')
RATIO_TARGET = 4.5
SAFETY = 1.04  # 留 4% 余量，抵消抗锯齿与亚像素渲染


def hex2rgb(h):
    h = h.lstrip('#')
    if len(h) == 3:
        h = ''.join(c * 2 for c in h)
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def rgb2hex(rgb):
    return '#%02X%02X%02X' % tuple(max(0, min(255, int(round(v)))) for v in rgb)


def _f(v):
    v = v / 255.0
    return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4


def luminance(rgb):
    r, g, b = rgb
    return 0.2126 * _f(r) + 0.7152 * _f(g) + 0.0722 * _f(b)


def contrast(a, b):
    l1, l2 = luminance(a), luminance(b)
    hi, lo = max(l1, l2), min(l1, l2)
    return (hi + 0.05) / (lo + 0.05)


def rgb2hsl(rgb):
    r, g, b = (v / 255.0 for v in rgb)
    mx, mn = max(r, g, b), min(r, g, b)
    l = (mx + mn) / 2
    if mx == mn:
        return 0.0, 0.0, l
    d = mx - mn
    s = d / (2 - mx - mn) if l > 0.5 else d / (mx + mn)
    if mx == r:
        h = ((g - b) / d) % 6
    elif mx == g:
        h = (b - r) / d + 2
    else:
        h = (r - g) / d + 4
    return h / 6.0, s, l


def hsl2rgb(h, s, l):
    if s == 0:
        v = l * 255
        return (v, v, v)
    q = l * (1 + s) if l < 0.5 else l + s - l * s
    p = 2 * l - q

    def hue2rgb(t):
        t = t % 1.0
        if t < 1 / 6:
            return p + (q - p) * 6 * t
        if t < 1 / 2:
            return q
        if t < 2 / 3:
            return p + (q - p) * (2 / 3 - t) * 6
        return p

    return tuple(x * 255 for x in (hue2rgb(h + 1 / 3), hue2rgb(h), hue2rgb(h - 1 / 3)))


def solve_color(fg_hex, bg_hexes):
    """返回 (新色 hex 或 None, 最差对比度, 新对比度)"""
    fg = hex2rgb(fg_hex)
    bgs = [hex2rgb(b) for b in bg_hexes]
    worst = min(contrast(fg, b) for b in bgs)
    if worst >= RATIO_TARGET:
        return None, worst, worst

    # 朝「远离底色」的方向调整亮度；二分找「刚好达标」的那一档，
    # 尽量贴近原设计，不为了好看的数字把颜色推到纯黑/纯白。
    fg_l, bg_l = luminance(fg), luminance(bgs[0])
    lighter = fg_l > bg_l
    h, s, l = rgb2hsl(fg)
    # 不变量：lo 始终是不达标侧，hi 始终是达标侧
    lo, hi = (l, 1.0) if lighter else (0.0, l)
    best = None
    for _ in range(40):
        mid = (lo + hi) / 2
        cand = hsl2rgb(h, s, mid)
        c = min(contrast(cand, b) for b in bgs)
        if c >= RATIO_TARGET * SAFETY:
            best = (mid, c)
            if lighter:
                hi = mid          # 达标 → 收窄上界，找更小的达标亮度
            else:
                lo = mid          # 达标 → 抬升下界，找更接近原值的达标亮度
        else:
            if lighter:
                lo = mid
            else:
                hi = mid
    if best is None:
        return None, worst, worst
    return rgb2hex(hsl2rgb(h, s, best[0])), worst, best[1]


BLOCK_RE = re.compile(
    r'(?P<sel>:root|\[data-theme="dark"\]|\[data-theme="light"\])\s*\{(?P<body>[^}]*)\}',
    re.I)


def fix_block(body, stats):
    bgs = []
    for name in BG_VARS:
        m = re.search(re.escape(name) + r'\s*:\s*(#[0-9A-Fa-f]{6})\b', body)
        if m:
            bgs.append(m.group(1))
    if not bgs:
        return body

    out = body
    for var in TARGET_VARS:
        m = re.search(re.escape(var) + r'\s*:\s*(#[0-9A-Fa-f]{6})\b', out)
        if not m:
            continue
        new, worst, after = solve_color(m.group(1), bgs)
        if new:
            out = out[:m.start(1)] + new + out[m.end(1):]
            stats['var'] += 1
            stats['detail'].append((var, m.group(1), new, round(worst, 2), round(after, 2)))
    return out


def process(path, apply):
    src = open(path, encoding='utf-8', errors='ignore').read()
    stats = {'var': 0, 'detail': []}

    def repl(m):
        return m.group('sel') + '{' + fix_block(m.group('body'), stats) + '}'

    out = BLOCK_RE.sub(repl, src)
    if out != src and apply:
        open(path, 'w', encoding='utf-8').write(out)
    return stats, out != src


def main():
    apply = '--dry' not in sys.argv
    targets = sorted(glob.glob('static/*.html'))
    targets += ['static/css/style.css', 'layouts/partials/head.html']
    total, touched = 0, 0
    samples = []
    for p in targets:
        st, changed = process(p, apply)
        if st['var']:
            touched += 1
            total += st['var']
            for d in st['detail']:
                samples.append((p, *d))
    print('模式:', '写入' if apply else '演练')
    print('涉及文件:', touched, ' 变量修正:', total)
    print()
    print(f'{"文件":38s} {"变量":18s} {"原值":9s} -> {"新值":9s}  对比度')
    for s in samples[:25]:
        print(f'{s[0][:38]:38s} {s[1]:18s} {s[2]:9s} -> {s[3]:9s}  {s[4]} -> {s[5]}')
    if len(samples) > 25:
        print(f'... 另有 {len(samples) - 25} 处')


if __name__ == '__main__':
    main()
