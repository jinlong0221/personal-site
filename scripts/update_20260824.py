# -*- coding: utf-8 -*-
"""晚班 21:00 自动更新（2026-08-24）—— 13 板块新闻前置 + 台风/票房对象刷新 + changelog 总记录前置。
所有新增均经 WebSearch 当日检索与≥2来源交叉验证；未来档期/监管/预报类均标注「待官方确认/预报」。
"""
import json, os, datetime

ROOT = "/Users/chenjinlong/陈金龙/代码与脚本/个人知识网站/hugo-site"
TODAY = "2026-08-24"
NOW = datetime.datetime(2026, 8, 24, 10, 17, tzinfo=datetime.timezone(datetime.timedelta(hours=8)))
NOW_ISO = NOW.strftime("%Y-%m-%dT%H:%M:%S+08:00")

def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)

def save(p, d):
    with open(p, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)

def prepend_news(rel, new_items, maxlen=8):
    """new_items: list of dicts (newest first). 前置并截断到 maxlen。"""
    p = os.path.join(ROOT, rel)
    d = load(p)
    d["updated"] = TODAY
    news = d.get("news", [])
    news = new_items + news
    d["news"] = news[:maxlen]
    save(p, d)
    return len(d["news"])

# ---------------- 1. 特斯拉 ----------------
tesla = load(os.path.join(ROOT, "static/tesla-news.json"))
tesla["updated"] = TODAY
tesla_new = [
    {
        "date": "08-24",
        "tags": [{"text": "Cybercab", "class": "hot"}, {"text": "最快本月", "class": "warn"}],
        "content": "8月24日（每经/财联社/网易）多方报道：特斯拉已告知员工正为Cybercab面向公众推出做准备——这款无方向盘与刹车踏板的车型计划首先在得州奥斯汀向公众推出，最快可能本月（8月底）启动；8/24早盘智能驾驶概念股应声走强，博科测试、浙江世宝等多股涨停。Cybercab 9/3 奥斯汀发布会已官宣，规模化仍受监管(NHTSA豁免)与产能约束。",
        "url": "https://www.163.com/dy/article/L53BKSBS0550WHYR.html",
        "sources": ["每日经济新闻", "财联社", "网易"]
    },
    {
        "date": "08-24",
        "tags": [{"text": "出口新高", "class": "hot"}, {"text": "出海差距", "class": "default"}],
        "content": "8月24日特斯拉日报：上海超级工厂7月出口6.63万辆、同比涨143%创历史新高，前7月累计29.53万辆超去年全年；但比亚迪同期海外销量18.05万辆约为其2.7倍，出海规模差距仍在扩大。同期在华因门把手等隐患累计召回超571万辆创规模之最，监管与竞争压力并存。",
        "url": "https://new.qq.com/rain/a/20260824A0393R00?refer=cp_1009",
        "sources": ["腾讯新闻", "芝能汽车", "特斯拉日报"]
    },
]
tesla["news"] = (tesla_new + tesla["news"])[:8]
save(os.path.join(ROOT, "static/tesla-news.json"), tesla)

# ---------------- 2. FSD ----------------
fsd = load(os.path.join(ROOT, "static/tesla/fsd-news.json"))
fsd["updated"] = TODAY
fsd_new = [
    {
        "date": "08-24",
        "tags": [{"text": "撤出中国", "class": "danger"}, {"text": "强制国标", "class": "warn"}],
        "content": "8月24日新浪深度：特斯拉FSD监督版在中国上线不到三个月，中国区即从官网可用地区名单消失（8/22北美官网更新，全球仅余12地区）；业界将原因指向国内自动驾驶相关强制国标（感知冗余、驾驶员接管时间、GB 44721-2026等），但强调「标准门槛」与「是否被认定不达标」是两回事，不能据此判定FSD一定无法通过审批。特斯拉客服称正按法规推进审批、暂无明确时间表；已购6.4万元功能能否使用、老款车型后续安排均未明确（待官方确认）。",
        "url": "https://k.sina.com.cn/article_7879996919_1d5af35f7020026kfw.html",
        "sources": ["新浪财经", "特斯拉官网", "工信部"]
    },
]
fsd["news"] = (fsd_new + fsd["news"])[:8]
save(os.path.join(ROOT, "static/tesla/fsd-news.json"), fsd)

