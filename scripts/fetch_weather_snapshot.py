#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fetch_weather_snapshot.py — 抓取射阳实时天气，生成静态快照 JSON。

目的（2026-11-18）：
  站点天气胶囊/天气页原 100% 依赖浏览器直连境外 Open-Meteo，国内网络约 1/6 概率
  超时 → 显示「--°」。本脚本在服务端（本机/自动更新）抓取并落盘为静态 JSON，
  前端先读快照打底、再尝试实时覆盖、失败保留快照，从而彻底消除「--°」。

数据源（按优先级）：
  1) 高德天气（国内最稳）——需环境变量 AMAP_KEY 或 HOLDER 环境变量；
     未配置时自动跳过。用户找到 key 后：`export AMAP_KEY=xxx` 再跑即可切换。
  2) Open-Meteo（境外兜底）——无需密钥，服务端网络相对稳定。

输出：static/data/weather-snapshot.json
  {
    "temp": 8,              // 当前温度（整数 °C）
    "code": 3,              // WMO 天气代码（供前端选图标）
    "desc": "多云",
    "city": "射阳",
    "updated": "2026-11-18T21:30:00+08:00",
    "source": "amap" | "open-meteo"
  }

用法：
  python3 scripts/fetch_weather_snapshot.py           # 抓取并写入
  python3 scripts/fetch_weather_snapshot.py --stdout  # 只打印结果（调试）
  python3 scripts/fetch_weather_snapshot.py --selftest# 自证
"""
import json
import os
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "static", "data", "weather-snapshot.json")

# 射阳坐标
LAT, LON = 33.77, 120.52
ADCODE = "320924"  # 射阳县行政区划代码（高德用）

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"

WMO = {
    0: "晴", 1: "晴间多云", 2: "多云", 3: "阴",
    45: "雾", 48: "雾凇",
    51: "毛毛雨", 53: "毛毛雨", 55: "毛毛雨", 56: "冻雨", 57: "冻雨",
    61: "小雨", 63: "中雨", 65: "大雨", 66: "冻雨", 67: "冻雨",
    71: "小雪", 73: "中雪", 75: "大雪", 77: "米雪",
    80: "阵雨", 81: "阵雨", 82: "强阵雨", 85: "阵雪", 86: "强阵雪",
    95: "雷阵雨", 96: "雷阵雨伴冰雹", 99: "雷阵雨伴冰雹",
}
# 高德天气现象 -> WMO code 近似映射（供前端图标复用）
AMAP_WX = {
    "晴": 0, "多云": 2, "阴": 3, "小雨": 61, "中雨": 63, "大雨": 65,
    "暴雨": 65, "阵雨": 80, "雷阵雨": 95, "雷阵雨伴冰雹": 99,
    "雨夹雪": 71, "小雪": 71, "中雪": 73, "大雪": 75, "暴雪": 75,
    "雾": 45, "霾": 45, "冻雨": 66, "沙尘暴": 45,
}


def now_iso():
    tz = timezone(timedelta(hours=8))
    return datetime.now(tz).replace(microsecond=0).isoformat()


def http_get(url, timeout=12, retries=2):
    last = None
    for i in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read().decode("utf-8")
        except Exception as e:
            last = e
            if i < retries:
                time.sleep(1)
    raise last


def fetch_amap():
    """高德天气（需 AMAP_KEY）。高德实时天气温度字段为 temperature（字符串°C）。"""
    key = os.environ.get("AMAP_KEY", "").strip()
    if not key:
        return None
    url = f"https://restapi.amap.com/v3/weather/weatherInfo?key={key}&city={ADCODE}&extensions=base&output=JSON"
    raw = http_get(url)
    d = json.loads(raw)
    if str(d.get("status")) != "1" or not d.get("lives"):
        raise RuntimeError("amap bad response: " + raw[:120])
    live = d["lives"][0]
    temp = int(round(float(live.get("temperature", 0))))
    wx = live.get("weather", "多云")
    code = AMAP_WX.get(wx, 3)
    return {"temp": temp, "code": code, "desc": wx, "city": live.get("city", "射阳"),
            "updated": now_iso(), "source": "amap"}


def fetch_open_meteo():
    url = (f"https://api.open-meteo.com/v1/forecast?latitude={LAT}&longitude={LON}"
           f"&current=temperature_2m,weather_code&timezone=Asia%2FShanghai&forecast_days=1")
    raw = http_get(url)
    d = json.loads(raw)
    cur = d.get("current") or {}
    if "temperature_2m" not in cur or "weather_code" not in cur:
        raise RuntimeError("open-meteo bad response: " + raw[:120])
    temp = int(round(float(cur["temperature_2m"])))
    code = int(cur["weather_code"])
    return {"temp": temp, "code": code, "desc": WMO.get(code, "天气"), "city": "射阳",
            "updated": now_iso(), "source": "open-meteo"}


def fetch():
    # 优先高德（若配置 key），失败则退回 Open-Meteo
    if os.environ.get("AMAP_KEY", "").strip():
        try:
            return fetch_amap()
        except Exception as e:
            print(f"[warn] 高德抓取失败，改用 Open-Meteo: {str(e)[:100]}", file=sys.stderr)
    return fetch_open_meteo()


def main():
    arg = sys.argv[1] if len(sys.argv) > 1 else ""
    if arg == "--selftest":
        ok = True
        checks = [
            ("WMO 晴=晴", WMO.get(0) == "晴"),
            ("WMO 雷阵雨代码95", WMO.get(95) == "雷阵雨"),
            ("高德映射 晴->0", AMAP_WX.get("晴") == 0),
            ("高德映射 雷阵雨->95", AMAP_WX.get("雷阵雨") == 95),
            ("输出路径指向 weather-snapshot.json", OUT.endswith("weather-snapshot.json")),
        ]
        for n, c in checks:
            print(("   ✅ " if c else "   ❌ ") + n)
            ok = ok and c
        print("[selftest] " + ("PASS" if ok else "FAIL"))
        return 0 if ok else 1

    data = fetch()
    text = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    if arg == "--stdout":
        print(text, end="")
        return 0
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"[ok] 天气快照已写入 {os.path.relpath(OUT, ROOT)}")
    print(f"     {data['city']} {data['temp']}° {data['desc']} ({data['source']}) {data['updated']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
