#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""逐页审计**部署产物**（gh-pages）的观感一致性，作为全站统一的金标准验收。

和 scripts/audit_site.py 的分工：
  audit_site.py  查源码（static/），看内容有没有缺图 / 空 alt / 死链
  本脚本         查产物（gh-pages），看**每一页渲染出来是否长得一样** ——
                 面包屑 / H1 / 页尾信息块 / CC 许可行 四项骨架，外加正文引号残留

为什么非要看产物而不是看源码：源码里 176 个 static/*.html 是全站统一过的，
但线上还有一批页是 Hugo 用 layouts/ 模板**现渲染**出来的（notes / tags / tag /
categories / search / bookmarks …）。改模板漏一个，源码侧一切正常，只有产物会露馅——
2026-09-17 就是这样抓到 /tags.html 与 /tag.html 全站唯一缺页尾信息块。

为什么用 HTMLParser 而不是正则：Hugo 的 --minify 会去掉属性引号（class=breadcrumb），
并且页面里混着 <script>/<style> 与代码块，正则分词会被带偏。HTMLParser 只取
真正的文本节点，跳过 script/style 与 code/pre（代码里的直引号是合法的）。

用法：
  python3 scripts/audit_live_artifact.py              # 自动拉 gh-pages 后审计
  python3 scripts/audit_live_artifact.py --root public # 审计本地某个目录
  python3 scripts/audit_live_artifact.py --keep       # 保留导出目录便于手查
退出码：0 = 全绿；1 = 有真实缺失（设计内豁免不算）
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
from html.parser import HTMLParser
from collections import Counter

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKIP_TEXT_TAGS = {"script", "style", "textarea", "title"}
# 代码块内的直引号是合法的（HTML 属性、JS 字符串、命令行参数），不算正文引号残留
CODE_TAGS = {"code", "pre", "kbd", "samp"}

# 设计内就不该有面包屑 / CC 许可行的页：
#   404 错误页、offline 离线兜底页、3 个主机图鉴别名 301 跳转壳、
#   travel 加密壳（页脚随内容一起加密，解锁后才出现）、
#   以及「脚趾抠地」App 的独立法律页（不属本站内容，套本站免责声明反而误导）
#   tags/ 是 Hugo 侧 301 跳转壳（content/tags/_index.md + layouts/_default/redirect.html），
#   与 static/ 下主机别名 / 已并板块的跳转页同族：只留 meta refresh 与说明文字，不该长骨架。
#
# ⚠️ 键一律写「相对产物根目录的路径」（如 tags/index.html），不要写裸文件名：
#    下面用 rel in SET 精确匹配。早期版本用 os.path.basename 匹配，
#    导致子目录里任何叫 index.html 的页根本没法登记进豁免表。
_BRACELET_SHELLS = {
    # 文玩手串板块 2026-09-22 起聚焦星月菩提一个品种，其余品类详情页改为跳转壳
    "bracelet/fengyan.html", "bracelet/longyan.html", "bracelet/magu.html",
    "bracelet/mengma.html", "bracelet/zijinboyu.html",
    "bracelet/pinxiang.html", "bracelet/wuxing.html",
}
STRUCTURE_EXEMPT = {
    "404.html", "offline.html",
    "console-gc.html", "console-n64.html", "console-wiiu.html",
    "apple-history.html",
    "travel.html", "tags/index.html",
    "privacy.html", "shesi-landing.html", "shesi-privacy.html",
} | _BRACELET_SHELLS
# 设计内就没有 H1 的页（跳转壳没有正文；加密壳的 H1 在密文里，解密后才注入）
H1_EXEMPT = {
    "console-gc.html", "console-n64.html", "console-wiiu.html",
    "apple-history.html",
    "travel.html", "tags/index.html",
} | _BRACELET_SHELLS


class TextGrab(HTMLParser):
    """只收可见文本节点；跳过 script/style/textarea/title 与 code/pre/kbd/samp。"""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.depth_skip = 0
        self.depth_code = 0
        self.chunks = []
        self.buf = []

    def handle_starttag(self, tag, attrs):
        if tag in SKIP_TEXT_TAGS:
            self.depth_skip += 1
            return
        if tag in CODE_TAGS:
            self.depth_code += 1
            return
        if tag in ("p", "div", "li", "h1", "h2", "h3", "h4", "br", "td", "th", "section"):
            self.buf.append("\n")

    def handle_endtag(self, tag):
        if tag in SKIP_TEXT_TAGS:
            self.depth_skip = max(0, self.depth_skip - 1)
            return
        if tag in CODE_TAGS:
            self.depth_code = max(0, self.depth_code - 1)
            return
        if tag in ("p", "div", "li", "h1", "h2", "h3", "h4", "td", "th", "section"):
            self.buf.append("\n")

    def handle_data(self, data):
        if self.depth_skip or self.depth_code:
            return
        self.chunks.append(data)

    def text(self):
        return "".join(self.chunks)


def audit_html(path):
    raw = open(path, encoding="utf-8", errors="replace").read()
    p = TextGrab()
    try:
        p.feed(raw)
    except Exception:
        pass
    txt = p.text()
    bad = [(ch, txt.count(ch)) for ch in ('"', "\u201c", "\u201d") if ch in txt]
    return {
        "bad_quotes": bad,
        "crumb": bool(re.search(r'class=["\']?breadcrumb\b', raw)),
        "meta": bool(re.search(r'class=["\']?page-meta\b', raw)),
        "cc": "BY-NC" in raw,
        "h1": bool(re.search(r"<h1[\s>]", raw)),
        "noindex": bool(re.search(r'name=["\']?robots["\']?[^>]*noindex', raw)),
        # 结构完整性：必须正常闭合。缺 </body>/</html> 时浏览器靠容错渲染，
        # 肉眼看不出来，但会让「往 </body> 前插脚本」的注入器退化成追加到文件末尾
        # （2026-09-19 体检发现 56 个 console 页自建站起就没闭合）。
        "unclosed": '<body' in raw and ('</body>' not in raw or '</html>' not in raw),
    }


def audit_json(root):
    """数据驱动的正文（news JSON / changelog / feed）也要查——只在 HTML 层归一管不到。"""
    out = []
    for dirpath, _dirs, files in os.walk(root):
        for f in sorted(files):
            if not f.endswith(".json"):
                continue
            fp = os.path.join(dirpath, f)
            rel = os.path.relpath(fp, root)
            try:
                d = json.load(open(fp, encoding="utf-8"))
            except Exception:
                continue

            def walk(o):
                if isinstance(o, dict):
                    for v in o.values():
                        yield from walk(v)
                elif isinstance(o, list):
                    for v in o:
                        yield from walk(v)
                elif isinstance(o, str):
                    yield o

            for v in walk(d):
                # 反引号包裹的行内代码（Markdown 片段）里的引号合法，先剔除
                if '"' in re.sub(r"`[^`]*`", "", v) or "\u201c" in v or "\u201d" in v:
                    out.append((rel, v[:70]))
                    break
    return out


def fetch_gh_pages(dest):
    """把 gh-pages 分支导出到 dest。

    不用 codeload / raw.githubusercontent（沙箱里常被拦或超时），走本地 git fetch ——
    push 既然能通，这条路就一定能通。
    """
    subprocess.run(
        ["git", "fetch", "origin", "gh-pages", "--depth=1", "-q"],
        cwd=REPO_ROOT, check=True,
    )
    rev = subprocess.run(
        ["git", "rev-parse", "--short", "origin/gh-pages"],
        cwd=REPO_ROOT, check=True, capture_output=True, text=True,
    ).stdout.strip()
    tar = subprocess.run(
        ["git", "archive", "--format=tar", "origin/gh-pages"],
        cwd=REPO_ROOT, check=True, capture_output=True,
    ).stdout
    with tempfile.NamedTemporaryFile(suffix=".tar", delete=False) as tmp:
        tmp.write(tar)
        tarpath = tmp.name
    os.makedirs(dest, exist_ok=True)
    with tarfile.open(tarpath) as tf:
        # filter="data" 需要 Python 3.11+；老解释器回落到默认行为
        try:
            tf.extractall(dest, filter="data")
        except TypeError:
            tf.extractall(dest)
    os.unlink(tarpath)
    return rev


def main():
    ap = argparse.ArgumentParser(description="逐页审计部署产物的观感一致性")
    ap.add_argument("--root", help="要审计的目录（默认自动拉 gh-pages）")
    ap.add_argument("--keep", action="store_true", help="保留导出的临时目录")
    args = ap.parse_args()

    tmpdir = None
    if args.root:
        root, rev = args.root, "(本地)"
    else:
        tmpdir = tempfile.mkdtemp(prefix="lx-audit-")
        rev = fetch_gh_pages(tmpdir)
        root = tmpdir
    try:
        rels = []
        for dirpath, _dirs, files in os.walk(root):
            for f in files:
                if f.endswith(".html"):
                    rels.append(os.path.relpath(os.path.join(dirpath, f), root))
        rels.sort()

        quote_bad, miss_crumb, miss_meta, miss_cc, miss_h1 = [], [], [], [], []
        unclosed = []
        skip_meta, noindex_cnt = [], 0

        for rel in rels:
            r = audit_html(os.path.join(root, rel))
            base = os.path.basename(rel)
            if r["bad_quotes"]:
                quote_bad.append((rel, r["bad_quotes"]))
            if r["noindex"]:
                noindex_cnt += 1
            if not r["crumb"] and rel != "index.html":
                miss_crumb.append(rel)
            if not r["h1"]:
                miss_h1.append(rel)
            if not r["meta"]:
                if r["noindex"] or rel == "index.html" or os.path.basename(rel) in STRUCTURE_EXEMPT:
                    skip_meta.append(rel)
                else:
                    miss_meta.append(rel)
            if not r["cc"]:
                miss_cc.append(rel)
            if r["unclosed"]:
                unclosed.append(rel)

        json_bad = audit_json(root)

        n = len(rels)
        ex_crumb = [r for r in miss_crumb if r in STRUCTURE_EXEMPT]
        ex_cc = [r for r in miss_cc if r in STRUCTURE_EXEMPT]
        ex_h1 = [r for r in miss_h1 if r in H1_EXEMPT]
        real_crumb = [r for r in miss_crumb if r not in ex_crumb]
        real_cc = [r for r in miss_cc if r not in ex_cc]
        real_h1 = [r for r in miss_h1 if r not in ex_h1]

        print(f"=== 部署产物审计 {rev}：{n} 个 HTML / {noindex_cnt} 个 noindex ===")
        print()
        print("--- 1. 正文引号（应为 0，代码块除外）---")
        if quote_bad:
            for rel, b in quote_bad:
                print("  BAD ", rel, b)
        else:
            print("  PASS  0 处直引号 / 弯引号残留")
        if json_bad:
            print(f"  JSON: {len(json_bad)} 个文件有残留")
            for rel, s in json_bad:
                print(f"    BAD  {rel} -> {s}")
        else:
            print("  PASS  数据 JSON 值内 0 处残留")
        print()
        print("--- 2. 骨架覆盖率（真实缺 = 扣除设计内豁免）---")
        print(f"  面包屑    : {n - len(miss_crumb)}/{n}  真实缺: {real_crumb or '无'}"
              f"  (豁免 {len(ex_crumb)})")
        print(f"  H1        : {n - len(miss_h1)}/{n}  真实缺: {real_h1 or '无'}"
              f"  (豁免 {len(ex_h1)})")
        print(f"  页尾信息块: {n - len(miss_meta) - len(skip_meta)}/{n}  真实缺: {miss_meta or '无'}"
              f"  (豁免 {len(skip_meta)} 个 noindex / 首页)")
        print(f"  CC 许可行 : {n - len(miss_cc)}/{n}  真实缺: {real_cc or '无'}"
              f"  (豁免 {len(ex_cc)})")
        print()
        print("--- 3. 结构完整性（</body>/</html> 必须闭合）---")
        if unclosed:
            print(f"  未闭合    : {len(unclosed)}/{n} 页")
            for rel in unclosed[:40]:
                print(f"    BAD  {rel}")
            if len(unclosed) > 40:
                print(f"    …另有 {len(unclosed) - 40} 页")
        else:
            print(f"  PASS  {n}/{n} 页均已正常闭合")

        ok = not (quote_bad or json_bad or miss_meta or real_cc or real_crumb
                  or real_h1 or unclosed)
        print()
        print("=== " + ("全绿 ✅" if ok else "有真实缺失 ❌") + " ===")
        return 0 if ok else 1
    finally:
        if tmpdir and not args.keep:
            shutil.rmtree(tmpdir, ignore_errors=True)
        elif tmpdir:
            print(f"\n导出目录保留在：{tmpdir}")


if __name__ == "__main__":
    sys.exit(main())