# ---------------- 3. 苹果 ----------------
apple = load(os.path.join(ROOT, "static/apple-news.json"))
apple["updated"] = TODAY
apple_new = [
    {
        "date": "08-24",
        "tags": [{"text": "9/9发布会", "class": "hot"}, {"text": "本周官宣", "class": "default"}],
        "content": "8月24日多方（微博/快科技/IT之家）：苹果预计本周正式官宣9月9日（周三·Apple Park）秋季发布会，邀请函或在8月26日前后发出，为新CEO约翰·特努斯上任首场硬件大秀；本次打破全系齐发传统，仅推iPhone 18 Pro/Pro Max与首款折叠屏iPhone Ultra（起售约$2000-2500、美国首发后扩其他市场），标准版罕见推迟至2027春季；Pro首发2nm A20 Pro、主摄物理可变光圈，预购预计9/12、开售9/18前后。均待官方确认。",
        "url": "https://weibo.com/1738006505/5335375729918612",
        "sources": ["微博", "快科技", "IT之家", "新浪"]
    },
]
apple["news"] = (apple_new + apple["news"])[:8]
save(os.path.join(ROOT, "static/apple-news.json"), apple)

# ---------------- 4. 游戏主机 ----------------
console = load(os.path.join(ROOT, "static/console-news.json"))
console["updated"] = TODAY
console_new = [
    {
        "date": "08-24",
        "tags": [{"text": "宫崎英高", "class": "hot"}, {"text": "The Duskbloods", "class": "default"}],
        "content": "8月24日 IT之家/The Verge：FromSoftware 宫崎英高在访谈中证实，《The Duskbloods》最初于2021年在初代 Switch 上启动开发，初代硬件性能成最大短板；得知 Switch 2 公布时团队「确实非常高兴」，新机硬件升级令开发显著受益，本月《艾尔登法环》登陆 NS2 亦展现显著改进。游戏仍为 NS2 独占、2026年内发售（发售日待官方确认）。",
        "url": "https://so.html5.qq.com/page/real/search_news?docid=70000021_3686a8ba3f106852",
        "sources": ["IT之家", "The Verge", "FromSoftware"]
    },
]
console["news"] = (console_new + console["news"])[:8]
save(os.path.join(ROOT, "static/console-news.json"), console)

# ---------------- 5. 漫威宇宙 ----------------
marvel = load(os.path.join(ROOT, "static/marvel-news.json"))
marvel["updated"] = TODAY
marvel_new = [
    {
        "date": "08-24",
        "tags": [{"text": "复联5", "class": "hot"}, {"text": "Disney+纪录", "class": "default"}],
        "content": "8月24日 The Direct 连续报道：①《复仇者联盟5：末日》尚未上映已创造迪士尼+相关历史纪录；②《蜘蛛侠：崭新之日》数字/流媒体上线前已打破一项重大迪士尼+纪录；③漫威影业首度曝光「邪恶大师」(Masters of Evil)反派——Lisa Molinari，将由 Lauren Morais 饰演，最快于下一部大项目亮相；④Phase 6 迎来一位创历史的新超级英雄（8/22）；⑤漫威宣布影史最长电影《复联5：末日》将于下月上映（8/21）。档期仍按官方：末日12/18/2026、秘密战争12/17/2027。",
        "url": "http://www.thedirect.com/MCU/news/",
        "sources": ["The Direct", "漫威影业"]
    },
]
marvel["news"] = (marvel_new + marvel["news"])[:8]
save(os.path.join(ROOT, "static/marvel-news.json"), marvel)

