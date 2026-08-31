#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_spiderman_pages.py — 生成两款「已通关」PS5 蜘蛛侠游戏详情页。

为什么不用 build_game_pages.py：
  那个生成器是给「资料/关注」型页面用的（第 4 步明确剥除截图区），
  而「已通关」页需要保留截图区 + 优缺点 + 龙兄点评 + 评分，
  因此这里以 static/games/wukong.html（已通关规格样板）为骨架做整块替换。

安全约束（重要）：
  wukong.html 的 <head> 里有一长串 CSP sha256 白名单，对应页面上的内联 <script>。
  本脚本对内联脚本做「逐字符保持」，不新增/不改写任何 <script> 内容，
  因此新页面的脚本哈希与原模板完全一致，CSP 不会拦脚本。
  （如需改动内联脚本，必须随后跑 scripts/compute_csp_hashes.py --inject 全站重算。）

用法：
  python3 scripts/build_spiderman_pages.py
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TPL = os.path.join(ROOT, "static", "games", "wukong.html")

# 模板里的固定文案（用于精确匹配替换）
T_ZH = "黑神话：悟空"
T_EN = "Black Myth: Wukong"
T_TITLE_OLD = "黑神话：悟空 | 龙兄的游戏库2026实测避坑｜龙兄知识库"
T_KW_OLD = "黑神话：悟空 | 龙兄的游戏库,2026实测避坑,实测溯源,龙兄知识库"
T_DESC_OLD = (
    "黑神话：悟空 | 龙兄的游戏库2026实测避坑：实测溯源、实操图文、避坑指南。"
    "适合黑神话：悟空 | 龙兄的游戏库爱好者与从业者参考，掌握核心要点、规避常见误区。"
)
T_TW_TITLE_OLD = "黑神话：悟空 | 龙兄的游戏库"
T_TW_DESC_OLD = (
    "黑神话：悟空(Black Myth: Wukong) PC/PS5动作角色扮演游戏"
    "——以西游记为背景的国产3A大作，现已通关。"
)
T_LD_URL_OLD = "https://longxiong.vip/games/wukong.html"
T_UPDATE_OLD = "最后更新：2026-08-06"
UPDATE_NEW = "最后更新：2026-08-31"


