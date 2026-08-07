#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成 static/chinajoy.html —— ChinaJoy 成长史板块页

可持续更新方式：
  1. 在下方 EDITIONS 列表最前面追加新一届的数据（保持字段一致）
  2. 如有新的里程碑 / 观众人次，同步更新 MILESTONES / ATTENDANCE
  3. 运行：python3 scripts/build_chinajoy.py
  4. hugo --gc 构建后提交即可

页面结构与站内其它板块页（herbs/console/marvel）完全一致：
  critical CSS -> navbar(内联) -> 面包屑 -> hero -> 自动更新动态 -> 正文 -> footer -> 脚本
"""
import os
import re
import html as htmllib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'static', 'chinajoy.html')
DONOR = os.path.join(ROOT, 'static', 'herbs.html')

LAST_UPDATE = '2026-08-06'

# ---------------------------------------------------------------- 年代分期
ERAS = [
    ('start', '起步落沪', '2004–2007', '从北京到上海，韩流网游当道，国产逐步崛起'),
    ('indus', '产业化',   '2008–2012', 'BTOB 落地、国内展品反超，展会变成产业平台'),
    ('mobile', '移动泛娱乐', '2013–2016', '手游爆发，CAWAE 与 eSmart 让边界向动漫、硬件延伸'),
    ('tech',  '科技驱动', '2017–2021', '规模冲上历史高点，5G、云、数字生活成为关键词'),
    ('newcy', '新周期',   '2023–2026', '二十周年后回归玩家，AI 第一次被写进主题'),
]

# ---------------------------------------------------------------- 历届数据
# no=届次, year=年份, date=日期, city, venue, theme, theme_en,
# scale=规模要点(list), games=代表作(list), brands=代表厂商(list), points=看点(list)
EDITIONS = [
    dict(no=23, year=2026, era='newcy', date='2026.7.31 – 8.3', city='上海',
         venue='上海新国际博览中心', theme='与 AI 同游', theme_en='Level Up With AI',
         scale=['总展览面积超 14 万㎡', '近 900 家企业参展（外资 275 家）', '覆盖 39 个国家和地区',
                'BTOC 近 12 万㎡ / 超 350 家', 'BTOB 2.5 万㎡ / 超 500 家（外资占 46.6%）',
                '超 500 家厂商带来逾 1000 款游戏', 'Steam 线上盛典报名超 600 款',
                'ChinaJoy Express 试玩区 88 款'],
         games=['魔兽世界', '炉石传说', '守望先锋', '暗黑破坏神 IV', '星际争霸 II', '逃离塔科夫'],
         brands=['腾讯游戏', '网易游戏', '暴雪游戏', '世纪华通', '巨人网络', '完美世界', '金山世游',
                 '咪咕互娱', '朝夕光年', '顺网科技', 'PlayStation', '360 游戏', '恺英网络',
                 'B站游戏', '华为游戏中心', '4399 & 好游快爆', 'Pocketpair', '高通骁龙',
                 'TCL 华星', '宇树科技'],
         points=['ChinaJoy 历史上第一次把「AI」写进展会主题',
                 '高通骁龙主题馆以「AI 驱动体验进化」为核心，联合三大运营商、中国广电与小米 / iQOO / 一加 / 荣耀 / 努比亚 / 红魔 / 联想 / 京东等品牌',
                 '宇树科技、逐际动力、魔法原子、露米智能、云幕智造等携人形机器人与具身智能产品集中亮相',
                 '新增「地偶街区」「ChinaJoy Next Play 创新游戏体验场」与国潮特色展区',
                 '同期举办第二届中国国际游戏开发者大会、全球电竞大会与 CDEC',
                 '中国音数协游戏工委与清华大学调研：国内游戏企业研发环节 AI 应用率已达 86.36%']),

    dict(no=22, year=2025, era='newcy', date='2025.8.1 – 8.4', city='上海',
         venue='上海新国际博览中心', theme='聚 · 你所爱', theme_en='',
         scale=['启用 11.5 个展馆 / 13.5 万㎡', '799 家企业参展', 'BTOC 313 家 / 11 万㎡',
                'BTOB 486 家 / 2.5 万㎡，来自 37 个国家和地区，海外及外资占比近 43%',
                '观众 41.03 万人次（历史新高）', 'BTOB 商务馆 41231 人次，海外观众占 35.82%'],
         games=['燕云十六声', '逆水寒', '第五人格', '永劫无间', '遗忘之海', '命运：群星', '无主星渊',
                '异环', 'DOTA2', '反恐精英：全球攻势', '女神异闻录：夜幕魅影', '诛仙世界', '解限机',
                '超自然行动组', '金庸群侠传', '无尽冬日', '最终幻想 14', '大航海时代：起源',
                '鹅鸭杀', '猫咪和汤', '斗罗大陆：猎魂世界', '无畏契约', 'DNF', '明日方舟'],
         brands=['腾讯游戏', '网易游戏', '暴雪游戏', '世纪华通', '完美世界', '巨人网络', '西山居',
                 '金山世游', '三七互娱', '万代南梦宫', 'PlayStation', '华为游戏中心', '4399',
                 '比亚迪', '高通骁龙'],
         points=['暴雪搭建「暴雪街区」，5 米高的大天使泰瑞尔雕像与巫妖王无敌战马领衔 70 余尊角色雕像',
                 '网易把《燕云十六声》凉州「葡萄美酒夜光杯」场景搬进现场，《逆水寒》巨型水缸美人鱼表演出圈',
                 '比亚迪展台带来与《黑神话：悟空》联动的痛车',
                 '腾讯占据 N4 馆近一半空间，「Cool 鹅夏日营地」主舞台 +《无畏契约》《符文战场》《DNF》专属展台',
                 'N5 馆为骁龙主题馆，聚合市面主流骁龙合作硬件品牌',
                 '主办方携《第五人格》《鸣潮》推出联名限定 IP 谷子门票',
                 '观众画像：男性 66% / 女性 34%，18–24 岁 33%、25–29 岁 31%，上海本地观众仅占 39%']),

    dict(no=21, year=2024, era='newcy', date='2024.7.26 – 7.29', city='上海',
         venue='上海新国际博览中心', theme='初心「游」在，精彩无限', theme_en='Stay True, Game On.',
         scale=['由国家新闻出版署与上海市人民政府共同指导'],
         games=[], brands=[],
         points=['主打「游戏 + IP」跨界，推动游戏与中华传统文化、当代美学融合',
                 '口号回到玩家视角，强调行业在版号常态化后重拾「初心」']),

    dict(no=20, year=2023, era='newcy', date='2023.7.28 – 7.31', city='上海',
         venue='上海新国际博览中心', theme='相伴二十载，越来悦精彩', theme_en='',
         scale=['四天展期吸引观众 33.8 万人次'],
         games=[], brands=[],
         points=['ChinaJoy 二十周年，同年 12 月中国游戏产业年会同期举办二十周年庆典',
                 '首次举办 AIGC 产业大会，AI 正式进入同期会议议程（尚未成为主角）',
                 '疫情三年后的全面回归，线下人气迅速修复']),

    dict(no=None, year=2022, era='newcy', date='停办', city='—', venue='—',
         theme='因疫情未能举办', theme_en='',
         scale=['ChinaJoy 创办以来唯一一次中断'],
         games=[], brands=[],
         points=['受疫情影响，2022 年未举办，届次由第 19 届直接顺延至 2023 年的第 20 届']),

    dict(no=19, year=2021, era='tech', date='2021.7.30 – 8.2', city='上海',
         venue='上海新国际博览中心', theme='科技创梦，乐赢未来', theme_en='',
         scale=[], games=[], brands=[],
         points=['连续第四届把「科技」写进主题，云游戏与数字生活成为论坛焦点']),

    dict(no=18, year=2020, era='tech', date='2020.7.31 – 8.3', city='上海',
         venue='上海新国际博览中心', theme='科技 · 引领数字娱乐新浪潮', theme_en='',
         scale=[], games=[], brands=['中国联通', '高通'],
         points=['疫情之下如期线下举办，成为当年全球罕见的大型线下游戏展',
                 '中国联通携手高通联合布展呈现 5G 成果，「5G 快闪直播间」成为现场热点']),

    dict(no=17, year=2019, era='tech', date='2019.8.2 – 8.5', city='上海',
         venue='上海新国际博览中心', theme='数字新娱乐，科技新生活', theme_en='',
         scale=['观众 36.47 万人次（疫情前的历史峰值）'],
         games=[], brands=[],
         points=['人气达到疫情前顶点，展会的「泛娱乐 + 科技」结构基本定型']),

    dict(no=16, year=2018, era='tech', date='2018.8.3 – 8.6', city='上海',
         venue='上海新国际博览中心', theme='新科技 新娱乐 新价值', theme_en='',
         scale=[], games=[], brands=[],
         points=['主题从「泛娱乐」切换到「科技」，此后连续四届延续科技主线']),

    dict(no=15, year=2017, era='tech', date='2017.7.27 – 7.30', city='上海',
         venue='上海新国际博览中心', theme='娱乐升级，全民消费时代到来', theme_en='',
         scale=['展出总面积 17 万㎡（历届最大）', '15 个展馆，BTOC 互动娱乐区 13 万㎡',
                '参展企业 900 多家', '展品 4000 款、现场体验机 5000 台以上', '观众超 30 万人次'],
         games=[], brands=[],
         points=['展出面积创下 ChinaJoy 历史纪录，至今未被超越',
                 '「全民消费」的提法标志游戏正式被视为大众消费品类']),

    dict(no=14, year=2016, era='mobile', date='2016.7.28 – 7.31', city='上海',
         venue='上海新国际博览中心', theme='游戏新时代，拥抱泛娱乐', theme_en='',
         scale=['来自 30 多个国家和地区的千余家企业参展'],
         games=[], brands=[],
         points=['同期首次举办国际智能娱乐硬件展览会（eSmart），完成「软硬兼备」战略布局',
                 '主办方发布展台着装「正误图示」，规范细到服装遮盖与模特互动']),

    dict(no=13, year=2015, era='mobile', date='2015.7.30 – 8.2', city='上海',
         venue='上海新国际博览中心', theme='让快乐更简单', theme_en='',
         scale=['来自 30 多个国家和地区的 700 余家企业参展'],
         games=[], brands=[],
         points=['主题回归「快乐」本身，呼应手游把游戏门槛大幅拉低的行业变化']),

    dict(no=12, year=2014, era='mobile', date='2014.7.31 – 8.3', city='上海',
         venue='上海新国际博览中心', theme='大作的时代，永不停歇的盛宴', theme_en='',
         scale=[], games=[], brands=[],
         points=['同期首次举办中国国际动漫及衍生品展览会（CAWAE），「游戏 + 动漫」双轮启动']),

    dict(no=11, year=2013, era='mobile', date='2013.7.25 – 7.28', city='上海',
         venue='上海新国际博览中心', theme='游戏演绎梦想，移动畅想未来', theme_en='',
         scale=[], games=[], brands=[],
         points=['移动游戏爆发元年，上半年手游收入激增',
                 '主题第一次把「移动」写进标题，此后数年产品形态与商业模式彻底改写']),

    dict(no=10, year=2012, era='indus', date='2012.7.26 – 7.29', city='上海',
         venue='上海新国际博览中心', theme='十进位 · 新纪元', theme_en='',
         scale=['中、美、日、德、韩等 20 余个国家和地区 300 多家企业参展', '展出面积约 7 万㎡'],
         games=[], brands=['索尼', 'EA', '暴雪', 'Intel', 'AMD', 'NVIDIA', 'Crytek'],
         points=['ChinaJoy 十周年，首次拥有编号式的纪念主题',
                 '芯片与硬件厂商大举进场，为四年后的 eSmart 埋下伏笔']),

    dict(no=9, year=2011, era='indus', date='2011.7.28 – 7.31', city='上海',
         venue='上海新国际博览中心', theme='', theme_en='',
         scale=['展出面积 6 万㎡', '展商 283 家（国内 204 / 国际 79）', '参展游戏 482 款',
                '观众约 15 万人次'],
         games=['火瀑', '魔兽世界', '星际争霸 2', '最终幻想 14', '黑金', '巫师之怒', '七龙珠 OL',
                '地下城守护者 OL'],
         brands=['第九城市', '暴雪', '网龙', 'EA'],
         points=['国际展商数量首次突破 70 家',
                 '开幕前主办方要求各展台严格审核演出人员数量、衣着与内容']),

    dict(no=8, year=2010, era='indus', date='2010.7.29 – 8.1', city='上海',
         venue='上海新国际博览中心', theme='与世博同行，共创美好生活', theme_en='',
         scale=['展出面积 5 万㎡', '展商 195 家（国内 160 / 国际 35）', '展品 407 款',
                '观众约 14 万人次（含约 2 万专业观众）'],
         games=['龙之谷之天空战记'], brands=['新浪微博', '中国移动游戏基地', '华友世纪'],
         points=['首次出现正式的展会主题，与上海世博会形成联动',
                 '新浪微博首次以展台形式亮相 ChinaJoy']),

    dict(no=7, year=2009, era='indus', date='2009.7.23 – 7.26', city='上海',
         venue='上海新国际博览中心', theme='', theme_en='',
         scale=['展商 192 家（国内 158 / 国际 34）', '参展游戏 367 款', '观众约 13 万人次'],
         games=[], brands=[],
         points=['高峰论坛体系成型：产业高峰论坛 + 投资、移动娱乐、休闲游戏三大分论坛',
                 '电竞大赛、Cosplay 嘉年华、Miss ChinaJoy 成为固定配套活动']),

    dict(no=6, year=2008, era='indus', date='2008.7.17 – 7.19', city='上海',
         venue='上海新国际博览中心', theme='', theme_en='',
         scale=['展出面积 4 万㎡', '169 家企业参展（国内 142 / 国际 27）',
                '展品 354 款（国内 207 / 国际 147）'],
         games=[],
         brands=['盛大', '网易', '第九城市', '巨人', '久游网', '完美时空', '腾讯', '金山',
                 '世纪天成', '联众', '育碧', '索尼'],
         points=['首次设立 BTOB 商务洽谈展区，展会从「玩家嘉年华」升级为产业平台',
                 '国内展品数量首次超过国外展品，标志国产游戏完成反超',
                 '新闻出版总署副署长在高峰论坛上首次公开批评部分网游对青少年的影响']),

    dict(no=5, year=2007, era='start', date='2007.7.12 – 7.15', city='上海',
         venue='上海新国际博览中心', theme='', theme_en='',
         scale=['展商 163 家（国内 139 / 国际 24）', '参展游戏 345 款', '观众约 10 万人次'],
         games=['魔兽世界：燃烧的远征', 'FIFA Online', '命令与征服 3：泰伯利亚之战',
                '模拟人生 — 生活物语', '仙剑 OL', '战锤', 'DOA Online', '一骑当千'],
         brands=['EA', '网禅', '世纪天成'],
         points=['《魔兽世界：燃烧的远征》中文版现场试玩，资料片时代到来',
                 '观众数量首次达到 10 万量级']),

    dict(no=4, year=2006, era='start', date='2006.7.28 – 7.30', city='上海',
         venue='上海新国际博览中心', theme='', theme_en='',
         scale=['展商 161 家（国内 138 / 国际 23）', '参展游戏 338 款（国内 138 / 国际 200）',
                '观众 134738 人次'],
         games=['剑网 3', '新大话西游 II', '暗黑之门', '天下贰', '奇迹世界', '卓越之剑',
                '一骑当千', '莎木 OL', '苍天', '激战'],
         brands=['索尼', '世嘉', 'KONAMI', 'Square Enix', 'EA', '育碧', '光荣'],
         points=['PlayStation 3 正式亮相 ChinaJoy',
                 '国际知名游戏公司参展数量创下当时之最',
                 '《剑网 3》《新大话西游 II》首次曝光，《天下贰》现场发放内测号']),

    dict(no=3, year=2005, era='start', date='2005.7.20 – 7.23', city='上海',
         venue='上海新国际博览中心', theme='', theme_en='',
         scale=['展位面积 2.5 万㎡', '展商 156 家（国内 137 / 国际 19）',
                '参展游戏 289 款（国内 97 / 国际 192）', '观众约 8 万人次', '门票 20 元'],
         games=['梦幻西游', '快乐西游', '洛奇', '完美世界'],
         brands=['EA', 'Intel', '索尼', '世嘉', '光荣', '育碧', '盛大', '网易', '第九城市'],
         points=['Cosplay 嘉年华第一次面向全国海选，成为展会最具吸引力的配套活动',
                 '明星站台成风：杨千嬅、张韶涵、张娜拉、水木年华、周星驰、元华悉数到场',
                 '国产游戏势头强劲，市场份额肉眼可见地上升']),

    dict(no=2, year=2004, era='start', date='2004.10.5 – 10.7', city='上海',
         venue='上海新国际博览中心', theme='', theme_en='',
         scale=['展商 140 家（国内 126 / 国际 14）', '参展游戏 167 款（国内 58 / 国际 109）',
                '观众约 7 万人次'],
         games=['魔兽世界', '仙剑奇侠传', '梦幻西游'],
         brands=['暴雪', '第九城市', '索尼', '育碧', 'EA', '唯美德', '网易',
                 '韩国游戏产业开发院（20 家）'],
         points=['ChinaJoy 自本届起永久落户上海',
                 '九城代理的《魔兽世界》成为全场最大焦点，此后深刻改写中国网游与网吧生态',
                 'Cosplay 比赛扩大规模并吸纳社会团体，22 家游戏厂商参赛',
                 'Showgirl 文化自此萌芽，也为日后的争议埋下伏笔']),

    dict(no=1, year=2004, era='start', date='2004.1.16 – 1.18', city='北京',
         venue='北京展览馆', theme='', theme_en='',
         scale=['展商 129 家（国内 117 / 国际 12）', '展品 145 款（国内 39 / 国际 106）',
                '观众约 6 万人次', '门票 20 元，在线预订 15 元'],
         games=['天堂 II', '大话西游 Online II', '传奇 3', '传奇世界', '神迹', '实况足球 7',
                '凯旋', '铁血三国志'],
         brands=['新浪乐谷', '网易', '光通', '盛大', '索尼', '腾讯', '华义'],
         points=['原定 2003 年 7 月在北京举办，先因扩大规模改址北京展览馆，又因非典（SARS）延期至 2004 年 1 月',
                 '全称为「中国国际数码互动娱乐产品及技术应用展览会」，当时国内市场以代理海外网游为主',
                 '韩国网游占据压倒性优势，同场展出的韩游超过 20 款',
                 '中央展厅领取《天堂 II》内测账号的队伍排成长龙，一直蜿蜒到邻近展厅',
                 '首届 Cosplay 嘉年华仅有游戏厂商参加']),
]

# ---------------------------------------------------------------- 品牌里程碑
MILESTONES = [
    ('2003', '筹备立项', '网络游戏成为中国数字内容产业中发展最蓬勃的领域，ChinaJoy 应运而生'),
    ('2004.01', '首届开幕', '第一届 ChinaJoy 在北京展览馆举行，中国游戏第一次有了属于自己的产业盛会'),
    ('2004.10', '永久落沪', '第二届移师上海新国际博览中心，此后永久落户上海'),
    ('2008', 'BTOB 展区', '设立商务洽谈展区，全面提升展会的商务服务功能，助力国产内容出海'),
    ('2014', 'CAWAE', '同期举办中国国际动漫及衍生品展览会，向动漫与文创延伸'),
    ('2016', 'eSmart', '国际智能娱乐硬件展览会成功举办，完成「软硬兼备」战略布局'),
    ('近年', 'CJTS / CJFM', '组织潮流玩具及模型展，把娱乐边界拓展到二次元与潮玩'),
    ('2023', 'AIGC 产业大会', '二十周年首办 AIGC 产业大会，AI 进入同期会议议程'),
    ('2026', '新展区上线', '新增地偶街区、ChinaJoy Next Play 创新游戏体验场与国潮特色展区'),
]

# ---------------------------------------------------------------- 观众人次
ATTENDANCE = [
    (2004, 6.0, '第 1 届'), (2004, 7.0, '第 2 届'), (2005, 8.0, '第 3 届'),
    (2006, 13.5, '第 4 届'), (2007, 10.0, '第 5 届'), (2009, 13.0, '第 7 届'),
    (2010, 14.0, '第 8 届'), (2011, 15.0, '第 9 届'), (2017, 30.0, '第 15 届'),
    (2019, 36.5, '第 17 届'), (2023, 33.8, '第 20 届'), (2025, 41.0, '第 22 届'),
]

# ---------------------------------------------------------------- 名人堂
HALL = [
    ('国际主机与 3A', '#4f46e5',
     ['索尼 PlayStation', '暴雪娱乐', '世嘉', 'KONAMI', 'Square Enix', '育碧',
      'Electronic Arts', '万代南梦宫', '光荣', 'Pocketpair']),
    ('国内头部厂商', '#c2410c',
     ['腾讯游戏', '网易游戏', '盛大 / 世纪华通', '完美世界', '巨人网络', '西山居 / 金山世游',
      '三七互娱', '第九城市', '恺英网络', '朝夕光年', '4399']),
    ('硬件与科技', '#0f766e',
     ['高通骁龙', 'Intel', 'AMD', 'NVIDIA', '华为', '中国移动咪咕', '顺网科技', 'TCL 华星',
      '宇树科技', '比亚迪']),
    ('平台与渠道', '#7e22ce',
     ['B站游戏', '好游快爆', '360 游戏', '京东', 'Steam 线上盛典', '新浪微博', '中国联通']),
]

SOURCES = [
    ('ChinaJoy 官方网站', 'https://www.chinajoy.net/'),
    ('ChinaJoy 英文官网（历届规模数据）', 'https://en.chinajoy.net/'),
    ('中国音像与数字出版协会 · 游戏工委', 'https://www.cgigc.com.cn/'),
]


# ================================================================= 工具函数
def esc(s):
    return htmllib.escape(str(s), quote=True)


def extract(donor_html, start_mark, end_mark, inclusive=True):
    """从供体页面里按标记截取一段（用于复用导航 / 页脚等公共结构）"""
    i = donor_html.index(start_mark)
    j = donor_html.index(end_mark, i)
    return donor_html[i:j + len(end_mark)] if inclusive else donor_html[i + len(start_mark):j]


def chips_html(items, cls='cj-chip-tag'):
    return ''.join('<span class="%s">%s</span>' % (cls, esc(x)) for x in items)



# ================================================================= 真实现场照片
# 仅当用户把真实现场照片放到  static/img/chinajoy/<年份>.{jpg,jpeg,png,webp,gif}
# 才会在该届卡片顶部显示图片。绝不生成或使用任何 AI 图片；无照片则卡片纯文字。
PHOTO_DIR = os.path.join(ROOT, 'static', 'img', 'chinajoy')

def resolve_photo(year):
    """仅返回真实存在的现场照片路径；无照片返回 None（不渲染任何占位图）"""
    for ext in ('jpg', 'jpeg', 'png', 'webp', 'gif'):
        p = os.path.join(PHOTO_DIR, '%d.%s' % (year, ext))
        if os.path.exists(p):
            return 'img/chinajoy/%d.%s' % (year, ext)
    return None

def build_edition_card(e):
    no = e['no']
    is_gap = no is None
    era = e['era']
    badge = '停办' if is_gap else '第 %d 届' % no
    search_pool = ' '.join([
        str(e['year']), badge, e['theme'], e['theme_en'], e['city'], e['venue'],
        ' '.join(e['games']), ' '.join(e['brands']), ' '.join(e['points']),
        ' '.join(e['scale']),
    ]).lower()

    parts = []
    parts.append('<article class="cj-card%s" data-era="%s" data-year="%s" data-q="%s">'
                 % (' cj-card-gap' if is_gap else '', era, e['year'], esc(search_pool)))
    # 真实现场照片（仅当用户已放入对应年份的真图才显示，绝不用 AI 图）
    photo = resolve_photo(e['year'])
    if photo:
        alt = ('第 %d 届 ChinaJoy 现场' % e['no']) if not is_gap else 'ChinaJoy 展会现场'
        parts.append('  <div class="cj-card-img-wrap">'
                     '<img class="cj-card-img" src="%s" alt="%s" loading="lazy" '
                     'width="320" height="200" decoding="async"></div>' % (esc(photo), esc(alt)))
    parts.append('  <div class="cj-card-head">')
    parts.append('    <div class="cj-card-no">%s</div>' % esc(badge))
    parts.append('    <div class="cj-card-meta">')
    parts.append('      <div class="cj-card-year">%s</div>' % e['year'])
    parts.append('      <div class="cj-card-date">%s</div>' % esc(e['date']))
    parts.append('    </div>')
    if not is_gap:
        parts.append('    <div class="cj-card-place">%s<span class="cj-venue">%s</span></div>'
                     % (esc(e['city']), esc(e['venue'])))
    parts.append('  </div>')

    if e['theme']:
        en = ('<span class="cj-theme-en">%s</span>' % esc(e['theme_en'])) if e['theme_en'] else ''
        label = '状态' if is_gap else '主题'
        parts.append('  <div class="cj-theme"><span class="cj-theme-label">%s</span>'
                     '<span class="cj-theme-txt">%s</span>%s</div>' % (label, esc(e['theme']), en))
    else:
        parts.append('  <div class="cj-theme cj-theme-none">'
                     '<span class="cj-theme-label">主题</span>'
                     '<span class="cj-theme-txt">未设置正式主题</span></div>')

    # ---- 详情（默认折叠，点击展开，降低长内容压迫感）----
    detail = []
    if e['scale']:
        detail.append('  <ul class="cj-scale">')
        for s in e['scale']:
            detail.append('    <li>%s</li>' % esc(s))
        detail.append('  </ul>')
    if e['games']:
        detail.append('  <div class="cj-block"><span class="cj-block-label">参展游戏</span>'
                     '<div class="cj-tags">%s</div></div>' % chips_html(e['games'], 'cj-tag cj-tag-game'))
    if e['brands']:
        detail.append('  <div class="cj-block"><span class="cj-block-label">参展品牌</span>'
                     '<div class="cj-tags">%s</div></div>' % chips_html(e['brands'], 'cj-tag cj-tag-brand'))
    if e['points']:
        detail.append('  <div class="cj-block"><span class="cj-block-label">本届看点</span>')
        detail.append('    <ul class="cj-points">')
        for p in e['points']:
            detail.append('      <li>%s</li>' % esc(p))
        detail.append('    </ul>')
        detail.append('  </div>')

    # 概要行：不展开也能快速扫读这届有什么
    teaser = []
    if e['games']:
        teaser.append('参展游戏 %d' % len(e['games']))
    if e['brands']:
        teaser.append('品牌 %d' % len(e['brands']))
    if e['points']:
        teaser.append('看点 %d' % len(e['points']))
    if teaser:
        parts.append('  <div class="cj-card-teaser">%s</div>' % ' · '.join(esc(t) for t in teaser))

    if detail:
        parts.append('  <button type="button" class="cj-card-toggle" aria-expanded="false">'
                     '<span class="cj-toggle-txt">展开详情</span> <span class="cj-caret">▾</span></button>')
        parts.append('  <div class="cj-card-detail">')
        parts.extend(detail)
        parts.append('  </div>')
    parts.append('</article>')
    return '\n'.join(parts)


# ================================================================= 页面组装
def main():
    with open(DONOR, encoding='utf-8') as f:
        donor = f.read()

    critical = extract(donor, '<style id="critical-css">', '</style>')
    navbar = extract(donor, '<nav class="navbar"', '</nav>')
    footer = extract(donor, '<footer role="contentinfo">', '</footer>')

    # 导航高亮切换到 ChinaJoy（herbs 供体上是中药材高亮）
    navbar = navbar.replace('<a href="herbs.html" class="active">中药材</a>',
                            '<a href="herbs.html">中药材</a>')
    navbar = navbar.replace('<a href="chinajoy.html">ChinaJoy 成长史</a>',
                            '<a href="chinajoy.html" class="active">ChinaJoy 成长史</a>')
    if 'chinajoy.html' not in navbar:
        raise SystemExit('供体导航缺少 ChinaJoy 链接，请先运行导航注入脚本')

    held = [e for e in EDITIONS if e['no'] is not None]
    total_editions = max(e['no'] for e in held)
    first_year = min(e['year'] for e in held)

    cards = '\n\n'.join(build_edition_card(e) for e in EDITIONS)

    era_chips = ['<button class="cj-chip active" data-era="all">全部 <b>%d</b></button>' % len(EDITIONS)]
    for key, name, span, _desc in ERAS:
        n = len([e for e in EDITIONS if e['era'] == key])
        era_chips.append('<button class="cj-chip" data-era="%s">%s <b>%d</b></button>' % (key, name, n))
    era_chips_html = '\n        '.join(era_chips)

    era_cards = '\n'.join(
        '      <div class="cj-era-card" data-jump="%s">'
        '<div class="cj-era-span">%s</div>'
        '<h3 class="cj-era-name">%s</h3>'
        '<p class="cj-era-desc">%s</p></div>' % (k, esc(span), esc(name), esc(desc))
        for k, name, span, desc in ERAS)

    mile_items = '\n'.join(
        '      <li class="cj-mile"><span class="cj-mile-year">%s</span>'
        '<div class="cj-mile-body"><strong>%s</strong><span>%s</span></div></li>'
        % (esc(y), esc(t), esc(d)) for y, t, d in MILESTONES)

    peak = max(v for _y, v, _l in ATTENDANCE)
    bars = '\n'.join(
        '      <div class="cj-bar-row"><span class="cj-bar-year">%d</span>'
        '<span class="cj-bar-track"><span class="cj-bar-fill" style="width:%.1f%%"></span></span>'
        '<span class="cj-bar-val">%s 万</span><span class="cj-bar-tip">%s</span></div>'
        % (y, v / peak * 100, ('%g' % v), esc(lab)) for y, v, lab in ATTENDANCE)

    hall_cards = '\n'.join(
        '      <div class="cj-hall-card" style="--hall:%s"><h3>%s</h3><div class="cj-tags">%s</div></div>'
        % (color, esc(name), chips_html(items, 'cj-tag cj-tag-hall'))
        for name, color, items in HALL)

    src_items = '\n'.join(
        '    <li><a href="%s" target="_blank" rel="noopener noreferrer">%s</a></li>' % (u, esc(n))
        for n, u in SOURCES)

    page_css = """
