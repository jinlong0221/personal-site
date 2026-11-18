#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
guard_weather_theme.py — 天气快照 + 主题统一守卫（2026-11-18）

防两类回归：
A) 天气快照 static/data/weather-snapshot.json 结构/取值非法，或前端三处
   （app.js / site-bundle.js / js-src/app.js）丢失「快照优先」逻辑。
   —— 防的是「--° 一大片」问题回潮。
B) 内联防闪白脚本回退到「按小时判断」（与 app.js 系统优先冲突、首次闪变）。
   —— 直接委托 sync_theme_flash.py --check。

接入：CI deploy.yml / .githooks/pre-commit / audit_regression.sh(A25)。
"""
import json
import os
import sys
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SNAP = os.path.join(ROOT, "static", "data", "weather-snapshot.json")
JS_FILES = ["static/js/app.js", "static/js/site-bundle.js", "scripts/js-src/app.js"]
SNAPSHOT_TOKEN = "data/weather-snapshot.json"


def check_snapshot():
    errs = []
    if not os.path.exists(SNAP):
        return ["weather-snapshot.json 不存在"]
    try:
        d = json.load(open(SNAP, encoding="utf-8"))
    except Exception as e:
        return [f"weather-snapshot.json 解析失败: {e}"]
    # 必需字段
    for k in ("temp", "code", "updated", "source"):
        if k not in d:
            errs.append(f"缺字段 {k}")
    if isinstance(d.get("temp"), (int, float)):
        if not (-60 <= d["temp"] <= 60):
            errs.append(f"temp 超出合理范围: {d['temp']}")
    else:
        errs.append("temp 非数值")
    if isinstance(d.get("code"), int):
        if not (0 <= d["code"] <= 99):
            errs.append(f"code 超出 WMO 范围: {d['code']}")
    else:
        errs.append("code 非整数")
    if d.get("source") not in ("amap", "open-meteo"):
        errs.append(f"source 非法: {d.get('source')}")
    upd = str(d.get("updated", ""))
    if "T" not in upd or "+" not in upd and not upd.endswith("Z"):
        errs.append(f"updated 非 ISO8601: {upd}")
    return errs


def check_js():
    errs = []
    for rel in JS_FILES:
        p = os.path.join(ROOT, rel)
        try:
            t = open(p, encoding="utf-8").read()
        except Exception as e:
            errs.append(f"{rel} 读取失败: {e}")
            continue
        if SNAPSHOT_TOKEN not in t:
            errs.append(f"{rel} 缺失快照读取逻辑（可能回退到只会写 --° 的旧逻辑）")
        # 不应再有「catch 里写 --°」的旧写法
        if "--°</span>" in t and "实时失败" not in t:
            errs.append(f"{rel} 仍可能在失败时写 --°")
    return errs


def check_theme():
    p = os.path.join(ROOT, "scripts", "sync_theme_flash.py")
    if not os.path.exists(p):
        return ["sync_theme_flash.py 缺失"]
    try:
        r = subprocess.run([sys.executable, p, "--check"],
                           capture_output=True, text=True)
        if r.returncode != 0:
            return ["内联防闪白脚本未统一为系统优先（运行 sync_theme_flash.py --check 看详情）"]
    except Exception as e:
        return [f"主题统一检查执行失败: {e}"]
    return []


def cmd_selftest():
    ok = True
    checks = [
        ("快照合法样本通过", check_sample({"temp": 8, "code": 0, "updated": "2026-11-18T21:00:00+08:00", "source": "amap"}) == []),
        ("非法temp被拦", len(check_sample({"temp": 999, "code": 0, "updated": "2026-11-18T21:00:00+08:00", "source": "amap"})) > 0),
        ("非法source被拦", len(check_sample({"temp": 8, "code": 0, "updated": "2026-11-18T21:00:00+08:00", "source": "xxx"})) > 0),
        ("缺字段被拦", len(check_sample({"temp": 8})) > 0),
    ]
    for n, c in checks:
        print(("   ✅ " if c else "   ❌ ") + n)
        ok = ok and c
    print("[selftest] " + ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


def check_sample(d):
    """对给定 dict 跑字段校验逻辑（复用 check_snapshot 的判据）。"""
    errs = []
    for k in ("temp", "code", "updated", "source"):
        if k not in d:
            errs.append(f"缺字段 {k}")
    if isinstance(d.get("temp"), (int, float)):
        if not (-60 <= d["temp"] <= 60):
            errs.append("temp range")
    else:
        errs.append("temp type")
    if isinstance(d.get("code"), int):
        if not (0 <= d["code"] <= 99):
            errs.append("code range")
    else:
        errs.append("code type")
    if d.get("source") not in ("amap", "open-meteo"):
        errs.append("source")
    upd = str(d.get("updated", ""))
    if "T" not in upd or ("+" not in upd and not upd.endswith("Z")):
        errs.append("updated")
    return errs


def main():
    if "--selftest" in sys.argv:
        return cmd_selftest()
    quiet = "-q" in sys.argv
    errs = []
    errs += [f"[快照] {e}" for e in check_snapshot()]
    errs += [f"[前端] {e}" for e in check_js()]
    errs += [f"[主题] {e}" for e in check_theme()]
    if errs:
        print("❌ guard_weather_theme 未通过：")
        for e in errs:
            print("   -", e)
        return 1
    if not quiet:
        print("✅ guard_weather_theme PASS（天气快照合法 + 前端快照逻辑在 + 主题统一）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