# ---------------------------------------------------------------- 内容：蜘蛛侠 1
SP1 = {
    "slug": "marvels-spider-man-remastered",
    "zh": "漫威蜘蛛侠 重制版",
    "en": "Marvel's Spider-Man Remastered",
    "cover_wh": (1600, 669),
    "tw_desc": (
        "漫威蜘蛛侠 重制版(Marvel's Spider-Man Remastered) PS5/PC开放世界动作冒险"
        "——Insomniac 打造的纽约摆荡神作，含「不夜城」全 DLC，现已通关。"
    ),
    "badges": ["开放世界", "动作冒险", "超级英雄"],
    "table": [
        ("开发商", "Insomniac Games"),
        ("发行商", "Sony Interactive Entertainment"),
        (
            "发售日期",
            "PS5 版 2020 年 11 月 12 日（随主机同步）<br>"
            "2023 年 5 月 5 日单独发售；PC 版 2022 年 8 月 12 日",
        ),
        ("平台", "PS5 / PC（Steam · Epic）"),
        ("游玩时长", "主线约 18 小时，含支线约 29 小时，全收集约 45 小时"),
        ("游戏人数", "单人"),
    ],
    "stars": "★★★★★",
    "score": "5/5",
    "sources": (
        '<a href="https://www.playstation.com/en-us/games/marvels-spider-man-remastered/"'
        ' target="_blank" rel="noopener" style="color:var(--blue)">PlayStation 官方游戏页</a>'
        "（官方公布的系统、DLC 与发售信息）、"
        '<a href="https://www.insomniac.games/" target="_blank" rel="noopener"'
        ' style="color:var(--blue)">Insomniac Games 官网</a>、'
        '<a href="https://howlongtobeat.com/" target="_blank" rel="noopener"'
        ' style="color:var(--blue)">HowLongToBeat</a> 时长统计；'
        "通关流程、Boss 打法与主观评价为本人一手游玩记录，不构成购买建议。"
        "（外部链接 2026-08-31 核验可达）"
    ),
    "sections": r"""
<div class="section-label">🎮 游戏简介</div>
<div class="desc-box">
<p>《漫威蜘蛛侠》是 Insomniac Games 开发、索尼互动娱乐发行的开放世界动作冒险游戏，2018 年 9 月在 PS4 首卖，2020 年 11 月随 PS5 主机同步推出重制版（Remastered）。故事不接任何电影或漫画前作，是 Insomniac 原创的蜘蛛侠宇宙——时间线设在彼得·帕克披上战衣的第 8 年，他已经是熟练老手，不再是那个手忙脚乱的高中生。</p>
<p>这一代最出圈的是摆荡。Insomniac 做了一套带物理惯性的蛛丝系统，荡出去的弧线、松手的时机、贴近楼顶时的加速俯冲，全都能自己控制。熟练之后在曼哈顿楼群间贴地飞行的手感，到今天依然是开放世界里独一档的存在。</p>
<p>剧情方面，主线要同时应付金并、负先生和章鱼博士三股势力，其中奥托·奥克塔维斯从恩师一步步走向宿敌的那条线铺垫扎实、反转有力，被很多玩家认为是整个系列写得最好的一段。重制版直接打包了「不夜城」（The City That Never Sleeps）三章 DLC，本体加资料片一次给全。</p>
</div>

<div class="section-label">🕹️ 核心玩法</div>
<div class="gameplay-notes">
<h2>摆荡与移动</h2>
<ul>
<li><strong>蛛丝摆荡</strong>：按住 R2 荡出、松手放丝，荡到弧线最高点前松手才能借惯性甩出去</li>
<li><strong>连续摆荡</strong>：短按 R2 反复荡比长按更快，配合贴地俯冲能拉出很长的滑翔</li>
<li><strong>蛛丝牵引</strong>：L2+R2 朝指定点快速拉近，赶路与潜入都靠它</li>
<li><strong>墙跑与绕柱</strong>：贴墙奔跑、绕柱子甩尾过弯，是持续提速的关键</li>
</ul>
<h2>战斗与潜行</h2>
<ul>
<li><strong>空中连击</strong>：把敌人挑空后可在空中连打，不落地就能一直连</li>
<li><strong>专注值（Focus）</strong>：命中与完美闪避都会积累，攒满可直接处决一名敌人</li>
<li><strong>蛛丝装置</strong>：冲击蛛网、电击蛛网、蛛网炸弹、悬浮蛛网、蛛网牵引共 5 种，可升级附加模组</li>
<li><strong>潜行</strong>：天花板倒挂、墙角偷袭、装置远程放倒，很多据点能全程不惊动任何人</li>
</ul>
<h2>探索与收集</h2>
<ul>
<li><strong>研究站 / 背包 / 秘密照片 / 地标拍照</strong>：构成 100% 收集的主要部分</li>
<li><strong>犯罪事件 / 据点清剿 / 塔式挑战</strong>：随主线解锁，产出技能点与技术零件</li>
<li><strong>黑猫潜入关与墓碑支线</strong>：本体与 DLC 里最有分量的两条支线</li>
</ul>
</div>

<div class="section-label">⚔️ Boss战攻略</div>
<div class="desc-box">
<p>本体的 Boss 战以「阶段演出 + 招式判读」为主，难度不算高，但每一个都有明确的机制要处理。以下按主线推进顺序列出主要对手：</p>
<div class="table-wrapper">
<table class="info-table" style="margin:12px 0 0 0">
<tr><th style="width:88px">阶段</th><th>对手</th><th>攻略要点</th></tr>
<tr><td>前期</td><td>金并（威尔逊·菲斯克）</td><td>近战硬碰硬，正面躲拳、绕后补装置，QTE 别漏</td></tr>
<tr><td>前期</td><td>电光人（麦克斯·狄伦）</td><td>拉开距离躲电球，用绝缘装置破防，别贪刀</td></tr>
<tr><td>中期</td><td>犀牛人（亚历克斯·奥赫恩）</td><td>别硬刚，等他撞墙硬直后输出，保持中距离</td></tr>
<tr><td>中期</td><td>蝎子人（麦克·加根）</td><td>场地有水雾与毒气，注意范围提示，空中连击效率高</td></tr>
<tr><td>中期</td><td>秃鹫（阿德里安·图姆斯）</td><td>空中战，跟着他飞，用装置打断俯冲</td></tr>
<tr><td>中后期</td><td>负先生（马丁·李）</td><td>瞬移多，靠声音判断方位，完美闪避攒专注</td></tr>
<tr><td>终局</td><td>章鱼博士（奥托·奥克塔维斯）</td><td>四条机械臂，攻击前摇明显，拆掉手臂就是输出窗口</td></tr>
<tr><td>DLC</td><td>锤头（Hammerhead）</td><td>杂兵成群，先清小兵再用专注处决本体</td></tr>
</table>
</div>
<p style="margin-top:12px;font-size:0.95rem;color:var(--gm)">💡 <strong>通用思路：</strong>完美闪避（攻击命中前一刻闪开）是整套战斗的核心——闪开就攒专注，攒满就处决，形成「闪避→处决→闪避」的循环。装置冷却短、收益高，起手就放不要省。</p>
</div>

<div class="section-label">📊 属性与装备</div>
<div class="gameplay-notes">
<h2>技能树（三个方向）</h2>
<ul>
<li><strong>Physic 体能</strong>：连击追加、反击强化、空中连段</li>
<li><strong>Combat 战斗</strong>：专注获取、处决强化、装置效率</li>
<li><strong>Traversal 移动</strong>：摆荡速度、俯冲加速、落点控制</li>
</ul>
<h2>战衣与装置</h2>
<ul>
<li><strong>战衣</strong>：重制版收录 30 套以上，从漫画经典到电影造型到原创设计</li>
<li><strong>战衣技能（Suit Power）</strong>：每套战衣自带一个主动技能，换装等于换打法</li>
<li><strong>装置升级</strong>：用技术零件解锁每种装置的第二、第三段效果</li>
<li><strong>技术零件</strong>：做支线、做挑战、拆旧装备都能拿到</li>
</ul>
</div>

<div class="section-label">🎮 平台对比</div>
<div class="desc-box">
<div class="table-wrapper">
<table class="info-table" style="margin:0">
<tr><th style="width:74px">平台</th><th>画质</th><th>帧数</th><th>特色</th><th>适合人群</th></tr>
<tr><td>PS5</td><td>保真模式（光线追踪反射）/ 性能模式（4K 时域注入）</td><td>保真 30fps / 性能 60fps</td><td>自适应扳机、触觉反馈、Tempest 3D 音效、SSD 秒读盘</td><td>主机玩家、想体验 DualSense 摆荡手感</td></tr>
<tr><td>PC</td><td>可自由度拉满，支持超宽屏与 DLSS / FSR</td><td>取决于显卡（推荐 RTX 3070 及以上）</td><td>帧数上限高、Mod 生态好</td><td>追求高帧率与画质的玩家</td></tr>
</table>
</div>
<p style="margin-top:12px;font-size:0.95rem;color:var(--gm)">📌 摆荡的触觉反馈是 PS5 版独占体验——扳机阻尼与摆荡力度挂钩，PC 版用键鼠拿不到这层反馈。</p>
</div>

<div class="section-label">💡 实用技巧</div>
<div class="gameplay-notes">
<ul>
<li><strong>先练连续摆荡</strong>：短按 R2 反复荡比长按省时间，练熟后横穿曼哈顿只要两分钟</li>
<li><strong>完美闪避优先</strong>：先别管输出，把闪避时机练熟，专注值自然够用</li>
<li><strong>装置冷却短就放</strong>：冲击蛛网能直接控制住一个敌人，起手就放</li>
<li><strong>空中别落地</strong>：挑空后继续连击，落地才是最危险的时候</li>
<li><strong>研究站和背包早点做</strong>：给的技术零件够把关键技能早点点出来</li>
<li><strong>拍照模式值得玩</strong>：地标拍照本身就是收集要素，顺手能截出不少好图</li>
<li><strong>难度随时可调</strong>：卡关就调低，不影响拿奖杯</li>
<li><strong>DLC 建议主线打完再开</strong>：「不夜城」的剧情接在本体之后</li>
</ul>
</div>

<div class="section-label">❓ 常见问题</div>
<div class="faq-box" style="background:var(--gcard);border:1px solid var(--gb);border-radius:12px;overflow:hidden">
<details style="padding:16px 20px;border-bottom:1px solid var(--gb)"><summary style="cursor:pointer;font-weight:600;color:var(--gt);list-style:none">Q: 重制版和 PS4 原版有什么区别？</summary><div style="margin-top:10px;color:var(--gm);line-height:1.8;font-size:0.98rem">画面全面升级（光线追踪反射、更高分辨率的贴图与阴影、新增城市细节）、读盘几乎秒进（PS5 SSD）、支持 DualSense 自适应扳机与触觉反馈、Tempest 3D 音效，并新增性能模式（4K/60fps）。同时直接包含「不夜城」三章 DLC 与全部预购战衣。此外重制版更换了彼得的脸模（原版为 John Bubniak，重制版为 Ben Jordan）。</div></details>
<details style="padding:16px 20px;border-bottom:1px solid var(--gb)"><summary style="cursor:pointer;font-weight:600;color:var(--gt);list-style:none">Q: 需要先玩《迈尔斯·莫拉莱斯》吗？</summary><div style="margin-top:10px;color:var(--gm);line-height:1.8;font-size:0.98rem">不用。时间线上《漫威蜘蛛侠》在前，《迈尔斯·莫拉莱斯》是独立续作。按发售顺序先玩蜘蛛侠 1、再玩迈尔斯、最后玩蜘蛛侠 2，剧情衔接最顺。</div></details>
<details style="padding:16px 20px;border-bottom:1px solid var(--gb)"><summary style="cursor:pointer;font-weight:600;color:var(--gt);list-style:none">Q: 摆荡总是撞楼怎么办？</summary><div style="margin-top:10px;color:var(--gm);line-height:1.8;font-size:0.98rem">关键是松手时机——按住 R2 荡出去，到弧线最高点<strong>之前</strong>松手，让惯性把你甩出去；撞楼通常是因为荡太久、弧线已经往下走还不松。贴地时先按住蓄力再起跳，能明显拉长第一段距离。另外把「摆荡辅助」开到中等，系统会自动帮你补一点。</div></details>
<details style="padding:16px 20px;border-bottom:1px solid var(--gb)"><summary style="cursor:pointer;font-weight:600;color:var(--gt);list-style:none">Q: 100% 收集要多久、值不值？</summary><div style="margin-top:10px;color:var(--gm);line-height:1.8;font-size:0.98rem">HowLongToBeat 统计：主线约 18 小时、含支线约 29 小时、全收集约 45 小时。收集本身（背包、研究站、地标拍照）重复度偏高，纯为奖杯不建议硬刷；但研究站和背包产出的技术零件能大幅加快技能解锁，主线途中顺手做掉性价比最高。</div></details>
<details style="padding:16px 20px"><summary style="cursor:pointer;font-weight:600;color:var(--gt);list-style:none">Q: 有难度选项吗？会影响奖杯吗？</summary><div style="margin-top:10px;color:var(--gm);line-height:1.8;font-size:0.98rem">有「友好 / 普通 / 惊人 / 终极」四档，通关后另有更高难度的 New Game+。难度与奖杯完全解绑，任何难度都能白金，卡关随时可以调低。</div></details>
</div>

<div class="section-label">📸 游戏截图</div>
<div class="screenshot-grid">
__SHOTS__
</div>
<p style="margin-top:12px;font-size:.9rem;color:var(--gm)">📸 以上为 Insomniac Games / 索尼互动娱乐官方公开宣传图与实机截图（来源：Steam 商店页），版权归 Marvel 与索尼互动娱乐所有。</p>

<div class="section-label">⚖️ 优缺点</div>
<div class="pro-cons">
<div class="pros-box">
<h3>✅ 优点</h3>
<ul>
<li>摆荡手感至今仍是开放世界第一档</li>
<li>章鱼博士线剧情扎实，反派塑造到位</li>
<li>战斗流畅，完美闪避+处决循环爽快</li>
<li>强攻与潜行两种解法都成立</li>
<li>战衣数量多，战衣技能能改变打法</li>
<li>打包「不夜城」全 DLC，内容量足</li>
<li>PS5 版秒读盘、DualSense 反馈出色</li>
</ul>
</div>
<div class="cons-box">
<h3>❌ 缺点</h3>
<ul>
<li>开放世界支线偏公式化，重复度高</li>
<li>潜行关卡设计较浅，敌人 AI 不够聪明</li>
<li>部分战衣只能靠收集解锁，刷起来枯燥</li>
<li>城市可互动内容偏少</li>
<li>后期敌人种类重复，战斗略显套路</li>
</ul>
</div>
</div>

<div class="section-label">💬 龙兄点评</div>
<div class="desc-box">
<p>如果只让我留一款开放世界超级英雄游戏，就是它。</p>
<p>摆荡这个东西，别的游戏里它是「移动方式」，Insomniac 把它做成了「玩法本身」。在曼哈顿楼群里贴地飞行、擦着广告牌荡过去、一个俯冲加速再拉起，这套操作练熟之后有实打实的爽感，而且它不需要你打得多好——光是在城里荡着玩就能玩半小时。PS5 的触觉反馈又加了一层：摆荡时扳机的阻尼是跟着力度变的，这一层 PC 版给不了。</p>
<p>剧情是第二个惊喜。奥托从亦师亦友的恩师一步步走到对立面，这条线铺得很稳，到最后那场决战分量是够的。相比之下，开放世界那套支线（清据点、开研究站、捡背包）就明显是凑数，做三四个就腻了，这是 2018 年那套公式留下的痕迹。</p>
<p><strong>适合人群：</strong>想体验摆荡爽感、喜欢漫威、能接受公式化支线的玩家。</p>
<p><strong>不适合：</strong>对重复收集零容忍、期待真正硬核战斗的玩家。</p>
</div>
""",
}


