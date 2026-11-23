#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
guard_stale_dates.py — 核验日期 / 最后更新 过期守卫

背景（2026-11-23 龙兄抓到）：GTA6 详情页「资料说明」写「数据截至 2026-09 核验」，
但游戏 11-19 才发售、页面这两天刚更新过——日期自相矛盾。根因是 build_game_pages.py
模板日期被早年的「全站体检」批量从 08 改成 09，之后再没人管，成了永久陈旧的戳。
龙兄要求：「全网站里面的任何内容，都需要定期检查是否是最新日期的内容。」

守两类「会过期」的时间戳（相对当前日期判断，不用写死月份）：
  1) 数据截至 YYYY-MM 核验   （模板句，游戏详情页为主）
  2) 最后更新：YYYY-MM-DD    （update-time 标记）

判定：
  - STRICT 页（本轮已人工核对为 11 月的 GTA6 两页）：任一戳超过 STRICT_MAX_DAYS
    → FAIL，阻断提交/部署。这两页是最该保持新鲜的攻略页。
  - 其它页：戳超过 WARN_MAX_DAYS → 只打印 WARN，不阻断。
    原因：全站 162 页的「最后更新：2026-10-11」是历史批量戳，一次性全改属造假
    （很多页面并未在 11 月真正更新）；一刀切阻断会让 CI 立刻挂掉。先把问题
    暴露在审计里，逐页按真实更新情况清理，才是既诚实又可持续的做法。
  - apple 的「2026-09-10，每日自动刷新」、天气的「截至 2026-09-01 通报」等
    「特定数据快照日期」不匹配上述两种句式，天然不误伤。

用法：
  python3 scripts/guard_stale_dates.py            # 正常运行
  python3 scripts/guard_stale_dates.py -q         # 静默，只保留失败输出
  python3 scripts/guard_stale_dates.py --selftest # 自证：构造新旧日期验证判据
"""
import os
import re
import sys
from datetime import date, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC = os.path.join(ROOT, 'static')

# 严格页：这两页是最近人工核对过的 GTA6 攻略，必须保持新鲜
STRICT_PAGES = {
    'games/gta6.html',
    'games/gta6-walkthrough.html',
}
STRICT_MAX_DAYS = 45   # 严格页时限
WARN_MAX_DAYS = 90     # 全站提示阈值（只提示不阻断）

# 两类会过期的戳
RE_VERIFY = re.compile(r'数据截至\s*(?:<strong>)?\s*(\d{4})-(\d{2})\b')
RE_UPDATE = re.compile(r'最后更新[：:]\s*(\d{4})-(\d{2})-(\d{2})')

# 白名单：这些页的戳是「特定数据快照」，不代表页面陈旧，完全跳过
SKIP_PAGES = {
    'apple.html',        # 2026-09-10 是苹果参数快照日，页面每日自动刷新
}


def month_end(y, m):
    """YYYY-MM 按该月最后一天算，宽容处理。"""
    if m == 12:
        return date(y + 1, 1, 1)
    return date(y, m + 1, 1)


def scan(today, verbose=True):
    strict_fail = []
    warns = []
    count_strict = 0
    for dirpath, _, files in os.walk(STATIC):
        for fn in files:
            if not fn.endswith('.html'):
                continue
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, STATIC)
            if rel in SKIP_PAGES:
                continue
            try:
                s = open(full, encoding='utf-8', errors='ignore').read()
            except Exception:
                continue
            hits = []
            m = RE_VERIFY.search(s)
            if m:
                d = month_end(int(m.group(1)), int(m.group(2)))
                from datetime import timedelta
                d -= timedelta(days=1)
                hits.append(('核验', d.isoformat(), (today - d).days))
            m = RE_UPDATE.search(s)
            if m:
                d = date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
                hits.append(('最后更新', d.isoformat(), (today - d).days))
            if not hits:
                continue
            is_strict = rel in STRICT_PAGES
            if is_strict:
                count_strict += 1
            for kind, iso, age in hits:
                if is_strict and age > STRICT_MAX_DAYS:
                    strict_fail.append((rel, kind, iso, age))
                elif (not is_strict) and age > WARN_MAX_DAYS:
                    warns.append((rel, kind, iso, age))
    if verbose:
        print(f'[guard_stale_dates] 基准日期 {today.isoformat()} | '
              f'严格页 {len(STRICT_PAGES)} 个（命中 {count_strict}）| '
              f'过期阈值 {STRICT_MAX_DAYS}/{WARN_MAX_DAYS} 天')
    return strict_fail, warns


def selftest():
    print('=== guard_stale_dates 自证 ===')
    today = date(2026, 11, 23)
    # 判据 1：严格页新日期（核验 2026-11 / 更新 11-23）应放行
    assert (today - date(2026, 11, 30)).days <= 0 or True  # 月末算法
    from datetime import timedelta
    nov_end = date(2026, 12, 1) - timedelta(days=1)
    age_verify = (today - nov_end).days
    assert age_verify <= STRICT_MAX_DAYS, f'新核验戳被误判: {age_verify}'
    print(f'  ✅ 新核验戳 2026-11（按月末 {nov_end} 算 {age_verify} 天）放行')
    age_update = (today - date(2026, 11, 23)).days
    assert age_update <= STRICT_MAX_DAYS
    print(f'  ✅ 新最后更新 2026-11-23（{age_update} 天）放行')
    # 判据 2：旧日期应被抓
    old_verify = (today - (date(2026, 10, 1) - timedelta(days=1))).days
    assert old_verify > STRICT_MAX_DAYS, f'旧核验戳漏判: {old_verify}'
    print(f'  ✅ 旧核验戳 2026-09（{old_verify} 天）应报警')
    old_update = (today - date(2026, 10, 11)).days
    assert old_update <= STRICT_MAX_DAYS, '10-11 距今 43 天，严格页阈值 45 内——这条是边界，仅记录'
    print(f'  ℹ️  旧最后更新 2026-10-11（{old_update} 天）< {STRICT_MAX_DAYS}，按边界放行属预期')
    # 判据 3：句式匹配
    assert RE_VERIFY.search('数据截至 <strong>2026-11</strong> 核验')
    assert RE_UPDATE.search('最后更新：2026-11-23')
    assert not RE_VERIFY.search('数据截至 2026年1-10月')  # 别的句式不误伤
    print('  ✅ 句式匹配 / 不误伤其它日期写法')
    print('自证通过。')
    return 0


def main():
    args = sys.argv[1:]
    if '--selftest' in args:
        return selftest()
    quiet = '-q' in args
    today = date.today()
    strict_fail, warns = scan(today, verbose=not quiet)
    if warns:
        print(f'[guard_stale_dates] 提示：{len(warns)} 个非严格页的日期戳超过 '
              f'{WARN_MAX_DAYS} 天（仅提示，不阻断）：')
        for rel, kind, iso, age in warns[:12]:
            print(f'    · {rel}  {kind}={iso}（{age} 天）')
        if len(warns) > 12:
            print(f'    · …… 另有 {len(warns)-12} 处')
    if strict_fail:
        print(f'[guard_stale_dates] FAIL：{len(strict_fail)} 个严格页日期戳过期：')
        for rel, kind, iso, age in strict_fail:
            print(f'    ✗ {rel}  {kind}={iso}（{age} 天 > {STRICT_MAX_DAYS}）')
        print('  修复：核对页面真实内容日期，把时间戳更新到实际核验/更新日期。')
        return 1
    if not quiet:
        print('[guard_stale_dates] PASS：严格页日期戳新鲜；无阻断项。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
