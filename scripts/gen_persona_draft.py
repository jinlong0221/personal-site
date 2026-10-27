#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gen_persona_draft.py — 自主更新的「思考层」草稿生成器（绝不自动发布）

定位：
  二米（auto_update_*.py）负责把"事实"自动搬进各板块；但龙兄要的"活的站点"还差一层——
  把新发生的事，自动联想到龙兄本人的立场、和他写过的随笔，形成一段"龙兄怎么看"的连接。
  这一层绝不能替龙兄编造第一人称日记（红线圈定），所以本脚本只做三件安全的事：
    1) 取"近期真实事件"（来自 data/changelog-curated.json 的 milestones）；
    2) 用关键词把事件映射到龙兄人格库里的某个板块态度，取出龙兄的【真实原话】与【真实随笔链接】；
    3) 产出一份 status=draft 的草稿（JSON + Markdown），交给龙兄本人过目、手写定稿后才进 notes.md。

护栏（来自 data/persona.json 的 review_policy / red_lines）：
  - 生成的任何"龙兄口吻"文字都不是龙兄已认证的，必须标注 草稿 / 待龙兄定稿；
  - 只引用龙兄真实原话（pull_quote）、只挂真实随笔链接（persona_pages），不自由造句；
  - 输出落点到 static/_drafts/ 与 data/，绝不写进任何线上页面或 notes.md。

用法：
  python3 scripts/gen_persona_draft.py            # 生成最近 8 条里程碑的草稿
  python3 scripts/gen_persona_draft.py --days 30  # 只看最近 30 天内的里程碑
  python3 scripts/gen_persona_draft.py --check    # 只打印，不写文件
