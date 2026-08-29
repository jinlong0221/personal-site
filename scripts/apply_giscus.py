#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
向“文章页”静态 HTML（含 seo-art-head 标记的页面）注入 giscus 评论块，
并把残留的 Gitalk 评论块替换为 giscus 块；同时给每个页面的内联 CSP
补上 giscus.app（script-src / style-src / connect-src）。

幂等：已含 giscus 块则跳过注入；CSP 已放行则跳过。
取代原 scripts/apply_gitalk.py。

背景：Gitalk 依赖 *.workers.dev 自建 CORS 代理，在大陆被墙；
且 GitHub 已删除修改 OAuth App callback URL 的 API。giscus 纯前端直连
GitHub Discussions，不依赖自建代理，国内可用。

用法：
  python3 scripts/apply_giscus.py            # 写入
  python3 scripts/apply_giscus.py --check    # 仅检查
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKIP_DIR_PARTS = {"admin", "pagefind", "js", "css", "img", "data", "fonts"}

GISCUS_BLOCK = (
    "\n<!-- giscus 评论（底部，第三方，存于 GitHub Discussions；纯前端无需自建代理） -->\n"
    '<div class="giscus-comments" aria-label="评论区"></div>\n'
    '<script src="https://giscus.app/client.js"\n'
    '        data-repo="jinlong0221/personal-site"\n'
    '        data-repo-id="R_kgDOTA19Vw"\n'
    '        data-category="General"\n'
    '        data-mapping="pathname"\n'
    '        data-strict="0"\n'
    '        data-reactions-enabled="1"\n'
    '        data-emit-metadata="0"\n'
    '        data-input-position="bottom"\n'
    '        data-theme="preferred_color_scheme"\n'
    '        data-lang="zh-CN"\n'
    '        data-loading="lazy"\n'
    '        crossorigin="anonymous"\n'
    "        async>\n"
    "</script>\n"
)

# 残留的 Gitalk 块：可选前置注释 + 固定两行
GITALK_RE = re.compile(
    r"(?:<!--[^\n]*Gitalk[^\n]*-->\n)?"
    r'<div class="gitalk-container"[^>]*>\s*</div>\n'
    r'<script src="/js/gitalk-init\.js" defer></script>\n'
)

CSP_META_RE = re.compile(
    r'(<meta http-equiv="Content-Security-Policy" content=")([^"]*)(")'
)

# giscus 需要放行的 CSP 指令（frame-src 在 fix_csp 里单独处理，因为原值是 'none'）
CSP_TARGETS = ("script-src", "style-src", "connect-src")


def fix_csp(txt: str) -> str:
    """给内联 CSP 补齐 giscus 所需放行：script-src / style-src / connect-src / frame-src。

    两个易踩的坑：
    1. 不能拿"整份文件文本"判断是否已含 giscus.app——注入的 giscus 脚本本身就
       含该域名，会导致提前返回、CSP 漏改。这里只解析 CSP meta 的 content。
    2. frame-src 必须单独处理：站点原 CSP 是 frame-src 'none'（禁止一切 iframe），
       而 giscus 是在 iframe 里渲染的，不把 'none' 换掉的话评论区整个被浏览器屏蔽。
       同样不能用"整体是否已含 giscus.app"提前返回，否则补完前三项后就轮不到它。
    """
    m = CSP_META_RE.search(txt)
    if not m:
        return txt
    csp = m.group(2)
    parts = []
    changed = False
    for part in csp.split("; "):
        name = part.split(" ")[0]
        if name == "frame-src" and "giscus.app" not in part:
            if "'none'" in part:
                part = " ".join(part.replace("'none'", "").split()) + " https://giscus.app"
            else:
                part = part + " https://giscus.app"
            changed = True
        elif name in CSP_TARGETS and "giscus.app" not in part:
            part = part + " https://giscus.app"
            changed = True
        parts.append(part)
    if not changed:
        return txt
    new_csp = "; ".join(parts)
    return txt[: m.start(2)] + new_csp + txt[m.end(2) :]


def process_file(path, check_only=False):
    with open(path, "r", encoding="utf-8") as f:
        html = f.read()

    changed = False

    # 1) 残留 Gitalk 块 → giscus 块
    if GITALK_RE.search(html):
        html = GITALK_RE.sub(GISCUS_BLOCK, html)
        changed = True
    # 2) 文章页尚未注入评论 → 注入 giscus 块
    elif (
        "seo-art-head" in html
        and "giscus.app/client.js" not in html
        and "</body>" in html
    ):
        html = html.replace("</body>", GISCUS_BLOCK + "</body>", 1)
        changed = True

    # 3) 补齐 CSP（只对已带评论块或本身就是文章页的页面）
    if "giscus.app/client.js" in html or "seo-art-head" in html:
        new_html = fix_csp(html)
        if new_html != html:
            html = new_html
            changed = True

    if changed and not check_only:
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)
    return changed


def main():
    check_only = "--check" in sys.argv
    count = 0
    for dirpath, dirnames, filenames in os.walk(os.path.join(ROOT, "static")):
        parts = set(os.path.relpath(dirpath, ROOT).split(os.sep))
        if parts & SKIP_DIR_PARTS:
            continue
        for fn in filenames:
            if not fn.endswith(".html"):
                continue
            full = os.path.join(dirpath, fn)
            if process_file(full, check_only=check_only):
                count += 1
                if check_only:
                    print("  would change:", os.path.relpath(full, ROOT))
    print(
        ("[check] " if check_only else "[done] ")
        + f"注入/迁移 giscus 评论的页面: {count}"
    )


if __name__ == "__main__":
    main()
