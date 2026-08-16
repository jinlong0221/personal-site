#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全站静态页 SEO 统一改造（需求 1-4）

对 static/ 下全部独立 HTML 页面（不含 admin/pagefind/js/css/img/data/fonts）：
  1) 统一 TDK：
     - 栏目页 title = 栏目全称 + 详细科普｜龙兄知识库
     - 文章页 title = 原标题(去品牌尾) + 2026实测避坑｜龙兄知识库
     - meta description 70-90 字统一风格：实测溯源、实操图文、避坑指南、适合人群
     - keywords / og:title / og:description / twitter:title / twitter:description 同步
  2) 图片：缺失 loading 的非 hero 图补 loading="lazy"；缺失 alt 补合理 alt
  3) 文章页(深度>=2) 头部注入统一模板（封面/更新时间/阅读收益/时效性标签）
  4) 文章页(深度>=2) 底部注入「相关专题推荐」（同目录真实兄弟页，内部链接）
幂等：已存在注入标记则跳过；description 先删后插，确保唯一。
首页与 Hugo content 文章(title/description 在 frontmatter) 不在此脚本处理。
"""
import os, re, sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC = os.path.join(BASE, 'static')
NEW_CSS_VER = '20260816'

FUNCTIONAL = {  # depth-1 功能性页（非栏目/文章）
    'about.html': '关于本站',
    'changelog.html': '更新日志',
    'status-history.html': '站点状态',
}
SKIP_DIR_PARTS = {'admin', 'pagefind', 'js', 'css', 'img', 'data', 'fonts'}


def read(f):
    with open(f, encoding='utf-8') as fh:
        return fh.read()


def write(f, t):
    with open(f, 'w', encoding='utf-8') as fh:
        fh.write(t)


def strip_brand(title):
    t = title.strip()
    # 去除尾部品牌缀：支持 ｜ / | / - / — / _ 多种分隔符
    t = re.sub(r'\s*(?:[-_—|｜]\s*)?龙兄知识库\s*$', '', t)
    return t.strip()


def clean_topic(existing, kind):
    """去除品牌缀 + 已可能存在的本脚本后缀，保证幂等（重复运行不产生叠加）。"""
    t = strip_brand(existing)
    if kind == 'column':
        t = re.sub(r'详细科普\s*$', '', t)
    elif kind == 'article':
        t = re.sub(r'2026实测避坑\s*$', '', t)
    return t.strip()


def make_desc(kind, topic):
    topic = topic.strip()
    if kind == 'article':
        base = (f"{topic}2026实测避坑：实测溯源、实操图文、避坑指南。"
                f"适合{topic}爱好者与从业者参考，掌握核心要点、规避常见误区。")
    elif kind == 'column':
        base = (f"{topic}详细科普：实测溯源、实操图文、避坑指南。"
                f"适合{topic}爱好者与从业者系统了解核心要点与鉴别方法，少走弯路、规避常见误区。")
    else:  # functional
        base = (f"{topic}：龙兄知识库说明页，介绍站点内容、栏目分类与更新动态，"
                f"方便读者快速了解本站并检索实用科普与生活百科内容。")
    if len(base) < 70:
        base = base.rstrip('。') + "。内容持续更新，欢迎对照实操、少踩坑。"
    if len(base) > 90:
        cut = base[:90]
        idx = -1
        for ch in ('。', '，', '、'):
            j = cut.rfind(ch)
            if j > 60:
                idx = j
                break
        cut = cut[:idx] if idx > 0 else cut[:88]
        base = cut.rstrip('，、') + '。'
    return base


def set_title(html, new_title):
    return re.sub(r'<title[^>]*>.*?</title>', f'<title>{new_title}</title>',
                  html, count=1, flags=re.S | re.I)


def set_meta_name(html, name, value):
    html = re.sub(r'<meta\b[^>]*\bname\s*=\s*["\']' + re.escape(name) + r'["\'][^>]*>\s*',
                  '', html, flags=re.I)
    tag = f'<meta name="{name}" content="{value}">\n'
    html = re.sub(r'(</title>)', r'\1\n' + tag, html, count=1, flags=re.I)
    return html


def set_meta_property(html, prop, value):
    def repl(m):
        tag = m.group(0)
        if re.search(r'\bcontent\s*=', tag, re.I):
            return re.sub(r'content\s*=\s*["\'][^"\']*["\']',
                          f'content="{value}"', tag, count=1, flags=re.I)
        return tag.rstrip('>') + f' content="{value}">'
    return re.sub(r'<meta\b[^>]*\bproperty\s*=\s*["\']' + re.escape(prop) + r'["\'][^>]*>',
                  repl, html, flags=re.I)


def add_lazy_and_alt(html, page_title):
    def repl(m):
        tag = m.group(0)
        if re.search(r'\bloading\s*=', tag, re.I):
            return tag
        if re.search(r'fetchpriority\s*=\s*["\']high', tag, re.I):
            return tag  # hero 保持 eager
        tag = re.sub(r'<img\b', '<img loading="lazy"', tag, count=1, flags=re.I)
        if not re.search(r'\balt\s*=', tag, re.I):
            tag = re.sub(r'<img\b', f'<img alt="{page_title}"', tag, count=1, flags=re.I)
        return tag
    return re.sub(r'<img\b[^>]*>', repl, html, flags=re.I)


ART_HEADER = '''<!--SEO-ARTICLE-HEADER-->
<section class="seo-art-head" aria-label="文章信息">
  <figure class="seo-cover"><div class="seo-cover-ph">封面图位置（建议 1200×630 WebP，放此处）</div></figure>
  <div class="seo-art-meta">
    <p class="seo-row"><span class="seo-k">🕓 更新时间</span><span class="seo-v seo-update">____（填 YYYY-MM-DD）</span></p>
    <p class="seo-row"><span class="seo-k">📌 阅读收益</span><span class="seo-v seo-benefit">一句话说明读完能得到什么（待填）</span></p>
    <p class="seo-row"><span class="seo-k">⏱ 时效性</span><span class="seo-v"><span class="seo-tag">时效性标签（如：长期有效 / 2026 适用 / 待核实）</span></span></p>
  </div>
</section>
'''

REL_HEADER = '<!--SEO-RELATED-->\n<section class="seo-related" aria-label="相关专题推荐">\n  <h2 class="seo-rel-hd">相关专题推荐</h2>\n  <div class="seo-rel-grid">\n'
REL_FOOTER = '  </div>\n</section>\n'


def sibling_cards(self_rel):
    d = os.path.dirname(self_rel)
    try:
        names = [n for n in sorted(os.listdir(d)) if n.endswith('.html') and n != os.path.basename(self_rel)]
    except OSError:
        return ''
    cards = []
    for n in names[:5]:
        try:
            t = read(os.path.join(d, n))
        except OSError:
            continue
        m = re.search(r'<title[^>]*>(.*?)</title>', t, re.S | re.I)
        sib_title = strip_brand(m.group(1)).strip() if m else n
        cards.append(
            f'    <a class="seo-rel-card" href="{n}">\n'
            f'      <div class="seo-rel-thumb" aria-hidden="true">图</div>\n'
            f'      <div class="seo-rel-title">{sib_title}</div>\n'
            f'    </a>\n')
    return ''.join(cards)


def inject_article(html, self_rel):
    if '<!--SEO-ARTICLE-HEADER-->' not in html:
        html = re.sub(r'(</nav>)', r'\1\n' + ART_HEADER, html, count=1, flags=re.I)
    if '<!--SEO-RELATED-->' not in html:
        cards = sibling_cards(self_rel)
        if cards:
            block = REL_HEADER + cards + REL_FOOTER
            html = re.sub(r'(</body>)', block + r'\1', html, count=1, flags=re.I)
    return html


def main():
    stats = {'files': 0, 'column': 0, 'article': 0, 'functional': 0,
             'desc': 0, 'lazy': 0, 'injected': 0, 'cssver': 0}
    for dp, dn, fn in os.walk(STATIC):
        dn[:] = [d for d in dn if d not in SKIP_DIR_PARTS]
        for f in sorted(fn):
            if not f.endswith('.html'):
                continue
            rel = os.path.relpath(os.path.join(dp, f), STATIC)
            parts = rel.split('/')
            if 'admin' in parts or any(p in SKIP_DIR_PARTS for p in parts):
                continue
            if f == '404.html':
                continue
            full = os.path.join(dp, f)
            html = read(full)
            before_lazy = len(re.findall(r'<img\b[^>]*>', html, re.I))
            m = re.search(r'<title[^>]*>(.*?)</title>', html, re.S | re.I)
            old_title = m.group(1).strip() if m else ''
            is_article = rel.count('/') >= 1
            fn_base = os.path.basename(rel)

            if not is_article:
                if fn_base in FUNCTIONAL:
                    kind = 'functional'
                    label = FUNCTIONAL[fn_base]
                    new_title = f'{label}｜龙兄知识库'
                    topic = clean_topic(old_title, 'functional')
                    stats['functional'] += 1
                else:
                    kind = 'column'
                    col = clean_topic(old_title, 'column') or old_title
                    new_title = f'{col}详细科普｜龙兄知识库'
                    topic = col
                    stats['column'] += 1
            else:
                kind = 'article'
                topic = clean_topic(old_title, 'article') or old_title
                new_title = f'{topic}2026实测避坑｜龙兄知识库'
                stats['article'] += 1

            html = set_title(html, new_title)
            desc = make_desc(kind, topic)
            html = set_meta_name(html, 'description', desc)
            stats['desc'] += 1
            if kind == 'article':
                kw = f'{topic},2026实测避坑,实测溯源,龙兄知识库'
            elif kind == 'column':
                kw = f'{topic},实测溯源,避坑指南,图文科普,龙兄知识库'
            else:
                kw = f'{topic},龙兄知识库'
            html = set_meta_name(html, 'keywords', kw)
            html = set_meta_property(html, 'og:title', new_title)
            html = set_meta_property(html, 'og:description', desc)
            html = set_meta_property(html, 'twitter:title', new_title)
            html = set_meta_property(html, 'twitter:description', desc)

            # 图片懒加载 + alt
            n_lazy_before = len(re.findall(r'<img\b[^>]*\bloading\s*=', html, re.I))
            html = add_lazy_and_alt(html, new_title)
            n_lazy_after = len(re.findall(r'<img\b[^>]*\bloading\s*=', html, re.I))
            stats['lazy'] += max(0, n_lazy_after - n_lazy_before)

            # CSS 缓存版本号抬高，确保新 .seo-* 样式生效
            if re.search(r'css/style\.css\?v=\d{8}', html):
                html = re.sub(r'(css/style\.css\?v=)\d{8}', r'\g<1>' + NEW_CSS_VER, html)
                stats['cssver'] += 1

            # 文章页注入头部模板 + 相关专题
            if is_article:
                html = inject_article(html, full)
                stats['injected'] += 1

            write(full, html)
            stats['files'] += 1

    print('=== apply_seo 完成 ===')
    for k, v in stats.items():
        print(f'  {k}: {v}')


if __name__ == '__main__':
    sys.exit(main())
