# -*- coding: utf-8 -*-
import json, os

BASE = "/Users/chenjinlong/陈金龙/代码与脚本/个人知识网站/hugo-site"
TODAY = "2026-10-21"

def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)

def dump(p, d):
    with open(p, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)
        f.write("\n")

# ---------- New entries (prepend) ----------
tesla_new = {
    "date": "2026-10-21",
    "tags": [
        {"text": "TSLA", "class": "hot"},
        {"text": "Q3财报", "class": "tag-blue"},
        {"text": "盘后", "class": "info"}
    ],
    "summary": "特斯拉将于10月21日美股盘后发布2026年第三季度财报并召开业绩电话会；第三季度交付486,532辆、储能部署13.7GWh低于分析师预期的15.9GWh，市场聚焦汽车毛利率与Robotaxi、FSD进展，股价盘前涨约2.11%至375.79美元。",
    "content": "特斯拉官方投资者关系与SEC文件显示，公司将于美东时间10月21日下午5:30（北京时间10月22日凌晨5:30）发布2026年第三季度财报并召开业绩电话会。第三季度特斯拉交付486,532辆（Model 3/Y 478,237辆、其他车型8,295辆），产量464,391辆，交付高于产量约22,141辆；能源业务部署13.7GWh储能产品，低于分析师预期的15.0—15.9GWh。市场关注汽车毛利率（雅虎财经援引Zacks共识预计汽车毛利率约17.3%、营收约278亿美元）与Robotaxi、FSD、Optimus进展。财报发布前，TSLA盘前涨约2.11%至375.79美元、市值约1.48万亿美元。\n\n⚠️ 口径说明：交付与储能为特斯拉官方已公布数据（10月2日SEC文件/IR公告）；营收、毛利率与EPS为分析师共识预测，非官方实际值，待盘后财报确认；本条目为「财报发布事件」预告+已确认交付数据，非业绩实际结果。",
    "url": "https://ir.tesla.com/press-release/tesla-third-quarter-2026-production-deliveries-and-deployments",
    "sources": [
        "特斯拉投资者关系 IR 公告《Tesla Third Quarter 2026 Production, Deliveries & Deployments》（Q3交付486,532辆、储能13.7GWh、10/21盘后发财报）",
        "SEC EDGAR 2026 Q3 交付文件 exhibit 99.1（生产464,391/交付486,532/储能13.7GWh）",
        "Yahoo Finance 2026-10-20《Tesla Gears Up to Report Q3 Earnings》（Zacks共识营收约278亿美元、汽车毛利率约17.3%；交付486,532辆）",
        "CoinGlass 2026-10-21 TSLA 盘前 375.79美元 +2.11%、市值约1.48万亿美元"
    ]
}

herbs_new = {
    "date": "2026-10-21",
    "tags": [
        {"text": "康美指数", "class": "hot"},
        {"text": "日总指数", "class": "tag-blue"},
        {"text": "1454.18", "class": "info"}
    ],
    "summary": "康美·中国中药材价格总指数10月21日报1454.18点，秋季产新集中上市、新货增多但终端需求未同步，大盘处于磨底阶段；周涨幅居前为安息香+49.02%（380元/kg）、地锦草+20.05%、罗汉果+16.81%。",
    "content": "康美中药网10月21日日总指数显示，康美·中国中药材价格总指数报1454.18点，较前期基本持平、周波动有限。周涨幅居前的品种为安息香+49.02%（参考价380元/kg）、地锦草+20.05%（7.50元）、罗汉果+16.81%（0.60—0.90元）、百合花+10.36%、鹿衔草+8.33%、牛膝+7.25%；周跌幅居前的品种为三七花-15.04%（180—190元）、水菖蒲-15.00%、辛夷-14.29%（60元）、沙苑子-9.85%、佩兰-8.41%、豨莶草-7.97%。康美中药网日常分析指出，大宗药材品种产新中、行情平淡，高位库存丰富与新增量压力较大，香料走动不及前快，网红药食品种依旧保持一定关注度。",
    "url": "https://www.kmzyw.com.cn/?device=mobile",
    "sources": [
        "康美中药网 kmzyw.com.cn 日总指数 2026-10-21（1454.18点）",
        "康美·中国中药材价格指数网 wapprice.kmzyw.com.cn 日指数 2026-10-20/21 发布页（周涨跌榜）",
        "康美中药网《日常分析:牛膝上调,海金沙回落》2026-10-20（产新集中、大盘磨底）"
    ]
}

