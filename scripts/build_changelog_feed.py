#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build_changelog_feed.py — 更新日志页的数据分层与静态回退注入

## 为什么需要它（2026-09-17 定位到的问题）

`static/changelog.html` 的正文过去 100% 由 `js/changelog.js` 在浏览器里现拼，
**源码里一个字都没有**。后果有三个：

1. **审计盲区**：只看 HTML 源码的产物体检（面包屑 / H1 / 页尾信息块 / 引号）
   四项全绿就放它过去了，内容质量问题一个都发现不了，成了长期盲区。
2. **爬虫与无 JS 环境**：搜索引擎与关闭 JS 的访客看到的是空容器。
3. **噪音淹没主线**：源头 `data/changelog.json` 里 652 条中约 418 条是
   「🌀 台风实时监测刷新」「🤖 自动巡检」这类自动化留痕，逐条铺开会把
   真正的改动（板块上线、缺陷修复、视觉重构）冲得看不见。

## 本脚本做两件事

### 1. 分层：主线 / 自动化运维

按内容首 80 字判定档位。**判定放在这里而不是写回数据源** ——
源头 652 条保持原样不删，自动任务继续往头部追加即可，渲染层自动分档。
分类规则日后要调，改本脚本一个地方即可。

- **主线**：整条原文进 feed，前端按天分组展示。
- **运维**：不逐条进 feed（418 条全文约 17 万字，塞进页面纯属噪音），
  按「天 × 类别」聚合成计数 + 每类最多 3 条样本。
  完整明细始终留在 `data/changelog.json` 里，页面上如实说明去哪看。

### 2. 静态回退：把正文写回 HTML

把「版本里程碑」与「最近 40 条主线条目」渲染成静态 HTML，
注入 `static/changelog.html` 的标记区之间。这样：

- 无 JS / 爬虫 / 首屏渲染都能看到真内容 → 审计盲区消失；
- JS 到位后 `changelog.js` 用完整 feed 覆盖 `#weeklyChangelog`，升级为
  全量 + 分档 + 按天分组的交互版本。**降级看得到，升级更好用。**

## 用法

    python3 scripts/build_changelog_feed.py            # 生成（幂等）
    python3 scripts/build_changelog_feed.py --check    # 只校验是否最新，过期退 1

护栏 `scripts/guard_changelog.py` 会以 --check 判定并在过期时自动重跑本脚本。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARCHIVE = os.path.join(ROOT, "data", "changelog.json")
CURATED = os.path.join(ROOT, "data", "changelog-curated.json")
FEED = os.path.join(ROOT, "static", "data", "changelog-feed.json")
PAGE = os.path.join(ROOT, "static", "changelog.html")

MS_START = "<!--CL:MILESTONES:START-->"
MS_END = "<!--CL:MILESTONES:END-->"
RC_START = "<!--CL:RECENT:START-->"
RC_END = "<!--CL:RECENT:END-->"

RECENT_MAIN = 40       # 静态回退里放多少条主线条目
OPS_SAMPLES = 3        # feed 里每类运维留痕最多给几条样本
OPS_SAMPLES_STATIC = 1 # 静态回退里给几条（页面体积与「看得见」的平衡点）
OPS_SAMPLE_CHARS = 220 # 静态回退里的样本截到多少字

# 自动化运维留痕的判定式。只在内容首 80 字内匹配，避免误伤正文里偶尔提到「台风」的主线条目。
OPS_RULES = [
    ("台风", r"^🌀|台风"),
    ("巡检", r"^🤖|自动巡检|巡检"),
    ("新闻接力", r"新闻接力|全部更新：|各板块新闻更新|新闻更新"),
    ("定时刷新", r"^📡|自动更新|自动刷新|定时刷新"),
]
OPS_HEAD_CHARS = 80
WEEKDAY = "一二三四五六日"


# ─────────────────────────── 基础工具 ───────────────────────────

