# -*- coding: utf-8 -*-
import json, os

BASE = "static"
TODAY = "2026-10-23"

# 各板块前置的新条目（date=发布日 MM-DD；summary 单段纯文字；content 为详情）
NEW = {
    "apple-news.json": {
        "date": "10-23",
        "tags": [{"text": "iPhone 18 Pro", "class": "hot"}, {"text": "iPhone Duo", "class": "hot"}],
        "summary": "苹果 iPhone 18 Pro 与折叠屏 iPhone Duo 于 2026 年 10 月 23 日正式发售，iPhone 18 Pro 起售价 1199 美元（256GB），搭载 2nm A20 Pro 芯片与机械可变光圈主摄；iPhone Duo 同步上市、首销备货偏紧。",
        "content": "苹果 iPhone 18 Pro 与折叠屏 iPhone Duo 于 2026 年 10 月 23 日正式发售。iPhone 18 Pro 起售价 1199 美元（256GB，较 iPhone 17 Pro 的 1099 美元涨 100 美元），搭载 2nm 制程 A20 Pro 芯片、48MP 融合主摄配机械可变光圈（f/1.48–f/4 六片激光切割叶片），最高 2TB 存储、12GB 内存，新增酒红色。iPhone Duo 折叠屏同日开始销售，首销备货紧张、部分订单交付延至 11 月中旬。彭博社 Mark Gurman 称苹果为 Duo 在旗舰店部署超 150 台演示样机；香港先达 10/23 实时回收价显示各容量均低于原价（倒蚀 419–3499 港元）。",
        "url": "https://hitechreports.com/news/iphone-18-pro-price-specs-release-date-and-deals-everything-we-know",
        "sources": ["hitechreports 2026-10-23", "TechNewsReel 2026-10-23", "idevice.com 引 Bloomberg Mark Gurman 2026-10-11/23", "debitbaba 2026-10-23 实时报价"]
    },
    "tesla-news.json": {
        "date": "10-23",
        "tags": [{"text": "FSD入华", "class": "hot"}, {"text": "财报", "class": "info"}],
        "summary": "特斯拉 10/21 财季电话会上马斯克称正积极争取 FSD 在华监管批准、与中国监管合作，并坦言中国本土车企竞争激烈、特斯拉尚未建立领先优势；他同时预测不受监管限制时特斯拉终将承担当地超半数客运里程。",
        "content": "特斯拉 10 月 21 日（当地时间）发布 2026 财年第三财季财报（总营收 280.04 亿美元、归母净利润 7.87 亿美元），CEO 马斯克在电话会上就 FSD 入华进展表示，公司正积极争取更广泛 FSD 监管批准并与中国监管机构合作；他坦言中国本土车企在自动驾驶领域竞争激烈，特斯拉尚未真正建立领先优势（环球网/IT之家/每日经济新闻 10-22、10-23 报道）。马斯克另预测：只要不受监管限制，特斯拉最终将承担允许其自由运营国家当地超过一半的乘客出行里程（金融界/商业内幕 10-23）。特斯拉 AI 副总裁阿肖克·埃卢斯瓦米同场宣布，无需驾驶员监督的 FSD 功能预计「明年第二季度前后」推出（待官方确认）。",
        "url": "https://k.sina.com.cn/article_2660940103_9e9ab94704001wfdo.html",
        "sources": ["环球网科技 2026-10-23", "IT之家 2026-10-22", "每日经济新闻/重庆日报 2026-10-22", "金融界/商业内幕 2026-10-23"]
    },
    "tesla/fsd-news.json": {
        "date": "10-23",
        "tags": [{"text": "FSD入华", "class": "hot"}, {"text": "监管批准", "class": "info"}],
        "summary": "特斯拉中国近期发布北京、上海、广州等 9 城智能驾驶测试岗位招聘，官方客服回应称正按国家法规积极推进 FSD 审批，获批后将向国内车主 OTA 推送；马斯克在财报会亦确认正争取在华监管批准。",
        "content": "特斯拉中国近期在招聘平台发布多个智能驾驶测试岗位（测试技师、测试工程师、测试场专员），办公地覆盖北京、上海、广州、深圳、苏州、武汉等 9 座城市，引发外界对 FSD 在华落地的猜测。据 GMT8 报道，记者以消费者身份咨询官方客服，关于已花 6.4 万元购买后能否通过 OTA 使用智驾功能，客服回应「目前您的车辆不兼容此功能，我们正按国家法规积极推进审批，一旦获批将及时推送给国内客户」。与此同时，马斯克在 10 月 21 日财报电话会上表示正积极争取更广泛 FSD 监管批准、与中国监管合作，并称在华尚未建立领先优势（待官方确认具体时间表）。特斯拉 AI 副总裁称无监督 FSD 预计「明年第二季度前后」推出（待官方确认）。",
        "url": "https://www.gmt8press.com/flash/detail/1373384",
        "sources": ["GMT8 2026-10", "新浪汽车/环球网 2026-10-23", "IT之家 2026-10-22"]
    },
    "marvel-news.json": {
        "date": "10-23",
        "tags": [{"text": "复联5", "class": "hot"}, {"text": "预告", "class": "info"}],
        "summary": "漫威《复仇者联盟：毁灭之日》(Avengers: Doomsday) 特别前瞻将于 2026 年 10 月 23 日晚（美东 8 点 FOX 世界大赛 G1）播出，影片定档 12 月 18 日上映、片长 165 分钟；另有爆料称新正式预告 10/23 9 点美东发布（待官方确认）。",
        "content": "漫威影业与 MLB 合作，将在 2026 年 10 月 23 日世界大赛第一场（坦帕湾光芒 vs 密尔沃基酿酒人，美东晚 8 点 FOX 直播）期间播出《复仇者联盟：毁灭之日》(Avengers: Doomsday) 的特别前瞻，MLB 官方 Instagram 于 10 月 22 日官宣（WDWNT/Comex/NewsBreak 报道）。影片由乔·罗素与安东尼·罗素回归执导，定档 2026 年 12 月 18 日上映、片长 165 分钟，主演含克里斯·埃文斯（饰美队）、小罗伯特·唐尼（饰毁灭博士）等；前作《复仇者联盟：秘密战争》定档 2027 年 12 月 17 日。另有内部人士 ProjectHurts 爆料称一支新正式预告将于 10 月 23 日美东 9 点发布，该时间点漫威尚未确认，按传闻处理（待官方确认）。",
        "url": "https://wdwnt.com/2026/10/marvel-to-air-exclusive-avengers-doomsday-preview-during-world-series-game-1/",
        "sources": ["WDWNT 2026-10-22", "MLB 官方 Instagram 2026-10-22", "ComingSoon/NewsBreak 2026-10-22", "bamsmackpow 2026-10（ProjectHurts 爆料·待官方确认）"]
    },
    "console-news.json": {
        "date": "10-23",
        "tags": [{"text": "Switch2", "class": "hot"}, {"text": "使命召唤", "class": "info"}],
        "summary": "任天堂 Switch 2 独占软件《Nintendo Switch Sports Resort》于 2026 年 10 月 22 日发售；10 月 23 日 Nintendo Download 更新中，《Call of Duty: Modern Warfare 4》登陆 Switch 2，另含《FINAL FANTASY RESONANCE》、Minecraft（10/27 预购）等。",
        "content": "任天堂香港 10 月 22 日发售 Switch 2 独占软件《Nintendo Switch Sports Resort》（设定于 Wuhu 岛，含 12 项运动），10 月 23 日 Nintendo eShop 新作资讯同步更新。10 月 23 日 Nintendo Download 周更中，《Call of Duty: Modern Warfare 4》于当日登陆 Nintendo Switch 2（战役+多人+DMZ 撤离），《FINAL FANTASY RESONANCE》（HD-2D 回合制，Square Enix）同步上线 NS/NS2；此外开放《Minecraft》Switch 2 版预购（10 月 27 日发售，含 Vibrant Visuals 与超级马里奥材质包），以及《007 First Light》预购（2027 年 3 月 18 日发售）。来源：任天堂香港、Nintendo 台湾、OtakuKart。",
        "url": "https://www.nintendo.com.hk/topics/index.html",
        "sources": ["任天堂香港 2026-10-22/23", "Nintendo 台湾 2026-10-23", "OtakuKart 2026-10-23"]
    },
    "herbs-news.json": {
        "date": "10-23",
        "tags": [{"text": "康美指数", "class": "hot"}, {"text": "霜降", "class": "info"}],
        "summary": "霜降交节当日康美中药指数收于 1454.69 点（较 10 日前微涨 0.04%）；安息香参考价 380 元/公斤周涨 49%、地锦草 7.5 元/公斤涨 20%、虎杖涨 6%，牛膝 16 元/公斤、地黄 13 元/公斤日行情平稳。",
        "content": "2026 年 10 月 23 日（秋季最后一个节气霜降于 17:37 交节）康美中药网数据：总指数 1454.69 点，较 10 日前微涨 0.04%；环比上涨品规由 18 个增至 27 个、下滑品规 50 个，涨跌比约 1:2。短线涨价品种：安息香参考价 380 元/公斤（较 7 日前大涨 +49.02%）、地锦草 7.5 元/公斤（涨 +20.05%）、虎杖 8.5 元/公斤（涨 +6.25%）、百合花 48–50 元/公斤（涨 +3.46%）。日行情（中药材天地网 10-23）：牛膝 16 元/公斤、地黄 13 元/公斤、北沙参亳州河北统 19 元/公斤（稳）。茯苓产区价格稳定：安徽岳西统丁 24 元/公斤、湖南靖州统货 17.5–18 元/公斤（FX 农业网 10-23）。门店草本足浴与药膳原料采购建议关注安息香、地锦草短线涨幅、提前锁价控本。",
        "url": "http://mp.weixin.qq.com/s?__biz=MzA3NzAyMjM1NA==&mid=2649492984&idx=1&sn=72ee9ec89e17d39bde3974b960a07a93&chksm=868d0ae6dc91c4e81246d9f0d970f000a2aa24e48f9c41ce7942f3351f9584207226291b8f2a",
        "sources": ["中医养生晨报 2026-10-23", "康美中药网 2026-10-21 收盘", "中药材天地网 2026-10-23", "FX农业网 2026-10-23"]
    },
    "zisha-news.json": {
        "date": "10-23",
        "tags": [{"text": "紫砂网拍", "class": "info"}, {"text": "慈善拍卖", "class": "hot"}],
        "summary": "多场紫砂拍卖 10 月 23 日同步进行：上海中南拍卖慈善网络拍卖上线扁腹紫砂壶、紫砂三友壶、西施紫砂壶等（起拍 100 元）；上氏拍卖秋拍「清 邵亭裕制紫砂壶」10/23 13:00 开拍；香港善學慈善晚宴拍卖吴芳娣《莲心壶》等紫砂作品。",
        "content": "2026 年 10 月 23 日紫砂拍卖动态：① 公拍网显示上海中南拍卖有限公司 2026 年 10 月 23 日 10:00 至 10 月 24 日 10:00 举行慈善网络在线拍卖，紫砂类含扁腹紫砂壶、紫砂三友壶、西施紫砂壶等，起拍价 100 元、单件围观逾 800 人。② 雅昌拍卖网：上氏拍卖 2026 秋季艺术品拍卖会「墨案茶香—文房、印章及茶道具等」专场，LOT 1229「清 邵亭裕制紫砂壶」（高 6.5cm、直径 11.5cm、「邵亭裕制」款）于 2026.10.23 13:00 开拍（时间顺延）。③ 橙新闻：善學慈善基金 10 月 23 日假丽豪航天城酒店举办「善美绽放」慈善晚宴，拍卖含宜兴吴派紫砂传人、正高工吴芳娣《莲心壶》等水墨紫砂雕塑。来源：公拍网、雅昌艺术网、橙新闻。",
        "url": "https://zc.gpai.net/zc/mechanismDivision?id=187&index=0",
        "sources": ["公拍网 2026-10-23", "雅昌艺术网 auction.artron.net 2026-10-23", "橙新闻 2026-10-23"]
    },
    "health-tea-news.json": {
        "date": "10-23",
        "tags": [{"text": "药食同源", "class": "hot"}, {"text": "霜降", "class": "info"}],
        "summary": "药食同源赛道景气延续，第 93 届全国药品交易会药食同源展（10/21–23 北京）收官；行业数据称该赛道 2025 年终端市场破 3700 亿元、2026 年预计 4500 亿元、年增 20%+，78.2% 青年愿为配方透明产品付溢价。",
        "content": "2026 年 10 月 23 日霜降（17:37 交节），药食同源消费品延续热度。第 93 届全国药品交易会（PHARMCHINA）药食同源健康饮品展暨中医药养生/药膳展区于 10 月 21–23 日在北京·中国国际展览中心（顺义新馆）举办，设药食同源专区，覆盖花草茶、滋补干货、养生茶饮等。同期《中医养生晨报》披露：药食同源赛道 2025 年终端市场规模突破 3700 亿元，2026 年预计达 4500 亿元、年增速维持 20% 以上；《2026 大健康消费洞察》显示 78.2% 受访青年愿为配方透明、检测可查、原料可溯产品支付溢价，90 后/00 后占药食同源线上消费 62%。企业侧：陕西国康「千年古都」中医茶疗 10/21 亮相《三农优选》直播；高平羊头山养生茶依托博士工作站研发黄芪黄梨复配产品（高平市政府 10/20）。",
        "url": "https://guangzhou08840.11467.com/m/news/17447259.asp",
        "sources": ["第93届全国药品交易会官网 2026-10-21/23", "中医养生晨报 2026-10-23", "腾讯新闻 2026-10-23（千年古都茶疗）", "高平市人民政府 2026-10-20"]
    },
    "sheyang-news.json": {
        "date": "10-23",
        "tags": [{"text": "台风蔷琵", "class": "hot"}, {"text": "防御部署", "class": "info"}],
        "summary": "江苏省部署第 30 号台风「蔷琵」防御工作，盐城气象预报 24–25 日有风雨、海区 8–9 级大风，射阳处北部边缘 25 日小到中雨、累积 5–15 毫米，需防范大风与降雨影响。",
        "content": "据射阳县人民政府网站 2026 年 10 月 23 日消息，江苏省当日部署第 30 号台风「蔷琵」防御工作。盐城市气象台预报：无论路径如何，24–25 日盐城均有风雨，海区风雨影响更大——24 日白天起风力渐增，24–25 日最大阵风北部 6–7 级、中南部 6–8 级、海区 8–9 级；26–27 日冷空气南下后全市风力持续较大（陆上 6–7 级、海区 8–9 级）。降雨：24 日小雨，25 日中南部中到大雨、北部小到中雨，射阳县处北部边缘、25 日小到中雨、累积 5–15 毫米。气象部门建议防范大风（督促海上船舶回港避风、加固设施）与降雨导致的道路湿滑低能见度。江苏省气象台 10/23 11:10 已发布海区大风黄色预警（南通海区、盐城南部海区 24–25 日 9 级左右东北大风）。",
        "url": "https://www.sheyang.gov.cn/",
        "sources": ["射阳县人民政府 2026-10-23", "盐城新闻网 ycnews.cn 2026-10-22/23", "江苏省气象台/中央气象台 nmc.cn 2026-10-23 11:10 海区大风黄色预警"]
    },
    "chinajoy-news.json": {
        "date": "10-23",
        "tags": [{"text": "国产3A", "class": "hot"}, {"text": "影之刃零", "class": "info"}],
        "summary": "国产 3A 武侠动作游戏《影之刃零》(S-Game/灵游坊，虚幻 5) 定档 2026 年 10 月 29 日全球发售，原定 9 月 9 日、延期 50 天打磨；腾讯战略投资、索尼提供 PS5 技术适配与全球宣发，预售曾登顶 Steam 全球热销榜。",
        "content": "国产 3A 武侠动作游戏《影之刃零》由北京灵游坊（S-Game）研发、采用虚幻引擎 5，构建功夫朋克架空世界，玩家饰演被诬陷的精英刺客「魂」。原定 2026 年 9 月 9 日发售，官方为打磨美术、场景与 PC 跨平台适配延期 50 天至 10 月 29 日全球发售（搜狐/今日头条 10 月 17 日报道）。第三方 Gamalytic 估算 Steam 预估销量约 47.35 万份、预估收入约 2840 万美元（约 1.89 亿元），预测首月销量有望冲 71.86 万份。研发获腾讯 2021 年战略投资，索尼提供 PS5 技术适配与全球宣发；TGA 定档 PV 在 YouTube 官方渠道合计播放超 753 万次，BW 与 ChinaJoy 线下试玩排队热度居第一梯队。外媒 IGN 称其「2026 年最酷的动作游戏之一」。",
        "url": "https://www.sohu.com/a/1090576792_121984121",
        "sources": ["搜狐 2026-10", "今日头条 2026-10-17", "Gamalytic 销量估算"]
    },
}

