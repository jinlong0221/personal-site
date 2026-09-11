#!/usr/bin/env python3
"""Extract executable inline <script> blocks from public/ and compute sha256 CSP hashes.

Usage: python3 compute_csp_hashes.py [--inject] [--csp-file PATH]
  Default: print unique hashes + which pages use them.
  --inject: also rewrite script-src in head.html and every static/*.html CSP meta
            (removes 'unsafe-inline', appends the unique sha256 hashes + keeps external domains).

Inline scripts that are data blocks (type=application/ld+json | application/json) or have a
src= attribute are SKIPPED (not executed by the browser, no hash needed).
"""
import os, re, sys, hashlib, html

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PUBLIC = os.path.join(ROOT, "public")
SKIP_TYPES = {"application/ld+json", "application/json"}

SCRIPT_RE = re.compile(r"<script\b([^>]*)>(.*?)</script>", re.DOTALL | re.IGNORECASE)

def sha256(s):
    return hashlib.sha256(s.encode("utf-8")).digest()

def b64(d):
    import base64
    return base64.b64encode(d).decode("ascii")

def collect():
    blocks = {}  # hash -> {'pages':set(), 'sample':'', 'len':int}
    for f in sorted(glob_html(PUBLIC)):
        try:
            raw = open(f, encoding="utf-8").read()
        except Exception:
            continue
        rel = os.path.relpath(f, PUBLIC)
        for attrs, content in SCRIPT_RE.findall(raw):
            if re.search(r"\bsrc\s*=", attrs, re.IGNORECASE):
                continue
            m = re.search(r"\btype\s*=\s*[\"']?([^\"'\s>]+)", attrs, re.IGNORECASE)
            if m and m.group(1).lower() in SKIP_TYPES:
                continue
            # CSP hashes the script's RAW text content (script is a raw-text element;
            # HTML entities are NOT decoded). Hash exactly as written.
            h = b64(sha256(content))
            if h not in blocks:
                blocks[h] = {"pages": set(), "sample": content.strip()[:80], "len": len(content)}
            blocks[h]["pages"].add(rel)
    return blocks

def glob_html(d):
    out = []
    for root, _, files in os.walk(d):
        for fn in files:
            if fn.endswith(".html"):
                out.append(os.path.join(root, fn))
    return out

def main():
    blocks = collect()
    print("=== Unique inline executable script hashes: %d ===" % len(blocks))
    for i, (h, info) in enumerate(sorted(blocks.items(), key=lambda kv: -kv[1]["len"]), 1):
        print(f"[{i}] sha256-{h}  (len={info['len']}, pages={len(info['pages'])})")
        print(f"     sample: {info['sample']!r}")
    raw_hashes = sorted(blocks)
    hashes = ["'sha256-%s'" % h for h in raw_hashes]
    print("\n=== script-src whitelist (%d hashes) ===" % len(hashes))
    print(" ".join(hashes))
    if "--inject" in sys.argv:
        inject(raw_hashes)

def inject(hashes):
    # hashes 此处为原始 base64（无 'sha256-' 前缀），由本函数统一加前缀，避免双重前缀。
    new_hashes = ["'sha256-%s'" % h for h in sorted(hashes)]
    # head.html (Hugo pages)
    head = os.path.join(ROOT, "layouts", "partials", "head.html")
    rewrite_csp(head, new_hashes)
    # every static page CSP meta
    n = 0
    for f in glob_html(os.path.join(ROOT, "static")):
        if rewrite_csp(f, new_hashes):
            n += 1
    print(f"\nInjected script-src into head.html + {n} static pages.")

def rewrite_csp(path, new_hashes):
    """Rewrite the CSP `script-src` of one file, preserving page-specific tokens.

    旧逻辑用固定基列表「'self' + 全部哈希 + 外链」整体覆写 script-src，会把各页面
    独有的令牌（如地图页的 'unsafe-eval'、map.qq.com、*.amap.com）整段抹掉，导致地图
    直接崩。修正为：只移除旧的 'sha256-...' 哈希与 'unsafe-inline'，其余既有令牌
    （'self'、'unsafe-eval'、外链域名等）原样保留，再追加当前全站哈希。

    匹配锚定在 CSP 的 meta `content="..."` 属性内，绝不会误伤 HTML 注释里的
    `script-src` 字样（旧版单行/跨行正则都曾踩这个坑导致整页 CSP 错乱）。
    """
    try:
        s = open(path, encoding="utf-8").read()
    except Exception:
        return False
    # 只匹配 CSP meta 的 content 属性
    meta_pat = re.compile(
        r'(<meta\b[^>]*Content-Security-Policy[^>]*content=")([^"]*)(")',
        re.IGNORECASE)
    mm = meta_pat.search(s)
    if not mm:
        return False
    csp = mm.group(2)
    csp_pat = re.compile(r"(script-src[ \t]+)([^;\n]*)(;)", re.IGNORECASE)
    cm = csp_pat.search(csp)
    if not cm:
        return False
    old_tokens = cm.group(2).split()
    # 保留非哈希、非 unsafe-inline 的既有令牌（'self'、'unsafe-eval'、地图域名等）
    keep = [t for t in old_tokens
            if t != "'unsafe-inline'" and not t.startswith("'sha256-")]
    merged, seen = [], set()
    for t in keep + new_hashes:
        if t not in seen:
            seen.add(t)
            merged.append(t)
    new_value = " ".join(merged)
    if new_value == cm.group(2):
        return False
    new_csp = csp_pat.sub(lambda mc: mc.group(1) + new_value + mc.group(3), csp, count=1)
    new = s[:mm.start(2)] + new_csp + s[mm.start(3):]
    open(path, "w", encoding="utf-8").write(new)
    return True

if __name__ == "__main__":
    main()
