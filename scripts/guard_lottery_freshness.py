#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
guard_lottery_freshness.py — 彩票开奖数据新鲜度 / 真实性守卫

背景（2026-11-24 龙兄：「看看彩票板块的数据更新的对不对？」）：
旧抓取脚本用第三方聚合 api.huiniao.top，11 月中旬起停更（双色球卡在
2026130 / 11-12，其余三种卡在 11-14）。但彩票刷新工作流每天照跑，
把四个 JSON 的 updated 无条件写成「运行当天」——页面就显示
「最近更新 2026-11-24」，实际开奖号还是 10 天前的。典型的装饰性时间戳。

本守卫把三件事做成硬闸：
  1. updated / meta.last / draws[-1].d 必须一致，且等于**真实最新开奖日**；
  2. 全量历史按（日期, 期号）升序、期号不重复、号码数量与范围合法
     （福彩3D / 排列3 的百十个位不校验升序，只校验范围）；
  3. 最新开奖日距今不得超过 7 天，也不得是未来日期。

用法：
  python3 scripts/guard_lottery_freshness.py                # 正常运行
  python3 scripts/guard_lottery_freshness.py -q             # 静默
  python3 scripts/guard_lottery_freshness.py --today=2026-11-24  # 指定基准日（自证用）
  python3 scripts/guard_lottery_freshness.py --selftest     # 内置自证