def write_news(rel, entry, maxn=8):
    p = os.path.join(BASE, rel)
    d = json.load(open(p, encoding="utf-8"))
    news = d.get("news", [])
    news.insert(0, entry)
    d["news"] = news[:maxn]
    d["updated"] = TODAY
    json.dump(d, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"OK {rel}: news now {len(d['news'])} (updated={d['updated']})")

for rel, e in NEW.items():
    write_news(rel, e)

# 台风板：规范化 updated + 前置一条 11:10 海区大风黄色预警 feed
tp = os.path.join(BASE, "typhoon.json")
td = json.load(open(tp, encoding="utf-8"))
feed = td.get("feed", [])
feed.insert(0, {
    "date": "2026-10-23 12:32",
    "content": "2026-10-23 12:32 跟进（基于江苏省气象台 2026-10-23 11:10 海区大风黄色预警·中央气象台 nmc.cn 同步刊发）：受今年第30号台风「蔷琵」外围影响，预计 24–25 日南通海区、盐城南部海区将出现 9 级左右东北大风；省应急厅（省防减救灾办）、省气象局提醒注意防范。结合盐城气象 24–25 日风雨预报（海区 8–9 级、射阳处北部边缘 25 日小到中雨 5–15mm），射阳陆地风险「中」、海区风险偏高，建议海上船舶提前回港避风、加固设施。此前 11:01 续报已确认蔷琵 23 日 10 时位于北纬 22.9°/东经 123.7°、强台风级 14 级 45m/s、距台北东南约 325km、向西北 20km/h、本体对射阳风险「低」，主要风险来自外围倒槽+冷空气带来的 24–25 日风雨。"
})
td["feed"] = feed[:8]
td["updated"] = TODAY
json.dump(td, open(tp, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print(f"OK typhoon.json: feed now {len(td['feed'])} (updated={td['updated']})")

# 漫威票房：仅规范化 updated 为纯日期
mp = os.path.join(BASE, "marvel-boxoffice.json")
md = json.load(open(mp, encoding="utf-8"))
md["updated"] = TODAY
json.dump(md, open(mp, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print(f"OK marvel-boxoffice.json: updated={md['updated']}")

# changelog 三副本前置总记录
changelog_paths = ["static/changelog.json", "data/changelog.json", "static/data/changelog.json"]
record = {"date": TODAY, "content": "午班 14:00 自动更新：检索 13 板块当日动态并交叉核验（含甄别平台重发旧稿）。已更新——苹果（iPhone 18 Pro/iPhone Duo 10/23 发售）、特斯拉（FSD 入华/客运预测）、FSD（9 城招聘+无监督版明年 Q2）、漫威（复联5 世界大赛前瞻）、主机（Switch2 Sports Resort+COD MW4）、中药材（霜降+康美指数）、紫砂（10/23 多场拍卖）、养生茶（药食同源展+赛道数据）、射阳（江苏部署蔷琵防御）、ChinaJoy（影之刃零 10/29 定档）、台风（蔷琵 11:10 海区大风黄警+updated 规范化）、漫威票房（数值稳定、updated 规范化）。文玩手串（星月菩提）当日无硬新闻，保留早班内容。全部 13 板块 updated 均置 2026-10-23，无受阻项待接力。"}
for cp in changelog_paths:
    if not os.path.exists(cp):
        print(f"SKIP missing {cp}"); continue
    arr = json.load(open(cp, encoding="utf-8"))
    if not isinstance(arr, list):
        print(f"WARN {cp} not a list"); continue
    # 避免同一天重复插入完全相同的记录
    if not any(r.get("date") == TODAY and r.get("content","").startswith("午班 14:00") for r in arr):
        arr.insert(0, record)
    json.dump(arr, open(cp, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"OK {cp}: len={len(arr)}")

print("\nALL DONE")
