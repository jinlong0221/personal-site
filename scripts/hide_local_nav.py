#!/usr/bin/env python3
# 隐藏本地化内容：从所有 static HTML 页的导航中移除本地入口与顶部天气图标。
# 兼容两种链接写法：顶层页 href="x.html"，子目录页 href="../x.html"。
# 删除整个 <a>...</a> 元素（含文本与闭合标签），幂等。
import os, re, glob

STATIC = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "static"))

HIDDEN = ["sheyang.html","sheyang-guide.html","xintan-weather.html","typhoon.html",
          "guanghui.html","gaokao.html","solar-terms.html","health-tea.html"]

# 整个 <a> 元素（兼容 0/1/2… 级 ../ 前缀，覆盖 pages/zisha/detail 等深层页）
RE_ANCHOR = re.compile(
    r'<a href="(?:\.\./)*(?:%s)">.*?</a>' % "|".join(re.escape(f) for f in HIDDEN),
    re.DOTALL)
# 主导航「射阳本地」整个 <li>
RE_NAV_LI = re.compile(
    r'<li><a href="(?:\.\./)*typhoon\.html">.*?</a></li>', re.DOTALL)
# 分组标题与分割线
RE_HD = re.compile(r'<span class="nav-more-hd">射阳本地</span>')
RE_HD_M = re.compile(r'<span class="nav-hd">射阳本地</span>')
RE_DIV = re.compile(r'<span class="nav-more-div"></span>|<span class="nav-div"></span>|<span class="nav-hd-div"></span>')
RE_WEATHER = re.compile(r'<span class="nav-weather"[^>]*>.*?</span>', re.DOTALL)

def clean(text):
    text = RE_ANCHOR.sub("", text)
    text = RE_NAV_LI.sub("", text)
    text = RE_HD.sub("", text)
    text = RE_HD_M.sub("", text)
    text = RE_DIV.sub("", text)
    text = RE_WEATHER.sub("", text)
    return text

count = 0
for path in glob.glob(os.path.join(STATIC, "**", "*.html"), recursive=True):
    with open(path, encoding="utf-8") as f:
        src = f.read()
    new = clean(src)
    if new != src:
        with open(path, "w", encoding="utf-8") as f:
            f.write(new)
        count += 1

print(f"已清理 {count} 个 static 页的本地导航入口(含 ../ 形式)")
