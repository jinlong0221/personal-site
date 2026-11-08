# -*- coding: utf-8 -*-
import json, os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def path(p): return os.path.join(BASE, p)

def load(p):
    with open(path(p), encoding="utf-8") as f:
        return json.load(f)

def save(p, d):
    with open(path(p), "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)
        f.write("\n")

def prepend(d, entry, keep=8):
    news = d.get("news", [])
    news.insert(0, entry)
    d["news"] = news[:keep]
    return d

# ---- console: 分析师呼吁主机厂商放缓性能追求以控价 ----
c = load("static/console-news.json")
c_entry = {
    "date": "2026-11-08",
    "tags": [
        {"text": "主机", "class": "hot"},
        {"text": "次世代", "class": "info"},
        {"text": "1000美元", "class": "tag-blue"}
    ],
    "summary": "多方行业分析师 11 月 8 日呼吁索尼、微软、任天堂放缓次世代主机的高性能追求，避免首发售价突破 1000 美元（约 6691 元人民币）。Ampere Analysis 的 Piers Harding-Rolls 称高画质强性能推高成本是涨价主因；Alinea Analytics 的 Rhys Elliott 预计 PS5 将持续销售至 PS6 发布后；Omdia 的 James McWhirter 预测主机市场将分化为多档价位。DRAM 短缺与 AI 芯片抢产能加剧零部件涨价压力。",
    "content": "科技媒体 TechRadar 2026-11-08 报道、经 IT之家与腾讯证券交叉确认：多名行业分析师表示，游戏主机厂商需要适当放缓对更高端性能的追逐，以避免次世代主机（PS6、Xbox Project Helix 等）首发售价突破 1000 美元大关。Ampere Analysis 分析师 Piers Harding-Rolls 指出，若索尼、微软和任天堂想让主机不那么昂贵，就必须降低对高画质、高性能的目标追求，\"对高端性能的持续追逐必须被克制\"。Alinea Analytics 分析师 Rhys Elliott 预计，受成本不断上涨影响，即使 PS6 发布后，PS5 也将在相当长一段时间内继续销售，跨世代游戏让玩家可延后硬件升级——\"下一代不会取代这一代，而是叠在其之上\"。Omdia 分析师 James McWhirter 预测，未来主机市场会出现更明显的档次划分，例如任天堂可能推出价格更低的 Switch 2 并搭配更多捆绑套餐，厂商也可能推迟新硬件发布以等待零部件成本回落。分析师强调，与上一世代不同，本世代主机价格并未随时间下降反而越来越贵，持续的 DRAM 内存危机与推高零部件成本的 AI 热潮，令平价硬件前景黯淡。",
    "url": "https://www.ithome.com/1/023/865.htm",
    "sources": [
        "IT之家 2026-11-08《分析师：索尼、微软和任天堂需适当放缓高性能追求，避免次世代主机售价突破 1000 美元》",
        "TechRadar 2026-11-08《Industry analysts say Sony, Microsoft, and Nintendo's relentless push for higher-end performance will need to be moderated to avoid $1000 launch consoles》",
        "腾讯证券 2026-11-08《分析师呼吁主机厂商放缓性能追求以控价》"
    ]
}
prepend(c, c_entry)
save("static/console-news.json", c)
print("console updated ->", c["updated"], "top:", c["news"][0]["date"], "n:", len(c["news"]))

# ---- herbs: 药通网 11-08 涨落排行 ----
h = load("static/herbs-news.json")
h_entry = {
    "date": "2026-11-08",
    "tags": [
        {"text": "中药材", "class": "hot"},
        {"text": "涨落排行", "class": "info"},
        {"text": "11-08", "class": "tag-blue"}
    ],
    "summary": "药通网 11 月 8 日涨落排行显示，落价榜前列为冰球子（贵州统）由 2000 元跌至 1200 元、周环比 -40.0%，毛慈姑（东北统）由 2200 元跌至 1600 元、周环比 -27.3%；涨价侧海金沙（亳州 江西/四川统）报 120 元、周环比 +4.3%，产新结束、陈货有量、行情由升转震荡。",
    "content": "中药材药通网 2026-11-08 价格涨落排行（经交叉确认）：落价药材方面，冰球子（贵州统）现价 1200 元、原价 2000 元、周环比 -40.0%，亳州市场 11 月 8 日 09:40 行情称\"货源充裕、需求不旺、大货交易受阻、行情低迷难改\"，家种货 1200 元、野生小个约 900 元；毛慈姑（东北统）现价 1600 元、原价 2200 元、周环比 -27.3%。涨价方面，海金沙（亳州市场 江西/四川统）报 120 元、周环比 +4.3%，对应市场资讯\"商家关注力度不减、货源进入正常消化、走销不及前期畅快、价格继续震荡中，现净货 120 元\"；其产新已基本结束，今年新货产量不大、陈货仍有库存待售，行情由升转震荡。整体看，落价多集中前期高价小品种，涨价以产新尾声波动为主，大盘仍偏稳中偏弱。",
    "url": "https://www.yt1998.com/ytw/mob/ym_jgxx/fluctuationrank.jsp?scid=1",
    "sources": [
        "药通网 2026-11-08 中药材价格涨落排行（冰球子/毛慈姑/海金沙）",
        "药通网 2026-11-08 09:40 冰球子亳州市场行情、海金沙亳州市场行情（交叉）"
    ]
}
prepend(h, h_entry)
save("static/herbs-news.json", h)
print("herbs updated ->", h["updated"], "top:", h["news"][0]["date"], "n:", len(h["news"]))

# ---- sheyang: 射阳县气象台 11-08 双预警 ----
s = load("static/sheyang-news.json")
s_entry = {
    "date": "2026-11-08",
    "tags": [
        {"text": "射阳", "class": "hot"},
        {"text": "寒潮黄色预警", "class": "info"},
        {"text": "大风蓝色预警", "class": "tag-blue"}
    ],
    "summary": "射阳县气象台 11 月 8 日 08:25 发布寒潮黄色预警，预计 8–10 日全县大部分地区 48 小时最低气温下降 8–9℃、10 日晨最低约 2℃；08:32 续发大风蓝色预警，预计 8 日夜里至 9 日白天部分地区阵风约 8 级，陆上 6–8 级、海区 9–10 级偏北大风。",
    "content": "射阳发布、中国天气网/国家预警信息发布中心 2026-11-08 消息（经新浪财经、盐城新闻网交叉确认）：射阳县气象台 2026 年 11 月 8 日 08 时 25 分发布寒潮黄色预警信号，受强冷空气影响，预计 8–10 日合德镇、临海镇、千秋镇、四明镇、海河镇、海通镇、兴桥镇、新坍镇、长荡镇、盘湾镇、特庸镇、洋马镇、黄沙港镇、经开区、港开区的大部分地区 48 小时最低气温将下降 8–9℃，10 日早晨最低气温 2℃左右；8 日夜里至 9 日白天将出现陆上 6–8 级、海区 9–10 级的偏北大风。08 时 32 分，县气象台继续发布大风蓝色预警信号，预计 8 日夜里至 9 日白天上述部分地区将出现 8 级左右阵风。县应急局、气象局联合提醒注意防寒潮与防风，海上船舶回港避风、加固港口设施，照顾好老弱病人、对农作物及水产采取防寒措施。盐城市气象台同日 08:16 亦发布寒潮黄色预警，预计全市 48 小时最低气温下降 8–10℃，10 日晨中北部 1–2℃、南部 4℃左右。",
    "url": "https://www.weather.com.cn/alarm/newalarmcontent.shtml?file=101190705-20261108082839-0402.html",
    "sources": [
        "中国天气网/国家预警信息发布中心 2026-11-08 射阳县寒潮黄色预警（08:25）+ 大风蓝色预警（08:32）",
        "射阳发布/新浪财经 2026-11-08 09:14《寒潮+大风！射阳发布双预警信号》",
        "盐城新闻网 2026-11-08《猛降10℃！盐城发布寒潮+大风双预警》"
    ]
}
prepend(s, s_entry)
save("static/sheyang-news.json", s)
print("sheyang updated ->", s["updated"], "top:", s["news"][0]["date"], "n:", len(s["news"]))
