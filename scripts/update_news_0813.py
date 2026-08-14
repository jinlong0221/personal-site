#!/usr/bin/env python3
"""Update all news JSON files for 2026-08-13 daily auto-update."""
import json
import os

BASE = "/Users/chenjinlong/陈金龙/代码与脚本/个人知识网站/hugo-site/static"

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")

def tag(text, cls="default"):
    return {"text": text, "class": cls}

def news_item(date, tags_list, content, url, sources):
    return {
        "date": date,
        "tags": tags_list,
        "content": content,
        "url": url,
        "sources": sources
    }

def update_news_file(filename, new_items, max_items=9):
    """Update a news JSON file: prepend new items, trim to max_items."""
    path = os.path.join(BASE, filename)
    data = load_json(path)
    data["updated"] = "2026-08-13"
    # Prepend new items
    existing = data.get("news", [])
    data["news"] = new_items + existing
    # Trim
    data["news"] = data["news"][:max_items]
    save_json(path, data)
    print(f"  {filename}: +{len(new_items)} items, total {len(data['news'])}")

# ========== 1. Tesla News ==========
print("=== Updating tesla-news.json ===")
tesla_items = [
    news_item(
        "08-13",
        [tag("NHTSA", "warn"), tag("召回20349辆", "default")],
        "8月11日NHTSA公布：特斯拉因部分车辆近光灯亮度可能超过法规要求（违反FMVSS No.108标准），召回20349辆Model 3和Model Y。涉及2017-2023款Model 3计1614辆、2020-2023款Model Y计18735辆（占比92.1%）。该缺陷为硬件问题、无法通过OTA修复，需线下更换灯具总成。特斯拉曾于2024年3月以「无关紧要」为由向NHTSA申请豁免，2026年8月被驳回并强制召回——从发现缺陷到正式召回周期长达29个月。同期NHTSA仍在推进约120万辆Model 3/Y前下横向连杆悬架故障初步调查（7月立案），两项监管行动间隔不足一月，特斯拉在美质量管控体系面临持续压力。",
        "https://auto.news18a.com/news/storys_285529.html",
        ["NHTSA", "界面新闻", "auto.news18a.com", "网易"]
    ),
    news_item(
        "08-13",
        [tag("Starlink", "hot"), tag("全系标配", "hot")],
        "8月12日特斯拉确认Starlink卫星互联网将作为全系车型标配配置，提供最高375Mbps下行速率。此前Cybercab已率先展示集成Starlink天线硬件，此次扩展至量产乘用车阵容，意味着特斯拉地面车队与星链太空网络全面打通——在偏远地区提供不间断遥测、OTA升级与车联网服务。此举也标志着马斯克旗下SpaceX与特斯拉在卫星互联网领域的深度协同进入新阶段。运营商侧，Starlink全球用户已突破300万，覆盖100余国家和地区（请以特斯拉官方公告为准）。",
        "https://new.qq.com/rain/a/20260812A030SA00",
        ["腾讯新闻", "科技有意思", "SpaceX"]
    ),
]
update_news_file("tesla-news.json", tesla_items)

# ========== 2. FSD News ==========
print("=== Updating tesla/fsd-news.json ===")
fsd_items = [
    news_item(
        "08-13",
        [tag("中国", "hot"), tag("数据合规墙", "warn")],
        "8月13日行业分析：FSD入华审批进入最后冲刺阶段，但数据合规仍是最大壁垒。特斯拉上海临港AI训练中心虽已完成数据存储、本地训练、算法优化全链路本土化，但「数据不出境」要求与特斯拉全球统一模型架构存在结构性矛盾——中国路测数据无法回传北美总部用于全球模型迭代，中国版FSD可能在长尾场景处理上滞后于海外版本。工信部要求FSD在华定位L2级辅助驾驶（TAD），须驾驶员全程接管，禁止「完全自动驾驶」类营销表述。四部门联合终审已于7月底完成，业内预判最快8月向合规HW4.0车型分批OTA（待官方公告，不预判确切日期）。",
        "https://www.163.com/dy/article/L43VUOSV0553TDSE.html",
        ["网易号", "工信部", "美国科技媒体"]
    ),
]
update_news_file("tesla/fsd-news.json", fsd_items)

