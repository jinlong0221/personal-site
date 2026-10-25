#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
guard_concise_copy.py — 全站文案「精华化」防回潮守卫

龙兄 2026-10-25：「网站是做技术交流的，不是做文字表述的……要放取其精华的文字，
让懂的人一看就懂，不喜欢各个板块的文字太多太浮肿。」

本守卫把上面这句话变成可自动执行的红线，四条判据：

  A 跨页重复正文段：同一段文字（≥40 中文字）出现在 ≥5 个页面 → FAIL
    （专治「同一句免责/引导语复制到全站每一页」——2026-10-25 精简前就是 81 页重复）

  B 口水话黑名单：只列「无论出现在哪都不含信息量」的短语 → FAIL
    （如「达到国际一线水准」「令人震撼」「发挥到极致」）

  C 元叙述黑名单：描述「本页是什么 / 本页曾是什么 / 接下来这一节讲什么」→ FAIL
    （如「本页原先作为该机型的独立图鉴存在」「这是本页的核心榜单」）

  D 超长段落：单个正文 <p> 超过 260 个中文字 → FAIL
    （技术交流站不该有整屏长段；应为短段 / 要点 / 表格）

豁免：页尾信息块（.page-meta）与「📌 资料说明」这类固定页脚块不参与 A 判据——
      它们是骨架要求（A9 audit_live_artifact.py 校验），且已由专门守卫把守。

用法：
  python3 scripts/guard_concise_copy.py            # 检查（有问题即 exit 1）
  python3 scripts/guard_concise_copy.py --selftest # 自证：故意造违规样本，必须被抓到
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC = os.path.join(ROOT, "static")

CJK = re.compile(r"[\u4e00-\u9fff]")
TAG = re.compile(r"<[^>]+>")

# ── B 口水话黑名单（这些词在任何语境下都不提供技术信息）────────────────
FLUFF = [
    "达到国际一线水准", "画面表现力达到", "让玩家能够体验到",
    "获得了极高的关注度", "年最热门的游戏之一",
    "令人震撼", "令人惊叹", "惊艳亮相", "美轮美奂",
    "发挥到极致", "极致演绎", "视听盛宴", "诚意之作",
    "史诗级体验", "重新定义了电动", "打破电动车的性能天花板",
]

# ── C 元叙述黑名单（描述页面本身，而非技术内容）────────────────────────
# 注：「内容来源：本页全部为……」是**出处声明**（一手记录/官方来源），不是自我描述，故不在此列。
META = [
    "本页原先", "现已整体并入", "这是本页的核心榜单", "合并后的主图鉴",
    "感谢你的理解与支持", "上面的配方讲的是", "一句话定位：",
    "如需查看详细参数或游戏列表",
]

# ── 阈值 ──────────────────────────────────────────────────────────────
DUP_MIN_PAGES = 5      # 同一段文字出现在几个页面就算「全站套话」
DUP_MIN_LEN = 40       # 段落至少这么多中文字才纳入重复检测
MAX_PARA_CJK = 260     # 单段中文字上限
SKIP_DIRS = ("/travel",)


def cjk(s: str) -> int:
    return len(CJK.findall(s))


def strip_tags(s: str) -> str:
    s = re.sub(r"<(script|style)\b.*?</\1>", " ", s, flags=re.S | re.I)
    s = re.sub(r"<!--.*?-->", " ", s, flags=re.S)
    s = TAG.sub(" ", s)
    return re.sub(r"\s+", " ", s).strip()


def page_files():
    for dp, _, files in os.walk(STATIC):
        if any(x in dp for x in SKIP_DIRS):
            continue
        for fn in sorted(files):
            if fn.endswith(".html"):
                yield os.path.join(dp, fn)


def is_redirect_shell(src: str) -> bool:
    """跳转壳页面：正文只有「本页已并入/停用，请去目标页」这一类提示。

    这类页面天然要在多页上重复同一句提示（每页都得告诉读者去哪），
    不属于「全站套话」，故豁免 A 判据。
    """
    if re.search(r'http-equiv="refresh"', src):
        return True
    if "恢复方法：" in src:
        return True
    return False


def analyse(path: str):
    """返回 (正文段落列表, 参与去重的段落集合)"""
    src = open(path, encoding="utf-8", errors="ignore").read()
    if is_redirect_shell(src):
        return []          # 跳转壳豁免
    # 去掉页尾信息块（骨架要求，不参与重复检测）
    body = re.sub(r'<div class="page-meta">.*?</div>\s*</div>', " ", src, flags=re.S)
    # 去掉「📌 资料说明」固定块
    body = re.sub(r'📌\s*资料说明.*?(?=<div class="section-label">|<!-- related|</main>)',
                  " ", body, flags=re.S)
    paras = []
    for m in re.finditer(r"<p\b[^>]*>(.*?)</p>", body, flags=re.S):
        t = strip_tags(m.group(1))
        if t:
            paras.append(t)
    return paras


