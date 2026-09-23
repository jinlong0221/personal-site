#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
guard_news_topic.py — 板块新闻「主题一致性」守卫（防错板 / 防跑题）。

历史教训
--------
2026-09-21：自动更新任务把「文玩手串」错认成「黄金/金手镯」，把金价、品牌金店、
            美联储议息写进了 bracelet-news.json。
2026-09-22：本板已收窄为「星月菩提」单一品种（bracelet.html 的「品种」区写明
            「当前 1 个：星月菩提」，7 个旧品类页已改跳转壳），但自动更新仍按旧口径
            继续产出——当天 6 条里 4 条沉香、1 条朱砂，星月菩提 0 条。

🔴 两次事故的真正共同点：**守卫写好了，但没有任何地方调用它。**
   本脚本 2026-09-21 就存在，却从未接进 CI 或 pre-commit，一次都没跑过
   （2026-09-22 复查 `grep -rn guard_news_topic scripts/ .github/ .githooks/` 只命中
   本文件自己的注释）。现已接入 .github/workflows/deploy.yml 与 .githooks/pre-commit。
   ——教训：加守卫时，把「调用点」一起改掉，否则等于没加。

三层判据
--------
1. HARD 禁词（命中即退出码 1）
   a. 金价/贵金属类：本板是文玩珠串，与黄金珠宝无关；
   b. 已下架品类的品种词：2026-09-22 起本板只剩星月菩提，
      沉香/奇楠/黄花梨/小叶紫檀… 一律视为跑题。
2. HARD 主题占比（本条才是根治跑题的那一条）
   本板条目中，必须有过半提到「星月菩提」相关词。它不依赖词表，
   任何未来新冒出来的跑题（哪怕词表没收录）都会让占比掉下来而被抓住。
3. WARN 疑似词（只提醒、不阻断）
   天然有歧义的词，一律不进 HARD，否则会误伤正品内容：
   - 蜜蜡 →「蜜蜡黄」是包浆色描述
   - 沉水 → 星月菩提讲密度必用「沉水测试」
   - 金刚菩提 / 落地红 → 正品避坑稿里会作为反面对照出现
   - 红木 / 核桃 → 「红木制品、红木核桃」是监管稿与展会稿的正当门类词
   - 黄金 →「黄金尺寸」是商家话术里的尺寸比喻（site 自家页面就在用）
   - 朱砂 →「朱砂供星月」是星月菩提的人工改色分类
   - 老山檀 →「加老山檀隔珠」是正当穿制工艺
   ⚠️ 这份「不进 HARD」的清单是 2026-09-22 拿现行星月菩提正文逐词反向对照后定下的
      （见本轮对话：蜜蜡/金刚菩提/沉水/黄金 四个词各命中 1–7 次，直接加禁会当场
      制造出一类新的 CI 红）。加词前务必重跑同样的对照，别凭直觉加。

设计纪律
--------
🔴 任何「只报 0 / 全绿」的检查都不可信 —— 必须先造一个「已知会失败」的样本，
   证明守卫真的会失败，再去测生产内容。本脚本内置该自证：
       python3 scripts/guard_news_topic.py --selftest
   它会分别造一个「跑题板」与一个「合格板」，断言前者必须 FAIL、后者必须 PASS。

用法
----
  python3 scripts/guard_news_topic.py            # 检查生产内容
  python3 scripts/guard_news_topic.py -q         # 静默模式（只报错）
  python3 scripts/guard_news_topic.py --selftest # 正反两向自证
