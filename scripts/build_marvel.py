#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成 static/marvel.html —— 漫威宇宙（龙兄观影手账）

版权安全说明（重要）：
  本页刻意不托管任何漫威官方剧照 / 海报 / 角色宣传图，全部以 emoji + 原创文字呈现。
  这是上一轮因版权风险下架后，按用户「漫威影迷」需求重建的合规版本。
  影片年份、阶段划分均为个人观影整理，官方制作计划可能调整，以官方最终上映为准。

可持续更新方式：
  1. 在下方 RELEASE_ORDER / STORY_ORDER / PHASES / HEROES / RATINGS / TRIVIA 中增删条目
  2. 运行：python3 scripts/build_marvel.py
  3. hugo --gc 构建后提交即可

页面结构与站内其它板块页（herbs/console/chinajoy）完全一致：
  critical CSS -> navbar(内联) -> 面包屑 -> hero -> 观影顺序 -> 阶段时间线
  -> 英雄档案卡 -> 私人评分 -> 冷知识 -> 关于本页 -> footer -> 脚本
"""
import os
import html as htmllib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'static', 'marvel.html')
DONOR = os.path.join(ROOT, 'static', 'herbs.html')

LAST_UPDATE = '2026-08-10'

# ---------------------------------------------------------------- 观影顺序：上映顺序
# (phase, 片名, 年份)
RELEASE_ORDER = [
    (1, '钢铁侠', 2008), (1, '无敌浩克', 2008), (1, '钢铁侠 2', 2010),
    (1, '雷神', 2011), (1, '美国队长', 2011), (1, '复仇者联盟', 2012),
    (2, '钢铁侠 3', 2013), (2, '雷神 2：黑暗世界', 2013),
    (2, '美国队长 2：冬日战士', 2014), (2, '银河护卫队', 2014),
    (2, '复仇者联盟 2：奥创纪元', 2015), (2, '蚁人', 2015),
    (3, '美国队长 3：内战', 2016), (3, '奇异博士', 2016),
    (3, '银河护卫队 2', 2017), (3, '蜘蛛侠：英雄归来', 2017),
    (3, '雷神 3：诸神黄昏', 2017), (3, '黑豹', 2018),
    (3, '复仇者联盟 3：无限战争', 2018), (3, '蚁人 2：黄蜂女现身', 2018),
    (3, '惊奇队长', 2019), (3, '复仇者联盟 4：终局之战', 2019),
    (3, '蜘蛛侠：英雄远征', 2019),
    (4, '黑寡妇', 2021), (4, '尚气与十环传奇', 2021), (4, '永恒族', 2021),
    (4, '蜘蛛侠：英雄无归', 2021), (4, '奇异博士 2：疯狂多元宇宙', 2022),
    (4, '雷神 4：爱与雷霆', 2022), (4, '黑豹 2：瓦坎达万岁', 2022),
    (4, '蚁人 3：量子狂潮', 2023),
    (5, '银河护卫队 3', 2023), (5, '惊奇队长 2', 2023),
    (5, '秘密入侵', 2023), (5, '洛基（第二季）', 2023),
    (5, '死侍与金刚狼', 2024), (5, '回声', 2024),
    (6, '神奇四侠：第一步', 2025),
    (6, '蜘蛛侠：崭新之日', 2026),
]

# ---------------------------------------------------------------- 观影顺序：故事时间线
# 一种常见的「按宇宙内时间线」观看顺序（粉丝向整理，非官方）
STORY_ORDER = [
    (1, '美国队长', 2011),   # 片头即 1940 年代
    (1, '钢铁侠', 2008),
    (1, '无敌浩克', 2008),
    (1, '钢铁侠 2', 2010),
    (1, '雷神', 2011),
    (1, '复仇者联盟', 2012),
    (2, '钢铁侠 3', 2013),
    (2, '雷神 2：黑暗世界', 2013),
    (2, '美国队长 2：冬日战士', 2014),
    (2, '银河护卫队', 2014),
    (2, '复仇者联盟 2：奥创纪元', 2015),
    (2, '蚁人', 2015),
    (3, '美国队长 3：内战', 2016),
    (3, '奇异博士', 2016),
    (3, '银河护卫队 2', 2017),
    (3, '蜘蛛侠：英雄归来', 2017),
    (3, '雷神 3：诸神黄昏', 2017),
    (3, '黑豹', 2018),
    (3, '复仇者联盟 3：无限战争', 2018),
    (3, '蚁人 2：黄蜂女现身', 2018),
    (3, '惊奇队长', 2019),
    (3, '复仇者联盟 4：终局之战', 2019),
    (3, '蜘蛛侠：英雄远征', 2019),
    (4, '黑寡妇', 2021),
    (4, '旺达幻视', 2021),
    (4, '尚气与十环传奇', 2021),
    (4, '永恒族', 2021),
    (4, '蜘蛛侠：英雄无归', 2021),
    (4, '奇异博士 2：疯狂多元宇宙', 2022),
    (4, '雷神 4：爱与雷霆', 2022),
    (4, '黑豹 2：瓦坎达万岁', 2022),
    (4, '蚁人 3：量子狂潮', 2023),
    (4, '洛基（全集）', 2021),
    (5, '银河护卫队 3', 2023),
    (5, '秘密入侵', 2023),
    (5, '死侍与金刚狼', 2024),
    (6, '神奇四侠：第一步', 2025),
    (6, '蜘蛛侠：崭新之日', 2026),
]

# ---------------------------------------------------------------- 阶段时间线
# (阶段号, 名称, 年份区间, 一句话, emoji)
PHASES = [
    ('1', '无限传奇 · 起步', '2008–2012', '从钢铁侠单枪匹马，到六位初代复仇者集结', '🚀'),
    ('2', '无限传奇 · 铺垫', '2013–2015', '无限宝石逐一登场，危机在笑声里暗涌', '💎'),
    ('3', '无限传奇 · 终章', '2016–2019', '无限战争到终局之战，十年布局一朝收束', '🏆'),
    ('4', '多元宇宙 · 开启', '2021–2023', '后终局时代，Disney+ 剧集把边界推向多元宇宙', '🌌'),
    ('5', '多元宇宙 · 推进', '2023–2024', '新老交替，康与秘密入侵搅动时间线', '⏳'),
    ('6', '多元宇宙 · 收官', '2025–', '秘密战争等规划中的大事件，传奇阶段落幕', '🌠'),
]

# ---------------------------------------------------------------- 英雄档案卡
# emoji, name, real(真名), debut(首登场), actor(演员), note(一句话点评)
HEROES = [
    dict(emoji='🤖', name='钢铁侠', real='托尼·斯塔克', debut='《钢铁侠》(2008)', actor='小罗伯特·唐尼',
         note='把嘴炮、天才与赎罪玩成英雄主义的灵魂人物，MCU 的原点。'),
    dict(emoji='🛡️', name='美国队长', real='史蒂夫·罗杰斯', debut='《美国队长》(2011)', actor='克里斯·埃文斯',
         note='老派正义感的化身，复仇者联盟的精神锚点。'),
    dict(emoji='⚡', name='雷神', real='索尔·奥丁森', debut='《雷神》(2011)', actor='克里斯·海姆斯沃斯',
         note='从傲慢王子到能硬扛灭霸的锤哥，喜剧天赋拉满。'),
    dict(emoji='🟢', name='浩克', real='布鲁斯·班纳', debut='《无敌浩克》(2008)', actor='爱德华·诺顿 / 马克·鲁法洛',
         note='科学家的愤怒，越大越孤单的绿巨人。'),
    dict(emoji='🕷️', name='蜘蛛侠', real='彼得·帕克', debut='《蜘蛛侠：英雄归来》(2017)', actor='汤姆·赫兰德',
         note='最年轻的复仇者，话痨担当，邻家男孩的英雄梦。'),
    dict(emoji='🔮', name='奇异博士', real='史蒂芬·斯特兰奇', debut='《奇异博士》(2016)', actor='本尼迪克特·康伯巴奇',
         note='用魔法兜底多元宇宙的神经外科医生，时间线的守门人。'),
    dict(emoji='🐾', name='黑豹', real='特查拉', debut='《黑豹》(2018)', actor='查德维克·博斯曼',
         note='瓦坎达的科技与尊严，影史文化意义远超一部超级英雄片。'),
    dict(emoji='✨', name='惊奇队长', real='卡罗尔·丹弗斯', debut='《惊奇队长》(2019)', actor='布丽·拉尔森',
         note='剧场版里战力天花板的存在，越宇宙如散步。'),
    dict(emoji='🌌', name='星爵', real='彼得·奎尔', debut='《银河护卫队》(2014)', actor='克里斯·帕拉特',
         note='靠一张混音带和贫嘴，把一队怪咖团结成家人。'),
    dict(emoji='🐜', name='蚁人', real='斯科特·朗', debut='《蚁人》(2015)', actor='保罗·路德',
         note='把量子物理拍成家庭喜剧，小人物的大冒险。'),
    dict(emoji='🗡️', name='洛基', real='洛基·劳菲森', villain=True, debut='《雷神》(2011)', actor='汤姆·希德勒斯顿',
         note='反派写出顶流，时间变异管理局的常客，亦正亦邪的 trickster。'),
    dict(emoji='🔥', name='死侍', real='韦德·威尔逊', debut='《死侍与金刚狼》(2024)', actor='瑞安·雷诺兹',
         note='打破第四面墙的嘴炮雇佣兵，R 级狂欢的代言人。'),
    dict(emoji='🐺', name='金刚狼', real='罗根', debut='《X 战警》系列 / 《死侍与金刚狼》', actor='休·杰克曼',
         note='自愈因子加骨爪，几代人的漫画情怀。'),
    dict(emoji='🕸️', name='黑寡妇', real='娜塔莎·罗曼诺夫', debut='《钢铁侠 2》(2010 客串)', actor='斯嘉丽·约翰逊',
         note='没有超能力的英雄，牺牲却最动人。'),
]

# ---------------------------------------------------------------- 私人评分
# (片名, 星级 1-5, 点评)
RATINGS = [
    ('复仇者联盟 4：终局之战', 5, '十年布局的句号，情怀拉满，影院里哭成一片。'),
    ('复仇者联盟 3：无限战争', 5, '灭霸的代价与英雄的溃败，反派赢一次的震撼。'),
    ('美国队长 2：冬日战士', 5, '谍战味最浓的一部，动作戏教科书级别。'),
    ('银河护卫队', 4, '最会整活的团队，混音带一响回忆杀。'),
    ('黑豹', 4, '文化符号大于电影本身，瓦坎达美学惊艳。'),
    ('蜘蛛侠：英雄无归', 4, '三代同框的眼泪，粉丝狂喜的一课。'),
    ('死侍与金刚狼', 4, 'R 级狂欢，打破次元壁的粉丝盛宴。'),
    ('钢铁侠', 4, '一切的起点，唐尼一人撑起一个宇宙。'),
]

# ---------------------------------------------------------------- 正在热映 & 未来计划
# (status, 片名, 日期, 一句话) —— 数据来自 SDCC 2026 漫威专场已公布片单
UPCOMING = [
    ('now', '蜘蛛侠：崭新之日', '2026-07-31',
     'MCU 第六阶段第 38 部，汤姆·赫兰德回归，「邻里英雄」基调重启，马克·鲁法洛饰绿巨人客串'),
    ('soon', '复仇者联盟4：终局之战（重映）', '2026-09-25',
     '院线重映并新增独家片段，专门铺垫《复联5》剧情（史蒂夫归还宝石、托尼经典台词）'),
    ('soon', '复仇者联盟5：毁灭之日', '2026-12-18',
     '罗素兄弟回归，小罗伯特·唐尼饰毁灭博士，集结复仇者 / 神奇四侠 / X战警 三大阵营'),
    ('soon', '蜘蛛侠：超越宇宙', '2027-06-18',
     '索尼动画（蜘蛛侠宇宙），平行宇宙三部曲终章，非 MCU 真人主线'),
    ('soon', '复仇者联盟6：秘密战争', '2027-12-17',
     '多元宇宙传奇收官之作，梳理纷乱时间线、开启英雄迭代新时代，与毁灭之日背靠背拍摄'),
    ('soon', '恶灵骑士', '2028（待定档）',
     '瑞恩·高斯林主演、肖恩·利维导演，划入 MCU 第七阶段，补齐暗黑超自然赛道'),
    ('soon', '黑豹3', '2028-12-15',
     '瑞恩·库格勒回归，大卫·荣松饰新一代黑豹特查拉二世，大画幅胶片打造史诗质感'),
    ('soon', 'X战警（重启版）', '开发中·待 D23 揭晓',
     '已官宣开发并纳入第七阶段片单，具体阵容与档期留待 2026 年 8 月迪士尼 D23 博览会公布'),
]

# ---------------------------------------------------------------- 冷知识
TRIVIA = [
    '钢铁侠是 MCU 第一部电影，当年没人料到它会长成一个电影宇宙。',
    '宇宙魔方（空间宝石）最早在《美国队长：复仇者先锋》(2011) 正片登场，并在《雷神》片尾彩蛋埋下复联伏笔。',
    '美国队长的振金盾牌，是漫画里最经典的道具之一。',
    '洛基是少数靠个人剧集真正出圈的反派角色。',
    '《复仇者联盟 4》大量使用 IMAX 胶片拍摄，画幅切换本身就是叙事。',
    'Disney+ 的剧集把「电影宇宙」扩展成了「影视宇宙」，观看顺序从此多了维度。',
]

SOURCES = [
    ('Marvel 官方网站', 'https://www.marvel.com/'),
    ('漫威电影宇宙中文维基（粉丝整理）', 'https://marvelcinematicuniverse.fandom.com/wiki/'),
]


# ================================================================= 工具函数
def esc(s):
    return htmllib.escape(str(s), quote=True)


def extract(donor_html, start_mark, end_mark, inclusive=True):
    """从供体页面里按标记截取一段（复用导航 / 页脚等公共结构）"""
    i = donor_html.index(start_mark)
    j = donor_html.index(end_mark, i)
    return donor_html[i:j + len(end_mark)] if inclusive else donor_html[i + len(start_mark):j]


# ================================================================= 观影顺序
def order_item(t, y, p):
    return ('      <li><span class="mv-order-t">%s</span>'
            '<span class="mv-order-p">Phase %d</span>'
            '<span class="mv-order-y">%d</span></li>' % (esc(t), p, y))


def build_orders():
    """按阶段分组渲染：每个阶段一个 <details>，默认仅展开 Phase 1，其余收起。
    大幅缩短首屏滚动量，避免「一路下拉」。"""
    pnames = {no: name for no, name, span, desc, em in PHASES}

    def group(phase_items):
        p = phase_items[0][0]
        items = '\n'.join(order_item(t, y, p) for p, t, y in phase_items)
        head = ('<summary><span class="mv-pg-no">Phase %d</span> %s'
                '<span class="mv-pg-count">%d 部</span></summary>'
                % (p, esc(pnames.get(str(p), '')), len(phase_items)))
        open_attr = ' open' if p == 1 else ''
        return ('      <details class="mv-phase-group"%s>%s\n'
                '      <ol class="mv-order">\n%s\n      </ol>\n      </details>'
                % (open_attr, head, items))

    rel, sto = {}, {}
    for p, t, y in RELEASE_ORDER:
        rel.setdefault(p, []).append((p, t, y))
    for p, t, y in STORY_ORDER:
        sto.setdefault(p, []).append((p, t, y))
    release = '\n'.join(group(rel[p]) for p in sorted(rel))
    story = '\n'.join(group(sto[p]) for p in sorted(sto))
    return release, story


# ================================================================= 阶段时间线
def build_phases():
    return '\n'.join(
        '      <article class="mv-phase-card" data-phase="%s">'
        '<div class="mv-phase-emoji">%s</div>'
        '<div class="mv-phase-no">Phase %s</div>'
        '<h3 class="mv-phase-name">%s</h3>'
        '<div class="mv-phase-span">%s</div>'
        '<p class="mv-phase-desc">%s</p></article>'
        % (esc(no), esc(em), esc(no), esc(name), esc(span), esc(desc))
        for no, name, span, desc, em in PHASES)


# ================================================================= 英雄档案卡
def build_heroes():
    out = []
    for h in HEROES:
        villain = ' villain-card' if h.get('villain') else ''
        out.append('''      <article class="hero-card%(v)s">
        <div class="hero-avatar">%(e)s</div>
        <h3>%(n)s</h3>
        <div class="hero-info">
          <div class="hero-row"><span class="label">真名</span> %(real)s</div>
          <div class="hero-row"><span class="label">首登场</span> %(d)s</div>
          <div class="hero-row"><span class="label">演员</span> %(a)s</div>
          <div class="hero-row"><span class="label">点评</span> %(note)s</div>
        </div>
      </article>''' % dict(v=villain, e=esc(h['emoji']), n=esc(h['name']), real=esc(h['real']),
                           d=esc(h['debut']), a=esc(h['actor']), note=esc(h['note'])))
    return '\n'.join(out)


# ================================================================= 私人评分
def stars(n):
    return '★' * n + '☆' * (5 - n)

def build_ratings():
    return '\n'.join(
        '      <div class="mv-rating-item">'
        '<div class="mv-rating-head"><span class="mv-rating-name">%s</span>'
        '<span class="mv-stars" aria-label="%d 星">%s</span></div>'
        '<p class="mv-rating-note">%s</p></div>'
        % (esc(t), n, stars(n), esc(c))
        for t, n, c in RATINGS)


# ================================================================= 冷知识
def build_trivia():
    return '\n'.join('      <li>%s</li>' % esc(x) for x in TRIVIA)


def build_soon():
    out = []
    for status, t, d, note in UPCOMING:
        badge = '正在热映' if status == 'now' else '待上映'
        cls = 'mv-soon-now' if status == 'now' else 'mv-soon-soon'
        out.append(
            '      <div class="mv-soon-item %s">'
            '<div class="mv-soon-head"><span class="mv-soon-name">%s</span>'
            '<span class="mv-soon-badge">%s</span></div>'
            '<div class="mv-soon-date">%s</div>'
            '<p class="mv-soon-note">%s</p></div>'
            % (cls, esc(t), badge, esc(d), esc(note)))
    return '\n'.join(out)


def build_sources():
    return '\n'.join(
        '    <li><a href="%s" target="_blank" rel="noopener noreferrer">%s</a></li>' % (u, esc(n))
        for n, u in SOURCES)


# ================================================================= 页面组装
def main():
    with open(DONOR, encoding='utf-8') as f:
        donor = f.read()

    critical = extract(donor, '<style id="critical-css">', '</style>')
    navbar = extract(donor, '<nav class="navbar"', '</nav>')
    footer = extract(donor, '<footer role="contentinfo">', '</footer>')

    # 导航高亮切换到漫威（herbs 供体上是中药材高亮）
    navbar = navbar.replace('<a href="herbs.html" class="active">中药材</a>',
                            '<a href="herbs.html">中药材</a>')
    navbar = navbar.replace('<a href="marvel.html">漫威宇宙</a>',
                            '<a href="marvel.html" class="active">漫威宇宙</a>')
    if 'marvel.html' not in navbar:
        raise SystemExit('供体导航缺少漫威链接，请先运行导航注入脚本（sync_navbar.py）')

    release_html, story_html = build_orders()
    n_films = len(RELEASE_ORDER)
    n_phases = len(PHASES)
    n_heroes = len(HEROES)
    n_ratings = len(RATINGS)

    page_css = """
