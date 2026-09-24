#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
auto_summary.py — 板块新闻「摘要自愈」层（2026-09-24）

为什么需要它
────────────────────────────────────────────────────────────────
每天有 4 个自动任务（早 07:30 / 午 14:00 / 晚 21:00 / 每 3 小时补漏）往 11 个
`*-news.json` 写新闻，全是 LLM 驱动 ——「严格照格式写」是概率事件，不是保证。

而 `guard_news_length.py` 是**硬闸**，且跑在 Hugo 构建之前：一旦某班漏写
summary、写超长、或顺手带了个换行，CI 会红 → **整站停止部署**。
龙兄 2026-09-24 的原话：「所有按照时间节点更新的，千万不能有网站改动，就有出错的可能。」

所以这一层的定位是**守卫前面的自愈网**，执行顺序：

    auto_summary --fix  →  guard_news_length  →  hugo build  →  deploy

- 能自动修好的（缺 / 空 / 带换行 / 超长 / 过短 / 正文为空 / 两层写反）就地修好，
  部署照常走；
- 只有「summary 与 content 都空」这种**真的没内容可展示**的，才留给守卫去拦 ——
  拦下来是对的，那种条目就算上线读者也看不到东西。

自愈出来的摘要**不会编造事实**：它直接从该条 content 里截取，
所以「摘要里的每个数字都出现在同一条正文里」这条性质是**构造性成立**的。

两条硬保证
────────────────────────────────────────────────────────────────
1. **幂等 + 零扰动**：先拿守卫自己的 `check_item()` 判一遍，已经合规的条目
   **一个字节都不碰**（不重排 JSON、不改缩进、不动末尾换行、不规范化全角空格）。
   所以自动任务提交时不会因为本脚本产生无谓 diff。
2. **只认守卫的验收**：修完再用 `check_item()` 验一次，**验不过就不写**。
   这样「自愈」与「守卫」永远同一套判据，不会各说各话。

用法
────────────────────────────────────────────────────────────────
    python3 scripts/auto_summary.py                    # 只报告，不写盘
    python3 scripts/auto_summary.py --fix              # 就地修（CI / pre-commit 用）
    python3 scripts/auto_summary.py --fix --dry-run    # 看会改什么，不落盘
    python3 scripts/auto_summary.py --fix --file /tmp/a.json      # 指定文件（可重复）
    python3 scripts/auto_summary.py --fix --list-file=/tmp/l      # 回报改动清单（hook 用）
    python3 scripts/auto_summary.py --selftest         # 自证修法（改逻辑前先跑）
"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from guard_news_length import (  # noqa: E402
    MAX_SUMMARY,
    MIN_SUMMARY,
    check_item,
    collect_files,
    zh_len,
)

TARGET_LO = 80      # 写作目标下限（与自动任务提示词一致）
TARGET_HI = 120     # 写作目标上限
HARD_HI = MAX_SUMMARY   # 180，守卫的硬上限

SENT_END = "。！？；!?;"
YEAR_RE = re.compile(r"(?:19|20)\d{2}")
SRC_WORDS = ("来源", "报道", "信源", "交叉", "首发", "实测", "转引", "供稿",
             "通讯社", "网", "报", "讯")
KEEP_PREFIX = ("截至", "自", "从", "其中", "含", "约")
PAREN_RE = re.compile(r"[（(]([^（）()]{0,200})[)）]")

# 行级定位：这 11 个文件的值全是单行（已核实），所以按行改是安全的。
LINE_DATE = re.compile(r'^(\s*)"date"\s*:')
LINE_SUM = re.compile(r'^(\s*)"summary"\s*:\s*("(?:[^"\\]|\\.)*")(,?)[ \t]*(\r?\n?)$')
LINE_BODY = re.compile(r'^(\s*)"content"\s*:\s*("(?:[^"\\]|\\.)*")(,?)[ \t]*(\r?\n?)$')


# ── 文本处理 ────────────────────────────────────────────────────────
def clean_text(s):
    """归一空白为单空格 + 去掉行内 Markdown 记号（摘要必须是纯文字单段）。"""
    t = re.sub(r"\s+", " ", str(s if s is not None else "")).strip()
    return t.replace("**", "").replace("`", "")


def _looks_like_citation(inner):
    """判断括注里装的是不是「来源罗列」。"""
    if len(inner) < 8:
        return False
    if YEAR_RE.search(inner):
        return True
    return sum(1 for w in SRC_WORDS if w in inner) >= 2


