#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
guard_date_honesty.py — 板块更新日期真实性守卫

背景（2026-10-24 事故，龙兄原话「网站的每一个板块，更新日期和记录一定要真实」）：
某次自动更新提交只把 static/bracelet-news.json 的 updated 从 2026-10-21
改成 2026-10-24，**没有新增任何内容**——页面因此显示「最后更新：今天」，
属于造假。全站扫描确认仅此一例，已修正为 2026-10-21。

难点：updated 晚于最新内容日期，有两种截然不同的情况——
  A) 造假：只改日期不加内容（bracelet 事故）→ 必须拦截
  B) 真实刷新：当天新增了真实条目，但事件本身发生得更早
     （例：static/data/global.json 于 2026-10-24 录入 5 条 10-16~10-21
     的真实海外动态，页面显示「更新至 10-24」属实）→ 必须放行
两者静态特征完全相同（updated > 最新内容日期），只有 git 能区分：
本次提交是否同时改了内容。

判定逻辑：
  1) updated <= 文件内最新内容日期            → PASS（常规）
  2) updated > 最新内容日期，且本文件相对 HEAD 有改动：
       - updated 变了但内容（去掉 updated 的其余部分）没变 → FAIL（纯 bump，A 类）
       - 内容也变了                                        → PASS（真实刷新，B 类）
  3) updated > 最新内容日期，但本文件相对 HEAD 无改动（稳态）：
       → REVIEW（只提示不拦截）：历史遗留的刷新日，人工已核实过的不拦
  4) 不在 git 仓库 / git 不可用 → 退化为静态检查，upd > latest 记 REVIEW

已知稳态 REVIEW 项（已人工核实为真实刷新，勿慌）：
  - static/data/global.json：updated=刷新日，2026-10-24 当天录入 5 条真实动态

修复方式（A 类被拦时）：把 updated 改回最新真实条目的日期，或补上真实内容。

