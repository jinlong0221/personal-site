# -*- coding: utf-8 -*-
import json, os

base = "/Users/chenjinlong/陈金龙/代码与脚本/个人知识网站/hugo-site/static"

def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)

def save(p, d):
    with open(p, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)
        f.write("\n")

# ---- Marvel (updated -> 11-08) ----
marvel_entry = {
    "date": "2026-11-08",
    "tags": [
        {"text": "漫威", "class": "hot"},
        {"text": "复仇者联盟5", "class": "info"},
        {"text": "选角", "class": "tag-blue"}
    ],
    "summary": "《复仇者联盟：毁灭之日》阵容新增詹姆斯·戴登，他曾在《死侍与金刚狼》中饰演 TVA 技术员，该角色先出现在《终局之战》重映彩蛋、六周后被正式写进正片；迪士尼确认《毁灭日》后漫威仅保留四部院线加一部剧，主动收缩剧集产能。",
    "content": "好莱坞电影动态日报 2026-11-08 报道（经交叉确认）：漫威影业《复仇者联盟：毁灭之日》（Avengers: Doomsday，北美 12 月 18 日上映）阵容新增詹姆斯·戴登（James Dryden），他在《死侍与金刚狼》中饰演 TVA 技术员拉尔夫；据披露，该角色先出现在《终局之战》重映版（Encore）第三段加场彩蛋——拉尔夫站在莫比乌斯身旁、指着屏幕说「入侵正在实时发生」，六周后被正式写进正片名单。同一批官方口径还确认《毁灭日》之后漫威的排产结构：四部院线电影——《秘密战争》2027/12/17、《X 战警》2028/5/5、《恶灵骑士》2028/7/28（高斯林）、《黑豹3》2028/12/15，以及仅剩的一部真人 Disney+ 剧《夜魔侠：重生》第三季。报道指出，MCU 正主动收缩剧集产能、把赌注压在影院事件上。",
    "url": "http://mp.weixin.qq.com/s?__biz=Mzk2NDQ3Njk3OQ==&mid=2247483933&idx=1&sn=d1a3bb71bbb4494d557ea3649f137173&chksm=c5f360cc8f58253873165b5dc4ec7aca7a38e206afb5bade1f6eafaee9b6e8d7f5311ab122e0#rd",
    "sources": [
        "好莱坞电影动态日报 2026-11-08《漫威每日动态》",
        "Marvel Studios 官方阵容 / Disney Upfront 27 口径交叉"
    ]
}

p = os.path.join(base, "marvel-news.json")
d = load(p)
d["news"] = [marvel_entry] + d["news"]
d["news"] = d["news"][:8]
d["updated"] = "2026-11-08"
save(p, d)
print("marvel updated ->", d["updated"], "top:", d["news"][0]["date"], "n:", len(d["news"]))

# ---- Health-tea (updated -> 11-08) ----
htea_sx = {
    "date": "2026-11-08",
    "tags": [
        {"text": "养生茶", "class": "hot"},
        {"text": "药食同源", "class": "info"},
        {"text": "进博会", "class": "tag-blue"}
    ],
    "summary": "陕西汉中企业汉尚云清携冷热双萃养生茶亮相第九届进博会「国家级步行街」陕西展，产品以中药材为原料、已上线销售并迎合海外冷水泡需求与国内年轻人冷饮喜好，企业每年推出养生新品、品类已超 80 种。",
    "content": "群众新闻网 2026-11-08 报道（经搜狐同题交叉确认）：陕西汉尚云清生物科技有限公司是一家做药食同源和养生大健康产品开发的科技型企业，本届进博会携冷热双萃茶新产品亮相「国家级步行街」陕西展，重点展示「东方茶兮」冷热双萃轻清茶、果茶和花茶及中药材代用茶。据介绍，公司此前以中药材为原料制成的东方养生茶曾亮相 2025 年日本大阪世博会，海外客户关心能否冷水泡，回国后研发出冷热双萃茶，上个月正式上线销售，既满足海外市场需求、又迎合国内年轻人夏天喝冷饮的喜好。作为汉中中药材产业链上企业，公司每年推出养生新品，目前产品品类已超过 80 种。第九届进博会 11 月 5 日开幕，162 个国家、地区和国际组织参与，规模与质量多项指标创历史新高。",
    "url": "https://www.sxdaily.com.cn/2026-11/08/content_20183436.html",
    "sources": [
        "群众新闻网 2026-11-08《「新」意十足，陕企共赴「东方之约》",
        "搜狐 2026-11-08 同题报道"
    ]
}
htea_wang = {
    "date": "2026-11-08",
    "tags": [
        {"text": "养生茶", "class": "hot"},
        {"text": "药食同源", "class": "info"},
        {"text": "立冬暖饮", "class": "tag-blue"}
    ],
    "summary": "立冬后药食同源养生茶进入旺季，业内明确药材须出自国家「既是食品又是中药材」目录，超目录须医师辨证且不得对外销售；中式养生水从「无糖」转向「功能性滋养」，红豆薏米、红枣枸杞、罗汉果陈皮成主力，秋冬暖饮主打滋阴润燥的罗汉果、陈皮、雪梨、百合、玉竹。",
    "content": "王兰老师每日分享全球茶咖茶饮讯息 2026.11.8（经交叉确认）：立冬后药食同源养生茶进入消费旺季。业内专家明确，药膳、养生茶所用药材必须来自国家公布的「按照传统既是食品又是中药材」目录，超出目录范围需专业医生辨证使用且不能对外销售，这条界限直接决定养生茶饮品牌的产品开发边界，选料前先查目录是硬要求。中式养生水进入 2.0 阶段，竞争关键词从「无糖」转向「功能性滋养」，消费者要求配料干净且功能明确，红豆薏米、红枣枸杞、罗汉果陈皮等传统食养配方成为产品主力。秋冬季原茶即饮旺销（农夫山泉东方树叶桂花乌龙季节限定热销），立冬后暖饮配方集中在滋阴润燥方向，罗汉果、陈皮、雪梨、百合、玉竹等药食同源食材成为品牌本季核心原料，多家品牌门店同步上线热饮版本。",
    "url": "http://mp.weixin.qq.com/s?__biz=Mzk0NjY1MzM2Ng==&mid=2247496082&idx=1&sn=08c93330faadb325aa5b825068e53764&chksm=c2b2ba3628ef48c506a91d71c9e2c62989977744c42940bfec4f0f01389540dcd1abe4db9862#rd",
    "sources": [
        "王兰老师每日分享全球茶咖茶饮讯息 2026.11.8",
        "群众新闻网 2026-11-08 陕企进博会报道（交叉）"
    ]
}

p = os.path.join(base, "health-tea-news.json")
d = load(p)
d["news"] = [htea_sx, htea_wang] + d["news"]
d["news"] = d["news"][:8]
d["updated"] = "2026-11-08"
save(p, d)
print("health-tea updated ->", d["updated"], "top:", d["news"][0]["date"], "n:", len(d["news"]))