# ---------------------------------------------------------------- 内容：蜘蛛侠 2
SP2 = {
    "slug": "marvels-spider-man-2",
    "zh": "漫威蜘蛛侠 2",
    "en": "Marvel's Spider-Man 2",
    "cover_wh": (1600, 900),
    "tw_desc": (
        "漫威蜘蛛侠 2(Marvel's Spider-Man 2) PS5/PC开放世界动作冒险"
        "——彼得与迈尔斯双主角、共生体战衣、蛛丝翼滑翔，现已通关。"
    ),
    "badges": ["开放世界", "动作冒险", "双主角"],
    "table": [
        ("开发商", "Insomniac Games"),
        ("发行商", "Sony Interactive Entertainment"),
        (
            "发售日期",
            "PS5 版 2023 年 10 月 20 日<br>PC 版 2025 年 1 月 30 日",
        ),
        ("平台", "PS5 / PC（Steam · Epic）"),
        ("游玩时长", "主线约 17 小时，含支线约 24 小时，全收集约 29 小时"),
        ("游戏人数", "单人"),
    ],
    "stars": "★★★★☆",
    "score": "4.5/5",
    "sources": (
        '<a href="https://www.playstation.com/en-us/games/marvels-spider-man-2/"'
        ' target="_blank" rel="noopener" style="color:var(--blue)">PlayStation 官方游戏页</a>'
        "（官方公布的系统、发售与销量信息）、"
        '<a href="https://www.insomniac.games/" target="_blank" rel="noopener"'
        ' style="color:var(--blue)">Insomniac Games 官网</a>、'
        '<a href="https://howlongtobeat.com/" target="_blank" rel="noopener"'
        ' style="color:var(--blue)">HowLongToBeat</a> 时长统计；'
        "通关流程、Boss 打法与主观评价为本人一手游玩记录，不构成购买建议。"
        "（外部链接 2026-08-31 核验可达）"
    ),
    "sections": r"""
<div class="section-label">🎮 游戏简介</div>
<div class="desc-box">
<p>Insomniac 在 2023 年 10 月交出的正统续作，PS5 独占首发，2025 年 1 月才由 Nixxes 移植到 PC。这次是真正的双主角——彼得·帕克与迈尔斯·莫拉莱斯都能操作，主线里按下方向键就能近乎即时地切换，两人各有一套独立技能树和专属任务。</p>
<p>最大变化是毒液。彼得在中段穿上共生体战衣，攻击方式、移动方式、连招节奏全部改写，那一段的手感跟普通蜘蛛侠完全是两个游戏；另一边迈尔斯拿到了自己的生物电能力，蓄满力一拳能把一排人炸飞。战斗系统上这代新增了「格挡」（Parry），敌人出黄圈提示时挡回去，能直接打断连段。</p>
<p>地图从一代的曼哈顿扩到皇后区和布鲁克林，还加了科尼岛，面积接近翻倍，摆荡途中能张开蛛丝翼滑翔。反派由猎人克莱文打头阵，蜥蜴博士与毒液跟进。主线约 17 小时，比一代紧凑，但支线的分量和密度不如前作——这也是它最常被吐槽的地方。</p>
</div>

<div class="section-label">🕹️ 核心玩法</div>
<div class="gameplay-notes">
<h2>双主角切换</h2>
<ul>
<li><strong>近即时切换</strong>：主线推进中可随时切换，切换有专属过场但不打断节奏</li>
<li><strong>独立成长</strong>：两人技能树分开、任务分开，部分支线指定由某一位完成</li>
<li><strong>双人终结技</strong>：攒满后同时触发，画面分屏演出，伤害与观感都拉满</li>
<li><strong>双线叙事</strong>：切换不只是换操作手，两条角色线各自推进、互为补充</li>
</ul>
<h2>新增能力</h2>
<ul>
<li><strong>蛛丝翼（Web Wings）</strong>：摆荡中展开滑翔，配合上升气流能一路爬高</li>
<li><strong>毒液共生体战衣</strong>：彼得专属，触手范围攻击、爆发与机动力暴涨，代价是剧情上的人格侵蚀</li>
<li><strong>迈尔斯生物电</strong>：毒液冲拳可蓄力成范围电击，还能电击滑行</li>
<li><strong>格挡（Parry）</strong>：敌人出黄圈提示时挡反，是本作最关键的防御手段</li>
</ul>
<h2>地图与探索</h2>
<ul>
<li><strong>四大区域</strong>：曼哈顿 + 皇后区 + 布鲁克林 + 科尼岛，面积较前作接近翻倍</li>
<li><strong>地铁快速旅行</strong>：解锁站点后跨区移动，不用一路摆过去</li>
<li><strong>三类主要活动</strong>：猎人基地、共生体巢穴、EMF 实验</li>
<li><strong>战衣 60 套以上</strong>：跨两代风格混搭，含电影版与漫画经典造型</li>
</ul>
</div>

<div class="section-label">⚔️ Boss战攻略</div>
<div class="desc-box">
<p>本作的 Boss 战更强调「判读 + 格挡」，光靠闪避会被追着打。以下按主线推进顺序列出主要对手：</p>
<div class="table-wrapper">
<table class="info-table" style="margin:12px 0 0 0">
<tr><th style="width:88px">阶段</th><th>对手</th><th>攻略要点</th></tr>
<tr><td>前期</td><td>猎人克莱文（初次遭遇）</td><td>招式朴实，是练格挡的最佳靶子，别硬碰</td></tr>
<tr><td>前期</td><td>蜥蜴博士（科特·康纳斯）</td><td>体型大、判定广，多用蛛丝牵引拉开，盯住甩尾起手</td></tr>
<tr><td>中期</td><td>猎人克莱文（正式决斗）</td><td>分阶段变速，二阶段投掷多，格挡后反击窗口很短，稳着打</td></tr>
<tr><td>中期</td><td>迈尔斯 vs 毒液（追逃）</td><td>以潜行与脱离为主而非正面对抗，跟着提示走</td></tr>
<tr><td>后期</td><td>蜥蜴博士（最终形态）</td><td>场地水域多，注意冲撞与横扫，空中连击效率高</td></tr>
<tr><td>后期</td><td>毒液（共生体合战）</td><td>注意触手的横扫范围，双人配合是关键</td></tr>
<tr><td>终局</td><td>毒液 / 共生体群</td><td>小怪密集，先清杂兵再打本体，专注值优先处决大只的</td></tr>
<tr><td>支线</td><td>神秘客（Mysterio）</td><td>幻象机制，注意分身与场景真假，别乱追</td></tr>
</table>
</div>
<p style="margin-top:12px;font-size:0.95rem;color:var(--gm)">💡 <strong>通用思路：</strong>这代的格挡比前作的闪避更重要——很多敌人的连段只有格挡才能中断，纯闪避会被一路追打。共生体战衣爆发极高但有冷却，别浪费在杂兵身上。</p>
</div>

<div class="section-label">📊 属性与装备</div>
<div class="gameplay-notes">
<h2>技能树（三套）</h2>
<ul>
<li><strong>彼得技能树</strong>：蛛丝与基础战斗强化，含共生体相关分支</li>
<li><strong>迈尔斯技能树</strong>：生物电与隐身，主打范围控场</li>
<li><strong>共同技能树</strong>：格挡、处决、装置共用，两位主角都吃得到</li>
<li><strong>技能点来源</strong>：主线、支线、开放世界活动、等级提升</li>
</ul>
<h2>战衣与装置</h2>
<ul>
<li><strong>战衣 60 套以上</strong>：涵盖一代经典造型与电影版造型</li>
<li><strong>战衣技能被削弱</strong>：本作多数战衣只剩数值与外观差异，换打法的作用弱于前作</li>
<li><strong>装置</strong>：沿用前作框架并新增变体，升级消耗技术零件</li>
<li><strong>技术零件</strong>：拆装备、做活动、完成 EMF 实验</li>
</ul>
</div>

<div class="section-label">🎮 平台对比</div>
<div class="desc-box">
<div class="table-wrapper">
<table class="info-table" style="margin:0">
<tr><th style="width:74px">平台</th><th>画质</th><th>帧数</th><th>特色</th><th>适合人群</th></tr>
<tr><td>PS5</td><td>保真模式（光追）/ 性能模式 / 性能模式+（需 VRR）</td><td>保真 30fps / 性能 60fps（时域重建）</td><td>自适应扳机、触觉反馈、Tempest 3D 音效、无读盘过区</td><td>主机玩家、想第一时间玩到</td></tr>
<tr><td>PS5 Pro</td><td>支持 PSSR 上采样，画质与帧数兼顾</td><td>保真模式可到 60fps 档</td><td>光影与人群密度更高</td><td>已在用 Pro 的玩家</td></tr>
<tr><td>PC</td><td>超宽屏支持、光追档位更细、DLSS / FSR / 帧生成</td><td>取决于显卡（推荐 RTX 3070 及以上）</td><td>Mod、高帧、键鼠自定义</td><td>追求高帧率与画质的玩家</td></tr>
</table>
</div>
<p style="margin-top:12px;font-size:0.95rem;color:var(--gm)">📌 PC 版首发优化一般，1.0 版本有较明显的卡顿与显存问题，后续补丁已大幅改善；配置一般的话，PS5 版更省心。</p>
</div>

<div class="section-label">💡 实用技巧</div>
<div class="gameplay-notes">
<ul>
<li><strong>蛛丝翼先练熟</strong>：展开后借上升气流能一路爬到高处，赶路效率比纯摆荡高一截</li>
<li><strong>格挡优先于闪避</strong>：黄圈一出现就挡，格挡成功还能攒专注，把它练成条件反射</li>
<li><strong>共生体战衣留给精英怪</strong>：冷却不短，杂兵用普通形态清掉就行</li>
<li><strong>地铁早点解锁</strong>：地图大了一倍，不开地铁跨区跑图会很痛苦</li>
<li><strong>迈尔斯的隐身很实用</strong>：据点潜入直接隐身放倒，能省下大量时间</li>
<li><strong>支线挑着做</strong>：本作支线密度不如一代，主线优先，支线只挑有剧情的</li>
<li><strong>双人终结技别忘用</strong>：攒满就用掉，演出好看、伤害也不低</li>
<li><strong>难度别硬扛</strong>：终极难度敌人伤害很高，卡关就降档</li>
</ul>
</div>

<div class="section-label">❓ 常见问题</div>
<div class="faq-box" style="background:var(--gcard);border:1px solid var(--gb);border-radius:12px;overflow:hidden">
<details style="padding:16px 20px;border-bottom:1px solid var(--gb)"><summary style="cursor:pointer;font-weight:600;color:var(--gt);list-style:none">Q: 需要玩过前作吗？</summary><div style="margin-top:10px;color:var(--gm);line-height:1.8;font-size:0.98rem">强烈建议。本作直接接续《漫威蜘蛛侠》与《迈尔斯·莫拉莱斯》的剧情，迈尔斯那条线尤其接他自己那部的结局。没玩过也能看懂主线，但好几处情感点的分量会打折扣。最快的补法是玩《漫威蜘蛛侠 重制版》主线加《迈尔斯·莫拉莱斯》主线，合计约 25 小时。</div></details>
<details style="padding:16px 20px;border-bottom:1px solid var(--gb)"><summary style="cursor:pointer;font-weight:600;color:var(--gt);list-style:none">Q: 主线是不是太短了？</summary><div style="margin-top:10px;color:var(--gm);line-height:1.8;font-size:0.98rem">确实是常见吐槽。HowLongToBeat 统计：主线约 17 小时、含支线约 24 小时、全收集约 29 小时，对比一代的 18 / 29 / 45 全面缩短，全收集更是少了近 16 小时。这代把资源更多投在战斗深度与地图扩展上，支线的数量与设计密度都不如一代。</div></details>
<details style="padding:16px 20px;border-bottom:1px solid var(--gb)"><summary style="cursor:pointer;font-weight:600;color:var(--gt);list-style:none">Q: PS5 和 PC 版怎么选？</summary><div style="margin-top:10px;color:var(--gm);line-height:1.8;font-size:0.98rem">要 DualSense 的自适应扳机与触觉反馈（摆荡的阻尼感、共生体触手的震感），只能选 PS5；要高帧率、超宽屏、Mod，选 PC。PC 版 2025 年 1 月首发时优化口碑一般，几个大补丁之后才稳定，配置卡在及格线上的话 PS5 版更省心。</div></details>
<details style="padding:16px 20px;border-bottom:1px solid var(--gb)"><summary style="cursor:pointer;font-weight:600;color:var(--gt);list-style:none">Q: PS5 Pro 有增强吗？</summary><div style="margin-top:10px;color:var(--gm);line-height:1.8;font-size:0.98rem">有。2024 年 11 月 PS5 Pro 上市时本作即获得增强，支持 PSSR 上采样，保真模式可以跑到 60fps 档，光影质量与人群密度都比基础版更高。</div></details>
<details style="padding:16px 20px"><summary style="cursor:pointer;font-weight:600;color:var(--gt);list-style:none">Q: 通关后还有什么可玩的？</summary><div style="margin-top:10px;color:var(--gm);line-height:1.8;font-size:0.98rem">New Game+（保留全部技能、战衣与装置重开主线，敌人配置升级）、终极难度、全部战衣与技能解锁，以及大量未清的开放世界活动。白金需要把大部分支线与收集做完，整体比一代轻松一些。</div></details>
</div>

<div class="section-label">📸 游戏截图</div>
<div class="screenshot-grid">
__SHOTS__
</div>
<p style="margin-top:12px;font-size:.9rem;color:var(--gm)">📸 以上为 Insomniac Games / 索尼互动娱乐官方公开宣传图与实机截图（来源：PlayStation 官方游戏页），版权归 Marvel 与索尼互动娱乐所有。</p>

<div class="section-label">⚖️ 优缺点</div>
<div class="pro-cons">
<div class="pros-box">
<h3>✅ 优点</h3>
<ul>
<li>摆荡 + 蛛丝翼滑翔，移动体验再上一层</li>
<li>双主角切换顺滑，两条线都有戏份</li>
<li>共生体战衣段落手感炸裂，是全作高光</li>
<li>格挡系统让战斗深度明显提升</li>
<li>地图扩大近一倍，区域风格有区分</li>
<li>PS5 无读盘过区，技术实现漂亮</li>
<li>画面处在 PS5 第一梯队</li>
</ul>
</div>
<div class="cons-box">
<h3>❌ 缺点</h3>
<ul>
<li>主线偏短，全收集时长明显少于一代</li>
<li>支线数量少、设计偏平淡</li>
<li>战衣技能被削弱，换装差异感下降</li>
<li>后期敌人种类重复，战斗套路化</li>
<li>PC 移植首发优化不稳</li>
<li>部分剧情转折略显仓促</li>
</ul>
</div>
</div>

<div class="section-label">💬 龙兄点评</div>
<div class="desc-box">
<p>更强、更快、更爽，但也更短——这大概是我对它的总评。</p>
<p>先说好的。蛛丝翼一展开，整个移动逻辑就变了：以前是贴着楼荡，现在是能借气流一路爬到高空再俯冲下来，皇后区和布鲁克林那种矮楼区的体验跟曼哈顿完全不同。格挡这个改动也关键，一代战斗到后期基本是「闪避 + 处决」一招鲜，这代你得看敌人的连段节奏，什么时候挡、什么时候闪，是有讲究的。至于共生体战衣那十几二十分钟——不用多说，玩过就知道，触手扫出去那一下的反馈值回票价。</p>
<p>问题是它结束得太快。主线 17 个小时，我还想多待会儿就没了；支线做得也明显不如一代用心，数量少、设计平，很多就是「换个地方清据点」。战衣倒是给到 60 多套，但这代把战衣技能砍弱了，换装更多是换个外观而不是换套打法，这点挺可惜。</p>
<p><strong>适合人群：</strong>玩过前两作、想看剧情收束、追求战斗手感的玩家。</p>
<p><strong>不适合：</strong>没玩过前作的新玩家（情感点会大量流失）、期待长流程与大体量支线的玩家。</p>
</div>
""",
}


