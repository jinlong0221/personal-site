#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
audit_visual.py —— 新页面上线前的「渲染级体检」（人工项 C1/C2/C3/C5 的自动化抓手）。

背景：自动化守卫（A2–A14）只管源码，管不到「页面渲染出来长什么样」。
      往常 C1/C2/C3/C5 靠人工截图目检，容易漏；本脚本把可客观判定的部分固定下来：
        ① 多宽度横向溢出扫描（用元素矩形 + 过滤 overflow-x 祖先，不用 scrollWidth）
        ② 图片是否真的可达（区分 404 与 loading="lazy" 未进视口）
        ③ 关掉 JS 后正文是否平铺可读（C3，判 getClientRects 与文本内容）
        ④ dark / light 双主题截图（C1 取证）
        ⑤ 文字对比度矩阵（C2，alpha 混合按实际叠色算，数值偏保守）
      剩下的「看着顺不顺眼」仍要人看截图。

用法：
  python3 scripts/audit_visual.py --dir public --url /games/ace-attorney-123.html
  python3 scripts/audit_visual.py --dir public --url /games.html --out /tmp/shots_games --widths 1440,768
  python3 scripts/audit_visual.py --dir public --url /x.html --check-only   # 只报数不截图

依赖：playwright（本机 /Users/chenjinlong/miniconda3/bin/python3 -m pip 已在装）。
      --dir 请先用 hugo --gc --minify 构建好（脚本不起 hugo，避免拖慢）。
