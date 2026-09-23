#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
guard_news_length.py — 板块新闻「摘要 / 详情」分层守卫。

背景（2026-09-24）
────────────────────────────────────────────────────────────────
龙兄反馈：「我感觉所有每天更新的新闻，内容都很多，感觉都是照搬原网址的新闻」。

逐条查过之后，问题不是照搬——88 条里 89% 带 sources 数组、平均 3.1 个源，
89% 正文里写着「交叉/核查」这类跨源措辞，照搬标记词（据悉/本文/版权归/
转载请注明/摘编/转自）全站 0 命中。甚至有一条自己标注了
「上述聚合站点措辞高度雷同，同源概率高，按 1 个源计」。

真正的问题是**颗粒度**：自动化提示词里写的要求是 `content(50-100字摘要)`，
实测平均 612 字、最长 2358 字，**超了 6–23 倍**。也就是说稿子本身没问题，
是「该写多长」这条规矩从来没被守过，于是板块页变成一篇篇改写过的新闻稿。

改法（两字段分层，见 static/js/auto_news_loader.js）
────────────────────────────────────────────────────────────────
  summary  60–160 字   ← 读者在板块页一眼看到的那段（默认只显示它）
  content  完整正文    ← 折叠在「展开详情」里，想看细节才点开

本脚本守的就是这个分层不许回退。判据（逐条 news 项）：

  ① 必须有 summary，去掉空白后非空
  ② summary 字数落在 MIN..MAX 之间（写作目标 80–120，留出余量给正常波动）
  ③ summary 不得含换行 —— 它的定位是「一句话看完」，带换行会膨胀成小正文
  ④ content 必须非空 —— 折叠区不能是空的（否则按钮点开一片空白）
  ⑤ summary 不得比 content 还长 —— 那说明两层搞反了。
     相等是允许的（简讯这类一短条，没有可折叠的细节，渲染器会自动不出按钮）

另有「不阻断、只提醒」的一项：
  · content 超过 1500 字会打印出来。折叠区是给人**主动**点开的，长一点不算错
    （读者点开就是想看细节），所以不做硬失败；但长到上千字通常意味着
    「又照搬了一篇通稿」，值得看一眼。这个提醒也是新提示词写「详情 ≤ 800 字」的依据。

用法
────────────────────────────────────────────────────────────────
  python3 scripts/guard_news_length.py              # 全量检查
  python3 scripts/guard_news_length.py -q           # 只输出结论（pre-commit 用）
  python3 scripts/guard_news_length.py --selftest   # 正反两向自证（改判据后先跑这个）
