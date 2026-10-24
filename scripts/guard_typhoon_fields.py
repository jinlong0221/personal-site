#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
guard_typhoon_fields.py — 台风板块数据模型契约守卫

背景（2026-10-24 事故，龙兄截图反馈「台风监测板块排版炸了、内容太多」）：
「台风实时监测」自动任务在每次刷新时，把整段监测续报**追加**进
name / nameEn / riskLabel，并把 current（应为对象）覆盖成字符串。
一天内 name 从 1265 字涨到 4106 字，hero 卡直接把长文当台风名渲染成
"文字山"，移动端横向溢出（元素宽 476px > 视口 390px）。
同类风险：任何"短字段被自动化写成长文"的模型。

本守卫在提交前拦截：
  - name / nameEn：短名，> 40 字即FAIL（台风名如「蔷琵」/ CHAMPI）
  - riskLabel / sheyang.riskLabel：短标签，> 60 字即FAIL
  - current：必须是对象（含 lat/lon）或缺省；若是字符串即FAIL
  - track：必须是非空数组，且最后一点含 lat/lon
长文只允许出现在 status / summary / riskNote / sheyangDistanceNote 等"长文字段"里。
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TARGET = os.path.join(ROOT, "static", "typhoon.json")

MAX_NAME = 40
MAX_LABEL = 60

LONG_FIELDS_OK = {"status", "summary", "riskNote", "sheyangDistanceNote", "headline",
                  "trackNote", "disclaimer"}


def main():
    quiet = "-q" in sys.argv
    if not os.path.exists(TARGET):
        if not quiet:
            print(f"[guard_typhoon_fields] 跳过：{TARGET} 不存在")
        return 0
    try:
        d = json.load(open(TARGET, encoding="utf-8"))
    except Exception as e:
        print(f"❌ typhoon.json 解析失败: {e}")
        return 1

    errors = []

    name = d.get("name", "")
    if not isinstance(name, str) or not name.strip():
        errors.append("name 为空或非字符串")
    elif len(name) > MAX_NAME:
        errors.append(f"name 超长 {len(name)} 字（上限 {MAX_NAME}）——疑似自动化把监测续报追加进了 name，"
                      f"短名应为「蔷琵」这类 2-6 字；长文放 status 字段")

    name_en = d.get("nameEn", "")
    if name_en and (not isinstance(name_en, str) or len(name_en) > MAX_NAME):
        errors.append(f"nameEn 超长 {len(str(name_en))} 字（上限 {MAX_NAME}），应为 CHAMPI 这类短名")

    for label_path in (("riskLabel",), ("sheyang", "riskLabel")):
        v = d
        ok = True
        for k in label_path:
            if isinstance(v, dict) and k in v:
                v = v[k]
            else:
                ok = False
                break
        if ok and isinstance(v, str) and len(v) > MAX_LABEL:
            errors.append(f"{'.'.join(label_path)} 超长 {len(v)} 字（上限 {MAX_LABEL}）——"
                          f"应为「台风蓝警在效·总体风险中」这类短标签；长文放 riskNote")

    cur = d.get("current", None)
    if cur is not None and not isinstance(cur, dict):
        errors.append(f"current 必须是对象（time/lat/lon/intensity/pressure），实际是 "
                      f"{type(cur).__name__}——疑似自动化用字符串覆盖了对象")

    track = d.get("track")
    if not isinstance(track, list) or not track:
        errors.append("track 必须是非空数组")
    else:
        last = track[-1]
        if not isinstance(last, dict) or last.get("lat") is None or last.get("lon") is None:
            errors.append("track 最后一点缺少 lat/lon")

    if errors:
        print("❌ guard_typhoon_fields 未通过：")
        for e in errors:
            print("   -", e)
        print("   修复参照：短字段只放短值；长文只进 status/summary/riskNote 等长文字段。")
        return 1
    if not quiet:
        print("[guard_typhoon_fields] PASS: typhoon.json 字段契约合规 "
              f"(name={len(name)}字, current={type(cur).__name__}, track={len(track)}点)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
