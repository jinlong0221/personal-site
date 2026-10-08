#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
板块更新时效性审计（可挂 CI / 本地定期跑）。

为什么需要它：
  全站分两类"会过时"的内容，时效判定逻辑不同，混在一起容易误报或漏报。

  [新闻板] static/*-news.json + static/tesla/fsd-news.json（+ 海外动态 static/data/global.json）
      · 取每条 date 的真实日期（兼容 MM-DD / YYYY-MM-DD，MM-DD 按【当前年】解释）。
      · 最新一条日期 = max_news；文件 updated 字段 = 自动化最后触碰时间。
      · 判定：
          - updated 距今 > STALE_UPDATED_DAYS(=3)  → ⚠️ 真实滞后（自动化可能漏跑 / 文件被弃）
          - 否则 max_news 落后今天 ≤ 2 天           → ✅（含「当日无合格新稿、未编造」的正常情形）
          - 否则（max_news 落后 >2 天但 updated 是今天）→ ℹ️ 当日无合格新稿（正常，守"不编造"红线）

  [数据板] ev-sales.json / ev-model-sales.json（月度行业数据，非日更）
      · 取 period 里的 latestMonth / month，得到「最新数据月份」。
      · 当前月份 = 今天所在月份。
      · 月份差（跨年按 year*12+month 计算）> DATA_MONTH_TOL(=2) → ⚠️ 数据板滞后（应刷新）
      · 否则 ✅（如 8 月数据在 10 月：因 9 月数据一般 10/8–10/10 才发布，属正常）

  [策划型组件] hot-picks.json / hero.json
      · 首页手工精选卡 / 头图轮播，常青内容、非时效新闻流 → 跳过（N/A，by design）。

退出码：
  默认报告模式：永远 0（只打印表格，不阻断）。
  --strict：仅当出现 ⚠️ 真实滞后 才退出 1（用于 CI 阻断）；ℹ️ / ✅ 不阻断。

用法：
    python3 scripts/check_freshness.py            # 报告模式
    python3 scripts/check_freshness.py --strict   # CI 阻断模式
"""
import datetime
import glob
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

NEWS_GLOBS = ["static/*-news.json", "static/tesla/fsd-news.json"]
NEWS_EXTRA = ["static/data/global.json"]          # 海外动态（items 数组）
DATA_BOARDS = ["static/ev-sales.json", "static/ev-model-sales.json"]
CURATED = ["static/hot-picks.json", "static/hero.json"]

STALE_UPDATED_DAYS = 3     # 新闻板：updated 超过此天数未碰 → 视为真实滞后
NEWS_LAG_TOL_DAYS = 2      # 新闻板：最新新闻落后今天 ≤ 此天数 视为正常（含无新稿日）
DATA_MONTH_TOL = 2         # 数据板：最新数据月份落后当前月份 ≤ 此月数 视为正常

_FULL = re.compile(r"^(\d{4})-(\d{1,2})-(\d{1,2})$")
_MD = re.compile(r"^(\d{1,2})-(\d{1,2})$")
_MONTH_IDX = re.compile(r"(\d{4})[\s年-]*(\d{1,2})")


def today():
    return datetime.date.today()


def infer(date_str, year):
    """把 date 字段推断成 datetime.date；MM-DD 按给定 year 解释；无法解析返回 None。"""
    d = str(date_str or "").strip()
    m = _FULL.match(d)
    if m:
        try:
            return datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            return None
    m = _MD.match(d)
    if m:
        try:
            return datetime.date(year, int(m.group(1)), int(m.group(2)))
        except ValueError:
            return None
    return None


def month_index(text):
    """从 '2026年8月' / '2026-08' / '202608' 之类提取 (year, month) 的 year*12+month 序号。"""
    if not text:
        return None
    m = _MONTH_IDX.search(str(text))
    if not m:
        return None
    try:
        y, mo = int(m.group(1)), int(m.group(2))
        return y * 12 + mo
    except ValueError:
        return None


def load(path):
    try:
        with open(os.path.join(ROOT, path), encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def classify_news(path, t):
    d = load(path)
    if not isinstance(d, dict):
        return ("N/A", path, "非 JSON 对象", None)
    arr = d.get("news") if isinstance(d.get("news"), list) else d.get("items")
    if not isinstance(arr, list) or not arr:
        return ("N/A", path, "无 news/items 数组", None)

    year = t.year
    mu = _FULL.match(str(d.get("updated", "")))
    if mu:
        try:
            upd = datetime.date(int(mu.group(1)), int(mu.group(2)), int(mu.group(3)))
        except ValueError:
            upd = None
    else:
        upd = None

    dates = [infer(it.get("date"), year) for it in arr if isinstance(it, dict)]
    dates = [x for x in dates if x]
    max_news = max(dates) if dates else None

    if upd is None:
        return ("⚠️", path, "updated 字段缺失/非法", max_news)
    upd_age = (t - upd).days
    if upd_age > STALE_UPDATED_DAYS:
        return ("⚠️", path, "updated 已 %d 天未碰（自动化可能漏跑）" % upd_age, max_news)
    lag = (t - max_news).days if max_news else None
    if lag is None:
        return ("ℹ️", path, "无日期条目", None)
    if lag <= NEWS_LAG_TOL_DAYS:
        return ("✅", path, "最新 %s（updated %s）" % (max_news, upd), max_news)
    return ("ℹ️", path, "最新 %s 落后 %d 天但 updated=%s（当日无合格新稿，未编造）" % (max_news, lag, upd), max_news)


def classify_data(path, t):
    d = load(path)
    if not isinstance(d, dict):
        return ("N/A", path, "非 JSON 对象", None)
    # 优先取 period.latestMonth / period.month；其次 nevMaker.period
    period = d.get("period") or {}
    latest = period.get("latestMonth") or period.get("month")
    if latest is None:
        nm = d.get("nevMaker") or {}
        p = nm.get("period") or ""
        mi = month_index(p)
    else:
        mi = month_index("%s-%s" % (period.get("year", t.year), latest)) if isinstance(latest, int) else month_index(str(latest))
    if mi is None:
        return ("N/A", path, "无法解析最新数据月份", None)
    cur = t.year * 12 + t.month
    gap = cur - mi
    upd = d.get("updated") or d.get("updatedAt") or ""
    if gap > DATA_MONTH_TOL:
        return ("⚠️", path, "最新数据月份落后 %d 个月（updated %s）" % (gap, upd), mi)
    return ("✅", path, "最新数据月份落后 %d 个月（updated %s，9 月数据通常 10/8–10/10 发布，属正常）" % (gap, upd), mi)


def main():
    t = today()
    print("══════════════════════════════════════════════════════════════")
    print(" 板块更新时效性审计  ·  今天 = %s" % t.isoformat())
    print("══════════════════════════════════════════════════════════════")

    rows = []
    warn = 0

    print("\n[新闻板]  最新一条新闻日期 / updated 是否近期被自动化触碰")
    news_paths = []
    for g in NEWS_GLOBS:
        news_paths += sorted(glob.glob(os.path.join(ROOT, g)))
    news_paths += [os.path.join(ROOT, p) for p in NEWS_EXTRA]
    for abspath in news_paths:
        rel = os.path.relpath(abspath, ROOT)
        status, _, detail, _ = classify_news(rel, t)
        rows.append((status, rel, detail))
        if status == "⚠️":
            warn += 1
        print("  %s %-32s %s" % (status, rel, detail))

    print("\n[数据板]  最新数据月份 vs 当前月份（月度行业数据，非日更）")
    for rel in DATA_BOARDS:
        status, _, detail, _ = classify_data(rel, t)
        rows.append((status, rel, detail))
        if status == "⚠️":
            warn += 1
        print("  %s %-32s %s" % (status, rel, detail))

    print("\n[策划型组件]  手工精选卡 / 头图轮播（常青内容，非时效流，跳过）")
    for rel in CURATED:
        rows.append(("N/A", rel, "by design，不日更"))
        print("  N/A %-32s %s" % (rel, "by design，不日更"))

    print("\n══════════════════════════════════════════════════════════════")
    print(" 结果：⚠️ 真实滞后 %d 项；其余正常 / 策划型跳过" % warn)
    print("══════════════════════════════════════════════════════════════")

    strict = "--strict" in sys.argv[1:]
    if strict and warn > 0:
        print("\n--strict 模式：存在 ⚠️ 真实滞后，退出码 1（阻断 CI）。")
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