# ========== 3. Marvel News ==========
print("=== Updating marvel-news.json ===")
marvel_items = [
    news_item(
        "08-13",
        [tag("D23", "hot"), tag("X战警阵容", "hot")],
        "8月13日漫威前瞻：D23博览会8月14-16日即将在安纳海姆举行，漫威工作室预计将正式公布MCU X战警阵容。目前已知萨迪·辛克（Sadie Sink）饰琴·格雷确认登场《蜘蛛侠：崭新之日》；基特·康纳（Kit Connor）饰镭射眼、萨马拉·维文饰白皇后等传闻尚未获官方确认。Sadie Sink回应选角传言时表示「网上总有传言，我从来不知道哪些是官方的」。据Deadline报道，漫威计划在D23上揭示MCU第六阶段变种人版图全貌，包括X战警电影的时间线与选角方向（具体以D23官方发布为准）。",
        "https://www.163.com/dy/article/L43ES9HF05561FZ0.html",
        ["网易号", "Vanity Fair名利场", "Deadline", "D23博览会"]
    ),
    news_item(
        "08-13",
        [tag("蜘蛛侠", "hot"), tag("影史TOP10", "hot")],
        "8月12日蜘蛛侠系列电影官方微博宣布：《蜘蛛侠：崭新之日》上映两周全球票房达19.52亿美元（约131.93亿元人民币），强势杀入影史票房TOP10并登顶2026全球票房冠军。索尼蜘蛛侠系列11部电影24年累计票房突破685亿元人民币。该片上映6天即破10亿美元（影史第二快），北美首周末3.60亿美元刷新北美影史最高开画纪录。目前正向20亿美元俱乐部迈进（数据以猫眼专业版、Box Office Mojo、The Numbers为准）。",
        "https://www.donews.com/news/detail/8/6668895.html",
        ["DoNews", "IT之家", "蜘蛛侠电影官方微博", "Box Office Mojo"]
    ),
]
update_news_file("marvel-news.json", marvel_items)

# ========== 4. Marvel Box Office ==========
print("=== Updating marvel-boxoffice.json ===")
box_path = os.path.join(BASE, "marvel-boxoffice.json")
box_data = load_json(box_path)
box_data["updated"] = "2026-08-13"
box_data["movie"]["status"] = "正在热映 · 两周杀入影史TOP10"
box_data["movie"]["boxOffice"] = {
    "worldwide": "19.52 亿美元（约 131.93 亿元人民币）",
    "domestic": "约 6.6 亿美元",
    "international": "约 12.9 亿美元",
    "china": "约 13.2 亿元人民币（约 1.87 亿美元）"
}
box_data["movie"]["milestones"] = [
    "上映 6 天破 10 亿美元，影史第二快（仅次于《复仇者联盟4：终局之战》）",
    "北美首周末 3.60 亿美元，刷新北美影史最高开画纪录（原纪录为《复联4》3.57 亿）",
    "上映两周全球票房 19.52 亿美元，杀入影史票房 TOP10，登顶 2026 全球票房年冠",
    "超越《复仇者联盟》（15.2 亿美元），跻身影史超级英雄电影票房前四",
    "索尼蜘蛛侠系列 11 部电影 24 年累计票房突破 685 亿元人民币",
    "全球正向 20 亿美元俱乐部迈进，Sacnilk 预测最终落点或达 25 亿美元区间"
]
box_data["movie"]["note"] = "数字为粗报 / 实时口径（截至 2026-08-12），精确数据以猫眼专业版、Box Office Mojo、The Numbers 等官方平台为准；19.52 亿美元数据来源为蜘蛛侠系列电影官方微博 8/12 宣布，经 DoNews、IT之家等多源交叉确认。全球最终落点属前瞻判断，非官方定档。"
box_data["sources"] = [
    "蜘蛛侠电影官方微博",
    "猫眼专业版",
    "Box Office Mojo",
    "The Numbers",
    "DoNews / IT之家",
    "Sacnilk"
]
save_json(box_path, box_data)
print(f"  marvel-boxoffice.json: updated to $1.952B worldwide, TOP10 all-time")

