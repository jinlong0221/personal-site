#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_game_calendar_covers.py — 为「游戏发售日历」页补齐封面图（占位图，非 AI / 非版权图）。

做法（与 scripts/build_game_covers.py 同源思路，且复用其已生成的 6 张日历封面）：
  - 用 Pillow 程序化绘制**文字封面占位图**：暗底 + 金色标题 + 英文名 + 发售信息。
  - 官方美术图有版权、不可随意取用，故只用确定性绘制的占位图；拿到授权素材后可直接覆盖同名文件。
  - 同时把 <img class="cal-cover" src="img/games/<slug>-cover.webp" data-rsp="1"> 注入到
    game-calendar.html 的每个发售日历卡片 / 史低价卡片顶部，并接全站响应式图管线。

单一数据源：GAMES 列表（name=页面卡片里的精确显示名，slug=封面文件名，zh/en/meta=封面文案）。
生成与注入都用同一份映射，保证文件名与卡片一一对应；脚本幂等（封面已存在则跳过、HTML 已注入则跳过）。

用法：
  python3 scripts/build_game_calendar_covers.py            # 生成缺失封面 + 注入 <img>
  python3 scripts/build_game_calendar_covers.py --covers-only
  python3 scripts/build_game_calendar_covers.py --inject-only
"""
import glob
import os
import re
import sys

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMG_DIR = os.path.join(ROOT, "static", "img", "games")
CAL_HTML = os.path.join(ROOT, "static", "game-calendar.html")

W, H = 1200, 630
BG_TOP = (20, 20, 20)
BG_BOTTOM = (34, 32, 30)
GOLD = (201, 168, 76)
MUTED = (150, 145, 135)
WHITE = (232, 226, 214)

# name=页面里的精确显示名；slug=封面文件名（不含 -cover.webp）；zh/en/meta=封面文案
GAMES = [
    # —— 发售日历（33）——
    ("Marvel Tokon: Fighting Souls", "marvel-tokon-fighting-souls", "漫威 Tokon 格斗", "Marvel Tokon: Fighting Souls", "2026-08-06 发售 · PS5 / PC"),
    ("Metal Gear Solid: Master Collection Vol. 2", "mgs-master-collection-2", "合金装备 大师合集2", "Metal Gear Solid: Master Collection Vol. 2", "2026-08-27 发售 · 全平台"),
    ("Star Wars Zero Company", "star-wars-zero-company", "星战 零号公司", "Star Wars Zero Company", "2026-08-27 发售 · PS5 / Xbox / PC"),
    ("Resonance: A Plague Tale Legacy", "resonance-plague-tale-legacy", "瘟疫传说 前传", "Resonance: A Plague Tale Legacy", "2026-08-27 发售 · PS5 / Xbox / PC"),
    ("The Blood of Dawnwalker", "blood-of-dawnwalker", "破晓行者之血", "The Blood of Dawnwalker", "2026-09-03 发售 · PS5 / Xbox / PC"),
    ("Marvel's Wolverine", "marvels-wolverine", "漫威金刚狼", "Marvel's Wolverine", "2026-09-15 发售 · PS5 独占"),
    ("LEGO Batman: Legacy of the Dark Knight", "lego-batman-dark-knight", "乐高蝙蝠侠 黑暗骑士传奇", "LEGO Batman: Legacy of the Dark Knight", "2026-09-18 发售 · 全平台"),
    ("Fire Emblem: Fortune's Weave", "fire-emblem-fortunes-weave", "火焰纹章 命运织线", "Fire Emblem: Fortune's Weave", "2026-09-17 发售 · Switch 2"),
    ("Silent Hill: Townfall", "silent-hill-townfall", "寂静岭 崩塌", "Silent Hill: Townfall", "2026-09-24 发售 · PS5 / PC"),
    ("Control Resonant", "control-resonant", "控制 共振", "Control Resonant", "2026-09-24 发售 · PS5 / Xbox / PC"),
    ("Ace Combat 8: Wings of Theve", "ace-combat-8", "皇牌空战8 色雷斯之翼", "Ace Combat 8: Wings of Theve", "待定 · PS5 / Xbox / PC"),
    ("Gears of War: E-Day", "gears-of-war-eday", "战争机器 黎明", "Gears of War: E-Day", "2026-10-06 发售 · Xbox / PC"),
    ("Castlevania: Belmont's Curse", "castlevania-belmonts-curse", "恶魔城 贝尔蒙特之咒", "Castlevania: Belmont's Curse", "2026-10-15 发售 · 全平台"),
    ("Call of Duty: Modern Warfare 4", "cod-modern-warfare-4", "使命召唤 现代战争4", "Call of Duty: Modern Warfare 4", "2026-10-23 发售 · 全平台"),
    ("Phantom Blade Zero", "phantom-blade-zero", "影之刃 零", "Phantom Blade Zero", "2026-10-29 发售 · PS5 / PC"),
    ("The Legend of Zelda: Ocarina of Time (Switch 2)", "zelda-ocarina-time-s2", "塞尔达传说 时之笛", "The Legend of Zelda: Ocarina of Time (Switch 2)", "2026-11-05 发售 · Switch 2"),
    ("Grand Theft Auto VI", "gta6", "侠盗猎车手6", "Grand Theft Auto VI", "2026-11-19 发售 · PS5 / Xbox"),
    ("Dragon Quest Monsters: The Withered World", "dq-monsters-withered", "勇者斗恶龙怪物篇", "Dragon Quest Monsters: The Withered World", "2026-12-03 发售 · PS5 / Switch"),
    ("Xenoblade Chronicles 3: Switch 2 Edition", "xenoblade-3-s2", "异度神剑3 Switch2版", "Xenoblade Chronicles 3: Switch 2 Edition", "2026-12-03 发售 · Switch 2"),
    ("Stranger Than Heaven", "stranger-than-heaven", "Stranger Than Heaven", "", "2027-01-15 发售 · PS5 / Xbox / PC"),
    ("Metroid Ravenous", "metroid-ravenous", "密特罗德 饕餮", "Metroid Ravenous", "2027-01-28 发售 · Switch 2"),
    ("Metro 2039", "metro-2039", "地铁2039", "Metro 2039", "2027-02-04 发售 · PS5 / Xbox / PC"),
    ("Tomb Raider: Legacy of Atlantis", "tomb-raider-atlantis", "古墓丽影 亚特兰蒂斯", "Tomb Raider: Legacy of Atlantis", "2027-02-12 发售 · 全平台"),
    ("God of War Laufey", "god-of-war-laufey", "战神 劳菲", "God of War: Laufey", "2027-02-16 发售 · PS5 独占"),
    ("Persona 4 Revival", "persona-4-revival", "女神异闻录4 重制版", "Persona 4 Revival", "2027-02-18 发售 · PS5 / Xbox / PC"),
    ("Fable", "fable", "神鬼寓言", "Fable", "2027-02-23 发售 · PS5 / Xbox / PC"),
    ("Exodus", "exodus", "Exodus", "", "2027-04-07 发售 · PS5 / Xbox / PC"),
    ("Final Fantasy VII: Revelation", "ff7-revelation", "最终幻想7 启示录", "Final Fantasy VII: Revelation", "待定 · 全平台"),
    ("Spyro: A Realm Beyond", "spyro-realm-beyond", "斯派罗 远方王国", "Spyro: A Realm Beyond", "待定 · 全平台"),
    ("Resident Evil: Veronica", "re-veronica", "生化危机 维罗妮卡", "Resident Evil: Veronica", "待定 · PS5 / Xbox / PC"),
    ("Pokémon Winds and Waves", "pokemon-winds-waves", "宝可梦 风云", "Pokémon Winds and Waves", "待定 · Switch 2"),
    ("State of Decay 3", "state-of-decay-3", "腐朽之都3", "State of Decay 3", "待定 · Xbox / PC"),
    ("Senua（Hellblade 续作）", "senua-hellblade-sequel", "塞努阿 地狱之刃续作", "Senua（Hellblade 续作）", "待定 · PS5 / Xbox / PC"),
    # —— 史低价（22）——
    ("The Witcher 3: Wild Hunt – 年度版", "witcher-3", "巫师3 狂猎 年度版", "The Witcher 3: Wild Hunt", "2015 · PC · Steam"),
    ("Stardew Valley", "stardew-valley", "星露谷物语", "Stardew Valley", "2016 · PC · Steam"),
    ("Grand Theft Auto V", "gta5", "侠盗猎车手5", "Grand Theft Auto V", "2013 · PC · Steam"),
    ("Cyberpunk 2077", "cyberpunk-2077", "赛博朋克2077", "Cyberpunk 2077", "2020 · PC · Steam"),
    ("Elden Ring", "elden-ring", "艾尔登法环", "Elden Ring", "2022 · PC · Steam"),
    ("Red Dead Redemption 2", "rdr2", "荒野大镖客2", "Red Dead Redemption 2", "2018 · PC · Steam"),
    ("Hades", "hades", "黑帝斯", "Hades", "2020 · PC · Steam"),
    ("Hollow Knight", "hollow-knight", "空洞骑士", "Hollow Knight", "2017 · PC · Steam"),
    ("Celeste", "celeste", "蔚蓝", "Celeste", "2018 · PC · Steam"),
    ("Dead Cells", "dead-cells", "死亡细胞", "Dead Cells", "2018 · PC · Steam"),
    ("Portal 2", "portal-2", "传送门2", "Portal 2", "2011 · PC · Steam"),
    ("Dark Souls III", "dark-souls-3", "黑暗之魂3", "Dark Souls III", "2016 · PC · Steam"),
    ("Sekiro: Shadows Die Twice", "sekiro", "只狼 影逝二度", "Sekiro: Shadows Die Twice", "2019 · PC · Steam"),
    ("DOOM Eternal", "doom-eternal", "毁灭战士 永恒", "DOOM Eternal", "2020 · PC · Steam"),
    ("Horizon Zero Dawn（PC 年度版）", "horizon-zero-dawn", "地平线 零之曙光", "Horizon Zero Dawn", "2017 · PC · Steam"),
    ("God of War（PC）", "god-of-war-pc", "战神", "God of War", "2018 · PC · Steam"),
    ("Monster Hunter: World", "mh-world", "怪物猎人 世界", "Monster Hunter: World", "2018 · PC · Steam"),
    ("Monster Hunter Rise", "mh-rise", "怪物猎人 崛起", "Monster Hunter Rise", "2021 · PC · Steam"),
    ("No Man's Sky", "no-mans-sky", "无人深空", "No Man's Sky", "2016 · PC · Steam"),
    ("Disco Elysium: Final Cut", "disco-elysium", "极乐迪斯科", "Disco Elysium", "2019 · PC · Steam"),
    ("Resident Evil Village", "re-village", "生化危机 村庄", "Resident Evil Village", "2021 · PC · Steam"),
    ("Baldur's Gate 3", "baldurs-gate-3", "博德之门3", "Baldur's Gate 3", "2023 · PC · Steam"),
]


def pick_font(size, bold=False):
    patterns = [
        "/System/Library/Fonts/STHeiti Medium.ttc",
        "/System/Library/Fonts/STHeiti Light.ttc",
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/Hiragino Sans GB.ttc",
        "/Library/Fonts/Arial Unicode.ttf",
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    ]
    for pat in patterns:
        for fp in glob.glob(pat):
            try:
                return ImageFont.truetype(fp, size, index=0)
            except Exception:
                continue
    return ImageFont.load_default()


def fit_font(draw, text, max_width, start_size, min_size, bold=False):
    size = start_size
    while size >= min_size:
        f = pick_font(size, bold)
        if draw.textlength(text, font=f) <= max_width:
            return f
        size -= 2
    return pick_font(min_size, bold)


def make_cover(slug, zh, en, meta):
    img = Image.new("RGB", (W, H), BG_TOP)
    d = ImageDraw.Draw(img)
    for y in range(H):
        t = y / (H - 1)
        r = int(BG_TOP[0] + (BG_BOTTOM[0] - BG_TOP[0]) * t)
        g = int(BG_TOP[1] + (BG_BOTTOM[1] - BG_TOP[1]) * t)
        b = int(BG_TOP[2] + (BG_BOTTOM[2] - BG_TOP[2]) * t)
        d.line([(0, y), (W, y)], fill=(r, g, b))
    d.rectangle([0, 0, W, 6], fill=GOLD)
    d.rectangle([0, H - 6, W, H], fill=GOLD)

    f_title = fit_font(d, zh, W * 0.86, start_size=88, min_size=40)
    tw = d.textlength(zh, font=f_title)
    d.text(((W - tw) / 2, H * 0.28), zh, font=f_title, fill=GOLD)

    if en and en.strip() and en.strip() != zh.strip():
        f_en = fit_font(d, en, W * 0.80, start_size=40, min_size=22)
        ew = d.textlength(en, font=f_en)
        d.text(((W - ew) / 2, H * 0.50), en, font=f_en, fill=WHITE)
        line_y = int(H * 0.60)
    else:
        line_y = int(H * 0.56)

    d.line([(W * 0.38, line_y), (W * 0.62, line_y)], fill=GOLD, width=2)

    f_meta = fit_font(d, meta, W * 0.84, start_size=34, min_size=20)
    mw = d.textlength(meta, font=f_meta)
    d.text(((W - mw) / 2, H * 0.66), meta, font=f_meta, fill=MUTED)

    note = "封面占位图 · 待补官方素材"
    f_note = pick_font(22)
    nw = d.textlength(note, font=f_note)
    d.text(((W - nw) / 2, H * 0.86), note, font=f_note, fill=(110, 106, 100))

    out = os.path.join(IMG_DIR, f"{slug}-cover.webp")
    img.save(out, "WEBP", quality=86)
    return out


def gen_covers(force=False):
    os.makedirs(IMG_DIR, exist_ok=True)
    n_new = n_skip = 0
    for name, slug, zh, en, meta in GAMES:
        dst = os.path.join(IMG_DIR, f"{slug}-cover.webp")
        if os.path.exists(dst) and not force:
            n_skip += 1
            continue
        p = make_cover(slug, zh, en, meta)
        n_new += 1
        print(f"  ✓ {os.path.basename(p)}  <- {name}")
    print(f"\n封面生成 {n_new} 张，跳过已存在 {n_skip} 张 → {IMG_DIR}")


def inject_imgs():
    html = open(CAL_HTML, encoding="utf-8").read()
    by_name = {name: slug for name, slug, *_ in GAMES}
    n_cal = n_price = n_skip = n_miss = 0

    def inject_into(block_re, card_open, img_tmpl):
        nonlocal html, n_cal, n_price, n_skip, n_miss
        # 逐卡处理：找到每张卡片的开标签，在其内首部插入封面 <img>
        out = []
        last = 0
        for m in re.finditer(card_open, html):
            out.append(html[last:m.end()])
            last = m.end()
            # 取出本卡后续一段以定位 c-name / p-name
            seg = html[m.end():m.end() + 600]
            nm = re.search(r'c-name">([^<]+)<', seg) or re.search(r'p-name">([^<]+)<', seg)
            if not nm:
                continue
            title = nm.group(1).strip()
            slug = by_name.get(title)
            if not slug:
                n_miss += 1
                print(f"  ! 未匹配封面：{title}")
                continue
            img = img_tmpl.format(slug=slug)
            if img in html:  # 已注入，幂等
                n_skip += 1
                continue
            out.append(img)
            if "cal-card" in card_open:
                n_cal += 1
            else:
                n_price += 1
        out.append(html[last:])
        html = "".join(out)
        return html

    html = inject_into(html, r'<div class="cal-card[^"]*"[^>]*>',
                      '<img class="cal-cover" src="img/games/{slug}-cover.webp" alt="" loading="lazy" data-rsp="1">\n')
    html = inject_into(html, r'<div class="price-card"[^>]*>',
                      '<img class="cal-cover price-cover" src="img/games/{slug}-cover.webp" alt="" loading="lazy" data-rsp="1">\n')

    open(CAL_HTML, "w", encoding="utf-8").write(html)
    print(f"\n注入封面 <img>：发售日历卡 {n_cal} / 史低价卡 {n_price}（已存在跳过 {n_skip}，未匹配 {n_miss}）")


def main():
    covers_only = "--covers-only" in sys.argv
    inject_only = "--inject-only" in sys.argv
    force = "--force" in sys.argv
    if not inject_only:
        gen_covers(force)
    if not covers_only:
        inject_imgs()


if __name__ == "__main__":
    main()
