#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
audit_mobile_layout.py — 窄屏排版体检（中文断行 / 横向溢出 / 超宽元素）。

背景（2026-08-30 游戏页表格事故）：
  模型不支持读图，无法目视截图判断排版对错。本脚本用 Playwright 在真机视口下
  做**量化**判定，把「看着别扭」变成可断言的数字。

检测三项：
  1. 按字断行 —— 用 Range.getClientRects() 数单元格渲染出的视觉行数，
     判定阈值：行数 >= 字数 * 0.75 且字数 >= 5，即几乎一字一行。
     修复前实测 32 行/32 字，修复后 7 行/32 字。
  2. 整页横向溢出 —— documentElement.scrollWidth > clientWidth。
     注意：若 body 是 overflow-x:clip，溢出不会体现为可滚动，而是**直接裁切**，
     比溢出更隐蔽也更严重，必须配合第 3 项一起看。
  3. 超宽元素 —— 宽度超过视口、且没有任何可滚动/裁剪祖先兜底的元素。
     这类元素的内容在手机上就是看不全的。

用法：
    # 体检本地最新构建产物（默认，推荐，能验到未部署的改动）
    python3 scripts/audit_mobile_layout.py

    # 体检线上
    python3 scripts/audit_mobile_layout.py --live

    # 指定目录/单页
    python3 scripts/audit_mobile_layout.py --dir public/games
    python3 scripts/audit_mobile_layout.py --url https://longxiong.vip/games/wukong.html

    # 换视口（默认 iPhone 12 390x844）
    python3 scripts/audit_mobile_layout.py --width 360 --height 780

依赖：playwright（本机装在 miniconda3：
      /Users/chenjinlong/miniconda3/bin/python3 scripts/audit_mobile_layout.py ）

