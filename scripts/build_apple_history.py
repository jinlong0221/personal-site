#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成「苹果」合并板块页里的「产品发展史」半区（注入 static/apple.html）。

背景
----
2026-09-18 应龙兄要求，「苹果新品」与「苹果产品发展史」两个板块合并为一个「苹果」板块：
一页两级切换，一级分「在售新品 / 产品发展史」两半（CSS-only radio + label），
二级在各自半区内部再分栏。本脚本只负责「产品发展史」这一半。

设计要点
--------
1. **只碰自己那一半**：用哨兵注释 `<!-- AHUB:HIST:START/END -->` 圈定写入范围，
   绝不改写「在售新品」半区，也绝不重写 `<head>`（CSP sha256 哈希绝不能变）。
2. **CSS-only 标签页**：用原生 `<input type="radio">` + `label` 切换产品线，
   本半区零内联脚本 → CSP 哈希天然有效、JS 失效也能用。
3. **不做长列表**：10 条产品线各自成栏，内部再按年代折叠，避免一拉到底。

改内容只改 scripts/apple_history_data.py，然后跑本脚本：

    python3 scripts/build_apple_history.py

生成的 static/apple.html 即部署源（CI 不重跑本脚本，改完必须手动跑一次并提交）。
"""

import html
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from apple_history_data import (  # noqa: E402
    AUDIO, CEOS, CHIP, COMPANY, DESC, ERAS, GALLERY, IPAD, IPHONE, IPOD,
    LEDE, LINES, MAC, SOFTWARE, SOURCES, SPATIAL, WATCH,
)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, "static", "apple.html")
UPDATED = "2026-09-18"
TAG_BLUE = ("换帅", "已排期")

E = html.escape


# ---------------------------------------------------------------------------
# 页面 CSS
# ---------------------------------------------------------------------------
def build_css(n_lines: int) -> str:
    tab_rules = ",\n".join(
        '#ah%d:checked~.ah-panels>.ah-panel:nth-child(%d)' % (i, i + 1)
        for i in range(n_lines)
    )
    active_rules = ",\n".join(
        '#ah%d:checked~.ah-tabbar label[for="ah%d"],\n'
        '#ah%d:checked~.ah-pick label[for="ah%d"]' % (i, i, i, i)
        for i in range(n_lines)
    )
    focus_rules = ",\n".join(
        '.ah-tabs:has(#ah%d:focus-visible) .ah-tabbar label[for="ah%d"],\n'
        '.ah-tabs:has(#ah%d:focus-visible) .ah-pick label[for="ah%d"]' % (i, i, i, i)
        for i in range(n_lines)
    )
    fg_rules = ",\n".join(
        '#ah%d:checked~.ah-pick label[for="ah%d"] b,\n'
        '#ah%d:checked~.ah-pick label[for="ah%d"] i,\n'
        '#ah%d:checked~.ah-pick label[for="ah%d"] em' % (i, i, i, i, i, i)
        for i in range(n_lines)
    )
    css = """:root{--ah:#c9a84c;--ah-2:#5ac8fa;--ah-soft:rgba(201,168,76,.14);--ah-line:rgba(201,168,76,.45)}
[data-theme="light"]{--ah:#a68a3c;--ah-2:#0a84c8;--ah-soft:rgba(166,138,60,.10);--ah-line:rgba(166,138,60,.45)}
.ah-lede{margin:18px 0 0;padding:14px 18px;border-left:3px solid var(--ah-2);border-radius:0 12px 12px 0;background:var(--bg-secondary);color:var(--text-secondary);font-size:.88rem;line-height:1.85}
.ah-sec{margin:48px 0 0}
.ah-sec-title{display:flex;align-items:center;flex-wrap:wrap;gap:8px 10px;font-size:1.26rem;font-weight:800;margin-bottom:6px;padding-left:12px;border-left:4px solid var(--ah)}
.ah-sec-sub{font-size:.86rem;color:var(--text-muted);margin:0 0 18px 16px}
.ah-era-strip{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}
.ah-era{display:block;background:var(--card);border:1px solid var(--border);border-top:3px solid var(--ah);border-radius:12px;padding:15px 15px 16px;transition:transform .2s,box-shadow .2s,border-color .2s}
.ah-era:hover{transform:translateY(-3px);box-shadow:var(--shadow-md);border-color:var(--ah)}
.ah-era-y{font-size:.73rem;font-weight:700;color:var(--ah-2);letter-spacing:.5px;font-variant-numeric:tabular-nums}
.ah-era-n{font-size:1rem;font-weight:800;margin:6px 0 8px;color:var(--text)}
.ah-era-d{font-size:.8rem;color:var(--text-secondary);line-height:1.7}
.ah-tabs{margin-top:4px}
.ah-r{position:absolute;width:1px;height:1px;opacity:0;pointer-events:none;margin:0}
.ah-pick{display:grid;grid-template-columns:repeat(auto-fit,minmax(152px,1fr));gap:10px;margin:16px 0 20px}
.ah-pk{display:block;cursor:pointer;background:var(--bg-secondary);border:1px solid var(--border);border-radius:11px;padding:11px 13px;transition:background .18s,border-color .18s,transform .18s}
.ah-pk:hover{border-color:var(--ah);transform:translateY(-2px)}
.ah-pk b{display:block;font-size:.9rem;font-weight:800;color:var(--text);line-height:1.35}
.ah-pk i{display:block;font-style:normal;font-size:.71rem;color:var(--text-muted);margin-top:3px;font-variant-numeric:tabular-nums}
.ah-pk em{display:block;font-style:normal;font-size:.7rem;font-weight:800;color:var(--ah);margin-top:7px}
.ah-tabbar{position:sticky;top:var(--nav-height,56px);z-index:29;display:flex;gap:6px;overflow-x:auto;scrollbar-width:none;-webkit-overflow-scrolling:touch;padding:9px 2px;margin:0 0 20px;background:var(--bg);border-bottom:1px solid var(--border)}
.ah-tabbar::-webkit-scrollbar{display:none}
.ah-tab{flex:0 0 auto;cursor:pointer;padding:7px 15px;border-radius:999px;border:1px solid var(--border);background:var(--card);color:var(--text-secondary);font-size:.83rem;font-weight:600;white-space:nowrap;transition:background .18s,color .18s,border-color .18s}
.ah-tab:hover{color:var(--text);border-color:var(--ah)}
.ah-panel{display:none}
/*TAB_RULES*/{display:block}
/*ACTIVE_RULES*/{background:var(--ah);border-color:var(--ah);color:#1a1408;font-weight:800}
/*FOCUS_RULES*/{outline:2px solid var(--ah);outline-offset:2px}
/*FG_RULES*/{color:#1a1408}
.ah-lt{font-size:1.18rem;margin:0 0 5px;display:flex;align-items:center;flex-wrap:wrap;gap:8px}
.ah-lt-n{font-size:.71rem;font-weight:800;color:var(--ah);border:1px solid var(--ah-line);border-radius:999px;padding:1px 9px;white-space:nowrap}
.ah-lt-sub{font-size:.86rem;color:var(--text-secondary);margin:0 0 3px;line-height:1.7}
.ah-lt-span{font-size:.75rem;color:var(--text-muted);font-variant-numeric:tabular-nums;letter-spacing:.3px}
.ah-group{margin-top:20px;border:1px solid var(--border);border-radius:12px;background:var(--card);overflow:hidden}
.ah-gh{display:flex;align-items:center;gap:10px;cursor:pointer;padding:11px 14px;background:var(--bg-secondary);border-left:3px solid var(--ah);list-style:none;transition:background .18s}
.ah-gh:hover{background:var(--card-hover)}
.ah-gh::-webkit-details-marker{display:none}
.ah-gh h4{font-size:.89rem;margin:0;color:var(--ah);font-weight:800;flex:1 1 auto;min-width:0;line-height:1.5}
.ah-gh-n{flex:0 0 auto;font-size:.69rem;font-weight:700;color:var(--text-muted);border:1px solid var(--border);border-radius:999px;padding:1px 8px;white-space:nowrap}
.ah-gh-a{flex:0 0 auto;width:8px;height:8px;border-right:2px solid var(--ah);border-bottom:2px solid var(--ah);transform:rotate(45deg);margin:-3px 2px 0 0;transition:transform .2s}
.ah-group[open]>.ah-gh .ah-gh-a{transform:rotate(-135deg);margin-top:4px}
.ah-tl{list-style:none;margin:0;padding:16px 16px 6px 34px;position:relative}
.ah-tl::before{content:'';position:absolute;left:16px;top:22px;bottom:18px;width:2px;background:linear-gradient(var(--ah),var(--ah-2));opacity:.75}
.ah-ev{position:relative;display:grid;grid-template-columns:92px 1fr;gap:4px 16px;padding:0 0 14px}
.ah-ev::before{content:'';position:absolute;left:-22px;top:5px;width:11px;height:11px;border-radius:50%;background:var(--ah);border:2px solid var(--card)}
.ah-ev-d{font-size:.74rem;font-weight:800;color:var(--ah);font-variant-numeric:tabular-nums;letter-spacing:.2px;padding-top:3px}
.ah-ev-b{min-width:0}
.ah-ev-t{font-size:.95rem;font-weight:700;margin:0 0 3px;line-height:1.5}
.ah-ev-b p{font-size:.84rem;color:var(--text-secondary);line-height:1.7;margin:0}
.ah-tag{display:inline-block;font-size:.67rem;font-weight:700;padding:1px 7px;border-radius:5px;margin-left:6px;vertical-align:1px;background:var(--ah-soft);color:var(--ah);white-space:nowrap}
.ah-tag-blue{background:rgba(90,200,250,.14);color:#2b93c9}
[data-theme="dark"] .ah-tag-blue{color:#7fd0f5}
.ah-now{margin-top:22px;padding:14px 16px;background:var(--bg-secondary);border:1px solid var(--border);border-left:3px solid var(--ah);border-radius:10px;font-size:.84rem;color:var(--text-secondary);line-height:1.8}
.ah-now b{color:var(--ah);margin-right:6px}
.ah-ceo-row{display:grid;grid-template-columns:repeat(3,1fr);gap:16px}
.ah-ceo{background:var(--card);border:1px solid var(--border);border-radius:14px;overflow:hidden}
.ah-ceo-img{aspect-ratio:3/2;background:var(--bg-secondary);overflow:hidden;display:flex;align-items:center;justify-content:center;padding:10px}
.ah-ceo-img img{max-width:100%;max-height:100%;width:auto;height:auto;object-fit:contain;display:block;border-radius:8px}
.ah-ceo-b{padding:14px 16px 16px}
.ah-ceo-n{font-size:1.02rem;font-weight:800;margin:0 0 2px}
.ah-ceo-t{font-size:.76rem;color:var(--ah);font-weight:700;margin-bottom:8px}
.ah-ceo-b p{font-size:.82rem;color:var(--text-secondary);line-height:1.72;margin:0}
.ah-gallery{display:grid;grid-template-columns:repeat(3,1fr);gap:16px}
.ah-fig{margin:0;background:var(--card);border:1px solid var(--border);border-radius:14px;overflow:hidden}
.ah-fig-img{aspect-ratio:4/3;background:var(--bg-secondary);overflow:hidden;display:flex;align-items:center;justify-content:center;padding:8px}
.ah-fig-img img{max-width:100%;max-height:100%;width:auto;height:auto;object-fit:contain;display:block;border-radius:6px}
.ah-fig-cap{padding:10px 13px 12px;font-size:.78rem;color:var(--text-secondary);line-height:1.62}
.ah-fig-cap b{display:block;color:var(--text);font-size:.86rem;margin-bottom:3px}
.ah-note{margin:44px 0 8px;padding:16px 18px;background:var(--bg-secondary);border:1px solid var(--border);border-radius:12px;font-size:.82rem;color:var(--text-secondary);line-height:1.85}
.ah-note h3{font-size:.92rem;margin:0 0 9px;color:var(--text)}
.ah-note ul{margin:0 0 12px;padding-left:19px}
.ah-note li{margin-bottom:5px}
.ah-note a{color:var(--ah);text-decoration:underline;text-underline-offset:2px}
@media(max-width:992px){.ah-era-strip,.ah-gallery,.ah-ceo-row{grid-template-columns:repeat(2,1fr)}}
@media(max-width:640px){.ah-sec{margin-top:30px}.ah-lede{padding:12px 14px;font-size:.84rem}.ah-era-strip,.ah-gallery{grid-template-columns:repeat(2,1fr);gap:10px}.ah-era{padding:11px 11px 12px}.ah-era-n{font-size:.92rem;margin:5px 0 6px}.ah-era-d{font-size:.76rem}.ah-fig-cap{padding:8px 10px 9px;font-size:.72rem}.ah-fig-cap b{font-size:.8rem}.ah-ev{grid-template-columns:1fr;gap:1px}.ah-ev-d{padding-top:0}.ah-pick{grid-template-columns:repeat(2,1fr)}.ah-lt{font-size:1.06rem}.ah-tl{padding:14px 12px 4px 30px}.ah-tl::before{left:13px}.ah-gh{padding:10px 12px}.ah-ceo-row{grid-template-columns:1fr;gap:10px}.ah-ceo{display:grid;grid-template-columns:94px 1fr}.ah-ceo-img{aspect-ratio:1/1;padding:7px;border-right:1px solid var(--border)}.ah-ceo-b{padding:9px 12px 10px}.ah-ceo-n{font-size:.94rem}.ah-ceo-t{font-size:.71rem;margin-bottom:4px}.ah-ceo-b p{font-size:.77rem;line-height:1.58}.ah-note{margin:30px 0 8px;padding:13px 15px;font-size:.79rem;line-height:1.76}}
@media print{.ah-panel{display:block!important}.ah-tabbar,.ah-pick,.ah-r{display:none!important}.ah-group>*:not(summary){display:block!important}.ah-gh{background:none}}
@media(prefers-reduced-motion:reduce){.ah-era,.ah-pk{transition:none}}"""
    return (css
            .replace("/*TAB_RULES*/", tab_rules)
            .replace("/*ACTIVE_RULES*/", active_rules)
            .replace("/*FOCUS_RULES*/", focus_rules)
            .replace("/*FG_RULES*/", fg_rules))


# ---------------------------------------------------------------------------
# 页面主体
# ---------------------------------------------------------------------------
def render_era_strip() -> str:
    out = ['<div class="ah-era-strip">']
    for idx, name, years, desc in ERAS:
        out.append(
            '      <div class="ah-era">\n'
            f'        <div class="ah-era-y">{E(years)}</div>\n'
            f'        <div class="ah-era-n">{E(idx)}　{E(name)}</div>\n'
            f'        <div class="ah-era-d">{E(desc)}</div>\n'
            "      </div>"
        )
    out.append("    </div>")
    return "\n".join(out)


def count_entries(line) -> int:
    return sum(len(items) for _, items in line[4])


def render_panel(line, index: int) -> str:
    lid, name, years, tagline, groups, now = line
    n = count_entries(line)
    out = [f'    <section class="ah-panel" id="ahp-{lid}" role="tabpanel" aria-label="{E(name)}">']
    out.append(f'      <h3 class="ah-lt">{E(name)}<span class="ah-lt-n">{n} 条</span></h3>')
    out.append(f'      <p class="ah-lt-sub">{E(tagline)}</p>')
    out.append(f'      <div class="ah-lt-span">{E(years)}</div>')
    for gi, (gtitle, items) in enumerate(groups):
        opened = " open" if gi == 0 else ""
        out.append(f'      <details class="ah-group"{opened}>')
        out.append(
            '        <summary class="ah-gh">\n'
            f'          <h4>{E(gtitle)}</h4>\n'
            f'          <span class="ah-gh-n">{len(items)} 条</span>\n'
            '          <i class="ah-gh-a" aria-hidden="true"></i>\n'
            "        </summary>"
        )
        out.append('        <ul class="ah-tl">')
        for date, title, body, flag in items:
            badge = ""
            if flag:
                cls = "ah-tag ah-tag-blue" if flag in TAG_BLUE else "ah-tag"
                badge = f'<span class="{cls}">{E(flag)}</span>'
            out.append(
                "          <li class=\"ah-ev\">\n"
                f'            <div class="ah-ev-d">{E(date)}</div>\n'
                '            <div class="ah-ev-b">\n'
                f'              <div class="ah-ev-t">{E(title)}{badge}</div>\n'
                f"              <p>{E(body)}</p>\n"
                "            </div>\n"
                "          </li>"
            )
        out.append("        </ul>")
        out.append("      </details>")
    if now:
        out.append(f'      <div class="ah-now"><b>现状</b>{E(now)}</div>')
    out.append("    </section>")
    return "\n".join(out)


def render_tabs() -> str:
    n = len(LINES)
    out = ['<div class="ah-tabs">']
    for i, line in enumerate(LINES):
        checked = " checked" if i == 0 else ""
        out.append(
            f'    <input class="ah-r" type="radio" name="ahtab" id="ah{i}"'
            f'{checked} aria-label="{E(line[1])}">'
        )
    out.append('    <div class="ah-pick">')
    for i, line in enumerate(LINES):
        lid, name, years, tagline, _groups, _now = line
        out.append(
            f'      <label class="ah-pk" for="ah{i}">\n'
            f"        <b>{E(name)}</b>\n"
            f"        <i>{E(years)}</i>\n"
            f"        <em>{count_entries(line)} 条 · 展开 ❯</em>\n"
            "      </label>"
        )
    out.append("    </div>")
    out.append('    <div class="ah-tabbar" role="tablist" aria-label="产品线切换">')
    for i, line in enumerate(LINES):
        out.append(f'      <label class="ah-tab" for="ah{i}">{E(line[1])}</label>')
    out.append("    </div>")
    out.append('    <div class="ah-panels">')
    for i, line in enumerate(LINES):
        out.append(render_panel(line, i))
    out.append("    </div>")
    out.append("  </div>")
    return "\n".join(out)


def render_half(total: int) -> str:
    """发展史半区内容。

    不含 <main>／面包屑／hero —— 合并后的 static/apple.html 自己承担这些，
    本函数只产出「产品发展史」这一半的内部 HTML。
    """
    out = []
    out.append('  <p class="ah-lede">%s</p>' % E(LEDE.replace("{N}", str(total))))
    out.append("")
    out.append('  <section class="ah-sec">')
    out.append('    <h2 class="ah-sec-title">六个时代，一部断代史</h2>')
    out.append('    <p class="ah-sec-sub">半个世纪被切成六段，每一段都有一个明确的转折点。</p>')
    out.append("    " + render_era_strip())
    out.append("  </section>")
    out.append("")
    out.append('  <section class="ah-sec">')
    out.append('    <h2 class="ah-sec-title">十条产品线，逐年拆开</h2>')
    out.append('    <p class="ah-sec-sub">先点产品线切换，再点开想看的年代分组——默认只展开第一条，不会一拉到底。打印本页会自动展开全部。</p>')
    out.append("  " + render_tabs())
    out.append("  </section>")
    out.append("")
    out.append('  <section class="ah-sec">')
    out.append('    <h2 class="ah-sec-title">三位掌门人</h2>')
    out.append('    <p class="ah-sec-sub">五十年里，真正掌权的只有三个人。</p>')
    out.append('    <div class="ah-ceo-row">')
    for _cid, name, term, img, w, h, bio in CEOS:
        out.append(
            '      <div class="ah-ceo">\n'
            '        <div class="ah-ceo-img">\n'
            f'          <img src="{E(img)}" alt="{E(name)}" width="{w}" height="{h}" loading="lazy" decoding="async">\n'
            "        </div>\n"
            '        <div class="ah-ceo-b">\n'
            f'          <h3 class="ah-ceo-n">{E(name)}</h3>\n'
            f'          <div class="ah-ceo-t">{E(term)}</div>\n'
            f"          <p>{E(bio)}</p>\n"
            "        </div>\n"
            "      </div>"
        )
    out.append("    </div>")
    out.append("  </section>")
    out.append("")
    out.append('  <section class="ah-sec">')
    out.append('    <h2 class="ah-sec-title">产品图集</h2>')
    out.append('    <p class="ah-sec-sub">全部为真实照片，来源见下方「参考来源」。</p>')
    out.append('    <div class="ah-gallery">')
    for slug, w, h, title, cap in GALLERY:
        out.append(
            '      <figure class="ah-fig">\n'
            '        <div class="ah-fig-img">\n'
            f'          <img src="img/apple/history/{slug}.webp" alt="{E(title)}" width="{w}" height="{h}" '
            'loading="lazy" decoding="async">\n'
            "        </div>\n"
            f'        <figcaption class="ah-fig-cap"><b>{E(title)}</b>{E(cap)}</figcaption>\n'
            "      </figure>"
        )
    out.append("    </div>")
    out.append("  </section>")
    out.append("")
    out.append('  <section class="ah-sec">')
    out.append('    <h2 class="ah-sec-title">参考来源</h2>')
    out.append('    <div class="ah-note">')
    out.append("      <h3>本页信息如何核对</h3>")
    out.append("      <ul>")
    for name, url, note in SOURCES:
        out.append(f'        <li><a href="{E(url)}" target="_blank" rel="noopener nofollow">{E(name)}</a>——{E(note)}</li>')
    out.append("      </ul>")
    out.append("      <ul>")
    out.append("        <li>所有条目均标注具体日期；同一年内多个事件按月份排序，日期存疑的只写年份或月份。</li>")
    out.append("        <li>历史产品照片来自 Wikimedia Commons（CC 授权），版权归原作者所有。</li>")
    out.append("        <li>本页为个人整理的知识沉淀，如发现事实性错误欢迎指正。</li>")
    out.append("      </ul>")
    out.append("    </div>")
    out.append("  </section>")
    out.append("")
    return "\n".join(out)


# ---------------------------------------------------------------------------
# 拼装
# ---------------------------------------------------------------------------
def main() -> int:
    if not os.path.exists(PAGE):
        print("找不到 %s" % PAGE)
        return 1
    src = open(PAGE, encoding="utf-8").read()

    total = sum(count_entries(l) for l in LINES)
    css = build_css(len(LINES))
    half = render_half(total)

    # 1) 页面级样式块 <style id="ah-css">（只装发展史半区的 .ah-* 规则）
    c_i = src.find('<style id="ah-css">')
    if c_i < 0:
        print("未找到 <style id=\"ah-css\">，请先用 _bootstrap_apple_hub.py 完成合并改造")
        return 1
    c_j = src.find("</style>", c_i)
    src = src[:c_i] + '<style id="ah-css">' + css + src[c_j:]

    # 2) 只替换发展史半区的哨兵区间，绝不碰「在售新品」半区
    s_i = src.find("<!-- AHUB:HIST:START")
    e_i = src.find("<!-- AHUB:HIST:END")
    if s_i < 0 or e_i < s_i:
        print("未找到 AHUB:HIST 哨兵注释")
        return 1
    s_e = src.find("-->", s_i) + 3
    src = src[:s_e] + "\n" + half + "\n        " + src[e_i:]

    # 3) 文章更新日期
    src = re.sub(r'<meta name="article-updated" content="[^"]*">',
                 '<meta name="article-updated" content="%s">' % UPDATED, src, count=1)

    open(PAGE, "w", encoding="utf-8").write(src)

    print("已生成 %s" % os.path.relpath(PAGE, ROOT))
    print("  产品线 %d 条，里程碑合计 %d 条，图集 %d 张" % (len(LINES), total, len(GALLERY)))
    print("  文件大小 %.1f KB" % (len(src.encode("utf-8")) / 1024))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
