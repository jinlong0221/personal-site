#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
guard_nav_sync.py — 全站导航一致性守卫（2026-10-25 新增，A22）。

背景（龙兄报障「顶部菜单键有缺失」后的根治）：
  static/*.html 不走 Hugo 模板，导航靠 sync_navbar.py 从 partial 同步。
  历史上出过三类漂移：① 104 个静态页下拉缺「AI 提示词库」；② changelog.html
  缺「本地生活」8 入口；③ herbs/ai-prompts 整页旧版导航且抽屉含重复项
  （中药材×2、台风监测×2）。根因是导航定义双轨（partial 手改 + 脚本硬编码），
  已重构为 partial 单一数据源，本守卫防复发。

检查项（任一不过即 FAIL）：
  1. 全站静态页导航与 partial 模板一致（跑 sync_navbar --check 逻辑，不允许有待同步页）
  2. partial 下拉 ⊆ 抽屉（付费内容/AI 提示词库这类入口不能只在下拉有）
  3. 菜单链接全部有对应页面文件（rss.xml 等非 .html 目标按实际存在性校验）
  4. 顶栏直达项非空且含「更多」按钮（结构完整性）

用法： python3 scripts/guard_nav_sync.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sync_navbar as sn  # noqa: E402

ROOT = sn.ROOT
STATIC_DIR = sn.STATIC_DIR


# Hugo 生成物（无静态源文件，默认输出开启即存在）
GENERATED = {"rss.xml"}


def page_exists(slug):
    """菜单 slug → 存在性。依次查：static 直置 / Hugo 布局 / Hugo 内容 / 构建产物。"""
    if slug in GENERATED:
        return True
    if os.path.exists(os.path.join(STATIC_DIR, slug)):
        return True
    name = slug.rsplit("/", 1)[-1]
    stem = name.rsplit(".", 1)[0]
    if os.path.exists(os.path.join(ROOT, "layouts", stem + ".html")):
        return True
    for cand in (stem + ".md", stem + "-index.md"):
        if os.path.exists(os.path.join(ROOT, "content", cand)):
            return True
    if os.path.isdir(os.path.join(ROOT, "content", stem)):
        return True
    return os.path.exists(os.path.join(ROOT, "public", slug))


def main():
    fails = []

    # 1) 全站静态页与模板一致
    drift = []
    for p, base in sn.iter_targets():
        res = sn.process_file(p, check_only=True, base_dir=base)
        if res.startswith("updated"):
            drift.append((os.path.relpath(p, ROOT), res))
    if drift:
        fails.append(f"{len(drift)} 个页面导航与 partial 模板不一致（跑 scripts/sync_navbar.py 同步）")
        for name, res in drift[:8]:
            fails.append(f"    - {name}: {res}")

    desktop, dropdown, drawer = sn.parse_partial()

    # 2) 下拉 ⊆ 抽屉
    dd_slugs = [it[1] for it in dropdown if it[0] == "link"]
    mn_slugs = [it[1] for it in drawer if it[0] == "link"]
    only_dd = [s for s in dd_slugs if s not in mn_slugs]
    if only_dd:
        fails.append(f"partial 下拉有、抽屉缺的入口: {only_dd}")

    # 3) 菜单链接目标存在
    all_slugs = {s for s, _ in desktop} | set(dd_slugs) | set(mn_slugs)
    dead = sorted(s for s in all_slugs if not page_exists(s))
    if dead:
        fails.append(f"菜单链接指向不存在的页面: {dead}")

    # 4) 结构完整：顶栏直达 + 更多按钮
    if not desktop:
        fails.append("partial 顶栏直达项为空")
    tpl = sn._read_tpl()
    if 'class="nav-more-btn"' not in tpl:
        fails.append("partial 缺少「更多」按钮")

    if fails:
        print("[guard_nav_sync] FAIL")
        for f in fails:
            print("  ✗", f)
        return 1
    print(
        f"[guard_nav_sync] PASS | 顶栏 {len(desktop)} 项 / 下拉 {len(dd_slugs)} 项 / "
        f"抽屉 {len(mn_slugs)} 项 / 全站静态页与模板一致 / 无死链"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
