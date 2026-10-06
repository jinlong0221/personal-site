# -*- coding: utf-8 -*-
import json, os

SITE = "/Users/chenjinlong/陈金龙/代码与脚本/个人知识网站/hugo-site"
FILES = [
    os.path.join(SITE, "static/changelog.json"),
    os.path.join(SITE, "data/changelog.json"),
    os.path.join(SITE, "static/data/changelog.json"),
]

entry = {
    "date": "2026-10-06 09:09",
    "content": "🌀 台风实时监测高频刷新（09:09）：经中央气象台台风公报(06日05时)与台风快讯2026总1239期(06:07)确认——第27号台风「彩云」(2627)减弱为强台风级14级(45m/s)/950hPa、中心28.9°N/145.7°E、向东北30-35km/h、距射阳逾两千公里无影响；诺洛#28(2628)/小熊#29(2629)仍远海不影响；舒力基#26 已于9/29 23时停编、本轮监测结束。本地：盐城市气象台(盐城气象)官方微博确认今(6日)傍晚到夜盐城中北部8-10级雷暴大风+海区局部10级(已确认·射阳处中北部在影响范围)，叠加今晨短临提醒点名射阳局地热对流(实况)；综合风险维持「中低」、statusLevel warn、状态「在效监测」。已更新 static/typhoon.json（updated→09:09、current/track/feed/timeline/status/headline/summary/riskLabel/riskNote/alerts/observed/wind/rain/distanceNote/prevention 同步），未改动其他板块。"
}

for p in FILES:
    d = json.load(open(p, encoding="utf-8"))
    if not (d and d[0].get("date") == "2026-10-06 09:09"):
        d.insert(0, entry)
    else:
        print("already has 09:09 at top of", p)
    # sort by date desc to be safe
    d.sort(key=lambda x: x.get("date", ""), reverse=True)
    json.dump(d, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    open(p, "a", encoding="utf-8").write("\n")

# verify byte-identical
import hashlib
def md5(p):
    return hashlib.md5(open(p, "rb").read()).hexdigest()
m = [md5(p) for p in FILES]
print("MD5:", m)
print("all identical:", len(set(m)) == 1)
print("counts:", [len(json.load(open(p, encoding="utf-8"))) for p in FILES])