def load_json(path: str):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def esc(s: str) -> str:
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def md_lite(s: str) -> str:
    """极简 Markdown 内联渲染：`code` 与 **bold**。

    源头正文里大量使用反引号包脚本名（如 `scripts/sync_v_param.py`），
    旧渲染层只做 HTML 转义，于是页面上满屏裸露的反引号 —— 这里补上。
    先转义再替换，不会引入 XSS 面。
    """
    out = esc(s)
    out = re.sub(r"`([^`]+)`", r"<code>\1</code>", out)
    out = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", out)
    return out


def split_lead(text: str, limit: int = 110, max_inline: int = 180) -> tuple[str, str]:
    """把一条记录拆成「首屏可见」与「收进详情」两段。

    旧渲染层把首句硬切到 60 字 + 省略号，切点常常落在脚本名或半句话中间，
    观感就是「话说到一半」。这里两条规则：

      1. 整体不超 max_inline（180 字）的短条目**整条显示**，不塞折叠 ——
         两句话就能讲完的事，让人多点一次「展开全文」纯属添堵。
      2. 长条目取首句；首句仍超 limit（110 字）时，回退到最近的标点
         （，、；：）断开，保证断在语义边界而不是半截脚本名上。
    """
    text = text.strip()
    if len(text) <= max_inline:
        return text, ""
    m = re.split(r"(?<=[。！？\n])", text, maxsplit=1)
    lead = m[0].strip()
    rest = (m[1].strip() if len(m) > 1 else "")
    if len(lead) <= limit:
        return lead, rest
    cut = -1
    for ch in "，、；：,;:":
        idx = lead.rfind(ch, 0, limit)
        if idx > cut:
            cut = idx
    if cut >= limit // 2:
        return lead[:cut + 1], (lead[cut + 1:] + (" " + rest if rest else "")).strip()
    return lead, rest


def classify(content: str) -> str | None:
    """返回运维类别名；主线条目返回 None。"""
    head = content[:OPS_HEAD_CHARS]
    for name, pat in OPS_RULES:
        if re.search(pat, head):
            return name
    return None


def fmt_day(date: str) -> str:
    y, m, d = date[:4], int(date[5:7]), int(date[8:10])
    import datetime
    wd = WEEKDAY[datetime.date(int(y), m, d).weekday()]
    return f"{y} 年 {m} 月 {d} 日 · 周{wd}"


def hhmm(date: str) -> str:
    return date[11:16] if len(date) >= 16 else ""


# ─────────────────────────── 组装 feed ───────────────────────────

def build():
    archive = load_json(ARCHIVE)
    curated = load_json(CURATED)

    ms = curated.get("milestones", [])
    early = curated.get("early", [])

    items: list[dict] = []
    for x in early:                     # 策展层：建站早期的逐日摘要
        c = (x.get("content") or "").strip()
        if c:
            items.append({"date": x["date"], "content": c, "src": "curated"})
    for x in archive:                   # 数据层：自动记录的逐条留痕
        c = (x.get("content") or "").strip()
        if c:
            items.append({"date": x.get("date", "").strip(), "content": c, "src": "archive"})

    # 去重（日期 + 去空白全文），保留先出现的（策展层优先）
    seen: dict[tuple, dict] = {}
    for x in items:
        seen.setdefault((x["date"], re.sub(r"\s+", "", x["content"])), x)
    items = list(seen.values())
    items.sort(key=lambda x: x["date"] if " " in x["date"] else x["date"] + " 00:00", reverse=True)

    # 分层
    days: dict[str, dict] = {}
    main_n = ops_n = 0
    for x in items:
        d10 = x["date"][:10]
        day = days.setdefault(d10, {"date": d10, "items": [], "ops": {}})
        op = classify(x["content"])
        if op is None:
            main_n += 1
            day["items"].append({"date": x["date"], "t": x["content"]})
        else:
            ops_n += 1
            slot = day["ops"].setdefault(op, {"n": 0, "s": []})
            slot["n"] += 1
            if len(slot["s"]) < OPS_SAMPLES:
                slot["s"].append(x["content"])

    day_list = [days[k] for k in sorted(days, reverse=True)]
    days_all = sorted(days)

    first, last = items[-1]["date"], items[0]["date"]
    stats = {
        "total": len(items),
        "main": main_n,
        "ops": ops_n,
        "days": len(days_all),
        "first": first[:10],
        "last": last,
        "chars": sum(len(x["content"]) for x in items),
        # 断档如实标注（数据源在 2026-07-24 ~ 08-04 确实没有记录，不补造）
        "gaps": find_gaps(days_all),
    }

    # 指纹同时纳入本脚本自身：只改渲染代码、没动数据时，--check 也必须认出来并重建，
    # 否则「改了渲染逻辑却没重新生成页面」这种事会静默发生。
    src_md5 = hashlib.md5(
        open(ARCHIVE, "rb").read()
        + open(CURATED, "rb").read()
        + open(os.path.abspath(__file__), "rb").read()
    ).hexdigest()

    feed = {
        "generated_at": last,
        "source_md5": src_md5,
        "stats": stats,
        "milestones": ms,
        "days": day_list,
    }
    return feed, stats, ms