def strip_citation(text, head=160):
    """删掉开头的来源括注。

    自动任务写正文的习惯是「9月24日（界面新闻 2026-09-23 15:09 首发、澎湃新闻…双源交叉）」。
    把这段搬进摘要，等于把板块页又变回来源清单 —— 那正是龙兄抱怨的观感来源。
    只在**正文前 160 字内**、且括注里带 4 位年份或两个以上来源词时才删；
    「（紫泥300CC）」这类规格括注、「（截至 9 月 23 日）」这类限定语都不动。
    """
    spans = []
    for m in PAREN_RE.finditer(text):
        if m.start() > head:
            break
        inner = m.group(1)
        if _looks_like_citation(inner) and not inner.strip().startswith(KEEP_PREFIX):
            spans.append((m.start(), m.end()))
    if not spans:
        return text
    out, prev = [], 0
    for a, b in spans:
        out.append(text[prev:a])
        prev = b
    out.append(text[prev:])
    return re.sub(r"\s+", " ", "".join(out)).strip()


def cut_at(text, limit):
    """切到 limit 字以内，优先切在句末标点；没有标点就硬切并补省略号。

    硬切时只保留 limit-1 个字再补「…」，否则「正文 limit 字 + 省略号」会变成
    limit+1 字、正好顶穿上限（这是自证里抓到的第一版 bug）。
    """
    if zh_len(text) <= limit:
        return text
    count, last_end = 0, -1
    for i, ch in enumerate(text):
        if count >= limit:
            break
        if not ch.isspace():
            count += 1
        if ch in SENT_END:
            last_end = i + 1
    if last_end > 0:
        return text[:last_end].strip()
    kept, count = [], 0
    for ch in text:
        if count >= limit - 1:
            break
        kept.append(ch)
        if not ch.isspace():
            count += 1
    return "".join(kept).rstrip() + "…"


def derive_summary(content):
    """从正文里截一段当摘要：先避开来源括注与开头日期，再按句取到 ≥80 字、最多 160 字。

    这是**兜底**手段（正常路径是自动任务自己写好 summary），所以宁可保守：
    只做「截取」，不做任何改写或概括，绝不引入原文没有的说法。
    """
    text = strip_citation(clean_text(content))
    # 摘要是「一眼看完发生了什么」，不该拿日期或来源开头（写作规范同款要求）
    text = re.sub(r"^(?:\d{1,2}月\d{1,2}日|\d{1,2}[/-]\d{1,2})[日]?[：:，,、；;\s]*", "", text)
    if not text:
        return ""
    if zh_len(text) <= TARGET_HI:
        return text                      # 正文本身就短：整条即摘要，不出折叠按钮
    parts = [p for p in re.split(r"(?<=[。！？；])", text) if p.strip()]
    acc = ""
    for p in parts:
        if not acc and zh_len(p) >= TARGET_HI:
            return cut_at(p, TARGET_HI)
        if acc and zh_len(acc + p) > TARGET_HI:
            break
        acc += p
        if zh_len(acc) >= TARGET_LO:
            break
    if zh_len(acc) < TARGET_LO:
        acc = cut_at(text, TARGET_HI)
    return acc.strip()