SHOT_CAPTIONS = {
    "marvels-spider-man-remastered": [
        "漫威蜘蛛侠 重制版 实机截图 1",
        "漫威蜘蛛侠 重制版 实机截图 2",
        "漫威蜘蛛侠 重制版 实机截图 3",
        "漫威蜘蛛侠 重制版 实机截图 4",
        "漫威蜘蛛侠 重制版 实机截图 5",
        "漫威蜘蛛侠 重制版 实机截图 6",
    ],
    "marvels-spider-man-2": [
        "漫威蜘蛛侠 2 实机截图 1",
        "漫威蜘蛛侠 2 实机截图 2",
        "漫威蜘蛛侠 2 实机截图 3",
        "漫威蜘蛛侠 2 实机截图 4",
        "漫威蜘蛛侠 2 实机截图 5",
        "漫威蜘蛛侠 2 实机截图 6",
    ],
}


def hero_block(cfg):
    w, h = cfg["cover_wh"]
    slug = cfg["slug"]
    cover = (
        f'<div class="detail-cover" data-lightbox data-caption="{cfg["zh"]}" '
        f'data-src="../img/games/{slug}-cover.webp">'
        f'<img width="{w}" height="{h}" src="../img/games/{slug}-cover.webp" '
        f'alt="{cfg["zh"]} 封面" loading="lazy" decoding="async"></div>'
    )
    badges = "\n".join(f"<span>{b}</span>" for b in cfg["badges"])
    rows = "".join(f"<tr><th>{k}</th><td>{v}</td></tr>\n" for k, v in cfg["table"])
    return (
        '<div class="detail-hero">\n'
        f"{cover}"
        '<div class="game-title-wrap">\n'
        f"<h1>{cfg['zh']}</h1>\n"
        '<div class="bm-bar"><button class="bm-btn" type="button" data-bm-btn aria-pressed="false" title="收藏这篇文章（本地保存，无需登录）"><svg class="bm-star" viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/></svg><span class="bm-label">收藏</span></button></div>\n'
        f'<span class="en-title">{cfg["en"]}</span>\n'
        '<div class="game-meta">\n'
        '<span class="badge platform">🎮 PS5</span>\n'
        '<span class="badge status-completed">✅ 已通关</span>\n'
        f"{badges}\n"
        "</div>\n"
        '<div class="table-wrapper">\n'
        '<table class="info-table">\n'
        f"{rows}"
        "</table>\n"
        "</div>\n"
        '<div class="rating">\n'
        "<span>龙兄评分：</span>\n"
        f"<span>{cfg['stars']}</span>\n"
        f"<span style=\"color:var(--gm)\">{cfg['score']}</span>\n"
        "</div>\n"
        "</div>\n"
        "</div>\n"
    )


