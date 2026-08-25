#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
apply_umami.py — 已弃用（安全加固 2026-08-22 起）

背景：
- Umami 此前仅为「占位死配置」（umami.example.com 是示例域名、UMAMI_WEBSITE_ID 从未填值），
  从未真实接入。红队加固已将其从 head.html CSP、全站 static 页、孤儿 partial 中彻底移除。
- 本脚本原先会在每次部署时把 umami.example.com 的 <script> 与宽 CSP 重新注入全站，
  属于回归源。现改为「安全空操作」：绝不写入任何内容，仅打印说明。
- 若日后真要接入 Umami，应新建独立、已配置好域名的注入脚本，而非复用此占位逻辑。

用法（兼容旧调用，行为为 no-op）：
  python3 scripts/apply_umami.py
  python3 scripts/apply_umami.py --check
"""
import sys


def main():
    check = "--check" in sys.argv
    print(
        "[apply_umami] 已弃用：Umami 为未配置的占位死配置，已从全站移除，本脚本不再注入任何内容。"
        + ("（--check 模式，无副作用）" if check else "")
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
