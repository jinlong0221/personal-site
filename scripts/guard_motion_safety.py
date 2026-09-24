#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""guard_motion_safety.py — 动效/立体化三层护栏（2026-09-20 新增）

三条规则全部来自本轮真实踩坑（每一条都造成过肉眼可见的缺陷）：

D1  JS 往元素上写的 CSS 变量名，不得与样式表里已有的「根级令牌」重名。
    事故：立体化倾斜脚本往卡片上写 --tx 存角度，而 --tx 在 style.css:62 是
    「文字色」的历史别名（17 处在消费）→ 鼠标一悬停，卡片内文字色被解析成非法值而失效；
    JS 未写入时 rotateY(var(--tx)) 把颜色当角度 → 整条 transform 作废回退 none。
    根治：倾斜变量改名 --tilt-x / --tilt-y。

D2  动画填充模式用 both / backwards，且起始帧把元素压到近乎不可见，**又写在条件块里**
    （@supports / @media）→ 条件命中但动画没跑起来时，元素会永久停在全透明起始帧。
    事故前科：2026-08-19「首页 hero 透明空洞」就是这一类的后果。
    本轮 main 的跨页淡入兜底一度写成 `@supports not (...){ main{animation:… both} }` +
    from{opacity:.001}，已改 forwards。**不在条件块里的普通入场动画只提示、不阻断**
    （那是全站既有写法，且页面加载时必然执行）—— 避免守卫为了普遍现象把 CI 卡死。

D3  改动 transform / filter 的 :hover 规则，若不在「有 hover 能力」的媒体条件里 → 提示。
    事故：射阳气象磁贴 `.tile:hover{transform:scale(1.02)}` 无门控 —— 触屏点按同样点亮
    :hover，手指按下去是「放大」而不是「压下去」（该页已修）。此项对全站作清单式提示。

用法：
  python3 scripts/guard_motion_safety.py            # D1/D2 违规即 exit 1；D3 仅计入提示数
  python3 scripts/guard_motion_safety.py --report   # 附带打印 D3 明细