"""
import json
import os
import re
import sys
from datetime import datetime, date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PERSONA = os.path.join(ROOT, "data", "persona.json")
CURATED = os.path.join(ROOT, "data", "changelog-curated.json")
OUT_JSON = os.path.join(ROOT, "data", "persona-drafts.json")
# 草稿落在仓库根目录（不在 static/ 下），避免被部署成公开页面；
# 仅供龙兄本地过目，定稿后手写进 notes.md 再删除。
DRAFT_DIR = os.path.join(ROOT, "_drafts")
OUT_MD = os.path.join(DRAFT_DIR, "龙兄怎么看-草稿.md")

# 事件关键词 → 龙兄人格库里的板块（用于把"事实"连到"龙兄视角"）
# 顺序敏感：具体的板块（特斯拉/紫砂…）放前面，泛化的（站点工具/工具箱/苹果）放后面，
# 避免「数据」「手机端」这类泛词把事件错配到不相关的板块。
KEYWORD_BOARD = [
    ("特斯拉|FSD|新能源|销量|电车|充电|车型", "特斯拉"),
    ("紫砂|壶|包浆|养", "紫砂"),
    ("手串|盘玩|星月|金刚|菩提", "文玩手串"),
    ("漫威|票房|电影|宇宙", "漫威"),
    ("主机|游戏机|掌机|Switch|PlayStation|Xbox", "主机图鉴"),
    ("游戏|通关|评分|游玩", "玩过的游戏"),
    ("中药|药材|香料|养生|茶|配方", "中药材香料"),
    ("天气|台风|节气|射阳|气象|降雨|农", "天气"),
    ("首页|板块墙|归类|栏目|导航|重构|分类", "站点工具"),
    ("隐私|合规|统计|计数|百度|提示词库|下线|砍掉", "工具箱"),
    ("折叠屏|iPhone|iPad|Mac|苹果", "苹果"),
]

RECENT_DEFAULT = 8


def load_json(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def map_board(title, body=""):
    # 标题优先：标题命中直接采用，避免正文里"顺带提到"的板块名造成误配
    # （如「折叠屏适配」正文提到"紫砂网格"、分类修复正文提到"台风"）
    for pat, board in KEYWORD_BOARD:
        if re.search(pat, title or ""):
            return board
    for pat, board in KEYWORD_BOARD:
        if re.search(pat, body or ""):
            return board
    return ""


def parse_date(s):
    for fmt in ("%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except Exception:
            pass
    return None


def main():
    check_only = "--check" in sys.argv
    days = RECENT_DEFAULT
    if "--days" in sys.argv:
        try:
            days = int(sys.argv[sys.argv.index("--days") + 1])
        except Exception:
            pass

    persona = load_json(PERSONA)
    att = persona.get("board_attitudes", {})
    pm = {p["url"]: p for p in persona.get("persona_pages", [])}
    curated = load_json(CURATED)
    milestones = curated.get("milestones", [])

    today = date.today()
    cutoff = today.replace(day=1)  # 默认不按天数，下面按条数截；--days 时再过滤
    if "--days" in sys.argv:
        from datetime import timedelta
        cutoff = today - timedelta(days=days)

    drafts = []
    for m in milestones:
        d = parse_date(m.get("date", ""))
        if d is None:
            continue
        if "--days" in sys.argv and d < cutoff:
            continue
        title = m.get("title", "")
        body = m.get("body", "")
        board = map_board(title, body)
        entry = {
            "date": m.get("date"),
            "event": title,
            "event_detail": body,
            "mapped_board": board,
            "persona_quote": "",
            "persona_quote_source": "",
            "persona_pages": [],
            "suggested_angle": "",   # 仅提示：哪条龙兄真实立场可呼应，不代写
            "status": "draft",       # 草稿，待龙兄本人定稿
            "note": "（待龙兄本人填写真实手记；本草稿只做连接建议，非龙兄已认证文字）",
        }
        if board and board in att:
            a = att[board]
            entry["persona_quote"] = a.get("pull_quote", "")
            entry["persona_quote_source"] = a.get("pull_source", "")
            entry["persona_pages"] = a.get("persona_links", [])
            entry["suggested_angle"] = a.get("stance", "")
        drafts.append(entry)
        if len(drafts) >= (days if "--days" not in sys.argv else days):
            # 按条数模式：取最近 RECENT_DEFAULT 条（milestones 已按时间排？取末尾）
            pass

    # milestones 可能按时间正序排列，统一按日期倒序，再取最近 N 条
    drafts.sort(key=lambda e: parse_date(e["date"]) or date.min, reverse=True)
    if "--days" not in sys.argv:
        drafts = drafts[:RECENT_DEFAULT]

    # ---- 输出 ----
    lines = ["# 龙兄怎么看 · 草稿（自动连接建议，待龙兄定稿）", "",
             "> 本文件由 gen_persona_draft.py 生成，全部为 **草稿（status=draft）**。",
             "> 只引用龙兄真实原话 + 真实随笔链接，**不含任何龙兄已认证的第一人称文字**。",
             "> 龙兄过目后，把认可的内容手写进 content/notes.md，再删除对应草稿。", ""]
    for e in drafts:
        lines.append(f"## {e['date']} · {e['event']}")
        lines.append(f"- 事实：{e['event_detail']}")
        if e["mapped_board"]:
            lines.append(f"- 可呼应板块：{e['mapped_board']}")
            if e["persona_quote"]:
                lines.append(f"- 龙兄原话（可引用）：「{e['persona_quote']}」 —— {e['persona_quote_source']}")
            if e["persona_pages"]:
                links = "、".join(f"[{pm[u]['title']}]({u})" for u in e["persona_pages"] if u in pm)
                lines.append(f"- 相关随笔：{links}")
            lines.append(f"- 角度提示：{e['suggested_angle']}")
        else:
            lines.append("- （未匹配到龙兄视角板块，可手动归类）")
        lines.append(f"- 状态：{e['status']} —— {e['note']}")
        lines.append("")

    md = "\n".join(lines)

    if not check_only:
        os.makedirs(DRAFT_DIR, exist_ok=True)
        json.dump(drafts, open(OUT_JSON, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        with open(OUT_MD, "w", encoding="utf-8") as f:
            f.write(md)
        print(f"已写入 {OUT_JSON} 与 {OUT_MD}（共 {len(drafts)} 条草稿）")
    else:
        print(md)


if __name__ == "__main__":
    main()