:root{--cj:#4f46e5;--cj-2:#7c3aed;--cj-soft:rgba(79,70,229,.12)}
[data-theme="light"]{--cj:#4338ca;--cj-2:#6d28d9;--cj-soft:rgba(67,56,202,.09)}
.cj-hero{position:relative;overflow:hidden;border-radius:16px;margin:16px 0 8px;padding:44px 28px 38px;text-align:center;background:linear-gradient(135deg,#1e1b4b 0%,#312e81 45%,#4c1d95 100%)}
.cj-hero::after{content:'';position:absolute;inset:0;background:radial-gradient(circle at 18% 22%,rgba(255,255,255,.16),transparent 46%),radial-gradient(circle at 82% 78%,rgba(124,58,237,.34),transparent 52%);pointer-events:none}
.cj-hero>*{position:relative;z-index:1}
.cj-hero .cj-kicker{display:inline-block;font-size:.74rem;font-weight:700;letter-spacing:2px;color:#c7d2fe;border:1px solid rgba(199,210,254,.45);border-radius:999px;padding:3px 14px;margin-bottom:14px}
.cj-hero h1{font-size:2.15rem;color:#fff;margin-bottom:12px;line-height:1.3}
.cj-hero p{max-width:660px;margin:0 auto;color:rgba(255,255,255,.82);font-size:.98rem;line-height:1.85}
.cj-kpi{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:18px 0 8px}
.cj-kpi-item{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:16px 10px;text-align:center}
.cj-kpi-num{display:block;font-size:1.6rem;font-weight:900;color:var(--cj);line-height:1.2}
.cj-kpi-label{display:block;font-size:.76rem;color:var(--text-secondary);margin-top:4px}
.cj-sec{margin:44px 0 0}
.cj-sec-title{display:flex;align-items:center;gap:10px;font-size:1.28rem;font-weight:800;margin-bottom:6px;padding-left:12px;border-left:4px solid var(--cj)}
.cj-sec-sub{font-size:.86rem;color:var(--text-muted);margin:0 0 18px 16px}
.cj-era-grid{display:grid;grid-template-columns:repeat(5,1fr);gap:12px}
.cj-era-card{background:var(--card);border:1px solid var(--border);border-top:3px solid var(--cj);border-radius:12px;padding:16px 14px;cursor:pointer;transition:transform .2s,box-shadow .2s,border-color .2s}
.cj-era-card:hover{transform:translateY(-3px);box-shadow:var(--shadow-md);border-color:var(--cj)}
.cj-era-span{font-size:.74rem;font-weight:700;color:var(--cj);letter-spacing:.5px}
.cj-era-name{font-size:1rem;margin:6px 0 8px}
.cj-era-desc{font-size:.8rem;color:var(--text-secondary);line-height:1.65}
.cj-filter{position:sticky;top:var(--nav-height);z-index:60;margin:0 0 20px;padding:12px 14px;background:color-mix(in srgb,var(--bg) 88%,transparent);backdrop-filter:blur(12px);-webkit-backdrop-filter:blur(12px);border:1px solid var(--border);border-radius:12px}
.cj-search-wrap{position:relative;margin-bottom:10px}
.cj-search{width:100%;padding:9px 34px 9px 34px;font-size:.9rem;color:var(--text);background:var(--bg-secondary);border:1px solid var(--border);border-radius:9px;font-family:inherit}
.cj-search:focus{outline:none;border-color:var(--cj);box-shadow:0 0 0 3px var(--cj-soft)}
.cj-search-ico{position:absolute;left:11px;top:50%;transform:translateY(-50%);color:var(--text-muted);font-size:.9rem;pointer-events:none}
.cj-search-clear{position:absolute;right:8px;top:50%;transform:translateY(-50%);background:none;border:none;color:var(--text-muted);cursor:pointer;font-size:1rem;padding:2px 6px;display:none}
.cj-chips{display:flex;flex-wrap:wrap;gap:7px}
.cj-chip{font-size:.8rem;padding:5px 13px;border-radius:999px;border:1px solid var(--border);background:var(--card);color:var(--text-secondary);cursor:pointer;font-family:inherit;transition:all .18s}
.cj-chip b{font-weight:700;opacity:.6;margin-left:2px;font-size:.74rem}
.cj-chip:hover{border-color:var(--cj);color:var(--cj)}
.cj-chip.active{background:var(--cj);border-color:var(--cj);color:#fff}
.cj-chip.active b{opacity:.85}
.cj-count-bar{display:flex;justify-content:space-between;align-items:center;font-size:.8rem;color:var(--text-muted);margin-bottom:14px}
.cj-reset{background:none;border:none;color:var(--cj);cursor:pointer;font-size:.8rem;font-family:inherit;text-decoration:underline}
/* 年代卡真实现场照片（仅当用户放入对应年份真图才显示） */
.cj-card-img-wrap{position:relative;margin:-20px -22px 14px;border-radius:14px 14px 0 0;overflow:hidden;aspect-ratio:320/200;background:var(--bg-secondary)}
.cj-card-img{display:block;width:100%;height:100%;object-fit:cover}
.cj-list{display:flex;flex-direction:column;gap:16px}
.cj-card{position:relative;background:var(--card);border:1px solid var(--border);border-radius:14px;padding:20px 22px;border-left:4px solid var(--cj);transition:box-shadow .2s,transform .2s}
.cj-card:hover{box-shadow:var(--shadow-md);transform:translateX(2px)}
.cj-card-gap{border-left-style:dashed;border-left-color:var(--text-muted);opacity:.86}
.cj-card-head{display:flex;align-items:center;gap:14px;flex-wrap:wrap;margin-bottom:12px}
.cj-card-no{flex:0 0 auto;font-size:.82rem;font-weight:800;color:#fff;background:linear-gradient(135deg,var(--cj),var(--cj-2));padding:5px 13px;border-radius:999px}
.cj-card-gap .cj-card-no{background:var(--text-muted)}
.cj-card-meta{display:flex;align-items:baseline;gap:10px}
.cj-card-year{font-size:1.5rem;font-weight:900;color:var(--text);line-height:1}
.cj-card-date{font-size:.82rem;color:var(--text-secondary)}
.cj-card-place{margin-left:auto;font-size:.82rem;color:var(--text-secondary);text-align:right}
.cj-venue{display:block;font-size:.74rem;color:var(--text-muted)}
.cj-theme{display:flex;align-items:baseline;gap:9px;flex-wrap:wrap;background:var(--cj-soft);border-radius:9px;padding:9px 13px;margin-bottom:12px}
.cj-theme-label{font-size:.72rem;font-weight:700;color:var(--cj);flex:0 0 auto}
.cj-theme-txt{font-size:1rem;font-weight:700;color:var(--text)}
.cj-theme-en{font-size:.78rem;color:var(--text-muted);font-style:italic}
.cj-theme-none{background:transparent;padding:0 0 4px}
.cj-theme-none .cj-theme-txt{font-weight:400;font-size:.86rem;color:var(--text-muted)}
/* 卡片折叠：详情默认收起，降低长内容压迫感 */
.cj-card-teaser{font-size:.78rem;color:var(--text-muted);margin:2px 0 12px;padding-left:12px;border-left:3px solid var(--cj-soft)}
.cj-card-toggle{display:inline-flex;align-items:center;gap:4px;margin:2px 0 6px;padding:5px 14px;font-size:.78rem;font-family:inherit;color:var(--cj);background:var(--cj-soft);border:1px solid transparent;border-radius:999px;cursor:pointer;transition:background .15s,border-color .15s}
.cj-card-toggle:hover{border-color:var(--cj)}
.cj-caret{display:inline-block;transition:transform .2s;font-size:.72rem;line-height:1}
.cj-card.open .cj-caret{transform:rotate(180deg)}
.cj-card-detail{display:none;margin-top:8px;animation:cjFade .2s ease}
.cj-card.open .cj-card-detail{display:block}
@keyframes cjFade{from{opacity:0;transform:translateY(-4px)}to{opacity:1;transform:none}}
.cj-count-actions{display:flex;gap:14px;align-items:center}
.cj-scale{list-style:none;display:flex;flex-wrap:wrap;gap:6px 8px;margin:0 0 12px}
.cj-scale li{font-size:.78rem;color:var(--text-secondary);background:var(--bg-secondary);border:1px solid var(--border);border-radius:7px;padding:3px 10px}
.cj-block{margin-top:11px}
.cj-block-label{display:inline-block;font-size:.72rem;font-weight:700;color:var(--text-muted);letter-spacing:.5px;margin-bottom:6px}
.cj-tags{display:flex;flex-wrap:wrap;gap:6px}
.cj-tag{font-size:.76rem;padding:3px 9px;border-radius:6px;line-height:1.6}
.cj-tag-game{background:rgba(79,70,229,.14);color:var(--cj)}
.cj-tag-brand{background:rgba(194,65,12,.13);color:#c2410c}
[data-theme="dark"] .cj-tag-brand{color:#fb923c}
.cj-tag-hall{background:color-mix(in srgb,var(--hall) 15%,transparent);color:var(--hall)}
[data-theme="dark"] .cj-tag-hall{background:color-mix(in srgb,var(--hall) 26%,transparent);color:#fff}
.cj-points{margin:0;padding-left:18px}
.cj-points li{font-size:.86rem;color:var(--text-secondary);line-height:1.8;margin-bottom:3px}
.cj-empty{display:none;text-align:center;padding:46px 20px;color:var(--text-muted);font-size:.9rem}
.cj-mile-list{list-style:none;margin:0;padding:0;position:relative}
.cj-mile-list::before{content:'';position:absolute;left:74px;top:6px;bottom:6px;width:2px;background:linear-gradient(var(--cj),var(--cj-2))}
.cj-mile{display:flex;gap:18px;align-items:flex-start;padding:9px 0;position:relative}
.cj-mile-year{flex:0 0 64px;text-align:right;font-size:.8rem;font-weight:800;color:var(--cj);padding-top:2px}
.cj-mile::after{content:'';position:absolute;left:69px;top:14px;width:12px;height:12px;border-radius:50%;background:var(--cj);border:2px solid var(--bg)}
.cj-mile-body{padding-left:16px}
.cj-mile-body strong{display:block;font-size:.94rem;margin-bottom:2px}
.cj-mile-body span{font-size:.83rem;color:var(--text-secondary);line-height:1.7}
.cj-chart{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:20px 18px}
.cj-bar-row{display:flex;align-items:center;gap:10px;margin-bottom:9px;font-size:.8rem}
.cj-bar-year{flex:0 0 40px;color:var(--text-muted);font-variant-numeric:tabular-nums}
.cj-bar-track{flex:1;height:16px;background:var(--bg-secondary);border-radius:8px;overflow:hidden}
.cj-bar-fill{display:block;height:100%;border-radius:8px;background:linear-gradient(90deg,var(--cj),var(--cj-2))}
.cj-bar-val{flex:0 0 54px;text-align:right;font-weight:700;color:var(--text);font-variant-numeric:tabular-nums}
.cj-bar-tip{flex:0 0 62px;color:var(--text-muted);font-size:.74rem}
.cj-hall-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:14px}
.cj-hall-card{background:var(--card);border:1px solid var(--border);border-top:3px solid var(--hall);border-radius:12px;padding:16px 16px 18px}
.cj-hall-card h3{font-size:.95rem;color:var(--hall);margin-bottom:10px}
[data-theme="dark"] .cj-hall-card h3{color:#fff}
.cj-note{margin:36px 0 8px;padding:16px 18px;background:var(--bg-secondary);border:1px solid var(--border);border-radius:12px;font-size:.82rem;color:var(--text-secondary);line-height:1.85}
.cj-note h3{font-size:.9rem;margin-bottom:8px;color:var(--text)}
.cj-note ul{margin:0;padding-left:18px}
@media(max-width:992px){.cj-era-grid{grid-template-columns:repeat(2,1fr)}.cj-kpi{grid-template-columns:repeat(2,1fr)}.cj-hall-grid{grid-template-columns:1fr}}
@media(max-width:576px){.cj-hero{padding:32px 18px 28px}.cj-hero h1{font-size:1.55rem}.cj-era-grid{grid-template-columns:1fr}
.cj-card{padding:16px 15px}.cj-card-place{margin-left:0;width:100%;text-align:left}.cj-card-year{font-size:1.25rem}
.cj-mile-list::before{left:52px}.cj-mile-year{flex:0 0 44px}.cj-mile::after{left:47px}
.cj-bar-tip{display:none}.cj-card-img-wrap{margin:-16px -15px 12px;border-radius:14px 14px 0 0;aspect-ratio:320/200}}
"""

    page_js = """
(function(){
  var list=document.getElementById('cjList');
  if(!list)return;
  var cards=[].slice.call(list.querySelectorAll('.cj-card'));
  var chips=[].slice.call(document.querySelectorAll('.cj-chip'));
  var input=document.getElementById('cjSearch');
  var clear=document.getElementById('cjClear');
  var shown=document.getElementById('cjShown');
  var empty=document.getElementById('cjEmpty');
  var reset=document.getElementById('cjReset');
  var ALIAS={'cj':'chinajoy','中国国际数码互动娱乐展览会':'chinajoy','游戏展':'chinajoy',
             'ps':'playstation','索尼':'playstation 索尼','ai':'ai 人工智能',
             '魔兽':'魔兽世界','wow':'魔兽世界','暴雪':'暴雪 blizzard'};
  var state={era:'all',q:''};

  cards.forEach(function(c){ c._q=(c.getAttribute('data-q')||'')+' '+(c.getAttribute('data-year')||''); });

  function render(){
    var n=0;
    cards.forEach(function(c){
      var okEra=(state.era==='all')||c.getAttribute('data-era')===state.era;
      var okQ=!state.q||c._q.indexOf(state.q)>-1;
      var ok=okEra&&okQ;
      c.style.display=ok?'':'none';
      if(ok)n++;
    });
    shown.textContent=n;
    empty.style.display=n?'none':'block';
    clear.style.display=state.q?'block':'none';
  }

  chips.forEach(function(ch){
    ch.addEventListener('click',function(){
      chips.forEach(function(x){x.classList.remove('active');});
      ch.classList.add('active');
      state.era=ch.getAttribute('data-era');
      render();
    });
  });

  input.addEventListener('input',function(){
    var v=input.value.trim().toLowerCase();
    if(ALIAS[v])v=ALIAS[v];
    state.q=v; render();
  });
  clear.addEventListener('click',function(){ input.value=''; state.q=''; render(); input.focus(); });
  reset.addEventListener('click',function(){
    input.value=''; state.q=''; state.era='all';
    chips.forEach(function(x){x.classList.toggle('active',x.getAttribute('data-era')==='all');});
    render();
  });

  // 卡片折叠 / 展开全部（默认收起详情，降低长内容压迫感）
  var toggles=[].slice.call(list.querySelectorAll('.cj-card-toggle'));
  function setToggleTxt(btn,open){ var t=btn.querySelector('.cj-toggle-txt'); if(t)t.textContent=open?'收起详情':'展开详情'; }
  toggles.forEach(function(btn){
    btn.addEventListener('click',function(){
      var card=btn.closest('.cj-card');
      var open=card.classList.toggle('open');
      btn.setAttribute('aria-expanded',open?'true':'false');
      setToggleTxt(btn,open);
    });
  });
  var expandBtn=document.getElementById('cjExpand');
  if(expandBtn){
    expandBtn.addEventListener('click',function(){
      var open=expandBtn.textContent.indexOf('收起')===-1;
      cards.forEach(function(c){ c.classList.toggle('open',open); });
      toggles.forEach(function(b){ b.setAttribute('aria-expanded',open?'true':'false'); setToggleTxt(b,open); });
      expandBtn.textContent=open?'收起全部':'展开全部';
    });
  }

  [].slice.call(document.querySelectorAll('.cj-era-card')).forEach(function(card){
    card.addEventListener('click',function(){
      var era=card.getAttribute('data-jump');
      var target=chips.filter(function(x){return x.getAttribute('data-era')===era;})[0];
      if(target){ target.click(); }
      var anchor=document.getElementById('cjArchive');
      if(anchor)anchor.scrollIntoView({behavior:'smooth',block:'start'});
    });
  });

  render();
})();
"""

    html = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<script>(function(){try{var t=localStorage.getItem('theme');if(t==='light'||t==='dark'){document.documentElement.setAttribute('data-theme',t)}else{var h=new Date().getHours();document.documentElement.setAttribute('data-theme',(h>=6&&h<18)?'light':'dark')}}catch(e){}})();</script>
<!-- 预加载关键资源 -->
<link rel="preload" href="js/app.js" as="script">
<link rel="preconnect" href="//hm.baidu.com">
<link rel="dns-prefetch" href="//hm.baidu.com">
<link rel="dns-prefetch" href="//busuanzi.ibruce.info">
__CRITICAL__
<link rel="preload" href="css/style.css?v=7080" as="style" onload="this.onload=null;this.rel='stylesheet'">
<noscript><link rel="stylesheet" href="css/style.css?v=7080"></noscript>
<title>ChinaJoy 成长史 - 龙兄知识库</title><meta name="description" content="ChinaJoy 成长史：从 2004 年首届到 2026 年第 23 届的完整档案，逐届梳理展会主题、规模数据、参展品牌与代表游戏，以及二十余年的行业变迁。">
<meta name="keywords" content="ChinaJoy,中国国际数码互动娱乐展览会,历届ChinaJoy,ChinaJoy主题,ChinaJoy参展游戏,游戏展,上海新国际博览中心">
<style>__PAGECSS__</style>
<script>
var _hmt = _hmt || [];
(function() {
  var hm = document.createElement("script");
  hm.src = "https://hm.baidu.com/hm.js?04913e92799dc86649938ea8f5eb4b78";
  var s = document.getElementsByTagName("script")[0];
  s.parentNode.insertBefore(hm, s);
})();
</script>
<script async src="//busuanzi.ibruce.info/busuanzi/2.3/busuanzi.pure.mini.js"></script>
<meta property="og:site_name" content="龙兄知识库">
<link rel="canonical" href="https://longxiong.vip/chinajoy.html">
<link rel="icon" type="image/svg+xml" href="https://longxiong.vip/favicon.svg">
<meta property="og:title" content="ChinaJoy 成长史 - 龙兄知识库">
<meta property="og:description" content="从 2004 年首届到 2026 年第 23 届，ChinaJoy 逐届档案：主题、规模、参展品牌与代表游戏。">
<meta property="og:type" content="article">
<meta property="og:url" content="https://longxiong.vip/chinajoy.html">
<meta property="og:image" content="https://longxiong.vip/img/og-image.png">
<meta property="og:locale" content="zh_CN">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="ChinaJoy 成长史 - 龙兄知识库">
<meta name="twitter:description" content="从 2004 年首届到 2026 年第 23 届，ChinaJoy 逐届档案：主题、规模、参展品牌与代表游戏。">
<meta name="twitter:image" content="https://longxiong.vip/img/og-image.png">
</head>
<body>

__NAVBAR__

  <main id="main-content" role="main"><div class="container">
  <div class="breadcrumb" id="breadcrumb">
    <a href="index.html">首页</a>
    <span class="sep">›</span>
    <span class="current">ChinaJoy 成长史</span>
  </div>

  <!-- ===== Hero ===== -->
  <div class="cj-hero">
    <span class="cj-kicker">CHINA DIGITAL ENTERTAINMENT EXPO</span>
    <h1>ChinaJoy 成长史</h1>
    <p>从 2004 年北京展览馆的第一届，到 2026 年上海新国际博览中心的第 __TOTAL__ 届——
    一份逐届梳理的完整档案：每一年的主题、规模、参展品牌与代表游戏，串起中国数字娱乐产业二十余年的变迁。</p>
  </div>

  <div class="cj-kpi">
    <div class="cj-kpi-item"><span class="cj-kpi-num">__TOTAL__</span><span class="cj-kpi-label">已举办届数</span></div>
    <div class="cj-kpi-item"><span class="cj-kpi-num">__FIRST__</span><span class="cj-kpi-label">首届年份</span></div>
    <div class="cj-kpi-item"><span class="cj-kpi-num">41.03<span style="font-size:.9rem">万</span></span><span class="cj-kpi-label">单届观众峰值</span></div>
    <div class="cj-kpi-item"><span class="cj-kpi-num">17<span style="font-size:.9rem">万㎡</span></span><span class="cj-kpi-label">历届最大展出面积</span></div>
  </div>

  <!-- ===== 自动更新动态 ===== -->
  <div class="home-collapsible" id="hc-auto-news" style="display:none;margin-top:32px;">
    <div class="home-collapsible-header" onclick="toggleHomeSection(this)">
      <div class="hc-left"><span class="hc-icon">🤖</span><span class="hc-title">每日自动更新</span><span class="hc-live"><span class="dot"></span>实时</span><span class="hc-count" id="autoNewsCount"></span></div>
      <span class="hc-arrow">▼</span>
    </div>
    <div class="home-collapsible-body" id="autoNewsBody"></div>
  </div>

  <!-- ===== 五个阶段 ===== -->
  <section class="cj-sec">
    <h2 class="cj-sec-title">五个阶段，一部产业断代史</h2>
    <p class="cj-sec-sub">ChinaJoy 改口号的历史，差不多就是中国游戏产业换重心的历史。点击任一阶段可直接筛选下方档案。</p>
    <div class="cj-era-grid">
__ERACARDS__
    </div>
  </section>

  <!-- ===== 历届档案 ===== -->
  <section class="cj-sec" id="cjArchive">
    <h2 class="cj-sec-title">历届完整档案</h2>
    <p class="cj-sec-sub">按年份倒序排列，支持关键词搜索（游戏名、厂商、主题、年份都能搜）与阶段筛选。</p>

    <div class="cj-filter">
      <div class="cj-search-wrap">
        <span class="cj-search-ico">🔍</span>
        <input type="search" class="cj-search" id="cjSearch" placeholder="搜索届次、主题、游戏或厂商，例如：魔兽世界 / 暴雪 / 泛娱乐 / 2016" aria-label="搜索历届 ChinaJoy">
        <button class="cj-search-clear" id="cjClear" aria-label="清空搜索">✕</button>
      </div>
      <div class="cj-chips">
        __ERACHIPS__
      </div>
    </div>

    <div class="cj-count-bar">
      <span>共 <strong id="cjShown">__CARDCOUNT__</strong> 条记录</span>
      <span class="cj-count-actions">
        <button class="cj-reset" id="cjExpand">展开全部</button>
        <button class="cj-reset" id="cjReset">重置筛选</button>
      </span>
    </div>

    <div class="cj-list" id="cjList">
__CARDS__
    </div>
    <div class="cj-empty" id="cjEmpty">没有匹配的记录，换个关键词试试～</div>
  </section>

  <!-- ===== 观众规模 ===== -->
  <section class="cj-sec">
    <h2 class="cj-sec-title">观众规模变化</h2>
    <p class="cj-sec-sub">单位：万人次。仅列出有公开数据的年份，2022 年停办。</p>
    <div class="cj-chart">
__BARS__
    </div>
  </section>

  <!-- ===== 品牌里程碑 ===== -->
  <section class="cj-sec">
    <h2 class="cj-sec-title">展会体系里程碑</h2>
    <p class="cj-sec-sub">从单一游戏展，到「游戏 + 动漫 + 硬件 + 潮玩」的综合数字娱乐平台。</p>
    <ul class="cj-mile-list">
__MILES__
    </ul>
  </section>

  <!-- ===== 名人堂 ===== -->
  <section class="cj-sec">
    <h2 class="cj-sec-title">参展品牌名人堂</h2>
    <p class="cj-sec-sub">二十余年间在 ChinaJoy 留下过展台的部分代表性企业。</p>
    <div class="cj-hall-grid">
__HALL__
    </div>
  </section>

  <div class="cj-note">
    <h3>关于本页</h3>
    <ul>
      <li>数据来源于 ChinaJoy 官方公告与公开报道，早期届次的观众数字在不同信源间存在口径差异，本页取较常被引用的一组。</li>
      <li>本页随每届展会持续更新，「每日自动更新」区块会跟进展会与行业的最新动态。</li>
      <li>每届卡片顶部可放一张该届的<b>真实现场照片</b>：把照片放到 <code>static/img/chinajoy/&lt;年份&gt;.jpg</code>（或 .png/.webp），重新构建后会在对应卡片顶部自动显示。本站<b>绝不使用 AI 生成图</b>，照片必须是真实拍摄的现场图。</li>
      <li>本页现有现场照片均来自 <b>Wikimedia Commons</b>（依据 CC BY-SA / CC BY 等自由许可使用），按年份一一对应；原作者与原始文件名见各图 alt 属性。未找到对应年份真图的届次暂以纯文字展示，绝不张冠李戴。</li>
      <li>参考资料：</li>
    </ul>
    <ul>
__SOURCES__
    </ul>
    <p style="margin-top:10px">最后更新时间：<span id="lastNewsUpdate">__LASTUPDATE__</span></p>
  </div>

</div>
</main>__FOOTER__

<script src="js/search.js"></script>
<script defer src="js/app.js"></script>
<script src="js/share.js"></script>

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@graph": [
    {
      "@type": "WebSite",
      "name": "龙兄知识库",
      "url": "https://longxiong.vip",
      "description": "AI · 文玩 · 游戏 · 养生 · 新能源 — 做一个有温度的知识站点"
    },
    {
      "@type": "Article",
      "author": { "@type": "Person", "name": "龙兄" },
      "headline": "ChinaJoy 成长史 - 龙兄知识库",
      "url": "https://longxiong.vip/chinajoy.html",
      "description": "从 2004 年首届到 2026 年第 23 届，ChinaJoy 逐届档案：主题、规模、参展品牌与代表游戏。"
    }
  ]
}
</script>

<script>
if (typeof toggleHomeSection === 'undefined') {
  function toggleHomeSection(el){ var wrap=el.parentElement; wrap.classList.toggle("open"); }
}
</script>
<script>__PAGEJS__</script>
<script src="js/auto_news_loader.js"></script>
</body>
</html>
"""

    html = (html
            .replace('__CRITICAL__', critical)
            .replace('__NAVBAR__', navbar)
            .replace('__FOOTER__', footer)
            .replace('__PAGECSS__', page_css.strip())
            .replace('__PAGEJS__', page_js.strip())
            .replace('__ERACARDS__', era_cards)
            .replace('__ERACHIPS__', era_chips_html)
            .replace('__CARDS__', cards)
            .replace('__CARDCOUNT__', str(len(EDITIONS)))
            .replace('__BARS__', bars)
            .replace('__MILES__', mile_items)
            .replace('__HALL__', hall_cards)
            .replace('__SOURCES__', src_items)
            .replace('__TOTAL__', str(total_editions))
            .replace('__FIRST__', str(first_year))
            .replace('__LASTUPDATE__', LAST_UPDATE))

    with open(OUT, 'w', encoding='utf-8') as f:
        f.write(html)

    print('生成完成: %s' % OUT)
    print('  届次记录 %d 条（含停办占位），已举办 %d 届' % (len(EDITIONS), total_editions))
    print('  文件大小 %.1f KB' % (len(html.encode('utf-8')) / 1024))


if __name__ == '__main__':
    main()