"""
import argparse
import json
import os
import shutil
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ── 1. HARD 禁词：命中即判错板 ──────────────────────────────────────────
FORBIDDEN = {
    "bracelet-news.json": [
        # a) 金价 / 贵金属类（2026-09-21 事故：「手串」被错认成「金手镯」）
        "金价", "现货金", "足金", "金饰", "美联储", "盎司", "XAU",
        "周大福", "老凤祥", "老庙", "回收价", "品牌金", "国际金价", "金店",
        "金手镯", "金手链", "黄金价格", "黄金首饰", "黄金市场", "黄金回收", "黄金珠宝",
        # b) 已下架品种（2026-09-22 本板收窄为星月菩提单一品种）
        #    注意：仅列「不可能出现在星月菩提正文里」的词。
        #    有歧义的（黄金/老山檀/朱砂/金刚菩提/红木…）一律放 SUSPECT。
        "沉香", "奇楠", "星洲系", "惠安系",
        "黄花梨", "降香黄檀", "小叶紫檀", "檀香紫檀", "猛犸", "手镯",
    ],
}

# ── 3. WARN 疑似词：只提醒，不改退出码 ──────────────────────────────────
SUSPECT = {
    "bracelet-news.json": [
        "黄金", "蜜蜡", "绿松石", "南红", "朱砂", "核桃", "核雕", "红木",
        "金刚菩提", "凤眼菩提", "龙眼菩提", "落地红", "酸枣核",
        "百香籽", "菩提根", "紫金鼠", "猴头", "老山檀", "崖柏", "天珠",
        "翡翠", "和田玉", "绿菩提",
    ],
}

# ── 2. 主题词：本板条目须有过半命中，否则判跑题 ─────────────────────────
TOPIC = {
    "bracelet-news.json": [
        "星月", "菩提", "黄藤", "红藤子", "正月", "弦月", "月相", "月眼",
        "星点", "挂瓷", "开片", "包浆", "干磨", "水磨", "漂白", "脱脂",
        "原生态", "石玉料", "阴皮", "陈籽", "沉水", "密度", "对孔", "盘玩",
    ],
}
MIN_TOPIC_RATIO = 0.5
MIN_ENTRIES_TO_CHECK = 3  # 条目太少时占比无统计意义（例如只剩 1–2 条）


def _flat_text(item):
    """把一条新闻里所有会被读者看到的文本拼起来（摘要 + 正文 + 标签 + 来源名）。"""
    # 🔴 summary 必须一起算：2026-09-24 起条目改成「摘要常显 + 正文折叠」，
    # 读者在板块页上看到的是 summary。若只拿 content 判定主题词，
    # 一条把主题词写在摘要里、正文换成同义说法的稿子会被误判跑题。
    parts = [str(item.get("summary", "")), str(item.get("content", ""))]
    for t in item.get("tags") or []:
        if isinstance(t, dict):
            parts.append(str(t.get("text", "")))
    for s in item.get("sources") or []:
        parts.append(str(s))
    return "\n".join(parts)


def _snip(text, kw, width=30):
    i = text.find(kw)
    if i < 0:
        return ""
    a = max(0, i - width)
    b = min(len(text), i + len(kw) + width)
    return ("…" if a else "") + text[a:b].replace("\n", " ") + ("…" if b < len(text) else "")


def _load(root, fname):
    path = os.path.join(root, "static", fname)
    if not os.path.exists(path):
        return None, []
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f), []
    except Exception as e:  # noqa: BLE001
        return None, [f"[{fname}] JSON 解析失败: {e}"]


def _entries(data):
    if not isinstance(data, dict):
        return []
    return [n for n in (data.get("news") or []) if isinstance(n, dict)]


def scan(root=ROOT):
    """返回 (hard, warn, notes)。hard 非空即判失败。"""
    hard, warn, notes = [], [], []

    for fname in FORBIDDEN:
        data, errs = _load(root, fname)
        notes.extend(errs)
        if data is None:
            continue

        ents = _entries(data)
        if not ents:
            continue

        # 判据 1 / 3：逐条扫词
        for i, n in enumerate(ents):
            text = _flat_text(n)
            day = n.get("date", "?")
            for kw in FORBIDDEN.get(fname, []):
                if kw and kw in text:
                    hard.append(
                        f"[{fname}] news[{i}]({day}) 命中禁词「{kw}」：{_snip(text, kw)}"
                    )
            for kw in SUSPECT.get(fname, []):
                if kw and kw in text:
                    warn.append(f"[{fname}] news[{i}]({day}) 疑似跑题词「{kw}」")

        # 判据 2：主题占比
        toks = TOPIC.get(fname)
        if toks and len(ents) >= MIN_ENTRIES_TO_CHECK:
            hit = [i for i, n in enumerate(ents)
                   if any(t in _flat_text(n) for t in toks)]
            ratio = len(hit) / len(ents)
            if ratio < MIN_TOPIC_RATIO:
                hard.append(
                    f"[{fname}] 主题占比不合格：只有 {len(hit)}/{len(ents)} "
                    f"= {ratio:.0%} 的条目提到本板主题词（{'／'.join(toks[:5])}…），"
                    f"低于 {MIN_TOPIC_RATIO:.0%} 底线。"
                    f"本板已收窄为「星月菩提」单品口径，跑题条目要重写，不是加词表能解决的。"
                )

    return hard, warn, notes


def _mkboard(root, entries):
    os.makedirs(os.path.join(root, "static"), exist_ok=True)
    with open(os.path.join(root, "static", "bracelet-news.json"), "w", encoding="utf-8") as f:
        json.dump({"updated": "2026-09-22", "news": entries}, f, ensure_ascii=False, indent=2)


def _selftest():
    """正反两向自证：造一个「已知会失败」的板 + 一个「已知该通过」的板。"""
    base = tempfile.mkdtemp(prefix="guard_news_topic_selftest_")
    ok = True
    try:
        # 反向对照 1：整板跑题（复刻 2026-09-22 事故现场：全是沉香）
        bad = os.path.join(base, "bad")
        _mkboard(bad, [
            {"date": "09-22", "tags": [{"text": "沉香", "class": "hot"}],
             "content": "北京荣宝拍卖沉香精品专场开拍，遴选 40 件沉香作品。", "sources": []},
            {"date": "09-22", "tags": [{"text": "沉香造假", "class": "warn"}],
             "content": "文玩沉香手串近期多篇科普提示注油泡香精造假风险。", "sources": []},
            {"date": "09-21", "tags": [{"text": "消费警示", "class": "tag-red"}],
             "content": "越南广宁调查揭购物店以杂木泡香精冒充沉香。", "sources": []},
        ])
        hard_bad, _, _ = scan(bad)
        if not hard_bad:
            print("❌ 自证失败(反向)：明知整板是沉香，守卫却报通过 —— 判据失效")
            ok = False
        else:
            print(f"✅ 反向对照通过：跑题板被抓到 {len(hard_bad)} 处")
            for line in hard_bad[:4]:
                print(f"     {line}")

        # 反向对照 2：单条金价稿混进来
        bad2 = os.path.join(base, "bad2")
        _mkboard(bad2, [
            {"date": "09-22", "tags": [{"text": "星月菩提", "class": "hot"}],
             "content": "星月菩提原生态顺白与脱脂的区别，干磨水磨怎么分。", "sources": []},
            {"date": "09-22", "tags": [{"text": "星月菩提", "class": "hot"}],
             "content": "星月菩提盘玩四阶段：挂瓷、上色、包浆、开片。", "sources": []},
            {"date": "09-21", "tags": [{"text": "金价", "class": "hot"}],
             "content": "今日国际金价走高，品牌金店足金饰品报价上调。", "sources": []},
        ])
        hard_bad2, _, _ = scan(bad2)
        if not hard_bad2:
            print("❌ 自证失败(反向)：明知混入金价稿，守卫却报通过")
            ok = False
        else:
            print(f"✅ 反向对照通过：混入的错板稿被抓到 {len(hard_bad2)} 处")

        # 正向对照：合格板（全部围绕星月菩提，含正当的行业稿）
        good = os.path.join(base, "good")
        _mkboard(good, [
            {"date": "09-20", "tags": [{"text": "消费提示", "class": "warn"}],
             "content": "景区「尼泊尔直发」菩提手串多为内地加工后运回销售，落地红冒充实心大金刚是老套路。",
             "sources": ["今日头条 2026-09-20 · 尹文《出门旅游别乱买》"]},
            {"date": "09-18", "tags": [{"text": "星月菩提", "class": "hot"}],
             "content": "星月菩提列 2026 秋季材质热度榜第九名，一条高密正月从百元到千元不等。",
             "sources": ["今日头条 2026-09-18 · 洛潇金银珠宝观察室"]},
            {"date": "09-14", "tags": [{"text": "行业展会", "class": "info"}],
             "content": "济南第十一届文房四宝暨珠宝玉石博览会收官，现场提供免费鉴宝。",
             "sources": ["济南时报 2026-09-14"]},
            {"date": "09-10", "tags": [{"text": "选购避坑", "class": "warn"}],
             "content": "星月菩提不要买漂白顺白、药水染色阴皮、脱脂过度糠籽；干磨优于水磨。",
             "sources": ["今日头条 2026-09-10 · 尹文"]},
            {"date": "09-07", "tags": [{"text": "原料科普", "class": "info"}],
             "content": "海南野生黄藤实拍：星月菩提的原料是黄藤种核，全株密刺采摘不易。",
             "sources": ["今日头条 2026-09-07 · 阿乐行观"]},
        ])
        hard_good, warn_good, _ = scan(good)
        if hard_good:
            print("❌ 自证失败(正向)：合格板被误判失败 —— 守卫过严，会误伤正品内容")
            for line in hard_good:
                print(f"     {line}")
            ok = False
        else:
            print(f"✅ 正向对照通过：合格板放行（提醒 {len(warn_good)} 处疑似词，不阻断）")
            for line in warn_good[:4]:
                print(f"     {line}")
    finally:
        shutil.rmtree(base, ignore_errors=True)

    print("\n" + ("✅ 自证全部通过：守卫既抓得到跑题，也不误伤正品。" if ok
                  else "❌ 自证未通过，判据需要修正。"))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("-q", "--quiet", action="store_true", help="只报错，不报提醒")
    ap.add_argument("--selftest", action="store_true", help="正反两向自证判据是否有效")
    args = ap.parse_args()

    if args.selftest:
        sys.exit(_selftest())

    hard, warn, notes = scan()

    if notes:
        for line in notes:
            print(f"⚠️ {line}")

    if warn and not args.quiet:
        print(f"🔎 疑似跑题词 {len(warn)} 处（仅供参考，不阻断部署）：")
        for line in warn:
            print(f"   {line}")

    if hard:
        print("❌ 新闻主题一致性守卫未通过（发现错板 / 跑题内容）：")
        for line in hard:
            print(f"   {line}")
        print("\n   处理办法：把该板 news[] 重写为本板主题的条目后重新提交。")
        sys.exit(1)

    print("✅ 新闻主题一致性守卫通过：未命中错板禁词，主题占比达标。")
    sys.exit(0)


if __name__ == "__main__":
    main()
