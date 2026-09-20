#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fetch_bracelet_images.py — 文玩手串板块「真实配图」下载 + 转码 + 出处登记

【在哪跑】
  在你自己联网的 Mac 终端跑（这个 AI 沙箱连不上维基共享资源，下载不了）。
  cd ~/陈金龙/代码与脚本/个人知识网站/hugo-site
  python3 scripts/fetch_bracelet_images.py

【做什么】
  1. 读 SOURCES（下面那个列表）：每项 = 本地文件名 + 图片来源 + 作者 + 许可 + 备注。
  2. 来源可以是：
       - 维基共享资源文件名：自动走 Special:FilePath 稳定解析（不用猜哈希前缀）；
       - 完整直链 URL（Flickr CC、博物馆官网等）。
  3. 下载前先查 HTTP 200 + 内容是图片，才保存原图。
  4. 用 Pillow 转 WebP（quality=80 视觉无损），源图最长边 >1600 才缩（清晰度优先，不乱缩）。
  5. 写入 static/img/bracelet/<本地名>.webp
  6. 生成 static/img/bracelet/ATTRIBUTIONS.md（来源 / 作者 / 许可），合规留痕。
  7. 任一来源取不到，只报“待补充”并跳过，不中断——你回头把对应 url 填上重跑即可。

【红线（龙兄定的）】
  只收 CC / 公有领域 / 官方图；绝不 AI 生成；绝不盗用版权大图。
  维基/Flickr 上确认许可再下；下载后自己肉眼看一眼确实是该材质，再提交。
"""
import os
import sys
import io
import urllib.request
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    sys.exit("❌ 需要 Pillow：pip install Pillow")

ROOT = Path(__file__).resolve().parent.parent          # hugo-site
OUT = ROOT / "static" / "img" / "bracelet"
OUT.mkdir(parents=True, exist_ok=True)

UA = "longxiong.vip-image-fetcher/1.0 (contact: webmaster@longxiong.vip)"

# 最长边上限（px）。源图比这大才缩，避免手机巨图；正常 CC 图一般不到这尺寸。
MAX_EDGE = 1600
WEBP_QUALITY = 80

# ───────────────────────────────────────────────────────────────────────────
# SOURCES —— 每个卡片要的图。url 留空 "" 表示「待龙兄在维基/Flickr 找 CC 图补上」。
# query 是给龙兄的搜索提示（在 commons.wikimedia.org 或 flickr.com 搜，筛 CC BY / CC0）。
# 维基文件名直接写 "File:XXX.jpg" 即可，脚本走 Special:FilePath 解析。
# ───────────────────────────────────────────────────────────────────────────
SOURCES = [
    # 本地名,                  url(或"File:名"),            作者,            许可,            备注/搜索词
    ("xingyue.webp",         "",                            "",              "",             "星月菩提实拍｜搜: 星月菩提 / Bodhi seed beads / moon star bodhi"),
    ("fengyan.webp",         "",                            "",              "",             "凤眼菩提实拍｜搜: 凤眼菩提 / Bodhi seed beads"),
    ("longyan.webp",         "",                            "",              "",             "龙眼菩提实拍｜搜: 龙眼菩提 / Longyan bodhi"),
    ("magu.webp",            "",                            "",              "",             "马骨/骨料手串实拍｜搜: 骨制手串 / bone beads bracelet"),
    ("mengma.webp",          "",                            "",              "",             "猛犸牙手串实拍（看勒兹纹）｜搜: 猛犸象牙 / mammoth ivory beads"),
    ("zijinboyu.webp",       "",                            "",              "",             "紫金钵盂菩提实拍｜搜: 菩提子手串 / bodhi seed bracelet"),
    ("xingyue-guide.webp",   "",                            "",              "",             "星月全套攻略配图（可复用星月图）｜搜: 星月菩提 包浆"),
    ("pinxiang.webp",        "",                            "",              "",             "手串品相/挑选实拍｜搜: 文玩手串 品相 / prayer beads macro"),
    ("wuxing.webp",          "",                            "",              "",             "多材质手串搭配实拍｜搜: 多宝手串 / mixed beads bracelet"),
    ("hero.webp",            "",                            "",              "",             "头图：星月/凤眼/金刚等菩提手串平铺实拍｜搜: 菩提手串 平铺 / bodhi mala flat lay"),
]

# 已确认可下的候选（示例，龙兄肉眼确认后把上面 url 填上即可）：
#   维基共享资源里佛教「念珠/佛珠」类目下有多张 CC 实拍，例如搜 "prayer beads" / "mala Buddhist"。
#   没把握的具体品种照片，宁可先用一张「真实念珠」通用图（也是真图），也别用版权图或 AI 图。


def resolve(url_or_file: str) -> str:
    """把 'File:XXX' 转成 Special:FilePath 直链；已是 http(s) 直链则原样返回。"""
    if url_or_file.startswith("http://") or url_or_file.startswith("https://"):
        return url_or_file
    name = url_or_file.split(":", 1)[-1] if ":" in url_or_file else url_or_file
    return f"https://commons.wikimedia.org/wiki/Special:FilePath/{urllib.parse.quote(name)}"


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        ctype = r.headers.get("Content-Type", "")
        if not ctype.startswith("image/"):
            raise ValueError(f"不是图片（Content-Type={ctype}）")
        return r.read()


def to_webp(data: bytes, dst: Path):
    img = Image.open(io.BytesIO(data)).convert("RGB")
    if max(img.size) > MAX_EDGE:
        scale = MAX_EDGE / max(img.size)
        img = img.resize((int(img.size[0] * scale), int(img.size[1] * scale)), Image.LANCZOS)
    img.save(dst, "WEBP", quality=WEBP_QUALITY, method=4)


def main():
    print(f"输出目录：{OUT}\n")
    ok, skip = [], []
    attr_lines = ["# 文玩手串板块配图出处（自动生成，提交前请核对许可）\n",
                  "> 所有图均为 CC / 公有领域 / 官方来源，非 AI 生成。\n", ""]
    for local, url_or_file, author, license_, note in SOURCES:
        dst = OUT / local
        if not url_or_file:
            print(f"⏭️  待补充：{local} —— {note}")
            skip.append((local, note))
            attr_lines.append(f"- **{local}**：待补充（{note}）")
            continue
        try:
            real = resolve(url_or_file)
            data = fetch(real)
            to_webp(data, dst)
            size = dst.stat().st_size
            print(f"✅ {local}  ({size//1024} KB)  ← {real}")
            ok.append(local)
            attr_lines.append(f"- **{local}**：来源 [{url_or_file}]({real})｜作者 {author or '未知'}｜许可 {license_ or '待填'}")
        except Exception as e:
            print(f"❌ {local}  失败：{e}")
            skip.append((local, f"{note} ｜错误：{e}"))

    attr_lines.append("")
    (OUT / "ATTRIBUTIONS.md").write_text("\n".join(attr_lines), encoding="utf-8")

    print(f"\n完成：成功 {len(ok)} 张，待补充/失败 {len(skip)} 张")
    print(f"出处登记：{OUT / 'ATTRIBUTIONS.md'}")
    if skip:
        print("\n待补清单（在 SOURCES 里把对应 url 填上后重跑）：")
        for s, n in skip:
            print(f"  - {s}: {n}")


if __name__ == "__main__":
    main()
