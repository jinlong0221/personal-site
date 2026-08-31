# -*- coding: utf-8 -*-
import json, os

BASE = "/Users/chenjinlong/陈金龙/代码与脚本/个人知识网站/hugo-site"
TODAY = "2026-08-31"
TODAY_MD = "08-31"

def load(p):
    with open(os.path.join(BASE, p), encoding="utf-8") as f:
        return json.load(f)

def save(p, d):
    with open(os.path.join(BASE, p), "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)
        f.write("\n")

def prepend(path, items, cap=8):
    d = load(path)
    d["updated"] = TODAY
    news = items + d["news"]
    d["news"] = news[:cap]
    save(path, d)
    return len(news)

# ---------- 1. tesla-news.json ----------
prepend("static/tesla-news.json", [
    {
        "date": TODAY_MD,
        "tags": [
            {"text": "港澳版Model 3", "class": "hot"},
            {"text": "降价8.5%", "class": "warn"},
            {"text": "续航572km", "class": "info"},
            {"text": "Cybercab 9/3", "class": "default"}
        ],
        "content": "8月31日（界面/九派财经/每经）特斯拉正式在中国香港、澳门推出配置简化、售价更低的Model 3版本：香港起售20.5万港元（约17.59万元，较此前降8.5%）、澳门25.2万澳门元；删减氛围灯/面料/轮毂但续航升至572公里。同期Model Y Performance国行版完成能耗备案、预计9月发布10月交付，Cybercab 9/3在奥斯汀公开载客。",
        "url": "https://www.toutiao.com/article/7680038092346049076/",
        "sources": ["界面新闻", "九派财经", "每日经济新闻", "腾讯新闻"]
    },
    {
        "date": TODAY_MD,
        "tags": [
            {"text": "SpaceX造叶片", "class": "hot"},
            {"text": "AI供电瓶颈", "class": "info"},
            {"text": "100GW太阳能", "class": "default"}
        ],
        "content": "8月31日（每经/网易财经早餐）马斯克确认SpaceX在得州建铸造厂自产大型燃气轮机叶片与导叶，可将AI数据中心供电瓶颈缓解、上线时间提前最多18个月；SpaceX与特斯拉各以最快速度建设年产100GW太阳能产能，但未来数年仍需天然气补充。马斯克将携萨克斯9/1线上出席G20创新部长级会议。",
        "url": "https://new.qq.com/rain/a/20260831A03FT500?refer=cp_1009",
        "sources": ["每日经济新闻", "网易财经早餐", "财联社", "金融界"]
    }
])

# ---------- 2. herbs-news.json ----------
prepend("static/herbs-news.json", [
    {
        "date": TODAY_MD,
        "tags": [
            {"text": "产地快讯", "class": "hot"},
            {"text": "旋覆花产新", "class": "info"},
            {"text": "猪苓下行", "class": "warn"},
            {"text": "日指数1254", "class": "default"}
        ],
        "content": "8月31日药通网/中药材天地网产地快讯：合欢花（河北安国52-55元）、天花粉、马兜铃、杜仲、苦地丁价格走稳；旋覆花产新上调（统38元、手选45元）；丹参、远志、柴胡、连翘、石菖蒲、茯苓、陈皮按需无变；猪苓疲软下行（小统70元、大统95-100元）；日指数1254.34、月指数1267.02。",
        "url": "https://www.yt1998.com/",
        "sources": ["药通网", "中药材天地网"]
    },
    {
        "date": TODAY_MD,
        "tags": [
            {"text": "百合大跌", "class": "danger"},
            {"text": "扩种过剩", "class": "warn"},
            {"text": "浙贝母小涨", "class": "info"}
        ],
        "content": "近期（中药材圈子/药通网）百合价格深跌：亳州市场统货由8月初约30元跌至25元、选货降至33-40元，较2025年高位95元/选货110元几近腰斩再腰斩；主因连年扩种致供应放量、库存偏高，短期供大于求难扭转。浙贝母产区购货商增多、无硫统片145-150元小幅上扬。",
        "url": "https://www.toutiao.com/article/7679335639774396991",
        "sources": ["中药材圈子", "药通网", "今日头条"]
    }
])

# ---------- 3. bracelet-news.json ----------
prepend("static/bracelet-news.json", [
    {
        "date": TODAY_MD,
        "tags": [
            {"text": "沉香暴涨舆情", "class": "hot"},
            {"text": "99元vs百万", "class": "warn"},
            {"text": "野生≠种植", "class": "info"}
        ],
        "content": "8月底（什么值得买/沉香之家）沉香圈再现「暴涨」舆情——小红书、知乎、抖音商家号密集渲染「野生沉香价格飙升/市场价十万到百万」，同期却有99元种植奇楠手串在批发；同款「沉香手串」价差可达万倍。行业提示：泡沫出清后价格体系已透明，野生老料与人工种植料本质两市场，购前须看清产区/含油量/是否沉水，警惕泡油压缩仿品。",
        "url": "https://post.m.smzdm.com/p/avgwgzdm",
        "sources": ["什么值得买", "沉香之家", "爱企查"]
    }
])

# ---------- 4. zisha-news.json ----------
prepend("static/zisha-news.json", [
    {
        "date": TODAY_MD,
        "tags": [
            {"text": "保利义品堂", "class": "hot"},
            {"text": "9/1举槌", "class": "info"},
            {"text": "春拍跌超50%", "class": "warn"}
        ],
        "content": "8月31日（保利拍卖/今日头条）北京保利2026「义品堂」第8期线上直播拍卖已上线（9/1—9/12举槌），23个专场含「匠造茶泥——当代紫砂壶」专场；同期行业复盘：2026春拍内地紫砂专场成交总额同比下滑超50%、当代紫砂流拍率超九成，行情跌回2000年前后水平，名家老壶（顾景舟等）相对抗跌。",
        "url": "https://so.html5.qq.com/page/real/search_news?docid=70000021_0276a91561c02752",
        "sources": ["保利拍卖", "今日头条", "丁砂泥绘"]
    }
])

# ---------- 5. console-news.json ----------
prepend("static/console-news.json", [
    {
        "date": TODAY_MD,
        "tags": [
            {"text": "Switch 2", "class": "hot"},
            {"text": "9/1涨价", "class": "warn"},
            {"text": "8/31末班车", "class": "info"}
        ],
        "content": "8月31日（IGN/IBTimes）Switch 2 美版9/1起由$449.99涨至$499.99（加/欧同步），今天是「Choose Your Game」捆绑包（$499.99含一游戏）最后一天，之后同价仅得裸机；涨价归因AI推高DRAM/存储价格，索尼微软年内亦涨价。新捆绑包：马里奥卡丁车世界版9月底$549.99、Sports Resort版10/22 $529.99（均含3月NSO）。",
        "url": "https://www.ibtimes.sg/nintendo-switch-2s-499-bundle-one-free-game-ends-aug-31-what-buyers-can-do-92718",
        "sources": ["IGN", "IBTimes", "Nintendo", "9to5Toys"]
    },
    {
        "date": TODAY_MD,
        "tags": [
            {"text": "GTA6 11/19", "class": "hot"},
            {"text": "NS2移植潮", "class": "info"},
            {"text": "巫师3重制", "class": "default"}
        ],
        'content': '8月31日（gamescom汇总/数毛社）R星Famitsu采访再确认《GTA6》2026年11月19日发售、对所有平台表现「完全满意」、首发不重蹈2077覆辙；PS5 Pro或被爆支持60帧。NS2移植潮：《巫师3 重制版》Switch2截图首曝（9/29上线、原版免费升）、"艾尔登法环 褪色者版"日本缺货炒至$120、卧龙苍天陨落完全版Switch2 9/3、鬼武者剑之道9/4。',
        "url": "https://feed.gg/story/nintendo-switch-2-price-increase-discussion/article/warning-this-is-your-last-chance-to-buy-a-switch-2-before-the-price-hike-3f2a8148",
        "sources": ["gamescom", "Digital Foundry", "GameSpot", "IGN"]
    }
])

# ---------- 6. marvel-news.json ----------
prepend("static/marvel-news.json", [
    {
        "date": TODAY_MD,
        "tags": [
            {"text": "蜘蛛侠破纪录", "class": "hot"},
            {"text": "影史第三/四", "class": "info"},
            {"text": "复联4重映9/25", "class": "default"}
        ],
        'content': '8月31日（微博/Box Office Mojo）"蜘蛛侠：崭新之日"全球票房升至影史第三/第四（各源分歧：微博8/31称23.32亿列第四、AceShowbiz称破23.8亿超《阿凡达2》列第三），北美第五周末连冠、累计约$8.915亿；中国内地累计约¥15.35亿（猫眼上映34天）。漫威官宣《复联4》重映"Endgame Encore"9/25登场含《毁灭日》前瞻；《复仇者联盟：毁灭日》定档12/18。',
        "url": "https://weibo.com/3930523361/5337937811605374",
        "sources": ["微博", "Box Office Mojo", "AceShowbiz", "猫眼"]
    },
    {
        "date": TODAY_MD,
        "tags": [
            {"text": "Ghost Rider 2028", "class": "hot"},
            {"text": "黑豹3 2028.12", "class": "info"},
            {"text": "毁灭日12/18", "class": "default"}
        ],
        "content": "2026圣地亚哥漫展（GamesRadar/Croma）明确MCU后续：Ghost Rider（瑞恩·高斯林主演、沙恩·利维执导）确认2028年上映；《黑豹3》定档2028年12月15日，大卫·乔森饰新黑豹、莱蒂希娅·赖特/温斯顿·杜克回归，瑞恩·库格勒继续执导；未定名死侍电影在开发中。已定档：蜘蛛侠崭新之日(在映)、复联4重映9/25、复仇者联盟毁灭日12/18、秘密战争12/17/2027。",
        "url": "https://gamesradar.com/new-marvel-tv-shows",
        "sources": ["GamesRadar", "Croma", "SDCC 2026"]
    }
])

# ---------- 7. fsd-news.json (static/tesla/) ----------
prepend("static/tesla/fsd-news.json", [
    {
        "date": TODAY_MD,
        "tags": [
            {"text": "舆论再发酵", "class": "hot"},
            {"text": "可订阅≠可用", "class": "info"},
            {"text": "待官方确认(L2)", "class": "warn"}
        ],
        "content": "8月31日（头条/新浪）FSD入华风波再发酵：自媒体复盘「8/21北美官网中国移出订阅名单→8/25上海数据中心人去楼空传闻→8/26特斯拉中国辟谣报案」链条，称「特斯拉不行了」属情绪判断而非事实；厘清「可订阅地区」移除≠退出中国，「可使用地区」列表China仍在。业内共识：技术实力在、落地时间仍「待官方确认(L2监督辅助)」，监管/审批/本土化三关卡未过，9月底前若无官宣则Q3冲刺存跳票风险。",
        "url": "https://www.toutiao.com/w/1875011552235593/",
        "sources": ["今日头条", "新浪财经", "MotorsMachine", "汽车之家"]
    }
])

# ---------- 9. health-tea-news.json ----------
prepend("static/health-tea-news.json", [
    {
        "date": TODAY_MD,
        "tags": [
            {"text": "半年2240亿", "class": "hot"},
            {"text": "+27.6%", "class": "info"},
            {"text": "男性超女性", "class": "default"}
        ],
        "content": "2026上半年药食同源行业数据（行业报告/中国保健营养）：终端市场规模2240亿元、同比+27.6%，全年有望破4500亿、全产业链估值超2万亿；休闲养生零食同比+40%(Q2+181%)、新式草本茶咖350亿成年轻刚需。消费画像颠覆：18-35岁占62%、男性56.1%首超女性；106种食药物质目录扩容、监管合规元年，普通食品严禁疗效宣传。聚焦消费品，不与中药材行情混淆。",
        "url": "https://www.yt1998.com/",
        "sources": ["中国保健营养", "行业研究报告", "艾媒咨询"]
    }
])

# ---------- 10. sheyang-news.json ----------
prepend("static/sheyang-news.json", [
    {
        "date": TODAY_MD,
        "tags": [
            {"text": "暴雨橙警", "class": "danger"},
            {"text": "射阳00:23", "class": "warn"},
            {"text": "盐城黄警", "class": "info"}
        ],
        "content": "8月31日（中国天气网/腾讯）射阳县气象台00:23升级发布暴雨橙色预警信号：预计凌晨到白天兴桥、合德、海通、海河、千秋、临海等镇6小时雨量150mm或小时75mm以上、伴雷电和局地7-9级雷暴大风，县水利/应急/气象联合提醒防范；盐城市气象台12:34继续发布暴雨黄色预警信号，落区点名射阳等县市区。30日05时—31日08时射阳面雨量74.7mm、海区最大阵风10级（华能H1平台）。与台风监测互补。",
        "url": "https://www.weather.com.cn/alarm/newalarmcontent.shtml?file=101190705-20260831003043-0203.html",
        "sources": ["中国天气网", "国家预警信息发布中心", "腾讯新闻", "盐城发布"]
    }
])

# ---------- 11. chinajoy-news.json ----------
prepend("static/chinajoy-news.json", [
    {
        "date": TODAY_MD,
        "tags": [
            {"text": "时空低语3A", "class": "hot"},
            {"text": "国风主机", "class": "info"},
            {"text": "抵抗者FPS", "class": "default"}
        ],
        "content": "ChinaJoy虽于8/3收官，但国产单机热度延续（8/2单机游戏动态）：星辰无双首款科幻3A《时空低语》披露——四线性章节+一半开放章节、四年投入超20亿、融入敦煌元素、计划2028-29上线；国风主机游戏《猿公剑》《古神：风里希》《一盏秋声：锦衣卫》试玩排长队（前两款预计明年、古神2028）；抗战单机FPS《抵抗者》CJ试玩排队两小时、B站实机单日破800万。",
        "url": "https://view.inews.qq.com/k/20260802A04PEL00?refer=cp_1009",
        "sources": ["游戏葡萄", "上观新闻", "新闻晨报", "界面"]
    }
])

# ---------- 12. marvel-boxoffice.json ----------
d = load("static/marvel-boxoffice.json")
d["updated"] = TODAY
d["movie"]["updated"] = TODAY
d["movie"]["boxOffice"]["worldwide"] = "约 23.3–23.8 亿美元（各源分歧：微博8/31称 $23.32B 列影史第四；AceShowbiz称破 $23.8B 超《阿凡达2》列第三；Box Office Mojo Top2026 列 $2.0B+）"
d["movie"]["boxOffice"]["domestic"] = "约 8.915 亿美元（$891.5M，第五周末连冠，距《星战7》北美影史 $936.7M 仅差约 $45M）"
d["movie"]["boxOffice"]["international"] = "约 14.4 亿美元（$1.44B，由全球减北美测算；66个海外市场夺冠）"
d["movie"]["boxOffice"]["china"] = "约 ¥15.35–15.36 亿元（猫眼实时：上映34天15.36亿；最大海外票仓，密钥延期至9/28）"
d["movie"]["status"] = "正在热映 · 第25周(8/30)北美五连冠、累计约$8.915亿($891.5M)距《星战7》北美影史仅差约$45M；全球粗报约23.3–23.8亿美元（各源分歧：微博8/31列第四、AceShowbiz称破23.8亿超《阿凡达2》列第三）· 中国内地累计约¥15.35亿(猫眼上映34天)、密钥延期至9/28 · 2026全球票房年冠有力竞争者"
d["movie"]["milestones"] = [
    "北美第五周末连冠，累计约$891.5M，距《星战7》北美影史$936.7M仅差约$45M",
    "全球粗报约23.3–23.8亿美元（各源分歧：影史第三 vs 第四，须标注各源测算差异）",
    "中国内地累计约¥15.35亿（猫眼实时上映34天15.36亿），刷新蜘蛛侠系列纪录、密钥延至9/28",
    "烂番茄新鲜度90–93%、爆米花98%；猫眼9.5/淘票票9.2"
]
d["sources"] = list(dict.fromkeys(d.get("sources", []) + ["Box Office Mojo", "AceShowbiz", "微博", "猫眼/灯塔"]))
save("static/marvel-boxoffice.json", d)

# ---------- 13. apple-news.json ----------
prepend("static/apple-news.json", [
    {
        "date": TODAY_MD,
        "tags": [
            {"text": "9/10发布", "class": "hot"},
            {"text": "特努斯接任", "class": "info"},
            {"text": "折叠屏Ultra", "class": "default"},
            {"text": "待官方确认", "class": "warn"}
        ],
        "content": "8月31日（IT之家/彭博/环球网）苹果确认9月9日太平洋10点（北京9/10凌晨1点）「Surprise and Shine」发布会——为新CEO约翰·特努斯9/1接替库克后首秀；首发iPhone 18 Pro/Pro Max（A20 Pro 2nm/WMCM/可变光圈/C2基带）+首款折叠屏iPhone Ultra（外5.3/内7.8英寸、侧边Touch ID、砍Face ID），标准版18/18e/Air2延至2027春；受2nm+存储涨价Pro起售或涨$200-300（待官方确认）。",
        "url": "https://weibo.com/1642632622/5337908610336012",
        "sources": ["IT之家", "彭博", "环球网", "微博"]
    }
])

# ---------- 8. typhoon.json (structured) ----------
d = load("static/typhoon.json")
d["updated"] = "2026-08-31T14:00:00+08:00"
d["headline"] = "〔14:00 午班巡检·无新增正式预警，维持「盐城黄警+射阳橙警」双预警叠加；沙德尔残涡移入南海北部或复活为热带低压/热带风暴级（待官方确认），对射阳无直接风力贡献；盐城周度展望明确风雨过程延续至9/2渐止、31日海区8-9级阵风；县级射阳暴雨橙警（00:23升级、县城合德镇在落区核心）截至14:00仍未解除/降级，综合维持「高」风险/橙色落区〕"
feed_item = {
    "date": "8月31日 14:00",
    "content": "〔14:00 午班巡检续报·沙德尔残涡南海北部或复活（待官方确认），盐城/射阳预警维持〕① 无新增正式预警：自12:34盐城市暴雨黄色预警后至14:00，未检索到盐城/射阳新一期暴雨类预警发布，维持「盐城黄警+射阳橙警」双预警叠加；县级射阳暴雨橙警（00:23升级、6小时150mm/小时75mm、县城合德镇在落区核心）截至14:00仍未解除或降级。② 残涡动向：沙德尔(2618)残涡已移入南海北部，与南海季风槽合并后或再发展为热带低压甚至热带风暴级（海南省气象台31日09:30继续发布暴雨四级预警），是否重新编号待中央气象台确认；路径偏南转东、远离江苏，对射阳无直接风力贡献。③ 其他系统：23号「班朗」远洋北上变性为温带气旋、22号「艾涛」已停止编号，均对我国无影响。④ 收尾时点：盐城周度展望明确保本风雨过程延续至9月2日渐止，31日海区8-9级阵风。综合维持「高」风险/橙色落区，本板块持续高频监测。"
}
d["feed"] = [feed_item] + d["feed"]
d["feed"] = d["feed"][:8]
if "sheyang" in d and isinstance(d["sheyang"], dict):
    d["sheyang"]["riskLabel"] = "**射阳维持「高」风险（8月31日 14:00）：盐城市气象台12时34分继续发布暴雨黄色预警信号（正式预警·落区点名射阳），县级射阳县气象台00时23分升级发布的暴雨橙色预警信号截至14:00仍在效、未解除未降级，县城合德镇仍处橙色落区核心（6小时150毫米／小时75毫米、伴局地7到9级雷暴大风）。沙德尔残涡已移入南海北部、或复活为热带低压/热带风暴级（待官方确认），路径远离江苏、对射阳无直接风力贡献；本轮风雨由残余环流＋季风槽＋冷空气共同维持，预计延续至9月2日渐止。**"
save("static/typhoon.json", d)

print("ALL JSON UPDATES DONE")
