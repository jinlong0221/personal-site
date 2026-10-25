#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_weather_redirects.py — 把四个独立天气页转换为「已合并到 weather.html」跳转壳。

设计：
  - 纯 meta refresh 跳转（无内联 JS，规避 CSP sha256 哈希维护成本，也避免 JS 被拦时无法跳转）。
  - 复用 weather.html 去重后的同一份 CSP（已确认合规：script-src 无 unsafe-inline）。
  - 国风黑金兜底样式（内联 style，style-src 保留 unsafe-inline 是全站既定取舍）。
  - 无 JS / 无网也能用的可见「已合并」卡片 + 手动跳转按钮（SEO 与无障碍友好）。
  - 不带 <nav>，sync_navbar 会按既有规则 skip（它们是已合并的遗留页，不再进顶栏）。
"""
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC = os.path.join(ROOT, "static")


def read(name):
    with open(os.path.join(STATIC, name), encoding="utf-8") as f:
        return f.read()


def extract_csp(html):
    m = re.search(r'<meta http-equiv="Content-Security-Policy" content="([^"]*)"', html)
    return m.group(1)


def shell(old_name, title, desc):
    page_title = f"{title} · 已合并到「天气」｜龙兄知识库"
    # 注意：本壳为完全自包含（不加载 css/style.css），故直接用字面色值，
    # 绝不在非关键 <style> 里用 :root 重定义 --gold/--bg 等全局主题变量（会触发 guard_theme_scope A3）。
    return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
<meta http-equiv="Content-Security-Policy" content="{CSP}">
<meta name="referrer" content="strict-origin-when-cross-origin">
<meta http-equiv="refresh" content="0; url=weather.html">
<title>{page_title}</title>
<meta name="description" content="{desc}">
<meta property="og:title" content="{page_title}">
<meta property="og:description" content="{desc}">
<meta property="og:type" content="article">
<meta property="og:url" content="https://longxiong.vip/weather.html">
<meta name="twitter:card" content="summary">
<meta name="twitter:title" content="{page_title}">
<meta name="twitter:description" content="{desc}">
<link rel="canonical" href="https://longxiong.vip/weather.html">
<meta name="robots" content="noindex">
<link rel="icon" type="image/svg+xml" href="/favicon.svg">
<style>
  *{{box-sizing:border-box;}}
  body{{margin:0;min-height:100vh;display:flex;align-items:center;justify-content:center;
    background:radial-gradient(120% 120% at 50% 0%,#1b1812 0%,#0E0D0B 60%);
    font-family:-apple-system,"PingFang SC","Microsoft YaHei",sans-serif;color:#ECE6D8;padding:24px;}}
  .box{{max-width:460px;width:100%;background:#16140F;border:1px solid rgba(201,168,76,.35);
    border-radius:18px;padding:34px 28px;text-align:center;box-shadow:0 18px 50px rgba(0,0,0,.45);}}
  .seal{{width:64px;height:64px;margin:0 auto 14px;display:block;color:#C9A84C;}}
  h1{{font-size:1.32rem;margin:0 0 8px;color:#C9A84C;letter-spacing:.04em;}}
  p{{margin:6px 0 20px;color:#9a937f;font-size:.95rem;line-height:1.6;}}
  a.btn{{display:inline-block;padding:12px 26px;border-radius:12px;text-decoration:none;font-weight:700;
    color:#0E0D0B;background:linear-gradient(135deg,#E2C26A,#C9A84C);transition:transform .15s ease;}}
  a.btn:hover{{transform:translateY(-2px);}}
  .tip{{margin-top:16px;font-size:.78rem;color:#6f6a5c;}}
</style>
</head>
<body>
  <div class="box">
    <svg class="seal" viewBox="0 0 100 100" aria-hidden="true"><rect x="4" y="4" width="92" height="92" rx="7" fill="none" stroke="currentColor" stroke-width="8"/><text x="50" y="53" font-size="50" fill="currentColor" text-anchor="middle" dominant-baseline="middle">龙</text></svg>
    <h1>本页已合并到「天气」</h1>
    <p>「{title}」已整合进统一的天气聚合页，<br>可一站式查看射阳天气、农田气象、台风与节气。</p>
    <a class="btn" href="weather.html">前往天气聚合页 →</a>
    <div class="tip">页面将在 1 秒内自动跳转……</div>
  </div>
</body>
</html>
'''


CSP = extract_csp(read("weather.html"))

REDIRECTS = [
    ("sheyang.html", "射阳天气", "射阳实时天气"),
    ("xintan-weather.html", "新坍农田气象", "新坍镇乡镇级精准农业气象"),
    ("typhoon.html", "台风监测", "台风实时路径与防御建议"),
    ("solar-terms.html", "二十四节气物候", "24 节气物候与农事建议"),
]

for old, title, desc in REDIRECTS:
    html = shell(old, title, desc)
    with open(os.path.join(STATIC, old), "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[build_weather_redirects] 重写 {old} -> 跳转壳 ({len(html.encode('utf-8'))} bytes)")

print("[build_weather_redirects] 完成")
