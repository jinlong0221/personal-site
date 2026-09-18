#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_bootstrap_apple_hub.py — 一次性手术：把「苹果新品」页改造成合并后的「苹果」板块页。

只跑一次。做完这件事就退休（后续内容更新走 build_apple_history.py）。

改造内容
1. body 加 data-no-secnav（本页自带分区导航，禁止按标题再生成章节条）
2. <head> 标题/关键词/描述/文章标签 改为覆盖「在售新品 + 产品发展史」两块
3. hero 重写：h1 苹果 + 覆盖两块的导语 + 三格统计
4. 删掉指向 apple-history.html 的旧宣传条（已被分区卡取代）
5. 追加两个样式块：<style id="ahub-css">（分区切换）、<style id="ah-css">（发展史，由生成器填）
6. 把原有「分栏导航 + 4 个面板」整体包进 NOW 半区，并追加 HIST 半区（哨兵注释包裹）

手术锚点全部走字符串查找 + 断言，找不到就直接报错退出，不会写坏文件。
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, "static", "apple.html")

TITLE = "苹果 · 在售新品与产品发展史｜龙兄知识库"
KEYWORDS = "苹果,Apple,iPhone,iPad,Mac,Apple Watch,在售新品,产品发展史,产品线,时间线,龙兄知识库"
DESC = ("苹果板块合二为一：在售机型的参数与国行价格每日自动刷新，"
        "1976–2026 五十年的十条产品线 293 条里程碑逐年可查。一个入口，既看现在也看过去。")
TAGS = "苹果,新品,发展史,时间线"

HERO = """  <!-- ===== Hero ===== -->
  <div class="ap-hero">
    <span class="ap-kicker">APPLE · 在售新品 + 产品发展史</span>
    <h1>苹果</h1>
    <p>一个入口装两块内容：<b>看现在</b>——在售机型的参数与国行价格，每日自动刷新；<b>看过去</b>——1976 年车库里的 Apple I 到 2026 年的折叠屏 iPhone Duo，十条产品线 293 条里程碑。点下面任意一张卡片切换。</p>
    <div class="ap-stats">
      <div class="ap-stat"><b>6 款</b><span>本期在售新品</span></div>
      <div class="ap-stat"><b>293 条</b><span>历史里程碑</span></div>
      <div class="ap-stat"><b>1976–2026</b><span>五十年跨度</span></div>
    </div>
  </div>
"""

SWITCH_OPEN = """  <!-- ===== 板块分区：在售新品 / 产品发展史（一次只看一半，避免一拉到底） ===== -->
  <div class="ahub">
    <input class="ahub-r" type="radio" name="ahub" id="ahub-now" checked aria-label="在售新品">
    <input class="ahub-r" type="radio" name="ahub" id="ahub-hist" aria-label="产品发展史">
    <div class="ahub-cards">
      <label class="ahub-card" for="ahub-now">
        <span class="ahub-ico" aria-hidden="true"><svg viewBox="0 0 24 24" width="21" height="21" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M3 7h18M3 12h18M3 17h11"/></svg></span>
        <span class="ahub-tx">
          <b>在售新品</b>
          <i>现在在卖的机型、参数与国行价格</i>
          <em>6 款 · 每日自动刷新</em>
        </span>
        <span class="ahub-go">看现在 →</span>
      </label>
      <label class="ahub-card" for="ahub-hist">
        <span class="ahub-ico" aria-hidden="true"><svg viewBox="0 0 24 24" width="21" height="21" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="8.5"/><path d="M12 7.2v5.1l3.4 2"/></svg></span>
        <span class="ahub-tx">
          <b>产品发展史</b>
          <i>1976–2026，十条产品线一路怎么走过来的</i>
          <em>293 条里程碑 · 10 条产品线</em>
        </span>
        <span class="ahub-go">看历史 →</span>
      </label>
    </div>
    <div class="ahub-halves">
      <div class="ahub-half" id="tab-now" data-half="now">
"""

SWITCH_CLOSE_AND_HIST = """      </div>

      <div class="ahub-half" id="tab-hist" data-half="hist">
        <!-- AHUB:HIST:START 由 scripts/build_apple_history.py 生成，请勿手改 -->
        <!-- AHUB:HIST:END -->
      </div>
    </div>
  </div>

"""

