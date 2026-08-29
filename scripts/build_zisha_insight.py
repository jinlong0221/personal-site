#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_zisha_insight.py — 给 40 把紫砂作品生成「深度解读」数据

背景：紫砂 40 个详情页原本只是「图片 + 规格表 + 模板化文案」，属于调研中
发现的「参数罗列型」页面——有数据，却没有"为什么/怎么用/值在哪"。

本脚本把页面里已有的真实规格（泥料 / 容量 / 工艺 / 系列 / 标签）翻译成
读者真正用得上的判断依据：适什么茶、几个人用、怎么养、器型什么来头、
工艺凭什么值这个价。

所有解读均来自紫砂领域的通用工艺常识（泥料收缩率与气孔结构、适茶性、
成型技法、经典器型典故），按"泥料 × 容量 × 器型 × 工艺"组合推导，
不做主观臆造，也不写"工艺精湛、值得收藏"这类空话。

用法：
  python3 scripts/build_zisha_insight.py            # 写入 static/data/zisha-insight.json
  python3 scripts/build_zisha_insight.py --check    # 只打印统计与抽样，不写文件
"""
import glob
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC = os.path.join(ROOT, "static")
DETAIL_DIR = os.path.join(STATIC, "pages", "zisha")
OUT = os.path.join(STATIC, "data", "zisha-insight.json")

# ---------------------------------------------------------------------------
# 泥料知识库
# key   : 归一化的泥料名（页面写法经 normalize_clay 映射后）
# 每条含：透气 适茶 养（养护/养成特点）
# 内容取自紫砂工艺通识：朱泥收缩大、段泥透气、紫泥适茶广、底槽清含云母…
# ---------------------------------------------------------------------------
CLAY = {
    "大红袍朱泥": {
        "breath": "胎质致密、结晶度高",
        "tea": "聚香扬香能力最强，首选乌龙（岩茶、凤凰单丛、铁观音）与红茶",
        "care": "收缩率大（约 18–30%）、怕温差，冬季务必先温水淋浴预热再泡，骤冷骤热易惊裂；养成后红润透亮、见效快",
    },
    "朱泥": {
        "breath": "胎质细腻致密",
        "tea": "扬香见长，适合乌龙、岩茶、红茶",
        "care": "收缩率偏大，冬季需温水预热防惊裂；养成后色泽红润",
    },
    "原矿紫泥": {
        "breath": "双气孔结构，透气与保温平衡",
        "tea": "适茶性最广——普洱（生熟皆宜）、乌龙、红茶都能压得住",
        "care": "泥性温和好养，养成后色泽由棕红转沉稳深栗",
    },
    "紫泥": {
        "breath": "双气孔结构，透气适中",
        "tea": "适茶性广，普洱、乌龙、红茶皆宜",
        "care": "泥性温和，养成后色泽沉稳",
    },
    "老紫泥": {
        "breath": "陈腐时间更长，气孔结构更疏松",
        "tea": "适茶性广，尤其适合普洱与老茶",
        "care": "陈腐充分、吃茶快，泡养见效比新紫泥更快",
    },
    "原矿清水泥": {
        "breath": "纯正紫泥不拼配，透气性纯正",
        "tea": "适茶性广，不夺茶味，普洱、乌龙、红茶皆可",
        "care": "无调配、泥性纯，养成后色泽沉静统一",
    },
    "原矿天星泥": {
        "breath": "多矿共生，颗粒层次丰富、透气性佳",
        "tea": "适合普洱熟茶、黑茶、老白茶——能吸附堆味、让汤感更醇厚",
        "care": "颗粒感会在泡养中逐渐显现，养成变化明显",
    },
    "天星泥": {
        "breath": "多矿共生，颗粒层次丰富",
        "tea": "适合普洱熟茶、黑茶、老白茶",
        "care": "养成后颗粒渐显、包浆温润",
    },
    "本山绿泥": {
        "breath": "段泥系，透气性极佳、不夺香",
        "tea": "清香型茶的首选——绿茶、白茶、生普，能保住鲜爽不闷熟",
        "care": "易养出清雅包浆，色泽由浅淡转温润",
    },
    "黄金段泥": {
        "breath": "段泥类，透气性好",
        "tea": "适合绿茶、白茶、生普等清香型茶",
        "care": "养壶变化明显，色泽由金黄渐转深沉温润",
    },
    "原矿降坡泥": {
        "breath": "段泥与紫泥过渡带泥料，透气性佳",
        "tea": "适合白茶、生普、绿茶",
        "care": "含铁适中，养成后包浆温润、色泽渐深",
    },
    "降坡泥": {
        "breath": "透气性佳",
        "tea": "适合白茶、生普、绿茶",
        "care": "养成后包浆温润",
    },
    "底槽清": {
        "breath": "紫泥优质品种，含云母颗粒、透气性好",
        "tea": "适茶性广，普洱与乌龙表现尤佳",
        "care": "养成后温润如玉，云母颗粒会随泡养逐渐显出",
    },
    "原矿红皮龙": {
        "breath": "稀有泥料，胎质红润",
        "tea": "适合乌龙、红茶，衬得住红浓汤色",
        "care": "存世量少，养成后红润油亮",
    },
    "红皮龙": {
        "breath": "稀有泥料，胎质红润",
        "tea": "适合乌龙、红茶",
        "care": "存世量少，养成后红润",
    },
}

# 页面写法 → 归一化泥料名（含"多矿配比"等后缀、简称等）
CLAY_ALIAS = [
    (r"大红袍", "大红袍朱泥"),
    (r"原矿天星泥", "原矿天星泥"),
    (r"^天星泥", "天星泥"),
    (r"本山绿泥|雅青", "本山绿泥"),
    (r"黄金段泥", "黄金段泥"),
    (r"底槽清", "底槽清"),
    (r"降坡泥", "原矿降坡泥"),
    (r"红皮龙", "原矿红皮龙"),
    (r"清水泥", "原矿清水泥"),
    (r"老紫泥", "老紫泥"),
    (r"朱泥", "大红袍朱泥"),
    (r"紫泥", "原矿紫泥"),
]

# ---------------------------------------------------------------------------
# 容量 → 使用场景
# ---------------------------------------------------------------------------
def scene_of(ml):
    if ml <= 0:
        return ""
    if ml <= 200:
        return f"{ml}ml 属小品，一人独饮或两人对坐的功夫茶节奏，投茶量小、出汤快，最能试出茶的底子"
    if ml <= 300:
        return f"{ml}ml 是 2–3 人对饮的常用规格，兼顾聚香与出汤量，日常主泡壶多在这一档"
    if ml <= 400:
        return f"{ml}ml 适合 3–4 人，茶汤降温慢，适合慢泡的普洱、老白茶"
    return f"{ml}ml 属大品，4 人以上或办公日常用，保温好、续杯方便，代价是香气聚拢不如小品"

# ---------------------------------------------------------------------------
# 器型 / 形制典故
# ---------------------------------------------------------------------------
SHAPE = {
    "掇只": "掇只是邵大亨的代表作，壶身浑圆饱满、重心压得极低，行内有「千金壶王」的说法——说的就是这路器型看似简单、实则极难做得精神",
    "西施": "西施壶是经典的美人壶，壶身圆润、截盖与壶口严丝合缝，短嘴倒把，握持重心贴手",
    "传炉": "传炉属方器经典，四方壶身配四足鼎立，取「薪火相传」之意",
    "方器": "方器不走圆器的拍身筒路子，而是泥片镶接成型，对角、对线、对面要求极严，同款里能做得挺括的不多",
    "圆器": "圆器靠拍身筒成型，讲究「圆、稳、匀、正」——正因为形制简单，圆的纯度最藏不住毛病",
    "盖杯": "盖杯胜在实用——带盖能保温防尘，办公桌上随手可及，不必像壶那样讲究出汤节奏",
    "葫芦": "取葫芦造型，谐音「福禄」，是传统吉祥题材里最讨喜的一路",
    "如意": "如意纹属吉祥题材，云头回卷的线条讲究连绵不断，寓意顺遂",
    "龙纹": "龙纹是紫砂装饰里的重工题材，鳞爪须发都要交代清楚，很吃刻绘功力",
    "石瓢": "石瓢是曼生十八式一路的经典，身筒为梯形、桥钮直流，线条干净利落，久看不腻",
    "景舟石瓢": "石瓢经顾景舟重新推敲过身筒、流与把的比例，后世称「景舟石瓢」，是当代石瓢的标杆",
    "仿古": "仿古壶取商周青铜器的鼓腹造型，压盖严密、腹身饱满——这路器型顾景舟做得最透，是圆器里见真功夫的一路",
    "扁腹": "属清末经典一脉，黄玉麟所制扁腹（又称汉扁）为其中代表：壶身压得极扁、桥钮横跨，线条简到不能再简",
    "莲子": "莲子壶取莲子之形，壶身圆润饱满、多作平盖，是清中期流传下来的传统形制",
    "大肚罗汉": "容天取大肚罗汉之意，壶身圆硕能容，是佛教题材里最讨喜的一路",
    "汉瓦": "汉瓦壶取秦汉瓦当之形，圆筒身配平盖，质朴大气；素面宽整，很适合做陶刻的载体",
    "合欢": "合欢属曼生十八式之一，壶身上下两片相合、腰间一道线，取「和合欢乐」之意",
    "双圈": "桥钮上作双圈，是这一路器型的识款特征",
    "玲珑": "小品类，壶身小巧，适合一人独饮细品",
    "宫灯": "宫灯取宫灯之形，多做六方或筋纹，六面要对称、棱线要挺",
    "思亭": "思亭是朱泥小品里的经典形制，壶身修长秀气，历来是工夫茶的主泡小壶",
    "一粒珠": "一粒珠属圆器经典，壶身浑圆如珠，形制极简",
    "竹韵": "竹题材，以竹节入壶、流把多作竹节状，取其清雅有节之意",
    "生肖": "生肖纪念题材，多为当年限量发行，年份本身就是看点",
    "套具": "成组套具，壶与杯形制统一，讲究整体的呼应",
    "挂盘": "挂盘不是壶，属紫砂摆件一路，以泥板作画，供陶刻或泥绘施展",
    "菱花": "菱花纹属筋纹器一路，壶身按等分起棱，要求每一瓣都完全一致",
    "紫气东来": "「紫气东来」取老子过函谷关的典故，是传统吉祥题材里气最正的一路",
    "前程似锦": "以奔马喻「前程似锦」，属生肖纪念一路，题材讨喜、适合赠礼",
    "和合": "取「和合」之意，成双成对的题材，多用于套具与赠礼场景",
}

# 系列 → 归类说明
SERIES = {
    "经典壶型": "属经典壶型一脉，器型经过上百年筛选留下，形制有出处可考",
    "盖杯": "属盖杯系列，走的是日常实用路线，而非纯观赏收藏",
    "朱泥大红袍": "属朱泥大红袍系列，泥料本身才是这一路的主角——朱泥收缩大、成品率低，能成器的都是挑出来的",
    "天星泥方器": "属天星泥方器系列，多矿共生的颗粒感配上方器的挺括棱线，是这路的看头",
    "本山绿泥": "属本山绿泥系列，泥色清雅是本钱，配素器最能显出泥料本身的味道",
    "套具": "属套具系列，讲求壶与杯的形制统一，成组使用时的整体感是主要考量",
    "生肖": "属生肖系列，按年份限量，纪念意义大于日常使用",
    "刻绘": "属刻绘艺术一路，陶刻是主角——字画刻在生坯上，烧成后与壶身一体，非后加",
    "柴烧": "属柴烧系列，柴窑中落灰在高温下自然成釉，每一件的釉色走向都不同，不可复制",
    "特别款": "属特别定制款，形制不循常规，多为特定题材或纪念用途",
}

# ---------------------------------------------------------------------------
# 工艺 → 价值与鉴别
# ---------------------------------------------------------------------------
CRAFT = {
    "拍打成型": "全手工拍打成型——泥片围身筒后靠拍子一下下打出弧度，内壁会留下手拍的螺旋纹与泥片接缝，这是与模具壶最直观的区别",
    "刻绘": "附陶刻装饰。陶刻是紫砂「文人壶」的重要载体，字画刻在生坯上，烧成后与壶身一体，非后加",
    "暗刻": "暗刻工艺——刻后再填泥，纹样隐在胎体里，需侧光才看得出层次",
    "雕刻": "带雕刻装饰，属于工重于素的一路，纹样的立体感是主要看点",
    "柴烧": "柴烧自然釉——柴窑中落灰在高温下自然成釉，每把的釉色走向都不同，不可复制",
    "全手工": "全手工制作，不借模具。鉴别看三点：内壁的手工痕迹、泥片接缝、以及壶口的规整度——全手工不会像模具壶那样规整得毫无破绽",
}


def normalize_clay(raw):
    s = (raw or "").strip()
    if not s:
        return ""
    for pat, name in CLAY_ALIAS:
        if re.search(pat, s):
            return name
    return s


def parse_ml(raw):
    m = re.search(r"(\d+)\s*ml", (raw or ""), re.I)
    return int(m.group(1)) if m else 0


def pick_series_note(series):
    for k, v in SERIES.items():
        if k in (series or ""):
            return v
    return ""


def pick_shape_notes(tags, series, title=""):
    """从标签、系列与标题里挑出适用的器型典故，最多 2 条。

    标题也要参与匹配：像「过桥扁腹」的标签只有「清末经典 / 黄玉麟之作」，
    器型词其实写在标题里。
    """
    out = []
    src = " ".join(tags) + " " + (series or "") + " " + (title or "")
    for k, v in SHAPE.items():
        if k in src and v not in out:
            out.append(v)
        if len(out) >= 2:
            break
    return out


def pick_craft_note(craft):
    c = craft or ""
    for k, v in CRAFT.items():
        if k in c:
            return v
    return ""


def extract(path):
    h = open(path, encoding="utf-8").read()
    spec = {}
    m = re.search(r'<table class="spec-table".*?</table>', h, re.S)
    if m:
        for r in re.finditer(
            r"<tr>\s*<t[dh][^>]*>([^<]{1,10})</t[dh]>\s*<t[dh][^>]*>([^<]{1,40})</t[dh]>",
            m.group(0),
        ):
            spec[r.group(1).strip()] = r.group(2).strip()
    pills = {}
    for mm in re.finditer(
        r'<span class="meta-pill">.{0,4}\s*([^：:]{1,6})[：:]\s*([^<]{1,30})', h
    ):
        pills[mm.group(1).strip()] = mm.group(2).strip()
    tags = [mm.group(1).strip() for mm in
            re.finditer(r'<span class="tag">([^<]{1,20})</span>', h)]
    t = re.search(r"<title>([^<]+)</title>", h)
    title = t.group(1).split("|")[0].strip() if t else ""

    clay_raw = spec.get("泥料") or pills.get("泥料", "")
    cap_raw = spec.get("容量") or pills.get("容量", "")
    craft = spec.get("工艺") or pills.get("工艺", "")
    series = spec.get("系列") or pills.get("系列", "")
    return {
        "title": title,
        "clay_raw": clay_raw,
        "clay": normalize_clay(clay_raw),
        "cap_raw": cap_raw,
        "ml": parse_ml(cap_raw),
        "craft": craft,
        "series": series,
        "tags": tags,
    }


def build_insight(d):
    """把规格翻译成解读。缺哪个维度就省略哪个，不编造。"""
    rows = []
    clay = CLAY.get(d["clay"])

    if clay:
        tea = f"{d['clay']}{'（' + d['clay_raw'] + '）' if d['clay_raw'] and d['clay_raw'] != d['clay'] else ''}：{clay['breath']}，{clay['tea']}"
        rows.append({"k": "适什么茶", "v": tea})
        rows.append({"k": "养壶要点", "v": clay["care"]})

    scene = scene_of(d["ml"])
    if scene:
        rows.append({"k": "什么场合用", "v": scene})

    shapes = pick_shape_notes(d["tags"], d["series"], d["title"])
    if shapes:
        rows.append({"k": "器型说", "v": "；".join(shapes)})

    series_note = pick_series_note(d["series"])
    if series_note and not shapes:
        rows.append({"k": "所属系列", "v": series_note})

    craft_note = pick_craft_note(d["craft"])
    if craft_note:
        rows.append({"k": "工艺与鉴别", "v": craft_note})

    return rows


def main():
    check_only = "--check" in sys.argv
    files = sorted(glob.glob(os.path.join(DETAIL_DIR, "detail-*.html")))
    out = {}
    missing_clay = []
    for f in files:
        d = extract(f)
        rows = build_insight(d)
        if not rows:
            continue
        if not d["clay"]:
            missing_clay.append((d["title"], d["clay_raw"]))
        key = "/pages/zisha/" + os.path.basename(f)
        out[key] = {
            "title": d["title"],
            "spec": {
                "泥料": d["clay_raw"],
                "容量": d["cap_raw"],
                "工艺": d["craft"],
                "系列": d["series"],
            },
            "rows": rows,
        }

    print(f"紫砂作品页: {len(files)}")
    print(f"生成解读:   {len(out)}")
    print(f"未识别泥料: {len(missing_clay)}")
    for t, c in missing_clay[:10]:
        print(f"   - {t}: {c!r}")

    if not check_only:
        json.dump(out, open(OUT, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        print(f"已写入 {OUT}")

    print("\n=== 抽样 ===")
    for k in list(out)[:3]:
        print(f"\n{k}  [{out[k]['title']}]")
        for r in out[k]["rows"]:
            print(f"   · {r['k']}：{r['v'][:88]}")


if __name__ == "__main__":
    main()