def is_changelog(rel: str) -> bool:
    """更新日志页是「台账」：它天然要引用被改掉的旧措辞（如「本页原先…」），
    引用旧话不算浮肿，故豁免 A/B/C 词表判据（但仍受 D 超长段约束）。"""
    return os.path.basename(rel) == "changelog.html"


def run_checks():
    """执行四项判据，返回 (errors, pages, total_cjk)"""
    errors = []
    dup_index = {}
    total_cjk = 0
    pages = 0

    for p in page_files():
        rel = os.path.relpath(p, ROOT)
        pages += 1
        paras = analyse(p)
        cl = is_changelog(rel)
        for t in paras:
            n = cjk(t)
            total_cjk += n
            # D 超长段落（更新日志台账也适用）
            if n > MAX_PARA_CJK:
                errors.append(
                    f"[D 超长段] {rel}：单段 {n} 中文字（上限 {MAX_PARA_CJK}）"
                    f" —— 技术交流站请拆成短段/要点/表格。摘录：{t[:60]}…")
            # B / C 词表（更新日志台账豁免：它要引用旧措辞）
            for w in FLUFF:
                if not cl and w in t:
                    errors.append(
                        f"[B 口水话] {rel}：出现「{w}」—— 换成可核查的事实。摘录：{t[:60]}…")
            for w in META:
                if not cl and w in t:
                    errors.append(
                        f"[C 元叙述] {rel}：出现「{w}」—— 别描述页面本身，直接给内容。摘录：{t[:60]}…")
            # A 跨页重复
            if n >= DUP_MIN_LEN and not cl:
                key = re.sub(r"\s+", "", t)[:40]
                dup_index.setdefault(key, set()).add(rel)

    for key, pset in sorted(dup_index.items(), key=lambda kv: -len(kv[1])):
        if len(pset) >= DUP_MIN_PAGES:
            errors.append(
                f"[A 跨页重复] 同一段文字出现在 {len(pset)} 个页面（阈值 {DUP_MIN_PAGES}）"
                f"：{key[:40]}… 例：{sorted(pset)[:3]}")
    return errors, pages, total_cjk


def main():
    if "--selftest" in sys.argv:
        return selftest()

    errors, pages, total_cjk = run_checks()
    print(f"=== 文案精华化守卫：{pages} 页，正文 {total_cjk} 中文字 ===")
    if errors:
        for e in errors:
            print("  " + e)
        print(f"\n发现 {len(errors)} 处问题 ❌")
        return 1
    print("  PASS  A 跨页重复 / B 口水话 / C 元叙述 / D 超长段 四项全过 ✅")
    return 0


def selftest():
    """自证：造 4 个违规样本，必须逐项被抓到（守卫生效的唯一证据）。"""
    base = os.path.join(ROOT, "static", "__guard_selftest_tmp__")
    dup = "这是一段会被复制到很多页面的通用套话文字，长度足够触发跨页重复检测判据。" * 2
    samples = [
        ("A", "跨页重复", dup),
        ("B", "口水话", "本作画面表现力达到国际一线水准，是一款诚意之作。"),
        ("C", "元叙述", "本页原先作为该机型的独立图鉴存在，现已整体并入主页面。"),
        ("D", "超长段", "长" * (MAX_PARA_CJK + 20)),
    ]
    rc_all = 0
    try:
        for code, name, text in samples:
            paths = []
            for i in range(DUP_MIN_PAGES):
                path = f"{base}_{i}.html"
                paths.append(path)
                with open(path, "w", encoding="utf-8") as f:
                    f.write(f"<html><body><main><p>{text}</p></main></body></html>")
            errors, _, _ = run_checks()
            hit = any(e.startswith(f"[{code} ") for e in errors)
            print(f"  {'✓' if hit else '✗'} 自证 [{code}] {name}："
                  f"{'已抓到' if hit else '漏检！'}")
            if not hit:
                rc_all = 1
            for p in paths:
                os.remove(p)
        print("  自证通过 ✅" if not rc_all else "  自证失败 ❌")
        return rc_all
    finally:
        for i in range(DUP_MIN_PAGES):
            p = f"{base}_{i}.html"
            if os.path.exists(p):
                os.remove(p)


if __name__ == "__main__":
    sys.exit(main())