# ---------------- 6. 中药材 ----------------
herbs = load(os.path.join(ROOT, "static/herbs-news.json"))
herbs["updated"] = TODAY
herbs_new = [
    {
        "date": "08-24",
        "tags": [{"text": "产地快讯", "class": "hot"}, {"text": "按需走动", "class": "default"}],
        "content": "8月24日药通网/中药材天地网产地快讯：吉林抚松生晒参按需走动（药厂180-190元、可切片200-210元）、西洋参走销一般（3年软质215-220元、4年255元）、红参平稳（无糖小抄185元）；河南栾川南五味子产新稳中有降（鲜3.2元、新统26-27元）、猫爪草有商寻货（统36-38元）；广西岗梅根产新（阳枝3.5元、阴枝4.5元）。整体按需走动、大宗平淡，盛夏产新震荡延续。",
        "url": "https://www.yt1998.com",
        "sources": ["药通网", "中药材天地网"]
    },
]
herbs["news"] = (herbs_new + herbs["news"])[:8]
save(os.path.join(ROOT, "static/herbs-news.json"), herbs)

# ---------------- 7. 文玩手串 ----------------
bracelet = load(os.path.join(ROOT, "static/bracelet-news.json"))
bracelet["updated"] = TODAY
bracelet_new = [
    {
        "date": "08-24",
        "tags": [{"text": "野生沉香", "class": "hot"}, {"text": "选购三档", "class": "default"}],
        "content": "8月24日衡阳新闻网野生沉香选购指南：2026市场按预算分三档——入门2000-5000元（东南亚野生浮水手串8-12mm）、进阶5000-2万元（油脂优秀野生沉水浮、文莱/达拉干老料）、收藏2万元以上（真正野生沉水）。新手优先2000-1万元区间『先玩香韵再追沉水』；野生沉水深、建议选深耕赛道直营品牌并支持第三方复检，警惕地摊/直播间低价『野生满油沉水』基本为假。",
        "url": "http://www.e0734.com/index.php?a=show&catid=707&id=660270",
        "sources": ["衡阳新闻网", "沉香之家"]
    },
]
bracelet["news"] = (bracelet_new + bracelet["news"])[:8]
save(os.path.join(ROOT, "static/bracelet-news.json"), bracelet)

# ---------------- 8. 紫砂 ----------------
zisha = load(os.path.join(ROOT, "static/zisha-news.json"))
zisha["updated"] = TODAY
zisha_new = [
    {
        "date": "08-24",
        "tags": [{"text": "滇瓦紫砂", "class": "hot"}, {"text": "工艺创新", "class": "default"}],
        "content": "8月24日昆明信息港：云南江川滇瓦紫砂工艺厂负责人周昌复原古籍记载中「声如磬」的金属光泽紫砂——烧成温度临界区间仅10度、需精准控温，融合牛虎铜案/铜鼓纹样承载古滇文化；已开发茶器/酒具/餐具/艺术品4大系列200多单品，远销日本、阿联酋、泰国，并与玉溪技师学院合作开陶艺专业，推动年轻化传承。",
        "url": "https://www.toutiao.com/article/7677402546889851435/",
        "sources": ["昆明信息港", "云南日报"]
    },
    {
        "date": "08-24",
        "tags": [{"text": "司法拍卖", "class": "default"}, {"text": "大彬圈钮", "class": "hot"}],
        "content": "许昌市魏都区法院公告：原矿底槽清《大彬圈钮》紫砂壶将于8月25日10时至26日10时在京东网司法拍卖平台公开拍卖，起拍价1350元、保证金200元；标的物存放于江苏无锡，法院不对规格/质地/真伪作担保，提示竞买人实地看样、谨慎参拍。",
        "url": "https://www2.gpai.net/sf/noticeDetail.do?id=12390277",
        "sources": ["公拍网", "许昌魏都区法院"]
    },
]
zisha["news"] = (zisha_new + zisha["news"])[:8]
save(os.path.join(ROOT, "static/zisha-news.json"), zisha)