# ========== 5. Herbs News ==========
print("=== Updating herbs-news.json ===")
herbs_items = [
    news_item(
        "08-13",
        [tag("药通网", "hot"), tag("亳州指数", "default")],
        "8月13日药通网《今日视点》：亳州中药材日指数报1258.85点、较前日跌0.29%，延续盛夏淡季震荡格局。市场动态：元胡（延胡索）走缓价疲、茯苓行情下滑、天花粉产新后货源增多走动迟缓、防风新货上市价偏弱；砂仁走销一般行情续滑、百合低迷下行、白芍新货增多要价较乱。上涨品种稀少：郁李仁货少上调、进口枣仁小幅上调、冬瓜皮反弹。整体看立秋产新施压地产品种、台风「白海豚」残涡对亳州产区影响暂有限，关注后续华南雨水对南药传导。康美十日指数同步走跌，总指数1493点附近徘徊。",
        "https://www.yt1998.com/scdt/ya9IrQ9Q.html",
        ["药通网", "康美中药网"]
    ),
]
update_news_file("herbs-news.json", herbs_items)

# ========== 6. Bracelet News ==========
print("=== Updating bracelet-news.json ===")
bracelet_items = [
    news_item(
        "08-13",
        [tag("沉香手串", "hot"), tag("选购指南", "default")],
        "8月13日文玩市场参考：野生沉香手串三档选购指南引发收藏圈关注。入门级（沉水浮，10年以上种植老料或50年野生）5万-20万/串，适合初次接触高端沉香的玩家；中档（沉水级，80年以上野生老料）20万-150万/串，凉甜香韵明显、适合资深香友；收藏级（百年野生老料或顶级奇楠）150万-500万以上，2025香港佳士得14mm富森红土手串曾以2300万港元成交。奇楠沉香手串基础知识同步普及：顶级芽庄白奇楠克价突破6万元、绿奇楠1.5万-5万元/克。业内提醒警惕泡油、高压注油、化学染色等造假手段，选购须认准完整产地证明与含油量检测报告（不构成投资建议）。",
        "https://www.chenxiangba.com/faq/35.html",
        ["沉香吧", "雅昌", "中国嘉德"]
    ),
]
update_news_file("bracelet-news.json", bracelet_items)

# ========== 7. Zisha News ==========
print("=== Updating zisha-news.json ===")
zisha_items = [
    news_item(
        "08-13",
        [tag("行业分析", "hot"), tag("老手退场", "warn")],
        "8月13日紫砂行业深度：近年紫砂市场出现「老手纷纷退场」现象——核心原因有三：①礼品市场与资本炒作退潮，中低端壶价格回归器物本位，利润空间大幅压缩；②供春款等明清老壶真伪难辨、流通多为后世仿作，一件供春款老壶仅以17万元成交（较早年百万级神话大幅回落），打击了老玩家信心；③年轻消费者审美转向当代简约风格，传统花货、筋纹器受众收窄。但顾景舟传世原作、陈鸣远仿生器、邵大亨精品因真迹明确仍稳居百万至千万元级，市场分化加剧——精品稀缺、普品承压。业内建议：收藏须以「真、精」为核心，关注当代国家级非遗传承人作品。",
        "https://www.toutiao.com/a7671599181828260352",
        ["今日头条", "紫砂观察"]
    ),
]
update_news_file("zisha-news.json", zisha_items)

# ========== 8. Console News ==========
print("=== Updating console-news.json ===")
console_items = [
    news_item(
        "08-13",
        [tag("Switch 2", "hot"), tag("八月大作", "hot")],
        "8月13日Switch 2八月大作盘点：匹诺曹的谎言 完整版（8/6发售，含DLC故事）、上古卷轴4 湮灭重制版（8/11卡带发售，无需key-card）、艾尔登法环 褪色者版（8/28，含本篇+DLC黄金树幽影+新职业）、合金装备大师合集Vol.2（8/27，含首次登陆PS3宿命的MGS4）。第一方方面，《宝可梦 Pokopia》新增Bubbly Basin DLC+免费潜水更新。任天堂NS2策略核心为「把PS5/Xbox已验证的重量级带到掌机平台」，第三方密集落地标志内容生态进入爆发期。",
        "https://cq-esports.com/news/nintendo-switch-2-august-2026-five-major-ports-one-big-twist",
        ["CQ Esports", "Game Freak", "任天堂"]
    ),
    news_item(
        "08-13",
        [tag("Xbox", "warn"), tag("宕机修复", "default")],
        "8月13日微软Xbox Live服务宕机事件更新：8月10日起Xbox网络核心服务出现大规模中断，影响在线游戏、商店购买与云游戏功能，持续约48小时。微软于8月12日确认修复，要求所有Xbox Series X|S用户在8月17日前强制安装系统更新以恢复完整在线功能。此次宕机是Xbox Live近两年来最严重的服务中断事件，叠加8月起欧美Xbox涨价（近13个月第三次），微软主机业务面临用户体验与价格双重压力。",
        "https://www.toutiao.com/a7670994140334785068",
        ["今日头条", "Xbox官方", "微软"]
    ),
]
update_news_file("console-news.json", console_items)

