#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
bundle_js.py — 把 head.html 中那一串独立 defer 脚本合并为单个 site-bundle.js

为什么做：
- 原 head.html 在每个页面都 defer 加载 16 个本地 JS（外加 4 个空闲延迟脚本），
  冷启动 = 16+ 个 JS 请求。与"秒开站"（通常 1-3 个打包 JS）的核心差距在此。
- 合并为 1 个文件：请求数 16 → 1，显著改善薄机器 / 蜂窝网络下的首屏打开速度。

安全约束（务必遵守，避免破坏站点）：
- 严格保持 head.html 的原加载顺序（脚本间有全局依赖与执行次序约定）。
- 先整份拼接，再用 terser 压缩一次：terser 把 16 个文件当作一个程序解析，
  自动正确处理 ASI / 边界；默认不混淆顶层（全局）名字，跨文件全局引用不变。
- 找不到 terser 时退化为纯拼接（仍能减少请求数，只是不压缩）。
- 源文件保留在 scripts/js-src/（版本源），本脚本由其重新生成 static/js/site-bundle.js。
  这样既能重新生成，又不会在 public/ 留下 16 个无人引用的死文件。

用法：
  python3 scripts/bundle_js.py                 # 生成 static/js/site-bundle.js
  TERSER=/path/to/terser python3 scripts/bundle_js.py
"""
import os
import re
import sys
import shutil
import subprocess
import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(ROOT, "scripts", "js-src")
OUT = os.path.join(ROOT, "static", "js", "site-bundle.js")
HEAD = os.path.join(ROOT, "layouts", "partials", "head.html")
# 只刷新 head.html 中 site-bundle.js 自己的 ?v= 戳；其余引用（style.css / site-live /
# pwa-register）各有各的提交日，绝不动。
BUNDLE_V_RE = re.compile(r"(js/site-bundle\.js\?v=)(\d{8})")


def bump_head_v(today):
    """重新生成 bundle 时，把 head.html 里 site-bundle.js 的 ?v= 戳刷新为当天日期。

    与仓库纪律一致：源码 ?v 应等于资源最后提交日，避免将来改了源文件重新打包后
    CDN/浏览器还命中旧缓存。bump_v_hash.py 会在 hugo 构建后把 public/ 里的 ?v=YYYYMMDD
    改写成 ?v=h<内容哈希>，此处只管源码这一层。
    """
    if not os.path.exists(HEAD):
        return
    with open(HEAD, "r", encoding="utf-8") as fh:
        text = fh.read()
    new_text, n = BUNDLE_V_RE.subn(lambda m: m.group(1) + today, text)
    if n:
        with open(HEAD, "w", encoding="utf-8") as fh:
            fh.write(new_text)
        print(f"[bundle_js] 已把 head.html 中 site-bundle.js 的 ?v 刷新为 {today}（{n} 处）")

# head.html 中的原顺序（与 layouts/partials/head.html 第 269-288 行一一对应）。
# 13 个全部并入 bundle，严格保持原始执行次序（app.js 在最前、auto_news_loader.js 第 3，
# 与其余 11 个的相对顺序与改动前完全一致，避免任何全局依赖/初始化次序回归）。
# 注意：app.js / auto_news_loader.js 同时保留 static/js/ 下的独立副本——它们被
# build_chinajoy.py / build_marvel.py / build_travel.py / build_ev_sales.py 注入到
# 「生成的静态页」（这些页是提交并部署的产物、CI 不重建），故独立副本不可删。
# bookmark.js / site-live.js / pwa-register.js 由 apply_site_widgets.py / apply_pwa.py
# 注入到 static/ 静态页，保留为独立文件、不并入 bundle（guard_v_param 亦校验其存在）。
ORDER = [
    "app.js",
    "animations.js",
    "auto_news_loader.js",
    "daily-pick.js",
    "home-feed.js",
    "solar-term.js",
    "daily-item.js",
    "hero.js",
    "reveal.js",
    "status-bubble.js",
    "updates.js",
    "auto-collapse.js",
    "countdown.js",
]


def find_terser():
    env = os.environ.get("TERSER")
    if env and os.path.exists(env):
        return env
    # 常见本地位置
    cand = [
        os.path.join(ROOT, "node_modules", ".bin", "terser"),
        "/tmp/tz/node_modules/.bin/terser",
    ]
    for c in cand:
        if os.path.exists(c):
            return c
    return None


def main():
    missing = [f for f in ORDER if not os.path.exists(os.path.join(SRC_DIR, f))]
    if missing:
        print(f"[bundle_js] 错误：缺少源文件: {missing}")
        sys.exit(1)

    # 1) 按顺序拼接
    parts = []
    for f in ORDER:
        with open(os.path.join(SRC_DIR, f), "r", encoding="utf-8") as fh:
            parts.append(fh.read().rstrip("\n"))
    combined = "\n;\n".join(parts) + "\n"

    terser = find_terser()
    if terser:
        try:
            p = subprocess.run(
                [terser, "--compress", "--mangle"],
                input=combined.encode("utf-8"),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=120,
            )
            if p.returncode == 0 and p.stdout:
                out_bytes = p.stdout
                mode = "terser 压缩"
            else:
                print(f"[bundle_js] terser 失败，退化为纯拼接: {p.stderr.decode('utf-8','replace')[:300]}")
                out_bytes = combined.encode("utf-8")
                mode = "纯拼接（terser 失败）"
        except Exception as e:
            print(f"[bundle__js] terser 异常，退化为纯拼接: {e}")
            out_bytes = combined.encode("utf-8")
            mode = "纯拼接（异常）"
    else:
        out_bytes = combined.encode("utf-8")
        mode = "纯拼接（无 terser）"

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "wb") as fh:
        fh.write(out_bytes)

    today = datetime.date.today().strftime("%Y%m%d")
    bump_head_v(today)

    orig = len(combined.encode("utf-8"))
    new = len(out_bytes)
    pct = (1 - new / orig) * 100 if orig else 0
    print(f"[bundle_js] 完成（{mode}）：{len(ORDER)} 个文件 -> {os.path.relpath(OUT, ROOT)}")
    print(f"[bundle_js] 体积: {orig} -> {new} 字节（减少 {pct:.1f}%）")


if __name__ == "__main__":
    main()
