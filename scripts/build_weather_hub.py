#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_weather_hub.py — 生成两个天气相关页面。

设计（2026-10-25 拆分需求）：
  用户点顶部「天气」功能键 → 进入 weather.html，这是一个【只显示访客当前所在城市
  实时天气】的专注页（打开即浏览器定位 → 反查城市 → Open-Meteo 实时天气）。
  射阳本地气象（射阳实时 + 新坍农田 + 台风 + 节气）从天气页里剥离，单独成页
  sheyang-weather.html（「射阳气象」），在 weather.html 内用一个醒目入口卡「放旁边」，
  同时在导航「生活」分组登记入口。

  四页源（scripts/weather_sources/）仍作为构建输入，不含上线态（Task 14 已把线上态
  转为跳转壳）。本脚本产出两页：
    - static/weather.html         本地实时天气（专注页）
    - static/sheyang-weather.html 四合一 · 射阳气象

用法： python3 scripts/build_weather_hub.py
"""
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC = os.path.join(ROOT, "static")
SOURCE_DIR = os.path.join(ROOT, "scripts", "weather_sources")


def read(name):
    with open(os.path.join(SOURCE_DIR, name), encoding="utf-8") as f:
        return f.read()


def csp_meta(html):
    m = re.search(r'(<meta http-equiv="Content-Security-Policy" content="[^"]*"\s*/?>)', html)
    if not m:
        raise RuntimeError("csp_meta: 未找到 CSP meta 标签")
    tag = m.group(1)
    csp = re.search(r'content="([^"]*)"', tag).group(1)
    parts = [p.strip() for p in csp.split(';') if p.strip()]
    merged, connect_srcs = [], []
    for p in parts:
        if p.startswith('connect-src'):
            connect_srcs.extend(p.split()[1:])
        else:
            merged.append(p)
    if connect_srcs:
        seen, uniq = set(), []
        for t in connect_srcs:
            if t not in seen:
                seen.add(t); uniq.append(t)
        merged.append('connect-src ' + ' '.join(uniq))
    new_csp = '; '.join(merged) + ';'
    return re.sub(r'content="[^"]*"', 'content="%s"' % new_csp, tag)


def critical_css(html):
    m = re.search(r'(<style id="critical-css">.*?</style>)', html, re.S)
    return m.group(1)


def non_critical_styles(html):
    out = []
    for m in re.finditer(r'<style[^>]*>(.*?)</style>', html, re.S):
        if 'id="critical-css"' in m.group(0):
            continue
        out.append(m.group(0))
    return "\n".join(out)


def main_inner(html):
    m = re.search(r'<main\b[^>]*>(.*?)</main>', html, re.S)
    s = m.group(1)
    s = re.sub(r'<div class="breadcrumb".*?</div>', '', s, flags=re.S)
    s = re.sub(r'<!-- related:begin -->.*?<!-- related:end -->', '', s, flags=re.S)
    s = re.sub(r'<div class="page-meta">.*?</div>', '', s, flags=re.S)
    return s.strip()


sheyang = read("sheyang.html")
xintan = read("xintan-weather.html")
typhoon = read("typhoon.html")
solar = read("solar-terms.html")

CSP = csp_meta(sheyang)
CRIT = critical_css(typhoon)
SHEYANG_CSS = non_critical_styles(sheyang)
XINTAN_CSS = non_critical_styles(xintan)
TYPHOON_CSS = non_critical_styles(typhoon)
SOLAR_CSS = non_critical_styles(solar)

SHEYANG_BODY = main_inner(sheyang)
XINTAN_BODY = main_inner(xintan)
TYPHOON_BODY = main_inner(typhoon)
SOLAR_BODY = main_inner(solar)

# 本地天气横幅样式（weather.html 专用）
LW_CSS = """
/* ===== 天气页 · 访客本地天气横幅 ===== */
.lw-wrap{padding:18px 16px 4px;}
.lw-card{display:flex;flex-direction:column;gap:8px;align-items:flex-start;max-width:640px;margin:0 auto;padding:18px 20px;border-radius:16px;
  background:linear-gradient(135deg,rgba(201,168,76,.10),rgba(201,168,76,.03));border:1px solid rgba(201,168,76,.30);}