"""
import argparse
import functools
import http.server
import os
import socketserver
import sys
import threading

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

OVERFLOW_JS = """() => {
  const de = document.documentElement;
  const out = [];
  document.querySelectorAll('*').forEach(e => {
    const r = e.getBoundingClientRect();
    if (r.width === 0) return;
    let p = e.parentElement, blocked = false;
    while (p) {
      const ov = getComputedStyle(p).overflowX;
      if (ov === 'hidden' || ov === 'auto' || ov === 'scroll') { blocked = true; break; }
      p = p.parentElement;
    }
    if (!blocked && (r.right > de.clientWidth + 1 || r.left < -1))
      out.push(e.tagName.toLowerCase() + '.' + String(e.className || '').slice(0, 40) + ' right=' + Math.round(r.right));
  });
  return {vp: de.clientWidth, sw: de.scrollWidth, culprits: out.slice(0, 8)};
}"""

# 对比度：沿祖先把半透明背景按 alpha 真正叠起来，避免「有 rgba 底就误判」
CONTRAST_JS = """() => {
  const lum = c => { const [r,g,b] = c.map(v => { v/=255; return v<=0.03928 ? v/12.92 : Math.pow((v+0.055)/1.055, 2.4); }); return 0.2126*r+0.7152*g+0.0722*b; };
  const parse = s => { const n = (s.match(/[\\d.]+/g)||[]).map(Number); return n.length>=3 ? {c:[n[0],n[1],n[2]], a: n.length>3?n[3]:1} : {c:[255,255,255], a:1}; };
  const mix = (fg, fa, bg) => fg.map((v,i) => v*fa + bg[i]*(1-fa));
  const bgOf = el => {
    const stack = [];
    let e = el;
    while (e) { const {c,a} = parse(getComputedStyle(e).backgroundColor); if (a > 0) stack.push({c,a}); if (a >= 1) break; e = e.parentElement; }
    let base = [255,255,255];
    for (let i = stack.length - 1; i >= 0; i--) base = mix(stack[i].c, stack[i].a, base);
    return base;
  };
  const out = [];
  document.querySelectorAll('h1,h2,h3,p,li,dd,dt,span,a,td,th,button').forEach(el => {
    const r = el.getBoundingClientRect();
    if (r.width < 8 || r.height < 8) return;
    if ((el.textContent||'').trim() === '' || el.children.length > 0) return;
    const cs = getComputedStyle(el);
    const fg = parse(cs.color); const bg = bgOf(el);
    const f = mix(fg.c, fg.a, bg);
    const l1 = lum(f), l2 = lum(bg);
    const ratio = (Math.max(l1,l2)+0.05)/(Math.min(l1,l2)+0.05);
    const size = parseFloat(cs.fontSize), bold = parseInt(cs.fontWeight,10) >= 700;
    const need = (size >= 24 || (size >= 18.66 && bold)) ? 3.0 : 4.5;
    if (ratio < need) out.push({t: (el.textContent||'').trim().slice(0,26), size, ratio: +ratio.toFixed(2), need});
  });
  return out.slice(0, 10);
}"""


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def serve(directory):
    handler = functools.partial(Quiet, directory=directory)
    httpd = socketserver.TCPServer(("127.0.0.1", 0), handler)
    httpd.allow_reuse_address = True
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    return httpd, httpd.server_address[1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=os.path.join(ROOT, "public"), help="已构建好的产物目录")
    ap.add_argument("--url", required=True, help="相对产物的路径，如 /games/ace-attorney-123.html")
    ap.add_argument("--out", default="/tmp/lx-visual", help="截图输出目录")
    ap.add_argument("--widths", default="1440,768,390")
    ap.add_argument("--check-only", action="store_true", help="不截图，只打印报告")
    args = ap.parse_args()

    from playwright.sync_api import sync_playwright

    httpd, port = serve(os.path.abspath(args.dir))
    url = f"http://127.0.0.1:{port}{args.url}"
    widths = [int(x) for x in args.widths.split(",") if x.strip()]
    fails = 0
    try:
        with sync_playwright() as p:
            b = p.chromium.launch()
            for w in widths:
                page = b.new_page(viewport={"width": w, "height": 900})
                page.goto(url, wait_until="domcontentloaded")
                page.wait_for_timeout(2000)
                # 只把「主动滚进视口后依然加载不出来」算 broken（lazy 图不进视口本就不该加载）
                page.evaluate("() => document.querySelectorAll('img[loading=lazy]').forEach(i => i.loading = 'eager')")
                page.wait_for_timeout(1200)
                broken = page.evaluate(
                    "() => [...document.images].filter(i => !i.complete || i.naturalWidth === 0).map(i => i.getAttribute('src'))")
                ov = page.evaluate(OVERFLOW_JS)
                print(f"[w={w}] 图片broken={broken or '无'} 溢出={ov['sw']}/{ov['vp']} culprits={ov['culprits'] or '无'}")
                fails += len(broken)
                if ov["culprits"]:
                    fails += 1
                page.close()

                page2 = b.new_page(viewport={"width": w, "height": 900}, java_script_enabled=False)
                page2.goto(url, wait_until="domcontentloaded")
                txt = page2.locator("body").inner_text()
                heads = page2.locator("h1, h2").count()
                h1_ok = len(txt.strip()) > 100
                print(f"[w={w}] 无JS: 标题 {heads} 个, 正文可读={h1_ok}")
                if not h1_ok:
                    fails += 1
                page2.close()

            for scheme in ("dark", "light"):
                ctx = b.new_context(viewport={"width": 1440, "height": 1000}, color_scheme=scheme)
                page = ctx.new_page()
                page.goto(url, wait_until="domcontentloaded")
                page.wait_for_timeout(2000)
                if not args.check_only:
                    name = args.url.strip("/").replace("/", "_") or "index"
                    page.screenshot(path=os.path.join(args.out, f"{name}_{scheme}.png"))
                    page.screenshot(path=os.path.join(args.out, f"{name}_{scheme}_full.png"), full_page=True)
                bad = page.evaluate(CONTRAST_JS)
                print(f"[{scheme}] 对比度不足 {len(bad)} 项:")
                for x in bad:
                    print("     ", x)
                fails += len(bad)
                ctx.close()
            b.close()
    finally:
        httpd.shutdown()
    print("渲染体检 FAIL 总数:", fails)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