"""
import datetime
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOTTERY_DIR = os.path.join(ROOT, "static", "data", "lottery")
TIDS = ("ssq", "dlt", "fc3d", "pls")
MAX_LAG_DAYS = 7


def validate(obj, today):
    """返回 (errors, info)；纯函数，便于 selftest 直接构造样例。"""
    errors = []
    for key in ("type", "name", "updated", "meta", "groups", "draws"):
        if key not in obj:
            errors.append("缺少顶层字段 %s" % key)
    if errors:
        return errors, {}

    draws = obj["draws"]
    meta = obj["meta"] or {}
    groups = obj["groups"] or []
    if not isinstance(draws, list) or not draws:
        return ["draws 为空或不是数组"], {}

    last = draws[-1]
    updated = str(obj.get("updated", ""))
    meta_last = str(meta.get("last", ""))
    real_last = str(last.get("d", ""))
    if updated != real_last:
        errors.append("updated=%s 与真实最新开奖日 %s 不一致（疑似装饰性时间戳）"
                      % (updated, real_last))
    if meta_last != real_last:
        errors.append("meta.last=%s 与真实最新开奖日 %s 不一致" % (meta_last, real_last))
    if meta.get("draws") != len(draws):
        errors.append("meta.draws=%s 与实际期数 %d 不一致" % (meta.get("draws"), len(draws)))
    if meta.get("first") != draws[0].get("d"):
        errors.append("meta.first=%s 与首期日期 %s 不一致"
                      % (meta.get("first"), draws[0].get("d")))

    # 升序 + 期号唯一
    for k in range(len(draws) - 1):
        a = (str(draws[k].get("d", "")), str(draws[k].get("i", "")))
        b = (str(draws[k + 1].get("d", "")), str(draws[k + 1].get("i", "")))
        if a > b:
            errors.append("第 %d/%d 条排序错乱：%s > %s" % (k + 1, k + 2, a, b))
            break
    issues = [str(x.get("i", "")) for x in draws]
    if len(set(issues)) != len(issues):
        errors.append("期号重复 %d 条" % (len(issues) - len(set(issues))))

    # 号码数量 / 范围
    bad = []
    for x in draws:
        for g in groups:
            arr = x.get(g.get("key")) or []
            if len(arr) != g.get("cnt") or any(
                    not (g["lo"] <= n <= g["hi"]) for n in arr):
                bad.append((x.get("i"), g.get("key")))
                break
    if bad:
        errors.append("号码越界/数量不符 %d 期，例：%s" % (len(bad), bad[:3]))

    # 新鲜度
    lag = None
    try:
        day = datetime.date.fromisoformat(real_last)
        lag = (today - day).days
        if lag < 0:
            errors.append("最新开奖日 %s 是未来日期" % real_last)
        elif lag > MAX_LAG_DAYS:
            errors.append("最新开奖日 %s 距今 %d 天，超过 %d 天阈值——"
                          "数据源疑似停更，不要用当天刷时间戳" %
                          (real_last, lag, MAX_LAG_DAYS))
    except ValueError:
        errors.append("最新开奖日 %s 不是合法 YYYY-MM-DD" % real_last)

    return errors, {"last": real_last, "issue": last.get("i"), "lag": lag,
                    "count": len(draws)}


def check(today):
    errors, infos = [], {}
    for tid in TIDS:
        path = os.path.join(LOTTERY_DIR, tid + ".json")
        if not os.path.exists(path):
            errors.append("%s: 数据文件不存在 %s" % (tid, path))
            continue
        try:
            obj = json.load(open(path, encoding="utf-8"))
        except Exception as e:
            errors.append("%s: JSON 解析失败 %s" % (tid, e))
            continue
        err, info = validate(obj, today)
        for e in err:
            errors.append("%s: %s" % (tid, e))
        infos[tid] = info
    return errors, infos


def make_sample(today):
    day = (today - datetime.timedelta(days=1)).isoformat()
    return {
        "type": "ssq", "name": "双色球", "updated": day,
        "meta": {"draws": 2, "first": "2026-11-21", "last": day, "skipped": 0},
        "groups": [
            {"key": "r", "label": "红球", "lo": 1, "hi": 33, "cnt": 6},
            {"key": "b", "label": "蓝球", "lo": 1, "hi": 16, "cnt": 1},
        ],
        "draws": [
            {"i": "2026133", "d": "2026-11-21", "r": [1, 2, 3, 4, 5, 6], "b": [1]},
            {"i": "2026134", "d": day, "r": [7, 8, 9, 10, 11, 12], "b": [2]},
        ],
    }


def selftest():
    import copy
    ok = True
    today = datetime.date(2026, 11, 24)

    def t(name, cond):
        nonlocal ok
        print(("  OK   " if cond else "  FAIL ") + name)
        ok = ok and cond

    print("=== guard_lottery_freshness selftest ===")
    sample = make_sample(today)
    err, _ = validate(sample, today)
    t("正常样本通过", not err)

    x = copy.deepcopy(sample)
    x["updated"] = "2026-11-24"
    t("识别假时间戳（updated 刷成运行日）", any("updated" in e for e in validate(x, today)[0]))

    x = copy.deepcopy(sample)
    x["meta"]["last"] = "2026-11-24"
    t("识别 meta.last 与真实开奖日不一致", any("meta.last" in e for e in validate(x, today)[0]))

    x = copy.deepcopy(sample)
    x["draws"][-1]["d"] = "2026-11-10"
    x["meta"]["last"] = "2026-11-10"
    x["updated"] = "2026-11-10"
    t("识别数据源停更超阈值", any("停更" in e for e in validate(x, today)[0]))

    x = copy.deepcopy(sample)
    x["draws"] = list(reversed(x["draws"]))
    t("识别排序错乱", any("排序" in e for e in validate(x, today)[0]))

    x = copy.deepcopy(sample)
    x["draws"][-1]["r"][0] = 99
    t("识别号码越界", any("越界" in e for e in validate(x, today)[0]))

    x = copy.deepcopy(sample)
    x["meta"]["draws"] = 999
    t("识别 meta.draws 不匹配", any("meta.draws" in e for e in validate(x, today)[0]))

    x = copy.deepcopy(sample)
    x["draws"][-1]["d"] = "2026-11-30"
    x["meta"]["last"] = "2026-11-30"
    x["updated"] = "2026-11-30"
    t("识别未来日期", any("未来日期" in e for e in validate(x, today)[0]))

    print("=== " + ("selftest 全绿 ✅" if ok else "selftest 失败 ❌") + " ===")
    return 0 if ok else 1


def main():
    args = sys.argv[1:]
    if "--selftest" in args:
        return selftest()
    quiet = "-q" in args
    today = datetime.date.today()
    for a in args:
        if a.startswith("--today="):
            today = datetime.date.fromisoformat(a.split("=", 1)[1])
    errors, infos = check(today)
    if not quiet:
        print("=== 彩票数据新鲜度（基准日 %s，阈值 %d 天）===" % (today, MAX_LAG_DAYS))
        for tid in TIDS:
            i = infos.get(tid)
            if i:
                print("  %-5s 最新 %s / 第 %s 期 / %d 条 / 距今 %s 天" %
                      (tid, i["last"], i["issue"], i["count"], i["lag"]))
    if errors:
        print("❌ 彩票数据守卫失败：%d 处" % len(errors))
        for e in errors:
            print("  " + e)
        return 1
    if not quiet:
        print("✅ 四种彩票数据日期真实、未过期、格式合法")
    return 0


if __name__ == "__main__":
    sys.exit(main())
