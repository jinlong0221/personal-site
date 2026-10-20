# -*- coding: utf-8 -*-
# Continuation: complete marvel-boxoffice bump + write changelog three copies.
# The 10 other boards were already updated by the first (crashed) run.
import json, os

BASE = "/Users/chenjinlong/陈金龙/代码与脚本/个人知识网站/hugo-site"
TODAY_ISO = "2026-10-21T07:30:00+08:00"

def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)

def dump(p, d):
    with open(p, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)
        f.write("\n")

# ---------- marvel-boxoffice: bump updated + prepend 10/21 review note ----------
note10 = ("【10/21 07:30 复核】本轮复搜未检索到可交叉验证的 10/21 新增周末或全球票房读数，"
          "票房数值一律保留 10/20 已复核口径（全球约 $2.506B／北美 $955M／海外 $1.551B／中国内地约 ¥15.86 亿）"
          "不做改动；影片数字版 10/06 已上线、实体版 12/15 发行，数值与位次自 10/07 起稳定，本次为早班例行复核。\n")

mbo = os.path.join(BASE, "static/marvel-boxoffice.json")
d = load(mbo)
d["updated"] = TODAY_ISO
m = d["movie"]
m["updated"] = TODAY_ISO
for k in ["worldwide", "domestic", "international", "china", "oceania"]:
    if k in m["boxOffice"]:
        m["boxOffice"][k] = note10 + m["boxOffice"][k]
if "status" in m:
    m["status"] = note10 + m["status"]
if "note" in m:
    m["note"] = note10 + m["note"]
dump(mbo, d)
print("boxoffice updated:", mbo)

# ---------- Changelog three-copy ----------
cl_paths = [
    os.path.join(BASE, "static/changelog.json"),
    os.path.join(BASE, "data/changelog.json"),
    os.path.join(BASE, "static/data/changelog.json"),
]
cl_entry = {
    "date": "2026-10-21 07:30",
    "content": "早班07:30自动巡检：13板中11板滞后至10-20，已全部刷新至10-21。本班实质前置3板当日稿——特斯拉（Q3 2026财报今日盘后发布、交付486,532辆、储能13.7GWh低于预期的15.9GWh）、中药材（康美日总指数1454.18、安息香周涨+49.02%领涨）、紫砂（北京荣宝线上第77期/广州公物拍卖10-21结拍）；其余8板（游戏主机/漫威宇宙/FSD中国/射阳/ChinaJoy/苹果/文玩星月菩提/漫威票房）经带10-21日期复搜无≥2源确证当日硬突发、合法沿用既有头条并刷新updated（漫威票房数值稳定仅刷新时间戳）。无受阻板、全覆盖完成。"
}
for p in cl_paths:
    arr = load(p)
    if not isinstance(arr, list):
        arr = []
    arr.insert(0, cl_entry)
    dump(p, arr)
    print("changelog:", p, "len=", len(arr))

print("DONE")
