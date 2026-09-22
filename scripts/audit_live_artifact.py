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

# 设计内就不该有面包屑 / CC 许可行的页（见下方两张表）。
#
# 🔴 2026-09-22 起：**跳转壳改为按特征自动豁免**（`_is_shell()`＝同时有 meta refresh + robots noindex）。
#    起因是一次真实 CI 失败：自动化把「7 个品类页转跳转壳」和「登记审计豁免」拆成了相邻两批提交，
#    中间那一批（6fc69d33）壳页已上线、豁免还没登记 → 本审计报真实缺面包屑/H1 → 部署被拦，
#    36 秒后下一批补上登记才自愈。**这类失败的本质是「豁免靠人工登记」**，于是改成按特征识别：
#    只要一页确实是跳转壳（refresh + noindex）就自动豁免 → **新增壳页不再需要任何登记**。
#    判定过的 12 个壳（2026-09-22 全量核对，目标页均正确，且不存在「有 refresh 无 noindex」的页）：
#      apple-history.html → apple.html#tab-hist（板块合并）
#      bracelet/{fengyan,longyan,magu,mengma,pinxiang,wuxing,zijinboyu}.html → ../bracelet.html（板块收缩）
#      console-{gc,n64,wiiu}.html → console-gamecube / console-nintendo-64 / console-wii-u.html（主机别名）
#      tags/index.html → /tags.html（Hugo 侧 301）
#
#    下面两张表因此**只登记「不靠跳转特征、另有设计原因」的页**（noindex 但无 refresh 的那类）。
#    ⚠️ 别再往这里加跳转壳——加进来是无效登记，还会掩盖「这一页的 refresh 掉了吗」这个真问题。
#    ⚠️ travel.html 在表里但**不是跳转壳**（它靠密文隐藏内容，没有 refresh），必须继续显式登记。
#
# ⚠️ 键一律写「相对产物根目录的路径」（如 tags/index.html），不要写裸文件名：
#    下面用 rel in SET 精确匹配。早期版本用 os.path.basename 匹配，
#    导致子目录里任何叫 index.html 的页根本没法登记进豁免表。
STRUCTURE_EXEMPT = {
    "404.html", "offline.html",
    "travel.html",              # 加密壳：页脚随内容一起加密，解锁后才出现
    "privacy.html", "shesi-landing.html", "shesi-privacy.html",   # App 独立法律页，不套本站免责声明
}
# 设计内就没有 H1 的页（加密壳的 H1 在密文里，解密后才注入）
H1_EXEMPT = {
    "travel.html",
}


def _is_shell(rec):
    """跳转壳判据：**同时**有 meta refresh 与 robots noindex。

    两条件缺一不可，避免误伤：
      - 只 noindex 没 refresh（如 404 / offline / privacy）→ 不是跳转壳，仍需骨架；
      - 只 refresh 没 noindex（正常页里不该出现）→ 不豁免，让它报出来引起注意。
    这样任何脚本/任何人新建的跳转壳都自动被识别，不需要再去登记两张表。
    """
    return bool(rec.get("refresh")) and bool(rec.get("noindex"))


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
        # 跳转壳特征：meta refresh。与 noindex 同时成立即可判定「这一页就是一张跳转页」，
        # 见下方 _is_shell()：这类页不该长骨架，按特征自动豁免，不必逐个登记。
        "refresh": bool(re.search(r'<meta[^>]+http-equiv=["\']?refresh', raw, re.I)),
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
        skip_meta, noindex_cnt, shell_pages = [], 0, set()

        for rel in rels:
            r = audit_html(os.path.join(root, rel))
            base = os.path.basename(rel)
            if r["bad_quotes"]:
                quote_bad.append((rel, r["bad_quotes"]))
            if r["noindex"]:
                noindex_cnt += 1
            if _is_shell(r):
                shell_pages.add(rel)
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
        ex_crumb = [r for r in miss_crumb if r in STRUCTURE_EXEMPT or r in shell_pages]
        ex_cc = [r for r in miss_cc if r in STRUCTURE_EXEMPT or r in shell_pages]
        ex_h1 = [r for r in miss_h1 if r in H1_EXEMPT or r in shell_pages]
        real_crumb = [r for r in miss_crumb if r not in ex_crumb]
        real_cc = [r for r in miss_cc if r not in ex_cc]
        real_h1 = [r for r in miss_h1 if r not in ex_h1]

        def ex_note(ex_list, reg_set):
            """豁免数拆成「登记 / 跳转壳自动」两段，便于一眼看出自动识别是否在起作用。"""
            auto = len([r for r in ex_list if r in shell_pages and r not in reg_set])
            reg = len(ex_list) - auto
            return f"(豁免 {len(ex_list)} = 登记 {reg} + 跳转壳自动 {auto})"

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
              f"  {ex_note(ex_crumb, STRUCTURE_EXEMPT)}")
        print(f"  H1        : {n - len(miss_h1)}/{n}  真实缺: {real_h1 or '无'}"
              f"  {ex_note(ex_h1, H1_EXEMPT)}")
        print(f"  页尾信息块: {n - len(miss_meta) - len(skip_meta)}/{n}  真实缺: {miss_meta or '无'}"
              f"  (豁免 {len(skip_meta)} 个 noindex / 首页)")
        print(f"  CC 许可行 : {n - len(miss_cc)}/{n}  真实缺: {real_cc or '无'}"
              f"  {ex_note(ex_cc, STRUCTURE_EXEMPT)}")
        print(f"  （跳转壳：{len(shell_pages)} 页按 meta refresh + noindex 特征自动豁免）")
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