# ── 修复一条 ────────────────────────────────────────────────────────
def repair_item(item):
    """返回 (新条目, 修复说明列表)；无需/无法修复时返回 (None, [])。

    入口先跑守卫的 check_item：**已合规的原样放行**，这是「零扰动」的保证。
    """
    if not isinstance(item, dict):
        return None, []
    errs, _ = check_item(item)
    if not errs:
        return None, []

    new = dict(item)
    reasons = []
    s = clean_text(item.get("summary"))
    b = clean_text(item.get("content"))

    # ① 正文为空 → 摘要顶上（页面至少还有东西，不会点开一片空白）
    if not b:
        if not s:
            return None, []          # 两个都空：真的没内容，交给守卫拦
        b = s
        reasons.append("content 为空 → 用 summary 补上")

    # ② 摘要为空 → 从正文截
    if not s:
        s = derive_summary(b)
        reasons.append("缺 summary → 从正文截取")
    else:
        # ③ 归一（只对已被判不合规的条目做，合规条目在上面的 early return 已放行）
        if s != str(item.get("summary") or ""):
            reasons.append("summary 含换行/行内记号 → 归一为纯文字单段")
        # ④ 超长 → 按句切到硬上限（尽量少动，先切 180 而不是 120）
        if zh_len(s) > HARD_HI:
            s = cut_at(s, HARD_HI)
            reasons.append("summary 超长 → 按句切到 %d 字以内" % HARD_HI)

    # ⑤ 两层写反：正文比摘要还短 → 直接对调。
    #    对调是唯一「一个字都不丢」的修法：两份文本都留着，短的当摘要、长的当正文；
    #    若只是把摘要复制给正文，原来那段短文本就被顶掉了（信息净损失）。
    if s and b and zh_len(s) > zh_len(b):
        s, b = b, s
        reasons.append("正文比摘要短（两层写反）→ 对调两层，两份文本都保留")

    # ⑥ 过短 → 补。但**只在本条正文够长时**才补：正文自己也短时，
    #    摘要短就是正确形态（与守卫的条件判据保持一致），此时一个字都不该动 ——
    #    早先这里写了个「摘要取全文」的兜底，结果会把 ⑤ 对调后那份短文本覆盖掉
    #    （净丢文本），是自证里的最后一例把这个缺陷逼出来的。
    if s and zh_len(s) < MIN_SUMMARY and zh_len(b) >= MIN_SUMMARY:
        # 🔴 补的时候要拿「已去掉来源括注」的正文来补。否则补出来的就是
        #    「9月24日（界面新闻 2026-09-23 15:09 首发、澎湃新闻…」这一串来源清单 ——
        #    格式上合规了，观感上正好退回龙兄抱怨的那个样子（2026-09-24 自证时抓到）。
        b_stripped = strip_citation(b)
        if b_stripped.startswith(s):
            for p in re.split(r"(?<=[。！？；])", b_stripped[len(s):]):
                if not p.strip():
                    continue
                s = (s + p).strip()
                if zh_len(s) >= TARGET_LO:
                    break
            s = cut_at(s, HARD_HI)
            reasons.append("summary 过短 → 顺着正文（已去掉来源括注）补足")
        else:
            s = derive_summary(b)
            reasons.append("summary 过短 → 从正文重新截取")

    s = clean_text(s)
    b = clean_text(b)
    if not s:
        return None, []

    new["summary"] = s
    new["content"] = b

    # 🔴 只认守卫的验收：验不过就不写（两个都空是唯一走不到这里的正常情况）
    errs2, _ = check_item(new)
    if errs2:
        return None, []

    # 值与原文一模一样就没必要写（避免产生空改动）
    if s == str(item.get("summary") or "") and b == str(item.get("content") or ""):
        return None, []
    return new, reasons


# ── 落盘：文本级改写，保住原缩进与末尾换行风格 ────────────────────────
def _kv_line(key, value, indent, comma, eol):
    return '%s"%s": %s%s%s' % (indent, key, json.dumps(value, ensure_ascii=False), comma, eol)


def apply_fixes(path, dry_run=False):
    """返回 [(条目序号, 说明列表), ...]；无改动返回 []。"""
    with open(path, encoding="utf-8") as f:
        raw = f.read()
    data = json.loads(raw)
    news = data.get("news") if isinstance(data, dict) else None
    if not isinstance(news, list):
        return []

    plan = {}
    for i, item in enumerate(news):
        new_item, reasons = repair_item(item)
        if new_item is not None:
            plan[i] = (new_item, reasons)
    if not plan:
        return []

    lines = raw.splitlines(keepends=True)
    date_idx = [k for k, l in enumerate(lines) if LINE_DATE.match(l)]
    if len(date_idx) != len(news):
        # 行结构与条目数对不上（前面已核实是齐平的）——不冒险，留给守卫处理
        raise RuntimeError("行结构与条目数不齐（%d 行 vs %d 条），拒绝改写" % (len(date_idx), len(news)))

    # 倒序处理：插入行不会打乱前面条目的行号
    for i in sorted(plan, reverse=True):
        new_item, _ = plan[i]
        start = date_idx[i]
        end = date_idx[i + 1] if i + 1 < len(date_idx) else len(lines)

        s_li = b_li = None
        for k in range(start, end):
            if s_li is None and LINE_SUM.match(lines[k]):
                s_li = k
            elif b_li is None and LINE_BODY.match(lines[k]):
                b_li = k

        if b_li is None:
            # 「连 content 行都没有」这种形态当前 11 个文件不存在。
            # 与其做一次危险的插入（要连带修逗号、容易把 JSON 改坏），
            # 不如直接放弃 —— 交回守卫去拦，宁可挡住也不能写坏文件。
            raise RuntimeError("%s 第 %d 条缺少 content 行，拒绝改写" % (path, i + 1))

        # ① content 的值（行仍在原位）
        m = LINE_BODY.match(lines[b_li])
        if m.group(2) != json.dumps(new_item["content"], ensure_ascii=False):
            lines[b_li] = _kv_line("content", new_item["content"], m.group(1), m.group(3), m.group(4))

        # ② summary：有就改值；没有就在 content 那一行前面，用同样的缩进插一行
        #    （插进去的这行必须带逗号，因为后面跟着 content）
        if s_li is not None:
            m = LINE_SUM.match(lines[s_li])
            if m.group(2) != json.dumps(new_item["summary"], ensure_ascii=False):
                lines[s_li] = _kv_line("summary", new_item["summary"], m.group(1), m.group(3), m.group(4))
        else:
            m = LINE_BODY.match(lines[b_li])
            lines.insert(b_li, _kv_line("summary", new_item["summary"], m.group(1), ",", "\n"))

    out = "".join(lines)

    # 🔴 写盘前两道自检：JSON 必须仍可解析、且每条目标条目必须通过守卫判据
    check = json.loads(out)
    for i, (new_item, _) in plan.items():
        got = check["news"][i]
        if got.get("summary") != new_item["summary"] or got.get("content") != new_item["content"]:
            raise RuntimeError("第 %d 条改写结果与预期不符，拒绝写盘" % (i + 1))
        errs, _ = check_item(got)
        if errs:
            raise RuntimeError("第 %d 条改写后仍不合规：%s" % (i + 1, "；".join(errs)))

    if not dry_run:
        with open(path, "w", encoding="utf-8") as f:
            f.write(out)
    return [(i, r) for i, (_, r) in sorted(plan.items())]