AHUB_CSS = """
<style id="ahub-css">
/* ===== 板块分区切换（在售新品 / 产品发展史） =====
   深色/浅色两套强调色：在售新品=金（沿用品牌金，与新品半区自己的强调色一致）
   产品发展史=青蓝（与历史半区自己的强调色一致）→ 颜色本身就是「识别码」。
   显隐全部由 .ahub-on 前缀门控：脚本没跑起来时两半都显示，内容一张不丢。 */
.ahub{margin:20px 0 4px}
.ahub-r{position:absolute;width:1px;height:1px;opacity:0;pointer-events:none;margin:0}
.ahub-cards{display:grid;grid-template-columns:repeat(2,1fr);gap:14px}
.ahub-card{position:relative;display:grid;grid-template-columns:auto 1fr auto;grid-template-areas:"ico tx go";align-items:center;gap:12px;cursor:pointer;padding:15px 17px;border:1px solid var(--border);border-left:3px solid var(--c);border-radius:14px;background:var(--bg-secondary);transition:background .18s,border-color .18s,transform .18s}
.ahub-card[for="ahub-now"]{--c:#c9a84c;--cf:#c9a84c}
.ahub-card[for="ahub-hist"]{--c:#5ac8fa;--cf:#5ac8fa}
[data-theme="light"] .ahub-card[for="ahub-now"]{--c:#a68a3c;--cf:#a68a3c}
[data-theme="light"] .ahub-card[for="ahub-hist"]{--c:#0a84c8;--cf:#3d9fd0}
.ahub-card:hover{border-color:var(--c);transform:translateY(-2px)}
.ahub-ico{grid-area:ico;display:flex;align-items:center;justify-content:center;width:40px;height:40px;border-radius:11px;background:var(--card);border:1px solid var(--border);color:var(--c)}
.ahub-tx{grid-area:tx;min-width:0}
.ahub-tx b{display:block;font-size:1.02rem;font-weight:800;color:var(--text);line-height:1.35}
.ahub-tx i{display:block;font-style:normal;font-size:.78rem;color:var(--text-secondary);line-height:1.55;margin-top:3px}
.ahub-tx em{display:block;font-style:normal;font-size:.72rem;font-weight:700;color:var(--text-muted);margin-top:6px;font-variant-numeric:tabular-nums}
.ahub-go{grid-area:go;font-size:.74rem;font-weight:800;color:var(--text-muted);white-space:nowrap;align-self:end}
/* 选中态：实心填充 + 深色字（金 #a68a3c / 青 #3d9fd0 与 #1a1408 对比度均 ≥5.5:1） */
.ahub-on #ahub-now:checked~.ahub-cards label[for="ahub-now"],
.ahub-on #ahub-hist:checked~.ahub-cards label[for="ahub-hist"]{background:var(--cf);border-color:var(--cf);transform:none}
.ahub-on #ahub-now:checked~.ahub-cards label[for="ahub-now"] b,
.ahub-on #ahub-now:checked~.ahub-cards label[for="ahub-now"] i,
.ahub-on #ahub-now:checked~.ahub-cards label[for="ahub-now"] em,
.ahub-on #ahub-now:checked~.ahub-cards label[for="ahub-now"] .ahub-go,
.ahub-on #ahub-now:checked~.ahub-cards label[for="ahub-now"] .ahub-ico,
.ahub-on #ahub-hist:checked~.ahub-cards label[for="ahub-hist"] b,
.ahub-on #ahub-hist:checked~.ahub-cards label[for="ahub-hist"] i,
.ahub-on #ahub-hist:checked~.ahub-cards label[for="ahub-hist"] em,
.ahub-on #ahub-hist:checked~.ahub-cards label[for="ahub-hist"] .ahub-go,
.ahub-on #ahub-hist:checked~.ahub-cards label[for="ahub-hist"] .ahub-ico{color:#1a1408}
.ahub-on #ahub-now:checked~.ahub-cards label[for="ahub-now"] .ahub-ico,
.ahub-on #ahub-hist:checked~.ahub-cards label[for="ahub-hist"] .ahub-ico{background:rgba(0,0,0,.12);border-color:transparent}
.ahub-on #ahub-now:checked~.ahub-cards label[for="ahub-now"] .ahub-go::after{content:"（当前）"}
.ahub-on #ahub-hist:checked~.ahub-cards label[for="ahub-hist"] .ahub-go::after{content:"（当前）"}
.ahub-half{display:block}
.ahub-on #ahub-hist:checked~.ahub-halves>[data-half="now"]{display:none}
.ahub-on #ahub-now:checked~.ahub-halves>[data-half="hist"]{display:none}
@media(max-width:640px){.ahub-cards{grid-template-columns:1fr;gap:10px}.ahub-card{padding:12px 14px;gap:10px}.ahub-ico{width:36px;height:36px}}
@media print{.ahub-cards{display:none!important}.ahub-half{display:block!important}}
</style>
"""


