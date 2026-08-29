#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
将站点内手写静态 HTML 文章页里的 Gitalk 评论块，批量替换为 giscus 评论块，
并给每页的内联 CSP 补上 giscus.app 域名（script-src / style-src / connect-src）。

背景：Gitalk 依赖 *.workers.dev 自建 CORS 代理，在大陆被墙；且 GitHub 已删除
修改 OAuth callback URL 的 API，只能手动改。giscus 纯前端直连 GitHub Discussions，
国内访客可用，无自建代理。

运行：python3 scripts/migrate_gitalk_to_giscus.py
可重复运行（已替换的会被跳过）。
"""
import glob
import re

GISCUS_BLOCK = """<!-- giscus 评论（底部，第三方，存于 GitHub Discussions；纯前端无需自建代理） -->
<div class="giscus-comments" aria-label="评论区"></div>
<script src="https://giscus.app/client.js"
        data-repo="jinlong0221/personal-site"
        data-repo-id="R_kgDOTA19Vw"
        data-category="General"
        data-mapping="pathname"
        data-strict="0"
        data-reactions-enabled="1"
        data-emit-metadata="0"
        data-input-position="bottom"
        data-theme="preferred_color_scheme"
        data-lang="zh-CN"
        data-loading="lazy"
        crossorigin="anonymous"
        async>
</script>
"""

# 匹配 gitalk 块：可选的前置注释 + 固定两行
GITALK_RE = re.compile(
    r'(?:<!--[^\n]*Gitalk[^\n]*-->\n)?'
    r'<div class="gitalk-container"[^>]*>\s*</div>\n'
    r'<script src="/js/gitalk-init\.js" defer></script>\n'
)


CSP_META_RE = re.compile(
    r'(<meta http-equiv="Content-Security-Policy" content=")([^"]*)(")'
)

# giscus 需要放行的三个 CSP 指令
CSP_TARGETS = ("script-src", "style-src", "connect-src")


def fix_csp(txt: str) -> str:
    """给内联 CSP 的 script-src / style-src / connect-src 各补上 giscus.app。

    注意：这里必须只针对 CSP meta 的 content 判断，不能用整份文件文本判断——
    否则 gitalk 块被替换成含 giscus.app 的脚本后会误触发"已处理"，导致 CSP 漏改。
    """
    m = CSP_META_RE.search(txt)
    if not m:
        return txt
    csp = m.group(2)
    if "giscus.app" in csp:
        return txt
    parts = []
    for part in csp.split("; "):
        name = part.split(" ")[0]
        if name in CSP_TARGETS and "giscus.app" not in part:
            part = part + " https://giscus.app"
        parts.append(part)
    new_csp = "; ".join(parts)
    return txt[: m.start(2)] + new_csp + txt[m.end(2) :]


def main():
    files = glob.glob("static/**/*.html", recursive=True)
    updated = 0
    for f in files:
        with open(f, "r", encoding="utf-8") as fh:
            txt = fh.read()
        # 两种文件都要处理：仍带 gitalk 块的（待替换），
        # 或已换成 giscus 块但 CSP 还没放行的（补 CSP）。
        if (
            "gitalk-init.js" not in txt
            and "gitalk-container" not in txt
            and "giscus.app/client.js" not in txt
        ):
            continue
        new = GITALK_RE.sub(GISCUS_BLOCK, txt)
        new = fix_csp(new)
        if new != txt:
            with open(f, "w", encoding="utf-8") as fh:
                fh.write(new)
            updated += 1
            print("updated", f)
    print(f"\nTotal updated: {updated}")


if __name__ == "__main__":
    main()
