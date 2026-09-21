#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
板块新闻日期排序护栏（幂等）。

作用：
  1) 把所有板块 news JSON 的 `news` 数组按「真实日期」倒序排列（最新在最前）。
     - 兼容 `MM-DD` 与 `YYYY-MM-DD` 两种写法。
     - 🔴 **跨年修正（本脚本的核心）**：`MM-DD` 不带年份，若直接按字符串倒序，
       「12-15」会大于「09-22」而被排到最顶 —— 于是去年的 12 月新闻压在今年的
       9 月新闻上面，看着就像"日期错了"。这里改为按**推断出的真实日期**排序：
       把 (今年, MM, DD) 与今天比较，若落在未来（留 3 天时区容差）则判为**去年**。
       例：今天 2026-09-22 时，「12-15」→ 2025-12-15（排到 09-xx 之后）。
  2) 陈旧告警（只提示、不删除）：推断日期距今超过 STALE_DAYS 的条目会在输出里
     点名，便于运营发现"老条目长期占位"。删除与否交给人工/自动化决策，避免误伤
     「板块当天无新稿时保留原有最新条目」的规则。

覆盖文件：static/*-news.json + static/tesla/fsd-news.json。
typhoon.json 的 feed 用 time(HH:MM) 无日期语义、changelog 由 guard_changelog.py 负责，均不在本脚本范围。

用法（仓库根目录执行）：
    python3 scripts/sort_news.py

退出码 0 = 全部处理成功（含无需调整的文件）。
"""
import datetime
import glob
import json
import re
import sys

TARGETS = sorted(glob.glob("static/*-news.json")) + ["static/tesla/fsd-news.json"]

TODAY = datetime.date.today()
FUTURE_TOL_DAYS = 3      # 时区容差：允许 3 天内的"未来"日期仍算今年
STALE_DAYS = 90          # 超过此天数只告警、不删除

_FULL = re.compile(r"^(\d{4})-(\d{1,2})-(\d{1,2})$")
_MD = re.compile(r"^(\d{1,2})-(\d{1,2})$")
_FAR = datetime.date(1900, 1, 1)   # 无日期条目的排序占位（排最后）


def infer_date(item):
    """把条目 date 推断成 datetime.date；无法解析/缺日期返回 None。"""
    d = str(item.get("date", "") or "").strip()
    m = _FULL.match(d)
    if m:
        y, mo, dd = (int(x) for x in m.groups())
        try:
            return datetime.date(y, mo, dd)
        except ValueError:
            return None
    m = _MD.match(d)
    if m:
        mo, dd = int(m.group(1)), int(m.group(2))
        limit = TODAY + datetime.timedelta(days=FUTURE_TOL_DAYS)
        for y in (TODAY.year, TODAY.year - 1):
            try:
                dt = datetime.date(y, mo, dd)
            except ValueError:
                return None
            if dt <= limit:
                return dt
        return None
    return None


def sort_file(path):
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        return f"跳过(不存在): {path}", []
    except Exception as e:
        return f"解析失败! {path} -> {e}", []

    if not isinstance(data, dict) or not isinstance(data.get("news"), list):
        return f"跳过(无 news 数组): {path}", []

    before = [str(it.get("date", "") or "").strip() for it in data["news"]]
    dated = [(infer_date(it), it) for it in data["news"]]

    # 真实日期倒序；无日期条目排最后且保持原有相对顺序（sorted 稳定排序）
    dated.sort(key=lambda t: (t[0] is not None, t[0] or _FAR), reverse=True)
    data["news"] = [it for _, it in dated]
    after = [str(it.get("date", "") or "").strip() for it in data["news"]]

    # 陈旧告警（不删）
    stale = []
    for dt, it in dated:
        if dt is not None and (TODAY - dt).days > STALE_DAYS:
            stale.append(f"{it.get('date')}({(TODAY - dt).days}天)")

    if before != after:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write("\n")
        msg = f"{path}: 重排 {len(after)} 条 [{' > '.join(after)}]"
    else:
        msg = f"{path}: 已有序 ({len(after)} 条)"

    if stale:
        msg += f"  ⚠️ 陈旧({STALE_DAYS}天+): {', '.join(stale)}"
    return msg, stale


if __name__ == "__main__":
    print("=== 板块新闻日期排序护栏（跨年感知）===")
    failures = []
    all_stale = []
    for t in TARGETS:
        msg, stale = sort_file(t)
        print("  " + msg)
        if "失败" in msg:
            failures.append(t)
        all_stale += stale
    if all_stale:
        print(f"  ⚠️ 共 {len(all_stale)} 条陈旧条目（仅告警，未删除）")
    print("=== 排序完成 ===")
    sys.exit(1 if failures else 0)
