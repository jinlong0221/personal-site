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
# Hugo 模板导航：与静态页共用同一份定义，避免「首页 = 一套、子页 = 另一套」的漂移
NAVBAR_TPL = os.path.join(os.path.dirname(STATIC_DIR), "layouts", "partials", "navbar.html")

# 6 大主题类目（顺序即展示顺序）：顶栏直达 + 「更多」按类目分组
# 分组理由：把 24 个入口按「同一维度」归族，消除"车与机里塞漫威""乡与家里塞高考"式的混搭。
CATEGORIES = [
    ("风物志", [
        ("health-tea.html", "养生茶"),
        ("bracelet.html", "文玩手串"),
        ("zisha.html", "紫砂艺术"),
    ]),
    ("车与数码", [
        ("tesla.html", "特斯拉"),
        ("apple.html", "苹果新品"),
        ("apple-history.html", "苹果产品发展史"),
        ("ev-sales.html", "新能源销量榜"),
        ("ev-charge.html", "充电桩查询"),
    ]),
    ("游戏影游", [
        ("console.html", "主机图鉴"),
        ("games.html", "玩过的游戏"),
        ("chinajoy.html", "ChinaJoy 成长史"),
        ("marvel.html", "漫威宇宙"),
    ]),
    ("射阳本地", [
        ("xintan-weather.html", "农田气象"),
        ("typhoon.html", "台风监测"),
        ("sheyang.html", "射阳天气"),
        ("guanghui.html", "光辉电力"),
    ]),
    ("生活工具", [
        ("calendar.html", "万年历"),
        ("gaokao.html", "高考查分"),
        ("tags.html", "标签聚合"),
        ("bookmarks.html", "我的收藏"),
    ]),
    ("关于我", [
        ("notes.html", "站长手记"),
        ("pitfalls.html", "踩坑记"),
        ("changelog.html", "更新日志"),
        ("status-history.html", "站点状态"),
        ("about.html", "关于本站"),
        ("rss.xml", "RSS 订阅"),
    ]),
]
# 独立入口：刻意低调、不归入任一主题类目（加密相册等隐私内容）
INDEPENDENT = [
    ("travel.html", "家庭旅行"),
]
# 顶栏直达：每个类目一个入口（指向该类目旗舰页），顺序即展示顺序
DESKTOP = [
    ("zisha.html", "风物志"),
    ("tesla.html", "车与数码"),
    ("console.html", "游戏影游"),
    ("typhoon.html", "射阳本地"),
    ("calendar.html", "生活工具"),
    ("about.html", "关于我"),
]
# 兼容旧引用（「更多」下拉 = 各类目成员汇总；移动端 = 首页 + 分组全量）
DROPDOWN = [item for _, items in CATEGORIES for item in items]
MOBILE = [("index.html", "首页")] + DROPDOWN

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
    # 「更多」下拉：按 6 大主题类目分组（分组标题 + 成员）
    _drop = []
    for _cat, _items in CATEGORIES:
        _drop.append(f'          <span class="nav-more-hd">{_cat}</span>')
        for t, name in _items:
            _drop.append(f'          <a href="{href(t)}"{cls(t)}>{name}</a>')
    if INDEPENDENT:
        _drop.append('          <span class="nav-more-div"></span>')
        for t, name in INDEPENDENT:
            _drop.append(f'          <a href="{href(t)}"{cls(t)}>{name}</a>')
    drop_links = "\n".join(_drop)
    # 移动端：首页 + 分组标题 + 成员
    _home = href("index.html")
    _mob = [f'  <a href="{_home}">首页</a>']
    for _cat, _items in CATEGORIES:
        _mob.append(f'  <span class="nav-hd">{_cat}</span>')
        for t, name in _items:
            _mob.append(f'  <a href="{href(t)}">{name}</a>')
    if INDEPENDENT:
        _mob.append('  <span class="nav-hd-div"></span>')
        for t, name in INDEPENDENT:
            _mob.append(f'  <a href="{href(t)}">{name}</a>')
    mob_links = "\n".join(_mob)
    return f'''<nav class="navbar" role="navigation" aria-label="主导航">
  <div class="navbar-inner">
    <a href="{href('index.html')}" class="logo" aria-label="龙兄知识库首页">
      <svg class="lx-seal lx-seal-sm" viewBox="0 0 100 100" aria-hidden="true"><rect x="4" y="4" width="92" height="92" rx="7" fill="none" stroke="currentColor" stroke-width="8"/><text class="lx-brush" x="50" y="53" font-size="50" fill="currentColor" text-anchor="middle" dominant-baseline="middle">龙</text></svg>
      <span>龙兄</span>
    </a>
    <a href="{href('calendar.html')}" class="nav-clock-link" id="navClockLink" title="点击查看万年历" aria-label="点击查看万年历"><span id="navClock" class="nav-clock" title="当前时间"></span></a>
    <span class="nav-weather" id="navWeather" data-nav="{href('sheyang.html')}" style="cursor:pointer;" title="点击查看当地天气详情">{SVG_WEATHER}</span>
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
    """从原 nav 中读出 active 链接的裸目标（去掉 ../ 前缀）。"""
    m = re.search(r'<a\b[^>]*\bactive\b[^>]*>', html)
    if not m:
        return None
    hm = re.search(r'href="([^"]+)"', m.group(0))
    if not hm:
        return None
    return re.sub(r'^(\.\./)+', '', hm.group(1))


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
    # 旅行加密相册的部署产物：正文由 TRAVEL_KEY 重新加密生成，但「外壳导航」是明文，
    # 且不在 static/ 下，此前一直漏同步（改名后仍挂着旧版导航）。这里单独补上；
    # 只替换 <nav>，不碰密文与密码门，guard_travel_dist.sh 的判据不受影响。
    extra_root = os.path.join(os.path.dirname(STATIC_DIR), "travel-dist")
    for fn in ("travel.html",):
        p = os.path.join(extra_root, fn)
        if not os.path.exists(p):
            continue
        res = process_file(p, check_only, base_dir=extra_root)
        if res.startswith("updated"):
            count["updated"] += 1
            changed.append((os.path.join("travel-dist", fn), res))
        elif res == "unchanged":
            count["unchanged"] += 1
        else:
            count["skip"] += 1
    # 同步 Hugo 模板导航（首页等经 Hugo 渲染的页面用它），与静态页共用同一份定义
    tpl_res = "unchanged"
    try:
        with open(NAVBAR_TPL, "r", encoding="utf-8") as f:
            old_tpl = f.read()
    except FileNotFoundError:
        old_tpl = ""
    new_tpl = build_nav("{{ .Site.BaseURL }}", None) + "\n"
    if new_tpl != old_tpl:
        tpl_res = "updated"
        if not check_only:
            with open(NAVBAR_TPL, "w", encoding="utf-8") as f:
                f.write(new_tpl)

    print(f"[sync_navbar] check_only={check_only}")
    print(f"  updated={count['updated']} unchanged={count['unchanged']} skip={count['skip']} | navbar.html={tpl_res}")
    for name, res in changed[:20]:
        print(f"  + {name}: {res}")
    if len(changed) > 20:
        print(f"  ... and {len(changed) - 20} more")
    if check_only and count["updated"] == 0:
        print("  无需改动。")


if __name__ == "__main__":
    main()
