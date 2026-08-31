#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_game_pages.py — 一次性生成器：为 5 款 PS5 即将发售游戏建立独立页面。

策略（修正版）：
- 以 static/games/gta6.html 为结构模板
- 1) 先定位文章区：起点 <div class="game-title-wrap"> 紧接 <h1>侠盗猎车手 VI</h1>；
       终点 = `<!-- game:begin -->` 标记之前最近的 `</div>`（即文章 detail-section 的收尾）
       替换为新游戏的文章（不包含 <!-- game:begin --> 标记）
- 2) 剥除旧 game 块（<!-- game:begin -->…<!-- game:end -->）
- 3) 剥除旧 related 块
- 4) 剥除截图区（避免 404 与 AI 图禁令）
- 5) 替换 title / meta / og / twitter / sources / JSON-LD

用法：python3 scripts/build_game_pages.py
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAMES_DIR = os.path.join(ROOT, "static", "games")
TEMPLATE = os.path.join(GAMES_DIR, "gta6.html")

# ---------------------------------------------------------------------------
# 5 款 PS5 即将发售游戏（2026-09 ~ 2027-02，避开已有 11 款）
# 资料来源：PlayStation Blog 2026-08-25 Gamescom ONL；cross-checked with playstation.com
# ---------------------------------------------------------------------------
GAMES = [
    {
        "slug": "marvels-wolverine",
        "title_en": "Marvel's Wolverine",
        "title_zh": "漫威金刚狼",
        "developer": "Insomniac Games",
        "publisher": "Sony Interactive Entertainment",
        "release": "2026-09-15",
        "platform": "PS5（独占）",
        "genre_full": "动作冒险 / 超级英雄",
        "price": "标准版 USD 69.99（以 PS Store 官方为准）",
        "en_subtitle": "Marvel's Wolverine",
        "platform_badge": "🎮 PS5（独占）",
        "badges": ['<span class="badge">动作</span>', '<span class="badge">超级英雄</span>', '<span class="badge">Insomniac</span>'],
        "intro_paras": [
            "<p>《<strong>Marvel's Wolverine</strong>》是 Insomniac Games 继《漫威蜘蛛侠》系列之后打造的第二款漫威改编作品，"
            "以金刚狼为主角，讲述他在失去记忆、追寻自身过去的过程中，凭借艾德曼合金利爪与不死之身穿越黑暗阴谋的故事。</p>"
            "<p>本作定位为面向成人的硬核动作游戏，官方从一开始便强调<strong>暴力、残酷与不屈</strong>的基调，"
            "战斗主打利爪连招与「狂怒」机制，叙事则把金刚狼放在一个与 X 战警主线相对独立的新位置上。</p>"
            "<p>作为 2026 年 9 月的 PS5 独占中量级作品，本页为公开资料整理，<strong>非本人实玩评测</strong>。</p>",
        ],
        "highlights": [
            "<strong>金刚狼视角</strong>：独立于 X 战警主线的全新故事线，主打追寻过去的悬疑叙事",
            "<strong>硬核动作</strong>：艾德曼合金利爪的高速连招、狂怒爆发与终结技",
            "<strong>成人基调</strong>：Insomniac 明确为「暴力、不加修饰」的超级英雄题材",
            "<strong>PS5 独占</strong>：充分利用 DualSense 与 Tempest 3D 音效",
        ],
        "official_links": [
            ('PlayStation 官方页', 'https://www.playstation.com/zh-hans-hk/games/marvels-wolverine/'),
        ],
        "source_label": "PlayStation 官方页",
        "source_url": "https://www.playstation.com/zh-hans-hk/games/marvels-wolverine/",
    },
    {
        "slug": "blood-of-dawnwalker",
        "title_en": "The Blood of Dawnwalker",
        "title_zh": "破晓行者之血",
        "developer": "Rebel Wolves（波兰）",
        "publisher": "Bandai Namco Entertainment",
        "release": "2026-09-03",
        "platform": "PS5 / PC / Xbox Series X|S",
        "genre_full": "开放世界 / 黑暗奇幻动作 RPG",
        "price": "标准版 / 数字豪华版（Eclipse）/ 实体版 / 收藏版（定价以各平台商店为准）",
        "en_subtitle": "The Blood of Dawnwalker",
        "platform_badge": "🎮 PS5 / Xbox / PC",
        "badges": ['<span class="badge">开放世界</span>', '<span class="badge">动作 RPG</span>', '<span class="badge">吸血鬼</span>'],
        "intro_paras": [
            "<p>《<strong>The Blood of Dawnwalker</strong>》（破晓行者之血）是波兰新工作室 <strong>Rebel Wolves</strong> 的首部作品，"
            "由前《巫师 3》《赛博朋克 2077》总监 <strong>Konrad Tomaszkiewicz</strong> 领衔，万代南梦宫发行，"
            "以 Unreal Engine 5 打造的<strong>单人开放世界黑暗奇幻动作 RPG</strong>。</p>"
            "<p>主角 <strong>科恩（Coen）</strong>是被转化为「破晓行者」的年轻人：白天以人身持剑施法，夜晚化身为吸血鬼。"
            "他只有 <strong>30 天 30 夜</strong>去阻止吸血鬼领主布伦西斯（Brencis）处决自己的家人，"
            "而每推进一项任务都会消耗这有限的时间——救谁、放弃谁，本身就是核心抉择。</p>"
            "<p>舞台是黑死病肆虐后的 14 世纪喀尔巴阡山谷<strong>瓦勒桑戈拉（Vale Sangora）</strong>。"
            "本作 <strong>2026-09-03</strong> 同步登陆 PS5 / Xbox Series X|S / PC，全部版本同日解锁、无提前体验。"
            "本页为公开资料整理，<strong>非本人实玩评测</strong>。</p>",
        ],
        "highlights": [
            "<strong>30 天倒计时</strong>：推进任务即消耗时间，救谁与放弃谁成为核心抉择",
            "<strong>昼夜双套玩法</strong>：白天的剑与魔法，夜晚的吸血鬼异能，能力循环截然不同",
            "<strong>前巫师/CDPR 总监领衔</strong>：Konrad Tomaszkiewicz，Rebel Wolves 首部作品",
            "<strong>PC 版无 Denuvo</strong>：官方确认不附带第三方反篡改 DRM",
        ],
        "official_links": [
            ('Bandai Namco 官方页', 'https://www.bandainamcoent.com/games/dawnwalker'),
        ],
        "source_label": "官方站 / PlayStation Blog",
        "source_url": "https://blog.playstation.com/2026/08/25/gamescom-opening-night-live-highlights-19-games-coming-to-playstation/",
    },
    {
        "slug": "silent-hill-townfall",
        "title_en": "Silent Hill: Townfall",
        "title_zh": "寂静岭：Townfall",
        "developer": "Screen Burn（苏格兰，原名 No Code）",
        "publisher": "Konami / Annapurna Interactive",
        "release": "2026-09-24",
        "platform": "PS5 / PC（Steam、Epic Games Store）",
        "genre_full": "心理恐怖 / 第一人称生存",
        "price": "标准版 USD 49.99 / 数字豪华版 USD 59.99（含 48 小时提前体验）",
        "en_subtitle": "Silent Hill: Townfall",
        "platform_badge": "🎮 PS5 / PC",
        "badges": ['<span class="badge">心理恐怖</span>', '<span class="badge">第一人称</span>', '<span class="badge">Konami</span>'],
        "intro_paras": [
            "<p>《<strong>Silent Hill: Townfall</strong>》由苏格兰工作室 <strong>Screen Burn</strong>（原名 No Code，"
            "《Observation》《Stories Untold》的开发商）开发，Konami 与 Annapurna Interactive 联合发行，"
            "是系列<strong>首次采用第一人称视角</strong>的完整长篇心理恐怖作品。</p>"
            "<p>故事设定在 1996 年苏格兰海岸的虚构小镇<strong>圣阿米利亚（St. Amelia）</strong>："
            "失忆的主角 <strong>Simon Ordell</strong> 在码头边的水中反复醒来，循着碎片追查自己与这座雾中小镇的关联。"
            "核心道具是一台<strong>便携电视 CRTV</strong>——取代了系列经典的收音机，用来捕捉信号、追踪异象并解谜。</p>"
            "<p>本作 <strong>2026-09-24</strong> 登陆 PS5 与 PC（Steam、Epic），主机端为 PS5 限时独占至少半年；"
            "数字豪华版可提前 48 小时（9 月 22 日）进入。本页为公开资料整理，<strong>非本人实玩评测</strong>。</p>",
        ],
        "highlights": [
            "<strong>系列首次第一人称</strong>：探索、潜行躲避与资源管理的压迫感更强",
            "<strong>CRTV 便携电视</strong>：取代经典收音机，兼作威胁侦测与解谜工具",
            "<strong>1996 年苏格兰雾港</strong>：动态海雾压缩视野，配乐随威胁逼近实时加层",
            "<strong>PS5 / PC 先行</strong>：主机端限时独占，Xbox 版本尚未公布",
        ],
        "official_links": [
            ('PlayStation 官方页', 'https://www.playstation.com/zh-hans-hk/games/silent-hill-townfall/'),
        ],
        "source_label": "PlayStation 官方页 / Konami 官方",
        "source_url": "https://www.playstation.com/zh-hans-hk/games/silent-hill-townfall/",
    },
    {
        "slug": "phantom-blade-zero",
        "title_en": "Phantom Blade Zero",
        "title_zh": "影之刃：零",
        "developer": "S-Game（锡萌游戏）",
        "publisher": "S-Game（锡萌游戏）",
        "release": "2026-10-29",
        "platform": "PS5 / PC",
        "genre_full": "功夫庞克 / 硬核动作",
        "price": "国区标准版 ¥268 / 数字豪华版 ¥328（以商店页面为准）",
        "en_subtitle": "Phantom Blade Zero",
        "platform_badge": "🎮 PS5 / PC",
        "badges": ['<span class="badge">武侠</span>', '<span class="badge">硬核动作</span>', '<span class="badge">国产</span>'],
        "intro_paras": [
            "<p>《<strong>Phantom Blade Zero</strong>》（影之刃：零）是国产团队 <strong>S-GAME（灵游坊）</strong>"
            "用 Unreal Engine 5 开发的暗黑武侠动作 RPG。官方把这种融合传统武侠、香港功夫片与机械义肢的美学"
            "称为「<strong>功夫庞克（Kungfupunk）</strong>」。</p>"
            "<p>主角「<strong>魂</strong>」是被同门陷害、被指控弑师的剑客，心脏受创后<strong>只剩 66 天可活</strong>——"
            "他必须在生命尽头前追查幕后真相。战斗以高速近身刀剑交锋为核心，靠格挡、闪避、反击与连段取胜，"
            "击败部分强敌后还能<strong>夺取对方的兵器与代表性招式</strong>。</p>"
            "<p>本作 <strong>2026-10-29</strong> 登陆 PS5 与 PC（PS5 主机端限时独占 12 个月），"
            "甄子丹担任动作顾问并为关键角色提供动捕。本页为公开资料整理，<strong>非本人实玩评测</strong>。</p>",
        ],
        "highlights": [
            "<strong>功夫庞克美学</strong>：古代兵器、机械义肢与工业遗迹交融的黑暗武林",
            "<strong>只剩 66 天</strong>：以寿命倒计时驱动的复仇主线",
            "<strong>夺招系统</strong>：击败强敌可夺取其兵器与代表性招式",
            "<strong>PS5 + PC</strong>：主机端限时独占 12 个月，甄子丹任动作顾问",
        ],
        "official_links": [
            ('PlayStation 官方页', 'https://www.playstation.com/zh-hans-hk/games/phantom-blade-zero/'),
        ],
        "source_label": "官方站 / PlayStation Blog",
        "source_url": "https://blog.playstation.com/2026/08/25/gamescom-opening-night-live-highlights-19-games-coming-to-playstation/",
    },
    {
        "slug": "god-of-war-laufey",
        "title_en": "God of War: Laufey",
        "title_zh": "战神：劳菲",
        "developer": "Santa Monica Studio",
        "publisher": "Sony Interactive Entertainment",
        "release": "2027-02-16",
        "platform": "PS5（独占）",
        "genre_full": "动作 / 神话冒险",
        "price": "尚未公布（官方仅确认将发行实体光盘版）",
        "en_subtitle": "God of War: Laufey",
        "platform_badge": "🎮 PS5（独占）",
        "badges": ['<span class="badge">动作</span>', '<span class="badge">北欧神话</span>', '<span class="badge">Santa Monica</span>'],
        "intro_paras": [
            "<p>《<strong>God of War: Laufey</strong>》是 Santa Monica Studio 的下一部战神新作，"
            "主角<strong>不再是奎托斯</strong>，而是他的妻子、阿特柔斯之母<strong>菲（Faye，即劳菲）</strong>——"
            "由 Deborah Ann Woll 出演，Christopher Judge 继续出演奎托斯。</p>"
            "<p>故事从 2018 年《战神》开篇的<strong>那场葬礼之后</strong>接上：菲在自己的葬礼后醒来，"
            "发现自己身处名为「<strong>Everywhen</strong>」的诸神死后世界，各神话体系的神祇在此争夺权力；"
            "而她生前为保护奎托斯与阿特柔斯所做的安排，正在崩解。</p>"
            "<p>本作 <strong>2027-02-16</strong> 登陆 PS5（独占，已确认发行实体光盘版）。"
            "创意总监 Cory Barlog 明确表示它「不是支线，而是通往下一部奎托斯作品的桥梁」——"
            "那部以奎托斯为主角的新作已在开发中。本页为公开资料整理，<strong>非本人实玩评测</strong>。</p>",
        ],
        "highlights": [
            "<strong>主角换成菲（劳菲）</strong>：系列首次由奎托斯之外的人物担纲主线",
            "<strong>Everywhen 诸神死后世界</strong>：跨神话体系的神祇在此角力",
            "<strong>通往下一部的桥梁</strong>：接续的奎托斯新作已在开发中",
            "<strong>PS5 独占 + 实体光盘</strong>：版本分档与定价尚未公布",
        ],
        "official_links": [
            ('PlayStation 官方页', 'https://www.playstation.com/zh-hans-hk/games/god-of-war-laufey/'),
        ],
        "source_label": "PlayStation 官方页",
        "source_url": "https://www.playstation.com/zh-hans-hk/games/god-of-war-laufey/",
    },
    {
        "slug": "onimusha-way-of-the-sword",
        "title_en": "Onimusha: Way of the Sword",
        "title_zh": "鬼武者 Way of the Sword",
        "developer": "Capcom",
        "publisher": "Capcom",
        "release": "2026-09-25",
        "platform": "PS5 / Xbox Series X|S / Steam / Epic / Switch 2",
        "genre_full": "剑戟动作 / 和风黑暗奇幻",
        "price": "标准版待官方公布（PS Store 为准）",
        "en_subtitle": "Onimusha: Way of the Sword",
        "platform_badge": "🎮 PS5 / Xbox / PC / Switch 2",
        "badges": ['<span class="badge">剑戟动作</span>', '<span class="badge">和风</span>', '<span class="badge">Capcom</span>'],
        "intro_paras": [
            "<p>《<strong>鬼武者 Way of the Sword</strong>》是 Capcom 时隔 20 年推出的<strong>鬼武者系列完全新作</strong>，"
            "主角为日本史上的剑豪<strong>宫本武藏</strong>，并采用已故传奇演员<strong>三船敏郎</strong>作为脸模。</p>"
            "<p>舞台设在江户时代初期的京都——被「瘴气」侵蚀而幻化的古都。"
            "武藏凭借神秘的<strong>鬼之笼手</strong>获得超凡鬼力，与来自地底的异形「幻魔」死战。"
            "战斗保留系列招牌的<strong>一闪</strong>与<strong>魂吸收</strong>，并新增精准格挡、弹反、"
            "Reflex Combo、鬼力刚腕与鬼力疾走等系统。</p>"
            "<p>本作计划 <strong>2026-09-25</strong> 发售，覆盖 PS5 / Xbox Series X|S / Steam / Epic / Nintendo Switch 2，"
            "并已推出约 30 分钟的免费试玩版（清水寺关卡 + 宿敌佐佐木岩流）。本页为公开资料整理，<strong>非本人实玩评测</strong>。</p>",
        ],
        "highlights": [
            "<strong>系列 20 年完全新作</strong>：宫本武藏为主角，三船敏郎脸模",
            "<strong>一闪 + 魂吸收回归</strong>：系列招牌剑戟手感全面进化",
            "<strong>鬼之笼手</strong>：吸收幻魔之魂转化为力量，含刚性/敏捷多形态",
            "<strong>江户京都舞台</strong>：瘴气侵蚀的清水寺、大江山等和风黑暗场景",
        ],
        "official_links": [
            ('CAPCOM 官方站', 'https://www.capcom-games.com/onimusha/ws/zh-hans'),
        ],
        "source_label": "CAPCOM 官方站",
        "source_url": "https://www.capcom-games.com/onimusha/ws/zh-hans",
    },
]