# ── 自证 ────────────────────────────────────────────────────────────
def selftest():
    ok_sum = "甲" * 100
    ok_body = "乙" * 700
    cases = [
        ("合规条目不该被碰", {"summary": ok_sum, "content": ok_body}, False),
        ("合规但含多个空格（也不该被碰）", {"summary": "甲" * 40 + "  " + "甲" * 60, "content": ok_body}, False),
        ("缺 summary", {"content": ok_body}, True),
        ("summary 为空串", {"summary": "", "content": ok_body}, True),
        ("summary 只有空白", {"summary": "   ", "content": ok_body}, True),
        ("summary 过短且是正文前缀", {"summary": ok_body[:30], "content": ok_body}, True),
        ("summary 过短且与正文不同源", {"summary": "短" * 20, "content": ok_body}, True),
        ("summary 超长", {"summary": "甲" * 240, "content": "乙" * 900}, True),
        ("summary 带换行", {"summary": "甲" * 60 + "\n" + "甲" * 60, "content": ok_body}, True),
        ("content 为空、summary 尚可", {"summary": "甲" * 100, "content": ""}, True),
        ("正文比摘要短（两层写反）", {"summary": "甲" * 120, "content": "乙" * 60}, True),
        ("正文本身很短（本来就合规，不该碰）", {"summary": "甲" * 20, "content": "乙" * 30}, False),
        ("短简讯但两层写反", {"summary": "甲" * 40, "content": "乙" * 30}, True),
        ("两个都空（修不了，该交给守卫拦）", {"summary": "", "content": ""}, False),
    ]
    print("=" * 60)
    print("auto_summary 自证 --selftest")
    print("=" * 60)
    bad = 0
    for desc, item, expect_fix in cases:
        new, reasons = repair_item(item)
        fixed = new is not None
        ok = fixed == expect_fix
        mark = "✅" if ok else "❌"
        if not ok:
            bad += 1
        detail = "→ " + "；".join(reasons) if reasons else ""
        print("%s %-34s 期望%s / 实得%s %s" % (
            mark, desc, "修" if expect_fix else "不碰", "修" if fixed else "不碰", detail))
        # 修过的必须通过守卫
        if fixed:
            errs, _ = check_item(new)
            if errs:
                bad += 1
                print("     ❌ 修完仍不合规：%s" % "；".join(errs))
            # 幂等：再修一次应当返回「不碰」
            again, _ = repair_item(new)
            if again is not None:
                bad += 1
                print("     ❌ 不幂等：修完的条目再修一次仍被改")
    # 额外断言：对调两层时，两份文本都必须还在。
    # 「修好一个问题、又引出新问题」最容易发生在这里 —— 早先 ⑥ 的兜底分支
    # 就会把 ⑤ 刚对调过来的短文本覆盖掉。
    a_txt, b_txt = "甲" * 40, "乙" * 30
    new, reasons = repair_item({"summary": a_txt, "content": b_txt})
    if new is None or {a_txt, b_txt} != {new["summary"], new["content"]}:
        bad += 1
        print("❌ 两层对调后文本有丢失：%r" % (new,))
    else:
        print("✅ 两层对调后两份文本都还在（没有净丢文本）")

    # ── 落盘环节自证：文本级改写最容易把 JSON 改坏，必须端到端跑一次 ──
    #    （只验 repair_item 是不够的 —— 它只处理字典，不碰文件的行结构。）
    import tempfile
    sample = {
        "updated": "2026-09-24 07:00",
        "news": [
            {"date": "09-24", "tags": [{"text": "甲", "class": "hot"}],
             "content": "乙" * 300 + "。", "url": "https://example.com/x", "sources": ["S1"]},
            {"date": "09-23", "tags": [], "summary": "", "content": "", "url": "", "sources": []},
        ],
    }
    tmp = ""
    try:
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
            json.dump(sample, f, ensure_ascii=False, indent=2)
            tmp = f.name
        plan = apply_fixes(tmp)
        with open(tmp, encoding="utf-8") as f:
            data = json.load(f)          # 能解析＝没把 JSON 改坏
        n0, n1 = data["news"][0], data["news"][1]
        e2e = [
            ("缺 summary 的那条被补上", bool(n0.get("summary"))),
            ("补出来的摘要能过守卫", not check_item(n0)[0]),
            ("原文一个字没丢", n0["content"].startswith("乙" * 50)),
            ("缩进风格保持 2 空格", json.dumps(data, ensure_ascii=False, indent=2) == open(tmp, encoding="utf-8").read().rstrip("\n")),
            ("两个都空的那条没被动过", n1.get("summary") == "" and n1.get("content") == ""),
            ("只报了 1 条改动", len(plan) == 1),
        ]
        for desc, okk in e2e:
            if not okk:
                bad += 1
            print("%s 落盘：%s" % ("✅" if okk else "❌", desc))
    finally:
        if tmp and os.path.exists(tmp):
            os.unlink(tmp)

    print("-" * 60)
    if bad:
        print("[FAIL] 自证 %d 处不符" % bad)
        return 1
    print("[PASS] 自证 %d 例全部符合预期（含幂等与「修完必过守卫」两重检查）" % len(cases))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fix", action="store_true", help="就地修复（默认只报告）")
    ap.add_argument("--dry-run", action="store_true", help="配合 --fix：只显示，不写盘")
    ap.add_argument("--file", action="append", default=[], help="只处理指定文件（可重复）")
    ap.add_argument("--list-file", default="", help="把改动过的文件路径写到这个文件（hook 用来精确 git add）")
    ap.add_argument("-q", "--quiet", action="store_true", help="只输出结论行")
    ap.add_argument("--selftest", action="store_true", help="跑修法自证")
    args = ap.parse_args()

    if args.selftest:
        return selftest()

    files = args.file or collect_files()
    changed, blocked = [], []
    for path in files:
        try:
            plan = apply_fixes(path, dry_run=(not args.fix) or args.dry_run)
        except Exception as e:  # noqa: BLE001
            print("[auto_summary] ⚠️ %s 处理失败（交由守卫判定）：%s" % (path, e))
            continue
        if not plan:
            continue
        if (not args.fix) or args.dry_run:
            blocked.append((path, plan))
            continue
        changed.append(path)
        if not args.quiet:
            rel = os.path.relpath(path, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            print("[auto_summary] 已自愈 %s（%d 条）" % (rel, len(plan)))
            for i, reasons in plan:
                print("    · 第 %d 条：%s" % (i + 1, "；".join(reasons)))

    if args.list_file and changed:
        with open(args.list_file, "w", encoding="utf-8") as f:
            f.write("\n".join(changed) + "\n")

    if blocked and not args.quiet:
        print("[auto_summary] 以下文件需要自愈（当前为只报告模式，未写盘）：")
        for path, plan in blocked:
            print("  %s —— %d 条" % (path, len(plan)))
            for i, reasons in plan:
                print("      · 第 %d 条：%s" % (i + 1, "；".join(reasons)))

    if args.fix and not args.dry_run:
        print("[auto_summary] 自愈完成：改动 %d 个文件（0 表示本来就合规）" % len(changed))
    elif changed or blocked:
        print("[auto_summary] 只报告模式：%d 个文件待自愈" % len(blocked))
    else:
        print("[auto_summary] PASS：全部文件已合规，无需自愈")
    return 0


if __name__ == "__main__":
    sys.exit(main())