# ========== 9. Health Tea News ==========
print("=== Updating health-tea-news.json ===")
health_tea_items = [
    news_item(
        "08-13",
        [tag("中草药囊泡", "hot"), tag("学术会议", "default")],
        "8月13日广州全球学术会议消息：中草药囊泡（植物外泌体）技术在节气养生茶领域取得突破性进展。中草药囊泡是植物细胞分泌的纳米级囊泡，携带活性成分具有高生物利用度与靶向性，广州研究团队将其应用于立秋节气养生茶配方——通过囊泡包裹技术提升荷叶碱、淡竹叶黄酮等活性成分的稳定性与吸收率。同期「秋天第一杯奶茶养生化」趋势引发关注：草本茶饮品牌将药食同源原料（枸杞、桂圆、红枣、陈皮）融入奶茶基底，单杯定价6-15元，18-35岁消费者占超六成，推动草本茶饮2026年预计突破600亿元规模。",
        "https://gzdaily.dayoo.com/pc/html/2026-08/12/content_872_913175.htm",
        ["广州日报", "中研网", "艾媒咨询"]
    ),
]
update_news_file("health-tea-news.json", health_tea_items)

# ========== 10. Sheyang News ==========
print("=== Updating sheyang-news.json ===")
sheyang_items = [
    news_item(
        "08-13",
        [tag("翠冠梨", "hot"), tag("丰收上市", "default")],
        "8月13日射阳农业动态：射阳翠冠梨进入丰收上市季。翠冠梨是射阳特色水果品种，以果肉细嫩、汁多味甜著称，今年受台风「白海豚」外围影响有限、产量保持稳定。同期千秋镇持续开展防台防汛督查工作，对低洼地带、田间排水系统、农业设施进行拉网式排查，确保后台风季节农业生产安全。海通镇开展「夏日送清凉」活动，为户外劳动者与田间作业农户发放防暑物资。射阳白玉蟹种质研发项目近期获奖，标志本地特色水产种业创新取得新进展。",
        "https://www.sheyang.gov.cn/",
        ["射阳县政府", "射阳发布", "盐城新闻网"]
    ),
]
update_news_file("sheyang-news.json", sheyang_items)

# ========== 11. ChinaJoy News ==========
print("=== Updating chinajoy-news.json ===")
chinajoy_items = [
    news_item(
        "08-13",
        [tag("朝夕光年", "hot"), tag("七大工作室", "default")],
        "8月13日ChinaJoy后续报道：字节跳动旗下朝夕光年游戏品牌在ChinaJoy 2026上以七大工作室矩阵集体亮相，标志着其在经历2024年战略调整后全面回归游戏赛道。七大工作室覆盖开放世界RPG、二次元、休闲社交、竞技对战等品类，展出《海贼梦想大陆》《星球重启2》等多款新品试玩。同期，国产科幻3A《时空低语》在CDEC全球游戏产业大会上披露最新研发进展——主线剧情已完成、预计2028-2029上线、首支PV年底发布。明朝武侠动作游戏《一盏秋声：锦衣卫》获日媒试玩好评，被称作「中国版只狼」。",
        "https://www.toutiao.com/article/7669126201528664612/",
        ["新闻晨报", "游戏葡萄", "ChinaJoy官网"]
    ),
]
update_news_file("chinajoy-news.json", chinajoy_items)

print("\n=== All news files updated successfully! ===")
