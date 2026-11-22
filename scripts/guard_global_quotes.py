#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""科技动态页「英文原话」守卫（龙兄 2026-11-22 需求）。

校验三件事：
  1) global.json: 凡有 quoteEn 的条目，必须同时有非空的 quoteZh / quoteSrc；
     凡引用块的英文原句内不得出现中文字符（防止把中文翻译误塞进原句）。
  2) global.html: 渲染器仍含 gl-quote / quoteEn 分支；页面声明为「短句引用」口径，
     不得回退到旧的「不全文引用」单口径表述。
  3) 数据 updated 字段存在且为 8 位日期。

--selftest: 跑内置正/反例，不读真实文件。
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "static/data/global.json"
PAGE = ROOT / "static/global.html"


def has_cjk(s):
    return bool(re.search(r"[\u4e00-\u9fff]", s or ""))


def check_data(d):
    errs = []
    items = d.get("items", [])
    if not isinstance(items, list) or not items:
        errs.append("items 为空")
    quoted = 0
    for idx, it in enumerate(items):
        q = it.get("quoteEn")
        if not q:
            continue
        quoted += 1
        if not isinstance(q, str) or not q.strip():
            errs.append(f"#{idx} quoteEn 为空")
        if has_cjk(q):
            errs.append(f"#{idx} quoteEn 含中文字符（原句不应被翻译覆盖）")
        for f in ("quoteZh", "quoteSrc"):
            if not it.get(f) or not str(it[f]).strip():
                errs.append(f"#{idx} 有 quoteEn 但 {f} 缺失")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(d.get("updated", ""))):
        errs.append(f"updated 格式异常: {d.get('updated')!r}")
    return errs, quoted


def check_page(s):
    errs = []
    for needle in ("gl-quote", "i.quoteEn", "gl-quote-en", "gl-quote-zh", "gl-quote-src"):
        if needle not in s:
            errs.append(f"global.html 缺少渲染标记: {needle}")
    if "短句引用" not in s:
        errs.append("global.html 声明未使用「短句引用」口径")
    # 旧口径：整句「不全文引用」单独作为声明出现（新文案里它只是补充说明，与短句引用并存，允许）
    if "想看原话可以点链接回去自己读" in s:
        errs.append("global.html 仍残留旧的「想看原话点链接」说明")
    return errs


def selftest():
    good = {"updated": "2026-11-22", "items": [
        {"quoteEn": "Hello world.", "quoteZh": "你好", "quoteSrc": "X, 2026-11-22"},
        {"summary": "no quote"},
    ]}
    e, n = check_data(good)
    assert not e and n == 1, e
    bad = {"updated": "2026-11-22", "items": [
        {"quoteEn": "世界你好", "quoteZh": ""},
    ]}
    e, _ = check_data(bad)
    assert e, "反例应报错"
    page_ok = ' '.join(['gl-quote', 'gl-quote-en', 'gl-quote-zh', 'gl-quote-src', 'i.quoteEn', '短句引用'])
    assert not check_page(page_ok), check_page(page_ok)
    assert check_page("旧文案 想看原话可以点链接回去自己读")
    print("[selftest] PASS")


def main():
    if "--selftest" in sys.argv:
        selftest()
        return
    quiet = "-q" in sys.argv
    errs = []
    d = json.loads(DATA.read_text(encoding="utf-8"))
    e, n = check_data(d)
    errs += e
    errs += check_page(PAGE.read_text(encoding="utf-8"))
    if errs:
        for x in errs:
            print("[FAIL]", x)
        sys.exit(1)
    if not quiet:
        print(f"[guard_global_quotes] PASS: {n} 条原话结构合法，渲染器与声明口径正确")


if __name__ == "__main__":
    main()
