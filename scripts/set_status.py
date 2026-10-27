#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
set_status.py — 一句话更新「龙兄公示牌 / 站点状态」

为什么要有它：
  站点状态有 3 个消费方，分散在 3 个文件里，手动改容易漏、容易漂移：
    1) data/status.json        —— 唯一真源。导航栏气泡由 Hugo 在构建时注入
                                   （layouts/partials/head.html 读 hugo.Data.status）。
    2) static/status.json      —— fetch 回退用的「当前态」（status-bubble.js /
                                   app.js / 历史页兜底都读它）。
    3) *-status-history.json   —— 历史页主数据，由 build_status_history.py
                                   以 data/status.json 为源重建（含去重 + 倒序）。
  本脚本把「改状态」收敛成一行命令：更新真源 + 同步回退态 + 重建历史 + 提交上线。

龙兄怎么用（最简单）：
  直接在咱俩聊天里跟我说一句你当下的状态就行，例如：
      「今天加班到很晚，勿扰」
      「正在跑步 🏃」
      「周末回射阳陪家人」
  我跑下面这行，剩下的写入 / 生成历史 / 上线全包了：
      python3 scripts/set_status.py "今天加班到很晚，勿扰" --emoji 🌙 --dnd

命令行用法（如果你想自己跑也行）：
  python3 scripts/set_status.py "状态文案" [--emoji 🏃] [--dnd] [--no-push]
                               [--date 2026-10-28] [--time 14:30] [--show]

  --emoji   表情，缺省自动沿用上一条
  --dnd     开启「勿扰」徽标；文案里出现 勿扰/非诚勿扰/别打扰/勿cue 也会自动开
  --no-push 只改本地、不提交不推送（CI 不会动这些文件，必须本地提交才上线）
  --show    只打印当前状态，不改任何东西
  --date/--time  覆盖日期 / 时间（默认取当前北京时间）

红线：status 文案 100% 照搬龙兄原话，绝不替他编、绝不润色成第一人称。
"""
import json
import os
import sys
import subprocess
import argparse
from datetime import datetime, timezone, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "data", "status.json")
STATIC_CUR = os.path.join(ROOT, "static", "status.json")
HISTORY_SCRIPT = os.path.join(ROOT, "scripts", "build_status_history.py")
DEAD_ROOT = os.path.join(ROOT, "status.json")  # 未服务的死副本，提醒用

CST = timezone(timedelta(hours=8))
DND_KEYWORDS = ("勿扰", "非诚勿扰", "别打扰", "勿cue", "别cue", "免打扰")


def now_fields():
    n = datetime.now(CST)
    iso = n.strftime("%Y-%m-%dT%H:%M:%S+08:00")
    return iso, n.strftime("%Y-%m-%d"), n.strftime("%H:%M")


def load():
    with open(SRC, encoding="utf-8") as f:
        return json.load(f)


def save(data):
    with open(SRC, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def sync_static_cur(status, emoji, dnd, date, time, iso):
    cur = {
        "status": status,
        "emoji": emoji,
        "dnd": dnd,
        "date": date,
        "time": time,
        "updatedAt": iso,
    }
    with open(STATIC_CUR, "w", encoding="utf-8") as f:
        json.dump(cur, f, ensure_ascii=False, indent=2)
        f.write("\n")


def rebuild_history():
    rc = subprocess.run([sys.executable, HISTORY_SCRIPT], cwd=ROOT)
    return rc.returncode


def git_commit_push(status, emoji):
    files = [
        "data/status.json",
        "static/status.json",
        "data/status-history.json",
        "static/status-history.json",
    ]
    add = subprocess.run(["git", "add", "--", *files], cwd=ROOT,
                         capture_output=True, text=True)
    if add.returncode != 0:
        print("ERROR: git add 失败\n" + add.stderr, file=sys.stderr)
        return 1
    msg = "状态更新：%s %s" % (status, emoji)
    com = subprocess.run(["git", "commit", "-m", msg], cwd=ROOT,
                         capture_output=True, text=True)
    if com.returncode != 0:
        print("ERROR: git commit 失败（可能是 pre-commit 守卫拦截）\n"
              + com.stdout + "\n" + com.stderr, file=sys.stderr)
        return 1
    push = subprocess.run(["git", "push"], cwd=ROOT,
                          capture_output=True, text=True)
    if push.returncode != 0:
        print("ERROR: git push 失败\n" + push.stdout + "\n" + push.stderr,
              file=sys.stderr)
        return 1
    return 0


def main():
    ap = argparse.ArgumentParser(description="一句话更新站点状态")
    ap.add_argument("status", nargs="?", help="状态文案（龙兄原话，照搬）")
    ap.add_argument("--emoji", default=None, help="表情，缺省沿用上一条")
    ap.add_argument("--dnd", action="store_true", help="开启勿扰徽标")
    ap.add_argument("--no-push", action="store_true", help="只改本地，不提交不推送")
    ap.add_argument("--date", default=None, help="覆盖日期 YYYY-MM-DD")
    ap.add_argument("--time", default=None, help="覆盖时间 HH:MM")
    ap.add_argument("--show", action="store_true", help="只打印当前状态")
    args = ap.parse_args()

    if args.show or not args.status:
        data = load()
        print("当前状态：%s %s%s" % (
            data.get("status", ""), data.get("emoji", ""),
            "  🔕勿扰" if data.get("dnd") else ""))
        print("更新时间：%s" % data.get("updatedAt", data.get("timestamp", "")))
        print("历史条数：%d" % len(data.get("history", [])))
        return 0

    status = args.status.strip()
    data = load()

    prev_emoji = data.get("emoji") or "📌"
    emoji = (args.emoji or prev_emoji).strip()
    dnd = args.dnd or any(k in status for k in DND_KEYWORDS)

    iso, d, t = now_fields()
    if args.date:
        d = args.date.strip()
    if args.time:
        t = args.time.strip()

    # 只改顶层「当前态」；旧当前态已在 history[] 里，build_status_history 会去重并入
    data["status"] = status
    data["emoji"] = emoji
    data["dnd"] = dnd
    data["date"] = d
    data["time"] = t
    data["timestamp"] = iso
    data["updatedAt"] = iso

    save(data)
    sync_static_cur(status, emoji, dnd, d, t, iso)

    rc = rebuild_history()
    if rc != 0:
        print("ERROR: 历史镜像重建失败（data/status.json 已更新，但历史页可能未刷新）",
              file=sys.stderr)
        return rc

    print("已更新当前状态：%s %s%s" % (status, emoji, "  🔕勿扰" if dnd else ""))
    print("  data/status.json + static/status.json 已同步；历史镜像已重建")

    if os.path.exists(DEAD_ROOT):
        print("提示：仓库根目录还有一份未服务的死副本 status.json（不被 Hugo 读取），"
              "建议一并删除，避免将来有人改错文件。")

    if args.no_push:
        print("（--no-push：已改本地，未提交；记得手动提交或去掉该参数）")
        return 0

    rc = git_commit_push(status, emoji)
    if rc == 0:
        print("已提交并推送，CI 会自动部署上线（约 1-2 分钟）。")
    return rc


if __name__ == "__main__":
    sys.exit(main())
