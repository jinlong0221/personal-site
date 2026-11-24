#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fetch_lottery_history.py — 从官方源抓取四种彩票开奖，增量合并进静态 JSON。

## 数据源（2026-11-24 重写）
旧源 api.huiniao.top 是第三方聚合，2026-11 中旬起停更（双色球卡在 2026130
期 / 11-12），导致网站数据陈旧 10+ 天、但 updated 却天天刷成当天——假时间戳。
改用两家**官方**接口，且带数据新鲜度自检：

  - 福彩（双色球 ssq / 福彩3D 3d）：
      https://www.cwl.gov.cn/cwl_admin/front/cwlkj/search/kjxx/findDrawNotice
      参数 name=<ssq|3d>&issueCount=<N>
  - 体彩（大乐透 gameNo=85 / 排列3 gameNo=35）：
      https://webapi.sporttery.cn/gateway/lottery/getHistoryPageListV1.qry
      参数 gameNo=<85|35>&pageSize=<N>&pageNo=1&isVerify=1
      ⚠️ 2026-11-24：该接口的安全策略会拦截 GitHub 海外服务器 IP，
      故加中彩网官方合作数据接口做备用源（jc.zhcw.com，字段已与官方交叉核对）。

## 合并策略
保留本地已有全量历史（不推倒重建，避免历史数据差异），只拉官方最近 N 期：
  - 官方有新期号 → 追加；
  - 官方与本地同一期号号码不一致 → 以官方为准覆盖并打印警告（官方是一手源）；
  - 号码越界/缺失 → 剔除该条，绝不写入脏数据或伪造。
排序：按日期升序、同日按期号升序（与既有结构一致）。
updated = meta.last = 真实最新开奖日（**不是运行当天**）——旧脚本无论有没有新开奖
都把 updated 写成当天，导致访客看到「最近更新 今天」而实际数据停在两周前。
数据源自身超过 7 天没出新期 → 报错退出，不写文件、不造时间戳。
若无新增/修正 → 文件字节不变，工作流不会触发无意义部署。
单个数据源不可达 → 只跳过该彩种、保留原数据并告警，不阻断整个工作流；
数据是否真的过期交给 guard_lottery_freshness.py 判断。

## 用法
  python3 scripts/fetch_lottery_history.py            # 抓取并写回
  python3 scripts/fetch_lottery_history.py ssq        # 只更新双色球
  python3 scripts/fetch_lottery_history.py --check    # 只检查最新期，不写文件
