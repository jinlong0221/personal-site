#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
guard_marvel_status.py — 漫威票房「展示字段」清爽度守卫

背景（2026-11-16 全站审计发现，上轮 11-13 修复回潮）：
────────────────────────────────────────────────────────────────
11-13 刚把 movie.status 压成 67 字单行、movie.boxOffice.china 删掉内部
对账说明；但 11-15 的自动更新又写回 119 字（塞进「索尼冲奥概率 0.46%」
「12/4 北美加长重映版」这类附加从句），china 字段重新混入
「猫眼实时 14.97 亿为分账口径差异、不采用」——这是内部对数的话，
不该给访客看。

根因：自动化提示词里「一行、禁附加从句」的规则**还在**，但只靠 LLM
自觉遵守，没有技术强制，某次执行没遵守就回潮了。本守卫把它变成硬闸。

判据（只查 movie.status 与 movie.boxOffice 四字段，不碰 milestones/note/sources）：
  ① status 长度 ≤ MAX_STATUS（80 字），超出即 FAIL
  ② status 不含分号拼接（「；」/「;」）—— 规则明确禁「｜」/「；」拼历史
  ③ status 禁附加从句关键词：冲奥/重映/加长/数字版/实体版/视频平台/Netflix/
     iTunes/概率/定档 —— 这些属于「事件动态」，不是当日票房口径，应进新闻板
  ④ status 必须以「。」结尾、恰好一句话（不含「｜」）
  ⑤ boxOffice 四字段禁内部对账话术：不采用/分账口径差异/单源快照/留痕不采用/
     不予采用/待核 —— 这些是内部判断，不该显示给访客
  ⑥ boxOffice 四字段各自单行（不含换行符 \n）

长文/流水只允许留在 milestones / note / sources 字段（页面已隐藏，JSON 留底）。

自证：python3 scripts/guard_marvel_status.py --selftest
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TARGET = os.path.join(ROOT, "static", "marvel-boxoffice.json")

MAX_STATUS = 80
# status 里不允许出现的「附加从句 / 事件动态」词（这些应写在新闻板，不写进票房口径）
STATUS_BAN = ["冲奥", "重映", "加长", "数字版", "实体版", "视频平台", "网播",
              "Netflix", "iTunes", "概率", "定档", "提名"]
# boxOffice 展示字段里不允许出现的「内部对账判断」话术
BO_BAN = ["不采用", "不予采用", "留痕不采用", "分账口径差异", "单源快照",
          "单源", "待核", "存疑", "交叉确认", "本轮", "本站"]
BO_FIELDS = ("worldwide", "domestic", "international", "china")


def check(data):
    """返回错误列表。供 main 与 selftest 共用。"""
    errors = []
    movie = data.get("movie", {}) if isinstance(data, dict) else {}
    status = movie.get("status", "")

    if not isinstance(status, str) or not status.strip():
        errors.append("movie.status 为空或非字符串")
    else:
        if len(status) > MAX_STATUS:
            errors.append(f"movie.status 超长 {len(status)} 字（上限 {MAX_STATUS}）——"
                          f"当日票房口径应只写一行摘要，事件动态写进新闻板")
        for sep in ("；", ";", "｜", "|"):
            if sep in status:
                errors.append(f"movie.status 含拼接分隔符「{sep}」——严禁用它拼历史/多件事")
        for w in STATUS_BAN:
            if w in status:
                errors.append(f"movie.status 含附加从句词「{w}」——事件动态不属于当日票房口径")
        if not status.rstrip().endswith("。"):
            errors.append("movie.status 应以句号「。」结尾（一条完整的一句话）")

    box = movie.get("boxOffice", {})
    for field in BO_FIELDS:
        val = box.get(field, "")
        if not isinstance(val, str):
            continue  # 字段缺失/非字符串由其它校验管，本守卫只查文案
        for w in BO_BAN:
            if w in val:
                errors.append(f"movie.boxOffice.{field} 含内部对账话术「{w}」——"
                              f"这是内部判断，不该显示给访客")
        if "\n" in val or "\\n" in val:
            errors.append(f"movie.boxOffice.{field} 含换行——四字段应各只保留一行最新口径")
    return errors


def selftest():
    """正反两向自证：违规样本必须被抓、合规样本必须放行。"""
    good = {
        "movie": {
            "status": "【11/15】全球 $2.52B／北美 $959M／海外 $1.56B／内地 ¥15.87亿，稳居 2026 年度冠军、全球影史第三。",
            "boxOffice": {
                "worldwide": "【11/15】全球累计 $2.52B（影史第三、2026 年度冠军）。",
                "domestic": "【11/15】北美 $959M（年度第一、影史第一）。",
                "international": "【11/15】海外 $1.56B。",
                "china": "【11/15】中国内地 ¥15.87亿（海外最大票仓）。",
            },
        }
    }
    assert check(good) == [], f"合规样本被误判: {check(good)}"

    bad_status = json.loads(json.dumps(good))
    bad_status["movie"]["status"] = ("【11/15】全球 $2.52B／北美 $959M／海外 $1.56B／内地 ¥15.87亿，"
                                     "影史第三+2026年度冠军；索尼启动冲奥（Deadline称最佳影片提名概率0.46%）"
                                     "并定档12/4北美加长重映版（含约10分钟未公开画面）。")
    e = check(bad_status)
    assert any("超长" in x for x in e), "未抓到超长"
    assert any("拼接分隔符" in x for x in e), "未抓到分号拼接"
    assert any("附加从句词" in x for x in e), "未抓到附加从句"

    bad_china = json.loads(json.dumps(good))
    bad_china["movie"]["boxOffice"]["china"] = (
        "【11/15】中国内地 ¥15.87亿（≈¥15.86亿最终口径，海外最大票仓，"
        "猫眼11-15实时14.97亿为分账口径差异、不采用）。")
    e = check(bad_china)
    assert any("boxOffice.china" in x and "内部对账话术" in x for x in e), "未抓到内部对账"

    print("[selftest PASS] 合规样本放行；超长/分号拼接/附加从句/内部对账 4 类违规均被拦截")


def main():
    if "--selftest" in sys.argv:
        selftest()
        return 0
    quiet = "-q" in sys.argv
    if not os.path.exists(TARGET):
        if not quiet:
            print(f"[guard_marvel_status] 跳过：{TARGET} 不存在")
        return 0
    try:
        data = json.load(open(TARGET, encoding="utf-8"))
    except Exception as e:
        print(f"❌ marvel-boxoffice.json 解析失败: {e}")
        return 1

    errors = check(data)
    if errors:
        print("❌ guard_marvel_status 未通过：")
        for e in errors:
            print("   -", e)
        print("   修法：status 只写一行当日票房口径（≤80字、句号结尾、无附加从句）；")
        print("         事件动态写进 marvel-news.json；内部对数话术只留 note/milestones/sources。")
        return 1

    if not quiet:
        print("[PASS] 漫威票房展示字段清爽：status 单行合规、四宫格无内部对账话术")
    else:
        print("[guard_marvel_status] PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
