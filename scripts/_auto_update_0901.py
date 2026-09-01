# -*- coding: utf-8 -*-
import json, os

BASE = "/Users/chenjinlong/陈金龙/代码与脚本/个人知识网站/hugo-site"
TODAY = "2026-09-01"
NEWS_UPDATED = "2026-09-01"

new_entries = {
    "static/tesla-news.json": [
        {
            "date": "09-01",
            "tags": [
                {"text": "Optimus量产", "class": "hot"},
                {"text": "股价+5.5%", "class": "info"},
                {"text": "费利蒙工厂", "class": "default"},
            ],
            "content": "9月1日（华尔街见闻/第一财经）特斯拉涨超5%领涨科技七巨头，市场确认其Optimus人形机器人已在加州费利蒙工厂正式进入量产阶段，重振资本市场对特斯拉由车企向「AI+机器人巨头」估值重塑的信心。",
            "url": "https://www.toutiao.com/article/7680265584331850291/",
            "sources": ["华尔街见闻", "第一财经"],
        }
    ],
    "static/tesla/fsd-news.json": [
        {
            "date": "09-01",
            "tags": [
                {"text": "FSD v14", "class": "hot"},
                {"text": "自动避坑", "class": "warn"},
                {"text": "马斯克确认", "class": "info"},
            ],
            "content": "9月1日（快科技/腾讯/IT时代网）马斯克确认特斯拉FSD自动避让路面坑洼功能「很快推出」，该功能已列入FSD v14待更新列表；目前FSD可识别纸箱、马粪等杂物，坑洼与突发路形仍是其难点。",
            "url": "https://new.qq.com/rain/a/20260901A02QZC00",
            "sources": ["快科技", "腾讯新闻", "IT时代网"],
        },
        {
            "date": "09-01",
            "tags": [
                {"text": "FSD入华", "class": "warn"},
                {"text": "Q3获批冲刺", "class": "info"},
                {"text": "待官方确认", "class": "default"},
            ],
            "content": "9月1日（新浪/每经）特斯拉辟谣上海数据中心关门，临港AI训练中心已投运、数据安全认证通过，FSD入华基建就绪；官方目标2026 Q3获批，社区预期9月内测、10月小范围、11月上线——具体仍以监管审批为准（待官方确认）。",
            "url": "https://k.sina.com.cn/article_7879777159_1d5abdb8706801ism8.html",
            "sources": ["新浪财经", "每日经济新闻", "爱范儿"],
        },
    ],
    "static/console-news.json": [
        {
            "date": "09-01",
            "tags": [
                {"text": "Switch 2涨价", "class": "hot"},
                {"text": "+$50", "class": "warn"},
                {"text": "9/1生效", "class": "default"},
            ],
            "content": "9月1日（Notebookcheck/TheBadGamer）任天堂Switch 2美国建议零售价今起由$449.99上调至$499.99（约+50美元），加拿大/欧洲同步涨价；两款新捆绑包——马里奥赛车世界(9月下旬$549.99)、运动度假(10/22 $529.99)随后推出。",
            "url": "https://www.notebookcheck.net/Switch-2-price-hike-to-take-effect-next-week-even-as-console-sales-take-a-hit-in-July.1381459.0.html",
            "sources": ["Notebookcheck", "TheBadGamer", "IGN"],
        }
    ],
    "static/marvel-news.json": [
        {
            "date": "09-01",
            "tags": [
                {"text": "复联4重映", "class": "hot"},
                {"text": "9/1开票", "class": "info"},
                {"text": "末日前瞻", "class": "default"},
            ],
            "content": "9月1日（Disney UK官宣）漫威《复仇者联盟4：终局之战》重映版「Encore」今起开票，9/25(英/印)起以IMAX与全新INFINITY VISION格式重映，含《复仇者联盟：末日》(Doomsday, 12/18)独家前瞻。澳大利亚9/24开映。",
            "url": "https://press.disney.co.uk/news/trailer-and-poster-for-marvel-studios-avengers-endgame-encore-now-available-tickets-on-sale-now-for-imax-and-infinity-vision-certified-screens",
            "sources": ["Disney UK Press", "Third Eye Cinemas"],
        },
        {
            "date": "09-01",
            "tags": [
                {"text": "Disney+ 9月", "class": "info"},
                {"text": "蜘蛛侠上线", "class": "default"},
                {"text": "猎人克莱文", "class": "default"},
            ],
            "content": "9月（ScreenRant）Disney+漫威片单：汤姆·赫兰德蜘蛛侠《英雄远征》《英雄无归》9/4上线，《猎人克莱文》9/13上线，配合《崭新之日》热映做IP联动回流。",
            "url": "https://screenrant.com/marvel-movies-shows-release-disney-plus-september-2026/",
            "sources": ["ScreenRant"],
        },
    ],
    "static/apple-news.json": [
        {
            "date": "09-01",
            "tags": [
                {"text": "库克交棒", "class": "info"},
                {"text": "特努斯接任", "class": "default"},
                {"text": "9/1生效", "class": "default"},
            ],
            "content": "9月1日（新浪/第一财经）蒂姆·库克8/31卸任苹果CEO最后一天，硬件工程高级副总裁约翰·特努斯今起接任CEO，库克转任董事会执行主席。交接恰逢2026秋季发布会(预计9月上旬)前夕。",
            "url": "https://finance.sina.com.cn/stock/usstock/c/2026-09-01/doc-iniqhfqf8481378.shtml",
            "sources": ["新浪财经", "第一财经"],
        },
        {
            "date": "09-01",
            "tags": [
                {"text": "iPhone 18", "class": "hot"},
                {"text": "A20芯片", "class": "info"},
                {"text": "待官方确认", "class": "warn"},
            ],
            "content": "9月（远传/landtop/iFix India）iPhone 18系列爆料：标准版A20/12GB/6.3英寸120Hz/自研C2基带/799美元起；Pro系列A20 Pro+可变光圈+屏下Face ID；折叠机iPhone Fold同期。发布会预计9月8-15日——规格待官方确认。",
            "url": "https://www.fetnet.net/content/cbu/tw/lifecircle/tech/2026/08/newiphonefile.html",
            "sources": ["远传电信", "landtop", "iFix India", "SpecEagle"],
        },
    ],
    "static/herbs-news.json": [
        {
            "date": "09-01",
            "tags": [
                {"text": "连翘价稳", "class": "info"},
                {"text": "蝉蜕转缓", "class": "default"},
                {"text": "旋覆花上调", "class": "warn"},
            ],
            "content": "9月1日（药通网/天地网产地快讯）山西新绛连翘价稳(鲜8-8.2元、去柄26-27元)；河南辉县连翘挥发油合格25-25.5元走良好；山东平邑蝉蜕转缓(沙地650元、水洗三遍1050元)；陕西鄠邑旋覆花上调至好统35-37元。",
            "url": "https://www.yt1998.com/",
            "sources": ["药通网", "中药材天地网"],
        },
        {
            "date": "09-01",
            "tags": [
                {"text": "下半年低位", "class": "info"},
                {"text": "政策托底", "class": "default"},
                {"text": "分化加剧", "class": "warn"},
            ],
            "content": "9月（中国价格信息网/药通网）研判：2026下半年中药材市场仍低位调整，7-9月夏秋产新增压；野生/矿物类高位，大宗家种过剩品种仍有下跌风险；政策端《中医药振兴十五五规划》与饮片追溯码托底优质货。",
            "url": "https://www.chinaprice.cn/slkjzsjcqkbg/61229.jhtml",
            "sources": ["中国价格信息网", "药通网"],
        },
    ],
    "static/bracelet-news.json": [
        {
            "date": "09-01",
            "tags": [
                {"text": "沉香分化", "class": "info"},
                {"text": "海南料走高", "class": "warn"},
                {"text": "奇楠抗跌", "class": "default"},
            ],
            "content": "9月（沉香之家）2026沉香市场明显分化：普通种植新料价格平稳、无升值空间；高端老料、沉水料、奇楠因存量递减稳中有涨，海南沉香成品连续多月走高、收藏价值凸显；网售低价「沉水串」多为压油仿品。",
            "url": "http://www.chenxiangba.com/faq/325.html",
            "sources": ["沉香之家"],
        }
    ],
    "static/zisha-news.json": [
        {
            "date": "09-01",
            "tags": [
                {"text": "上海国拍紫砂专场", "class": "hot"},
                {"text": "9/6开拍", "class": "info"},
                {"text": "司法拍卖6328件", "class": "default"},
            ],
            "content": "9月（东方网拍卖）上海国拍第919期紫砂专场9/6 9:00-9/7 21:30网络在线拍卖；北京一中院6328件紫砂壶二次司法拍卖9/4-9/5（起拍141.35万元）；保利9/4「匠造茶泥——当代紫砂壶」专场同步。",
            "url": "https://auc.eastday.com/pmgg/20260822/d84bc59d45fd43c9833a9c303161dfaf.html",
            "sources": ["东方网拍卖", "北京产权交易所", "保利拍卖"],
        }
    ],
    "static/health-tea-news.json": [
        {
            "date": "09-01",
            "tags": [
                {"text": "药食同源4500亿", "class": "hot"},
                {"text": "养生茶高增长", "class": "info"},
                {"text": "年轻化", "class": "default"},
            ],
            "content": "9月（艾媒/行业报告）2026上半年药食同源终端销售额2240亿元、同比+27.6%，全年有望破4500亿；养生茶饮2025年642.7亿、2028预测1189.5亿；18-35岁占62%、男性消费首超女性(56.1%)，年轻化趋势确立。",
            "url": "https://www.iimedia.cn/",
            "sources": ["艾媒咨询", "中国保健营养"],
        },
        {
            "date": "09-01",
            "tags": [
                {"text": "监管收紧", "class": "warn"},
                {"text": "目录106种", "class": "info"},
                {"text": "贴牌出清", "class": "default"},
            ],
            "content": "9月（行业报告）药食同源合规元年：食药物质目录扩至106种(黄芪/党参/西洋参等放开)，普通食品严禁宣称疗效，上半年超千家贴牌作坊停产出局；拥有自建基地+检测资质的品牌份额逆势上涨。",
            "url": "https://www.iimedia.cn/",
            "sources": ["艾媒咨询", "中国食品药品企业质量安全促进会"],
        },
    ],
    "static/sheyang-news.json": [
        {
            "date": "09-01",
            "tags": [
                {"text": "射阳中到大雨", "class": "warn"},
                {"text": "海区7-8级风", "class": "danger"},
                {"text": "9/2渐止", "class": "info"},
            ],
            "content": "9月1日（盐城新闻网/盐城气象）盐城继续暴雨黄色预警：9/1全市中到大雨、局部暴雨，射阳小雨；受低压倒槽+冷空气影响，9/1-3海区阵风7-8级；9/2降雨减弱渐止转多云。开学出行注意防范短时强降水与雷暴大风。",
            "url": "https://www.ycnews.cn/ycyw/2026/08-31/514KoGJk.html",
            "sources": ["盐城新闻网", "盐城气象"],
        }
    ],
    "static/chinajoy-news.json": [
        {
            "date": "09-01",
            "tags": [
                {"text": "国产3A第二波", "class": "hot"},
                {"text": "黑神话:钟馗", "class": "info"},
                {"text": "影之刃零预售", "class": "default"},
            ],
            "content": "9月（今日头条/36氪）国产3A第二波浪潮确立：影之刃零8/12全平台预售1小时登顶Steam国区；湮灭之潮8/15成都千人试玩；黑神话:钟馗8/20发售两周年放实机演示；科隆夜14款中国游戏登台创纪录。",
            "url": "https://www.toutiao.com/article/7679322107238531584/",
            "sources": ["今日头条", "36氪"],
        },
        {
            "date": "09-01",
            "tags": [
                {"text": "ChinaJoy AI", "class": "info"},
                {"text": "腾讯AI工具", "class": "default"},
                {"text": "中国英雄计划", "class": "default"},
            ],
            "content": "9月（KrASIA）ChinaJoy 2026成AI游戏分水岭：腾讯展示Codename Craft(自然语言生成游戏)、LAP(资产生成)、MagicDawn(渲染)；索尼中国英雄计划《The Defiant》等国产单机亮相，AI从「能否做」转向「如何用好」。",
            "url": "https://kr-asia.com/chinajoy-2026-shows-how-deeply-ai-is-becoming-embedded-in-gaming",
            "sources": ["KrASIA", "36氪"],
        },
    ],
}