def find_gaps(days_all: list[str]) -> list[str]:
    """相邻记录日跨度 > 3 天视为断档，返回 'YYYY-MM-DD~YYYY-MM-DD' 列表。"""
    import datetime
    gaps = []
    for a, b in zip(days_all, days_all[1:]):
        da = datetime.date(*map(int, a.split("-")))
        db = datetime.date(*map(int, b.split("-")))
        if (db - da).days > 3:
            gaps.append(f"{a}~{b}")
    return gaps


# ─────────────────────────── 静态回退渲染 ───────────────────────────

def render_milestones(ms: list[dict]) -> str:
    """版本里程碑，按 curated 里的 phase 连续分段渲染。

    2026-09-17 扩写：里程碑从 6 条补到 20 条（7/06 之后一直没人补过，见
    data/changelog-curated.json 的 _note）。20 张卡平铺有两个副作用：

      1. 底部自动章节导航（app.js 区域J）扫全页 h2/h3，20 条里程碑会把
         目录从 8 项撑到 22 项 → 卡片标题降为 h4，改由阶段标题（h3）进目录，
         目录反而收敛成「版本里程碑 + 4 阶段 + 更新轨迹」。
      2. 平铺看不出「哪几件是一批」→ 按阶段分段，每段单独一个网格。

    阶段名与顺序由数据决定（同阶段条目在倒序列表里必然相邻，故按相邻去重分段）。
    """
    if not ms:
        return ""

    groups: list[tuple[str, list[dict]]] = []
    for m in ms:
        ph = (m.get("phase") or "").strip()
        if not groups or groups[-1][0] != ph:
            groups.append((ph, []))
        groups[-1][1].append(m)

    out: list[str] = []
    for name, items in groups:
        if name:
            vers = [x["version"] for x in items if x.get("version")]
            if len(vers) > 1:
                rng = f"{vers[-1]} – {vers[0]}"   # 列表为倒序，升序展示才顺眼
            else:
                rng = vers[0] if vers else ""
            out.append(
                '<div class="cl-ms-ghead">'
                f'<h3 class="cl-ms-group">{esc(name)}</h3>'
                + (f'<span class="cl-ms-gver">{esc(rng)}</span>' if rng else "")
                + "</div>"
            )
        out.append('<div class="cl-ms-track">')
        for m in items:
            ver = f'<span class="cl-ms-ver">{esc(m["version"])}</span>' if m.get("version") else ""
            out.append(
                '<article class="cl-ms">'
                f'<div class="cl-ms-hd"><span class="cl-ms-ico" aria-hidden="true">{esc(m["emoji"])}</span>'
                f'<h4>{esc(m["title"])}{ver}</h4></div>'
                f'<div class="cl-ms-meta">{esc(m["date"])}</div>'
                f'<p>{md_lite(m["body"])}</p>'
                '</article>'
            )
        out.append("</div>")
    return "\n          ".join(out)


