#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sync_navbar.py — 用 layouts/partials/navbar.html 单一模板统一全站静态页导航栏。

为什么存在：
  static/*.html 不经 Hugo 模板渲染，无法用 partial。此前各静态页各自维护导航，
  曾出现「下拉缺入口、抽屉缺入口、整页旧版导航」三类漂移（2026-10-25 审计：
  104 页下拉缺 AI 提示词库、changelog 缺本地生活 8 入口、herbs/ai-prompts
  整页旧版导航且抽屉含重复项）。

单一数据源（2026-10-25 重构）：
  本脚本曾内置一份 CATEGORIES 硬编码定义，与 partial 双轨维护 → 必然漂移。
  现改为**直接解析 partial**：顶栏直达项、「更多」下拉分组、移动端抽屉分组
  全部从 navbar.html 读出，静态页按目录深度加 ../ 前缀重新生成。
  改导航只改一处（partial），跑一次本脚本即全站同步。

保证：
  1. 下拉与移动端菜单内容全站一致（含付费内容/AI 提示词库、本地生活 8 入口）
  2. 各页相对路径按目录深度自动加 ../ 前缀（depth0 顶层 / depth1+ 子目录）
  3. active 高亮：优先按本页文件名匹配菜单项，匹配不到再回退读旧导航
  4. 导航外壳（logo/时钟/搜索/主题/分享/汉堡）与 partial 逐字一致

用法：
  python3 scripts/sync_navbar.py           # 执行并写回
  python3 scripts/sync_navbar.py --check   # 只报告会改动哪些文件，不写回
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_DIR = os.path.join(ROOT, "static")
# Hugo 模板导航 = 单一数据源；静态页与 Hugo 页共用同一份定义
NAVBAR_TPL = os.path.join(ROOT, "layouts", "partials", "navbar.html")

SVG_SEARCH = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>'
SVG_SHARE = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><line x1="8.59" y1="13.51" x2="15.42" y2="17.49"/><line x1="15.41" y1="6.51" x2="8.59" y2="10.49"/></svg>'
SVG_SUN = '<svg class="icon-sun" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="4"/><line x1="12" y1="2" x2="12" y2="5"/><line x1="12" y1="19" x2="12" y2="22"/><line x1="2" y1="12" x2="5" x2="12"/><line x1="19" y1="12" x2="22" y2="12"/><line x1="4.9" y1="4.9" x2="7" y2="7"/><line x1="17" y1="17" x2="19.1" y2="19.1"/><line x1="4.9" y1="19.1" x2="7" y2="17"/><line x1="17" y1="7" x2="19.1" y2="4.9"/></svg>'
SVG_MOON = '<svg class="icon-moon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M21 12.8A9 9 0 1111.2 3 7 7 0 0021 12.8z"/></svg>'


# ---------------------------------------------------------------- partial 解析
def _read_tpl():
    with open(NAVBAR_TPL, "r", encoding="utf-8") as f:
        return f.read()


def _extract_tag_block(html, open_pat):
    """取出 open_pat 匹配的标签对应的完整块（按 <div 深度配平）。"""
    m = re.search(open_pat, html)
    if not m:
        return None
    i = m.end()
    depth = 1
    while i < len(html) and depth:
        if html.startswith("<div", i):
            depth += 1
        elif html.startswith("</div>", i):
            depth -= 1
        i += 1
    return html[m.start():i]


def _parse_items(block):
    """把菜单块解析成有序序列：
    ('hd', 组名) | ('div',) | ('link', 裸slug, 文案)
    """
    out = []
    for m in re.finditer(
        r'<span class="nav-more-hd">([^<]+)</span>'
        r'|<span class="nav-more-hd-div"></span>'
        r'|<span class="nav-hd">([^<]+)</span>'
        r'|<span class="nav-hd-div"></span>'
        r'|<span class="nav-more-div"></span>'
        r'|<a\s+class="active"\s+href="[^"]*?([\w-]+\.(?:html|xml))"[^>]*>([^<]+)</a>'
        r'|<a href="[^"]*?([\w-]+\.(?:html|xml))"[^>]*>([^<]+)</a>',
        block,
    ):
        if m.group(1):
            out.append(("hd", m.group(1)))
        elif m.group(2):
            out.append(("hd", m.group(2)))
        elif m.group(3):
            out.append(("link", m.group(3), m.group(4)))
        elif m.group(5):
            out.append(("link", m.group(5), m.group(6)))
        elif "div" in (m.group(0) or ""):
            out.append(("div",))
    return out


def parse_partial():
    """从 partial 读出：顶栏直达 / 下拉序列 / 抽屉序列。"""
    tpl = _read_tpl()
    ul_m = re.search(r'<ul class="nav-links">(.*?)</ul>', tpl, re.S)
    desktop = []
    if ul_m:
        for m in re.finditer(
            r'<li><a href="[^"]*?([\w-]+\.(?:html|xml))"[^>]*>([^<]+)</a></li>', ul_m.group(1)
        ):
            desktop.append((m.group(1), m.group(2)))
    dropdown = _parse_items(_extract_tag_block(tpl, r'<div class="nav-more-dropdown">'))
    drawer = _parse_items(_extract_tag_block(tpl, r'<div class="mobile-nav" id="mobileNav">'))
    if not desktop or not dropdown or not drawer:
        raise SystemExit("partial 解析失败：顶栏/下拉/抽屉有一项为空，请检查 navbar.html 结构")
    return desktop, dropdown, drawer


# ---------------------------------------------------------------- 导航生成
def build_nav(prefix, active_bare):
    """按 partial 结构生成导航；prefix 为 URL 前缀（相对路径或 Hugo baseURL token）。"""
    desktop, dropdown, drawer = parse_partial()

    def href(slug):
        return prefix + slug

    def cls(slug):
        return ' class="active"' if slug == active_bare else ""

    nav_links = "\n".join(
        f'      <li><a href="{href(s)}"{cls(s)}>{n}</a></li>' for s, n in desktop
    )
    drop_lines = []
    for item in dropdown:
        if item[0] == "hd":
            drop_lines.append(f'          <span class="nav-more-hd">{item[1]}</span>')
        elif item[0] == "div":
            drop_lines.append('          <span class="nav-more-div"></span>')
        else:
            _, s, n = item
            drop_lines.append(f'          <a href="{href(s)}"{cls(s)}>{n}</a>')
    mob_lines = []
    for item in drawer:
        if item[0] == "hd":
            mob_lines.append(f'  <span class="nav-hd">{item[1]}</span>')
        elif item[0] == "div":
            mob_lines.append('  <span class="nav-hd-div"></span>')
        else:
            _, s, n = item
            mob_lines.append(f'  <a href="{href(s)}">{n}</a>')
    drop_links = "\n".join(drop_lines)
    mob_links = "\n".join(mob_lines)
    return f'''<nav class="navbar" role="navigation" aria-label="主导航">
  <div class="navbar-inner">
    <a href="{href('index.html')}" class="logo" aria-label="龙兄知识库首页">
      <svg class="lx-seal lx-seal-sm" viewBox="0 0 100 100" aria-hidden="true"><rect x="4" y="4" width="92" height="92" rx="7" fill="none" stroke="currentColor" stroke-width="8"/><text class="lx-brush" x="50" y="53" font-size="50" fill="currentColor" text-anchor="middle" dominant-baseline="middle">龙</text></svg>
      <span>龙兄</span>
    </a>
    <a href="{href('calendar.html')}" class="nav-clock-link" id="navClockLink" title="点击查看万年历" aria-label="点击查看万年历"><span id="navClock" class="nav-clock" title="当前时间"></span></a>
    <ul class="nav-links">
{nav_links}
      <li class="nav-more-wrap">
        <button type="button" class="nav-more-btn">更多 ▾</button>
        <div class="nav-more-dropdown">
{drop_links}
        </div>
      </li>
    </ul>
    <div class="nav-actions">
      <button class="icon-btn" id="searchBtn" aria-label="搜索" title="搜索">
        {SVG_SEARCH}
      </button>
      <button class="icon-btn" id="themeToggle" aria-label="切换主题" title="切换主题">
        {SVG_SUN}
        {SVG_MOON}
      </button>
      <button class="icon-btn" id="shareBtn" aria-label="分享" title="分享到微信">
        {SVG_SHARE}
      </button>
      <button class="hamburger" id="hamburger" aria-label="打开菜单" aria-expanded="false">
        <span></span><span></span><span></span>
      </button>
    </div>
  </div>
  <div class="mobile-nav" id="mobileNav">
{mob_links}
  </div>
</nav>'''


def extract_active_bare(html):
    """回退方案：从旧 nav 中读出 active 链接的裸目标（去掉 ../ 前缀）。"""
    m = re.search(r'<a\b[^>]*\bactive\b[^>]*>', html)
    if not m:
        return None
    hm = re.search(r'href="([^"]+)"', m.group(0))
    if not hm:
        return None
    return re.sub(r"^(\.\./)+", "", hm.group(1))


def menu_slugs():
    """partial 菜单覆盖的全部裸 slug（顶栏 + 下拉 + 抽屉）。"""
    desktop, dropdown, drawer = parse_partial()
    slugs = {s for s, _ in desktop}
    for item in dropdown + drawer:
        if item[0] == "link":
            slugs.add(item[1])
    return slugs


def process_file(path, check_only=False, base_dir=None):
    base_dir = base_dir or STATIC_DIR
    with open(path, "r", encoding="utf-8") as f:
        html = f.read()
    m = re.search(r'<nav class="navbar".*?</nav>', html, re.S)
    if not m:
        return "skip(no-nav)"
    orig = m.group(0)
    rel = os.path.relpath(path, base_dir)
    depth = rel.count(os.sep)
    prefix = "../" * depth
    # active：优先按本页文件名匹配（自身在菜单里就高亮），否则回退读旧导航
    own = os.path.basename(rel)
    active_bare = own if own in menu_slugs() else extract_active_bare(orig)
    new_nav = build_nav(prefix, active_bare)
    if new_nav == orig:
        return "unchanged"
    new_html = html[: m.start()] + new_nav + html[m.end():]
    if not check_only:
        with open(path, "w", encoding="utf-8") as f:
            f.write(new_html)
    return f"updated(depth={depth},active={active_bare})"


def iter_targets():
    """全部待同步页面：static/ 递归 + travel-dist 部署产物。"""
    for root, _, files in os.walk(STATIC_DIR):
        for fn in files:
            if fn.endswith(".html"):
                yield os.path.join(root, fn), STATIC_DIR
    extra = os.path.join(ROOT, "travel-dist", "travel.html")
    if os.path.exists(extra):
        # 旅行加密相册部署产物：只换外壳导航，不碰密文（guard_travel_dist 判据不受影响）
        yield extra, os.path.join(ROOT, "travel-dist")


def main():
    check_only = "--check" in sys.argv
    count = {"updated": 0, "unchanged": 0, "skip": 0}
    changed = []
    for p, base in iter_targets():
        res = process_file(p, check_only, base_dir=base)
        if res.startswith("updated"):
            count["updated"] += 1
            changed.append((os.path.relpath(p, ROOT), res))
        elif res == "unchanged":
            count["unchanged"] += 1
        else:
            count["skip"] += 1
    print(f"[sync_navbar] check_only={check_only}")
    print(f"  updated={count['updated']} unchanged={count['unchanged']} skip={count['skip']}")
    for name, res in changed[:20]:
        print(f"  + {name}: {res}")
    if len(changed) > 20:
        print(f"  ... and {len(changed) - 20} more")
    if check_only and count["updated"] == 0:
        print("  无需改动。")
    return 1 if (check_only and count["updated"]) else 0


if __name__ == "__main__":
    sys.exit(main())
