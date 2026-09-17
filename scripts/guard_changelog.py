#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
changelog 提交前护栏（防御性清洗）。

作用：过滤三份 changelog 副本（static/changelog.json、data/changelog.json、
static/data/changelog.json）中所有 `content` 为空 / 空白 / 缺失的记录，避免
更新日志页出现空白条目。changelog 三副本属永久规则——任何改动都须三份同步。
2026-08-20 起同时内联执行板块新闻日期排序自愈（scripts/sort_news.py）。

2026-09-17 加两道：

  · **条数暴跌拦截**。只删空记录对「条数大面积缩水」零感知 —— 提交 48c1e092
    （message 只有「🌀 台风实时监测刷新」）把 435 条砍到 40 条，一路没人拦，
    更新日志页因此只剩 17 天记录。现在与上一个提交比，掉 15 条以上且掉幅
    超 20% 就阻断提交（有意清理请带 CHANGELOG_ALLOW_SHRINK=1）。
  · **feed 自愈**。数据改完忘跑 scripts/build_changelog_feed.py，页面就停在
    旧内容上；自动任务天天追加条目，靠人记得跑不现实。这里检测到过期就重建。

用法（仓库根目录执行）：
    python3 scripts/guard_changelog.py

退出码 0 表示清洗成功（无解析失败、条数无异常、feed 已同步）。
"""
import hashlib
import json
import os
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


# ── 条数暴跌护栏（2026-09-17 加）────────────────────────────────────────
# 背景：提交 48c1e092（2026-09-02，message 只有「🌀 台风实时监测刷新」）把
# data/changelog.json 从 435 条砍到 40 条、static 侧同样砍，diff 1640 行全是删除；
# 5 天后的 0d69aeca 又把 80 条砍到 60 条。两次都没被任何护栏拦住，
# 最终结果就是更新日志页只剩 17 天记录，而页面自称「记录每次进化轨迹」。
# 旧 clean() 只删空 content，对「条数大面积减少」零感知。
#
# 这里补一道：与上一个提交比，条数掉 15 条以上且掉幅超 20% 就阻断提交。
# 正常清理（例如 2026-08-17 有意清 104 条空记录，169→94）也会命中，
# 所以留了显式放行开关 —— 确认是有意为之就带上环境变量再提交：
#     CHANGELOG_ALLOW_SHRINK=1 git commit ...
SHRINK_MIN_ITEMS = 15
SHRINK_MIN_RATIO = 0.20


def _count_in_head(path: str) -> int | None:
    """读上一个提交里该文件的条数；取不到（新文件/git 不可用）返回 None。"""
    import subprocess
    try:
        out = subprocess.run(
            ["git", "show", f"HEAD:{path}"],
            capture_output=True, text=True, timeout=20,
        )
        if out.returncode != 0:
            return None
        data = json.loads(out.stdout)
        return len(data) if isinstance(data, list) else None
    except Exception:
        return None


def is_shrink(old: int, now: int,
              min_items: int = SHRINK_MIN_ITEMS,
              min_ratio: float = SHRINK_MIN_RATIO) -> bool:
    """条数是否属「异常暴跌」。抽成纯函数，方便单测（见 --self-test）。"""
    if old <= 0 or now >= old:
        return False
    drop = old - now
    return drop >= min_items and drop / old >= min_ratio


def check_shrink() -> list[str]:
    if os.environ.get("CHANGELOG_ALLOW_SHRINK"):
        print("  ⚠️ 已设 CHANGELOG_ALLOW_SHRINK=1，跳过条数暴跌检查（请确认确属有意清理）")
        return []
    bad = []
    for path in TARGETS:
        try:
            now = len(json.load(open(path, encoding="utf-8")))
        except Exception:
            continue
        old = _count_in_head(path)
        if old is None or old == 0:
            continue
        if is_shrink(old, now):
            print(f"  🔴 条数暴跌: {path}  {old} → {now}（少 {old - now} 条，"
                  f"{(old - now) / old * 100:.0f}%）")
            bad.append(path)
    if bad:
        print("  ⛔ 疑似被脚本覆盖式重写，已阻断提交。")
        print("     确认是有意清理，请重新执行并带上 CHANGELOG_ALLOW_SHRINK=1。")
    else:
        print("  ✅ 条数无异常下跌")
    return bad


def self_test() -> int:
    """判定逻辑自测（不碰真实文件）。"""
    cases = [
        # (old, now, 期望拦截, 说明)
        (435, 40, True, "复现 2026-09-02 事故：435 → 40"),
        (80, 60, True, "复现 2026-09-05 二次截断：80 → 60"),
        (169, 94, True, "2026-08-17 有意清 104 条空记录：169 → 94（需显式放行）"),
        (653, 640, False, "正常小幅清理：653 → 640"),
        (238, 653, False, "历史恢复（条数上升）"),
        (30, 20, False, "小体量下跌未达条数门槛：30 → 20"),
        (653, 653, False, "无变化"),
    ]
    ok = True
    for old, now, want, desc in cases:
        got = is_shrink(old, now)
        flag = "✅" if got == want else "❌"
        if got != want:
            ok = False
        print(f"  {flag} {desc}  →  拦截={got}（期望 {want}）")
    print("  " + ("全部通过" if ok else "有不符预期的用例"))
    return 0 if ok else 1


def build_feed() -> list[str]:
    """保持更新日志 feed 与页面静态回退最新（改完数据忘跑脚本 = 页面停在旧内容）。"""
    import subprocess
    gen = os.path.join(os.path.dirname(os.path.abspath(__file__)), "build_changelog_feed.py")
    chk = subprocess.run([sys.executable, gen, "--check"], capture_output=True, text=True)
    if chk.returncode == 0:
        print(chk.stdout.strip())
        return []
    print("  检测到 changelog feed 过期，自动重建…")
    run = subprocess.run([sys.executable, gen], capture_output=True, text=True)
    sys.stdout.write(run.stdout)
    if run.returncode != 0:
        print(run.stderr)
        print("  ⛔ feed 重建失败")
        return ["build_changelog_feed"]
    return []


def verify_identical() -> list[str]:
    """同步后回读三副本，确认字节完全一致。
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
    if "--self-test" in sys.argv:
        print("=== changelog 护栏：条数暴跌判定自测 ===")
        sys.exit(self_test())

    print("=== changelog 护栏：开始清洗空记录 ===")
    failures = []
    for t in TARGETS:
        msg = clean(t)
        print("  " + msg)
        if "失败" in msg or "异常" in msg:
            failures.append(t)
    print("=== 清洗完成 ===")

    # —— 条数暴跌检查（2026-09-17 加，专治「机器人脚本覆盖式重写」）——
    print("=== changelog 条数暴跌检查 ===")
    failures.extend(check_shrink())

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

    # —— 更新日志 feed / 页面静态回退（2026-09-17 接入）——
    # 数据改完忘跑 build_changelog_feed.py，页面就停在旧内容上。
    # 自动任务天天往 changelog 里追加条目，靠人记得跑不现实，故在此自愈。
    print("=== changelog feed 同步 ===")
    failures.extend(build_feed())

    sys.exit(1 if failures else 0)