def render_recent(day_list: list[dict], limit: int) -> tuple[str, int]:
    """最近 N 条主线条目（含当天运维计数摘要），按天分组。"""
    buf, used = [], 0
    for day in day_list:
        if used >= limit:
            break
        rows = []
        for it in day["items"]:
            if used >= limit:
                break
            used += 1
            lead, rest = split_lead(it["t"])
            detail = ""
            if rest:
                detail = ('<details class="cl-detail"><summary>展开全文</summary>'
                          f'<div class="cl-body">{md_lite(rest)}</div></details>')
            t = hhmm(it["date"])
            time_html = f'<span class="cl-time">{t}</span>' if t else ""
            rows.append(f'<div class="cl-item">{time_html}'
                        f'<div class="cl-main"><p class="cl-head">{md_lite(lead)}</p>{detail}</div></div>')
        ops = render_ops_inline(day["ops"], OPS_SAMPLES_STATIC, OPS_SAMPLE_CHARS)
        if not rows and not ops:
            continue
        n = f'<span class="cl-day-n">{len(rows)} 项改动</span>' if rows else ""
        # 日分组用 h4 而非 h3：app.js 的区域J 自动章节导航会扫全页 h2/h3 生成目录，
        # 70 天的小标题会把它撑成 70 项。降一级后目录只剩「版本里程碑 +
        # 6 条里程碑」，层级上也更贴切——日分组本就隶属于「更新轨迹」。
        buf.append(
            f'<section class="cl-day"><h4 class="cl-day-hd">'
            f'<time datetime="{day["date"]}">{fmt_day(day["date"])}</time>{n}</h4>'
            + ("\n            ".join(rows) + "\n            " if rows else "")
            + (ops + "\n          " if ops else "")
            + "</section>"
        )
    return "\n        ".join(buf), used


def render_ops_inline(ops: dict, samples: int, sample_chars: int) -> str:
    if not ops:
        return ""
    chips, bodies = [], []
    for name, slot in ops.items():
        chips.append(f'<span class="cl-chip">{esc(name)} ×{slot["n"]}</span>')
        shown = slot["s"][:samples]
        items = "".join(
            f'<p class="cl-ops-row">{md_lite(clip(s, sample_chars))}</p>'
            + (f'<p class="cl-ops-more">…（该条完整记录见数据文件）</p>'
               if len(s) > sample_chars else "")
            for s in shown
        )
        rest = slot["n"] - len(shown)
        more = (f'<p class="cl-ops-more">另有 {rest} 条同类记录，'
                f'完整明细见站点数据文件 data/changelog.json。</p>' if rest > 0 else "")
        bodies.append(f'<div class="cl-ops-grp"><div class="cl-ops-name">{esc(name)}</div>{items}{more}</div>')
    return (
        '<details class="cl-ops"><summary><span class="cl-ops-t">自动化运维</span>'
        + "".join(chips) +
        '<span class="cl-ops-hint">展开明细</span></summary>'
        '<div class="cl-ops-body">' + "".join(bodies) + "</div></details>"
    )


