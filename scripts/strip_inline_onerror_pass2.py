#!/usr/bin/env python3
"""Pass 2: strip residual inline `onerror` HTML attributes from all source .html.

Idempotent. The first-pass converter missed `onerror` values containing single
quotes (e.g. the zisha image-retry form `onerror="this.onerror=null;this.src=this.src+'?retry='+..."`)
because its regex stopped at the inner quote. This pass removes any remaining
`onerror="..."` / `onerror='...'` HTML attribute. Image retry / hide-on-error is
handled globally by the capture-phase listener added to app.js (see data-hide-onerror).

Scans repo .html except public/ node_modules/ .git/ .workbuddy/ themes/.
"""
import os, re, glob

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXCLUDE = ("/public/", "/node_modules/", "/.git/", "/.workbuddy/", "/themes/")

# onerror="..." (value may contain single quotes) OR onerror='...' (value may contain double quotes)
ONERROR = re.compile(r"""\s+onerror\s*=\s*"[^"]*"|\s+onerror\s*=\s*'[^']*'""")

def scan():
    out = []
    for f in glob.glob(os.path.join(ROOT, "**", "*.html"), recursive=True):
        if any(ex in f for ex in EXCLUDE):
            continue
        out.append(f)
    return out

def main():
    changed = 0
    for f in scan():
        try:
            html = open(f, encoding="utf-8").read()
        except Exception:
            continue
        new = ONERROR.sub("", html)
        if new != html:
            open(f, "w", encoding="utf-8").write(new)
            changed += 1
            print("changed:", os.path.relpath(f, ROOT))
    print(f"\nTotal files changed: {changed}")

if __name__ == "__main__":
    main()