zisha_new = {
    "date": "2026-10-21",
    "tags": [
        {"text": "紫砂拍卖", "class": "hot"},
        {"text": "网拍", "class": "info"},
        {"text": "10-21结拍", "class": "tag-blue"}
    ],
    "summary": "紫砂秋拍线上持续活跃：北京荣宝线上第77期设民国宜兴紫砂加彩花卉纹壶、罐（无底价）10月21日结拍；广州公物拍卖「紫砂壶一批」（披露价1.3423万元）10月21日10:15网络竞价，为查扣资产处置。",
    "content": "据雅昌拍卖网，北京荣宝2026金风雅物集珍拍卖会（线上）设多场专场，其中「无底价明清瓷器及工艺品专场（五）」上拍民国宜兴紫砂加彩花卉纹壶、罐（两件，壶长19cm、高16cm，罐高12cm、直径15cm，估价无底价、壶底磕无提梁、罐全品），拍卖时间2026年10月21日结拍。另据全国产权行业信息化综合服务平台，广州市公物拍卖行10月21日上午10:15对「紫砂壶一批」（转让底价1.3423万元，标的为查扣的摆件一批、含紫砂壶，需现场看样）进行网络电子竞价，拍卖机构为广州市公物拍卖行有限公司。两场均为国庆后紫砂网拍延续，体现秋拍季线上化与资产处置并行。",
    "url": "https://auction.artron.net/paimai-art5268900009",
    "sources": [
        "雅昌拍卖网 auction.artron.net《民国 宜兴紫砂加彩花卉纹壶,罐(两件)》（北京荣宝线上第77期，2026.10.21 结拍）",
        "全国产权行业信息化综合服务平台 cspea.com.cn《A6-紫砂壶一批》（广州公物拍卖，2026-10-21 10:15 网络竞价，披露价1.3423万元）"
    ]
}

def prepend(path, entry):
    d = load(path)
    d.setdefault("news", [])
    d["news"].insert(0, entry)
    d["news"] = d["news"][:8]
    d["updated"] = TODAY
    dump(path, d)
    print("prepend+updated:", path)

def bump(path):
    d = load(path)
    d["updated"] = TODAY
    dump(path, d)
    print("bump:", path)

# Boards with new 10-21 entries
prepend(os.path.join(BASE, "static/tesla-news.json"), tesla_new)
prepend(os.path.join(BASE, "static/herbs-news.json"), herbs_new)
prepend(os.path.join(BASE, "static/zisha-news.json"), zisha_new)

# Bump-only boards (recent 10-20 content, no distinct 10-21 hard news)
for fn in ["static/console-news.json", "static/marvel-news.json",
           "static/tesla/fsd-news.json", "static/sheyang-news.json",
           "static/chinajoy-news.json", "static/apple-news.json",
           "static/bracelet-news.json"]:
    bump(os.path.join(BASE, fn))

# marvel-boxoffice: bump updated + prepend a 10/21 review note to the changelog-style strings
mbo = os.path.join(BASE, "static/marvel-boxoffice.json")
d = load(mbo)
d["updated"] = "2026-10-21T07:30:00+08:00"
note10 = "【10/21 07:30 复核】本轮复搜未检索到可交叉验证的 10/21 新增周末或全球票房读数，票房数值一律保留 10/20 已复核口径（全球约 $2.506B／北美 $955M／海外 $1.551B／中国内地约 ¥15.86 亿）不做改动；影片数字版 10/06 已上线、实体版 12/15 发行，数值与位次自 10/07 起稳定，本次为早班例行复核。\n"
for k in ["worldwide", "domestic", "international", "china"]:
    if k in d["boxOffice"]:
        d["boxOffice"][k] = note10 + d["boxOffice"][k]
if "status" in d["movie"]:
    d["movie"]["status"] = note10 + d["movie"]["status"]
if "note" in d:
    d["note"] = note10 + d["note"]
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