另管一件事（2026-10-25 增补）：site-live.js / layouts/index.html 里那行
「全站最近发布：X」的文案回归——它显示的是 CI 构建发布时刻，不是本页内容日期，
被改回「本站更新于」这类模糊措辞同样 FAIL（会把全站发布误导成本页刚更新）。
"""
import glob
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")
DATE_KEYS = ("date", "publishDate", "published", "time")

# updated 语义特殊的文件：changelog 的 updated 指日志更新日（guard_changelog 管），
# home-feed 用 generated 不用 updated，festivals/games 非资讯流
SKIP_FILES = {"changelog.json", "changelog-feed.json", "home-feed.json",
              "festivals.json", "games.json"}


def latest_content_date(obj):
    """递归收集所有内容日期，返回最大者（无则 None）。"""
    dates = []

    def walk(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if k in DATE_KEYS and isinstance(v, str):
                    m = DATE_RE.match(v.strip())
                    if m:
                        dates.append(m.group(1))
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)

    walk(obj)
    return max(dates) if dates else None


def strip_updated(d):
    """去掉顶层 updated，剩下的是「内容」。"""
    if isinstance(d, dict):
        return {k: v for k, v in d.items() if k != "updated"}
    return d


def git_show_head(relpath):
    """取 HEAD 版本文件内容；不在 HEAD / git 不可用返回 None。"""
    try:
        r = subprocess.run(
            ["git", "-C", ROOT, "show", f"HEAD:{relpath}"],
            capture_output=True, text=True, timeout=30)
        if r.returncode != 0:
            return None
        return json.loads(r.stdout)
    except Exception:
        return None


def check_live_wording():
    """site-live 行文案回归检查（2026-10-25 增补）。

    这行显示的是「全站每次 CI 构建的发布时刻」，不是本页内容日期。旧文案
    「本站更新于 X 分钟前」紧挨各页写死的「最后更新：旧日期」（如 ev-sales
    数据 10-19），读者必然误读成「这页刚更新过」——龙兄 2026-10-24 截图抓到。
    正判据：两处激活代码都必须含「全站最近发布」；被改回模糊措辞即 FAIL。
    注释里引述旧文案（防改回说明）不拦。
    """
    errors = []
    targets = [
        (os.path.join(ROOT, "static", "js", "site-live.js"), "全站最近发布"),
        (os.path.join(ROOT, "layouts", "index.html"), "全站最近发布"),
    ]
    for path, must in targets:
        if not os.path.exists(path):
            errors.append(f"{os.path.relpath(path, ROOT)} 不存在")
            continue
        src = open(path, encoding="utf-8").read()
        if must not in src:
            errors.append(f"{os.path.relpath(path, ROOT)} 缺少「{must}」——"
                          f"疑似被改回「本站更新于」这类模糊措辞（会把全站发布时刻"
                          f"误导成本页刚更新，2026-10-25 铁律）")
    return errors


def main():
    quiet = "-q" in sys.argv
    targets = sorted(glob.glob(os.path.join(ROOT, "static", "**", "*.json"),
                               recursive=True)) + \
        sorted(glob.glob(os.path.join(ROOT, "data", "**", "*.json"),
                         recursive=True))

    fails = []      # A 类：纯 bump 造假
    reviews = []    # 稳态刷新日 / 无法核验
    checked = 0

    for path in targets:
        base = os.path.basename(path)
        if base in SKIP_FILES:
            continue
        rel = os.path.relpath(path, ROOT)
        try:
            d = json.load(open(path, encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(d, dict):
            continue
        upd = d.get("updated")
        if not isinstance(upd, str):
            continue
        m = DATE_RE.match(upd.strip())
        if not m:
            continue
        upd_date = m.group(1)
        latest = latest_content_date(strip_updated(d))
        if latest is None:
            continue  # 无带日期内容，不判定
        checked += 1
        if upd_date <= latest:
            continue  # 常规：日期不大于内容，真实

        # upd > latest：需要 git 区分「造假 bump」与「真实刷新」
        head = git_show_head(rel)
        if head is None:
            # 新文件或 git 不可用：无法核验本次是否伴随内容变化
            reviews.append((rel, upd_date, latest, "新文件或git不可用，无法核验"))
            continue
        head_has_same_file = True
        upd_changed = head.get("updated") != d.get("updated")
        content_changed = strip_updated(head) != strip_updated(d)
        file_modified = (head != d)
        if not file_modified:
            reviews.append((rel, upd_date, latest, "稳态：相对HEAD无改动（历史刷新日）"))
        elif upd_changed and not content_changed:
            fails.append((rel, upd_date, latest))
        # 其余（内容变了/日期没动）→ 真实刷新或无新日期声明，放行

    if fails:
        print("❌ guard_date_honesty 未通过（只改更新日期不加内容＝造假）：")
        for rel, upd, latest in fails:
            print(f"   - {rel}: updated={upd} > 最新内容日期={latest}，且内容零变化")
        print("   修复：把 updated 改回最新真实条目日期；当天无新稿不准改 updated，"
              "巡检留痕写 changelog.json。")
        return 1

    wording_errors = check_live_wording()
    if wording_errors:
        print("❌ guard_date_honesty 未通过（全站发布时刻文案回归）：")
        for e in wording_errors:
            print("   -", e)
        print("   修复：恢复「全站最近发布」措辞——它显示的是 CI 构建发布时刻，")
        print("   不是本页内容日期；写成「本站更新于」会让读者误读成本页刚更新。")
        return 1

    if reviews and not quiet:
        print("[guard_date_honesty] 提示（已核实的刷新日，不拦截）：")
        for rel, upd, latest, why in reviews:
            print(f"   - {rel}: updated={upd} > 最新内容={latest}（{why}）")
    if not quiet:
        print(f"[guard_date_honesty] PASS: {checked} 个板块数据文件，"
              f"无造假日期{'' if not reviews else f'（{len(reviews)} 个已核实刷新日）'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
