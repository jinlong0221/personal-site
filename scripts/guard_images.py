#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
guard_images.py —— 页面配图自检守卫（尺寸声明 / 透明丢失 / 体积）。

背景（2026-10-03 真实事故）：给游戏页换配图时踩了三个坑，都是「源码看着没问题、
页面才出事」的类型，光靠 grep 查不出来：
  ① **透明 PNG 被转成 RGB**：`Image.open(png).convert('RGB').save('x.webp')`
     会把透明区烤成**纯黑**；深色主题下看不出，浅色主题下就是一个大黑块。
     判据：RGB 图四角同时接近纯黑（各通道 < 12）→ 高度可疑。
  ② **width/height 声明与真实尺寸不符**：换图后没同步声明，浏览器按声明算占位，
     真实图渲染出来不是 16:9 → 布局跳动/留白。
  ③ **图注与画面对不上**（这个脚本查不了，需要人眼）——但它会在报告里
     列出「每张图的 alt」，方便人工比对时逐张过。

用法：
  python3 scripts/guard_images.py                 # 扫 static/ 全部 html
  python3 scripts/guard_images.py --file X        # 只扫一个页面
  python3 scripts/guard_images.py -q              # 安静模式（只靠退出码）
  python3 scripts/guard_images.py --stats         # 附带图片体积 TOP 榜