退出码：0 = 全部通过；1 = 有问题页。CI 可直接接。
"""
import argparse
import asyncio
import glob
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

AUDIT_JS = r"""() => {
  const de = document.documentElement, vw = de.clientWidth;
  const res = {vw, pageOverflow: de.scrollWidth > vw + 1, scrollW: de.scrollWidth,
               bodyOverflowX: getComputedStyle(document.body).overflowX,
               tables: [], wide: []};

  // 3) 超宽元素：宽度超视口，且没有可滚动/裁剪的祖先兜底
  document.querySelectorAll('body *').forEach(el => {
    const r = el.getBoundingClientRect();
    if (r.width > vw + 1) {
      let p = el.parentElement, guarded = false;
      while (p && p.tagName !== 'HTML') {
        const ox = getComputedStyle(p).overflowX;
        if (ox === 'auto' || ox === 'scroll' || ox === 'hidden' || ox === 'clip') { guarded = true; break; }
        p = p.parentElement;
      }
      if (!guarded) res.wide.push({tag: el.tagName.toLowerCase(),
        cls: (el.className || '').toString().slice(0, 40), w: Math.round(r.width)});
    }
  });

  // 1) 按字断行：Range 数视觉行数
  document.querySelectorAll('table').forEach((t, ti) => {
    const wrap = t.closest('.table-wrapper'), cells = [];
    t.querySelectorAll('td, th').forEach(c => {
      const rg = document.createRange(); rg.selectNodeContents(c);
      const lines = [];
      Array.from(rg.getClientRects()).forEach(rc => {
        const hit = lines.find(l => Math.abs(l.y - rc.top) < 4);
        if (hit) { hit.w += rc.width; hit.n++; } else lines.push({y: rc.top, w: rc.width, n: 1});
      });
      const txt = (c.textContent || '').trim().replace(/\s+/g, ' ');
      if (txt.length > 4) cells.push({txt: txt.slice(0, 24), lines: lines.length, chars: txt.length});
    });
    cells.sort((a, b) => (b.lines / b.chars) - (a.lines / a.chars));
    res.tables.push({i: ti,
      tableW: Math.round(t.getBoundingClientRect().width),
      wrapW: wrap ? Math.round(wrap.getBoundingClientRect().width) : null,
      canScroll: wrap ? (wrap.scrollWidth > wrap.clientWidth) : null,
      worst: cells.slice(0, 2)});
  });
  return res;
}"""

CHAR_BREAK_RATIO = 0.75
MIN_CHARS = 5


def judge(r):
    """返回 (是否健康, 问题标签列表)"""
    flags = []
    if r["pageOverflow"]:
        flags.append(f"整页横向溢出({r['scrollW']}>{r['vw']})")
    break_cells = []
    for tb in r["tables"]:
        for c in tb["worst"]:
            if c["chars"] >= MIN_CHARS and c["lines"] >= c["chars"] * CHAR_BREAK_RATIO:
                break_cells.append((tb["i"], c))
    if break_cells:
        flags.append("按字断行")
    if r["wide"]:
        flags.append(f"超宽元素{len(r['wide'])}个")
    return (not flags), flags, break_cells


async def run(urls, width, height, verbose):
    from playwright.async_api import async_playwright

    bad = []
    async with async_playwright() as p:
        b = await p.chromium.launch()
        ctx = await b.new_context(viewport={"width": width, "height": height},
                                  is_mobile=True, has_touch=True)
        pg = await ctx.new_page()
        for u in urls:
            try:
                await pg.goto(u, wait_until="load", timeout=30000)
            except Exception as e:
                print(f"  ⚠️  加载失败 {u}: {e}")
                bad.append(u)
                continue
            await pg.wait_for_timeout(150)
            r = await pg.evaluate(AUDIT_JS)
            ok, flags, break_cells = judge(r)
            name = u.split("/")[-1] or u
            print(("✅ " if ok else "❌ ") + name + ("" if ok else "  " + "、".join(flags)),
                  flush=True)
            if not ok or verbose:
                for tb in r["tables"]:
                    w = tb["worst"][0] if tb["worst"] else None
                    ws = f"{w['lines']}行/{w['chars']}字" if w else "-"
                    print(f"      表#{tb['i']} 表宽={tb['tableW']} 容器={tb['wrapW']} "
                          f"可横向滑={tb['canScroll']} 最差断行={ws}")
                for ti, c in break_cells:
                    print(f"      ⚠️ 表#{ti} 按字断: {c['lines']}行/{c['chars']}字 「{c['txt']}」")
                for w in r["wide"][:5]:
                    print(f"      ⚠️ 超宽 {w['w']}px <{w['tag']} class=\"{w['cls']}\">")
            if not ok:
                bad.append(u)
        await b.close()
    return bad


def start_server(root, port=8765):
    """在后台起一个本地静态服务。

    为什么不能用 file://：站点 CSS/JS 用绝对路径（/css/style.css?v=...），
    file:// 协议下会解析成 file:///css/style.css 而加载失败，
    导致所有依赖外部样式表的规则（.table-wrapper 的横向滚动、
    .scoreline-table 的 min-width 等）在测量时"不存在"，结论完全失真。
    2026-08-30 就因此误判 gaokao.html 表格不能横向滚动。
    """
    import socket
    import subprocess
    for _ in range(10):
        with socket.socket() as s:
            if s.connect_ex(("127.0.0.1", port)) != 0:
                break
        port += 1
    proc = subprocess.Popen(
        [sys.executable, "-m", "http.server", str(port), "--bind", "127.0.0.1"],
        cwd=root, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(40):
        with socket.socket() as s:
            if s.connect_ex(("127.0.0.1", port)) == 0:
                return proc, port
        time.sleep(0.1)
    proc.terminate()
    raise RuntimeError("本地静态服务启动失败")


def collect_urls(args):
    """返回 (urls, server_proc)。server_proc 非 None 时需由调用方 terminate。"""
    if args.url:
        return [args.url], None
    if args.live:
        base = "https://longxiong.vip/"
        rel = args.dir.lstrip("/") if args.dir else "games"
        names = [os.path.basename(f)[:-5]
                 for f in sorted(glob.glob(os.path.join(ROOT, "static", rel, "*.html")))]
        ts = str(int(time.time()))
        return [f"{base}{rel}/{n}.html?ts={ts}" for n in names], None
    d = args.dir or os.path.join(ROOT, "public", "games")
    if not os.path.isabs(d):
        d = os.path.join(ROOT, d)
    d = os.path.abspath(d)
    if args.recursive:
        files = sorted(glob.glob(os.path.join(d, "**", "*.html"), recursive=True))
    else:
        files = sorted(glob.glob(os.path.join(d, "*.html")))
    if args.no_serve:
        return ["file://" + f for f in files], None
    proc, port = start_server(d)
    rels = [os.path.relpath(f, d).replace(os.sep, "/") for f in files]
    return [f"http://127.0.0.1:{port}/{r}" for r in rels], proc


def main():
    ap = argparse.ArgumentParser(description="窄屏排版体检")
    ap.add_argument("--live", action="store_true", help="体检线上站点（默认体检本地 public/）")
    ap.add_argument("--dir", help="相对目录（默认 public/games）或线上路径段（默认 games）")
    ap.add_argument("--url", help="单个页面 URL")
    ap.add_argument("--recursive", action="store_true", help="递归扫描目录下所有 HTML（全站体检）")
    ap.add_argument("--no-serve", action="store_true",
                    help="用 file:// 直开（结果不可靠：外链 CSS 加载不到，易误报）")
    ap.add_argument("--width", type=int, default=390)
    ap.add_argument("--height", type=int, default=844)
    ap.add_argument("-v", "--verbose", action="store_true", help="通过的页面也打印表格明细")
    args = ap.parse_args()

    urls, proc = collect_urls(args)
    if not urls:
        print("未找到待检页面")
        return 1
    mode = "线上" if args.live or args.url else ("本地 file://（不可靠）" if args.no_serve else "本地 HTTP 服务")
    print(f"🔍 窄屏排版体检（{mode}，视口 {args.width}x{args.height}），共 {len(urls)} 页\n")
    try:
        bad = asyncio.run(run(urls, args.width, args.height, args.verbose))
    finally:
        if proc:
            proc.terminate()
    print("\n" + "=" * 52)
    if bad:
        print(f"❌ 问题页 {len(bad)}/{len(urls)}")
        for u in bad:
            print("   -", u)
        return 1
    print(f"✅ 全部通过 {len(urls)}/{len(urls)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
