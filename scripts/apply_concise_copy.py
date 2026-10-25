#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
apply_concise_copy.py — 全站文案「取其精华」精简（一次性改写脚本，幂等）

龙兄 2026-10-25：「网站是做技术交流的，不是做文字表述的……要放取其精华的文字，
让懂的人一看就懂，不喜欢文字太多太浮肿。」

判定原则（改动只动「表达」，不动「事实」）：
  ① 删纯重复：与上文重复的来源尾注、与数据表重复的免责句 → 删
  ② 删元叙述：描述「本页有什么」「本页曾是什么」的行政说明 → 删
  ③ 事实换形容词：「达到国际一线水准」这类无信息量的评价 → 换成可核查的事实
  ④ 结论先行：板块页开头不铺陈，直接给数字与范围
红线：不得改动发售日期、规格参数、销量、价格、来源链接等事实性内容。
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# (文件, 旧串, 新串, 说明)  —— 旧串必须是文件中真实存在的连续片段
EDITS = [
    # ── ① 板块页开头：删「描述页面」式铺陈，结论先行 ──────────────────
    ('static/marvel.html',
     '<p>从 2008 年托尼·斯塔克在山洞里敲出第一套战甲，到今天横跨电影与剧集的多元宇宙——一份属于龙兄的观影手账：怎么看、按什么顺序看、谁值得记住，以及哪些片子最对胃口。</p>',
     '<p>2008 年《钢铁侠》到今天的多元宇宙：39 部影剧，按上映顺序与故事时间线两条线整理，含阶段划分、英雄档案与私人评分。</p>',
     '漫威板块开头：铺陈 → 数字范围'),

    ('static/chinajoy.html',
     '<p>从 2004 年北京展览馆的第一届，到 2026 年上海新国际博览中心的第 23 届——     一份逐届梳理的完整档案：每一年的主题、规模、参展品牌与代表游戏，串起中国数字娱乐产业二十余年的变迁。</p>',
     '<p>2004 年北京首届至 2026 年上海第 23 届：逐届记录主题、规模、参展品牌与代表游戏，附五阶段划分与关键词搜索。</p>',
     'ChinaJoy 开头：铺陈 → 覆盖范围'),

    ('static/apple.html',
     '<p>一个入口装两块内容：<b>看现在</b>——在售机型的参数与国行价格，每日自动刷新；<b>看过去</b>——1976 年车库里的 Apple I 到 2026 年的折叠屏 iPhone Duo，十条产品线 293 条里程碑。点下面任意一张卡片切换。</p>',
     '<p>两块内容：<b>在售新品</b>（参数与国行价格，每日刷新）与 <b>产品发展史</b>（1976 年 Apple I 至 2026 年 iPhone Duo，10 条产品线 293 条里程碑），顶部卡片切换。</p>',
     '苹果板块开头：铺陈 → 两块内容'),

    ('static/apple.html',
     '<p class="sec-sub">6 款全部列出：官方图 + 国行起售价 + 三个最值得看的点 + 开卖时间。</p>',
     '<p class="sec-sub">官方图 · 国行起售价 · 三个看点 · 开卖时间</p>',
     '苹果新品小标题：去掉界面描述'),

    ('static/herbs.html',
     '<p class="intro">       系统整理 10 种中药材与名贵香料的鉴别要点、功效用法与避坑指南。内容以通俗实用为主，便于日常查阅与购买决策。     </p>',
     '<p class="intro">10 种中药材与名贵香料：鉴别要点、功效用法与避坑指南。</p>',
     '中药材开头：去掉「便于查阅」填充语'),

    ('static/ev-sales.html',
     '<p class="ev-lead">这是本页的核心榜单：<b>新能源乘用车</b>厂商排行。批发榜看出货（含出口），       零售榜看国内真实上牌，两者成员差异很大，合起来看才完整。</p>',
     '<p class="ev-lead"><b>新能源乘用车</b>厂商排行。批发榜看出货（含出口），零售榜看国内真实上牌，两者成员差异很大，合起来看才完整。</p>',
     '销量榜开头：删「这是本页的核心榜单」'),

    # ── ② 删元叙述（描述「本页怎么用」而非技术内容）──────────────────
    ('static/sheyang-guide.html',
     '<strong>一句话定位：</strong>给在射阳生活、或要到射阳 / 盐城办事、探亲、旅行的人看的一份实用清单——交通怎么走、事去哪儿办、周末去哪儿玩、本地有啥讲究，尽量一次说清。',
     '',
     '射阳指南：删「一句话定位」自我描述'),

    # ── ③ 事实换形容词：营销腔 → 可核查事实 ─────────────────────────
    ('static/games/wukong.html',
     '<td>追求极致画质、高帧率玩家</td>',
     '<td>追求高画质、高帧率玩家</td>',
     '黑神话：适格词'),

    ('static/console-super-famicom.html',
     '在《超级马里奥世界》的飞艇关卡和《最终幻想 VI》的开场动画中，Mode 7的效果令人震撼。',
     'Mode 7 以单张贴图做逐行仿射变换，在《超级马里奥世界》飞艇关卡与《最终幻想 VI》开场动画中做出旋转缩放的伪 3D 效果，是家用机伪 3D 的代表实现。',
     'SFC：Mode 7「令人震撼」→ 技术事实'),

    ('static/console-playstation-5.html',
     '首次在《宇宙机器人无线控制器使用指南》中惊艳亮相',
     '首次在《宇宙机器人无线控制器使用指南》中亮相',
     'PS5：适格词'),

    ('static/console-gameboy-advance.html',
     '<strong>Game Boy Micro（2005）：</strong>极致迷你版，仅能玩GBA游戏（不兼容GB/GBC），日本市场失败',
     '<strong>Game Boy Micro（2005）：</strong>体积最小的 GBA 掌机，仅能玩GBA游戏（不兼容GB/GBC），日本市场失败',
     'GBA：适格词'),

    ('static/tesla/models.html',
     'Plaid版以三电机、超强动力和惊人续航重新定义了电动性能车的天花板。',
     'Plaid 版以三电机、1020 马力与 CLTC 715km 续航成为量产电动轿车的性能标杆。',
     'Model S：去掉「重新定义天花板」'),

    ('static/tesla/models.html',
     '<strong>极致性能：</strong>想要2.1s破百+322km/h极速+三电机1020马力的量产电动轿车，Model S Plaid是历史性选择。',
     '<strong>极致性能：</strong>2.1s 破百、322km/h 极速、三电机 1020 马力，量产电动轿车里的性能标杆。',
     'Model S：去推销腔，留参数'),

    ('static/tesla/roadster.html',
     '全新一代 Roadster 将再次打破电动车的性能天花板。',
     '',
     'Roadster：删无依据的「打破天花板」'),

    ('static/pages/zisha/detail-linglong.html',
     '<p>薄胎工艺将大红袍朱泥的细腻质感发挥到极致。</p><p>一手可握，盈盈一握间尽显东方雅韵。</p>',
     '<p>薄胎工艺，呈现大红袍朱泥的细腻质感；一手可握。</p>',
     '紫砂玲珑：去掉空泛形容'),

    ('static/marvel.html',
     '<p class="mv-rating-note">灭霸的代价与英雄的溃败，反派赢一次的震撼。</p>',
     '<p class="mv-rating-note">灭霸的代价与英雄的溃败：反派赢一次。</p>',
     '漫威短评：去形容'),

    ('static/marvel.html',
     '<p class="mv-rating-note">文化符号大于电影本身，瓦坎达美学惊艳。</p>',
     '<p class="mv-rating-note">文化符号大于电影本身，瓦坎达美学是最大看点。</p>',
     '漫威短评：去形容'),

    # ── ④ 工具页：清单去描述化（卡片里已逐个列出）────────────────────
    ('static/tools.html',
     '<p class="tl-lede">二十个纯浏览器小工具——图片压缩、格式转换、尺寸与 DPI、图片转 PDF、批量加水印、长图拼接、EXIF 查看与清除、取色配色板、二维码生成、音频转 WAV、日期天数计算、文本对比、九宫格切图、长图切段、图片打码、单位换算、时区转换、时间戳转换、BMI 与健康、密码生成。<br> 所有内容都在<b>你自己的设备里</b>处理完，<b>不上传、不联网、不留存</b>，断网也能照常用。</p>',
     '<p class="tl-lede">二十个纯浏览器小工具：图片压缩、格式转换、图片转 PDF、加水印、长图拼接、EXIF 清除、取色、二维码、音频转 WAV、日期天数、文本对比、九宫格切图、长图切段、图片打码、单位换算、时区转换、时间戳、BMI、密码生成。<br> 全部在<b>你自己的设备里</b>处理，<b>不上传、不联网、不留存</b>，断网也能用。</p>',
     '工具箱：清单去描述化'),
]