# ---------------------------------------------------------------------------
# 模板读取
# ---------------------------------------------------------------------------
with open(TEMPLATE, encoding="utf-8") as f:
    tpl = f.read()

# 截图整段（gta6 独有，移除避免 404 / 违反 AI 图禁令）
SCREENSHOT_BLOCK = (
    '<div class="section-label">📸 游戏截图</div>\n'
    '<div class="screenshot-grid">\n'
    '  <div class="screenshot-item" data-lightbox data-caption="罪恶都市 街景（PS5 实机）" data-src="../img/games/gta6-shot-vicecity-1.webp"><img width="1600" height="900" src="../img/games/gta6-shot-vicecity-1.webp" alt="罪恶都市 街景（PS5 实机）" loading="lazy" decoding="async"></div>\n'
    '  <div class="screenshot-item" data-lightbox data-caption="罪恶都市 夜景（PS5 实机）" data-src="../img/games/gta6-shot-vicecity-2.webp"><img width="1600" height="900" src="../img/games/gta6-shot-vicecity-2.webp" alt="罪恶都市 夜景（PS5 实机）" loading="lazy" decoding="async"></div>\n'
    '  <div class="screenshot-item" data-lightbox data-caption="利昂尼达群岛（PS5 实机）" data-src="../img/games/gta6-shot-keys.webp"><img width="1600" height="900" src="../img/games/gta6-shot-keys.webp" alt="利昂尼达群岛（PS5 实机）" loading="lazy" decoding="async"></div>\n'
    '  <div class="screenshot-item" data-lightbox data-caption="草河流域 湿地（PS5 实机）" data-src="../img/games/gta6-shot-grassrivers.webp"><img width="1600" height="900" src="../img/games/gta6-shot-grassrivers.webp" alt="草河流域 湿地（PS5 实机）" loading="lazy" decoding="async"></div>\n'
    '  <div class="screenshot-item" data-lightbox data-caption="盖尔霍恩港 工业区（PS5 实机）" data-src="../img/games/gta6-shot-port.webp"><img width="1600" height="900" src="../img/games/gta6-shot-port.webp" alt="盖尔霍恩港 工业区（PS5 实机）" loading="lazy" decoding="async"></div>\n'
    '  <div class="screenshot-item" data-lightbox data-caption="卡拉加大山 国家公园（PS5 实机）" data-src="../img/games/gta6-shot-mountain.webp"><img width="1600" height="900" src="../img/games/gta6-shot-mountain.webp" alt="卡拉加大山 国家公园（PS5 实机）" loading="lazy" decoding="async"></div>\n'
    '</div>\n'
)


