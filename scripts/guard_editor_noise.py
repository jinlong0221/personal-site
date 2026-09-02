#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
guard_editor_noise.py — 根因守卫：禁止 IDE/编辑器自动注入的元数据混进站点源码

背景（2026-09-02 实录）：
    在 IDE（Codebuddy Code 等带"可视化元素定位"能力的编辑器）里打开过某个 HTML
    页面后，编辑器会给页面里几乎每一个标签自动追加形如

        <html lang="zh-CN" data-page-node-id="56O1z6YtHg92edl530q8EH">

    的属性，用来给 DOM 节点打唯一 ID。这类属性有三个问题：

    1. **对站点毫无用处**——纯编辑器内部实现细节，浏览器和访客都不需要，
       但会给每个页面平白增加约 3KB 体积（一页 180+ 处）。
    2. **污染 diff**——一次"什么都没改"的编辑产生 363 行变更，
       真正的业务改动被淹没在噪音里，代码审查基本失效。
    3. **反复回潮**——不是一次性污染。只要谁再用那个编辑器打开这页，
       属性就又写一遍，每轮都要重新纠结"这次要不要一起提交"。

    所以这里立一道闸：**发现即报错，阻断构建**。宁可让提交失败让人手工清掉，
    也不能让噪音反复进库。

判定范围：
    扫描 css/ static/ layouts/ travel-dist/ content/ js/ scripts/ 下的
    .html / .css / .js；跳过 public/ node_modules/ .git/ 等产物与依赖目录。

规则表（RULES）：
    每条规则是 (规则名, 正则, 人话说明)。新增同类污染时往这里加一行即可，
    不要散落到各处 if-else。

两种用法：
    python3 scripts/guard_editor_noise.py          # 只检查，命中即退出 1（CI 用，阻断构建）
    python3 scripts/guard_editor_noise.py --fix    # 就地剥离后退出 0（pre-commit 用，无感自愈）
    python3 scripts/guard_editor_noise.py --fix --list-file=/tmp/lst
                                                   # 同上，另把清理过的文件路径按行写入
                                                   # 指定文件，供 pre-commit 精确 git add
                                                   # （不用 git add -u，免得误加别的文件）

为什么分两种：
    编辑器会在「打开/检出页面」时反复重写这些属性，靠人手工 checkout 治不住——
    2026-09-02 实测：`git checkout -- static/ev-sales.html` 还原后，工作区立刻又被
    写回 616 处。所以本地提交环节走 --fix 自动清干净（提交者无感），CI 再留一道
    纯检查兜底——万一有人绕过本地 hook 直接推，也会被拦下。

退出码：检查模式下命中任一规则返回 1（构建失败），否则 0；--fix 模式恒为 0。
"""

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SCAN_DIRS = ["css", "static", "layouts", "travel-dist", "content", "js", "scripts"]
SKIP_DIRS = {"public", "node_modules", ".git", "resources", ".workbuddy",
             ".design", "data", "outputs"}
SCAN_EXTS = {".html", ".css", ".js"}

# (规则名, 编译后的正则, 说明)
# 注意：只匹配"属性形态"，避免误伤正文里恰好出现同样字样的普通文本。
RULES = [
    (
        "data-page-node-id",
        re.compile(r"""\sdata-page-node-id\s*=\s*["'][^"']*["']"""),
        "IDE 元素定位元数据（编辑器给 DOM 节点打的唯一 ID），站点不需要",
    ),
]


def iter_files():
    """产出待扫描文件的绝对路径。"""
    for d in SCAN_DIRS:
        base = os.path.join(ROOT, d)
        if not os.path.isdir(base):
            continue
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = [x for x in dirnames if x not in SKIP_DIRS]
            for fn in filenames:
                if os.path.splitext(fn)[1].lower() in SCAN_EXTS:
                    yield os.path.join(dirpath, fn)


def strip_noise(text):
    """剥离所有规则命中的编辑器元数据属性。幂等，可重复执行。"""
    for _name, pattern, _desc in RULES:
        text = pattern.sub("", text)
    return text


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    fix = "--fix" in argv
    # --list-file=PATH：把被清理的文件路径按行写入指定文件，供 pre-commit 精确
    # git add（不用 git add -u，免得把无关的未暂存改动一起加进提交）。
    list_file = None
    for a in argv:
        if a.startswith("--list-file="):
            list_file = a.split("=", 1)[1]

    # rule_name -> [(相对路径, 命中次数), ...]
    hits = {}
    scanned = 0

    for fpath in iter_files():
        try:
            with open(fpath, "r", encoding="utf-8") as fh:
                text = fh.read()
        except (UnicodeDecodeError, OSError):
            continue
        scanned += 1
        rel = os.path.relpath(fpath, ROOT)
        for name, pattern, _desc in RULES:
            n = len(pattern.findall(text))
            if n:
                hits.setdefault(name, []).append((rel, n))

    if not hits:
        print(f"[guard_editor_noise] PASS: {scanned} 个文件无编辑器注入元数据")
        return 0

    total = sum(n for lst in hits.values() for _rel, n in lst)
    files = sorted({rel for lst in hits.values() for rel, _n in lst})

    if fix:
        cleaned = []
        for rel in files:
            p = os.path.join(ROOT, rel)
            try:
                with open(p, "r", encoding="utf-8") as fh:
                    old = fh.read()
                new = strip_noise(old)
                if new != old:
                    with open(p, "w", encoding="utf-8") as fh:
                        fh.write(new)
                    cleaned.append((rel, len(old) - len(new)))
            except OSError as e:
                print(f"[guard_editor_noise] 写入失败 {rel}: {e}")
                return 1
        # 复检：--fix 必须真的清干净，否则等于没修（不能只信自己改过）
        left = []
        for rel, _saved in cleaned:
            with open(os.path.join(ROOT, rel), "r", encoding="utf-8") as fh:
                t = fh.read()
            for _name, pattern, _desc in RULES:
                if pattern.search(t):
                    left.append(rel)
                    break
        if left:
            print(f"[guard_editor_noise] FIX 未清干净: {', '.join(left)}")
            return 1
        saved = sum(s for _r, s in cleaned)
        print(f"[guard_editor_noise] FIX: 已清理 {len(cleaned)} 个文件、"
              f"剔除 {total} 处元数据（省下 {saved} 字节）")
        for rel, s in cleaned:
            print(f"    - {rel}  (-{s} 字节)")
        if list_file:
            try:
                with open(list_file, "w", encoding="utf-8") as fh:
                    for rel, _s in cleaned:
                        fh.write(rel + "\n")
            except OSError as e:
                print(f"[guard_editor_noise] 无法写清单文件 {list_file}: {e}")
                return 1
        return 0

    print(f"[guard_editor_noise] FAIL: {len(files)} 个文件、共 {total} 处"
          f"编辑器注入的元数据")
    for name, lst in sorted(hits.items()):
        desc = next(d for n, _p, d in RULES if n == name)
        print(f"\n  规则 {name}：{desc}")
        for rel, n in sorted(lst, key=lambda x: -x[1]):
            print(f"    - {rel}  ({n} 处)")
    print("\n  修复：python3 scripts/guard_editor_noise.py --fix")
    print("        （本地 pre-commit 会自动调用；CI 里需人工跑完再提交）")
    return 1


if __name__ == "__main__":
    sys.exit(main())
