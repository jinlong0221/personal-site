#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成首页「近期节点」节日清单 -> data/festivals.json

设计目标（对应龙兄要求：大小节刻都要显示、星期天不单列、节刻到了的第二天即从主页剔除）：
- 农历节日用 lunardate 精确换算公历，杜绝手写错年（曾因中秋漏填 2026 误显 389 天）。
- 清明/冬至为节气，用权威年表（已核对日历网/国务院放假安排）。
- 仅保留 [今天, 今天+WINDOW] 内的节日。过期节日因不在窗口内而自动消失；
  下一个年度 recurrence 落在窗口之外，不会"刚过完就显示还有 365 天"。
- 二米自动化每日运行本脚本：清单随日期推移自动滚动，过期节日次日即被剔除。

用法：python3 scripts/gen_festivals.py
依赖：lunardate（pip install lunardate）
"""
import json
import os
import sys
from datetime import date, timedelta

try:
    import lunardate
except ImportError:
    sys.stderr.write("需要 lunardate：pip install lunardate\n")
    sys.exit(2)

# 展示窗口（天）：未来约 11 个月内的节日；下一个年度 recurrence 因 > 窗口而不立即出现
WINDOW_DAYS = 330

# 节气年表（已核对权威来源）：term_key -> {year: (month, day)}
SOLAR_TERMS = {
    "qingming": {  # 清明
        2024: (4, 4), 2025: (4, 4), 2026: (4, 5), 2027: (4, 5),
        2028: (4, 4), 2029: (4, 4), 2030: (4, 5), 2031: (4, 5), 2032: (4, 4),
    },
    "dongzhi": {  # 冬至
        2024: (12, 21), 2025: (12, 22), 2026: (12, 22), 2027: (12, 22),
        2028: (12, 21), 2029: (12, 21), 2030: (12, 22), 2031: (12, 22), 2032: (12, 21),
    },
}

# (label, kind, spec, type)
#   kind: fixed(MM-DD 固定公历) | lunar((农历月, 农历日)) | solar(term_key)
#   type: legal(法定大节) | traditional(传统小节) | solar(节气) | special(特殊节点)
FESTIVALS = [
    ("元旦", "fixed", "01-01", "legal"),
    ("春节", "lunar", (1, 1), "legal"),
    ("元宵", "lunar", (1, 15), "legal_trad"),
    ("龙抬头", "lunar", (2, 2), "traditional"),
    ("清明", "solar", "qingming", "legal"),
    ("劳动", "fixed", "05-01", "legal"),
    ("端午", "lunar", (5, 5), "legal"),
    ("七夕", "lunar", (7, 7), "traditional"),
    ("中元", "lunar", (7, 15), "traditional"),
    ("中秋", "lunar", (8, 15), "legal"),
    ("重阳", "lunar", (9, 9), "traditional"),
    ("寒衣节", "lunar", (10, 1), "traditional"),
    ("腊八", "lunar", (12, 8), "traditional"),
    ("小年", "lunar", (12, 23), "traditional"),
    ("冬至", "solar", "dongzhi", "solar"),
    ("国庆", "fixed", "10-01", "legal"),
    ("高考", "fixed", "06-07", "special"),
]


def resolve_date(year, kind, spec):
    if kind == "fixed":
        m, d = int(spec[:2]), int(spec[3:5])
        return date(year, m, d)
    if kind == "lunar":
        lm, ld = spec
        try:
            return lunardate.LunarDate(year, lm, ld).to_solar_date()
        except Exception:
            return None
    if kind == "solar":
        if year in SOLAR_TERMS[spec]:
            m, d = SOLAR_TERMS[spec][year]
            return date(year, m, d)
    return None


def main():
    today = date.today()
    start_year = today.year - 1
    end_year = today.year + 2
    out = []
    for label, kind, spec, ftype in FESTIVALS:
        for y in range(start_year, end_year + 1):
            d = resolve_date(y, kind, spec)
            if d is None:
                continue
            if today <= d <= today + timedelta(days=WINDOW_DAYS):
                out.append({"label": label, "date": d.isoformat(), "type": ftype})

    # 同日期去重（极端情况下不同历法/节气同日落在一个窗口），保标签稳定
    seen = {}
    dedup = []
    for x in out:
        if x["date"] in seen:
            continue
        seen[x["date"]] = True
        dedup.append(x)
    dedup.sort(key=lambda x: x["date"])

    here = os.path.dirname(os.path.abspath(__file__))
    repo = os.path.dirname(here)
    dest = os.path.join(repo, "data", "festivals.json")
    with open(dest, "w", encoding="utf-8") as f:
        json.dump(dedup, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print("生成 %d 个节日节点 -> %s" % (len(dedup), dest))
    for x in dedup:
        print("  %s  %s  (%s)" % (x["date"], x["label"], x["type"]))


if __name__ == "__main__":
    main()
