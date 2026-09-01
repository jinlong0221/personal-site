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
    hashes = ["'sha256-%s'" % h for h in sorted(blocks)]
    print("\n=== script-src whitelist (%d hashes) ===" % len(hashes))
    print(" ".join(hashes))
    if "--inject" in sys.argv:
        inject(hashes)

def inject(hashes):
    external = "https://hm.baidu.com https://busuanzi.ibruce.info"
    new_script_src = "'self' " + " ".join(hashes) + " " + external
    # head.html (Hugo pages)
    head = os.path.join(ROOT, "layouts", "partials", "head.html")
    rewrite_csp(head, new_script_src)
    # every static page CSP meta
    n = 0
    for f in glob_html(os.path.join(ROOT, "static")):
        if rewrite_csp(f, new_script_src):
            n += 1
    print(f"\nInjected script-src into head.html + {n} static pages.")

def rewrite_csp(path, new_script_src):
    try:
        s = open(path, encoding="utf-8").read()
    except Exception:
        return False
    if "Content-Security-Policy" not in s:
        return False
    pat = re.compile(r"(script-src\s+)([^;]*)(;)", re.IGNORECASE)
    if not pat.search(s):
        return False
    new = pat.sub(lambda m: m.group(1) + new_script_src + m.group(3), s, count=1)
    if new == s:
        return False
    open(path, "w", encoding="utf-8").write(new)
    return True

if __name__ == "__main__":
    main()
