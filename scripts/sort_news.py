#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
板块新闻日期排序护栏（幂等）。

作用：把所有板块 news JSON 的 `news` 数组按 `date` 倒序排列（最新在最前），
根治「板块日期乱序」（如 08-17 > 08-11 > 08-15）。稳定排序：同日条目保持原有先后。

覆盖文件：static/*-news.json + static/tesla/fsd-news.json。
typhoon.json 的 feed 用 time(HH:MM) 无日期语义、changelog 由 guard_changelog.py 负责排序校验，均不在本脚本范围。

用法（仓库根目录执行）：
    python3 scripts/sort_news.py

退出码 0 = 全部处理成功（含无需调整的文件）。
"""
import glob
import json
import sys

TARGETS = sorted(glob.glob("static/*-news.json")) + ["static/tesla/fsd-news.json"]


def date_key(item):
    """MM-DD 或 YYYY-MM-DD 字符串；倒序用。缺日期的条目排最后。"""
    d = str(item.get("date", "") or "").strip()
    return d


def sort_file(path):
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        return f"跳过(不存在): {path}"
    except Exception as e:
        return f"解析失败! {path} -> {e}"

    if not isinstance(data, dict) or not isinstance(data.get("news"), list):
        return f"跳过(无 news 数组): {path}"

    before = [date_key(it) for it in data["news"]]
    # 稳定倒序排序：sorted 正序后反转会破坏同日稳定性，故用 key 取负序不可行，
    # 直接按 key 降序 + enumerate 保持稳定（Python sorted 为稳定排序，reverse=True 同样保持同 key 相对顺序）
    data["news"] = sorted(data["news"], key=date_key, reverse=True)
    after = [date_key(it) for it in data["news"]]

    if before == after:
        return f"{path}: 已有序 ({len(after)} 条)"

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
    return f"{path}: 重排 {len(after)} 条 [{' > '.join(after)}]"


if __name__ == "__main__":
    print("=== 板块新闻日期排序护栏 ===")
    failures = []
    for t in TARGETS:
        msg = sort_file(t)
        print("  " + msg)
        if "失败" in msg:
            failures.append(t)
    print("=== 排序完成 ===")
    sys.exit(1 if failures else 0)