def build_title_block(g):
    return (
        f'<title>{g["title_zh"]} | 龙兄的游戏库2026实测避坑｜龙兄知识库</title>\n'
        f'<meta name="keywords" content="{g["title_zh"]} | 龙兄的游戏库,2026实测避坑,实测溯源,龙兄知识库">\n\n'
        f'<meta name="description" content="{g["title_zh"]} | 龙兄的游戏库2026实测避坑：公开资料整理，发售信息、平台、类型与官方资讯。适合 {g["title_zh"]} 关注者与玩家参考。">\n'
    )


def build_og_twitter(g):
    return (
        f'<meta property="og:title" content="{g["title_zh"]} | 龙兄的游戏库2026实测避坑｜龙兄知识库">\n'
        f'<meta property="og:description" content="{g["title_zh"]} | 龙兄的游戏库2026实测避坑：公开资料整理，发售信息、平台、类型与官方资讯。">\n'
        f'<meta property="og:type" content="article">\n'
        f'<meta property="og:url" content="https://longxiong.vip/games/{g["slug"]}.html">\n'
        f'<meta property="og:image" content="https://longxiong.vip/img/og-image.png">\n'
        f'<meta property="og:locale" content="zh_CN">\n'
        f'<meta name="twitter:card" content="summary_large_image">\n'
        f'<meta name="twitter:title" content="{g["title_zh"]} | 龙兄的游戏库">\n'
        f'<meta name="twitter:description" content="{g["title_zh"]}（{g["title_en"]}）公开资料整理：发售信息、平台、类型与官方资讯。">\n'
        f'<meta name="twitter:image" content="https://longxiong.vip/img/og-image.png">\n'
    )