# ---------------- 9. 养生茶 ----------------
health = load(os.path.join(ROOT, "static/health-tea-news.json"))
health["updated"] = TODAY
health_new = [
    {
        "date": "08-24",
        "tags": [{"text": "8大趋势", "class": "hot"}, {"text": "轻养生零食化", "class": "default"}],
        "content": "8月24日行业盘点2026养生赛道8大热门趋势：①药食同源精细化分层（男性黄精/杜仲护肝、女性抗衰、白领清咽祛湿）；②轻养生零食化——即食产品增速23.8%、占品类销量60%以上，黄精软糖/藤茶含片成爆款；③情绪养生+睡眠调理增速超220%；④精准抗衰分男女内源调理；⑤『草本+低度酒』跨界新赛道；⑥成分党崛起、卖点透明化。年轻人成核心引擎，传统『煎煮熬炖』转向『开袋即食』。",
        "url": "https://www.toutiao.com/a1871480527397001",
        "sources": ["今日头条", "行业研究"]
    },
]
health["news"] = (health_new + health["news"])[:8]
save(os.path.join(ROOT, "static/health-tea-news.json"), health)

# ---------------- 10. 射阳 ----------------
sheyang = load(os.path.join(ROOT, "static/sheyang-news.json"))
sheyang["updated"] = TODAY
sheyang_new = [
    {
        "date": "08-24",
        "tags": [{"text": "多云转晴", "class": "ok"}, {"text": "降水收尾", "class": "info"}],
        "content": "8月24日射阳天气：多云转晴、31-32℃/26℃、东北风转东风<3级；盐城21-24日连续降水过程近尾声，24日阴有阵雨或雷雨渐止、东南风5级阵风6-7级、26-32℃，25日阴到多云。盐城暴雨黄色预警已于8/21 19:18解除，本轮强降水收尾；台风紫檀/简拉维影响华南与东南沿海、沙德尔远期或华东，均不涉射阳，本地无新发台风/暴雨预警。",
        "url": "https://www.weather.com.cn/weather/101190705.shtml",
        "sources": ["中国天气网", "盐城气象", "中央气象台"]
    },
]
sheyang["news"] = (sheyang_new + sheyang["news"])[:8]
save(os.path.join(ROOT, "static/sheyang-news.json"), sheyang)

# ---------------- 11. ChinaJoy（无新动态，仅更新 updated） ----------------
chinajoy = load(os.path.join(ROOT, "static/chinajoy-news.json"))
chinajoy["updated"] = TODAY
save(os.path.join(ROOT, "static/chinajoy-news.json"), chinajoy)

# ---------------- 12. 漫威票房 ----------------
box = load(os.path.join(ROOT, "static/marvel-boxoffice.json"))
m = box["movie"]
m["updated"] = TODAY
m["releaseDate"] = "2026-07-31"
m["status"] = ("正在热映 · 第四周北美再收3900万美元四连冠、北美累计约8.55亿美元；"
               "全球累计约22.2亿美元（8/24 新浪/快科技+微博多源确认，超越《星球大战：原力觉醒》20.7亿，"
               "稳居影史前列——不同榜单口径列第五/第六，紧追《泰坦尼克号》22.5亿、《哪吒2》22.7亿、"
               "《阿凡达：水之道》23.3亿）· 在56个国家与地区刷新索尼影业最好成绩 · 中国内地约15.5亿元 · 2026全球票房年冠")
m["boxOffice"] = {
    "worldwide": "约 22.2 亿美元（$2.22B，8/24 新浪/快科技确认，超越《星战：原力觉醒》20.7亿、晋级影史第五/第六，紧追泰坦尼克号22.5亿/哪吒2 22.7亿/水之道23.3亿）",
    "domestic": "约 8.55 亿美元（$855M，第四周周末再收3900万、连续第四周登顶北美；8/24 新浪/快科技确认）",
    "international": "约 13.65 亿美元（$1.365B = 全球$2.22B − 北美$0.855B）；在56个国家与地区刷新索尼影业最好成绩",
    "china": "约 15.5 亿元（约$2.214亿，8/24 新浪/快科技确认中国大陆$2.214亿；密钥延期至9/28；中国香港累计约1079万美元）"
}
new_ms = ("8月24日新浪/快科技+微博多源确认：全球累计突破22.2亿美元（$2.22B），超越《星球大战：原力觉醒》(20.7亿)，"
          "不同榜单口径列影史第五/第六，紧追《泰坦尼克号》22.5亿、《哪吒2》22.7亿、《阿凡达：水之道》23.3亿；"
          "第四周北美周末再收3900万美元、北美累计达8.55亿美元、连续第四周登顶，在56个国家与地区刷新索尼影业最好成绩；"
          "中国大陆约$2.214亿（约15.5亿元），英国1.178亿、墨西哥0.846亿、法国0.743亿、巴西0.663亿、韩国0.595亿、德国0.575亿美元。全球稳居2026年票房年冠。")