def main() -> int:
    src = open(PAGE, encoding="utf-8").read()
    orig = src
    report = []

    def must(cond, msg):
        if not cond:
            print("✗ 断言失败：%s" % msg)
            sys.exit(1)

    # 幂等护栏：已经改造过就不要再动
    must("AHUB:HIST:START" not in src, "本页已是合并后的结构，无需重复 bootstrap")

    # ---- 1. body ----
    must(src.count("<body>") == 1, "未找到唯一的 <body>")
    src = src.replace("<body>", '<body data-no-secnav="true">', 1)
    report.append("body 加 data-no-secnav")

    # ---- 2. head 元信息 ----
    src, n = re.subn(r'<title>[^<]*</title>', '<title>%s</title>' % TITLE, src, count=1)
    must(n == 1, "标题替换失败")
    src, n = re.subn(r'<meta name="keywords" content="[^"]*">',
                     '<meta name="keywords" content="%s">' % KEYWORDS, src, count=1)
    must(n == 1, "keywords 替换失败")
    src, n = re.subn(r'<meta name="description" content="[^"]*">',
                     '<meta name="description" content="%s">' % DESC, src, count=1)
    must(n == 1, "description 替换失败")
    src, n = re.subn(r'<meta name="article-tags" content="[^"]*">',
                     '<meta name="article-tags" content="%s">' % TAGS, src, count=1)
    must(n == 1, "article-tags 替换失败")
    report.append("head 元信息改写（标题/关键词/描述/文章标签）")

    # ---- 3. hero 重写（含删掉旧的 apple-history 宣传条） ----
    hi = src.find('  <!-- ===== Hero（精简） ===== -->')
    must(hi > 0, "未找到旧 hero 注释")
    hj = src.find("  <!-- ===== 分栏导航", hi)
    must(hj > hi, "未找到分栏导航锚点")
    assert "ap-hist-link" in src[hi:hj], "旧 hero 里应含 ap-history 宣传条"
    src = src[:hi] + HERO + "\n" + src[hj:]
    report.append("hero 重写 + 删除指向 apple-history.html 的旧宣传条")

    # ---- 4. 样式块 ----
    si = src.find("/* ===== 苹果新品板块专属样式 ===== */")
    must(si > 0, "未找到苹果新品专属样式块")
    sj = src.find("</style>", si) + len("</style>")
    src = src[:sj] + "\n" + AHUB_CSS + '<style id="ah-css"></style>\n' + src[sj:]
    report.append("追加 #ahub-css（分区切换）与 #ah-css（发展史）样式块")

    # ---- 5. 包裹 NOW 半区 + 追加 HIST 半区 ----
    ai = src.find("  <!-- ===== 分栏导航")
    must(ai > 0, "未找到分栏导航起点")
    bi = src.find("  <!-- 底部链接 -->", ai)
    must(bi > ai, "未找到底部链接锚点")
    seg = src[ai:bi]
    d_open = len(re.findall(r"<div\b", seg))
    d_close = seg.count("</div>")
    must(d_open == d_close, "NOW 区段 <div> 不配平（%d/%d）" % (d_open, d_close))
    must(seg.count('class="ap-panel') == 4, "NOW 区段应含 4 个面板")
    src = src[:ai] + SWITCH_OPEN + seg + SWITCH_CLOSE_AND_HIST + src[bi:]
    report.append("包裹 NOW 半区（4 面板，%d 字节）+ 追加 HIST 半区哨兵" % len(seg))

    must(src != orig, "没有任何改动")
    open(PAGE, "w", encoding="utf-8").write(src)

    print("✓ 已改造 %s" % os.path.relpath(PAGE, ROOT))
    for r in report:
        print("   ·", r)
    print("   文件大小 %.1f KB" % (len(src.encode("utf-8")) / 1024))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