"""
import argparse
import glob
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC = os.path.join(ROOT, "static")

# 目标：新闻数据文件（含子目录里那一个）
PATTERNS = [
    os.path.join(STATIC, "*-news.json"),
    os.path.join(STATIC, "tesla", "fsd-news.json"),
]

MIN_SUMMARY = 50
MAX_SUMMARY = 180
CONTENT_WARN = 1500


def zh_len(s):
    """字数：去掉所有空白后按字符计（中文一个字算一个，标点照算）。

    不区分全角/半角 —— 摘要里难免有「2026-09-24」「1556 万元」这类半角串，
    为它们单独折算反而让人写稿时算不清。
    """
    return len(re.sub(r"\s+", "", str(s or "")))


def check_item(item):
    """返回 (errors, warnings)；errors 为空即这条合规。"""
    errors = []
    warnings = []

    if not isinstance(item, dict):
        return ["条目不是对象：%r" % (item,)], warnings

    raw_sum = item.get("summary")
    raw_body = item.get("content")

    if raw_sum is None or not str(raw_sum).strip():
        errors.append("缺 summary（板块页上读者看不到这条的内容）")
        sum_len = 0
    else:
        sum_len = zh_len(raw_sum)
        if "\n" in str(raw_sum) or "\r" in str(raw_sum):
            errors.append("summary 含换行（摘要要能一句话看完，请写成单段）")
        if sum_len < MIN_SUMMARY:
            errors.append("summary 只有 %d 字，少于下限 %d 字（太短＝没把事说清）" % (sum_len, MIN_SUMMARY))
        elif sum_len > MAX_SUMMARY:
            errors.append("summary 有 %d 字，超过上限 %d 字（又变成正文了）" % (sum_len, MAX_SUMMARY))

    if raw_body is None or not str(raw_body).strip():
        errors.append("content 为空（折叠区点开会是空白）")
        body_len = 0
    else:
        body_len = zh_len(raw_body)
        if sum_len and sum_len > body_len:
            errors.append(
                "summary(%d 字) 比 content(%d 字) 还长 —— 两层写反了" % (sum_len, body_len)
            )
        if body_len > CONTENT_WARN:
            warnings.append("content %d 字（折叠区，不阻断；通常意味着又照搬了一篇通稿）" % body_len)

    return errors, warnings


def collect_files():
    out, seen = [], set()
    for pat in PATTERNS:
        for p in sorted(glob.glob(pat)):
            if p not in seen:
                seen.add(p)
                out.append(p)
    return out


def load_news(path):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        return []
    news = data.get("news") or []
    return news if isinstance(news, list) else []


def label_of(item, idx):
    """给一条新闻起个能定位的名字：优先 date + 正文开头。"""
    date = str((item or {}).get("date", "")).strip() or "第 %d 条" % (idx + 1)
    text = str((item or {}).get("summary") or (item or {}).get("content") or "").strip()
    text = re.sub(r"\s+", " ", text)[:34]
    return "%s  %s%s" % (date, text, "…" if len(text) >= 34 else "")


def scan():
    """返回 (总条数, 文件数, errors, warnings)。"""
    errors, warns, total, nfiles = [], [], 0, 0
    for path in collect_files():
        rel = os.path.relpath(path, ROOT)
        try:
            news = load_news(path)
        except Exception as e:  # noqa: BLE001
            errors.append("  [%s] JSON 解析失败: %s" % (rel, e))
            continue
        if not news:
            continue
        nfiles += 1
        total += len(news)
        for i, item in enumerate(news):
            errs, wws = check_item(item)
            for e in errs:
                errors.append("  [%s · %s]\n      %s" % (rel, label_of(item, i), e))
            for w in wws:
                warns.append("  [%s · %s]\n      %s" % (rel, label_of(item, i), w))
    return total, nfiles, errors, warns


# ── 自证：拿合成数据验判据本身，不依赖仓库当前内容 ────────────────────
def selftest():
    ok_sum = "甲" * 100
    ok_body = "乙" * 700
    cases = [
        # (说明, item, 期望是否合规)
        ("合规条目", {"summary": ok_sum, "content": ok_body}, True),
        ("缺 summary", {"content": ok_body}, False),
        ("summary 为空白", {"summary": "   ", "content": ok_body}, False),
        ("summary 过短", {"summary": "甲" * 20, "content": ok_body}, False),
        ("summary 过长", {"summary": "甲" * 200, "content": "乙" * 900}, False),
        ("summary 带换行", {"summary": "甲" * 60 + "\n" + "甲" * 60, "content": ok_body}, False),
        ("content 为空", {"summary": ok_sum, "content": "  "}, False),
        ("两层写反", {"summary": "甲" * 120, "content": "乙" * 80}, False),
        ("摘要与正文等长（允许，渲染器不出按钮）", {"summary": "甲" * 60, "content": "甲" * 60}, True),
        ("边界：正好下限", {"summary": "甲" * MIN_SUMMARY, "content": ok_body}, True),
        ("边界：正好上限", {"summary": "甲" * MAX_SUMMARY, "content": "乙" * 900}, True),
        ("边界：下限少 1 字", {"summary": "甲" * (MIN_SUMMARY - 1), "content": ok_body}, False),
        ("边界：上限多 1 字", {"summary": "甲" * (MAX_SUMMARY + 1), "content": "乙" * 900}, False),
    ]
    print("=" * 60)
    print("guard_news_length 自证 --selftest")
    print("=" * 60)
    bad = 0
    for desc, item, expect_ok in cases:
        errs, _ = check_item(item)
        got_ok = not errs
        mark = "✅" if got_ok == expect_ok else "❌"
        if got_ok != expect_ok:
            bad += 1
        print("%s %-38s 期望%s / 实得%s%s" % (
            mark, desc,
            "合规" if expect_ok else "不合规",
            "合规" if got_ok else "不合规",
            "" if got_ok == expect_ok else "   → " + "；".join(errs),
        ))
    print("-" * 60)
    if bad:
        print("[FAIL] 自证 %d 例不符，判据本身有问题" % bad)
        return 1
    print("[PASS] 自证 %d 例全部符合预期" % len(cases))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-q", "--quiet", action="store_true", help="只输出结论行")
    ap.add_argument("--selftest", action="store_true", help="跑判据自证")
    args = ap.parse_args()

    if args.selftest:
        return selftest()

    total, nfiles, errors, warns = scan()

    if not args.quiet:
        print("=" * 60)
        print("板块新闻摘要/详情分层守卫 guard_news_length")
        print("=" * 60)

    if errors:
        print("[FAIL] %d 条新闻的摘要/详情分层不合规：" % len(errors))
        print("       判定规则：summary 必须存在、单段、%d–%d 字；content 必须非空、不短于 summary。" % (MIN_SUMMARY, MAX_SUMMARY))
        print("       写作目标 80–120 字（这里留余量，不按目标值卡）。\n")
        for line in errors:
            print(line)
        print("\n修法：给每条新闻补/改 summary —— 只压缩原文，不引入原文没有的事实，")
        print("     关键数字（金额/日期/票房/文号）与「待官方确认」标记必须保留。")
        return 1

    if warns and not args.quiet:
        print("[提醒] %d 条正文偏长（不阻断部署）：\n" % len(warns))
        for line in warns:
            print(line)
        print("")

    if not args.quiet:
        print("[PASS] %d 个新闻文件、%d 条新闻：摘要齐全、长度合规、正文非空" % (nfiles, total))
        print("       （覆盖 static/*-news.json 与 static/tesla/fsd-news.json）")
    else:
        print("[guard_news_length] PASS %d 文件 / %d 条" % (nfiles, total))
    return 0


if __name__ == "__main__":
    sys.exit(main())
