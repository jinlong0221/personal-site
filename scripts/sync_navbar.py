#!/usr/bin/env python3
"""
sync_navbar.py — 用单一规范模板统一生成全站静态页导航栏。

为什么存在：
  static/*.html 不经 Hugo 模板渲染，无法用 partial。此前 160 个静态页各自
  手写了几乎相同的 <nav>，导致 emoji 满天飞、首页与子页下拉不一致。
  本脚本以一个规范模板为所有静态页重新生成导航栏，保证：
    1. 完全去 emoji（天气/主题切换改 SVG，移动端链接去 emoji 前缀）
    2. 各页相对路径按目录深度自动加 ../ 前缀（depth0 顶层 / depth1 子目录）
    3. 保留各页原有的 active 高亮（从原 nav 读取 active 链接）
    4. 下拉与移动端菜单内容全站一致（含光辉电力）

用法：
  python3 scripts/sync_navbar.py           # 执行并写回
  python3 scripts/sync_navbar.py --check   # 只报告会改动哪些文件，不写回

注意：只替换 <nav class="navbar" ...>...</nav> 块，页面其余内容不动。幂等。
"""
import os
import re
import sys

STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static")

# 桌面主导航（顺序即展示顺序）
DESKTOP = [
    ("herbs/chenxiang.html", "沉香鉴别"),
    ("herbs.html", "中药材"),
    ("health-tea.html", "养生茶"),
    ("bracelet.html", "文玩手串"),
    ("tesla.html", "特斯拉"),
    ("marvel.html", "漫威宇宙"),
    ("xintan-weather.html", "农田气象"),
    ("zisha.html", "紫砂艺术"),
    ("console.html", "游戏主机"),
]
# “更多”下拉
DROPDOWN = [
    ("travel.html", "家庭旅行"),
    ("microblog.html", "碎碎念"),
    ("chinajoy.html", "ChinaJoy 成长史"),
    ("guanghui.html", "光辉电力"),
    ("gaokao.html", "高考查分"),
    ("pitfalls.html", "踩坑记"),
    ("typhoon.html", "台风监测"),
    ("games.html", "游戏库"),
    ("about.html", "关于本站"),
]
MOBILE = [("index.html", "首页")] + DESKTOP + DROPDOWN

SVG_SEARCH = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>'
SVG_SHARE = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><line x1="8.59" y1="13.51" x2="15.42" y2="17.49"/><line x1="15.41" y1="6.51" x2="8.59" y2="10.49"/></svg>'
SVG_SUN = '<svg class="icon-sun" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><circle cx="12" cy="12" r="4"/><line x1="12" y1="2" x2="12" y2="5"/><line x1="12" y1="19" x2="12" y2="22"/><line x1="2" y1="12" x2="5" y2="12"/><line x1="19" y1="12" x2="22" y2="12"/><line x1="4.9" y1="4.9" x2="7" y2="7"/><line x1="17" y1="17" x2="19.1" y1="19.1"/><line x1="4.9" y1="19.1" x2="7" y2="17"/><line x1="17" y1="7" x2="19.1" y1="4.9"/></svg>'
SVG_MOON = '<svg class="icon-moon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M21 12.8A9 9 0 1111.2 3 7 7 0 0021 12.8z"/></svg>'
SVG_WEATHER = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M7 18a4 4 0 010-8 5 5 0 019.6-1.5A4 4 0 0118 18H7z"/></svg>'


def build_nav(prefix, active_bare):
    def href(t):
        return prefix + t

    def cls(t):
        return ' class="active"' if t == active_bare else ''

    nav_links = "\n".join(
        f'      <li><a href="{href(t)}"{cls(t)}>{name}</a></li>' for t, name in DESKTOP
    )
    drop_links = "\n".join(
        f'          <a href="{href(t)}"{cls(t)}>{name}</a>' for t, name in DROPDOWN
    )
    mob_links = "\n".join(
        f'  <a href="{href(t)}">{name}</a>' for t, name in MOBILE
    )
    return f'''<nav class="navbar" role="navigation" aria-label="主导航">
  <div class="navbar-inner">
    <a href="{href('index.html')}" class="logo" aria-label="龙兄知识库首页">
      <svg class="lx-seal lx-seal-sm" viewBox="0 0 100 100" aria-hidden="true"><rect x="4" y="4" width="92" height="92" rx="7" fill="none" stroke="currentColor" stroke-width="8"/><text class="lx-brush" x="50" y="53" font-size="50" fill="currentColor" text-anchor="middle" dominant-baseline="middle">龙</text></svg>
      <span>龙兄知识库</span>
    </a>
    <a href="{href('calendar.html')}" class="nav-clock-link" id="navClockLink" title="点击查看万年历" aria-label="点击查看万年历"><span id="navClock" class="nav-clock" title="当前时间"></span></a>
    <span class="nav-weather" id="navWeather" onclick="location.href='{href('sheyang.html')}'" style="cursor:pointer;" title="点击查看当地天气详情">{SVG_WEATHER}</span>
    <ul class="nav-links">
{nav_links}
      <li class="nav-more-wrap">
        <button type="button" class="nav-more-btn" onclick="var w=this.parentElement;w.classList.toggle('open');event.stopPropagation();">更多 ▾</button>
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
    """从原 nav 中读出 active 链接的裸目标（去掉 ../ 前缀）。"""
    m = re.search(r'<a\b[^>]*\bactive\b[^>]*>', html)
    if not m:
        return None
    hm = re.search(r'href="([^"]+)"', m.group(0))
    if not hm:
        return None
    return re.sub(r'^(\.\./)+', '', hm.group(1))


def process_file(path, check_only=False):
    with open(path, "r", encoding="utf-8") as f:
        html = f.read()
    m = re.search(r'<nav class="navbar".*?</nav>', html, re.S)
    if not m:
        return "skip(no-nav)"
    orig = m.group(0)
    rel = os.path.relpath(path, STATIC_DIR)
    depth = rel.count(os.sep)
    prefix = "../" * depth
    active_bare = extract_active_bare(orig)
    new_nav = build_nav(prefix, active_bare)
    if new_nav == orig:
        return "unchanged"
    new_html = html[: m.start()] + new_nav + html[m.end():]
    if not check_only:
        with open(path, "w", encoding="utf-8") as f:
            f.write(new_html)
    return f"updated(depth={depth},active={active_bare})"


def main():
    check_only = "--check" in sys.argv
    count = {"updated": 0, "unchanged": 0, "skip": 0}
    changed = []
    for root, _, files in os.walk(STATIC_DIR):
        for fn in files:
            if not fn.endswith(".html"):
                continue
            p = os.path.join(root, fn)
            res = process_file(p, check_only)
            if res.startswith("updated"):
                count["updated"] += 1
                changed.append((os.path.relpath(p, STATIC_DIR), res))
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


if __name__ == "__main__":
    main()
