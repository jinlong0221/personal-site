#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
audit_duo_viewports.py — iPhone Duo（苹果首款折叠屏，2026-10-23 发售）三视口渲染审计

设备事实（Apple 官方技术规格 support.apple.com/zh-cn/148588）：
  - 折叠态外屏 5.4"：1398×2034@460ppi → 约 466×678 CSS px（≤480 移动档）
  - 展开态内屏 7.6"：1878×2670@430ppi → 约 626×890 CSS px（竖屏）/ 890×626（横屏）
  - 双屏同比例、均带灵动岛；iOS 27；折叠/展开切换由 CSS 媒体查询天然响应

审计内容（每个 页面×视口 组合）：
  ① 页面级横向滚动：document.scrollWidth > clientWidth 即 FAIL
     （龙兄硬规矩：移动端绝不允许页面级横向滚动；容器内横滑如轮播/筛选条属设计使然，放行）
  ② 元素越界：getBoundingClientRect().right > clientWidth 且不在任何横向滚动容器内 → 记录
  ③ 退出码：任一页面级横向滚动 → 1；仅元素越界 → 0 但打印明细（越界多半是滚动容器漏判）

用法：
  # 需要 playwright（本机专用环境）：
  ~/.workbuddy/binaries/python/envs/playwright/bin/python3 scripts/audit_duo_viewports.py
  # 可选参数：
  --pages index.html,games.html     只测指定页（逗号分隔，默认内置代表页清单）
  --shots /tmp/dir                  额外存三视口截图（深色主题）
  --skip-build                      跳过 hugo 构建（复用已有 /tmp/duo-public）

为什么要本地 baseURL 单独构建（2026-10-25 踩坑记录）：
  页面 CSP 是 default-src 'self'，而 Hugo 产物里的 css/js 用的是 https://longxiong.vip 绝对地址；
  在 127.0.0.1 上打开时外域资源被 CSP 拦掉，页面只剩内联 critical-css，
  量出来的 computed style 全是假的（曾误判导航下拉菜单常开）。所以必须先
  hugo --baseURL http://127.0.0.1:PORT/ --destination /tmp/duo-public 再测。
  另外：后台自动化（二米等）会用生产 baseURL 反复重建 public/，别把测试构建放进 public/。