def build_article(g):
    """新文章内容。不包含 <!-- game:begin --> 标记（让 apply_game_guide 干净注入）。"""
    intro = "".join(g["intro_paras"])
    highlights_li = "\n".join(f"      <li>{h}</li>" for h in g["highlights"])
    official_li = "\n".join(
        f'      <li><a href="{u}" target="_blank" rel="noopener">{label} ↗</a></li>'
        for label, u in g["official_links"]
    )
    return (
        f'<div class="game-title-wrap">\n'
        f'<h1>{g["title_zh"]}</h1>\n'
        f'<h2 style="position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border:0">游戏资料</h2>\n'
        f'<div class="bm-bar"><button class="bm-btn" type="button" data-bm-btn aria-pressed="false" title="收藏这篇文章（本地保存，无需登录）"><svg class="bm-star" viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/></svg><span class="bm-label">收藏</span></button></div>\n'
        f'<span class="en-title">{g["en_subtitle"]}</span>\n'
        f'<div class="game-meta">\n'
        f'<span class="badge platform">{g["platform_badge"]}</span>\n'
        f'<span class="badge status-follow">🔖 资料</span>\n'
        + "".join(b + "\n" for b in g["badges"]) +
        f'</div>\n'
        f'<div class="table-wrapper">\n'
        f'<table class="info-table">\n'
        f'<tr><th>开发商</th><td>{g["developer"]}</td></tr><tr><th>发行商</th><td>{g["publisher"]}</td></tr><tr><th>发售日期</th><td>{g["release"]}</td></tr><tr><th>平台</th><td>{g["platform"]}</td></tr><tr><th>类型</th><td>{g["genre_full"]}</td></tr><tr><th>首发定价</th><td>{g["price"]}</td></tr>\n'
        f'</table>\n'
        f'</div>\n'
        f'<div class="rating"><span>资料状态：</span><span style="color:var(--gm)">公开资料整理 · 非本人实玩评测</span></div>\n'
        f'</div>\n'
        f'</div>\n\n'
        f'<div class="detail-section">\n\n'
        f'<div class="section-label">🎮 游戏简介</div>\n'
        f'<div class="desc-box">\n'
        f'{intro}\n'
        f'</div>\n\n'
        f'<div class="section-label">🕹️ 核心特色</div>\n'
        f'<div class="gameplay-notes">\n'
        f'<h3>本作亮点</h3>\n'
        f'<ul>\n'
        f'{highlights_li}\n'
        f'</ul>\n'
        f'</div>\n\n'
        f'<div class="section-label">📌 资料说明</div>\n'
        f'<div class="desc-box">\n'
        f'<p>本页为<strong>公开资料整理</strong>，<strong>非本人实玩评测</strong>。'
        f'所有信息（开发商、发行商、发售日、平台、定价、类型）来自各游戏官方网站与权威商店页面，'
        f'数据截至 <strong>2026-08</strong> 核验，已交叉核对；游戏更新、价格调整或平台变动后可能与官方最新公告存在差异，'
        f'<strong>以官方为准</strong>。本节暂不收录官方截图，发行后可补；所有信息以官方公告为准。</p>\n'
        f'</div>\n\n'
        f'<div class="section-label">🔗 官方与购买</div>\n'
        f'<div class="gameplay-notes">\n'
        f'<h3>前往官方渠道</h3>\n'
        f'<ul>\n'
        f'{official_li}\n'
        f'</ul>\n'
        f'</div>\n\n'
        f'</div>\n'
    )


