#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sync_update_time.py — 用 git 真实提交日期自动同步页面的「最后更新时间」

## 背景

站点的 .update-time 字段原本是手工硬编码的，没有任何机制保证它与实际内容
同步。结果是：文玩手串 9 个详情页停留在 2026-07-07，而 git 记录的真实提交
日期是 2026-08-29——脱节 54 天。读者会误以为内容陈旧，但这些页面几乎每天
都有新闻数据注入。

同类脱节也出现在 health-tea(页面 08-19 / git 08-29)、zisha(08-17 / 08-29)。

## 解法

用 `git log -1 --format=%cd --date=short -- <file>` 取每个文件的真实最后提交
日期自动回填。CI 已配置 fetch-depth: 0，git 历史完整可用。

同步两处：
  1. 页面里的 <div class="update-time">最后更新时间：YYYY-MM-DD</div>
  2. static/data/updates.json 各板块的 lastUpdate（驱动首页"最新板块"展示）

## 用法
    python3 scripts/sync_update_time.py            # 写入
    python3 scripts/sync_update_time.py --check    # 只打印会改什么，不写文件
"""
import glob
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC = os.path.join(ROOT, "static")
UPDATES_JSON = os.path.join(STATIC, "data", "updates.json")

# JS 模板占位（如 sheyang.html 的「更新于 ${ts}」）运行时填充，跳过
JS_PLACEHOLDER = re.compile(r"\$\{|\{\{")

UPDATE_TIME_RE = re.compile(
    r'(<div class="update-time">[^<]*?)(\d{4}-\d{2}-\d{2})([^<]*</div>)'
)


def git_date(rel_path):
    """取文件最后一次提交的日期（YYYY-MM-DD）。"""
    try:
        out = subprocess.run(
            ["git", "log", "-1", "--format=%cd", "--date=short", "--", rel_path],
            cwd=ROOT, capture_output=True, text=True, timeout=30,
        )
        d = (out.stdout or "").strip()
        return d if re.fullmatch(r"\d{4}-\d{2}-\d{2}", d) else ""
    except Exception:
        return ""


def sync_pages(check_only):
    changed = []
    for path in sorted(glob.glob(os.path.join(STATIC, "**", "*.html"),
                                 recursive=True)):
        rel = os.path.relpath(path, ROOT)
        try:
            html = open(path, encoding="utf-8").read()
        except Exception:
            continue
        if 'class="update-time"' not in html:
            continue
        m = UPDATE_TIME_RE.search(html)
        if not m:
            continue
        if JS_PLACEHOLDER.search(m.group(0)):
            continue  # JS 动态填充，不要动
        real = git_date(rel)
        if not real or real == m.group(2):
            continue
        new_html = html[: m.start(2)] + real + html[m.end(2):]
        changed.append((rel, m.group(2), real))
        if not check_only:
            open(path, "w", encoding="utf-8").write(new_html)
    return changed


def sync_updates_json(check_only):
    """用板块落地页的真实 git 日期，刷新 data/updates.json 的 lastUpdate。"""
    if not os.path.exists(UPDATES_JSON):
        return []
    data = json.load(open(UPDATES_JSON, encoding="utf-8"))
    changed = []
    for key, val in data.items():
        if not isinstance(val, dict):
            continue
        url = val.get("url") or ""
        if not url or JS_PLACEHOLDER.search(url):
            continue
        page = os.path.join("static", url)
        if not os.path.exists(os.path.join(ROOT, page)):
            continue
        real = git_date(page)
        if not real or real == val.get("lastUpdate"):
            continue
        changed.append((key, val.get("lastUpdate", ""), real))
        val["lastUpdate"] = real
    if changed and not check_only:
        json.dump(data, open(UPDATES_JSON, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=2)
    return changed


def news_updated_for(page_path):
    """取页面对应板块新闻数据的 updated 字段。

    规律：bracelet.html -> bracelet-news.json，zisha.html -> zisha-news.json
    """
    base = os.path.basename(page_path)[:-5]  # 去 .html
    for cand in (os.path.join(STATIC, base + "-news.json"),):
        if os.path.exists(cand):
            try:
                d = json.load(open(cand, encoding="utf-8"))
                u = d.get("updated", "")
                return u if re.fullmatch(r"\d{4}-\d{2}-\d{2}", u or "") else ""
            except Exception:
                return ""
    return ""


def changelog_latest():
    """取 changelog 最新日期。"""
    best = ""
    for p in (os.path.join(STATIC, "changelog.json"),
              os.path.join(STATIC, "data", "changelog.json")):
        if not os.path.exists(p):
            continue
        try:
            d = json.load(open(p, encoding="utf-8"))
            items = d if isinstance(d, list) else d.get("items", d.get("changelog", []))
            for x in items:
                if isinstance(x, dict):
                    v = x.get("date", "")
                    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", v or "") and v > best:
                        best = v
        except Exception:
            pass
    return best


# JS 运行时会用新闻 updated 覆盖这些 span，但源码里的兜底值（爬虫/JS 失败时可见）会陈旧
SPAN_RE = re.compile(
    r'(<div class="update-time">[^<]*<span id="(?:lastNewsUpdate|changelogUpdated)">)'
    r"(\d{4}-\d{2}-\d{2})(</span>[^<]*</div>)"
)


def sync_dynamic_spans(check_only):
    """同步 JS 动态填充的 span 的静态兜底值，让源码与运行时一致。"""
    changed = []
    for path in sorted(glob.glob(os.path.join(STATIC, "**", "*.html"),
                                 recursive=True)):
        rel = os.path.relpath(path, ROOT)
        try:
            html = open(path, encoding="utf-8").read()
        except Exception:
            continue
        m = SPAN_RE.search(html)
        if not m or JS_PLACEHOLDER.search(m.group(0)):
            continue
        if "changelogUpdated" in m.group(1):
            real = changelog_latest()
        else:
            real = news_updated_for(path)
        if not real or real == m.group(2):
            continue
        new_html = html[: m.start(2)] + real + html[m.end(2):]
        changed.append((rel, m.group(2), real))
        if not check_only:
            open(path, "w", encoding="utf-8").write(new_html)
    return changed


def main():
    check_only = "--check" in sys.argv
    pages = sync_pages(check_only)
    spans = sync_dynamic_spans(check_only)
    jsons = sync_updates_json(check_only)
    tag = "[check] " if check_only else "[done] "
    print(f"{tag}页面 .update-time 同步: {len(pages)} 处")
    for rel, old, new in pages[:25]:
        print(f"   {rel}   {old} -> {new}")
    print(f"{tag}动态 span 兜底值同步: {len(spans)} 处")
    for rel, old, new in spans[:25]:
        print(f"   {rel}   {old} -> {new}")
    print(f"{tag}data/updates.json lastUpdate 同步: {len(jsons)} 处")
    for key, old, new in jsons[:25]:
        print(f"   {key}: {old or '(空)'} -> {new}")


if __name__ == "__main__":
    main()