.lw-badge{align-self:flex-start;font-size:.72rem;padding:3px 10px;border-radius:999px;background:rgba(201,168,76,.18);color:var(--gold);font-weight:600;}
.lw-main{display:flex;align-items:center;gap:12px;}
.lw-main svg{width:34px;height:34px;color:var(--gold);flex:none;}
.lw-now{display:flex;align-items:baseline;gap:10px;}
.lw-temp{font-size:2.1rem;font-weight:700;color:var(--text);line-height:1;}
.lw-desc{font-size:1rem;color:var(--text-secondary);}
.lw-place{font-size:1.05rem;font-weight:600;color:var(--gold);}
.lw-foot{font-size:.74rem;color:var(--text-muted);}
.lw-title{font-size:1.05rem;font-weight:700;color:var(--text);}
.lw-sub{font-size:.86rem;color:var(--text-muted);margin:0;}
.lw-btn{margin-top:4px;padding:9px 16px;border-radius:10px;border:1px solid var(--gold);background:transparent;color:var(--gold);font-weight:600;cursor:pointer;}
.lw-btn:hover{background:rgba(201,168,76,.12);}
.lw-loading{display:flex;align-items:center;gap:10px;color:var(--text-muted);}
.lw-spin{width:16px;height:16px;border:2px solid var(--border);border-top-color:var(--gold);border-radius:50%;animation:lwspin .8s linear infinite;}
@keyframes lwspin{to{transform:rotate(360deg);}}
@media(max-width:640px){.lw-temp{font-size:1.8rem;}}
"""

# 本地天气页「射阳气象」入口卡样式
WE_CSS = """
/* ===== 天气页 · 射阳气象入口卡（放旁边） ===== */
.we-wrap{padding:24px 16px 10px;}
.we-card{max-width:640px;margin:0 auto;text-align:center;padding:22px 20px;border-radius:16px;
  border:1px dashed rgba(201,168,76,.38);background:rgba(201,168,76,.04);}