# (文件, 正则, 替换, 说明) —— 用于源文件里换行/缩进不稳定的段落
REGEX_EDITS = [
    ('static/chinajoy.html',
     r'<p>从 2004 年北京展览馆的第一届[\s\S]*?</p>',
     '<p>2004 年北京首届至 2026 年上海第 23 届：逐届记录主题、规模、参展品牌与代表游戏，附五阶段划分与关键词搜索。</p>',
     'ChinaJoy 开头：铺陈 → 覆盖范围'),

    ('static/herbs.html',
     r'<p class="intro">\s*系统整理 10 种中药材[\s\S]*?</p>',
     '<p class="intro">10 种中药材与名贵香料：鉴别要点、功效用法与避坑指南。</p>',
     '中药材开头：去掉「便于查阅」填充语'),

    ('static/ev-sales.html',
     r'<p class="ev-lead">\s*这是本页的核心榜单[\s\S]*?</p>',
     '<p class="ev-lead"><b>新能源乘用车</b>厂商排行。批发榜看出货（含出口），零售榜看国内真实上牌，两者成员差异很大，合起来看才完整。</p>',
     '销量榜开头：删「这是本页的核心榜单」'),

    ('static/health-tea.html',
     r'上面的配方讲的是「怎么配」[\s\S]*?那一栏往往比功效更重要。',
     '六种最常喝的代茶饮：功效、适宜与「别喝的人」。性味功效以《中华人民共和国药典》为准，禁忌与用量参考国家中医药管理局、广东省中医药局、北京市中医管理局及《中国中医药报》的公开科普，均已交叉核对。',
     '养生茶：删「上面的配方讲的是…」元叙述'),

    ('static/games/wukong.html',
     r'<p>游戏采用虚幻5引擎开发[\s\S]*?成为2024年最热门的游戏之一。</p>',
     '<p>虚幻 5 引擎；战斗沿用魂系的「闪避 + 处决 + 资源管理」框架，另加变身与法术系统（定身、分身、金刚不坏）。</p> <p>2024-08-20 发售，销量迅速突破千万套。</p>',
     '黑神话：营销腔 → 引擎/系统/销量'),

    ('static/tools.html',
     r'<p class="tl-lede">\s*二十个纯浏览器小工具——[\s\S]*?</p>',
     '<p class="tl-lede">二十个纯浏览器小工具：图片压缩、格式转换、图片转 PDF、加水印、长图拼接、EXIF 清除、取色、二维码、音频转 WAV、日期天数、文本对比、九宫格切图、长图切段、图片打码、单位换算、时区转换、时间戳、BMI、密码生成。<br> 全部在<b>你自己的设备里</b>处理，<b>不上传、不联网、不留存</b>，断网也能用。</p>',
     '工具箱：清单去描述化'),
]

