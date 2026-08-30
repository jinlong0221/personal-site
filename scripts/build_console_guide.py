#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_console_guide.py — 给游戏主机图鉴页生成「选购与避坑」解读

背景：主机图鉴 75 页已有相当完整的正文（历史背景 / 硬件规格 / 游戏阵容 /
型号演变 / 市场表现），缺的不是内容量，而是**读者做决策时真正需要的判断**：
二手还值不值得买、这台机器有什么出了名的毛病、挑的时候该看哪里。

本脚本基于页面真实元数据（发售年份 / 销量 / 机型类型）推导，知识取自各机型的
公开通病与老化规律——都是具体条目，不是「经典值得收藏」这类空话。

内容组织（每台最多 4 条，缺维度就省略，不编造）：
  1. 这台机器的定位 —— 年份 + 厂商 + 销量
  2. 出了名的毛病 —— 该机型公认的通病（有则写）
  3. 二手怎么挑     —— 按类型（光驱 / 卡带 / 掌机 / 硬盘 / 串流）的老化要点
  4. 现在还值不值得 —— 按年代给价值判断

用法：
  python3 scripts/build_console_guide.py            # 写入 static/data/console-guide.json
  python3 scripts/build_console_guide.py --check    # 只打印统计与抽样
"""
import glob
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC = os.path.join(ROOT, "static")
OUT = os.path.join(STATIC, "data", "console-guide.json")

# 厂商聚合页（不是具体机型），不生成选购建议
BRAND_PAGES = {
    "雅达利 Atari", "任天堂 Nintendo", "微软 Microsoft", "世嘉 SEGA",
    "索尼 Sony", "其他品牌",
}

# ---------------------------------------------------------------------------
# 具体机型的公认通病（按标题关键词匹配，取第一个命中的）
# 每条都是该机型在玩家群体中出了名的问题，可核验
# ---------------------------------------------------------------------------
MODEL_ISSUES = [
    ("Xbox 360",
     "三红（RRoD）是这台机器绕不开的话题——早期主板的 GPU/CPU 长期热胀冷缩后虚焊，"
     "三盏红灯亮起即宣告报废。后期改版主板（Jasper 之后）大幅改善，"
     "二手机优先看主板版本，并要求卖家通电实测"),
    ("Xbox One",
     "电源适配器外置且风扇噪音偏大是常见抱怨；后期 S/X 已改为内置电源，二手优先选这两个型号"),
    ("Xbox Series",
     "机器本身可靠性不错，主要注意存储空间——内置 SSD 扩容卡价格不低，"
     "Series S 的 512GB 装几个 3A 就见底"),
    ("PlayStation 5",
     "硬件可靠性目前没有普遍性通病。真正要留意的是散热环境与 SSD 扩容的兼容性，"
     "以及 Pro 机型是否为首发批次"),
    ("PlayStation 4",
     "早期厚机（CUH-10xx/11xx）风扇噪音明显，长期高负载后更甚；"
     "Slim 与 Pro 在噪音和发热上都有改善"),
    ("PlayStation 3",
     "早期 90nm/65nm 的 CELL 与 RSX 机型有黄灯（YLOD）问题，本质是虚焊；"
     "后期的 Slim / Super Slim 可靠性好得多，二手机优先选后者"),
    ("PlayStation 2",
     "厚机的光驱是消耗品，激光头衰减后读盘困难、挑碟；"
     "薄机（7xxxx 之后）光驱相对耐用，但电源适配器容易丢"),
    ("PlayStation (PS1)",
     "光头老化是通病，读盘时会出现卡顿、跳音、挑碟（尤其 CD-R）；"
     "挑二手机务必实测读盘，或者考虑用 ODE 光驱模拟器替代"),
    ("PS Vita",
     "记忆卡是专有规格且价格离谱，买之前先确认存储方案；"
     "初代 1000 型是 OLED 屏，长期显示固定画面会有烧屏残留"),
    ("PSP Go",
     "取消了 UMD 只支持数字版，容量内置且不可换电池——"
     "买它等于接受一台被存储续航双重限制的机器"),
    ("PSP",
     "UMD 光驱与摇杆都有老化问题：光驱读盘慢且耗电，1000/2000 型的摇杆用久会漂移；"
     "按键排线断裂也是常见故障"),
    ("PlayStation Portal",
     "它不能独立运行——本质是 PS5 的串流手柄，必须有一台 PS5 并依赖网络质量；"
     "没有 PS5 或家里 Wi-Fi 一般的话，这台设备很难发挥"),
    ("Nintendo Switch 2",
     "新机型暂无普遍性通病，主要看首发批次的良率与后续固件更新；"
     "买新不买旧，二手机目前溢价可能性高"),
    ("Switch Lite",
     "摇杆漂移同样存在，而且 Joy-Con 焊死在主板上——"
     "老机型还能换 Joy-Con 解决，Lite 漂移就得拆机或送修"),
    ("Nintendo Switch",
     "Joy-Con 摇杆漂移是这代最出名的毛病，用久了会出现不碰自己动的情况；"
     "另外掌机屏幕没贴膜很容易被底座刮花"),
    ("Wii U",
     "GamePad 电池续航短、离开主机一段距离就断连；本体内置存储只有 8GB/32GB，"
     "装数字版必须外接硬盘"),
    ("Wii",
     "光驱读盘老化是主要问题；另外 Wiimote 的电池仓弹簧与硅胶套老化很常见"),
    ("GameCube",
     "用的是 miniDVD 光碟，光驱激光头老化后读盘困难；"
     "另外后期机型取消了数字输出口，想接现代显示器要留意这一点"),
    ("Nintendo 64",
     "卡带金手指氧化是头号问题，插上去黑屏多半是接触不良，酒精+橡皮基本能救；"
     "部分游戏（如《塞尔达：姆吉拉的假面》）还需要 Expansion Pak 扩展内存"),
    ("New Nintendo 3DS",
     "新增的 C-Stick 与 ZL/ZR 键用久会失灵；另外上下屏色温不一致是通病，挑机时注意对比"),
    ("New Nintendo 2DS XL",
     "转轴是易损件，开合次数多了会松动甚至开裂；屏幕排线也在转轴附近，属于高风险位"),
    ("Nintendo 3DS XL",
     "转轴松动/开裂是这代的结构性弱点；另外合盖时上屏可能压伤下屏，挑机看有无压痕"),
    ("Nintendo 3DS",
     "转轴与摇杆是主要损耗点，此外上下屏色温差异明显，建议实地对比后再买"),
    ("Nintendo 2DS",
     "取消了转轴改成直板，反而避开了 3DS 系列最脆弱的结构件，耐用性比折叠款好"),
    ("DSi",
     "转轴与下屏触控漂移是常见问题；内置存储小，主要靠 SD 卡"),
    ("DS Lite",
     "转轴断裂（hinge crack）是这台机器的招牌故障，二手几乎必查；"
     "另外下屏触控漂移、电池衰减也很常见"),
    ("Nintendo DS",
     "转轴与下屏触控是主要损耗点；这台机器上市已 20 年，电池基本都到了该换的时候"),
    ("Game Boy Micro",
     "屏幕只有 2 英寸且不可换电池，实用性远不如收藏价值；"
     "另外它不支持 GBA 之前的卡带"),
    ("Game Boy Advance SP",
     "AGS-001 是前光版、AGS-101 才是背光版，两者观感差很多，买之前一定确认型号；"
     "内置电池用久了也需要更换"),
    ("Game Boy Advance",
     "原版没有背光，光线稍暗就看不清——后来才出的 AGS-101（SP 背光版）解决了这个问题；"
     "二手机还要留意屏幕划痕与坏点"),
    ("Game Boy Color",
     "屏幕老化发暗、电池仓弹簧腐蚀是常见问题；"
     "外壳发黄在这台机器上尤其普遍"),
    ("Game Boy Light",
     "只在日本发售，本身带背光是优点，但存量少、电池仓腐蚀问题同样存在，"
     "收藏属性大于实用"),
    ("Game Boy Pocket",
     "屏幕偏压现象普遍（画面整体发暗或偏色）；电池仓触点腐蚀也是老 GB 通病"),
    ("Game Boy",
     "四十年前的机器了：屏幕偏压、电池仓弹簧腐蚀、外壳发黄，"
     "挑机重点看屏幕有无竖线与电池仓是否干净"),
    ("Game & Watch",
     "液晶屏老化发黑、按键导电胶磨损是主要问题；"
     "这类机器现在更多是收藏品，实用价值有限"),
    ("Sega Nomad",
     "要 6 节 AA 电池且续航很短，屏幕也偏暗；"
     "它本质是便携版 MD，二手还要注意卡带槽与视频输出"),
    ("Sega Game Gear",
     "90 年代电容漏电的重灾区——声音变小、屏幕发暗几乎都是电容问题，"
     "买之前最好确认是否换过电容"),
    ("Sega Dreamcast",
     "GD-ROM 光驱读盘能力随年限下降，且很多机器被改过直读；"
     "VMU 记忆卡的纽扣电池耗尽会丢存档"),
    ("Sega Saturn",
     "光驱老化是主要问题；另外部分格斗游戏需要 4MB 扩展卡才能正常运行，"
     "买游戏前先确认"),
    ("Mega Drive",
     "卡带槽久用会松导致接触不良；老机型多为 RF 输出，"
     "接现代电视需要转接或改 AV/RGB"),
    ("Master System",
     "卡带槽氧化与 RF 输出是主要问题，视频输出改造在这台机器上很常见"),
    ("SG-1000",
     "卡带接触不良是通病；这台机器存世量少，更多是考古价值"),
    ("Neo Geo AES",
     "卡带价格是真正的门槛——家用卡带动辄数千上万元，"
     "买机器容易，买游戏才是主要开销"),
    ("Neo Geo Pocket Color",
     "屏幕老化与电池仓是主要问题；这台机器在国内存量不大"),
    ("Bandai WonderSwan",
     "只在日本发售，屏幕老化是主要问题，横竖都能玩的独特设计是它的卖点"),
    ("TurboExpress",
     "屏幕与耗电是两大短板（要 6 节电池且续航极短），"
     "它本质是便携版 PC Engine，二手屏幕状态决定价值"),
    ("3DO",
     "首发 699 美元的定价是它失败的直接原因；"
     "现在二手机的光驱老化、配件难寻是主要问题"),
    ("Nokia N",
     "换卡必须关机、打电话要贴着脸（Sidetalking）是它成为梗的原因；"
     "现在入手主要是猎奇与收藏"),
    ("Atari Lynx",
     "屏幕老化与耗电大户（6 节电池只能用几小时）是硬伤；"
     "它比 GB 性能强但续航完全不在一个量级"),
    ("Atari 7800",
     "无内置音效芯片（沿用 2600 的 TIA），声音表现是短板；"
     "卡带金手指氧化是二手机主要问题"),
    ("Atari 5200",
     "自带摇杆不可自动回中、手感极差是这台机器最出名的槽点；"
     "RF 输出与卡带接触同样要留意"),
    ("Atari 2600",
     "多为 RF 射频输出，接现代电视需要转换；"
     "卡带金手指氧化、电源适配器老化是二手机常见状况"),
    ("小霸王",
     "本质是 FC 兼容机，键盘与卡带槽是主要损耗点；"
     "现在入手多是怀旧，注意它并不等同原装 FC"),
    ("Family Computer",
     "72-pin 卡带插槽弹片氧化是红白机最典型的毛病——"
     "吹气、插拔多次才能让游戏跑起来，就是弹片老了；清洁或更换插槽可解决"),
    ("Steam Deck",
     "Valve 的 SteamOS 更新与兼容层（Proton）维护得不错，"
     "但非 Steam 游戏仍可能遇到兼容问题；续航在 3A 大作下普遍只有 1.5–2 小时"),
    ("ROG Ally",
     "Windows 掌机的通病在这台都有：驱动与 Armoury Crate 软件偶发冲突、"
     "高负载续航短；另外 SD 卡槽早期批次有过过热隐患，买之前查一下批次"),
    ("Legion Go",
     "8.8 英寸大屏是优点，代价是机身偏重、长时间手持累；"
     "Windows 掌机的驱动与续航问题同样存在"),
    ("MSI Claw",
     "首批用的是 Intel 处理器，能效与驱动优化都不如 AMD 方案，"
     "续航和兼容性口碑一般，建议等后续改版"),
    ("AYANEO",
     "小厂 Windows 掌机，性能给得足但驱动与售后依赖厂商更新节奏，"
     "买之前确认固件维护是否还活跃"),
    ("GPD Win",
     "是最早一批 x86 掌机，键盘手感与散热是老问题；"
     "现在看性能已经落后，主要适合折腾党"),
]

# ---------------------------------------------------------------------------
# 按类型的老化要点（补充机型通病之外、该类型都要注意的事）
# ---------------------------------------------------------------------------
TYPE_ISSUES = [
    ("WIN掌机", ("Steam Deck", "ROG Ally", "Legion Go", "MSI Claw", "AYANEO", "GPD Win"),
     "这类 x86 掌机共同的取舍：性能越强续航越短，"
     "选购时优先看散热与厂商固件维护是否活跃——小厂机型容易买来就没更新了"),
    ("串流", ("PlayStation Portal",),
     "串流设备的体验完全取决于家里的网络与主机：Wi-Fi 抖动会直接变成画面糊和延迟，"
     "买之前先确认自己的网络环境扛不扛得住"),
    ("光碟", ("PlayStation", "PS2", "PS3", "PS4", "PS5", "Xbox", "GameCube",
              "Wii", "Dreamcast", "Saturn", "3DO"),
     "光驱机型的通病是激光头衰减：读盘慢、挑碟、卡 LOGO 都是信号。"
     "二手机务必通电实测读盘，别只看外观"),
    ("卡带", ("Family Computer", "Super Famicom", "Nintendo 64", "Mega Drive",
              "Master System", "Atari", "SG-1000", "Neo Geo AES", "小霸王",
              "Game Boy", "Game & Watch"),
     "卡带机型的接触问题是主旋律：金手指氧化会导致黑屏或花屏，"
     "橡皮+酒精擦拭基本能救，插拔手感过松的卡槽要额外留意"),
    ("掌机", ("Game Boy", "PSP", "PS Vita", "Nintendo DS", "Nintendo 3DS",
              "Nintendo 2DS", "Nintendo Switch", "Lynx", "Game Gear", "Nomad",
              "TurboExpress", "WonderSwan", "Neo Geo Pocket"),
     "掌机三件套最容易出事：电池衰减、屏幕老化、转轴/摇杆磨损。"
     "二手机优先看这三项，外观反而是其次"),
]

# ---------------------------------------------------------------------------
# 按年代的价值判断
# ---------------------------------------------------------------------------
def era_value(year, handheld=False):
    """按年代给价值判断。

    掌机与家用机的老化重点完全不同：掌机是电池/屏幕/转轴，
    家用机是光驱/卡带/视频输出。混用会写出「Game Boy 正值光碟转折点」
    这种张冠李戴的话，所以必须分开。
    """
    if not year:
        return ""
    y = int(year)
    if handheld:
        if y < 1995:
            return (f"{y} 年的掌机，电池仓腐蚀、屏幕偏压、外壳发黄几乎躲不掉；"
                    "它现在是收藏品，当作日常游戏设备不现实")
        if y < 2005:
            # 这一档横跨卡带掌机（GB/GBA）与光碟掌机（PSP），
            # 存储介质不能写死成某一种
            return (f"{y} 年的掌机，电池衰减与屏幕老化是主要问题；"
                    "存储介质同样会老化（卡带清金手指、UMD 光驱读盘变慢），"
                    "动手换块电池就能明显改善体验")
        if y < 2015:
            return (f"{y} 年的掌机，电池衰减、屏幕老化、转轴/摇杆磨损是三件套；"
                    "二手价格已经下来，挑的时候重点看这三项")
        if y < 2022:
            return (f"{y} 年的掌机，硬件还能正常服役，主要损耗是电池与摇杆，"
                    "换电池基本能满血复活")
        return (f"{y} 年的掌机仍在役，硬件没什么普遍性问题；"
                "主要考虑保修、摇杆手感与配件投入")
    if y < 1985:
        return (f"{y} 年的机器，距今已四十年上下——它的意义更多是行业考古与收藏，"
                "当作日常游戏设备已经不现实，原装配件和卡带的获取成本才是主要门槛")
    if y < 1995:
        return (f"{y} 年发售，属于 8/16 位时代。拿来怀旧很合适，"
                "但要有心理准备：卡带接触、电容老化、视频输出（多为 RF）都需要处理，"
                "动手能力强才玩得舒服")
    if y < 2005:
        return (f"{y} 年发售，正值 3D 与光碟的转折点。二手性价比不错，"
                "但光驱机型要实测读盘、卡带机型要清金手指，"
                "配件（记忆卡/手柄）也常有缺失")
    if y < 2015:
        return (f"{y} 年的机器，硬件还能正常服役，二手价格也下来了；"
                "主要留意电池衰减（掌机）与硬盘健康（家用机）")
    if y < 2022:
        return (f"{y} 年发售，仍在同一世代的主流支持范围内，"
                "二手与全新都能买到，买之前对比一下现役机型的性价比")
    return (f"{y} 年的现役机型，硬件可靠性通常还没暴露出普遍问题；"
            "主要考虑保修、固件版本与配件（存储/手柄）的后续投入")


# ---------------------------------------------------------------------------
# 世代定位：这台机器当时身处哪一场战争、对手是谁、那一代争的是什么。
# 页面正文已有年份与销量，复述毫无增量；真正的增量是"它在历史里的位置"。
# ---------------------------------------------------------------------------
GENERATION = [
    # (起, 止, 是否掌机, 世代名, 同代主要机型, 这一代争的是什么)
    (1972, 1984, False, "早期家用机",
     "Atari 2600、ColecoVision、Intellivision",
     "还没有统一标准，各家自造芯片、自定卡带规格，谁的游戏多谁赢"),
    (1983, 1990, False, "8 位机时代",
     "FC/红白机、Sega Master System、Atari 7800",
     "任天堂用「权利金制度」重建了行业秩序——1983 年雅达利大崩溃之后，"
     "北美市场对家用机几乎失去信心，是 FC 把它救回来的"),
    (1987, 1994, False, "16 位机时代",
     "Mega Drive、Super Famicom、Neo Geo、PC Engine",
     "世嘉与任天堂的正面对决：MD 走美式硬派路线，SFC 靠第一方与第三方阵容取胜，"
     "这一代奠定了此后几十年的主机战争格局"),
    (1993, 1999, False, "32/64 位时代",
     "PlayStation、Sega Saturn、Nintendo 64、3DO",
     "核心分歧是卡带还是光碟：索尼押注 CD，成本与容量优势让它拿走了大量第三方；"
     "任天堂坚持卡带，代价是失去第三方支持；3DO 则败在 699 美元的定价"),
    (1998, 2006, False, "128 位时代",
     "PlayStation 2、Xbox、GameCube、Dreamcast",
     "PS2 用 DVD 播放功能当特洛伊木马，一举拿下统治地位；"
     "微软首次入场；世嘉在 DC 失败后彻底退出主机硬件"),
    (2005, 2013, False, "高清时代",
     "Xbox 360、PlayStation 3、Wii",
     "微软靠提前一年发售与 Xbox Live 抢占先机；索尼用 Cell 押注高性能却开局艰难；"
     "任天堂另辟蹊径用体感赢下了更广的受众"),
    (2012, 2017, False, "第八世代",
     "PlayStation 4、Xbox One、Wii U",
     "索尼靠价格与开发者友好度取胜，微软因首发强制联网与 Kinect 捆绑失了先手，"
     "Wii U 则因定位混乱成为任天堂最失败的家用机"),
    (2017, 2030, False, "第九世代",
     "PlayStation 5、Xbox Series X/S、Nintendo Switch",
     "家用机拼的是性能与 SSD，任天堂依然用 Switch 的「随时随地」另走一条路——"
     "两种思路各自成立"),
    (1989, 1998, True, "便携机早期",
     "Game Boy、Game Gear、Atari Lynx、Sega Nomad",
     "同样的便携概念，Game Boy 用黑白屏与四节电池换来了十倍于对手的续航，"
     "彩色与背光的对手们输在了电池上"),
    (1996, 2004, True, "GB 进化期",
     "Game Boy Pocket/Color/Light、Game Boy Advance、Neo Geo Pocket、WonderSwan",
     "GB 靠向下兼容累积了巨大卡带库，GBA 把它推向顶峰；"
     "挑战者们各自有亮点，但没能撼动卡带库的护城河"),
    (2004, 2011, True, "双屏与光碟掌机",
     "Nintendo DS、PSP、Game Boy Micro",
     "NDS 用触控与双屏开拓了非玩家人群，PSP 用多媒体与性能切入——"
     "两条路线都取得了商业成功"),
    (2011, 2020, True, "裸眼 3D 与高性能掌机",
     "Nintendo 3DS、PS Vita、Nintendo 2DS",
     "3DS 开局不利靠降价与第一方翻身；PS Vita 硬件很强，"
     "但专有记忆卡与第三方撤离让它没能走远"),
    (2017, 2030, True, "混合形态掌机",
     "Nintendo Switch、Switch Lite、Steam Deck、ROG Ally、Legion Go",
     "Switch 把掌机与家用机合二为一；随后 Steam Deck 带火了 x86 掌机，"
     "Windows 阵营（ROG Ally、Legion Go）也加入战局"),
]

HANDHELD_KEYS = ("Game Boy", "PSP", "PS Vita", "Nintendo DS", "Nintendo 3DS",
                 "Nintendo 2DS", "Switch", "Lynx", "Game Gear", "Nomad",
                 "TurboExpress", "WonderSwan", "Neo Geo Pocket", "N-Gage",
                 "Micro", "Steam Deck", "ROG Ally", "Legion Go", "MSI Claw",
                 "AYANEO", "GPD Win")


def is_handheld(title):
    return any(k in title for k in HANDHELD_KEYS)


def generation_of(year, handheld):
    """取该年份所属的世代。

    注意：世代区间有意重叠（例如 2011-2020「裸眼 3D 掌机」与 2017-2030
    「混合形态掌机」都包含 2017）。这种情况下要取**起始年份最大**的那一个——
    一台机器属于它所在世代的"开端"，而不是上一代的尾声。
    （Switch 是 2017 年的新世代，不能归进 2011 年的 3DS 世代。）
    """
    if not year:
        return None
    y = int(year)
    matched = [
        (lo, hi, name, peers, note)
        for lo, hi, is_h, name, peers, note in GENERATION
        if is_h == handheld and lo <= y <= hi
    ]
    if not matched:
        return None
    lo, _hi, name, peers, note = max(matched, key=lambda t: t[0])
    return (name, peers, note)


def pick_model_issue(title):
    for key, text in MODEL_ISSUES:
        if key in title:
            return text
    return ""


def pick_type_issue(title):
    for _label, keys, text in TYPE_ISSUES:
        for k in keys:
            if k in title:
                return text
    return ""


def pick_brand_note(title):
    for key, text in BRAND_NOTE:
        if key in title:
            return text
    return ""


def extract(path):
    h = open(path, encoding="utf-8").read()
    t = re.search(r"<title>([^<]+)</title>", h)
    raw = t.group(1) if t else ""
    title = raw.split("-")[0].strip()
    y = re.search(r"(\d{4})\s*年(?:发布|发售|推出)", h)
    year = y.group(1) if y else ""
    s = re.search(r"([\d.]+\s*[亿万]?\+?)\s*(?:全球销量|销量|台)", h)
    sales = s.group(1).strip() if s else ""
    return {"title": title, "raw": raw, "year": year, "sales": sales}


def build_guide(d):
    rows = []
    title = d["title"]

    # 1) 世代定位：不重复页面已有的年份/销量，给"它在历史里的位置"
    gen = generation_of(d["year"], is_handheld(title))
    if gen and d["year"]:
        name, peers, note = gen
        # 从同代清单里剔除自己（以及自己的衍生型号），否则会出现
        # "Switch 的同代对手是 Nintendo Switch" 这种自指
        others = [
            p.strip() for p in peers.split("、")
            if p.strip() and p.strip() not in title and title not in p.strip()
        ]
        peer_txt = ("。同代主要机型：" + "、".join(others)) if others else ""
        rows.append({
            "k": "它在历史里的位置",
            "v": f"{d['year']} 年发售，属于{name}{peer_txt}。{note}",
        })

    # 2) 机型通病（具体，价值最高）
    issue = pick_model_issue(title)
    if issue:
        rows.append({"k": "出了名的毛病", "v": issue})

    # 3) 类型要点：只在没有具体机型通病时给，避免与上面重复
    if not issue:
        t_issue = pick_type_issue(title)
        if t_issue:
            rows.append({"k": "二手怎么挑", "v": t_issue})

    # 4) 年代价值判断（区分掌机/家用机）
    ev = era_value(d["year"], is_handheld(title))
    if ev:
        rows.append({"k": "现在还值不值得", "v": ev})

    return rows


def main():
    check_only = "--check" in sys.argv
    files = sorted(glob.glob(os.path.join(STATIC, "console-*.html")))
    out = {}
    skipped = []
    for f in files:
        d = extract(f)
        if d["title"] in BRAND_PAGES or not d["title"]:
            skipped.append(d["title"])
            continue
        rows = build_guide(d)
        if not rows:
            skipped.append(d["title"])
            continue
        key = "/" + os.path.basename(f)
        out[key] = {"title": d["title"], "year": d["year"], "rows": rows}

    print(f"主机页总数: {len(files)}")
    print(f"生成解读:   {len(out)}")
    print(f"跳过(厂商页/无数据): {len(skipped)} -> {skipped}")

    if not check_only:
        json.dump(out, open(OUT, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        print(f"已写入 {OUT}")

    # 统计
    from collections import Counter
    c = Counter()
    for v in out.values():
        for r in v["rows"]:
            c[r["k"]] += 1
    n = len(out)
    print("\n覆盖统计:")
    for k, cnt in c.most_common():
        print(f"  {k}: {cnt}/{n}")

    print("\n=== 抽样 ===")
    for k in ["/console-switch.html", "/console-xbox-360.html",
              "/console-game-gear.html"]:
        if k in out:
            print(f"\n{out[k]['title']}")
            for r in out[k]["rows"]:
                print(f"   · {r['k']}：{r['v'][:96]}")


if __name__ == "__main__":
    main()