"""
import argparse
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_PAGES = [
    "index.html", "changelog.html", "games.html", "marvel.html", "tesla.html",
    "console.html", "zisha.html", "bracelet.html", "herbs.html", "gaokao.html",
    "sheyang.html", "calendar.html", "about.html", "health-tea.html",
    "xintan-weather.html", "global.html", "apple.html", "guanghui.html",
    "tools.html", "typhoon.html",
]
VIEWPORTS = [
    ("duo-折叠外屏-竖", 466, 678),
    ("duo-展开内屏-竖", 626, 890),
    ("duo-展开内屏-横", 890, 626),
    ("duo-展开外屏-横", 678, 466),   # 外屏横持（少见但存在）
    ("参照-主流手机", 390, 844),
    ("参照-桌面", 1280, 800),
]

JS = r"""
() => {
  const vw = document.documentElement.clientWidth;
  const out = {pageScroll: 0, docW: document.documentElement.scrollWidth, cliW: vw, offenders: [], sheetErr: ''};
  // 外链样式表加载自检：至少 2 个 sheet（内联 critical-css + 外链 style.css），
  // 且外链那个能读到 cssRules（跨域被 CSP 拦时会抛 SecurityError）
  try {
    const ext = [...document.styleSheets].find(s => s.href && s.href.includes('/css/style.css'));
    if (!ext) out.sheetErr = 'no-external-sheet';
    else ext.cssRules;
  } catch (e) { out.sheetErr = e.name; }
  if (document.documentElement.scrollWidth > vw + 1) out.pageScroll = 1;
  const inScroller = (el) => {
    let n = el.parentElement;
    while (n && n !== document.body) {
      const s = getComputedStyle(n);
      if ((s.overflowX === 'auto' || s.overflowX === 'scroll') && n.scrollWidth > n.clientWidth + 1) return true;
      n = n.parentElement;
    }
    return false;
  };
  const seen = new Set();
  for (const el of document.querySelectorAll('body *')) {
    const r = el.getBoundingClientRect();
    if (r.width === 0 || r.height === 0) continue;
    if (r.right > vw + 1 || r.left < -1) {
      const cls = typeof el.className === 'string' ? el.className : '';
      const key = el.tagName + '|' + cls;
      if (seen.has(key)) continue;
      seen.add(key);
      if (inScroller(el)) continue;
      out.offenders.push({tag: el.tagName, cls: cls.slice(0, 60),
                          right: Math.round(r.right), w: Math.round(r.width),
                          text: (el.textContent || '').trim().slice(0, 40)});
    }
    if (out.offenders.length > 10) break;
  }
  return out;
}
"""


def free_port(preferred=8973):
    """默认用固定端口 8973：ad-hoc 验证脚本都认这个口，重建后引用不会错位。
    被占用就先杀掉占用者（只可能是本脚本自己起的 stale http.server）。"""
    s = socket.socket()
    try:
        s.bind(("127.0.0.1", preferred))
        s.close()
        return preferred
    except OSError:
        s.close()
        out = subprocess.run(["lsof", "-ti", f"tcp:{preferred}"], capture_output=True, text=True).stdout.split()
        for pid in out:
            try:
                subprocess.run(["kill", pid], capture_output=True)
            except Exception:
                pass
        import time
        time.sleep(0.5)
        s2 = socket.socket()
        try:
            s2.bind(("127.0.0.1", preferred))
            s2.close()
            return preferred
        except OSError:
            s2.close()
            s3 = socket.socket()
            s3.bind(("127.0.0.1", 0))
            p = s3.getsockname()[1]
            s3.close()
            print(f"! 8973 仍被占用，改用随机端口 {p}（注意：ad-hoc 验证脚本需同步改端口）")
            return p


def build(port):
    dest = "/tmp/duo-public"
    if os.path.isdir(dest):
        shutil.rmtree(dest)
    cmd = ["hugo", "--minify", "--baseURL", f"http://127.0.0.1:{port}/", "--destination", dest]
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stdout[-2000:], r.stderr[-2000:])
        raise SystemExit("hugo 构建失败")
    return dest


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", default="")
    ap.add_argument("--shots", default="")
    ap.add_argument("--skip-build", action="store_true")
    ap.add_argument("--port", type=int, default=8973)
    args = ap.parse_args()
    pages = args.pages.split(",") if args.pages else DEFAULT_PAGES
    port = args.port if args.skip_build else free_port(args.port)
    if not args.skip_build:
        build(port)
    if not os.path.isfile("/tmp/duo-public/index.html"):
        raise SystemExit("/tmp/duo-public 不存在，请先构建或去掉 --skip-build")

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        raise SystemExit("缺少 playwright：用 ~/.workbuddy/binaries/python/envs/playwright/bin/python3 运行")

    print(f"测试服务：http://127.0.0.1:{port}/（构建目录 /tmp/duo-public，baseURL 同端口）")

    # 起本地静态服务（后台子进程，跑完即杀）
    srv = subprocess.Popen(
        [sys.executable, "-m", "http.server", str(port), "--bind", "127.0.0.1"],
        cwd="/tmp/duo-public", stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    import time
    for _ in range(50):
        try:
            import urllib.request
            urllib.request.urlopen(f"http://127.0.0.1:{port}/index.html", timeout=1)
            break
        except Exception:
            time.sleep(0.2)

    fails, total = [], 0
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            for vname, w, h in VIEWPORTS:
                ctx = browser.new_context(viewport={"width": w, "height": h}, color_scheme="dark")
                page = ctx.new_page()
                for pg in pages:
                    total += 1
                    try:
                        page.goto(f"http://127.0.0.1:{port}/{pg}", wait_until="domcontentloaded")
                        page.wait_for_timeout(1600)
                        r = page.evaluate(JS)
                    except Exception as e:
                        print(f"[{vname}] {pg:22s} ERROR {str(e)[:70]}")
                        fails.append((vname, pg, "load-error"))
                        continue
                    flag = "横向滚动!" if r["pageScroll"] else "ok"
                    # 自检：外链样式表必须真加载（CSP default-src 'self' 下，指向生产域名的
                    # 绝对地址在 127.0.0.1 上会被静默拦掉，页面只剩 critical-css，
                    # 量出来的 computed style 全是假的——2026-10-25 实测踩坑）
                    if r["sheetErr"]:
                        print(f"[{vname}] {pg:22s} !! 外链样式表未加载（{r['sheetErr']}）——"
                              f"端口/构建不一致，结果无效", file=sys.stderr)
                        fails.append((vname, pg, "css-not-loaded"))
                        continue
                    print(f"[{vname}] {pg:22s} docW={r['docW']:5d} vw={r['cliW']:4d} {flag} 越界={len(r['offenders'])}")
                    if r["pageScroll"]:
                        fails.append((vname, pg, "page-scroll"))
                    for o in r["offenders"][:4]:
                        print(f"    → <{o['tag']}> .{o['cls']} right={o['right']} «{o['text']}»")
                    if args.shots and vname.startswith("duo"):
                        os.makedirs(args.shots, exist_ok=True)
                        page.screenshot(path=os.path.join(args.shots, f"{vname}_{pg.replace('.html','')}.png"))
                ctx.close()
            browser.close()
    finally:
        srv.terminate()

    print("=" * 64)
    if fails:
        print(f"结果：FAIL {len(fails)} / {total}")
        for f in fails:
            print("  ", f)
        sys.exit(1)
    print(f"结果：PASS {total} / {total}（三种 Duo 视口 + 外屏横持 + 两个参照，全部零页面级横向滚动）")


if __name__ == "__main__":
    main()
