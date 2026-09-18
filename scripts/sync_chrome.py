#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sync_chrome.py — 全站静态页「页面骨架」统一器（面包屑 / 标题 / 页尾信息块 / 页脚）

## 为什么存在

sync_navbar.py 统一了顶栏，但页面其余「骨架」仍各写各的，145 个静态页里存在：

  1. 面包屑 4 种写法 + 90 个页面完全没有：
       <div id="breadcrumb"></div>                     （空占位，靠 js/app.js 生成，且只认旧版）
       <div class="breadcrumb" data-path="..."></div>   （data-path 无人解析，死机制）
       <div class="breadcrumb">…首页›板块…</div>          （写死，无「类目」层级）
       .breadcrumb-nav                                   （Hugo 模板另一套类名）
     且 js/app.js 的 slug 表不认识 zisha/apple/ev-sales 等，会直接显示英文 slug。

  2. 页脚 6 种写法；且只有首页有 CC BY-NC 4.0 许可行，140 个静态页没有——
     版权条款只声明在首页，子页读者看不到。

  3. bracelet/* 9 页页脚 HTML 嵌套是坏的：两个 <footer>、外层缺 </footer>。

  4. 标题不统一：11 个带 emoji 前缀（🍵🎮🌀🎓🚧 等）、tesla 带「#必看」话题尾巴、
     「文玩手串百科 / 养生茶配方 / 特斯拉动态新闻」与导航里的板块名对不上。

  5. 页尾信息块（.page-meta）只在 85 页存在；75 个主机详情页的「最后更新」是写死的
     2026-07-07 且不在 .update-time 组件内 —— sync_update_time.py 认不出，CI 永不刷新。

## 统一规范（本脚本是唯一真相源，幂等可重跑）

  <nav class="navbar">                       ← sync_navbar.py 负责
  <div class="breadcrumb" id="breadcrumb">   ← 本脚本：首页 › 类目 › 板块[ › 内容]
  <main>
    <h1>板块名</h1>                            ← 本脚本：去 emoji、去话题尾巴、与板块名一致
    …正文…
    <div class="page-meta">                    ← 本脚本：来源(可选) + 免责说明 + 最后更新
  <footer role="contentinfo">…</footer>        ← 本脚本：单一模板（含 CC 许可行）

  例外（豁免，保持原样）：
    404.html / offline.html                —— 无 main、结构本就特殊
    privacy.html / shesi-*.html            —— 《脚趾抠地》对外页，属独立资产
    console-gc/n64/wiiu.html               —— 301 跳转壳，无正文
    travel.html                            —— 加密相册，产物由 TRAVEL_KEY 重新加密生成

## Hugo 侧的同规范实现（本脚本管不到由模板渲染出来的那 7 个页面）

  站长手记 notes、建站清单 checklist、全站栏目总览 categories、全站标签导航 tags、
  全站搜索 search、标签文章 tag、标签聚合 tags.html、我的收藏 bookmarks ——
  它们是 public/ 里由 Hugo 模板渲染的页，规范落在 layouts/：

    layouts/partials/page-header.html   —— 面包屑；$cats 映射须与上面 CATEGORIES 对齐
    layouts/partials/page-meta.html     —— 页尾信息块（Hugo 页专用）
    layouts/_default/single.html        —— 挂上面两个 partial
    layouts/_default/list.html          —— 同上（categories / tags 两个索引页）
    layouts/tags.html                   —— /tags.html（标签聚合一）挂 page-meta
    layouts/tag.html                    —— /tag.html?tag=X（标签聚合二）挂 page-meta
    hugo.toml                           —— enableGitInfo = true，页面日期取该文件最后一次
                                           提交日，与 sync_update_time.py 给静态页的口径同源

  ⚠️ 排查过的坑：/tags.html 与 /tag.html 走的是 layouts/tags.html 与 layouts/tag.html
     两个**自定义模板**，不是 _default/list.html。早期只改了 list.html，结果这两页
     全站唯一缺页尾信息块（2026-09-17 第二轮产物回读抓到）。改动单.html 时务必确认
     它实际由哪个模板渲染 —— content/tags-index.md 与 content/tag.md 用 `layout:` 指定。

  两个刻意的不一致，都是设计内：
    1. front matter 标了 noindex 的**纯工具页**（search / bookmarks / checklist / offline、
       以及 3 个别名跳转页）不加 .page-meta —— 它们是工具而非内容页。
       注意 tag.html 也带 noindex，但它是 tags.html 的下一步落地页、用户真的在看内容，
       所以照样挂信息块：noindex 只是 SEO 策略，不等于"工具页"。
    2. Hugo 页的信息块外面套了一层 <div class="container">，否则它落在裸 <main> 里会撑满
       整屏宽（实测 1432px，而静态页是 1160px），同一组件出现两种宽度。

## 引号规范（全站正文统一用「」）

  站内主风格是「」（116 个页面在用）。直双引号 " 与中文弯引号 “ ” 已由
  scripts/unify_quotes.py 一次性归一为「」。该脚本只动"可见文本节点"，绝不碰属性、
  HTML 注释、script/style、code/pre，也不碰 Markdown 的 YAML 头与代码块。
  单引号 ' 一概不动 —— 站内 18 处全是英文撇号（Marvel's、Nintendon't）或 CSP 指令
  语法（frame-src 'none'），不是中文引号。


用法：
    python3 scripts/sync_chrome.py           # 写回
    python3 scripts/sync_chrome.py --check   # 只报告会改哪些文件
"""
import glob
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sync_navbar import CATEGORIES, INDEPENDENT  # 类目/板块名的唯一真相源

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC = os.path.join(ROOT, "static")

# ---------------------------------------------------------------- 豁免清单
SKIP_FILES = {
    "404.html", "offline.html",                                  # 特殊结构
    "privacy.html", "shesi-landing.html", "shesi-privacy.html",   # 《脚趾抠地》独立资产
    "console-gc.html", "console-n64.html", "console-wiiu.html",   # 301 跳转壳
    "apple-history.html",                                         # 已并入 apple.html，仅留跳转壳
    "travel.html",                                                # 加密相册（密钥重加密）
}

# ---------------------------------------------------------------- 板块归属
# 顶层板块页 → (类目, 板块名)
SEC_CAT = {}
SEC_NAME = {}
for _cat, _items in CATEGORIES:
    for _f, _n in _items:
        SEC_CAT[_f] = _cat
        SEC_NAME[_f] = _n
for _f, _n in INDEPENDENT:
    SEC_CAT[_f] = None          # 独立入口：面包屑只有「首页 › 名称」
    SEC_NAME[_f] = _n

# 详情页 → 所属板块页（键为页面所在目录，相对 static/）
DETAIL_DIRS = {
    "bracelet": "bracelet.html",
    "games": "games.html",
    "tesla": "tesla.html",
    "pages/zisha": "zisha.html",     # 紫砂作品详情页
}
DETAIL_PREFIXES = [("console-", "console.html")]   # 顶层 console-*.html → 主机图鉴

# ---------------------------------------------------------------- 标题规范
# 板块页 H1 = 全站正式板块名。光辉电力例外：导航用简称，页面标题用公司全称（专有名词）。
H1_OVERRIDE = {
    "about.html": "关于本站",
    "apple.html": "苹果",
    "bracelet.html": "文玩手串",
    "calendar.html": "万年历",
    "changelog.html": "更新日志",
    "chinajoy.html": "ChinaJoy 成长史",
    "console.html": "主机图鉴",
    "ev-charge.html": "充电桩查询",
    "ev-sales.html": "新能源销量榜",
    "games.html": "玩过的游戏",
    "gaokao.html": "高考查分",
    "guanghui.html": "江苏光辉电力器材有限公司",
    "health-tea.html": "养生茶",
    "marvel.html": "漫威宇宙",
    "pitfalls.html": "踩坑记",
    "sheyang.html": "射阳天气",
    "status-history.html": "站点状态",
    "tesla.html": "特斯拉",
    "tools.html": "工具箱",
    "typhoon.html": "台风监测",
    "xintan-weather.html": "农田气象",
    "zisha.html": "紫砂艺术",
}

# 免责说明（信息块里没有真实来源时使用的通用文案；不编造任何具体来源）
REF_NOTE = "本站内容为个人整理与实测记录，仅供参考；涉及外部数据以正文标注的来源为准。"

SEAL_SVG = (
    '<svg class="lx-seal lx-seal-xs" viewBox="0 0 100 100" aria-hidden="true">'
    '<rect x="4" y="4" width="92" height="92" rx="7" fill="none" stroke="currentColor" stroke-width="8"/>'
    '<text class="lx-brush" x="50" y="53" font-size="50" fill="currentColor" '
    'text-anchor="middle" dominant-baseline="middle">龙</text></svg>'
)

# 由 sync_update_time.py 自动刷新的动态标记（保留，不降级成死文本）
DYNAMIC_IDS = ("lastNewsUpdate", "changelogUpdated")

EMOJI_RE = re.compile(
    "[\U0001F000-\U0001FAFF\u2600-\u27BF\u2B00-\u2BFF\uFE0F\u20E3\uFE0E]"
)
DATE_RE = re.compile(r"最后更新(?:时间)?[：:]\s*(\d{4}-\d{2}-\d{2})")
# 5 组：标签 / class 前属性 / class / class 后属性 / 内容
UT_ELEM_RE = re.compile(
    r'<([a-z]+)([^>]*?)\bclass="([^"]*\bupdate-time\b[^"]*)"([^>]*)>(.*?)</\1>', re.S
)
# 只包着一个 .update-time 的空壳 div（摘掉标记后会留下无主死壳，先解包）
WRAP_UT_RE = re.compile(
    r'<div\b([^>]*)>\s*(<(?:p|span|div)[^>]*\bclass="[^"]*\bupdate-time\b[^"]*"[^>]*>.*?</(?:p|span|div)>)\s*</div>',
    re.S,
)
# 旧面包屑：4 种写法一次清掉（含紧邻的 HTML 注释）
OLD_BC_RE = re.compile(
    r'(?:\s*<!--\s*面包屑[^>]*?-->\s*)?'
    r'<(?:div|nav)[^>]*(?:\bclass="[^"]*breadcrumb[^"]*"|\bid="breadcrumb")[^>]*>.*?</(?:div|nav)>',
    re.S,
)
MAIN_RE = re.compile(r'<main\b[^>]*\bid="main-content"[^>]*>', re.I)
BODY_RE = re.compile(r"<body\b[^>]*>", re.I)


# ---------------------------------------------------------------- 小工具
def rel_of(path):
    return os.path.relpath(path, STATIC).replace(os.sep, "/")


def prefix_of(rel):
    return "../" * rel.count("/")


def strip_emoji(s):
    return re.sub(r"\s{2,}", " ", EMOJI_RE.sub("", s)).strip()


def git_date(rel_static):
    """页面最后一次提交日期；与 sync_update_time.py 同口径，保证本地与部署一致。"""
    try:
        out = subprocess.run(
            ["git", "log", "-1", "--format=%cd", "--date=short", "--",
             "static/" + rel_static],
            cwd=ROOT, capture_output=True, text=True, timeout=30,
        )
        d = (out.stdout or "").strip()
        return d if re.fullmatch(r"\d{4}-\d{2}-\d{2}", d) else ""
    except Exception:
        return ""


def find_div_end(html, start):
    """start 指向 '<div' 的 '<'，返回配对 '</div>' 之后的下标。"""
    depth = 0
    for m in re.finditer(r"<(/?)div\b", html[start:], re.I):
        if m.group(1):
            depth -= 1
            if depth == 0:
                # 注意：index() 的起点已是绝对偏移，返回值也是绝对下标，不要再加 start
                return html.index(">", start + m.end()) + 1
        else:
            depth += 1
    return -1


def load_email_anchor():
    """邮箱链接（含站点真实地址）从现有页面原文提取，避免脚本里硬编码。"""
    try:
        h = open(os.path.join(STATIC, "about.html"), encoding="utf-8").read()
    except OSError:
        return ""
    m = re.search(r'<a class="obf-email"[^>]*>.*?</a>', h, re.S)
    if not m:
        return ""
    return re.sub(r'style="[^"]*"', 'style="color:var(--email-green)"', m.group(0))


EMAIL_ANCHOR = load_email_anchor()


# ---------------------------------------------------------------- ① 面包屑
def build_breadcrumb(prefix, crumbs):
    """crumbs: [(文字, 链接或None, 是否当前页)]"""
    out = []
    for label, href, cur in crumbs:
        if cur:
            out.append(f'<span class="current">{label}</span>')
        elif href:
            out.append(f'<a href="{prefix}{href}">{label}</a>')
        else:
            out.append(f'<span class="crumb-cat">{label}</span>')
    seq = '<span class="sep">›</span>'.join(out)
    return (
        f'<div class="breadcrumb" id="breadcrumb" role="navigation" '
        f'aria-label="面包屑导航">{seq}</div>'
    )


def crumbs_for(rel, h1_text):
    home = ("首页", "index.html", False)
    if rel in SEC_NAME:                       # 顶层板块页
        cat = SEC_CAT.get(rel)
        mid = [(cat, None, False)] if cat else []
        return [home] + mid + [(SEC_NAME[rel], None, True)]
    parent = None
    if "/" in rel:
        parent = DETAIL_DIRS.get(rel.rsplit("/", 1)[0])
    else:
        for pfx, sec in DETAIL_PREFIXES:
            if rel.startswith(pfx):
                parent = sec
                break
    if parent and parent in SEC_NAME:
        cat = SEC_CAT.get(parent)
        mid = [(cat, None, False)] if cat else []
        return [home] + mid + [(SEC_NAME[parent], parent, False), (h1_text, None, True)]
    return []                                  # 未知归属：不动


def sync_breadcrumb(html, rel, h1_text):
    crumbs = crumbs_for(rel, h1_text)
    if not crumbs:
        return html, "bc:skip"
    new = build_breadcrumb(prefix_of(rel), crumbs)
    m = OLD_BC_RE.search(html)
    if m:
        if m.group(0).strip() == new:
            return html, "bc:unchanged"
        keep_nl = "\n  " if "\n" in m.group(0) else ""
        html = html[: m.start()] + keep_nl + new + html[m.end():]
        return html, "bc:updated"
    m = MAIN_RE.search(html)
    if m:
        html = html[: m.end()] + "\n  " + new + html[m.end():]
        return html, "bc:added"
    m = re.search(r"</nav>", html)
    if m:
        html = html[: m.end()] + "\n" + new + html[m.end():]
        return html, "bc:added(after-nav)"
    m = BODY_RE.search(html)
    if m:
        html = html[: m.end()] + "\n" + new + html[m.end():]
        return html, "bc:added(after-body)"
    return html, "bc:no-anchor"


# ---------------------------------------------------------------- ② 标题
def sync_h1(html, rel):
    m = re.search(r"<h1([^>]*)>(.*?)</h1>", html, re.S)
    if not m:
        return html, None, "h1:none"
    inner = m.group(2)
    body = inner.strip()
    desired = H1_OVERRIDE.get(rel) or strip_emoji(re.sub(r"<[^>]+>", "", body))
    if body == desired and "<" not in body:
        return html, strip_emoji(re.sub(r"<[^>]+>", "", body)), "h1:unchanged"
    lead = inner[: len(inner) - len(inner.lstrip())]
    trail = inner[len(inner.rstrip()):]
    html = html[: m.start(2)] + lead + desired + trail + html[m.end(2):]
    return html, desired, "h1:updated"


# ---------------------------------------------------------------- ③④ 信息块 + 页脚
def build_footer(prefix):
    links = " <span class=\"sep\">·</span> ".join(
        f'<a href="{prefix}{t}">{n}</a>'
        for t, n in (("about.html", "关于本站 / 免责声明"), ("categories/", "全部栏目"),
                     ("notes.html", "站长手记"), ("tags.html", "标签聚合"),
                     ("rss.xml", "RSS 订阅"))
    )
    legal = (f'如发现内容涉及侵权，请联系 {EMAIL_ANCHOR}，我们会在核实后尽快处理。'
             if EMAIL_ANCHOR else "如发现内容涉及侵权，请通过「关于本站」页面的联系方式告知，我们会在核实后尽快处理。")
    return f'''<footer role="contentinfo">
  <div class="footer-brand-row">
    {SEAL_SVG}
    龙兄知识库 <span class="evolved">· 这个网站是活的</span>
  </div>
  <div class="footer-info-row">
    © 2026 龙兄知识库 <span class="sep">·</span> 专注实用科普与生活百科
  </div>
  <div class="footer-license-row">
    内容采用 <a href="https://creativecommons.org/licenses/by-nc/4.0/" target="_blank" rel="noopener noreferrer">CC BY-NC 4.0</a> 许可
    <span class="sep">·</span> 代码版权所有
  </div>
  <div class="footer-stats-row">
    <span class="footer-stat">访问 <strong id="busuanzi_value_site_pv">-</strong> 次</span>
    <span class="footer-stat">访客 <strong id="busuanzi_value_site_uv">-</strong> 人</span>
  </div>
  <div class="footer-links-row">
    {links}
  </div>
  <div class="footer-legal">
    {legal}
  </div>
</footer>'''


def take_update_time(html, notes):
    """摘出页内所有 .update-time 元素，返回 (剩余 html, 元素列表, 出现的日期集合)。

    三种例外一律不动：
      · 内容含 ${...}/{{...}} —— JS 运行时填充的模板；
      · 元素还带别的 class（兼作副标题/hero meta）—— 只摘掉更新标记，保留元素本身；
      · 包在 .page-meta 里只包着它自己的空壳 div —— 先解包，避免留死壳。
    """
    def _unwrap(m):
        return m.group(0) if "page-meta" in m.group(1) else m.group(2)

    for _ in range(3):
        new = WRAP_UT_RE.sub(_unwrap, html)
        if new == html:
            break
        html = new

    elems = []
    dates = set()

    def _sub(m):
        tag, a1, cls, a2, body = m.group(1), m.group(2), m.group(3), m.group(4), m.group(5)
        if "${" in body or "{{" in body:
            return m.group(0)                       # JS 模板占位
        dates.update(DATE_RE.findall(body))
        dates.update(re.findall(r">\s*(\d{4}-\d{2}-\d{2})\s*<", body))
        classes = cls.split()
        if len(classes) > 1:                        # 兼作他用：只摘标记
            rest = [c for c in classes if c != "update-time"]
            body2 = re.sub(r"[·|｜]\s*$", "", DATE_RE.sub("", body).strip())
            if not re.sub(r"<[^>]+>|[\s·|｜]", "", body2):
                return ""                           # 摘完变空壳，直接删
            return f'<{tag}{a1}class="{" ".join(rest)}"{a2}>{body2}</{tag}>'
        elems.append(m.group(0))
        return ""

    html = UT_ELEM_RE.sub(_sub, html)
    if elems:
        notes.append(f"ut:{len(elems)}")
    return html, elems, dates


def pick_update_time(elems, date):
    """在摘出的元素里挑一个沿用（保留动态 span），否则造规范的纯文本标记。"""
    for e in elems:
        if any(i in e for i in DYNAMIC_IDS):
            return e if "\n" not in e else re.sub(r"\s+", " ", e).strip()
    return f'<div class="update-time">最后更新：{date}</div>'


def clean_meta_inner(inner):
    """信息块内部归一：清掉散落的「最后更新：日期」、去掉行内 style、统一来源行类名。"""
    inner = DATE_RE.sub("", inner)
    inner = re.sub(r"(?<=>)\s*[|｜]\s*", "", inner)          # 残留的分隔符
    inner = re.sub(r"[|｜]\s*(?=</)", "", inner)
    inner = re.sub(r'class="page-meta"[^>]*style="[^"]*"', 'class="page-meta"', inner)
    inner = re.sub(r"<(p|div)([^>]*)>\s*</\1>\s*", "", inner)
    # 来源行统一用 .source（与既有 85 页信息块一致）
    def _src(m):
        tag, attrs, body = m.group(1), m.group(2), m.group(3)
        if re.search(r"信息来源|数据来源", body):
            return f'<div class="source">{body.strip()}</div>'
        return m.group(0)
    inner = re.sub(r"<(p|div)([^>]*)>(.*?)</\1>", _src, inner, flags=re.S)
    return inner


def sync_meta(html, rel, notes, date):
    """整段摘出页尾信息块，归一内部结构 + 更新标记，返回 (剩余 html, 新信息块)。"""
    m = re.search(r'[ \t]*<div class="page-meta"[^>]*>', html)
    block = None
    if m:
        div_start = html.index("<div", m.start())
        end = find_div_end(html, div_start)
        # 连同行首缩进与随后的一个换行一起摘走，否则每跑一次都会在原地多留一个空行
        start = div_start
        while start > 0 and html[start - 1] in " \t":
            start -= 1
        eat = 1 if html[end:end + 1] == "\n" else 0
        block = html[start:end]
        html = html[:start] + html[end + eat:]
        notes.append("pm:found")
    else:
        notes.append("pm:new")

    html, ut_elems, _ = take_update_time(html, notes)
    inner = ""
    if block is not None:
        block, ut2, _ = take_update_time(block, notes)
        ut_elems = ut2 + ut_elems
        # 用 match.end() 定位开头标签的真实终点（block 可能带行首缩进，不能用长度硬算）
        mo = re.search(r"<div[^>]*>", block)
        inner = block[mo.end(): -len("</div>")]
        inner = clean_meta_inner(inner)
    # 只用 strip() 规范化首尾空白：内部原样保留（有些来源行会跨行写属性），
    # 且这一变换天然幂等，重复执行不会累积空白。
    body = inner.strip() or f'<p class="ref-note">{REF_NOTE}</p>'
    ut = pick_update_time(ut_elems, date)
    block_new = f'<div class="page-meta">\n    {body}\n    {ut}\n  </div>'
    return html, block_new


def sync_footer(html, rel, notes):
    """把首个 <footer> 到最后一个 </footer> 之间的内容（bracelet/* 就是坏嵌套）整段换成规范页脚。"""
    i = html.find("<footer")
    if i < 0:
        return html, None
    j = html.rfind("</footer>")
    if j < i:
        return html, None
    new = build_footer(prefix_of(rel))
    if html[i: j + len("</footer>")].strip() == new.strip():
        notes.append("ft:unchanged")
        return html, new
    notes.append("ft:updated")
    return html[:i] + new + html[j + len("</footer>"):], new


def ensure_scripts(html, notes):
    """页脚依赖：邮箱混淆（有链接就必须有脚本）、访问统计（有占位就必须有脚本）。"""
    if "obf-email" in html and "obfuscate-email.js" not in html:
        m = re.search(r"</body>", html, re.I)
        tag = '<script src="/js/obfuscate-email.js"></script>\n'
        html = html[: m.start()] + tag + html[m.start():] if m else html + tag
        notes.append("js:email")
    if "busuanzi_value_site_pv" in html and "busuanzi.pure.mini.js" not in html:
        m = re.search(r"</body>", html, re.I)
        tag = ('<script async src="/js/busuanzi.pure.mini.js" '
               'integrity="sha384-oaKlriFiEaHzTKw66TKlzwgjYHPT5tvx+uf4JRnAGvP7HCHj5NPqEoAkyyOAPxZN" '
               'crossorigin="anonymous"></script>\n')
        html = html[: m.start()] + tag + html[m.start():] if m else html + tag
        notes.append("js:pv")
    return html


# ---------------------------------------------------------------- 主流程
def process_file(path, check_only=False):
    rel = rel_of(path)
    if rel in SKIP_FILES:
        return "skip(exempt)"
    html = open(path, encoding="utf-8").read()
    orig = html
    notes = []

    html, h1_text, h1_note = sync_h1(html, rel)
    notes.append(h1_note)
    if h1_text is None:
        h1_text = SEC_NAME.get(rel) or ""
    html, bc_note = sync_breadcrumb(html, rel, h1_text)
    notes.append(bc_note)

    html, block_new = sync_meta(html, rel, notes, git_date(rel) or "2026-09-17")

    html, footer = sync_footer(html, rel, notes)
    if footer is not None:
        cm = html.rfind("</main>")
        cf = html.rfind("<footer")
        # 信息块要留在正文容器内：仅当 </main> 后面除页脚别无内容时才插在 </main> 之前
        tight = cm >= 0 and cm < cf and html[cm + len("</main>"):cf].strip() == ""
        pos = cm if tight else cf
        line_start = html.rfind("\n", 0, pos) + 1
        html = (html[:line_start] + "  " + block_new + "\n" + html[line_start:])
        notes.append("pm:placed" + ("" if tight else "(pre-footer)"))
    html = ensure_scripts(html, notes)

    if html == orig:
        return "unchanged"
    if not check_only:
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)
    return "updated[" + ",".join(notes) + "]"


def main():
    check_only = "--check" in sys.argv
    counts = {"updated": 0, "unchanged": 0, "skip": 0}
    changed = []
    for path in sorted(glob.glob(os.path.join(STATIC, "**", "*.html"), recursive=True)):
        res = process_file(path, check_only)
        if res.startswith("updated"):
            counts["updated"] += 1
            changed.append((rel_of(path), res))
        elif res == "unchanged":
            counts["unchanged"] += 1
        else:
            counts["skip"] += 1
    print(f"[sync_chrome] check_only={check_only}  "
          f"updated={counts['updated']} unchanged={counts['unchanged']} skip={counts['skip']}")
    for name, res in changed[:40]:
        print(f"  + {name}: {res}")
    if len(changed) > 40:
        print(f"  ... and {len(changed) - 40} more")


if __name__ == "__main__":
    main()
