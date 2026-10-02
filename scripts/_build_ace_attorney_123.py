#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""一次性写入：static/games/ace-attorney-123.html（逆转裁判 123 Switch 版）。

以 static/games/onimusha-1.html 为底稿复制而来（保证 CSP / 骨架 / 页尾 / 相关阅读块一致），
本脚本只做「整段替换」，每条都断言命中 1 次，绝不静默漏改。
改完由 build_game_guide.py + apply_game_guide.py 注入「值不值得玩」块，
再由 build_related.py / apply_related.py 刷新相关阅读。
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, "static", "games", "ace-attorney-123.html")

TITLE = "逆转裁判123：成步堂精选集｜玩过的游戏·Switch｜龙兄知识库"

REPL = [
    # ── 标题四字段（title / og / twitter / JSON-LD headline 必须完全一致，sync_titles 会卡） ──
    ("<title>鬼武者 | 玩过的游戏2026实测避坑｜龙兄知识库</title>", "<title>" + TITLE + "</title>"),
    (('<meta property="og:title" content="鬼武者 | 玩过的游戏2026实测避坑｜龙兄知识库">'),
     ('<meta property="og:title" content="' + TITLE + '">')),
    ('<meta name="twitter:title" content="鬼武者 | 玩过的游戏2026实测避坑｜龙兄知识库">',
     '<meta name="twitter:title" content="' + TITLE + '">'),
    ('"headline": "鬼武者 | 玩过的游戏2026实测避坑｜龙兄知识库"',
     '"headline": "' + TITLE + '"'),
    ('"url": "https://longxiong.vip/games/onimusha-1.html"',
     '"url": "https://longxiong.vip/games/ace-attorney-123.html"'),
    ('"description": "鬼武者(Onimusha: Warlords) 卡普空战国生存动作游戏——以金城武饰演的明智左马介为主角，系列开山之作，现已通关。"',
     '"description": "逆转裁判123：成步堂精选集（Phoenix Wright: Ace Attorney Trilogy）卡普空法庭推理冒险 Switch 版——收录前三代共 14 话，庭上追问证词、庭外调查取证。"'),

    # ── 面包屑 / 封面 / 标题 ──
    ('<span class="current">鬼武者</span>', '<span class="current">逆转裁判123</span>'),
    ('<div class="detail-cover" data-lightbox data-caption="鬼武者" data-src="../img/games/onimusha-1-cover.webp">'
     '<img width="1280" height="720" src="../img/games/onimusha-1-cover.webp" alt="鬼武者 封面" loading="lazy" decoding="async"></div>',
     '<div class="detail-cover" data-lightbox data-caption="逆转裁判123 封面" data-src="../img/games/ace-attorney-123-cover.webp">'
     '<img width="1280" height="720" src="../img/games/ace-attorney-123-cover.webp" alt="逆转裁判123 封面" loading="lazy" decoding="async"></div>'),
    ("<h1>鬼武者</h1>", "<h1>逆转裁判 123</h1>"),
    ('<span class="en-title">Onimusha: Warlords</span>', '<span class="en-title">Phoenix Wright: Ace Attorney Trilogy</span>'),

    # ── 徽章 / 信息表 ──
    ('<span class="badge platform">🎮 PS2</span>\n'
     '<span class="badge status-completed">✅ 已通关</span>\n'
     '<span class="badge">战国生存动作</span>\n'
     '<span class="badge">动作</span>\n'
     '<span class="badge">幻魔</span>',
     '<span class="badge platform">🎮 Switch</span>\n'
     '<span class="badge status-completed">✅ 已玩过</span>\n'
     '<span class="badge">法庭推理</span>\n'
     '<span class="badge">文字冒险</span>\n'
     '<span class="badge">剧情向</span>'),

    ('<tr><th>开发商</th><td>Capcom（卡普空）</td></tr>\n'
     '<tr><th>发行商</th><td>Capcom（卡普空）</td></tr>\n'
     '<tr><th>发售日期</th><td>2001年1月（PS2）/ 高清重制版 2018年</td></tr>\n'
     '<tr><th>平台</th><td>PS2（原版）/ PS4·Switch·Xbox·PC（重制版）</td></tr>\n'
     '<tr><th>游玩时长</th><td>待补充</td></tr>\n'
     '<tr><th>游戏人数</th><td>单人</td></tr>',
     '<tr><th>开发商</th><td>Capcom（卡普空）</td></tr>\n'
     '<tr><th>发行商</th><td>Capcom（卡普空）</td></tr>\n'
     '<tr><th>发售日期</th><td>2019年2月21日（Switch／PS4／Xbox One 同步）/ PC 版 2019年4月10日</td></tr>\n'
     '<tr><th>平台</th><td>Nintendo Switch（本机版本）/ PS4·Xbox One·PC / 初版为 3DS（2014年）</td></tr>\n'
     '<tr><th>游玩时长</th><td>共 14 话，官方未公布统一时长，按章节体量推算全通约 20 小时上下</td></tr>\n'
     '<tr><th>游戏人数</th><td>单人</td></tr>\n'
     '<tr><th>语言</th><td>日／英／西／法／德／葡／韩／中（简繁中文 2019年8月22日更新追加）</td></tr>\n'
     '<tr><th>分级</th><td>12 岁以上（CERO B／ESRB Teen／PEGI 12）</td></tr>\n'
     '<tr><th>下载容量</th><td>2.8 GB（任天堂商店页标注）</td></tr>'),

    # ── 游戏简介 ──
    ('<p>《鬼武者》（Onimusha: Warlords）是卡普空于 2001 年推出的战国生存动作游戏，系列开山之作。主角明智左马介秀信以演员金城武为原型并亲自配音，讲述其与幻魔（Genma）一族周旋、拯救被掳走的雪姬的战国奇谭。</p>\n'
     '<p>游戏把「战国版生化危机」的箱庭探索与爽快的刀剑战斗结合，首创「一闪」反击系统——看准敌人攻击瞬间按键，可一击秒杀并吸取其鬼力。这一设计后来成为整个系列的灵魂，也被无数动作游戏借鉴。</p>\n'
     '<p>作为 PS2 早期代表作，鬼武者凭借金城武的明星效应、浓郁的日本妖怪美学和流畅的剑戟演出，全球累计销量突破 200 万套，是卡普空动作线的重要基石。</p>',
     '<p>《逆转裁判123：成步堂精选集》（Phoenix Wright: Ace Attorney Trilogy）是卡普空把系列前三代打包的高清合集，'
     'Switch 版 2019 年 2 月 21 日与 PS4、Xbox One 同步发售，PC（Steam）版 4 月 10 日跟进。'
     '收录《逆转裁判：复苏的逆转》《逆转裁判2》《逆转裁判3》共 14 话，正是成步堂龙一当主角的原点三部曲。</p>\n'
     '<p>玩法是典型的法庭推理冒险：庭外调查找证物、庭上质询证人，靠指出证词里的矛盾把案子翻过来。'
     'Switch 版完整支持掌机／桌面／电视三种模式，也支持触屏操作，通勤路上能一口气推完一整案。</p>\n'
     '<p>这一代也是系列第一次官方中文化的作品——2019 年 8 月 22 日的更新给家用机与 Steam 版追加了简繁中文文本及对应语音，'
     '任天堂商店页列明的语言共 8 种。销量方面，卡普空公布该作 Switch／PS4／PC 三平台全球累计 210 万份（截至 2023 年 3 月）。</p>'),

    # ── 核心玩法 ──
    ('<h2>战斗系统</h2>\n'
     '<ul>\n'
     '<li><strong>一闪（Issen）</strong>：敌人攻击前摇瞬间按键，触发一闪秒杀并吸取鬼力，是输出的核心手段</li>\n'
     '<li><strong>鬼力 / 吸魂</strong>：击败敌人积攒鬼力，用于强化武器与释放鬼战术</li>\n'
     '<li><strong>武器（刀）</strong>：以日本刀近战为主，招式简洁但时机要求高</li>\n'
     '<li><strong>鬼战术</strong>：消耗鬼力发动范围攻击或特殊招式，应对群敌</li>\n'
     '</ul>\n'
     '<h2>探索要素</h2>\n'
     '<ul>\n'
     '<li><strong>箱庭关卡</strong>：类似生化危机的锁定场景，解谜与战斗交替</li>\n'
     '<li><strong>木札 / 道具</strong>：收集补给与线索推进流程</li>\n'
     '<li><strong>隐藏要素</strong>：多周目解锁更强力武器与结局</li>\n'
     '</ul>',
     '<h2>法庭辩论</h2>\n'
     '<ul>\n'
     '<li><strong>追问证词</strong>：庭上一段段推进证人发言，挑出前后对不上的地方接着追</li>\n'
     '<li><strong>出示证据</strong>：把庭外调查拿到的证物亮给证人或法庭，直接戳穿说法</li>\n'
     '<li><strong>检察官施压</strong>：御剑怜侍、狩魔豪这些检察官负责逼问，2 代起狩魔冥也登场对台</li>\n'
     '</ul>\n'
     '<h2>调查要素</h2>\n'
     '<ul>\n'
     '<li><strong>现场取证</strong>：在场景里翻找可交互物件，收集证物与人物关系</li>\n'
     '<li><strong>档案与证词</strong>：先搞清「谁在哪、说了什么」，再带着账上庭才有抓手</li>\n'
     '<li><strong>三作任选顺序</strong>：三个故事可随意挑着玩，不必硬按 1 到 3 的顺序</li>\n'
     '</ul>'),

    # ── 系列定位 ──
    ('<p>鬼武者开创了卡普空「战国奇幻动作」的一条独立产品线，与《生化危机》共享生存动作基因，却用日本刀与妖魔题材走出了截然不同的味道。左马介的故事在三代中横跨战国与现代巴黎，是系列最完整的叙事弧线。</p>\n'
     '<p style="margin-top:12px;font-size:0.95rem;color:var(--gm)">📌 想接着看续作，可前往 <a href="../games/onimusha-2.html" style="color:var(--blue-light)">鬼武者2</a> 与 <a href="../games/onimusha-3.html" style="color:var(--blue-light)">鬼武者3</a>。</p>',
     '<p>这是对 2014 年 3DS 版《逆转裁判123 成步堂精选集》的家用机移植：场景全部高清重绘、界面重做，也是系列第一次在非任天堂主机上发售。</p>\n'
     '<p>往后看，成步堂篇到 3 代为止：《逆转裁判4》换王泥喜法介担纲，5、6 代由成步堂、王泥喜与希月心音共同主角的篇章承接；'
     '另有《逆转检事》外传与《大逆转裁判》两部支线可补。</p>\n'
     '<p style="margin-top:12px;font-size:0.95rem;color:var(--gm)">📌 想接着翻其他已玩记录，可看 <a href="../games/onimusha-1.html" style="color:var(--blue-light)">鬼武者</a> 与 <a href="../games/wukong.html" style="color:var(--blue-light)">黑神话：悟空</a>。</p>'),

    # ── 截图 ──
    ('<div class="screenshot-item" data-lightbox data-caption="鬼武者 实机截图 1" data-src="../img/games/onimusha-1-shot-1.webp">'
     '<img width="1600" height="900" src="../img/games/onimusha-1-shot-1.webp" alt="鬼武者 实机截图 1" loading="lazy" decoding="async"></div>',
     '<div class="screenshot-item" data-lightbox data-caption="逆转裁判123 实机截图 1" data-src="../img/games/ace-attorney-123-shot-1.webp">'
     '<img width="1600" height="900" src="../img/games/ace-attorney-123-shot-1.webp" alt="逆转裁判123 实机截图 1" loading="lazy" decoding="async"></div>'),
    ('<div class="screenshot-item" data-lightbox data-caption="鬼武者 实机截图 2" data-src="../img/games/onimusha-1-shot-2.webp">'
     '<img width="1600" height="900" src="../img/games/onimusha-1-shot-2.webp" alt="鬼武者 实机截图 2" loading="lazy" decoding="async"></div>',
     '<div class="screenshot-item" data-lightbox data-caption="逆转裁判123 实机截图 2" data-src="../img/games/ace-attorney-123-shot-2.webp">'
     '<img width="1600" height="900" src="../img/games/ace-attorney-123-shot-2.webp" alt="逆转裁判123 实机截图 2" loading="lazy" decoding="async"></div>'),
    ('<div class="screenshot-item" data-lightbox data-caption="鬼武者 实机截图 3" data-src="../img/games/onimusha-1-shot-3.webp">'
     '<img width="1600" height="900" src="../img/games/onimusha-1-shot-3.webp" alt="鬼武者 实机截图 3" loading="lazy" decoding="async"></div>',
     '<div class="screenshot-item" data-lightbox data-caption="逆转裁判123 实机截图 3" data-src="../img/games/ace-attorney-123-shot-3.webp">'
     '<img width="1600" height="900" src="../img/games/ace-attorney-123-shot-3.webp" alt="逆转裁判123 实机截图 3" loading="lazy" decoding="async"></div>'),
    ('<div class="screenshot-item" data-lightbox data-caption="鬼武者 实机截图 4" data-src="../img/games/onimusha-1-shot-4.webp">'
     '<img width="1600" height="900" src="../img/games/onimusha-1-shot-4.webp" alt="鬼武者 实机截图 4" loading="lazy" decoding="async"></div>',
     '<div class="screenshot-item" data-lightbox data-caption="逆转裁判123 实机截图 4" data-src="../img/games/ace-attorney-123-shot-4.webp">'
     '<img width="1600" height="900" src="../img/games/ace-attorney-123-shot-4.webp" alt="逆转裁判123 实机截图 4" loading="lazy" decoding="async"></div>'),
    ('<div class="screenshot-item" data-lightbox data-caption="鬼武者 实机截图 5" data-src="../img/games/onimusha-1-shot-5.webp">'
     '<img width="1600" height="900" src="../img/games/onimusha-1-shot-5.webp" alt="鬼武者 实机截图 5" loading="lazy" decoding="async"></div>',
     '<div class="screenshot-item" data-lightbox data-caption="逆转裁判123 实机截图 5" data-src="../img/games/ace-attorney-123-shot-5.webp">'
     '<img width="1600" height="900" src="../img/games/ace-attorney-123-shot-5.webp" alt="逆转裁判123 实机截图 5" loading="lazy" decoding="async"></div>'),
    ('<div class="screenshot-item" data-lightbox data-caption="鬼武者 实机截图 6" data-src="../img/games/onimusha-1-shot-6.webp">'
     '<img width="1600" height="900" src="../img/games/onimusha-1-shot-6.webp" alt="鬼武者 实机截图 6" loading="lazy" decoding="async"></div>',
     '<div class="screenshot-item" data-lightbox data-caption="逆转裁判123 实机截图 6" data-src="../img/games/ace-attorney-123-shot-6.webp">'
     '<img width="1600" height="900" src="../img/games/ace-attorney-123-shot-6.webp" alt="逆转裁判123 实机截图 6" loading="lazy" decoding="async"></div>'),
    ('📸 以上为卡普空官方公开实机截图与宣传图（来源：PlayStation 商店页），版权归 Capcom 所有。',
     '📸 以上为任天堂（Nintendo）官方商店公开的游戏封面与实机截图，版权归 Capcom 所有。'),

    # ── 优缺点 ──
    ('<li>一闪系统爽快且耐钻研</li>\n'
     '<li>金城武主演带来强代入感</li>\n'
     '<li>日本妖怪美术氛围浓郁</li>\n'
     '<li>流程紧凑、节奏明快</li>\n'
     '<li>配乐与战国气质契合</li>',
     '<li>14 话剧本密度高，台词与角色辨识度是系列标杆</li>\n'
     '<li>案子短，一章一两小时，通勤能推完一整案</li>\n'
     '<li>2019 年 8 月更新后有官方简繁中文，翻译完成度高</li>\n'
     '<li>Switch 掌机模式完整可用，支持触屏与云存档</li>'),
    ('<li>原版视角与镜头偏固定</li>\n'
     '<li>迷宫偶尔容易卡解谜</li>\n'
     '<li>战斗深度相比续作较浅</li>\n'
     '<li>重制版主要是高清化，玩法未大改</li>',
     '<li>画面是 3DS 时代的高清重绘，2026 年回头看年代感明显</li>\n'
     '<li>法庭流程每章同一套模板，中后期新鲜度下降</li>\n'
     '<li>主体是读文本，不爱看大段文字的人是门槛</li>\n'
     '<li>纯文字游戏却要 2.8 GB 下载（任天堂商店页口径）</li>'),

    # ── 龙兄点评 ──
    ('<p>鬼武者是我心里「战国动作」的启蒙作。一闪那个手感，按对的瞬间真的会上瘾——后来很多游戏都在抄这个设计，但卡普空自己做得最地道。</p>\n'
     '<p>金城武那张脸往主角上一放，当年简直降维打击，代入感拉满。剧情虽然不算多复杂，但幻魔、织田信长妖魔化这些改编够大胆，看得出卡普空想讲点不一样的战国故事。</p>\n'
     '<p><strong>缺点也有</strong>：原版的固定视角现在回头看有点古早，解谜偶尔让人摸不着头脑；战斗深度放到今天不算深。但作为开山之作，它的地位和爽快度都值得给高分。</p>\n'
     '<p><strong>适合人群：</strong>喜欢日本战国、刀剑动作、追求一击必杀爽感的玩家。</p>',
     '<p>逆转裁判是那种「明知道流程就那样，还是一章接一章停不下来」的游戏。真正抓人的是剧本——每章翻案那一刻的劲头，比不少大制作的花活都足，「异议！」喊出口的满足感是设计出来的，不是特效堆出来的。</p>\n'
     '<p><strong>我这台走的是中文版</strong>，从 2019 年那次更新算起，翻译在引进的日式推理游戏里属于第一梯队，不用隔着一层去看翻译腔。</p>\n'
     '<p><strong>缺点也说清楚</strong>：庭上庭下两件事翻来覆去就那几招，玩到第三作基本是凭剧情撑着；画面就更别提，高清重绘救不了 2014 年的底子。但论「单位时间里讲了多少故事」，它在同价位里很少输。</p>\n'
     '<p><strong>适合人群：</strong>愿意安安静静读完一段好剧本、喜欢从证词裂缝里揪真凶的玩家；对动作手感或开放世界有期待的，这台会让你失望。</p>'),

    # ── 值不值得玩块：先删掉，交给 apply_game_guide 注入 ──
    ('<!-- game:begin -->\n'
     '<section class="lx-insight lx-insight-guide" aria-label="值不值得玩">\n'
     '  <div class="lx-insight-head">\n'
     '    <span class="lx-insight-kicker">玩之前先看这个</span>\n'
     '    <h2 class="lx-insight-title">值不值得玩</h2>\n'
     '  </div>\n'
     '  <dl class="lx-insight-list">\n'
     '    <div class="lx-insight-row">\n'
     '      <dt class="lx-insight-k">这是什么游戏</dt>\n'
     '      <dd class="lx-insight-v">Capcom 的和风生存恐怖动作，把《生化危机》的 fixed camera 换成了日本战国舞台，「一刀斩」是它最出名的系统</dd>\n'
     '    </div>\n'
     '    <div class="lx-insight-row">\n'
     '      <dt class="lx-insight-k">适合谁</dt>\n'
     '      <dd class="lx-insight-v">适合对 PS2 时代老游戏、和风题材有兴趣的玩家；想看画面表现的话，它的年代感很明显</dd>\n'
     '    </div>\n'
     '    <div class="lx-insight-row">\n'
     '      <dt class="lx-insight-k">上手门槛</dt>\n'
     '      <dd class="lx-insight-v">固定机位 + 坦克操作是主要门槛，另外资源管理与解谜比重比现代动作游戏高</dd>\n'
     '    </div>\n'
     '  </dl>\n'
     '</section>\n'
     '<!-- game:end -->',
     '<!-- game:begin -->\n<!-- game:end -->'),

    # ── 相关阅读：先留占位块，交给 apply_related 刷新 ──
    ('<!-- related:begin -->\n'
     '<section class="lx-related" aria-label="相关阅读">\n'
     '  <div class="lx-related-head">\n'
     '    <span class="lx-related-kicker">继续读</span>\n'
     '    <h2 class="lx-related-title">相关阅读</h2>\n'
     '    <span class="lx-rule1"></span>\n'
     '  </div>\n'
     '  <ul class="lx-related-list">\n'
     '    <li class="lx-related-item">\n'
     '      <a class="lx-related-link" href="../games/onimusha-way-of-the-sword.html">\n'
     '        <span class="lx-related-board">玩过的游戏</span>\n'
     '        <span class="lx-related-name">鬼武者 Way of the Sword</span>\n'
     '      </a>\n'
     '    </li>\n'
     '    <li class="lx-related-item">\n'
     '      <a class="lx-related-link" href="../games/onimusha-2.html">\n'
     '        <span class="lx-related-board">玩过的游戏</span>\n'
     '        <span class="lx-related-name">鬼武者2</span>\n'
     '      </a>\n'
     '    </li>\n'
     '    <li class="lx-related-item">\n'
     '      <a class="lx-related-link" href="../games/onimusha-3.html">\n'
     '        <span class="lx-related-board">玩过的游戏</span>\n'
     '        <span class="lx-related-name">鬼武者3</span>\n'
     '      </a>\n'
     '    </li>\n'
     '    <li class="lx-related-item">\n'
     '      <a class="lx-related-link" href="../games/gta6.html">\n'
     '        <span class="lx-related-board">玩过的游戏</span>\n'
     '        <span class="lx-related-name">侠盗猎车手 VI</span>\n'
     '      </a>\n'
     '    </li>\n'
     '  </ul>\n'
     '</section>\n'
     '<!-- related:end -->',
     '<!-- related:begin -->\n'
     '<section class="lx-related" aria-label="相关阅读">\n'
     '  <div class="lx-related-head">\n'
     '    <span class="lx-related-kicker">继续读</span>\n'
     '    <h2 class="lx-related-title">相关阅读</h2>\n'
     '    <span class="lx-rule1"></span>\n'
     '  </div>\n'
     '  <ul class="lx-related-list">\n'
     '  </ul>\n'
     '</section>\n'
     '<!-- related:end -->'),

    # ── 页尾更新日 ──
    ('<div class="update-time">最后更新：2026-09-25</div>', '<div class="update-time">最后更新：2026-10-02</div>'),

    # ── 灯箱 alt ──
    ('style="max-width:92%;max-height:92vh;border-radius:8px;object-fit:contain" />\';o.onclick=function(){document.body.removeChild(o)};document.body.appendChild(o);}\n'
     '</script>',
     'style="max-width:92%;max-height:92vh;border-radius:8px;object-fit:contain" />\';o.onclick=function(){document.body.removeChild(o)};document.body.appendChild(o);}\n'
     '</script>'),
    ('<img width="800" height="600" loading="lazy" src="\'+s+\'" alt="鬼武者详情图"',
     '<img width="800" height="600" loading="lazy" src="\'+s+\'" alt="逆转裁判123 详情图"'),
]


def main():
    html = open(PAGE, encoding="utf-8").read()
    for old, new in REPL:
        n = html.count(old)
        if n != 1:
            print("[FAIL] 命中 %d 次（应为 1）：%s" % (n, old[:70]))
            sys.exit(1)
        html = html.replace(old, new, 1)
    # 灯箱那段 alt 是内联 script 里的单引号包裹，单独处理
    html = html.replace('alt="鬼武者详情图"', 'alt="逆转裁判123 详情图"')
    with open(PAGE, "w", encoding="utf-8") as f:
        f.write(html)
    print("[done] %s 写入完成，共 %d 处替换" % (os.path.basename(PAGE), len(REPL)))
    left = html.count("鬼武者")
    print("      残留「鬼武者」字样：%d 处" % left)


if __name__ == "__main__":
    main()