def build_sources(g):
    return (
        f'<p style="margin-top:8px;font-size:0.8rem;color:var(--text-muted);">最后更新：2026-08-30</p>\n'
        f'<p style="margin-top:6px;font-size:0.78rem;line-height:1.7;color:var(--text-muted);max-width:820px;margin-left:auto;margin-right:auto;"><a id="sources" class="src-anchor"></a>资料来源：<a href="{g["source_url"]}" target="_blank" rel="noopener" style="color:var(--blue)">{g["source_label"]}</a>（各游戏官方网站与商店页）；发售与定价数据截至 2026-08 核验，已交叉核对。本页为公开资料整理，非本人实玩评测，游戏更新后可能与官方最新公告存在差异，以官方为准。（外部链接 2026-08 核验可达）</p>\n'
    )


# ---------------------------------------------------------------------------
# 渲染 5 个页面
# ---------------------------------------------------------------------------
# 计算文章区终点：`<!-- game:begin -->` 之前最近的 `</div>`
# 起点：`<div class="game-title-wrap">\n<h1>侠盗猎车手 VI</h1>`
article_start = '<div class="game-title-wrap">\n<h1>侠盗猎车手 VI</h1>'
gb_marker = '<!-- game:begin -->'
s_base = tpl.find(article_start)
gb_pos = tpl.find(gb_marker, s_base)
assert s_base != -1 and gb_pos != -1, "模板缺关键标记（game-title-wrap / game:begin）"
e_base = tpl.rfind('</div>', s_base, gb_pos) + len('</div>')

