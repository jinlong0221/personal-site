#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""给科技动态 global.json 的条目补充「当事人英文原话 + 中文翻译 + 出处」。

原则（龙兄 2026-11-22 确认）：
- 只加英文权威媒体一致引用、能溯源的确凿原话；查不到的一律不加，保留中文摘要。
- 按 日期+人物+标题 精确定位，幂等（重复执行只会覆盖同一批，不会新增条目）。
- 不改动任何其它字段、不改动条目顺序。
"""
import json
from pathlib import Path

P = Path("static/data/global.json")

# key = (date, who, title片段)，value = 原话三件套
QUOTES = [
    {
        "date": "2026-11-21",
        "who": "musk",
        "title_key": "FSD V15下月全面推送",
        "quoteEn": "FSD V15 goes to wide release next month. It will be something special.",
        "quoteZh": "FSD V15 下个月将全面推送。它会非常特别。",
        "quoteSrc": "Elon Musk 在 X 的帖子（gettesla.com、electricvehicles.com 等英文媒体一致引用，2026-11-21）",
    },
    {
        "date": "2026-11-20",
        "who": "musk",
        "title_key": "Blindsight只待监管批准",
        "quoteEn": "Neuralink's Blindsight product is now just waiting for regulatory approval.",
        "quoteZh": "Neuralink 的 Blindsight 产品现在只待监管批准。",
        "quoteSrc": "Elon Musk 在 X 的帖子（aglena.com、NDTV 等英文媒体嵌引，2026-11-20）",
    },
    {
        "date": "2026-11-19",
        "who": "musk",
        "title_key": "剧透无方向盘自动驾驶Model Y",
        "quoteEn": "You've got a winning streak ... and then you kick Michael Jordan off your team. Doesn't seem like a smart decision to me.",
        "quoteZh": "你正处在连胜中……然后把迈克尔·乔丹踢出球队。这在我看来不是个明智的决定。",
        "quoteSrc": "Elon Musk 在纽约时报 DealBook 峰会（CNBC、IBTimes 等英文媒体一致引用，2026-11-18）",
    },
    {
        "date": "2026-11-18",
        "who": "huang",
        "title_key": "卸任后首度发声愿回归",
        "quoteEn": "If the board of directors decides that my return is in the best interest of our shareholders, our employees, the company and America, I would be honored to answer these calls and return as CEO.",
        "quoteZh": "如果董事会认定我的回归符合股东、员工、公司和美国的最佳利益，我将很荣幸回应这些呼声，重新担任 CEO。",
        "quoteSrc": "黄仁勋卸任后首份公开声明（ABC News、CBS News 等英文媒体一致引用，2026-11-17）",
    },
    {
        "date": "2026-11-17",
        "who": "musk",
        "title_key": "确认再度访华",
        "quoteEn": "I will be in China, so it will be digital me.",
        "quoteZh": "我会在中国，所以届时将由数字版的我出席。",
        "quoteSrc": "Elon Musk 在 X 回复 DealBook 峰会嘉宾帖（中新社、新华社等引用，2026-11-17）",
    },
]


def main():
    d = json.loads(P.read_text(encoding="utf-8"))
    items = d["items"]
    hit = 0
    for q in QUOTES:
        found = None
        for it in items:
            if (it.get("date") == q["date"] and it.get("who") == q["who"]
                    and q["title_key"] in it.get("title", "")):
                found = it
                break
        if found is None:
            raise SystemExit("未匹配到条目，请核对：%s / %s / %s" % (q["date"], q["who"], q["title_key"]))
        found["quoteEn"] = q["quoteEn"]
        found["quoteZh"] = q["quoteZh"]
        found["quoteSrc"] = q["quoteSrc"]
        hit += 1
        print("已加原话：%s %s —— %s" % (q["date"], q["who"], found["title"][:24]))

    # 同步更新页面说明文案（短句引用口径）
    d["note"] = "有原话的条目为英文原句 + 中文翻译的短句引用，其余为中文摘要；均注明出处，观点归原作者。"
    n_quoted = sum(1 for it in items if it.get("quoteEn"))
    P.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("完成：本次 %d 条，全库含原话 %d / %d 条，updated=%s" % (hit, n_quoted, len(items), d["updated"]))


if __name__ == "__main__":
    main()