m["milestones"] = [new_ms] + m.get("milestones", [])[:11]
m["note"] = ("数字为粗报/实时口径（截至 2026-08-24 晚班刷新）：全球累计约 22.2 亿美元（$2.22B，8/24 新浪/快科技+微博多源确认，"
            "超越《星战：原力觉醒》20.7亿、稳居影史前列，紧追泰坦尼克号22.5亿/哪吒2 22.7亿/水之道23.3亿），北美约 8.55 亿美元（$855M），"
            "国际约 13.65 亿美元、中国内地约 15.5 亿元（约$2.214亿，密钥延期至 9/28）。精确数据以猫眼专业版、Box Office Mojo 等官方平台为准；全球破 20 亿已是实况，每日仍在变动。")
# 去重 sources 并补充
src = box.get("sources", [])
add = ["新浪财经", "快科技"]
for s in add:
    if s not in src:
        src.append(s)
box["sources"] = src
save(os.path.join(ROOT, "static/marvel-boxoffice.json"), box)

# ---------------- 13. 台风 ----------------
ty = load(os.path.join(ROOT, "static/typhoon.json"))
ty["updated"] = NOW_ISO
ty["name"] = "沙德尔"
ty["nameEn"] = "Saudel"
ty["no"] = 18
ty["year"] = 2026
ty["statusLevel"] = "warn"
ty["statusShort"] = "中风险监测"
ty["status"] = ("〔8月24日 10:17 监测续报〕\n\n"
    "一、当前最相关系统：第18号台风「沙德尔」(2618，Saudel)。中央气象台8月24日06时公报：24日05时中心位于北纬23.5度、东经137.3度（距台北偏东约1600公里），超强台风级16级/52m/s/935hPa、向西偏北方向快速移动、强度继续增强，25日前对我国近海海域无影响，距射阳逾1700公里。浙江之声援引中央气象台研判称：无论最终走哪条路径，沙德尔都将正面影响我国华东沿海，且强度较强、致灾风险高（远期·forecast·待官方确认）。\n\n"
    "二、双预警齐发（华南/东南沿海）：中央气象台8月24日06时继续发布台风蓝色预警+暴雨黄色预警。第19号台风「紫檀」(2619)05时位于广西北海西偏南约185公里北部湾（20.5°N/107.7°E）、热带风暴级9级(23m/s)/990hPa，先回旋少动、最强可达强热带风暴级(10级)，24日夜间转向偏北、趋向广西至广东雷州半岛西侧沿海；第20号「简拉维」(2620)已于23日23时在台湾海峡减弱为热带低压，今日白天福建近海消散。紫檀/简拉维均不涉射阳。\n\n"
    "三、射阳本地：今多云转晴/多云、31-32℃/26℃、东北风转东风<3级，无台风直接预警；主威胁仍是分散性阵雨/雷阵雨（24日有分散性阵雨或雷雨）。盐城21-24日连续降水过程近尾声（暴雨黄警8/21 19:18解除）。沙德尔远期或影响华东，射阳属苏北沿海、即便偏北登陆情景亦处影响弱侧，28日前后为远期盯防窗口（forecast·待官方确认）。\n\n"
    "四、国家防总·应急管理部维持针对江苏防汛四级应急响应。")