"""
import datetime
import json
import os
import sys
import time
import urllib.request
import urllib.error

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"

# 官方接口
CWL_API = "https://www.cwl.gov.cn/cwl_admin/front/cwlkj/search/kjxx/findDrawNotice"
CWL_REF = "https://www.cwl.gov.cn/"
SPORT_API = "https://webapi.sporttery.cn/gateway/lottery/getHistoryPageListV1.qry"
SPORT_REF = "https://www.sporttery.cn/"
# 备用源：中彩网数据接口（与体彩官方开奖公告逐期交叉核对过）
ZHCW_API = "https://jc.zhcw.com/port/client_json.php"
ZHCW_REF = "https://www.zhcw.com/"
ZHCW_ID = {"dlt": "281", "pls": "283"}

# 每次拉最近多少期（覆盖日常 1-3 天漏抓 + 数据源延迟公布）
RECENT = 40

# 官方源超过这个天数没出新期，视为数据源异常：宁可不更新，也不写假时间戳
MAX_LAG_DAYS = 7

CONFIG = {
    "ssq": {
        "name": "双色球", "src": "cwl", "name_param": "ssq",
        "groups": [
            {"key": "r", "label": "红球", "lo": 1, "hi": 33, "cnt": 6, "sample": True},
            {"key": "b", "label": "蓝球", "lo": 1, "hi": 16, "cnt": 1, "sample": True},
        ],
    },
    "dlt": {
        "name": "大乐透", "src": "sport", "game_no": "85",
        "groups": [
            {"key": "r", "label": "前区", "lo": 1, "hi": 35, "cnt": 5, "sample": True},
            {"key": "b", "label": "后区", "lo": 1, "hi": 12, "cnt": 2, "sample": True},
        ],
    },
    "fc3d": {
        "name": "福彩3D", "src": "cwl", "name_param": "3d",
        "groups": [
            {"key": "r", "label": "开奖号", "lo": 0, "hi": 9, "cnt": 3, "sample": False,
             "positions": ["百", "十", "个"]},
        ],
    },
    "pls": {
        "name": "排列3", "src": "sport", "game_no": "35",
        "groups": [
            {"key": "r", "label": "开奖号", "lo": 0, "hi": 9, "cnt": 3, "sample": False,
             "positions": ["百", "十", "个"]},
        ],
    },
}


def fetch_json(url, ref):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Referer": ref,
                                               "Accept": "application/json"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
            if attempt == 2:
                raise
            time.sleep(1.5 * (attempt + 1))
    return None


def fetch_text(url, ref):
    """取原始文本（备用源可能返回 JSONP 包装）。"""
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Referer": ref,
                                               "Accept": "*/*"})
    for attempt in range(2):
        try:
            with urllib.request.urlopen(req, timeout=25) as resp:
                return resp.read().decode("utf-8", "replace")
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError):
            if attempt == 1:
                raise
            time.sleep(1.5)


def to_int(v):
    try:
        return int(str(v).strip())
    except (ValueError, AttributeError):
        return None


def fetch_cwl(name_param, recent):
    """福彩官方：返回 [{i,d,r,b}, ...]（已归一）。"""
    url = "%s?name=%s&issueCount=%d" % (CWL_API, name_param, recent)
    d = fetch_json(url, CWL_REF)
    if not d or d.get("state") != 0:
        raise RuntimeError("福彩官方接口返回异常: %s" % str(d)[:200])
    out = []
    for row in (d.get("result") or []):
        issue = str(row.get("code", "")).strip()
        day = str(row.get("date", ""))[:10].strip()
        red = row.get("red") or ""
        blue = row.get("blue") or ""
        r = [to_int(x) for x in str(red).split(",") if x.strip()]
        b = [to_int(x) for x in str(blue).split(",") if x.strip()] if blue else []
        if not issue or not day or any(x is None for x in r):
            continue
        if b and any(x is None for x in b):
            continue
        # 双色球红球按升序展示；福彩3D 的 red 是百/十/个位置，必须保序不能排序
        reds = sorted(x for x in r if x is not None) if name_param == "ssq" \
            else [x for x in r if x is not None]
        blues = sorted(x for x in b if x is not None)
        out.append({"i": issue, "d": day, "r": reds, "b": blues})
    return out


def fetch_zhcw(tid, recent):
    """中彩网备用源：返回 [{i,d,r,b}, ...]（已归一）。"""
    url = ("%s?transactionType=10001001&lotteryId=%s&type=0&pageNum=1"
           "&pageSize=%d&issueCount=%d&tt=%s"
           % (ZHCW_API, ZHCW_ID[tid], recent, recent, time.time()))
    text = fetch_text(url, ZHCW_REF).strip()
    if text and not text.startswith("{"):
        a, b = text.find("("), text.rfind(")")
        if a >= 0 and b > a:
            text = text[a + 1:b]
    d = json.loads(text)
    out = []
    for row in (d.get("data") or []):
        issue = str(row.get("issue", "")).strip()
        day = str(row.get("openTime", ""))[:10].strip()
        r = [to_int(x) for x in str(row.get("frontWinningNum", "")).split()]
        b = [to_int(x) for x in str(row.get("backWinningNum", "")).split()]
        if not issue or not day or any(x is None for x in r + b):
            continue
        # 大乐透前区/后区升序；排列3 是百十个位，保序
        if tid == "dlt":
            r, b = sorted(r), sorted(b)
        out.append({"i": issue, "d": day, "r": r, "b": b})
    return out


def fetch_sport(game_no, recent):
    """体彩数据：官方优先，被拦/异常时自动切中彩网备用源。"""
    tid = "dlt" if game_no == "85" else "pls"
    url = ("%s?gameNo=%s&provinceId=0&pageSize=%d&isVerify=1&pageNo=1"
           % (SPORT_API, game_no, recent))
    try:
        d = fetch_json(url, SPORT_REF)
        if not d or not d.get("success"):
            raise RuntimeError("体彩官方接口返回异常: %s" % str(d)[:160])
        rows = ((d.get("value") or {}).get("list") or [])
        out = []
        for row in rows:
            issue = str(row.get("lotteryDrawNum", "")).strip()
            day = str(row.get("lotteryDrawTime", "")).strip()
            nums = [to_int(x) for x in str(row.get("lotteryDrawResult", "")).split()]
            if not issue or not day or any(x is None for x in nums):
                continue
            nums = [x for x in nums if x is not None]
            # 排列3(game_no=35)：3 位顺序（百十个），不排序；大乐透：前 5 后 2
            if game_no == "35":
                r, b = nums[:3], []
            else:
                r, b = sorted(nums[:5]), sorted(nums[5:7])
            out.append({"i": issue, "d": day, "r": r, "b": b})
        if out:
            return out
        raise RuntimeError("体彩官方接口无有效数据")
    except Exception as e:
        print("  ⚠️ 体彩官方源不可用（%s），切换中彩网备用源" % e)
        return fetch_zhcw(tid, recent)


def valid(draw, groups):
    """范围校验：任一号码越界或数量不符即判脏。"""
    for grp in groups:
        arr = draw.get(grp["key"]) or []
        if len(arr) != grp["cnt"]:
            return False
        for n in arr:
            if not (grp["lo"] <= n <= grp["hi"]):
                return False
    return True


def build(tid, check_only=False):
    cfg = CONFIG[tid]
    src = fetch_cwl(cfg["name_param"], RECENT) if cfg["src"] == "cwl" \
        else fetch_sport(cfg["game_no"], RECENT)
    src = [x for x in src if valid(x, cfg["groups"])]
    if not src:
        raise RuntimeError("%s 官方源没有拿到有效数据" % tid)

    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "..", "static", "data", "lottery")
    path = os.path.join(out_dir, tid + ".json")
    local = json.load(open(path, encoding="utf-8"))
    draws = local.get("draws", [])
    by_issue = {x["i"]: x for x in draws}

    added, corrected = 0, 0
    for row in src:  # 官方按新→旧
        if row["i"] in by_issue:
            old = by_issue[row["i"]]
            if old["r"] != row["r"] or old["b"] != row["b"] or old["d"] != row["d"]:
                print("  ⚠️ 第 %s 期与官方不一致，以官方为准: %s -> %s"
                      % (row["i"], old, row))
                old.update(row)
                corrected += 1
        else:
            by_issue[row["i"]] = row
            added += 1

    merged = sorted(by_issue.values(), key=lambda x: (x["d"], x["i"]))
    latest = merged[-1]  # 按日期排序后的真实最新一期，不依赖接口返回顺序
    lag = (datetime.date.today() - datetime.date.fromisoformat(latest["d"])).days
    if lag > MAX_LAG_DAYS:
        raise RuntimeError("官方最新一期 %s(%s) 距今 %d 天，超过 %d 天阈值；"
                           "疑似数据源停更，拒绝写入假时间戳"
                           % (latest["i"], latest["d"], lag, MAX_LAG_DAYS))
    print("  %s: 官方最新 %s(%s) | 新增 %d 期 / 修正 %d 期 | 本地共 %d 期"
          % (cfg["name"], latest["i"], latest["d"], added, corrected, len(merged)))

    if check_only:
        return {"tid": tid, "latest": latest, "added": added, "corrected": corrected,
                "total": len(merged)}

    result = {
        "type": tid,
        "name": cfg["name"],
        "updated": latest["d"],  # 真实开奖日，绝不写运行当天
        "meta": {
            "draws": len(merged),
            "first": merged[0]["d"] if merged else "",
            "last": latest["d"],
            "skipped": local.get("meta", {}).get("skipped", 0),
        },
        "groups": cfg["groups"],
        "draws": merged,
    }
    payload = json.dumps(result, ensure_ascii=False, separators=(",", ":"))
    old_text = open(path, encoding="utf-8").read().strip()
    if old_text == payload:
        print("  无新增/修正，文件保持不变（不刷假时间戳、不触发部署）")
    else:
        with open(path, "w", encoding="utf-8") as f:
            f.write(payload)
    return {"tid": tid, "latest": latest, "added": added, "corrected": corrected,
            "total": len(merged)}


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    check_only = "--check" in sys.argv
    only = args or list(CONFIG.keys())
    failed = []
    for tid in only:
        if tid not in CONFIG:
            print("未知彩种: %s" % tid)
            failed.append(tid + "(配置错误)")
            continue
        print("[%s] %s" % (tid, CONFIG[tid]["name"]))
        try:
            build(tid, check_only=check_only)
        except Exception as e:
            print("  ⚠️ 抓取失败，保留原数据: %s" % e)
            failed.append(tid)
    if failed:
        # 上游临时抽风不该让整个工作流飘红：没写文件就不会有假时间戳，
        # 也不该因此阻断其它已成功的彩种。是否真过期由新鲜度守卫把关。
        print("\n⚠️ %d 个彩种本轮未更新（%s）：保留原数据、不写半成品。" %
              (len(failed), "、".join(failed)))
        print("   站点新鲜度守卫会继续核对数据日期；这里不阻断工作流。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
