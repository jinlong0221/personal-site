#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
v_param.py —— ?v=YYYYMMDD 缓存版本号的「唯一真相来源」

为什么要有它：
  站点用 ?v=YYYYMMDD 破坏浏览器缓存。版本号的正确取值 = 该资源在 git 里的
  最后改动日（与 guard_v_param.py 的软校验口径一致，跑完必然 PASS）。

  历史上这个日期被**写死**在好几个脚本里（apply_pwa.py 写死 20260826、
  build_chinajoy/build_marvel/build_travel 写死 20260901）。写死的日期必然
  过期 —— 一旦别的页面被同步到新日期，这些脚本产出的页面就会带着旧版本号，
  于是「同一资源两种 ?v」，guard_v_param.py 判 ERROR、CI 直接红。
  2026-09-02 新增 ev-sales.html 时就是这样把部署打挂的。

  所以：任何需要生成 ?v= 的地方，一律调用本模块，不要手写日期。

用法：
    from v_param import version_for
    version_for("static/css/style.css")     -> '20260901'
    version_for("static/js/pwa-register.js") -> '20260828'

取不到 git 日期时（比如资源是全新文件、还没提交）退回当天日期，
保证产出的页面与站上其它页面口径一致，不会凭空造出一个孤立版本号。
"""
import os
import subprocess
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def git_last_date(relpath):
    """资源在 git 里的最后改动日，格式 YYYYMMDD；查不到返回 None。"""
    try:
        out = subprocess.run(
            ["git", "log", "-1", "--format=%cd", "--date=format:%Y%m%d", "--", relpath],
            cwd=ROOT, capture_output=True, text=True, timeout=30,
        )
        if out.returncode == 0 and out.stdout.strip():
            return out.stdout.strip()
    except Exception:
        pass
    return None


def version_for(relpath):
    """资源的 ?v 版本号：git 最后改动日；查不到则退回当天。

    relpath 为相对仓库根的路径，如 'static/css/style.css'。
    也接受 'css/style.css'（自动补 static/ 前缀）。
    """
    rel = relpath.replace("\\", "/").lstrip("./")
    if not rel.startswith("static/") and os.path.exists(os.path.join(ROOT, "static", rel)):
        rel = "static/" + rel
    return git_last_date(rel) or datetime.now().strftime("%Y%m%d")


def css_version():
    """全站主样式表 static/css/style.css 的版本号（页面里最常用）。"""
    return version_for("static/css/style.css")


if __name__ == "__main__":
    import sys
    for p in (sys.argv[1:] or ["static/css/style.css", "static/js/pwa-register.js"]):
        print("%s -> ?v=%s" % (p, version_for(p)))