changed = []
for rel, entries in new_entries.items():
    path = os.path.join(BASE, rel)
    with open(path, "r", encoding="utf-8") as f:
        d = json.load(f)
    existing = d.get("news", [])
    merged = entries + existing
    d["news"] = merged[:8]
    d["updated"] = NEWS_UPDATED
    with open(path, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)
    changed.append((rel, len(entries), len(d["news"])))
    print("UPDATED", rel, "prepended", len(entries), "now len", len(d["news"]))

# typhoon.json: prepend a fresh 08:05 inspection feed entry
tp = os.path.join(BASE, "static/typhoon.json")
with open(tp, "r", encoding="utf-8") as f:
    td = json.load(f)
ty_entry = {
    "date": "9月1日 08:05",
    "content": "〔08:05 早班巡检·中央气象台9月1日06时台风蓝色预警仍为最新：沙德尔(2618)残涡凌晨在南海西北部再度加强为台风(热带风暴级)，05时中心19.2N/112.8E、8级18m/s、995hPa，东偏北25km/h、今天白天移入南海东北部、3日起回旋减弱；其大风与降水落区完全在闽浙粤台/海南，对射阳无直接风力与暴雨贡献。射阳县暴雨橙色预警(00:23升级)截至08:05仍列最新、未检索到解除或降级期次，县城合德镇仍处橙色落区核心；9/1 射阳中到大雨局部暴雨(收尾)、海区阵风7-8级。按铁律「县级橙警未解除前不下调」，维持「高」/danger/徽标「县城橙色预警」。",
    "tags": [
        {"text": "08:05巡检", "class": "info"},
        {"text": "蓝警仍最新", "class": "warn"},
        {"text": "县城橙警未解", "class": "danger"},
    ],
}
td["feed"] = [ty_entry] + td.get("feed", [])[:7]
td["updated"] = "2026-09-01T08:05:00+08:00"
with open(tp, "w", encoding="utf-8") as f:
    json.dump(td, f, ensure_ascii=False, indent=2)