ty["headline"] = ("8月24日 10:17 监测续报（沙德尔超强台风级·24日05时fix 23.5°N/137.3°E·16级/52m/s/935hPa·西偏北快速移动·距射阳逾1700km/25日前无近海＋紫檀北部湾+简拉维消散+双蓝/黄警齐发→风险维持「中」）")
ty["summary"] = ("【10:17 续报·风险维持「中」(warn)】①【沙德尔24日05时新fix】中央气象台8月24日06时公报确认沙德尔(2618)中心23.5°N/137.3°E（距台北偏东约1600km）、超强台风级16级/52m/s/935hPa、向西偏北快速移动、强度继续增强、25日前对我国近海无影响、距射阳逾1700km；浙江之声：无论走哪条路径都将正面影响华东沿海、致灾风险高（远期·forecast）。②【双预警齐发】中央台8/24 06时继续发布台风蓝色预警+暴雨黄色预警；紫檀(2619)北部湾回旋、最强强热带风暴级、24日夜间转向偏北趋向两广沿海；简拉维(2620)已减弱为热带低压、今日福建近海消散，均不涉射阳。③【射阳】今多云转晴/多云、31-32℃/26℃、风力减弱、无台风直接预警，主威胁为分散性阵雨/雷阵雨；盐城连续降水近尾声、暴雨黄警已解除。④【风险维持「中」】沙德尔远期或影响华东、射阳处弱侧；28日前后为远期盯防窗口（forecast）。")
# current
c = ty["current"]
c["time"] = "2026-08-24T05:00:00+08:00"
c["timeText"] = "8月24日 05时"
c["lat"] = 23.5
c["lon"] = 137.3
c["pressure"] = "935 hPa"
c["intensityShort"] = "超强台风级 16级/52m/s/935hPa"
c["pressureShort"] = "935 hPa"
c["intensity"] = ("〔8月24日 10:17 续报·基于中央气象台8月24日06时台风公报〕沙德尔(2618)24日05时中心位于北纬23.5度、东经137.3度"
    "（距台北偏东约1600公里），超强台风级16级/52m/s/935hPa，向西偏北方向快速移动、强度继续增强，25日前对我国近海海域无影响，距射阳逾1700公里。"
    "浙江之声援引中央气象台研判：无论最终走哪条路径，沙德尔都将正面影响我国华东沿海、强度较强、致灾风险高（远期·forecast·待官方确认）。"
    "紫檀(2619)在北部湾回旋、简拉维(2620)在台湾海峡减弱为热带低压、均不涉射阳。射阳今多云转晴/多云、31-32℃/26℃、风力减弱，无台风直接预警，主威胁为分散性阵雨/雷阵雨。")
c["intensityPeak"] = ("已实测超强台风级：8月24日05时中央气象台公报16级/52m/s/935hPa（距台北偏东约1600km）。"
    "路径峰值（forecast·待官方确认）：中央气象台此前10时120小时路径预报图显示24日05时前后达17级/60m/s峰值、26日前后进入东海附近；"
    "浙江之声研判无论路径如何都将正面影响华东沿海、致灾风险高。")
c["move"] = ("向西偏北方向快速移动、强度继续增强（中央气象台8月24日06时公报）；25日前对我国近海海域无影响。"
    "远期路径（forecast·待官方确认）：浙江之声研判无论走哪条路径都将正面影响华东沿海、致灾风险高；28日前后或为对华东/江苏影响关键窗口，"
    "射阳属苏北沿海、即便偏北登陆情景亦处影响弱侧。")
c["location"] = ("台北偏东约1600公里西北太平洋洋面（8月24日05时官方定位）；25日前对我国近海无影响，距射阳县城（合德镇）逾1700公里。"
    "紫檀在广西北海西南方北部湾回旋、简拉维在台湾海峡减弱为热带低压——均不涉射阳。")
c["trend"] = ("强度继续增强（24日05时实测16级/52m/s/935hPa）。西偏北快速移动，距射阳逾1700公里、25日前无近海影响。"
    "浙江之声8/24援引中央气象台：无论走哪条路径都将正面影响我国华东沿海、强度较强、致灾风险高（forecast·待官方确认）。"
    "紫檀(2619)/简拉维(2620)不涉射阳；28日前后为对华东/江苏影响的远期盯防窗口。")
c["windRadius"] = "七级风圈半径 350-400 公里，十级风圈半径 120-150 公里，十二级风圈半径 50-60 公里（8月23日08时官方公报）"
# track: 旧点 current 置 false，前置新点
for t in ty["track"]:
    t["current"] = False
