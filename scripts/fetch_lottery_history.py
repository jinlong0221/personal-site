#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fetch_lottery_history.py — 抓取四种彩票全量历史开奖，打包成静态 JSON。

数据来源：api.huiniao.top 聚合接口（按福彩/体彩官网口径交叉校验的第三方源）。
仅在本机运行，产物放进 static/data/lottery/，网站运行时不再联网。

彩种映射：
  ssq  双色球   6 红(1-33) + 1 蓝(1-16)
  dlt  大乐透   5 前区(1-35) + 2 后区(1-12)
  fc3d 福彩3D   百位/十位/个位（各 0-9，独立）
  pls  排列3    百位/十位/个位（各 0-9，独立）

输出结构（每个文件）：
  {
    "type": "ssq", "name": "双色球",
    "updated": "YYYY-MM-DD",
    "meta": {"draws": N, "first": "YYYY-MM-DD", "last": "YYYY-MM-DD"},
    "groups": [ {"key":"r","label":"红球","lo":1,"hi":33,"cnt":6,"sample":true},
                {"key":"b","label":"蓝球","lo":1,"hi":16,"cnt":1,"sample":true} ],
    "draws": [ {"i":"2026126","d":"2026-11-03","r":[9,10,13,22,29,32],"b":[12]}, ... ]
  }
  福彩3D / 排列3 只有 r（三位），b 为空 []，groups 仅一组、sample=false、带 positions。
"""

import json
import os
import sys
import time
import urllib.request
import urllib.error

API = "https://api.huiniao.top/interface/home/lotteryHistory"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"

# 每种彩：api 类型 + 取数字段 + 范围配置
CONFIG = {
    "ssq": {
        "api": "ssq", "name": "双色球",
        "groups": [
            {"key": "r", "label": "红球", "lo": 1, "hi": 33, "cnt": 6, "sample": True},
            {"key": "b", "label": "蓝球", "lo": 1, "hi": 16, "cnt": 1, "sample": True},
        ],
        "fields": {"r": ["one", "two", "three", "four", "five", "six"], "b": ["seven"]},
    },
    "dlt": {
        "api": "dlt", "name": "大乐透",
        "groups": [
            {"key": "r", "label": "前区", "lo": 1, "hi": 35, "cnt": 5, "sample": True},
            {"key": "b", "label": "后区", "lo": 1, "hi": 12, "cnt": 2, "sample": True},
        ],
        "fields": {"r": ["one", "two", "three", "four", "five"], "b": ["six", "seven"]},
    },
    "fc3d": {
        "api": "fcsd", "name": "福彩3D",
        "groups": [
            {"key": "r", "label": "开奖号", "lo": 0, "hi": 9, "cnt": 3, "sample": False,
             "positions": ["百", "十", "个"]},
        ],
        "fields": {"r": ["one", "two", "three"], "b": []},
    },
    "pls": {
        "api": "pls", "name": "排列3",
        "groups": [
            {"key": "r", "label": "开奖号", "lo": 0, "hi": 9, "cnt": 3, "sample": False,
             "positions": ["百", "十", "个"]},
        ],
        "fields": {"r": ["one", "two", "three"], "b": []},
    },
}


def fetch_json(tid, page, limit=500):
    url = "%s?type=%s&page=%d&limit=%d" % (API, tid, page, limit)
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
            if attempt == 2:
                raise
            time.sleep(1.5 * (attempt + 1))
    return None


def to_int(v):
    try:
        return int(str(v).strip())
    except (ValueError, AttributeError):
        return None


def collect(tid):
    # 用 limit=500 取首页，这样 totalPage 才是按 500/页 算出来的正确值
    first = fetch_json(tid, 1, 500)
    inner = first["data"]["data"]
    total = int(inner.get("totalCount", 0) or 0)
    total_page = int(inner.get("totalPage", 1) or 1)
    print("  total=%d  pages=%d" % (total, total_page))

    rows = []
    for p in range(1, total_page + 1):
        d = fetch_json(tid, p, 500)
        if not d:
            print("  ! 第 %d 页拉取失败，跳过" % p)
            continue
        lst = (d.get("data", {}).get("data", {}) or {}).get("list") or []
        rows.extend(lst)
        if p % 10 == 0 or p == total_page:
            print("  已抓 %d/%d 页" % (p, total_page))
        time.sleep(0.25)
    return rows


def build(tid):
    cfg = CONFIG[tid]
    raw = collect(cfg["api"])
    draws = []
    bad = 0
    for row in raw:
        issue = str(row.get("code", "")).strip()
        day = str(row.get("day", "")).strip()
        if not issue or not day:
            bad += 1
            continue
        g = {}
        ok = True
        for key, flds in cfg["fields"].items():
            nums = []
            for f in flds:
                v = to_int(row.get(f))
                if v is None:
                    v = 0
                nums.append(v)
            g[key] = nums
        g.setdefault("b", [])
        # 范围校验：任一号码越界（如上游脏数据把单数字写成 71）则整条剔除，绝不伪造
        for grp in cfg["groups"]:
            arr = g.get(grp["key"]) or []
            for n in arr:
                if not (grp["lo"] <= n <= grp["hi"]):
                    ok = False
        if not ok:
            bad += 1
            continue
        draws.append({"i": issue, "d": day, "r": g["r"], "b": g["b"]})

    # 按日期升序；同日按 issue 升序
    draws.sort(key=lambda x: (x["d"], x["i"]))

    out = {
        "type": tid,
        "name": cfg["name"],
        "updated": time.strftime("%Y-%m-%d"),
        "meta": {
            "draws": len(draws),
            "first": draws[0]["d"] if draws else "",
            "last": draws[-1]["d"] if draws else "",
            "skipped": bad,
        },
        "groups": cfg["groups"],
        "draws": draws,
    }
    return out


def main():
    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "static", "data", "lottery")
    os.makedirs(out_dir, exist_ok=True)
    only = sys.argv[1:] or list(CONFIG.keys())
    for tid in only:
        if tid not in CONFIG:
            print("未知彩种: %s" % tid)
            continue
        print("[%s] %s" % (tid, CONFIG[tid]["name"]))
        data = build(tid)
        path = os.path.join(out_dir, tid + ".json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
        size = os.path.getsize(path)
        print("  -> %s  (%d 期, %.1f KB)\n" % (path, data["meta"]["draws"], size / 1024))


if __name__ == "__main__":
    main()