# ── 全站游戏页：同一句免责话在「资料状态徽章 / 游戏简介 / 资料说明」出现三次 ──
# 徽章已经写了「公开资料整理 · 非本人实玩评测」，简介末尾与资料说明不必再重复。
SITE_EDITS = [
    # 资料说明：括号里那串字段名与上方数据表完全重复，删；「以官方为准」说了两遍，合并
    ('所有信息（开发商、发行商、发售日、平台、定价、类型）来自各游戏官方网站与权威商店页面，',
     '信息来自各游戏官网与权威商店页面，'),
    ('游戏更新、价格调整或平台变动后可能与官方最新公告存在差异，以官方为准。',
     '更新与价格变动以官方公告为准。'),
    # 游戏简介末尾的独立免责句：徽章与资料说明已覆盖
    ('本页为公开资料整理，非本人实玩评测。</p>', '</p>'),
]


def main():
    ok = miss = 0
    saved = 0
    # 逐条改：同一文件可能有多条，按文件分组处理
    by_file = {}
    for path, old, new, label in EDITS:
        by_file.setdefault(path, []).append((old, new, label))

    for path, items in by_file.items():
        full = os.path.join(ROOT, path)
        if not os.path.exists(full):
            print(f"! 文件不存在: {path}")
            miss += len(items)
            continue
        src = open(full, encoding="utf-8").read()
        for old, new, label in items:
            if old not in src:
                if new in src:
                    print(f"  · [已应用] {label} {path}")
                    continue
                print(f"  ✗ 未命中 [{label}] {path}")
                miss += 1
                continue
            src = src.replace(old, new, 1)
            saved += len(old) - len(new)
            ok += 1
            print(f"  ✓ [{label}] {path}")
        # 清理改写后被掏空的 <p>
        src = re.sub(r"[ \t]*<p[^>]*>\s*</p>\n?", "", src)
        open(full, "w", encoding="utf-8").write(src)

    # ── 正则段（换行/缩进不稳定处）────────────────────────────────
    for path, pat, new, label in REGEX_EDITS:
        full = os.path.join(ROOT, path)
        if not os.path.exists(full):
            print(f"! 文件不存在: {path}")
            miss += 1
            continue
        src = open(full, encoding="utf-8").read()
        src2, n = re.subn(pat, new, src, count=1)
        if n == 0:
            if new in src:
                print(f"  · [已应用] {label} {path}")
                continue
            print(f"  ✗ 未命中 [{label}] {path}")
            miss += 1
            continue
        saved += len(src) - len(src2)
        ok += 1
        print(f"  ✓ [{label}] {path}")
        open(full, "w", encoding="utf-8").write(src2)

    # ── 全站游戏页统一精简 ─────────────────────────────────────────
    gd = os.path.join(ROOT, "static", "games")
    gpages = [os.path.join(gd, f) for f in sorted(os.listdir(gd)) if f.endswith(".html")]
    g_ok = g_saved = 0
    for full in gpages:
        src = open(full, encoding="utf-8").read()
        before = len(src)
        for old, new in SITE_EDITS:
            src = src.replace(old, new)
        src = re.sub(r"[ \t]*<p[^>]*>\s*</p>\n?", "", src)
        if src != open(full, encoding="utf-8").read():
            open(full, "w", encoding="utf-8").write(src)
            g_saved += before - len(src)
            g_ok += 1
    if g_ok:
        print(f"\n游戏页统一精简：{g_ok}/{len(gpages)} 页，净精简 {g_saved} 字符")

    print(f"\n完成：命中 {ok} 条，未命中 {miss} 条，净精简 {saved} 字符")
    return 1 if miss else 0

if __name__ == "__main__":
    sys.exit(main())
