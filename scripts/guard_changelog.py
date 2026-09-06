#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
changelog 提交前护栏（防御性清洗）。

作用：过滤三份 changelog 副本（static/changelog.json、data/changelog.json、
static/data/changelog.json）中所有 `content` 为空 / 空白 / 缺失的记录，避免
更新日志页出现空白条目。changelog 三副本属永久规则——任何改动都须三份同步。
2026-08-20 起同时内联执行板块新闻日期排序自愈（scripts/sort_news.py）。

用法（仓库根目录执行）：
    python3 scripts/guard_changelog.py

退出码 0 表示清洗成功（无解析失败）。
"""
import hashlib
import json
import sys

# changelog 三副本：static/ 与 static/data/ 为运行时读取，data/ 为 Hugo 构建读取，均须保持干净。
TARGETS = ["static/changelog.json", "data/changelog.json", "static/data/changelog.json"]


def clean(path: str) -> str:
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        return f"跳过(不存在): {path}"
    except Exception as e:  # 解析失败绝不静默放过
        return f"解析失败! {path} -> {e}"

    if not isinstance(data, list):
        return f"跳过(非数组，结构异常): {path}"

    before = len(data)
    out = [r for r in data if isinstance(r, dict) and (r.get("content") or "").strip()]
    dropped = before - len(out)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    return f"{path}: {before} 条 -> {len(out)} 条 (删除空记录 {dropped})"


def verify_identical() -> list[str]:
    """同步后回读三副本，确认字节完全一致。

    2026-09-06 加：sync_canonical 只是「写过」，不等于「真的一致」。
    实测曾出现三副本差一个末尾换行、护栏却报「已同步」的情况——
    根因不在本脚本，而在 pre-commit 钩子重加暂存时漏了一个文件，
    导致提交里装的还是旧内容。这里加一道回读断言，让这类偏差下次直接暴露。
    """
    digests = {}
    for path in TARGETS:
        try:
            with open(path, "rb") as f:
                digests[path] = hashlib.md5(f.read()).hexdigest()
        except FileNotFoundError:
            digests[path] = None
    missing = [p for p, d in digests.items() if d is None]
    if missing:
        print("  回读失败(文件缺失): " + ", ".join(missing))
        return missing
    if len(set(digests.values())) != 1:
        print("  ⚠️ 三副本字节不一致:")
        for p, d in digests.items():
            print(f"      {d}  {p}")
        return ["三副本不一致"]
    print(f"  ✅ 三副本字节一致 (md5 {next(iter(digests.values()))[:12]}…)")
    return []


def sync_canonical(canonical: str = "static/changelog.json") -> list[str]:
    """以 canonical 副本为准，强制三副本字节一致；返回被同步的路径列表。"""
    synced = []
    try:
        with open(canonical, encoding="utf-8") as f:
            text = f.read()
        # 解析校验：确保 canonical 是合法 JSON
        json.loads(text)
    except Exception as e:
        print(f"  同步失败: canonical {canonical} 无法读取或解析 -> {e}")
        return synced

    for target in TARGETS:
        if target == canonical:
            continue
        try:
            with open(target, "w", encoding="utf-8") as f:
                f.write(text)
            synced.append(target)
        except Exception as e:
            print(f"  同步失败: {target} -> {e}")
    return synced


if __name__ == "__main__":
    print("=== changelog 护栏：开始清洗空记录 ===")
    failures = []
    for t in TARGETS:
        msg = clean(t)
        print("  " + msg)
        if "失败" in msg or "异常" in msg:
            failures.append(t)
    print("=== 清洗完成 ===")

    # —— 三副本同步：以 static/changelog.json 为准，强制 data/ 与 static/data/ 一致 ——
    print("=== changelog 三副本同步 ===")
    synced = sync_canonical()
    if synced:
        print("  已同步至: " + ", ".join(synced))
    else:
        print("  三副本已一致，无需同步")

    # 回读断言：同步完必须真的一致，不一致就阻断提交
    failures.extend(verify_identical())
    print("=== 同步完成 ===")

    # —— 板块新闻日期排序（自愈护栏，2026-08-20 接入）——
    # 所有自动更新任务提交前都会执行本脚本；顺带把各板块 news 数组按日期倒序
    # 规范化（scripts/sort_news.py，幂等），根治「板块日期乱序」。
    # 排序失败则本护栏整体退出码置 1，阻断提交。
    import runpy
    try:
        runpy.run_path("scripts/sort_news.py", run_name="__main__")
    except SystemExit as e:
        if e.code:
            print("  sort_news 报告失败，退出码:", e.code)
            failures.append("sort_news")
    except Exception as e:  # 排序脚本本身异常（缺文件/权限等）
        print(f"  sort_news 执行异常: {e}")
        failures.append("sort_news")

    sys.exit(1 if failures else 0)
