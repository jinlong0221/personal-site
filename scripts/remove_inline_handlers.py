#!/usr/bin/env python3
"""Remove inline event handlers from all HTML (replacing with data-* + delegated listeners).

Idempotent. Scans repo .html except public/ node_modules/ .git/ .workbuddy/ themes/.
Mappings:
  onclick="location.href='X'"            -> data-nav="X"
  onclick="copyText(this)" (data-text)  -> data-copy-text (rename) + drop onclick (handled by .copy-btn delegation)
  onclick="toggleHomeSection(this)"     -> data-act="toggleHomeSection"
  onclick="toggleCollapse(this)"        -> data-act="toggleCollapse"
  onclick="togglePitfall(this)"         -> data-act="togglePitfall"
  onclick="xwCopy()"                     -> data-act="xwCopy"
  onclick="document.getElementById('ID').scrollIntoView(...)" -> data-scroll="ID"
  onerror="this.style.display='none'"    -> data-hide-onerror="1"
  onerror="...retry..."                   -> (drop; global capture-phase fallback handles it)
"""
import os, re, glob

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXCLUDE = ("/public/", "/node_modules/", "/.git/", "/.workbuddy/", "/themes/")

def scan():
    out = []
    for f in glob.glob(os.path.join(ROOT, "**", "*.html"), recursive=True):
        if any(ex in f for ex in EXCLUDE):
            continue
        out.append(f)
    return out

# (pattern, replacement) — order matters
SUBS = [
    # 8) hide-on-error -> data attr (before generic onerror drop)
    (re.compile(r"""onerror\s*=\s*(["'])this\.style\.display\s*=\s*['"]none['"]\1"""),
     'data-hide-onerror="1"'),
    # 9) generic onerror drop (retry fallback handled globally)
    (re.compile(r"""onerror\s*=\s*(["'])[^"']*\1"""),
     ''),
    # 1) navigation
    (re.compile(r"""onclick\s*=\s*(["'])\s*location\.href\s*=\s*(["'])([^"']*)\2\s*\1"""),
     r'data-nav="\3"'),
    # 2a) copyText(this): rename data-text -> data-copy-text (handled by existing .copy-btn delegation)
    (re.compile(r"""data-text\s*=\s*(["'])([^"']*)\1"""),
     r'data-copy-text="\2"'),
    # 2b) copyText(this): drop onclick
    (re.compile(r"""onclick\s*=\s*(["'])copyText\(this\)\1"""),
     ''),
    # 3) toggleHomeSection
    (re.compile(r"""onclick\s*=\s*(["'])toggleHomeSection\(this\)\1"""),
     'data-act="toggleHomeSection"'),
    # 4) toggleCollapse
    (re.compile(r"""onclick\s*=\s*(["'])toggleCollapse\(this\)\1"""),
     'data-act="toggleCollapse"'),
    # 5) togglePitfall
    (re.compile(r"""onclick\s*=\s*(["'])togglePitfall\(this\)\1"""),
     'data-act="togglePitfall"'),
    # 6) xwCopy
    (re.compile(r"""onclick\s*=\s*(["'])xwCopy\(\)\1"""),
     'data-act="xwCopy"'),
    # 7) scrollIntoView
    (re.compile(r"""onclick\s*=\s*(["'])document\.getElementById\((["'])([^"']+)\2\)\.scrollIntoView\(\{[^}]*\}\)\1"""),
     r'data-scroll="\3"'),
]

def main():
    changed = 0
    for f in scan():
        try:
            html = open(f, encoding="utf-8").read()
        except Exception:
            continue
        new = html
        for rx, rep in SUBS:
            new = rx.sub(rep, new)
        if new != html:
            open(f, "w", encoding="utf-8").write(new)
            changed += 1
            print("changed:", os.path.relpath(f, ROOT))
    print(f"\nTotal files changed: {changed}")

if __name__ == "__main__":
    main()
