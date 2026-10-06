# -*- coding: utf-8 -*-
import json, os

SITE = "/Users/chenjinlong/陈金龙/代码与脚本/个人知识网站/hugo-site"
SRC = os.path.join(SITE, "static/typhoon.json")
d = json.load(open(SRC, encoding="utf-8"))

def apply(s, reps):
    for o, n in reps:
        c = s.count(o)
        if c != 1:
            print("WARN count=%d: %r" % (c, o[:70]))
        s = s.replace(o, n)
    return s

dn = d["sheyangDistanceNote"]
dn = apply(dn, [
  ("强台风级15级48m/s/945hPa、北纬28.1°/东经145.5°(距东京东南约1005km、较23时27.9°N北抬0.2°N、西调0.2°E)、强度变化不大",
   "强台风级14级45m/s/950hPa、北纬28.9°/东经145.7°(距东京东南约945km、较02时28.1°N北抬0.8°N、西调0.2°E)、强度逐渐减弱"),
  ("仍维持强台风级15级、尚未变性；05时快讯未索引以实时发布为准",
   "已减弱为强台风级14级、尚未变性；05时台风公报已发布(28.9°N/145.7°E·14级45m/s)、08时中央气象台台风网与温州台风网交叉印证继续东北偏北"),
  ("中央气象台台风快讯2026总1234期(02时18分)", "中央气象台台风公报(05时)"),
])
d["sheyangDistanceNote"] = dn

ob = d["sheyang"]["observed"]
ob = apply(ob, [
  ("中央气象台台风快讯2026总1234期(02时)确认强台风级15级48m/s/945hPa、中心北纬28.1°/东经145.5°、向东北偏北30-35km/h",
   "中央气象台台风公报(05时)确认强台风级14级45m/s/950hPa、中心北纬28.9°/东经145.7°、向东北30-35km/h"),
  ("尚未变性；05时快讯未索引以实时发布为准",
   "尚未变性；05时台风公报已发布、08时中央气象台台风网与温州台风网(29.8°N/145.7°E)交叉印证继续东北偏北"),
])
d["sheyang"]["observed"] = ob

with open(SRC, "w", encoding="utf-8") as f:
    json.dump(d, f, ensure_ascii=False, indent=2)
    f.write("\n")
json.load(open(SRC, encoding="utf-8"))
print("OK fix3. distanceNote 彩云 has 14级:", "强台风级14级" in dn, "| observed 彩云 has 14级:", "强台风级14级" in ob)