count = 0
for g in GAMES:
    out = tpl

    # 1) 替换文章区
    out = out[:s_base] + build_article(g) + out[e_base:]
    # 1b) 替换面包屑标题
    out = out.replace(
        '<a href="../games.html">游戏库</a><span>›</span>\n<span>侠盗猎车手 VI</span>',
        f'<a href="../games.html">游戏库</a><span>›</span>\n<span>{g["title_zh"]}</span>',
    )
    # 1c) 移除封面图（无官方素材，避免 404；hero 保留 title-wrap）
    out = out.replace('<div class="detail-cover" data-lightbox data-caption="侠盗猎车手 VI" data-src="../img/games/gta6-cover.webp"><img width="1200" height="630" src="../img/games/gta6-cover.webp" alt="侠盗猎车手 VI 封面" loading="lazy" decoding="async">\n</div>\n', "")


    # 2) 剥除旧 game 块
    out = re.sub(r"<!-- game:begin -->.*?<!-- game:end -->\n?", "", out, flags=re.S)
    # 3) 剥除旧 related 块
    out = re.sub(r"<!-- related:begin -->.*?<!-- related:end -->\n?", "", out, flags=re.S)
    # 4) 剥除截图区
    out = out.replace(SCREENSHOT_BLOCK, "")
    # 5) 修正版权措辞
    out = out.replace(
        "图片为各游戏官方公开美术图与实机截图，版权归原权利方所有。",
        "本节暂不收录官方截图，发行后可补；所有信息以官方公告为准。",
    )

    # 6) 替换 title + meta
    out = out.replace(
        '<title>侠盗猎车手 VI | 龙兄的游戏库2026实测避坑｜龙兄知识库</title>\n'
        '<meta name="keywords" content="侠盗猎车手 VI | 龙兄的游戏库,2026实测避坑,实测溯源,龙兄知识库">\n\n'
        '<meta name="description" content="侠盗猎车手 VI | 龙兄的游戏库2026实测避坑：实测溯源、实操图文、避坑指南。适合侠盗猎车手 VI | 龙兄的游戏库爱好者与从业者参考，掌握核心要点、规避常见误区。">\n',
        build_title_block(g),
    )
    # 7) 替换 og / twitter
    out = out.replace(
        '<meta property="og:title" content="侠盗猎车手 VI | 龙兄的游戏库2026实测避坑｜龙兄知识库">\n'
        '<meta property="og:description" content="侠盗猎车手 VI | 龙兄的游戏库2026实测避坑：实测溯源、实操图文、避坑指南。适合侠盗猎车手 VI | 龙兄的游戏库爱好者与从业者参考，掌握核心要点、规避常见误区。">\n'
        '<meta property="og:type" content="article">\n'
        '<meta property="og:url" content="https://longxiong.vip/games/gta6.html">\n'
        '<meta property="og:image" content="https://longxiong.vip/img/og-image.png">\n'
        '<meta property="og:locale" content="zh_CN">\n'
        '<meta name="twitter:card" content="summary_large_image">\n'
        '<meta name="twitter:title" content="侠盗猎车手 VI | 龙兄的游戏库">\n'
        '<meta name="twitter:description" content="侠盗猎车手 VI（Grand Theft Auto VI）公开资料整理：发售信息、平台、类型与官方美术图。">\n'
        '<meta name="twitter:image" content="https://longxiong.vip/img/og-image.png">\n',
        build_og_twitter(g),
    )
    # 8) 替换 sources 段落
    out = out.replace(
        '<p style="margin-top:8px;font-size:0.8rem;color:var(--text-muted);">最后更新：2026-08-16</p>\n'
        '<p style="margin-top:6px;font-size:0.78rem;line-height:1.7;color:var(--text-muted);max-width:820px;margin-left:auto;margin-right:auto;"><a id="sources" class="src-anchor"></a>资料来源：<a href="https://www.rockstargames.com/VI" target="_blank" rel="noopener" style="color:var(--blue)">Rockstar 官方站</a>（各游戏官方网站与商店页）；发售与定价数据截至 2026-08 核验，已交叉核对。本页为公开资料整理，非本人实玩评测，游戏更新后可能与官方最新公告存在差异，以官方为准。（外部链接 2026-08 核验可达）</p>',
        build_sources(g),
    )
    # 9) 替换 JSON-LD
    out = out.replace(
        '"headline": "侠盗猎车手 VI | 龙兄的游戏库",\n'
        '      "url": "https://longxiong.vip/games/gta6.html",\n'
        '      "description": "侠盗猎车手 VI（Grand Theft Auto VI）公开资料整理：发售信息、平台、类型与官方美术图。"',
        f'"headline": "{g["title_zh"]} | 龙兄的游戏库",\n'
        f'      "url": "https://longxiong.vip/games/{g["slug"]}.html",\n'
        f'      "description": "{g["title_zh"]}（{g["title_en"]}）公开资料整理：发售信息、平台、类型与官方资讯。"',
    )

    out_path = os.path.join(GAMES_DIR, f"{g['slug']}.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(out)
    count += 1
    print(f"  ✓ {g['slug']}.html  ({len(out)} chars)")

print(f"\n生成完成：{count} 个游戏页")