"""
import argparse
import glob
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSS = os.path.join(ROOT, 'static', 'css', 'style.css')
errors = []
warns = []


def read(p):
    return io.open(p, encoding='utf-8', errors='replace').read()


def strip_comments(t):
    return re.sub(r'/\*.*?\*/', '', t, flags=re.S)


def walk(text):
    """把一段 CSS 拆成 [(选择器, 祖先条件元组, 规则主体)]。
    祖先条件只保留 @ 规则的前导文本（如 '@media (hover: hover) and (pointer: fine)'）。"""
    out, stack, buf, i = [], [], '', 0
    while i < len(text):
        ch = text[i]
        if ch == '{':
            head = buf.strip()
            stack.append((head.startswith('@'), head, i + 1))
            buf = ''
        elif ch == '}':
            if stack:
                is_at, head, start = stack.pop()
                ctx = tuple(h for k, h, _ in stack if k)
                if not is_at and head:
                    out.append((head, ctx, text[start:i]))
            buf = ''
        else:
            buf += ch
        i += 1
    return out


def keyframes(text):
    """{动画名: 起始帧声明文本}"""
    kf = {}
    for m in re.finditer(r'@keyframes\s+([A-Za-z0-9_-]+)\s*\{', text):
        j, depth, k = m.end() - 1, 0, m.end() - 1
        while k < len(text):
            if text[k] == '{':
                depth += 1
            elif text[k] == '}':
                depth -= 1
                if depth == 0:
                    break
            k += 1
        kf[m.group(1)] = text[j + 1:k]
    return kf


# -------------------------------------------------------------------------- D1
def root_tokens(css_text):
    names = set()
    for m in re.finditer(r'(:root|\[data-theme="?(?:light|dark)"?\])\s*\{', css_text):
        j, depth, k = m.end() - 1, 0, m.end() - 1
        while k < len(css_text):
            if css_text[k] == '{':
                depth += 1
            elif css_text[k] == '}':
                depth -= 1
                if depth == 0:
                    break
            k += 1
        for d in re.finditer(r'(--[A-Za-z0-9_-]+)\s*:', css_text[j + 1:k]):
            names.add(d.group(1))
    return names


def js_written_tokens():
    found = {}
    # 2026-09-24：原来还扫一行仓库根的 js/*.js（双副本时代的死副本，从不进 public），
    # 随双副本拆除一并去掉。真正会上线的只有 static/js/。
    pats = glob.glob(os.path.join(ROOT, 'static', 'js', '**', '*.js'), recursive=True)
    rx = re.compile(r'(?:set|remove)Property\(\s*[\'"](--[A-Za-z0-9_-]+)[\'"]')
    for p in pats:
        rel = os.path.relpath(p, ROOT)
        for i, line in enumerate(read(p).split('\n'), 1):
            for m in rx.finditer(line):
                found.setdefault(m.group(1), []).append(f'{rel}:{i}')
    return found


def check_d1():
    defined = root_tokens(read(CSS))
    for p in glob.glob(os.path.join(ROOT, 'static', '*.html')):
        for m in re.finditer(r'<style[^>]*>(.*?)</style>', read(p), re.S):
            defined |= root_tokens(m.group(1))
    written = js_written_tokens()
    for name in sorted(set(written) & defined):
        errors.append(
            f'D1 变量名撞车：JS 写 {name}（{", ".join(written[name][:3])}），'
            f'但样式表已在根级把 {name} 定义成别的东西 → 该元素及其后代读到错误的值。'
            f'请改用独占名字（如 --tilt-x / --tilt-y）。'
        )
    return len(written), len(defined)


# -------------------------------------------------------------------------- D2
def css_sources():
    srcs = [(CSS, strip_comments(read(CSS)))]
    for p in sorted(glob.glob(os.path.join(ROOT, 'static', '*.html'))):
        t = read(p)
        for m in re.finditer(r'<style[^>]*>(.*?)</style>', t, re.S):
            srcs.append((p, strip_comments(m.group(1))))
    return srcs


def check_d2():
    candidates = 0
    for path, text in css_sources():
        if not text.strip():
            continue
        kf = keyframes(text)
        for sel, ctx, body in walk(text):
            if '::view-transition' in sel:
                continue                       # 视图转场的伪元素只在转场期间存在，both 是标准写法
            for d in re.finditer(r'animation(?:-fill-mode)?\s*:\s*([^;{}]+)', body):
                val = d.group(1)
                if not re.search(r'(?<![-\w])(both|backwards)(?![-\w])', val):
                    continue
                names = [n for n in kf if re.search(r'(?<![-\w])' + re.escape(n) + r'(?![-\w])', val)]
                if not names:
                    continue
                candidates += 1
                for n in names:
                    low = None
                    for fm in re.finditer(r'(?:^|[,{}])\s*(?:from|0%)\s*\{([^}]*)\}', kf[n]):
                        om = re.search(r'opacity\s*:\s*([0-9.]+)', fm.group(1))
                        if om and float(om.group(1)) < 0.05:
                            low = om.group(1)
                    if low is None:
                        continue
                    rel = os.path.relpath(path, ROOT)
                    if any(c.startswith(('@supports', '@media')) for c in ctx):
                        errors.append(
                            f'D2 不可见陷阱：`{sel[:46]}` 在条件块 '
                            f'[{"; ".join(ctx)[:60]}] 里用 both/backwards 填充，'
                            f'而 @keyframes {n} 起始帧 opacity={low} → 条件命中但动画未执行时，'
                            f'元素永久停在近乎全透明。请改成 forwards。出处 {rel}'
                        )
                    else:
                        warns.append(f'D2(提示) {rel} :: {sel[:40]} :: @keyframes {n} from{{opacity:{low}}}')
    return candidates


# -------------------------------------------------------------------------- D3
def check_d3():
    hits = []
    for path, text in css_sources():
        if not text.strip():
            continue
        for sel, ctx, body in walk(text):
            if ':hover' not in sel:
                continue
            if not re.search(r'(?:^|[;\s])(?:-webkit-)?(transform|filter)\s*:', body):
                continue
            if any(re.search(r'hover\s*:', c) for c in ctx):
                continue                        # 已在 hover 能力条件里（含 (hover:none) 的兜底块）
            hits.append((os.path.relpath(path, ROOT), ' '.join(ctx)[:50] or '(无媒体条件)',
                         sel.strip()[:80]))
    return hits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--report', action='store_true')
    args = ap.parse_args()

    js_n, tok_n = check_d1()
    cand = check_d2()
    d3 = check_d3()

    if errors:
        print('guard_motion_safety: 发现 %d 项问题' % len(errors))
        for e in errors:
            print('  ✗', e)
        return 1

    print('guard_motion_safety: PASS（D1 JS 写变量 %d 个 / 根级令牌 %d 个；'
          'D2 both|backwards 动画 %d 处；D3 未门控 :hover %d 处）' % (js_n, tok_n, cand, len(d3)))
    for w in warns:
        print('  ·', w)
    if args.report and d3:
        print('  D3 清单（未包在 hover 能力条件里、却改 transform/filter 的 :hover ——'
              ' 触屏点按会被误当悬停，建议逐个判断是否加 @media (hover:hover) and (pointer:fine)）：')
        for f, ctx, sel in d3:
            print(f'    · {f}  [{ctx}]  {sel}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