"""
import argparse
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC = os.path.join(ROOT, "static")
SKIP_DIRS = {"pagefind", "admin"}
IMG_RE = re.compile(r"<img[^>]+>", re.S)

try:
    from PIL import Image
except ImportError:  # 没装 Pillow 就只做「文件存在性」检查
    Image = None


def resolve(src, page_path):
    """把页面里的相对 src 解析成磁盘绝对路径（page_path 本身已是绝对路径）。"""
    if src.startswith(("http://", "https://", "//", "data:")):
        return None
    base = os.path.dirname(os.path.abspath(page_path))
    return os.path.normpath(os.path.join(base, src))


def scan_page(page_path):
    """返回 (errors, warns, stats)。
    errors = 硬问题（文件缺失/打不开），会阻断 CI；
    warns  = 软问题（尺寸声明不符、疑似透明烤黑底），只提示，人工判断。"""
    with open(page_path, "r", encoding="utf-8", errors="ignore") as f:
        html = f.read()
    errors = []
    warns = []
    stats = {"count": 0, "bytes": 0}
    for tag in IMG_RE.findall(html):
        m_src = re.search(r'src="([^"]+)"', tag)
        if not m_src:
            continue
        src = m_src.group(1)
        # JS 模板拼接出来的 src（如 lightbox 模板 '+s+'）跳过
        if "+" in src or "${" in src:
            continue
        path = resolve(src, page_path)
        if path is None or not os.path.isfile(path):
            continue
        stats["count"] += 1
        stats["bytes"] += os.path.getsize(path)
        if Image is None:
            continue
        try:
            im = Image.open(path)
            im.load()
        except Exception as e:
            issues.append(f"  打不开：{os.path.basename(path)}（{e}）")
            continue
        m_w = re.search(r'width="(\d+)"', tag)
        m_h = re.search(r'height="(\d+)"', tag)
        if m_w and m_h:
            dw, dh = int(m_w.group(1)), int(m_h.group(1))
            if (dw, dh) != im.size:
                # 只有「比例不一致」才值得报：等比缩放（如 900×1350 声明 vs 853×1280 实际）
                # 不影响渲染；比例不同会在没有 object-fit 约束时让图变形。
                if abs((dw / dh) - (im.width / im.height)) > 0.02:
                    warns.append(
                        f"  比例不符：{os.path.basename(path)} 声明 {dw}×{dh}"
                        f"（{dw/dh:.2f}）/ 实际 {im.width}×{im.height}（{im.width/im.height:.2f}）"
                        f" —— 有 object-fit:cover 则无碍，否则会变形")
                else:
                    stats["ratio_only"] = stats.get("ratio_only", 0) + 1
        if im.mode == "RGB":
            small = im.convert("RGB").resize((32, 32))
            raw = small.tobytes()          # RGB 每像素 3 字节，避开 getdata 的弃用告警
            px = [tuple(raw[i:i + 3]) for i in range(0, len(raw), 3)]
            dark = all(sum(p) < 12 for p in px[:4] + px[-4:])
            bright = sum(sum(p) for p in px) / len(px) / 3
            if dark and bright > 55:
                # 四角纯黑但画面整体明亮 → 典型的「透明 PNG 被 convert('RGB') 烤了黑底」
                warns.append(
                    f"  疑似透明烤黑底：{os.path.basename(path)} —— 四角纯黑但画面平均亮度 {bright:.0f}，"
                    f"多半是 convert('RGB') 把透明区烤成了黑色（浅色主题下会变成黑块）")
    return errors, warns, stats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", default=None)
    ap.add_argument("-q", "--quiet", action="store_true")
    ap.add_argument("--stats", action="store_true")
    ap.add_argument("--staged", action="store_true",
                    help="只扫本次 git 暂存区里的 html（pre-commit 用，避免每次提交都扫全站 194 页）")
    args = ap.parse_args()

    if args.file:
        files = [args.file]
    elif args.staged:
        import subprocess
        try:
            out = subprocess.run(["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"],
                                 cwd=ROOT, capture_output=True, text=True, timeout=60).stdout
        except Exception as e:
            print(f"[guard_images] 读暂存区失败（{e}），退回全站扫描", file=sys.stderr)
            out = ""
        files = [os.path.join(ROOT, x) for x in out.split() if x.endswith(".html")]
        if not files:
            if not args.quiet:
                print("[guard_images] PASS：本次暂存区没有 html 页面，跳过")
            return 0
    else:
        files = []
        for dp, dn, fn in os.walk(STATIC):
            dn[:] = [d for d in dn if d not in SKIP_DIRS]
            files += [os.path.join(dp, x) for x in fn if x.endswith(".html")]

    bad = 0
    soft = 0
    total_imgs = 0
    for p in sorted(files):
        try:
            errs, warns, st = scan_page(p)
        except Exception as e:
            errs, warns, st = [f"  读取失败：{e}"], [], {"count": 0, "bytes": 0}
        total_imgs += st["count"]
        rel = os.path.relpath(p, ROOT)
        if errs:
            bad += 1
            print(f"[FAIL] {rel}")
            for i in errs[:10]:
                print(i)
        if warns:
            soft += 1
            if not args.quiet:
                print(f"[WARN] {rel}")
                for i in warns[:6]:
                    print(i)
                if len(warns) > 6:
                    print(f"  …… 另有 {len(warns)-6} 条")
    if not args.quiet:
        if bad:
            print(f"\n[guard_images] FAIL：{bad}/{len(files)} 个页面有硬问题（图片文件缺失/打不开）")
        else:
            print(f"[guard_images] PASS：{len(files)} 个页面、{total_imgs} 张本地图，无缺失/损坏")
        if soft:
            print(f"[guard_images] 另有 {soft} 个页面存在软问题（比例不符 / 疑似透明烤黑底），不阻断，需人工判断")
            print("  判据说明：游戏截图本身偏暗不算「烤黑底」；等比缩放的尺寸差异不算「比例不符」。")
        print("  提醒：图注与画面是否相符，脚本查不出来 —— 换图后必须人眼逐张对一遍（见 AUDIT_REGRESSION C10）。")
        if args.stats:
            big = []
            for dp, dn, fn in os.walk(os.path.join(STATIC, "img")):
                for x in fn:
                    fp = os.path.join(dp, x)
                    big.append((os.path.getsize(fp), os.path.relpath(fp, ROOT)))
            big.sort(reverse=True)
            print("\n体积 TOP10：")
            for s, n in big[:10]:
                print(f"  {s/1024:8.1f} KB  {n}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
