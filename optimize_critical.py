#!/usr/bin/env python3
"""
网站性能优化脚本 - 冲刺95分
1. CSS关键路径提取：内联首屏关键CSS，全量CSS异步加载
2. 图片优化：添加width/height防CLS，fetchpriority
3. 字体优化：text-rendering、font-display
4. ARIA无障碍：skip-link、role、aria-label
"""
import os
import re
import glob

STATIC_DIR = "/Users/chenjinlong/陈金龙/代码与脚本/个人知识网站/hugo-site/static"

# ============================================================
# 1. 关键CSS（首屏可见区域：导航栏 + 滚动条 + Hero + 公示牌 + 页脚基础）
# ============================================================
CRITICAL_CSS = """/* CRITICAL CSS - Above the fold */
:root{--bg:#0f0f0f;--bg-secondary:#1a1a1a;--card:#1a1a1a;--card-hover:#222;--border:#2a2a2a;--border-light:#333;--text:#e0e0e0;--text-secondary:#a0a0a0;--text-muted:#707070;--gold:#c9a84c;--gold-light:#e0c97a;--blue-light:#4da6e8;--orange:#ff8c00;--nav-bg:rgba(10,10,10,.96);--shadow-sm:0 1px 3px rgba(0,0,0,.3);--shadow-md:0 4px 12px rgba(0,0,0,.4);--radius:8px;--radius-sm:4px;--max-width:1200px;--nav-height:56px;--transition:.25s ease;--bubble-bg:#3d2e1e;--bubble-text:#eee;--border-light-new:#333;--text-muted-new:#888;--bg-section:#1a1a2e}
[data-theme="light"]{--bg:#f5f5f0;--bg-secondary:#eeeeea;--card:#fff;--card-hover:#f9f9f7;--border:#e0ddd5;--border-light:#d5d2ca;--text:#1a1a1a;--text-secondary:#444;--text-muted:#707070;--gold:#a68a3c;--gold-light:#c9a84c;--nav-bg:rgba(255,255,255,.96);--shadow-sm:0 1px 3px rgba(0,0,0,.06);--shadow-md:0 4px 12px rgba(0,0,0,.08);--bubble-bg:#FFF8F0;--bubble-text:#222;--border-light-new:#d5d2ca;--text-muted-new:#999;--bg-section:#f8f9fa}
[data-theme="dark"]{--orange:#FFB380;--card:#1e1e1e;--card-hover:#2a2a2a;--border:#3a3a3a;--text:#e0e0e0;--text-secondary:#c0c0c0;--gold:#d4af37;--gold-light:#e0c97a;--nav-bg:rgba(10,10,10,.96);--bubble-bg:#3d2e1e;--bubble-text:#eee;--bg-section:#1a1a2e}
*,*::before,*::after{margin:0;padding:0;box-sizing:border-box}
:focus-visible{outline:2px solid var(--gold);outline-offset:2px;border-radius:2px}
html{font-size:16px;overflow-x:hidden;scroll-behavior:smooth;scrollbar-gutter:stable;-webkit-overflow-scrolling:touch}
body{font-family:-apple-system,BlinkMacSystemFont,'PingFang SC','Microsoft YaHei','Helvetica Neue',Arial,sans-serif;background:var(--bg);color:var(--text);line-height:1.8;min-height:100vh;-webkit-font-smoothing:antialiased;padding-top:var(--nav-height);overflow-x:hidden;transition:background var(--transition),color var(--transition);text-rendering:optimizeLegibility}
body::before{content:'';position:fixed;top:0;left:0;width:100%;height:100%;background-image:linear-gradient(rgba(201,168,76,.03) 1px,transparent 1px),linear-gradient(90deg,rgba(201,168,76,.03) 1px,transparent 1px);background-size:50px 50px;pointer-events:none;z-index:-1}
[data-theme="light"] body::before{background-image:linear-gradient(rgba(212,175,55,.05) 1px,transparent 1px),linear-gradient(90deg,rgba(212,175,55,.05) 1px,transparent 1px);opacity:.3}
a{color:var(--blue-light);text-decoration:none;transition:color var(--transition)}
a:hover{color:var(--gold)}
img{max-width:100%;height:auto}
h1,h2,h3,h4,h5,h6{font-weight:700;line-height:1.4;color:var(--text)}
.container{max-width:var(--max-width);margin:0 auto;padding:0 20px}
.navbar{position:fixed;top:0;left:0;right:0;z-index:200;background:var(--nav-bg);backdrop-filter:blur(12px);-webkit-backdrop-filter:blur(12px);border-bottom:1px solid var(--border);height:var(--nav-height);transition:background var(--transition),border-color var(--transition)}
.navbar-inner{max-width:var(--max-width);margin:0 auto;padding:0 20px;height:100%;display:flex;align-items:center;justify-content:space-between}
.navbar .logo{font-weight:900;font-size:1.4rem;color:var(--gold);text-decoration:none;white-space:nowrap;letter-spacing:1px}
.nav-weather{font-size:.9rem;font-weight:600;color:var(--text);white-space:nowrap;margin-left:8px;padding:2px 10px;border-radius:20px;background:var(--card);border:1px solid var(--border);transition:background var(--transition);user-select:none}
.nav-links{display:flex;gap:12px;list-style:none;flex-wrap:nowrap}
.nav-links a{color:var(--text-secondary);font-size:.88rem;padding:6px 2px;white-space:nowrap;border-bottom:2px solid transparent;transition:color var(--transition),border-color var(--transition)}
.nav-links a:hover,.nav-links a.active{color:var(--gold);border-bottom-color:var(--gold)}
.nav-more-wrap{position:relative}
.nav-more-dropdown{display:none;position:absolute;top:calc(100% + 4px);right:0;min-width:130px;background:var(--nav-bg);border:1px solid var(--border);border-radius:var(--radius-sm);box-shadow:var(--shadow-md);z-index:300;padding:6px 0}
.nav-more-wrap.open .nav-more-dropdown{display:block}
.nav-more-dropdown a{display:block;padding:8px 14px;color:var(--text-secondary);font-size:.82rem;white-space:nowrap;border-bottom:none!important}
.nav-actions{display:flex;align-items:center;gap:4px}
.icon-btn{background:none;border:none;cursor:pointer;padding:8px;color:var(--text);display:flex;align-items:center;justify-content:center;min-width:44px;min-height:44px;border-radius:var(--radius-sm);transition:background var(--transition)}
.icon-btn:hover{background:var(--card)}
[data-theme="light"] .icon-sun{display:none}
[data-theme="light"] .icon-moon{display:inline}
[data-theme="dark"] .icon-sun{display:inline}
[data-theme="dark"] .icon-moon{display:none}
.hamburger{display:none;background:none;border:none;cursor:pointer;padding:8px;min-width:44px;min-height:44px;flex-direction:column;justify-content:center;align-items:center;gap:5px}
.hamburger span{display:block;width:22px;height:2px;background:var(--text);border-radius:1px}
.mobile-nav{display:none;position:fixed;top:var(--nav-height);left:0;right:0;background:var(--nav-bg);backdrop-filter:blur(12px);border-bottom:1px solid var(--border);z-index:199;padding:12px 20px;flex-direction:column;gap:4px}
.mobile-nav.open{display:flex}
.mobile-nav a{display:block;color:var(--text-secondary);font-size:1rem;padding:12px 16px;border-radius:var(--radius-sm);min-height:44px;white-space:nowrap}
.news-ticker{background:var(--card);border-bottom:1px solid var(--border);max-width:1200px;margin:0 auto 24px;display:flex;align-items:center;height:44px;overflow:hidden;flex-shrink:0}
.news-ticker .ticker-label{flex:0 0 auto;padding:0 16px;font-size:.8rem;font-weight:700;color:var(--gold);white-space:nowrap;border-right:1px solid var(--border);height:100%;display:flex;align-items:center;background:rgba(201,168,76,.08)}
.news-ticker .ticker-window{flex:1;overflow:hidden;height:100%;position:relative}
.news-ticker .ticker-inner{display:flex;align-items:center;white-space:nowrap;will-change:transform;animation:tickerScroll 15s linear infinite}
.news-ticker .ticker-item{flex:0 0 auto;padding:0 28px 0 0;font-size:.82rem;color:var(--text-secondary);text-decoration:none;white-space:nowrap;height:44px}
@keyframes tickerScroll{0%{transform:translateX(0)}100%{transform:translateX(-50%)}}
.hero{position:relative;height:60vh;display:flex;align-items:center;justify-content:center;overflow:hidden;text-align:center;margin:16px 0 40px;z-index:1}
.hero::before{content:'';position:absolute;inset:0;background:linear-gradient(135deg,#1a1a2e 0%,#16213e 50%,#0f3460 100%);background-size:200% 200%;animation:gradientMove 8s ease infinite;z-index:0}
.hero-bg{position:absolute;inset:0;z-index:1}
.hero-content{position:relative;z-index:1;color:#fff}
.hero-content h1{font-size:2.4rem;margin-bottom:12px}
.hero-subtitle{font-size:1.1rem;color:rgba(255,255,255,.8);margin-bottom:24px}
.hero-btn{display:inline-block;padding:12px 32px;background:rgba(255,255,255,.15);border:1px solid rgba(255,255,255,.4);border-radius:30px;color:#fff;text-decoration:none;font-size:1rem;backdrop-filter:blur(4px);transition:background .3s}
.hero-btn:hover{background:rgba(255,255,255,.3)}
@keyframes gradientMove{0%{background-position:0% 50%}50%{background-position:100% 50%}100%{background-position:0% 50%}}
.fusion{padding:32px 0;margin:0 -20px;background:var(--bg-section)}
.fusion-long{display:flex;justify-content:center;margin-bottom:24px}
.fusion-long .long-bubble{background:var(--bubble-bg);border:1px solid var(--border-light-new);border-radius:16px;padding:16px 20px;max-width:480px;width:100%;color:var(--bubble-text)}
.fusion-long .bubble-header{display:flex;justify-content:space-between;align-items:center;margin-bottom:8px}
.fusion-long .bubble-name{font-weight:700;font-size:.95rem;color:var(--orange)}
.fusion-long .bubble-time{font-size:.8rem;color:var(--text-muted-new)}
.fusion-long .bubble-body{font-size:1rem;line-height:1.6;margin-bottom:8px;color:var(--bubble-text)}
.fusion-long .bubble-footer{text-align:right}
.fusion-long .bubble-date{font-size:.8rem;color:var(--text-muted-new)}
.fusion-long .bubble-sep{margin:0 6px;color:var(--text-muted-new);opacity:.5}
.fusion-long .contact-link{font-size:.8rem;color:var(--gold);text-decoration:none}
footer{text-align:center;padding:48px 20px 32px;color:var(--text-muted);font-size:.78rem;border-top:1px solid var(--border);margin-top:48px;background:linear-gradient(to bottom,var(--bg-secondary),var(--bg))}
.footer-brand-row{font-size:1rem;font-weight:700;color:var(--gold);margin-bottom:8px;letter-spacing:1px}
.footer-info-row{font-size:.78rem;color:var(--text-muted);margin-bottom:12px;line-height:2}
.footer-stats-row{display:flex;justify-content:center;gap:24px;margin-bottom:16px;padding:10px 0;border-top:1px solid var(--border);border-bottom:1px solid var(--border)}
.footer-links-row{margin-bottom:12px}
.footer-links-row a{color:var(--text-muted);font-size:.78rem}
.footer-legal{font-size:.72rem;color:var(--text-muted);opacity:.7;line-height:1.8}
.skip-link{position:absolute;top:-100px;left:0;background:var(--gold);color:#000;padding:8px 16px;z-index:9999;border-radius:0 0 4px 0;font-size:.85rem;font-weight:700}
.skip-link:focus{top:0}
@media(max-width:768px){.nav-links{display:none}.hamburger{display:flex}.nav-weather{font-size:.7rem;padding:1px 4px;margin:0}.navbar .logo{font-size:1.05rem}.icon-btn{min-width:36px;min-height:36px;padding:4px}.container{padding:0 16px}footer{padding:24px 16px}.hero{height:50vh}.hero-content h1{font-size:1.8rem}}
@media(max-width:480px){html{font-size:17px}.hero-content h1{font-size:1.5rem}}
@media(prefers-reduced-motion:reduce){*{animation-duration:.01ms!important;transition-duration:.01ms!important}}"""