print("UPDATED static/typhoon.json feed now len", len(td["feed"]))

# marvel-boxoffice.json: refresh Holland record + box office text
mp = os.path.join(BASE, "static/marvel-boxoffice.json")
with open(mp, "r", encoding="utf-8") as f:
    md = json.load(f)
mov = md["movie"]
prev_status = mov.get("status", "")
new_status = ("9/1 荷兰弟(汤姆·赫兰德)凭《崭新之日》登顶全球影史男演员票房榜(参演影片全球累计146.8亿美元、位列男演员第一)；影片全球约23.59亿美元升至影史第三 · " + prev_status)[:1500]
mov["status"] = new_status
bo = mov.get("boxOffice", {})
bo["worldwide"] = "约 23.3–23.8 亿美元（各源分歧：新浪9/1列 $23.59B 影史第三；AceShowbiz称破 $23.8B 超《阿凡达2》列第三；BoxOfficeHype列 $2.304B）"
mov["boxOffice"] = bo
ms = mov.get("milestones", [])
ms.insert(0, "9/1 荷兰弟凭《蜘蛛侠：崭新之日》登顶全球影史男演员票房榜（参演影片累计146.8亿美元），影片全球约23.59亿美元列影史第三")
mov["milestones"] = ms[:12]
md["updated"] = NEWS_UPDATED
md["sources"] = list(dict.fromkeys(["新浪财经", "Box Office Mojo", "猫眼专业版", "AceShowbiz", "BoxOfficeHype"] + md.get("sources", [])))[:8]
with open(mp, "w", encoding="utf-8") as f:
    json.dump(md, f, ensure_ascii=False, indent=2)
print("UPDATED static/marvel-boxoffice.json")
print("DONE")