def shots_block(slug, zh):
    out = []
    for i, cap in enumerate(SHOT_CAPTIONS[slug], start=1):
        src = f"../img/games/{slug}-shot-{i}.webp"
        out.append(
            f'<div class="screenshot-item" data-lightbox data-caption="{cap}" '
            f'data-src="{src}">'
            f'<img width="1600" height="900" src="{src}" alt="{cap}" '
            f'loading="lazy" decoding="async"></div>'
        )
    return "\n".join(out)


def build(cfg):
    s = open(TPL, encoding="utf-8").read()
    slug, zh, en = cfg["slug"], cfg["zh"], cfg["en"]

    title_new = f"{zh} | 龙兄的游戏库2026实测避坑｜龙兄知识库"
    kw_new = f"{zh} | 龙兄的游戏库,2026实测避坑,实测溯源,龙兄知识库"
    desc_new = (
        f"{zh} | 龙兄的游戏库2026实测避坑：实测溯源、实操图文、避坑指南。"
        f"适合{zh} | 龙兄的游戏库爱好者与从业者参考，掌握核心要点、规避常见误区。"
    )
    url_new = f"https://longxiong.vip/games/{slug}.html"
    tw_title_new = f"{zh} | 龙兄的游戏库"

    pairs = [
        (f"<title>{T_TITLE_OLD}</title>", f"<title>{title_new}</title>"),
        (
            f'<meta name="keywords" content="{T_KW_OLD}">',
            f'<meta name="keywords" content="{kw_new}">',
        ),
        (
            f'<meta name="description" content="{T_DESC_OLD}">',
            f'<meta name="description" content="{desc_new}">',
        ),
        (
            f'<link rel="canonical" href="{T_LD_URL_OLD}">',
            f'<link rel="canonical" href="{url_new}">',
        ),
        (
            f'<meta property="og:title" content="{T_TITLE_OLD}">',
            f'<meta property="og:title" content="{title_new}">',
        ),
        (
            f'<meta property="og:description" content="{T_DESC_OLD}">',
            f'<meta property="og:description" content="{desc_new}">',
        ),
        (
            f'<meta property="og:url" content="{T_LD_URL_OLD}">',
            f'<meta property="og:url" content="{url_new}">',
        ),
        (
            f'<meta name="twitter:title" content="{T_TW_TITLE_OLD}">',
            f'<meta name="twitter:title" content="{tw_title_new}">',
        ),
        (
            f'<meta name="twitter:description" content="{T_TW_DESC_OLD}">',
            f'<meta name="twitter:description" content="{cfg['tw_desc']}">',
        ),
        (f"<span>{T_ZH}</span>", f"<span>{zh}</span>"),
        (T_UPDATE_OLD, UPDATE_NEW),
        (f'"headline": "{T_TW_TITLE_OLD}"', f'"headline": "{tw_title_new}"'),
        (f'"url": "{T_LD_URL_OLD}"', f'"url": "{url_new}"'),
        (
            f'"description": "{T_TW_DESC_OLD}"',
            f'"description": "{cfg['tw_desc']}"',
        ),
    ]

    for old, new in pairs:
        n = s.count(old)
        assert n == 1, f"[精确替换] 命中 {n} 次（应为 1）: {old[:70]}"
        s = s.replace(old, new)

    # --- 正则块替换 ---
    # 1) detail-hero 整块
    hero_re = re.compile(
        r'<div class="detail-hero">.*?\n</div>\n\n(?=<div class="detail-section">)', re.S
    )
    assert len(hero_re.findall(s)) == 1, "detail-hero 块定位失败"
    s = hero_re.sub(lambda m: hero_block(cfg), s, count=1)

    # 2) detail-section 内容整块（锚点是唯一的 <!-- game:begin -->）
    sec_re = re.compile(
        r'(<div class="detail-section">\n).*?(\n\n</div>\n\n)(?=<!-- game:begin -->)',
        re.S,
    )
    assert len(sec_re.findall(s)) == 1, "detail-section 块定位失败"
    body = cfg["sections"].replace("__SHOTS__", shots_block(slug, zh))
    s = sec_re.sub(lambda m: m.group(1) + body.strip("\n") + m.group(2), s, count=1)

    # 3) 剥掉模板自带的 game/related 块，交给 apply 脚本按新页面重新注入
    strip_re = re.compile(
        r"<!-- game:begin -->.*?<!-- game:end -->\n<!-- related:begin -->.*?<!-- related:end -->\n",
        re.S,
    )
    assert len(strip_re.findall(s)) == 1, "game/related 块剥离失败"
    s = strip_re.sub("", s, count=1)

    # 4) footer 资料来源段
    src_re = re.compile(
        r'(<a id="sources" class="src-anchor"></a>资料来源：).*?（外部链接 [\d-]+ 核验可达）'
    )
    assert len(src_re.findall(s)) == 1, "资料来源段定位失败"
    s = src_re.sub(lambda m: m.group(1) + cfg["sources"], s, count=1)

    # --- 收尾校验 ---
    assert T_ZH not in s, f"仍残留模板标题「{T_ZH}」"
    assert T_EN not in s, f"仍残留模板英文名「{T_EN}」"
    assert "wukong" not in s, "仍残留 wukong 路径/文件名"
    assert s.count("__SHOTS__") == 0
    assert "<!-- game:begin -->" not in s and "<!-- related:begin -->" not in s

    out = os.path.join(ROOT, "static", "games", f"{slug}.html")
    open(out, "w", encoding="utf-8").write(s)
    print(f"✅ 已生成 {os.path.relpath(out, ROOT)}  ({len(s)} 字节)")


def main():
    for cfg in (SP1, SP2):
        build(cfg)
    print("\n提示：内联 <script> 未做任何改动，CSP 哈希与模板一致，无需重算。")


if __name__ == "__main__":
    sys.exit(main())