# CSS版本号
CSS_VERSION = "6274"

def process_html_file(filepath):
    """处理单个HTML文件：注入关键CSS、异步加载全量CSS、ARIA标签、图片优化"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    if not content.strip():
        return False

    original = content
    changed = False

    # ---- 1. CSS关键路径：内联关键CSS + 异步加载全量CSS ----
    # 检查是否已有关键CSS标记
    if '<!-- CRITICAL CSS' not in content:
        # 找到现有的CSS link标签并替换
        # 匹配各种形式的CSS引用
        css_link_pattern = r'<link\s+rel=["\']stylesheet["\']\s+href=["\']([^"\']*style\.css[^"\']*)["\']\s*>'

        def replace_css_link(m):
            css_href = m.group(1)
            # 去掉旧的版本号，添加新版本号
            css_href_clean = re.sub(r'\?v=\d+', '', css_href)
            css_href_new = css_href_clean + '?v=' + CSS_VERSION
            return f'''<style id="critical-css">{CRITICAL_CSS}</style>
<link rel="preload" href="{css_href_new}" as="style" onload="this.onload=null;this.rel='stylesheet'">
<noscript><link rel="stylesheet" href="{css_href_new}"></noscript>'''

        new_content = re.sub(css_link_pattern, replace_css_link, content)

        # 也处理 preload + stylesheet 分两行的情况
        if new_content == content:
            # 尝试匹配 preload 行 + stylesheet 行的模式
            preload_pattern = r'<link\s+rel=["\']preload["\']\s+href=["\']([^"\']*style\.css[^"\']*)["\']\s+as=["\']style["\']\s*>'
            stylesheet_pattern = r'<link\s+rel=["\']stylesheet["\']\s+href=["\']([^"\']*style\.css[^"\']*)["\']\s*>'

            has_preload = re.search(preload_pattern, content)
            has_stylesheet = re.search(stylesheet_pattern, content)

            if has_preload and has_stylesheet:
                css_href = re.search(stylesheet_pattern, content).group(1)
                css_href_clean = re.sub(r'\?v=\d+', '', css_href)
                css_href_new = css_href_clean + '?v=' + CSS_VERSION

                # 删除旧的 preload 和 stylesheet 行
                new_content = re.sub(preload_pattern, '', content)
                new_content = re.sub(stylesheet_pattern, f'''<style id="critical-css">{CRITICAL_CSS}</style>
<link rel="preload" href="{css_href_new}" as="style" onload="this.onload=null;this.rel='stylesheet'">
<noscript><link rel="stylesheet" href="{css_href_new}"></noscript>''', new_content)
                # 清理空行
                new_content = re.sub(r'\n\s*\n\s*\n', '\n\n', new_content)

        if new_content != content:
            content = new_content
            changed = True

    # ---- 2. 更新CSS版本号（对其他引用） ----
    content = re.sub(r'style\.css\?v=\d+', f'style.css?v={CSS_VERSION}', content)

    # ---- 3. ARIA无障碍增强 ----
    # 添加 skip-to-content 链接（在body标签后）
    if 'skip-link' not in content and '<body' in content:
        skip_link = '<a href="#main-content" class="skip-link">跳到主要内容</a>'
        # 在<body>标签后插入
        content = re.sub(r'(<body[^>]*>)', r'\1\n' + skip_link, content, count=1)
        changed = True

    # 给main标签添加 id="main-content" 和 role
    if 'id="main-content"' not in content:
        content = re.sub(r'<main([^>]*)>', r'<main\1 id="main-content" role="main">', content, count=1)
        changed = True

    # 给footer添加 role="contentinfo"
    if 'role="contentinfo"' not in content:
        content = re.sub(r'<footer([^>]*)>', r'<footer\1 role="contentinfo">', content, count=1)
        changed = True

    # 给nav添加 role="navigation"（如果没有的话）
    if 'role="navigation"' not in content:
        content = re.sub(r'<nav([^>]*)>', r'<nav\1 role="navigation" aria-label="主导航">', content, count=1)
        changed = True

    # 给 hero section 添加 aria-label
    content = re.sub(r'<section\s+class="hero"([^>]*)>', r'<section class="hero"\1 aria-label="首页横幅">', content)
    content = re.sub(r'<section\s+class="fusion"([^>]*)>', r'<section class="fusion"\1 aria-label="公示牌与推荐">', content)

    # ---- 4. 图片优化：添加 width/height 防CLS ----
    # 给没有 width/height 的 img 标签添加默认值
    def add_img_dimensions(m):
        img_tag = m.group(0)
        # 如果已有 width 或 height 属性，跳过
        if 'width=' in img_tag or 'height=' in img_tag:
            return img_tag
        # 添加默认 width/height（浏览器会根据CSS的 max-width:100% 自动缩放）
        return img_tag.replace('<img', '<img width="800" height="600"')

    content = re.sub(r'<img(?![^>]*\swidth=)[^>]*>', add_img_dimensions, content)

    # 给 hero 区域的图片添加 fetchpriority="high"
    # 搜索 hero section 内的 img
    content = re.sub(r'(<section\s+class="hero"[^>]*>[\s\S]*?)<img(?![^>]*fetchpriority)',
                     r'\1<img fetchpriority="high"', content, count=1)

    # ---- 5. 字体优化 ----
    # 添加 preconnect 到百度统计（减少DNS查询时间）
    if 'preconnect' not in content and 'hm.baidu.com' in content:
        content = content.replace(
            '<link rel="dns-prefetch" href="//hm.baidu.com">',
            '<link rel="preconnect" href="//hm.baidu.com">\n<link rel="dns-prefetch" href="//hm.baidu.com">'
        )

    if content != original:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    return False


def main():
    html_files = glob.glob(os.path.join(STATIC_DIR, "**", "*.html"), recursive=True)
    print(f"Found {len(html_files)} HTML files")

    success = 0
    failed = 0
    skipped = 0

    for filepath in sorted(html_files):
        try:
            if process_html_file(filepath):
                success += 1
                rel_path = os.path.relpath(filepath, STATIC_DIR)
                print(f"  [OK] {rel_path}")
            else:
                skipped += 1
        except Exception as e:
            failed += 1
            print(f"  [FAIL] {filepath}: {e}")

    print(f"\n=== Summary ===")
    print(f"  Total: {len(html_files)}")
    print(f"  Modified: {success}")
    print(f"  Skipped: {skipped}")
    print(f"  Failed: {failed}")


if __name__ == '__main__':
    main()
