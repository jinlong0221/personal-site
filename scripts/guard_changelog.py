#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
changelog 提交前护栏（防御性清洗）。

作用：过滤 static/changelog.json 与 data/changelog.json 中所有
`content` 为空 / 空白 / 缺失的记录，避免更新日志页出现空白条目。
changelog 双副本属永久规则——任何改动都须进这两份。

用法（仓库根目录执行）：
    python3 scripts/guard_changelog.py

退出码 0 表示清洗成功（无解析失败）。
"""
import json
import sys

# changelog 双副本：static/ 为运行时读取，data/ 为 Hugo 构建读取，均须保持干净。
TARGETS = ["static/changelog.json", "data/changelog.json"]


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


if __name__ == "__main__":
    print("=== changelog 护栏：开始清洗空记录 ===")
    failures = []
    for t in TARGETS:
        msg = clean(t)
        print("  " + msg)
        if "失败" in msg or "异常" in msg:
            failures.append(t)
    print("=== 清洗完成 ===")
    sys.exit(1 if failures else 0)