.we-card .we-tip{font-size:.88rem;color:var(--text-muted);margin:0 0 14px;}
.we-card .we-split{display:flex;gap:10px;align-items:center;justify-content:center;flex-wrap:wrap;margin-bottom:14px;color:var(--text-muted);font-size:.82rem;}
.we-card .we-split b{color:var(--gold);}
.we-btn{display:inline-block;padding:12px 22px;border-radius:12px;background:linear-gradient(135deg,var(--gold),#b8913f);
  color:#1a1408;font-weight:700;text-decoration:none;font-size:1rem;box-shadow:0 6px 18px rgba(201,168,76,.25);}
.we-btn:hover{filter:brightness(1.06);}
@media(max-width:640px){.we-btn{display:block;}}
"""

# 四合一（射阳气象）页内锚点导航样式
HUB_CSS = """
/* ===== 射阳气象页 · 站内锚点导航 ===== */
.wh-hero{padding:40px 20px 26px;text-align:center;background:linear-gradient(135deg,rgba(201,168,76,.08),rgba(201,168,76,.02));border-bottom:1px solid var(--border);}
.wh-hero h1{font-size:2rem;color:var(--gold);margin-bottom:8px;letter-spacing:.04em;}
[data-theme="light"] .wh-hero h1{color:#6B4F00;}
.wh-hero p{color:var(--text-muted);font-size:1rem;}
.wh-anchor{position:sticky;top:var(--nav-height);z-index:120;display:flex;gap:8px;flex-wrap:wrap;justify-content:center;
  padding:12px 16px;background:var(--nav-bg);backdrop-filter:blur(12px);border-bottom:1px solid var(--border);}
.wh-anchor a{flex:1 1 150px;max-width:220px;text-align:center;padding:10px 12px;border-radius:10px;border:1px solid var(--border);
  color:var(--text-secondary);font-weight:600;font-size:.92rem;background:var(--card);transition:all .2s ease;text-decoration:none;}
.wh-anchor a:hover,.wh-anchor a.active{border-color:var(--gold);color:var(--gold);background:var(--card-hover);}
.wh-section{scroll-margin-top:calc(var(--nav-height) + 64px);padding:36px 0 8px;}
.wh-section-head{display:flex;align-items:center;gap:10px;flex-wrap:wrap;font-size:1.5rem;color:var(--text);
  margin:0 0 6px;padding-bottom:12px;border-bottom:2px solid rgba(201,168,76,.22);}
.wh-section-head .wh-en{font-size:.72rem;letter-spacing:1.6px;text-transform:uppercase;color:var(--text-muted);font-weight:400;}
.wh-section-head .wh-tag{margin-left:auto;font-size:.74rem;padding:3px 11px;border-radius:999px;background:rgba(201,168,76,.16);color:var(--gold);}
@media(max-width:640px){.wh-hero h1{font-size:1.5rem;}.wh-section-head{font-size:1.15rem;}}
"""

PAGE_CSS_VERSION = "20261025"

# 标准导航（占位，稍后由 sync_navbar.py 以 navbar.html 单一数据源重生成）
NAV = '''<nav class="navbar" role="navigation" aria-label="主导航">
  <div class="navbar-inner">
    <a href="index.html" class="logo" aria-label="龙兄知识库首页">
      <svg class="lx-seal lx-seal-sm" viewBox="0 0 100 100" aria-hidden="true"><rect x="4" y="4" width="92" height="92" rx="7" fill="none" stroke="currentColor" stroke-width="8"/><text class="lx-brush" x="50" y="53" font-size="50" fill="currentColor" text-anchor="middle" dominant-baseline="middle">龙</text></svg>
      <span>龙兄</span>
    </a>
    <a href="calendar.html" class="nav-clock-link" id="navClockLink" title="点击查看万年历" aria-label="点击查看万年历"><span id="navClock" class="nav-clock" title="当前时间"></span></a>
    <ul class="nav-links">
      <li><a href="zisha.html">风物志</a></li>
      <li><a href="tesla.html">车与数码</a></li>
      <li><a href="console.html">游戏影游</a></li>
      <li><a href="tools.html">生活工具</a></li>
      <li><a href="about.html">关于我</a></li>
      <li class="nav-more-wrap">
        <button type="button" class="nav-more-btn">更多 ▾</button>
        <div class="nav-more-dropdown">
          <span class="nav-more-hd">风物志</span>
          <a href="bracelet.html">文玩手串</a>
          <a href="zisha.html">紫砂艺术</a>
          <span class="nav-more-hd">车与数码</span>
          <a href="tesla.html">特斯拉</a>
          <a href="apple.html">苹果</a>
          <a href="ev-sales.html">新能源销量榜</a>
          <a href="ev-charge.html">充电桩查询</a>
          <a href="digital-compare.html">数码参数对比</a>
          <span class="nav-more-hd">科技动态</span>
          <a href="global.html">科技动态</a>
          <span class="nav-more-hd">游戏影游</span>
          <a href="console.html">主机图鉴</a>
          <a href="games.html">玩过的游戏</a>
          <a href="chinajoy.html">ChinaJoy 成长史</a>
          <a href="marvel.html">漫威宇宙</a>
          <span class="nav-more-hd">生活工具</span>
          <a href="tools.html">工具箱</a>
          <a href="calendar.html">万年历</a>
          <a href="tags.html">标签聚合</a>
          <a href="bookmarks.html">我的收藏</a>
          <span class="nav-more-hd">关于我</span>
          <a href="notes.html">站长手记</a>
          <a href="reading.html">读书笔记</a>
          <a href="methodology.html">知识管理</a>
          <a href="about.html">关于本站</a>
          <span class="nav-more-hd">站务</span>
          <a href="changelog.html">更新日志</a>
          <a href="status-history.html">站点状态</a>
          <a href="pitfalls.html">踩坑记</a>
          <a href="rss.xml">RSS 订阅</a>
          <span class="nav-more-hd">生活</span>
          <a href="guanghui.html">光辉电力</a>
          <a href="herbs.html">中药材</a>
          <a href="health-tea.html">养生茶</a>
          <a href="weather.html" class="active">天气</a>
          <a href="gaokao.html">高考</a>
          <span class="nav-more-div"></span>
          <a href="travel.html">家庭旅行</a>
        </div>
      </li>
    </ul>
    <div class="nav-actions">
      <button class="icon-btn" id="searchBtn" aria-label="搜索" title="搜索">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
      </button>
      <button class="icon-btn" id="themeToggle" aria-label="切换主题" title="切换主题">
        <svg class="icon-sun" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="4"/><line x1="12" y1="2" x2="12" y2="5"/><line x1="12" y1="19" x2="12" y2="22"/><line x1="2" y1="12" x2="5" x2="12"/><line x1="19" y1="12" x2="22" y2="12"/><line x1="4.9" y1="4.9" x2="7" y2="7"/><line x1="17" y1="17" x2="19.1" y2="19.1"/><line x1="4.9" y1="19.1" x2="7" y2="17"/><line x1="17" y1="7" x2="19.1" y2="4.9"/></svg>
        <svg class="icon-moon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M21 12.8A9 9 0 1111.2 3 7 7 0 0021 12.8z"/></svg>
      </button>
      <button class="icon-btn" id="shareBtn" aria-label="分享" title="分享到微信">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><line x1="8.59" y1="13.51" x2="15.42" y2="17.49"/><line x1="15.41" y1="6.51" x2="8.59" y2="10.49"/></svg>
      </button>
      <button class="hamburger" id="hamburger" aria-label="打开菜单" aria-expanded="false">
        <span></span><span></span><span></span>
      </button>
    </div>
  </div>
  <div class="mobile-nav" id="mobileNav">
  <a href="index.html">首页</a>
  <span class="nav-hd">风物志</span>
  <a href="bracelet.html">文玩手串</a>
  <a href="zisha.html">紫砂艺术</a>
  <span class="nav-hd">车与数码</span>
  <a href="tesla.html">特斯拉</a>
  <a href="apple.html">苹果</a>
  <a href="ev-sales.html">新能源销量榜</a>
  <a href="ev-charge.html">充电桩查询</a>
  <a href="digital-compare.html">数码参数对比</a>
  <span class="nav-hd">科技动态</span>
  <a href="global.html">科技动态</a>
  <span class="nav-hd">游戏影游</span>
  <a href="console.html">主机图鉴</a>
  <a href="games.html">玩过的游戏</a>
  <a href="chinajoy.html">ChinaJoy 成长史</a>
  <a href="marvel.html">漫威宇宙</a>
  <span class="nav-hd">生活工具</span>
  <a href="tools.html">工具箱</a>
  <a href="calendar.html">万年历</a>
  <a href="tags.html">标签聚合</a>
  <a href="bookmarks.html">我的收藏</a>
  <span class="nav-hd">关于我</span>
  <a href="notes.html">站长手记</a>
  <a href="reading.html">读书笔记</a>
  <a href="methodology.html">知识管理</a>
  <a href="about.html">关于本站</a>
  <span class="nav-hd">站务</span>
  <a href="changelog.html">更新日志</a>
  <a href="status-history.html">站点状态</a>
  <a href="pitfalls.html">踩坑记</a>
  <a href="rss.xml">RSS 订阅</a>
  <span class="nav-hd">生活</span>
  <a href="guanghui.html">光辉电力</a>
  <a href="herbs.html">中药材</a>
  <a href="health-tea.html">养生茶</a>
  <a href="weather.html">天气</a>
  <a href="gaokao.html">高考</a>
  <span class="nav-hd-div"></span>
  <a href="travel.html">家庭旅行</a>
  </div>
</nav>'''

FOOTER = '''<footer role="contentinfo">
  <div class="footer-brand-row">
    <svg class="lx-seal lx-seal-xs" viewBox="0 0 100 100" aria-hidden="true"><rect x="4" y="4" width="92" height="92" rx="7" fill="none" stroke="currentColor" stroke-width="8"/><text class="lx-brush" x="50" y="53" font-size="50" fill="currentColor" text-anchor="middle" dominant-baseline="middle">龙</text></svg>
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
    <a href="about.html">关于本站 / 免责声明</a> <span class="sep">·</span> <a href="categories/">全部栏目</a> <span class="sep">·</span> <a href="notes.html">站长手记</a> <span class="sep">·</span> <a href="tags.html">标签聚合</a> <span class="sep">·</span> <a href="rss.xml">RSS 订阅</a>
  </div>
  <div class="footer-legal">
    如发现内容涉及侵权，请联系 <a class="obf-email" data-obf-user="799958000" data-obf-domain="qq.com">[email protected]</a>，我们会在核实后尽快处理。
  </div>
</footer>'''

COMMON_SCRIPTS = '''
<script defer src="/js/board-nav.js"></script>
<script defer src="js/app.js"></script>
<script defer src="js/interactions.js"></script>
<script defer src="js/search.js"></script>
<script defer src="js/share.js"></script>
<script src="js/bookmark.js" defer></script>
<script src="js/auto-collapse.js?v=20260824" defer></script>
<script src="/js/obfuscate-email.js"></script>
<script src="js/page-reveal.js?v=20260923" defer></script>
<script src="js/site-live.js?v=20261025" defer></script>'''


def build_page(title, desc, keywords, article_cat, article_tags, canonical_rel,
               og_url, h1, hero_p, head_css, main_inner_html, extra_body_scripts,
               extra_scripts_for_jsonld, jsonld_headline, jsonld_desc,
               breadcrumb_current, ref_note, out_name):
    breadcrumb = (
        '<div aria-label="面包屑导航" class="breadcrumb" id="breadcrumb" role="navigation">'
        '<a href="index.html">首页</a><span class="sep">›</span>'
        '<span class="crumb-cat">生活</span><span class="sep">›</span>'
        '<span class="current">%s</span></div>' % breadcrumb_current
    )
    page_meta = (
        '<div class="page-meta">\n'
        '<p class="ref-note">%s</p>\n' % ref_note +
        '<div class="update-time">最后更新：<span id="lastNewsUpdate">2026-10-25</span></div>\n'
        '</div>'
    )
    jsonld = (
        '<script type="application/ld+json">\n'
        '{\n'
        '  "@context": "https://schema.org",\n'
        '  "@graph": [\n'
        '    { "@type": "WebSite", "name": "龙兄知识库", "url": "https://longxiong.vip", "description": "AI · 文玩 · 游戏 · 养生 · 新能源 — 做一个有温度的知识站点" },\n'
        '    { "@type": "Article", "author": { "@type": "Person", "name": "龙兄" }, "headline": "%s", "url": "%s", "description": "%s" }\n'
        '  ]\n'
        '}\n'
        '</script>' % (jsonld_headline, og_url, jsonld_desc)
    )

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
{CSP}
<meta name="referrer" content="strict-origin-when-cross-origin">
<script>
(function(){{
  if(window.self !== window.top){{
    try{{ window.top.location.href = window.self.location.href; }}
    catch(e){{
      document.documentElement.style.visibility='hidden';
      document.addEventListener('DOMContentLoaded',function(){{ document.documentElement.style.display='none'; }});
    }}
  }}
}})();
</script>

<title>{title}</title>
<meta name="keywords" content="{keywords}">
<meta name="description" content="{desc}">
<meta name="article-category" content="{article_cat}">
<meta name="article-tags" content="{article_tags}">
<meta name="article-updated" content="2026-10-25">

<script>(function(){{try{{var t=localStorage.getItem('theme');if(t==='light'||t==='dark'){{document.documentElement.setAttribute('data-theme',t)}}else{{var h=new Date().getHours();document.documentElement.setAttribute('data-theme',(h>=6&&h<18)?'light':'dark')}}}}catch(e){{}}}})();</script>
<link rel="preload" href="js/app.js" as="script">
<link rel="preconnect" href="https://hm.baidu.com">
<link rel="dns-prefetch" href="https://hm.baidu.com">
{CRIT}
<style>
/* ===== 安全变量兜底 ===== */
:root{{--bg-card:var(--card);--border-subtle:var(--border);--text-primary:var(--text);}}
{head_css}
</style>
<link rel="stylesheet" href="css/style.css?v={PAGE_CSS_VERSION}">
  <script defer src="https://events.vercount.one/js"></script>
  <script>
var _hmt = _hmt || [];
(function() {{
  var hm = document.createElement("script");
  hm.src = "https://hm.baidu.com/hm.js?04913e92799dc86649938ea8f5eb4b78";
  var s = document.getElementsByTagName("script")[0];
  s.parentNode.insertBefore(hm, s);
}})();
</script>
<link rel="canonical" href="https://longxiong.vip/{canonical_rel}">
<link rel="icon" type="image/svg+xml" href="/favicon.svg">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:type" content="article">
<meta property="og:url" content="{og_url}">
<meta property="og:image" content="https://longxiong.vip/img/og-image.png">
<meta property="og:locale" content="zh_CN">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{title}">
<meta name="twitter:description" content="{desc}">
<meta name="twitter:image" content="https://longxiong.vip/img/og-image.png">
<script src="/js/pwa-register.js?v=20260828" defer></script>
</head>
<body>
{NAV}

<main id="main-content" role="main">
  {breadcrumb}
  <div class="wh-hero">
    <h1>{h1}</h1>
    <p>{hero_p}</p>
  </div>

{main_inner_html}

{page_meta}
</main>

{FOOTER}
{COMMON_SCRIPTS}
{extra_body_scripts}
{jsonld}
</body>
</html>
'''
    out = os.path.join(STATIC, out_name)
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    return out, len(html.encode("utf-8"))


# ------------------------------------------------------------------ 页面 1：本地实时天气（专注页）
def build_local_weather():
    main_inner_html = '''  <section id="localWeather" class="lw-wrap" aria-live="polite"></section>
  <div class="we-wrap">
    <div class="we-card">
      <p class="we-tip">以上是您当前所在城市的实时天气。要看射阳本地气象（射阳实时、新坍农田、台风、节气），点下面：</p>
      <div class="we-split"><span>📍 您的位置</span><b>››</b><span>🌦️ 射阳本地气象</span></div>
      <a class="we-btn" href="sheyang-weather.html">🌦️ 射阳气象（射阳实时·新坍农田·台风·节气）→</a>
    </div>
  </div>
  <section class="lx-related" aria-label="相关阅读">
    <div class="lx-related-head">
      <span class="lx-related-kicker">继续读</span>
      <h2 class="lx-related-title">相关阅读</h2>
      <span class="lx-rule1"></span>
    </div>
    <ul class="lx-related-list">
      <li class="lx-related-item"><a class="lx-related-link" href="sheyang-weather.html"><span class="lx-related-board">射阳气象</span><span class="lx-related-name">射阳气象（实时·农田·台风·节气）</span></a></li>
      <li class="lx-related-item"><a class="lx-related-link" href="guanghui.html"><span class="lx-related-board">本地产业</span><span class="lx-related-name">光辉电力</span></a></li>
      <li class="lx-related-item"><a class="lx-related-link" href="herbs.html"><span class="lx-related-board">养生</span><span class="lx-related-name">中药材</span></a></li>
    </ul>
  </section>'''
    extra_body_scripts = '''
<script defer src="js/geo-weather.js?v=20261025"></script>
<script>if(window.initClock)initClock();</script>'''
    out, n = build_page(
        title="天气 · 您所在城市的实时天气｜龙兄知识库",
        desc="打开即自动定位您当前所在城市，显示实时天气（温度与天气状况）。射阳本地气象请前往「射阳气象」。",
        keywords="实时天气,本地天气,定位天气,Open-Meteo,龙兄知识库",
        article_cat="天气",
        article_tags="天气,实时,定位",
        canonical_rel="weather.html",
        og_url="https://longxiong.vip/weather.html",
        h1="天气 · 您所在城市的实时天气",
        hero_p="本页打开后会自动获取您所在位置的实时天气。要看射阳本地（射阳实时、新坍农田、台风、节气），请点下方「射阳气象」。",
        head_css=LW_CSS + WE_CSS,
        main_inner_html=main_inner_html,
        extra_body_scripts=extra_body_scripts,
        extra_scripts_for_jsonld="",
        jsonld_headline="天气 · 您所在城市的实时天气｜龙兄知识库",
        jsonld_desc="打开即自动定位您当前所在城市，显示实时天气。射阳本地气象请前往「射阳气象」。",
        breadcrumb_current="天气",
        ref_note="本页实时天气来自 Open-Meteo 公开接口，浏览器本地定位获取，不上传任何数据；仅供参考。",
        out_name="weather.html",
    )
    return out, n


# ------------------------------------------------------------------ 页面 2：射阳气象（四合一）
def build_sheyang_hub():
    main_inner_html = '''  <nav class="wh-anchor" aria-label="天气板块导航">
    <a href="#sec-sheyang">🌦️ 射阳天气</a>
    <a href="#sec-xintan">🌾 新坍农田气象</a>
    <a href="#sec-typhoon">🌀 台风监测</a>
    <a href="#sec-solar">🌿 节气物候</a>
  </nav>

  <div class="container">
    <section class="wh-section" id="sec-sheyang">
      <div class="wh-section-head">射阳天气<span class="wh-en">Sheyang Weather</span><span class="wh-tag">33.77°N · 120.26°E</span></div>
      {SHEYANG_BODY}
    </section>

    <section class="wh-section" id="sec-xintan">
      <div class="wh-section-head">新坍镇农田气象<span class="wh-en">Xintan Farm Weather</span><span class="wh-tag">乡镇级精准农业气象</span></div>
      {XINTAN_BODY}
    </section>

    <section class="wh-section" id="sec-typhoon">
      <div class="wh-section-head">台风实时监测<span class="wh-en">Typhoon Tracker</span><span class="wh-tag">中央气象台等</span></div>
      {TYPHOON_BODY}
    </section>

    <section class="wh-section" id="sec-solar">
      <div class="wh-section-head">二十四节气 · 物候与农事<span class="wh-en">24 Solar Terms</span><span class="wh-tag">公历近似日期</span></div>
      {SOLAR_BODY}
    </section>
  </div>

  <section class="lx-related" aria-label="相关阅读">
    <div class="lx-related-head">
      <span class="lx-related-kicker">继续读</span>
      <h2 class="lx-related-title">相关阅读</h2>
      <span class="lx-rule1"></span>
    </div>
    <ul class="lx-related-list">
      <li class="lx-related-item"><a class="lx-related-link" href="weather.html"><span class="lx-related-board">天气</span><span class="lx-related-name">您所在城市的实时天气</span></a></li>
      <li class="lx-related-item"><a class="lx-related-link" href="sheyang-guide.html"><span class="lx-related-board">射阳生活</span><span class="lx-related-name">射阳生活指南</span></a></li>
      <li class="lx-related-item"><a class="lx-related-link" href="guanghui.html"><span class="lx-related-board">本地产业</span><span class="lx-related-name">光辉电力</span></a></li>
    </ul>
  </section>'''
    main_inner_html = main_inner_html.replace("{SHEYANG_BODY}", SHEYANG_BODY) \
                                    .replace("{XINTAN_BODY}", XINTAN_BODY) \
                                    .replace("{TYPHOON_BODY}", TYPHOON_BODY) \
                                    .replace("{SOLAR_BODY}", SOLAR_BODY)
    extra_body_scripts = '''
<script src="js/sheyang-weather.js?v=20261011" defer></script>
<script src="js/xintan-weather.js?v=20261011" defer></script>
<script defer src="js/auto_typhoon_loader.js?v=20261025"></script>
<script>if(window.initClock)initClock();</script>'''
    out, n = build_page(
        title="射阳气象 · 射阳天气与节气｜龙兄知识库",
        desc="射阳实时天气、新坍农田气象、台风实时监测与二十四节气物候，一站式聚合：实时气象数据、台风路径与农事建议。",
        keywords="射阳天气,新坍农田气象,台风监测,节气物候,实时气象,龙兄知识库",
        article_cat="射阳气象",
        article_tags="射阳,气象,台风,节气,农事",
        canonical_rel="sheyang-weather.html",
        og_url="https://longxiong.vip/sheyang-weather.html",
        h1="射阳气象 · 射阳天气与节气",
        hero_p="射阳实时天气、新坍农田气象、台风实时监测与二十四节气物候，一处看全。想看您自己所在城市的天气，点上方天气胶囊或返回「天气」。",
        head_css=HUB_CSS + SHEYANG_CSS + XINTAN_CSS + TYPHOON_CSS + SOLAR_CSS,
        main_inner_html=main_inner_html,
        extra_body_scripts=extra_body_scripts,
        extra_scripts_for_jsonld="",
        jsonld_headline="射阳气象 · 射阳天气与节气｜龙兄知识库",
        jsonld_desc="射阳实时天气、新坍农田气象、台风实时监测与二十四节气物候，一站式聚合。",
        breadcrumb_current="射阳气象",
        ref_note="本站天气数据来自中央气象台、Open-Meteo 等公开来源，实时刷新，仅供参考；农事与物候为传统经验整理，请结合当地实际。",
        out_name="sheyang-weather.html",
    )
    return out, n


def main():
    out1, n1 = build_local_weather()
    print("[build_weather_hub] wrote", out1, "bytes:", n1)
    out2, n2 = build_sheyang_hub()
    print("[build_weather_hub] wrote", out2, "bytes:", n2)


if __name__ == "__main__":
    main()
