#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_status_history.py — 站点状态历史：由唯一真相源生成静态镜像（幂等）

背景（2026-09-19 体检发现并修复）：
  static/status-history.html 的取数逻辑是

      if (xhr.response && xhr.response.history) renderHistory(xhr.response.history);
      else showCurrentStatusOnly();          // 退回只显示单条当前状态

  即它期望 `{"history": [...]}` 这种「带外壳」的对象。但仓库里的
  static/status-history.json 一直是**裸数组** `[ {...}, {...} ]`，
  于是 `response.history` 恒为 undefined，页面**永远只显示 1 条当前状态**，
  文件里那两条历史从来没有被渲染过。

  同时还有第二重漂移：真源 data/status.json 的 history 有 18 条，
  而 static 镜像只有 2 条（最后一次同步是 2026-08-06 那次状态更新）。

本脚本做两件事：
  1) 以 data/status.json 为唯一真相源，重建派生镜像
     → data/status-history.json 与 static/status-history.json（两份内容一致）
  2) 统一输出成页面期望的 `{"history": [...]}` 外壳形态

幂等：内容已一致时不写盘；--check 只报告不写（供 CI / 本地核验用）。

用法：
  python3 scripts/build_status_history.py            # 生成（默认）
  python3 scripts/build_status_history.py --check    # 只核对，不同步（不一致时退出码 1）
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SRC = os.path.join(ROOT, "data", "status.json")
TARGETS = [
    os.path.join(ROOT, "data", "status-history.json"),
    os.path.join(ROOT, "static", "status-history.json"),
]

FIELDS = ("date", "time", "status", "emoji", "updatedAt")


def _norm(item):
    """规范单条记录：只保留已知字段，time 为空则去掉该键。"""
    out = {}
    for k in FIELDS:
        v = item.get(k)
        if v in (None, ""):
            continue
        out[k] = v
    return out


def _key(item):
    return (item.get("date", ""), item.get("time") or "00:00", item.get("status", ""))


def build_history(data):
    """由 data/status.json 的内容推导出完整历史（去重 + 按时间倒序）。

    同时容纳两种上游形态：
      A) 顶层带 history 数组（当前形态）
      B) 只有顶层状态字段（无 history，例如早期文件）
    并把「顶层当前状态」本身也算作一条，保证最新一条永不在镜像里丢失。
    """
    rows = []
    hist = data.get("history")
    if isinstance(hist, list):
        rows.extend(h for h in hist if isinstance(h, dict))

    # 顶层字段就是「当前状态」，可能已包含在 history 里，去重即可
    cur = {k: data.get(k) for k in FIELDS if data.get(k) not in (None, "")}
    if cur.get("status"):
        rows.append(cur)

    seen = set()
    out = []
    for r in rows:
        n = _norm(r)
        if not n.get("status") or not n.get("date"):
            continue
        k = _key(n)
        if k in seen:
            continue
        seen.add(k)
        out.append(n)

    out.sort(key=_key, reverse=True)
    return out


def render(history):
    return json.dumps({"history": history}, ensure_ascii=False, indent=2) + "\n"


def main():
    check = "--check" in sys.argv

    if not os.path.exists(SRC):
        print("ERROR: 找不到真源 %s" % os.path.relpath(SRC, ROOT))
        return 1

    with open(SRC, "r", encoding="utf-8") as f:
        data = json.load(f)

    history = build_history(data)
    if not history:
        print("ERROR: 从 %s 推导出的历史为空，拒绝写入" % os.path.relpath(SRC, ROOT))
        return 1

    content = render(history)
    newest, oldest = history[0], history[-1]
    label = "%d 条（%s → %s），最新：%s" % (
        len(history), oldest.get("date"), newest.get("date"),
        str(newest.get("status"))[:24])

    stale = []
    for t in TARGETS:
        rel = os.path.relpath(t, ROOT)
        cur = None
        if os.path.exists(t):
            with open(t, "r", encoding="utf-8") as f:
                cur = f.read()
        if cur == content:
            print("  OK   %-34s 已是最新" % rel)
        else:
            stale.append(rel)

    if not stale:
        print("状态历史已同步：%s" % label)
        return 0

    if check:
        print("  DRIFT %d 个文件与真源不一致：" % len(stale))
        for rel in stale:
            print("        - %s" % rel)
        print("错误：状态历史镜像落后于 %s（跑 scripts/build_status_history.py 同步）"
              % os.path.relpath(SRC, ROOT))
        return 1

    for t in TARGETS:
        if os.path.relpath(t, ROOT) in stale:
            with open(t, "w", encoding="utf-8") as f:
                f.write(content)
            print("  写回 %s" % os.path.relpath(t, ROOT))
    print("状态历史已同步：%s" % label)
    return 0


if __name__ == "__main__":
    sys.exit(main())