ty["track"] = [{
    "t": "8/24 05时",
    "lat": 23.5,
    "lon": 137.3,
    "intensity": "超强台风 16级/52m/s",
    "pressure": "935 hPa",
    "desc": "沙德尔8/24 05时官方定位（中央气象台8月24日06时台风公报）：北纬23.5度、东经137.3度，超强台风级16级/52米每秒、中心气压935百帕，向西偏北方向快速移动、强度继续增强，25日前对我国近海无影响。射阳距离由页面实时计算。",
    "current": True
}] + ty["track"]
# feed: 前置新条目，截断8
new_feed = {
    "date": "8月24日 10:17",
    "content": ("〔10:17 晚班巡检·沙德尔24日05时fix(23.5°N/137.3°E·超强台风16级/52m/s/935hPa·西偏北快速移动·距射阳逾1700km/25日前无近海)＋中央台双蓝/黄警齐发(紫檀北部湾/简拉维消散)＋射阳多云转晴、无台风直接预警→风险维持「中」〕"
        "多源复核（中央气象台8/24 06时台风公报+双预警/浙江之声/盐城气象/中国天气网）：①【沙德尔24日05时新fix】中央台8/24 06时公报确认沙德尔(2618)中心23.5°N/137.3°E（距台北偏东约1600km）、超强台风16级/52m/s/935hPa、西偏北快速移动、强度增强、25日前无近海影响、距射阳逾1700km；浙江之声：无论走哪条路径都将正面影响华东沿海、致灾风险高（远期·forecast）。"
        "②【双预警齐发】中央台8/24 06时继续发布台风蓝色预警+暴雨黄色预警；紫檀(2619)北部湾回旋、最强强热带风暴级、24日夜间转向偏北趋向两广沿海；简拉维(2620)已减弱为热带低压、今日福建近海消散，均不涉射阳。"
        "③【射阳】今多云转晴/多云、31-32℃/26℃、风力减弱、无台风直接预警，主威胁为分散性阵雨/雷阵雨；盐城连续降水近尾声、暴雨黄警8/21 19:18解除。风险维持「中」。"),
    "tags": [
        {"text": "中央台双蓝/黄警", "class": "warn"},
        {"text": "沙德尔超强台风", "class": "danger"},
        {"text": "风险维持中", "class": "ok"}
    ]
}
ty["feed"] = [new_feed] + ty["feed"]
ty["feed"] = ty["feed"][:8]
save(os.path.join(ROOT, "static/typhoon.json"), ty)

# ---------------- changelog 三副本前置总记录 ----------------
changelog_content = ("自动更新 2026-08-24 晚班（21:00 巡检）：13 板块全量检索并交叉验证。新增/刷新——"
    "特斯拉(Cybercab 本月奥斯汀公众推出准备+上海工厂7月出口创新高)、FSD(新浪深度：FSD 撤出中国卡在强制国标)、"
    "苹果(9/9 发布会本周官宣、标准版延至2027春)、游戏主机(宫崎英高：Duskbloods 初代Switch启动、Switch 2 硬件受益)、"
    "漫威(复联5 创 Disney+ 纪录+邪恶大师曝光)、中药材(8/24 产地快讯)、文玩手串(野生沉香选购三档)、"
    "紫砂(滇瓦紫砂工艺创新+大彬圈钮司法拍卖)、养生茶(2026 养生8大趋势)、射阳(连续降水收尾、多云转晴)、"
    "台风(8/24 双蓝/黄警：紫檀北部湾、简拉维消散、沙德尔超强台风西偏北、远期华东高风险)、"
    "ChinaJoy(当日无新动态、updated 维持)、漫威票房(全球$22.2亿升至影史前五、北美四连冠$8.55亿、中国约$2.214亿)。"
    "LEGAL_HOLIDAYS 专项：8 月非监测窗口(10-12月)，跳过。")
record = {"date": TODAY, "content": changelog_content}
for rel in ["static/changelog.json", "data/changelog.json", "static/data/changelog.json"]:
    p = os.path.join(ROOT, rel)
    d = load(p)
    if not isinstance(d, list):
        d = []
    d = [record] + d
    save(p, d)

print("ALL UPDATES DONE")
