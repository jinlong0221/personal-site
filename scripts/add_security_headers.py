#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
为全站静态 HTML（static/ 下所有 *.html）注入安全加固块：
  ① 内容安全策略（meta CSP）
  ② Referrer 策略
  ③ 防 iframe 点击劫持的 frame-buster 脚本

说明：
- GitHub Pages 自定义域名无法下发 CSP / X-Frame-Options 等响应头，
  故用 <meta> CSP 等效，frame-ancestors 不支持则改用 JS 兜底。
- 仅注入到 <meta name="viewport" ...> 之后，与 layouts/partials/head.html 保持一致。
- 幂等：已含 Content-Security-Policy 的文件跳过，可反复运行。
- 与 sync_navbar.py 同性质：凡是重新生成 static/*.html 的脚本跑完后，应再跑本脚本。

用法：
  python3 scripts/add_security_headers.py            # 注入 static/
  python3 scripts/add_security_headers.py --check    # 仅报告缺漏，不写文件
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_DIR = os.path.join(ROOT, "static")

MARKER = "Content-Security-Policy"

BLOCK = """<!-- 安全加固①：内容安全策略（meta CSP；GitHub Pages 自定义域名无法下发响应头时的等效方案） -->
<meta http-equiv="Content-Security-Policy" content="default-src 'self'; script-src 'self' 'unsafe-inline' https://hm.baidu.com https://busuanzi.ibruce.info; style-src 'self' 'unsafe-inline'; img-src 'self' data: https://api.qrserver.com; font-src 'self' data:; connect-src 'self' https://api.open-meteo.com; frame-src 'none'; object-src 'none'; base-uri 'self'; form-action 'self'; upgrade-insecure-requests">
<!-- 安全加固②：Referrer 策略（同源泄露完整路径，跨域仅泄露源） -->
<meta name="referrer" content="strict-origin-when-cross-origin">
<!-- 安全加固③：防 iframe 点击劫持。meta CSP 无 frame-ancestors，用脚本兜底 -->
<script>
(function(){
  if(window.self !== window.top){
    try{ window.top.location.href = window.self.location.href; }
    catch(e){
      document.documentElement.style.visibility='hidden';
      document.addEventListener('DOMContentLoaded',function(){ document.documentElement.style.display='none'; });
    }
  }
})();
</script>
"""

VIEWPORT_RE = re.compile(r'(<meta\s+name="viewport"[^>]*>)', re.IGNORECASE)


def process_file(path, check_only):
    with open(path, "r", encoding="utf-8") as f:
        html = f.read()
    if MARKER in html:
        return "skip"
    m = VIEWPORT_RE.search(html)
    if not m:
        # 兜底：插到 <head> 之后
        head_m = re.search(r"(<head[^>]*>)", html, re.IGNORECASE)
        if head_m:
            html = html[: head_m.end()] + "\n" + BLOCK + html[head_m.end():]
            status = "inject(head)"
        else:
            return "no-head"
    else:
        html = html[: m.end()] + "\n" + BLOCK + html[m.end():]
        status = "inject"
    if not check_only:
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)
    return status


def main():
    check_only = "--check" in sys.argv
    if not os.path.isdir(STATIC_DIR):
        print(f"未找到 static 目录：{STATIC_DIR}")
        sys.exit(1)
    counts = {"inject": 0, "skip": 0, "no-head": 0}
    for dirpath, _, filenames in os.walk(STATIC_DIR):
        for fn in filenames:
            if not fn.endswith(".html"):
                continue
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, STATIC_DIR).replace(os.sep, "/")
            if rel.startswith("admin/") or "/admin/" in rel:
                continue  # 后台页自带宽松 CSP，跳过严格注入
            st = process_file(full, check_only)
            if st.startswith("inject"):
                counts["inject"] += 1
                if check_only:
                    print(f"  缺漏: {os.path.relpath(full, ROOT)}")
            elif st == "skip":
                counts["skip"] += 1
            elif st == "no-head":
                counts["no-head"] += 1
                print(f"  [警告] 无 <head>/viewport，未注入: {os.path.relpath(full, ROOT)}")
    mode = "（仅检查）" if check_only else ""
    print(f"\n完成{mode}：注入 {counts['inject']} 个，已存在跳过 {counts['skip']} 个，无 head 跳过 {counts['no-head']} 个。")


if __name__ == "__main__":
    main()
