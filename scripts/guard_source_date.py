#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
guard_source_date.py — 来源核验日保护守卫

背景（2026-11-23）：全站 72 页的「最后更新：2026-08-07」是内容来源核验日
（有据可查的真实日期），不是 git 提交日。但 CI 的 sync_update_time.py 会按
git 提交日回填日期，批量提交当天把 72 页全刷成 2026-11-23——正是龙兄明确
反对的「装饰性时间戳」，等于把「去伪存真」的成果推倒。

解法：这类页的日期元素打上 data-source-verified 标记，sync_update_time.py
回填时跳过。本守卫保证这套机制不失效：
  1. 每个带标记的 update-time 元素里必须是一个合法日期（YYYY-MM-DD）；
  2. 用 sync_update_time 的真实回填逻辑验证：带标记的日期不会被改动
     （判据同源，避免两套实现各说各话）；
  3. 内置自证 selftest。

用法：
  python3 scripts/guard_source_date.py             # 正常运行
  python3 scripts/guard_source_date.py -q          # 静默，只保留失败输出
  python3 scripts/guard_source_date.py --selftest  # 自证
"""
import glob
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC = os.path.join(ROOT, "static")

# 与 sync_update_time.py 同源：从它导入标记名和回填函数，避免判据漂移
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    import sync_update_time as sut
    MARK = sut.SOURCE_VERIFIED_ATTR
except Exception:  # 兜底常量（正常不会走到）
    MARK = "data-source-verified"

# 匹配带标记的 update-time 开标签一直到日期，捕获日期值
RE_MARKED_DATE = re.compile(
    r'(<[a-z]+[^>]*\bclass="[^"]*\bupdate-time\b[^"]*"[^>]*'
    + re.escape(MARK) + r'[^>]*>[^<]*?)'
    r'(\d{4}-\d{2}-\d{2})'
)
# 只匹配「最后更新：YYYY-MM-DD」来源日句式，用于统计应打标却漏标的页
RE_LAST_UPDATE = re.compile(r'最后更新[：:]\s*(\d{4}-\d{2}-\d{2})')


def check():
    errors = []
    marked_pages, dated_pages = [], []
    for path in sorted(glob.glob(os.path.join(STATIC, "**", "*.html"),
                                 recursive=True)):
        rel = os.path.relpath(path, ROOT)
        try:
            html = open(path, encoding="utf-8").read()
        except Exception:
            continue
        RE_LAST_UPDATE.search(html) and dated_pages.append(rel)

        if MARK not in html:
            continue
        marked_pages.append(rel)
        m = RE_MARKED_DATE.search(html)
        if not m:
            errors.append(f"{rel}: 带 {MARK} 但日期元素内不是合法 YYYY-MM-DD")
            continue
        # 用回填脚本的真实判据验证：这个元素会被识别为「来源核验日」而跳过
        if not sut.has_source_verified(m.group(1)):
            errors.append(f"{rel}: {MARK} 未被回填脚本识别，可能被 CI 覆盖")

    return errors, marked_pages, dated_pages


def selftest():
    ok = True

    def t(name, cond):
        nonlocal ok
        print(("  OK   " if cond else "  FAIL ") + name)
        ok = ok and cond

    print("=== guard_source_date selftest ===")
    t("has_source_verified 识别裸标记",
      sut.has_source_verified(f'<div class="update-time" {MARK}>最后更新：'))
    t("has_source_verified 识别 =1 标记",
      sut.has_source_verified(f'<div class="update-time" {MARK}="1">最后更新：'))
    t("has_source_verified 不误伤无标记",
      not sut.has_source_verified('<div class="update-time">最后更新：'))
    t("has_source_verified 不误伤 -extra",
      not sut.has_source_verified(f'<div class="update-time" {MARK}-extra>最后更新：'))
    t("RE_MARKED_DATE 抓到日期",
      bool(RE_MARKED_DATE.search(
          f'<div class="update-time" {MARK}>最后更新：2026-08-07</div>').group(2)
          == "2026-08-07"))
    t("RE_MARKED_DATE 拒绝非法日期",
      not RE_MARKED_DATE.search(
          f'<div class="update-time" {MARK}>最后更新：昨天</div>'))
    print("=== " + ("selftest 全绿 ✅" if ok else "selftest 失败 ❌") + " ===")
    return 0 if ok else 1


def main():
    args = sys.argv[1:]
    if "--selftest" in args:
        return selftest()
    quiet = "-q" in args
    errors, marked, dated = check()
    if not quiet:
        print(f"=== 来源核验日保护：{len(marked)} 页打了 {MARK} / "
              f"{len(dated)} 页带最后更新日期 ===")
    if errors:
        print(f"❌ 来源核验日守卫失败：{len(errors)} 处")
        for e in errors[:30]:
            print("  " + e)
        return 1
    if not quiet:
        print("✅ 所有来源核验日标记合法且不会被 CI 回填覆盖")
    return 0


if __name__ == "__main__":
    sys.exit(main())