def clip(s: str, n: int) -> str:
    if len(s) <= n:
        return s
    head = s[:n]
    cut = max(head.rfind(c) for c in "。！？；;!?")
    return (head[:cut + 1] if cut >= n // 2 else head) + "…"


def render_summary(stats: dict) -> str:
    g = stats["gaps"]
    gap_html = ""
    if g:
        gap_html = ('<p class="cl-sum-gap">记录断档：' +
                    "、".join(esc(x.replace("~", " ~ ")) for x in g) +
                    '（那几天本站未维护更新日志，此处不补造内容）</p>')
    return (
        f'<p class="cl-sum-lead">从 {esc(stats["first"])} 建站第一天起，'
        f'共 <strong>{stats["total"]}</strong> 条记录、覆盖 <strong>{stats["days"]}</strong> 天，'
        f'累计 <strong>{stats["chars"]:,}</strong> 字。</p>'
        f'<p class="cl-sum-sub">其中 <strong>{stats["main"]}</strong> 条是站点本身的改动'
        f'（新板块、修复、重构、文案），另有 <strong>{stats["ops"]}</strong> 条是台风监测、'
        f'新闻巡检这类自动化留痕 —— 后者按天折叠，不占版面。</p>'
        + gap_html
    )


def render_page(feed: dict) -> str:
    page = open(PAGE, encoding="utf-8").read()
    ms_html = render_milestones(feed["milestones"])
    recent_html, used = render_recent(feed["days"], RECENT_MAIN)

    page = splice(page, MS_START, MS_END, ms_html)
    page = splice(page, RC_START, RC_END, recent_html)

    # 「最后更新」拆两个 span：#changelogUpdated 只放日期（scripts/sync_update_time.py
    # 的兜底同步正则只认 \d{4}-\d{2}-\d{2}，写进时刻它就不认了），
    # 精确时刻另放 #clLastStamp，互不打架。
    last = feed["stats"]["last"]
    page = re.sub(r'(<span id="changelogUpdated">)[^<]*(</span>)',
                  lambda m: m.group(1) + esc(last[:10]) + m.group(2), page)
    stamp = f' {last[11:16]}' if len(last) >= 16 else ""
    page = re.sub(r'(<span id="clLastStamp"[^>]*>)[^<]*(</span>)',
                  lambda m: m.group(1) + esc(stamp) + m.group(2), page)

    # JSON-LD dateModified 同步到最新一条记录（旧值长期停留在 2026-08-09）
    page = re.sub(r'("dateModified"\s*:\s*")[^"]*(")',
                  lambda m: m.group(1) + last[:10] + m.group(2), page)
    return page, used


def splice(page: str, start: str, end: str, inner: str) -> str:
    i, j = page.find(start), page.find(end)
    if i < 0 or j < 0 or j < i:
        raise SystemExit(f"! 页面缺少标记 {start} / {end}，先修 static/changelog.html")
    return page[:i + len(start)] + "\n        " + inner + "\n        " + page[j:]


# ─────────────────────────── 入口 ───────────────────────────

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="只校验 feed 是否最新")
    args = ap.parse_args()

    feed, stats, ms = build()
    json_text = json.dumps(feed, ensure_ascii=False, separators=(",", ":")) + "\n"

    if args.check:
        try:
            old = load_json(FEED)
        except Exception:
            print("  ! changelog-feed.json 缺失或损坏，需重跑 build_changelog_feed.py")
            return 1
        if old.get("source_md5") != feed["source_md5"]:
            print("  ! changelog-feed.json 已过期（源数据变过），需重跑 build_changelog_feed.py")
            return 1
        page = open(PAGE, encoding="utf-8").read()
        for mark in (MS_START, MS_END, RC_START, RC_END):
            if mark not in page:
                print(f"  ! changelog.html 缺少标记 {mark}")
                return 1
        print(f"  ✅ changelog feed 与源数据同步（{stats['total']} 条）")
        return 0

    os.makedirs(os.path.dirname(FEED), exist_ok=True)
    with open(FEED, "w", encoding="utf-8") as f:
        f.write(json_text)

    page, used = render_page(feed)
    with open(PAGE, "w", encoding="utf-8") as f:
        f.write(page)

    print(f"  feed: {os.path.relpath(FEED, ROOT)}  {len(json_text)} 字节")
    print(f"  统计: 共 {stats['total']} 条 / 主线 {stats['main']} / 运维 {stats['ops']} / "
          f"{stats['days']} 天 / {stats['chars']:,} 字")
    print(f"  范围: {stats['first']} → {stats['last']}" + (f"  断档 {stats['gaps']}" if stats["gaps"] else ""))
    print(f"  页面: 里程碑 {len(ms)} 条，静态回退主线条目 {used} 条")
    return 0


if __name__ == "__main__":
    sys.exit(main())