:root{--mv:#e23636;--mv-2:#b3122b;--mv-soft:rgba(226,54,54,.12)}
[data-theme="light"]{--mv:#c1121f;--mv-2:#9b0d1c;--mv-soft:rgba(193,18,31,.09)}
.mv-hero{position:relative;overflow:hidden;border-radius:16px;margin:16px 0 8px;padding:44px 28px 38px;text-align:center;background:linear-gradient(135deg,#1a0608 0%,#3a0d12 45%,#7a1220 100%)}
.mv-hero::after{content:'';position:absolute;inset:0;background:radial-gradient(circle at 20% 20%,rgba(255,255,255,.14),transparent 46%),radial-gradient(circle at 80% 80%,rgba(226,54,54,.34),transparent 52%);pointer-events:none}
.mv-hero>*{position:relative;z-index:1}
.mv-hero .mv-kicker{display:inline-block;font-size:.74rem;font-weight:700;letter-spacing:2px;color:#ffd2d2;border:1px solid rgba(255,210,210,.45);border-radius:999px;padding:3px 14px;margin-bottom:14px}
.mv-hero h1{font-size:2.15rem;color:#fff;margin-bottom:12px;line-height:1.3}
.mv-hero p{max-width:680px;margin:0 auto;color:rgba(255,255,255,.82);font-size:.98rem;line-height:1.85}
.mv-kpi{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:18px 0 8px}
.mv-kpi-item{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:16px 10px;text-align:center}
.mv-kpi-num{display:block;font-size:1.6rem;font-weight:900;color:var(--mv);line-height:1.2}
.mv-kpi-label{display:block;font-size:.76rem;color:var(--text-secondary);margin-top:4px}
.mv-sec{margin:44px 0 0}
.mv-sec-title{display:flex;align-items:center;gap:10px;font-size:1.28rem;font-weight:800;margin-bottom:6px;padding-left:12px;border-left:4px solid var(--mv)}
.mv-sec-sub{font-size:.86rem;color:var(--text-muted);margin:0 0 18px 16px}
/* 观影顺序双 Tab */
.mv-tabs{display:flex;gap:10px;margin-bottom:16px;flex-wrap:wrap}
.mv-tab{font-family:inherit;font-size:.9rem;padding:8px 18px;border-radius:999px;border:1px solid var(--border);background:var(--card);color:var(--text-secondary);cursor:pointer;transition:all .18s}
.mv-tab:hover{border-color:var(--mv);color:var(--mv)}
.mv-tab.active{background:var(--mv);border-color:var(--mv);color:#fff}
.mv-order{list-style:none;margin:0;padding:0;counter-reset:mv;display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:10px}
.mv-order li{counter-increment:mv;display:flex;align-items:center;gap:10px;background:var(--card);border:1px solid var(--border);border-left:4px solid var(--mv);border-radius:10px;padding:10px 14px;font-size:.9rem;transition:transform .15s,box-shadow .15s}
.mv-order li:hover{transform:translateX(2px);box-shadow:var(--shadow-sm)}
.mv-order li::before{content:counter(mv);flex:0 0 26px;height:26px;display:flex;align-items:center;justify-content:center;font-size:.78rem;font-weight:800;color:#fff;background:linear-gradient(135deg,var(--mv),var(--mv-2));border-radius:50%}
.mv-order-t{font-weight:700;color:var(--text);flex:1;min-width:0}
.mv-order-p{font-size:.72rem;color:var(--mv);background:var(--mv-soft);padding:2px 8px;border-radius:999px;white-space:nowrap}
.mv-order-y{font-size:.78rem;color:var(--text-muted);font-variant-numeric:tabular-nums;white-space:nowrap}
/* 观影顺序按阶段折叠 */
.mv-order-groups{display:flex;flex-direction:column;gap:12px}
.mv-phase-group{border:1px solid var(--border);border-radius:12px;overflow:hidden;background:var(--card)}
.mv-phase-group>summary{list-style:none;cursor:pointer;display:flex;align-items:center;gap:10px;padding:13px 16px;font-weight:800;font-size:.96rem;user-select:none;transition:background .15s}
.mv-phase-group>summary::-webkit-details-marker{display:none}
.mv-phase-group>summary:hover{background:var(--bg-secondary)}
.mv-phase-group>summary::before{content:'▸';color:var(--mv);font-size:.8rem;transition:transform .2s}
.mv-phase-group[open]>summary::before{content:'▾'}
.mv-pg-no{color:var(--mv);font-weight:800;font-size:.8rem;letter-spacing:.5px}
.mv-pg-count{margin-left:auto;font-size:.74rem;color:var(--text-muted);font-weight:500}
.mv-phase-group .mv-order{padding:4px 14px 14px;gap:8px}
/* 章节锚点导航 */
html{scroll-behavior:smooth}
.mv-toc{position:sticky;top:62px;z-index:5;display:flex;flex-wrap:wrap;gap:8px;margin:22px 0 6px;padding:10px 12px;background:var(--card);border:1px solid var(--border);border-radius:12px;box-shadow:var(--shadow-sm)}
.mv-toc a{font-size:.82rem;padding:6px 13px;border-radius:999px;background:var(--bg-secondary);color:var(--text-secondary);text-decoration:none;transition:all .15s}
.mv-toc a:hover{background:var(--mv-soft);color:var(--mv)}
.mv-sec{scroll-margin-top:74px}
/* 大板块整体折叠 */
.mv-sec>summary{position:relative;list-style:none;cursor:pointer;padding:6px 30px 8px 0;outline:none}
.mv-sec>summary::-webkit-details-marker{display:none}
.mv-sec>summary .mv-sec-title{margin-bottom:2px;transition:color .15s}
.mv-sec>summary:hover .mv-sec-title{color:var(--mv)}
.mv-sec>summary .mv-sec-sub{margin:0 0 0 16px}
.mv-sec>summary::after{content:'▸';position:absolute;right:4px;top:10px;color:var(--mv);font-size:1.1rem;line-height:1;transition:transform .2s}
.mv-sec[open]>summary::after{content:'▾'}
/* 阶段时间线 */
.mv-phase-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}
.mv-phase-card{background:var(--card);border:1px solid var(--border);border-top:3px solid var(--mv);border-radius:12px;padding:18px 16px;transition:transform .2s,box-shadow .2s}
.mv-phase-card:hover{transform:translateY(-3px);box-shadow:var(--shadow-md)}
.mv-phase-emoji{font-size:1.8rem}
.mv-phase-no{font-size:.74rem;font-weight:700;color:var(--mv);letter-spacing:.5px;margin:6px 0 2px}
.mv-phase-name{font-size:1.02rem;margin-bottom:6px}
.mv-phase-span{font-size:.76rem;color:var(--text-muted);margin-bottom:8px}
.mv-phase-desc{font-size:.82rem;color:var(--text-secondary);line-height:1.65}
/* 英雄档案卡沿用全局 .hero-grid / .hero-card / .hero-avatar / .hero-info */
.hero-avatar{font-size:2.6rem}
/* 私人评分 */
.mv-rating{display:flex;flex-direction:column;gap:12px}
.mv-rating-item{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:14px 16px}
.mv-rating-head{display:flex;align-items:center;justify-content:space-between;gap:10px;flex-wrap:wrap}
.mv-rating-name{font-size:1rem;font-weight:700;color:var(--text)}
.mv-stars{color:#f5b301;letter-spacing:2px;font-size:1.05rem;white-space:nowrap}
.mv-rating-note{font-size:.86rem;color:var(--text-secondary);line-height:1.7;margin:8px 0 0}
/* 冷知识 */
.mv-trivia{list-style:none;margin:0;padding:0;display:grid;gap:10px}
.mv-trivia li{position:relative;padding:12px 14px 12px 40px;background:var(--bg-secondary);border:1px solid var(--border);border-radius:10px;font-size:.88rem;color:var(--text-secondary);line-height:1.7}
.mv-trivia li::before{content:'🎬';position:absolute;left:12px;top:11px;font-size:1rem}
.mv-note{margin:36px 0 8px;padding:16px 18px;background:var(--bg-secondary);border:1px solid var(--border);border-radius:12px;font-size:.82rem;color:var(--text-secondary);line-height:1.85}
/* 正在热映 & 未来计划 */
.mv-soon{display:flex;flex-direction:column;gap:12px}
.mv-soon-item{border:1px solid var(--border);border-radius:12px;padding:14px 16px;background:var(--card)}
.mv-soon-now{border-left:4px solid var(--mv)}
.mv-soon-soon{border-left:4px solid var(--text-muted)}
.mv-soon-head{display:flex;align-items:center;justify-content:space-between;gap:10px;flex-wrap:wrap}
.mv-soon-name{font-size:1.05rem;font-weight:700;color:var(--text)}
.mv-soon-badge{font-size:.72rem;padding:2px 10px;border-radius:999px;white-space:nowrap}
.mv-soon-now .mv-soon-badge{background:var(--mv-soft);color:var(--mv)}
.mv-soon-soon .mv-soon-badge{background:var(--bg-secondary);color:var(--text-secondary)}
.mv-soon-date{font-size:.8rem;color:var(--text-muted);margin-top:4px;font-variant-numeric:tabular-nums}
.mv-soon-note{font-size:.84rem;color:var(--text-secondary);line-height:1.65;margin:8px 0 0}
.mv-note h3{font-size:.9rem;margin-bottom:8px;color:var(--text)}
.mv-note ul{margin:0;padding-left:18px}
@media(max-width:992px){.mv-phase-grid{grid-template-columns:repeat(2,1fr)}.mv-kpi{grid-template-columns:repeat(2,1fr)}}
@media(max-width:576px){.mv-hero{padding:32px 18px 28px}.mv-hero h1{font-size:1.55rem}.mv-phase-grid{grid-template-columns:1fr}.mv-order{grid-template-columns:1fr}}
"""

    page_js = """
(function(){
  var tabs=[].slice.call(document.querySelectorAll('.mv-tab'));
  var rel=document.getElementById('mvRelease');
  var sto=document.getElementById('mvStory');
  if(!tabs.length||!rel||!sto)return;
  tabs.forEach(function(btn){
    btn.addEventListener('click',function(){
      tabs.forEach(function(x){x.classList.remove('active');});
      btn.classList.add('active');
      var kind=btn.getAttribute('data-order');
      rel.style.display=kind==='release'?'block':'none';
      sto.style.display=kind==='story'?'block':'none';
    });
  });
  // 章节锚点：点击时自动展开目标板块并平滑滚动
  var toc=document.querySelector('.mv-toc');
  if(toc){
    toc.addEventListener('click',function(e){
      var a=e.target.closest('a');
      if(!a)return;
      var id=a.getAttribute('href');
      if(id&&id.charAt(0)==='#'){
        var sec=document.getElementById(id.slice(1));
        if(sec){
          if(sec.tagName==='DETAILS'){ sec.open=true; }
          e.preventDefault();
          sec.scrollIntoView({behavior:'smooth',block:'start'});
        }
      }
    });
  }
})();
"""

    html = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<script>(function(){try{var t=localStorage.getItem('theme');if(t==='light'||t==='dark'){document.documentElement.setAttribute('data-theme',t)}else{var h=new Date().getHours();document.documentElement.setAttribute('data-theme',(h>=6&&h<18)?'light':'dark')}}catch(e){}})();</script>
<link rel="preload" href="js/app.js" as="script">
<link rel="preconnect" href="//hm.baidu.com">
<link rel="dns-prefetch" href="//hm.baidu.com">
<link rel="dns-prefetch" href="//busuanzi.ibruce.info">
__CRITICAL__
<link rel="preload" href="css/style.css?v=20260819" as="style" onload="this.onload=null;this.rel='stylesheet'">
<noscript><link rel="stylesheet" href="css/style.css?v=20260819"></noscript>
<title>漫威宇宙 · 龙兄观影手账 - 龙兄知识库</title><meta name="description" content="龙兄的漫威观影手账：MCU 上映顺序与故事时间线双轨观影指南、六个阶段的时间线、英雄档案卡、私人评分与冷知识。纯文字与 emoji 呈现，规避版权风险。">
<meta name="keywords" content="漫威,Marvel,MCU,漫威观影顺序,漫威电影宇宙,复仇者联盟,钢铁侠,美国队长,银河护卫队,观影指南">
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
<link rel="canonical" href="https://longxiong.vip/marvel.html">
<link rel="icon" type="image/svg+xml" href="https://longxiong.vip/favicon.svg">
<meta property="og:title" content="漫威宇宙 · 龙兄观影手账 - 龙兄知识库">
<meta property="og:description" content="MCU 双轨观影指南、六阶段时间线、英雄档案卡、私人评分与冷知识。">
<meta property="og:type" content="article">
<meta property="og:url" content="https://longxiong.vip/marvel.html">
<meta property="og:image" content="https://longxiong.vip/img/og-image.png">
<meta property="og:locale" content="zh_CN">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="漫威宇宙 · 龙兄观影手账 - 龙兄知识库">
<meta name="twitter:description" content="MCU 双轨观影指南、六阶段时间线、英雄档案卡、私人评分与冷知识。">
<meta name="twitter:image" content="https://longxiong.vip/img/og-image.png">
</head>
<body>

__NAVBAR__

  <main id="main-content" role="main"><div class="container">
  <div class="breadcrumb" id="breadcrumb">
    <a href="index.html">首页</a>
    <span class="sep">›</span>
    <span class="current">漫威宇宙</span>
  </div>

  <!-- ===== Hero ===== -->
  <div class="mv-hero">
    <span class="mv-kicker">MARVEL CINEMATIC UNIVERSE · 龙兄观影手账</span>
    <h1>漫威宇宙</h1>
    <p>从 2008 年托尼·斯塔克在山洞里敲出第一套战甲，到今天横跨电影与剧集的多元宇宙——一份属于龙兄的观影手账：怎么看、按什么顺序看、谁值得记住，以及哪些片子最对胃口。</p>
  </div>

  <div class="mv-kpi">
    <div class="mv-kpi-item"><span class="mv-kpi-num">__NFILMS__</span><span class="mv-kpi-label">已收录影剧</span></div>
    <div class="mv-kpi-item"><span class="mv-kpi-num">__NPHASES__</span><span class="mv-kpi-label">阶段划分</span></div>
    <div class="mv-kpi-item"><span class="mv-kpi-num">__NHEROES__</span><span class="mv-kpi-label">英雄档案</span></div>
    <div class="mv-kpi-item"><span class="mv-kpi-num">__NRATINGS__</span><span class="mv-kpi-label">私人评分</span></div>
  </div>

  <nav class="mv-toc" aria-label="章节导航">
    <a href="#sec-order">🎬 观影顺序</a>
    <a href="#sec-phase">📜 阶段</a>
    <a href="#sec-hero">🦸 英雄</a>
    <a href="#sec-rate">⭐ 评分</a>
    <a href="#sec-trivia">💡 冷知识</a>
    <a href="#sec-soon">🎟️ 热映/计划</a>
  </nav>

  <!-- ===== 观影顺序 ===== -->
  <details class="mv-sec" id="sec-order">
    <summary><h2 class="mv-sec-title">观影顺序：两条线任你选</h2>
    <p class="mv-sec-sub">「上映顺序」按当年影院节奏看，「故事时间线」按宇宙内时间看；点标题展开，再点阶段标题看明细。</p></summary>
    <div class="mv-tabs">
      <button class="mv-tab active" data-order="release">🎬 上映顺序</button>
      <button class="mv-tab" data-order="story">🕰️ 故事时间线</button>
    </div>
    <div class="mv-order-groups" id="mvRelease">
__RELEASE__
    </div>
    <div class="mv-order-groups" id="mvStory" style="display:none">
__STORY__
    </div>
  </details>

  <!-- ===== 阶段时间线 ===== -->
  <details class="mv-sec" id="sec-phase">
    <summary><h2 class="mv-sec-title">六个阶段，一部传奇编年</h2>
    <p class="mv-sec-sub">官方把 MCU 分成「无限传奇（Phase 1–3）」与「多元宇宙传奇（Phase 4–6）」两大篇章；以下阶段与年份为个人整理，官方计划可能调整。</p></summary>
    <div class="mv-phase-grid">
__PHASES__
    </div>
  </details>

  <!-- ===== 英雄档案卡 ===== -->
  <details class="mv-sec" id="sec-hero">
    <summary><h2 class="mv-sec-title">英雄档案卡</h2>
    <p class="mv-sec-sub">挑了些最常被提起的名字，纯文字卡片，绝不托管任何官方剧照或海报。</p></summary>
    <div class="hero-grid">
__HEROES__
    </div>
  </details>

  <!-- ===== 私人评分 ===== -->
  <details class="mv-sec" id="sec-rate">
    <summary><h2 class="mv-sec-title">龙兄私人评分</h2>
    <p class="mv-sec-sub">凭个人口味打的星，仅供参考，欢迎来辩。</p></summary>
    <div class="mv-rating">
__RATINGS__
    </div>
  </details>

  <!-- ===== 冷知识 ===== -->
  <details class="mv-sec" id="sec-trivia">
    <summary><h2 class="mv-sec-title">冷知识</h2>
    <p class="mv-sec-sub">几件看片时不一定会注意的小事。</p></summary>
    <ul class="mv-trivia">
__TRIVIA__
    </ul>
  </details>

  <details class="mv-sec" id="sec-soon">
    <summary><h2 class="mv-sec-title">正在热映 &amp; 未来计划</h2>
    <p class="mv-sec-sub">现在正在映与已定档的院线新片，持续更新。</p></summary>
    <div class="mv-soon">
__SOON__
    </div>
  </details>

  <div class="mv-note">
    <h3>关于本页</h3>
    <ul>
      <li>本页为<b>个人影迷手账</b>，全部以 emoji 与原创文字呈现，<b>不托管任何漫威官方剧照、海报或角色宣传图</b>，以此规避版权风险。</li>
      <li>影片年份、阶段划分、观看顺序均为个人整理与偏好，<b>官方制作计划可能调整</b>，一切以官方最终上映为准。</li>
      <li>英雄卡、评分、冷知识均为主观整理，如有出入欢迎指正。</li>
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
      "headline": "漫威宇宙 · 龙兄观影手账 - 龙兄知识库",
      "url": "https://longxiong.vip/marvel.html",
      "description": "MCU 双轨观影指南、六阶段时间线、英雄档案卡、私人评分与冷知识。"
    }
  ]
}
</script>

<script>__PAGEJS__</script>
</body>
</html>
"""

    html = (html
            .replace('__CRITICAL__', critical)
            .replace('__NAVBAR__', navbar)
            .replace('__FOOTER__', footer)
            .replace('__PAGECSS__', page_css.strip())
            .replace('__PAGEJS__', page_js.strip())
            .replace('__RELEASE__', release_html)
            .replace('__STORY__', story_html)
            .replace('__PHASES__', build_phases())
            .replace('__HEROES__', build_heroes())
            .replace('__RATINGS__', build_ratings())
            .replace('__TRIVIA__', build_trivia())
            .replace('__SOON__', build_soon())
            .replace('__SOURCES__', build_sources())
            .replace('__NFILMS__', str(n_films))
            .replace('__NPHASES__', str(n_phases))
            .replace('__NHEROES__', str(n_heroes))
            .replace('__NRATINGS__', str(n_ratings))
            .replace('__LASTUPDATE__', LAST_UPDATE))

    with open(OUT, 'w', encoding='utf-8') as f:
        f.write(html)

    print('生成完成: %s' % OUT)
    print('  上映顺序 %d 部，故事时间线 %d 部，阶段 %d，英雄 %d，评分 %d，冷知识 %d'
          % (len(RELEASE_ORDER), len(STORY_ORDER), n_phases, n_heroes, n_ratings, len(TRIVIA)))
    print('  文件大小 %.1f KB' % (len(html.encode('utf-8')) / 1024))


if __name__ == '__main__':
    main()
