#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
bump_v_hash.py — 后构建 ?v= 内容哈希化（自动版本化，免手动 bump）

解决的问题：
- 站点用 ?v=YYYYMMDD 做 CSS/JS 缓存破坏。手工日期版本号有两大痛点：
  1) 改了文件却忘了 bump ?v → 旧缓存不刷新，线上"改了跟没改一样"；
  2) 日期粒度太粗，一天内多次改动只有最后一次生效，且多个引用点需手工对齐。
- 本脚本在 hugo 构建产物 public/ 上做"事后改写"：
  把每个 src/href/url() 里的 ?v=YYYYMMDD 换成 ?v=h<sha256前12位>，
  哈希值由"被引用的那个资源文件内容"算出。文件没变 → 哈希不变 → 缓存命中；
  文件变了 → 哈希必变 → 浏览器自动拉新。从此永不再忘 bump，且缓存精度到字节。

设计要点（与现有护栏友好共存）：
- 只改 public/ 构建产物，绝不碰源码。源码 head.html / static/*.html 仍保留 ?v=\\d{8}，
  故 guard_v_param.py（只扫源码、强制 \\d{8}）继续 PASS，不触发任何回归。
- 仅改写"能解析到 public/ 内真实文件"的本地资源引用；外部 URL / 解析不到的保持原样。
- h 前缀保证哈希值永不像 8 位数字日期，任何 grep / 正则都不会误判。
- 幂等：跑两次结果一致；仅真正改动的文件才写回。
- 内置自校验：改写后重扫，凡可解析本地资源若仍为 ?v=\d{8} → 视为遗漏 FAIL；
  已写 ?v=h<hash> 与其文件内容重算不一致 → 完整性 FAIL。

用法：
  python3 scripts/bump_v_hash.py public            # 改写 + 自校验（CI 用）
  python3 scripts/bump_v_hash.py public --check    # 仅校验，不改写（可用于独立 CI 闸）
  python3 scripts/bump_v_hash.py public --dry-run   # 只打印将改什么，不写盘
"""

import os
import re
import sys
import hashlib
import base64

# 扫描的文件类型（均为文本）
SCAN_EXTS = {".html", ".css", ".js", ".xsl"}

# 匹配 src/href="...?v=DATE" 或 url(...?v=DATE)
# 同时捕获属性内整条值，便于在子串层面精确替换版本号、保留其余属性不动。
ATTR_RE = re.compile(
    r"""(?P<attr>src|href)\s*=\s*["'](?P<val>[^"']*?)(?P<vq>[?&]v=)(?P<ver>\d{8})["']"""
    r"""|url\(\s*["']?(?P<uval>[^"')]*?)(?P<uvq>[?&]v=)(?P<uver>\d{8})["']?\s*\)""",
    re.IGNORECASE,
)

# 校验阶段：已哈希的 ?v=h<hash>
HASH_RE = re.compile(
    r"""(?P<attr>src|href)\s*=\s*["'](?P<val>[^"']*?)\?v=h(?P<hsh>[0-9a-f]{12})["']"""
    r"""|url\(\s*["']?(?P<uval>[^"')]*?)\?v=h(?P<uhsh>[0-9a-f]{12})["']?\s*\)""",
    re.IGNORECASE,
)

HASH_LEN = 12

# 同域 <script src> / <link rel=stylesheet href> 的 SRI 注入：匹配标签名 + 整段属性串
SRI_TAG_RE = re.compile(r"<(script|link)\b([^>]*)>", re.IGNORECASE)


def sha12(path):
    """被引用资源文件内容的 sha256 前 12 位十六进制。"""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()[:HASH_LEN]


def resolve(asset_path, from_file, root):
    """把引用路径解析为 public/ 内真实文件路径；解析失败返回 None。"""
    if asset_path.startswith(("//", "data:")):
        return None
    # 同站绝对 URL（http(s)://host/path）按站点根解析：剥掉协议与主机，仅留路径。
    if asset_path.startswith(("http://", "https://")):
        rest = asset_path.split("://", 1)[1]
        slash = rest.find("/")
        if slash == -1:
            return None
        asset_path = rest[slash:]  # 形如 /js/app.js
    if asset_path.startswith("/"):
        cand = os.path.normpath(os.path.join(root, asset_path.lstrip("/")))
        return cand if os.path.exists(cand) else None
    # 相对路径：先相对当前文件目录，再退化到站点根（public/ 下资源都挂在根）
    base = os.path.dirname(from_file)
    cand = os.path.normpath(os.path.join(base, asset_path))
    if os.path.exists(cand):
        return cand
    cand2 = os.path.normpath(os.path.join(root, asset_path))
    return cand2 if os.path.exists(cand2) else None


def sha384_of(path):
    """同域资源文件的 sha384(base64)，用于 SRI integrity 属性（Web 世界的强制代码签名）。"""
    h = hashlib.sha384()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return "sha384-" + base64.b64encode(h.digest()).decode("ascii")


def attr_val(attrs, name):
    """从标签属性串中取出 name="..." / name='...' / name=token 的值；取不到返回 None。"""
    m = re.search(r"\b" + name + r"\s*=\s*(\"([^\"]*)\"|'([^']*)'|([^\s>]+))", attrs, re.IGNORECASE)
    if not m:
        return None
    return m.group(2) if m.group(2) is not None else (m.group(3) if m.group(3) is not None else m.group(4))


def inject_sri(text, fpath, root, cache_sri):
    """对同域 <script src>/<link rel=stylesheet href> 注入 integrity="sha384-…" + crossorigin。
    跨域(CDN/统计)/内联/data:/已含 integrity 的标签跳过。返回 (new_text, added, skipped)。
    """
    added = 0
    skipped = 0

    def repl(m):
        nonlocal added, skipped
        tag = m.group(1).lower()
        attrs = m.group(2)
        if "integrity=" in attrs.lower():
            return m.group(0)  # 已有 integrity（如 encrypt_travel 注入的 argon2 模块），不重复注入
        if tag == "script":
            path = attr_val(attrs, "src")
            if not path:
                return m.group(0)
        else:  # link：仅样式表需要 SRI；其他 rel（preload/icon…）不参与
            rel = attr_val(attrs, "rel")
            if not rel or "stylesheet" not in rel.lower():
                return m.group(0)
            path = attr_val(attrs, "href")
            if not path:
                return m.group(0)
        # 去除查询串/片段后解析到 public/ 内真实文件；解析不到（外部/CDN）跳过
        clean = path.split("?", 1)[0].split("#", 1)[0]
        real = resolve(clean, fpath, root)
        if real is None or not os.path.exists(real):
            skipped += 1
            return m.group(0)
        integ = cache_sri.get(real)
        if integ is None:
            integ = sha384_of(real)
            cache_sri[real] = integ
        new_attrs = attrs.rstrip()
        if not new_attrs.endswith(" "):
            new_attrs += " "
        prefix = "" if new_attrs.startswith(" ") else " "
        added += 1
        return "<" + m.group(1) + prefix + new_attrs + 'integrity="' + integ + '" crossorigin="anonymous">'

    return SRI_TAG_RE.sub(repl, text), added, skipped


def collect_files(root):
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        for fn in filenames:
            if os.path.splitext(fn)[1].lower() in SCAN_EXTS:
                out.append(os.path.join(dirpath, fn))
    return out


def transform(root, dry_run):
    """改写 public/ 内可解析本地资源的 ?v=DATE → ?v=h<hash>，并注入 SRI。
    返回 (changed_files, replaced, skipped, sri_added, sri_skipped)。
    """
    cache = {}       # 资源绝对路径 -> ?v 哈希（保证同文件同哈希）
    cache_sri = {}   # 资源绝对路径 -> sha384 integrity（保证同文件同哈希）
    changed_files = []
    replaced = 0
    skipped = 0      # 解析不到的外部/未知引用（?v 阶段，保持原样，不算错误）
    sri_added = 0
    sri_skipped = 0  # 跨域/已含 integrity/解析不到（SRI 阶段，保持原样）

    for fpath in collect_files(root):
        try:
            with open(fpath, "r", encoding="utf-8") as fh:
                text = fh.read()
        except (UnicodeDecodeError, OSError):
            continue

        def repl(m):
            nonlocal replaced, skipped
            if m.group("attr") is not None:
                path = m.group("val")
                ver = m.group("ver")
            else:
                path = m.group("uval")
                ver = m.group("uver")
            real = resolve(path, fpath, root)
            if real is None or not os.path.exists(real):
                skipped += 1
                return m.group(0)
            h = cache.get(real)
            if h is None:
                h = sha12(real)
                cache[real] = h
            token_old = "?v=" + ver
            if m.group(0).find(token_old) == -1:
                token_old = "&v=" + ver
            new = m.group(0).replace(token_old, "?v=h" + h, 1)
            replaced += 1
            return new

        new_text = ATTR_RE.sub(repl, text)
        # SRI 注入（独立于 ?v；同源 script/link 加 integrity，跨域跳过）。
        # 仅对 HTML/XSL 文档生效：.js/.css 内的 <script>/<link> 多为字符串字面量
        # （如 board-nav.js 动态注入自身的 '<script src=...>'），对它们注入会污染
        # 文件自身内容、且因文件遍历顺序导致跨文件哈希错配，故严格限制文档类型。
        ext = os.path.splitext(fpath)[1].lower()
        if ext in (".html", ".xsl"):
            new_text, sa, ss = inject_sri(new_text, fpath, root, cache_sri)
        else:
            sa, ss = 0, 0
        sri_added += sa
        sri_skipped += ss
        if new_text != text:
            changed_files.append(fpath)
            if not dry_run:
                with open(fpath, "w", encoding="utf-8") as fh:
                    fh.write(new_text)
    return changed_files, replaced, skipped, sri_added, sri_skipped


def verify(root):
    """自校验：返回 (errors, checked)。
    - 任何可解析本地资源仍带 ?v=\\d{8} → 遗漏错误。
    - 已带 ?v=h<hash> 但与其文件内容重算不一致 → 完整性错误。
    """
    errors = []
    errors = []
    checked = 0       # ?v=h 完整性校验计数
    sri_checked = 0   # SRI integrity 完整性校验计数
    for fpath in collect_files(root):
        try:
            with open(fpath, "r", encoding="utf-8") as fh:
                text = fh.read()
        except (UnicodeDecodeError, OSError):
            continue

        # 1) 残留日期版本（仅统计可解析本地资源）
        for m in ATTR_RE.finditer(text):
            path = m.group("val") if m.group("attr") is not None else m.group("uval")
            real = resolve(path, fpath, root)
            if real is not None and os.path.exists(real):
                errors.append(
                    f"{os.path.relpath(fpath, root)} -> 本地资源仍带日期版本 ?v={m.group('ver') or m.group('uver')}: {path}"
                )

        # 2) 已哈希完整性
        for m in HASH_RE.finditer(text):
            checked += 1
            path = m.group("val") if m.group("attr") is not None else m.group("uval")
            h = m.group("hsh") if m.group("attr") is not None else m.group("uhsh")
            real = resolve(path, fpath, root)
            if real is None or not os.path.exists(real):
                continue  # 解析不到的哈希引用无法校验，跳过（一般不会发生）
            if sha12(real) != h:
                errors.append(
                    f"{os.path.relpath(fpath, root)} -> ?v=h{h} 与文件内容不符（应为 h{sha12(real)}）: {path}"
                )

        # 3) SRI integrity 完整性（仅 HTML/XSL 文档：.js/.css 内的标签为字符串字面量，不校验）
        if os.path.splitext(fpath)[1].lower() in (".html", ".xsl"):
            for m in SRI_TAG_RE.finditer(text):
                attrs = m.group(2)
                integ = attr_val(attrs, "integrity")
                if not integ or not integ.startswith("sha384-"):
                    continue
                tag = m.group(1).lower()
                if tag == "script":
                    path = attr_val(attrs, "src")
                else:
                    rel = attr_val(attrs, "rel")
                    if not rel or "stylesheet" not in rel.lower():
                        continue
                    path = attr_val(attrs, "href")
                if not path:
                    continue
                clean = path.split("?", 1)[0].split("#", 1)[0]
                real = resolve(clean, fpath, root)
                if real is None or not os.path.exists(real):
                    continue  # 跨域/解析不到不校验
                sri_checked += 1
                if sha384_of(real) != integ:
                    errors.append(
                        f"{os.path.relpath(fpath, root)} -> SRI integrity 与文件内容不符（应为 {sha384_of(real)}）: {path}"
                    )
    return errors, checked, sri_checked


def main():
    args = sys.argv[1:]
    if not args:
        print("用法: bump_v_hash.py <public_dir> [--check] [--dry-run]")
        sys.exit(2)
    root = args[0]
    check_only = "--check" in args
    dry_run = "--dry-run" in args
    if not os.path.isdir(root):
        print(f"[bump_v_hash] 目录不存在: {root}")
        sys.exit(2)

    if check_only:
        errors, checked, sri_checked = verify(root)
        if errors:
            print(f"[bump_v_hash] CHECK FAIL: {len(errors)} 处问题")
            for e in errors:
                print(f"  - {e}")
            sys.exit(1)
        print(f"[bump_v_hash] CHECK PASS: {checked} 处 ?v=h 哈希完整、{sri_checked} 处 SRI integrity 完整、无残留日期版本")
        sys.exit(0)

    changed_files, replaced, skipped, sri_added, sri_skipped = transform(root, dry_run)
    if dry_run:
        print(f"[bump_v_hash] DRY-RUN: 将改写 {replaced} 处 ?v 引用、注入 {sri_added} 处 SRI；{len(changed_files)} 个文件受影响；{skipped} 处 ?v 外部/未知引用、{sri_skipped} 处 SRI 跨域/已注入引用保持原样")
        sys.exit(0)

    # 改写后自校验
    errors, checked, sri_checked = verify(root)
    if errors:
        print(f"[bump_v_hash] FAIL: 改写完成但自校验发现 {len(errors)} 处问题")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    print(f"[bump_v_hash] PASS: 改写 {replaced} 处 ?v 引用、{len(changed_files)} 个文件；注入 {sri_added} 处 SRI、{sri_skipped} 处跨域/已注入跳过；{checked} 处 ?v 哈希 + {sri_checked} 处 SRI 自校验通过")
    sys.exit(0)


if __name__ == "__main__":
    main()
