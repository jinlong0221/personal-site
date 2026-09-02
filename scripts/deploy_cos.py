#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
deploy_cos.py — 把 hugo 构建产物 public/ 增量同步到腾讯云 COS

## 为什么需要它

站点原本发布到 GitHub Pages，但**国内网络到 GitHub Pages 的 IP 长期不通**
（2026-09-02 实测：185.199.108~111.153 四个 IP 直连 443 全部超时，三轮重试 0/4；
对照组百度腾讯均通；GitHub 官方状态页无故障）。结果是国内访客整站打不开。

腾讯云 COS 是最省事的落点：源站放在腾讯云，域名解析过去即可，不用自己维护服务器，
也不用改动前面十几个构建步骤——只替换「发布」这一棒。

## 设计原则

1. **增量同步**。先拉远端对象清单，按 MD5 比对，只传变化的文件。全站约 1000 个文件，
   每次全量上传既慢又白烧流量，日常真正变化的往往只有几个。
2. **可选依赖、可缺席**。腾讯云 SDK 只在真要上传时才需要；没装 SDK 或没配密钥时，
   脚本直接跳过并返回 0，原有 GitHub Pages 流程不受任何影响——改造零风险。
3. **先演练后真跑**。`--dry-run` 只打印打算做什么，绝不动远端文件。
4. **删远端多余文件要显式确认**。默认不删（怕误伤），加 `--delete` 才删。

## 用法

    # 演练（不需要密钥，只看会同步哪些文件）
    python3 scripts/deploy_cos.py public --dry-run

    # 真跑（CI 里由 secrets 注入）
    python3 scripts/deploy_cos.py public \
        --secret-id "$TENCENTCLOUD_SECRET_ID" \
        --secret-key "$TENCENTCLOUD_SECRET_KEY" \
        --bucket "site-1234567890" \
        --region "ap-hongkong" \
        --delete --workers 16

退出码：0=成功或跳过；1=配置/同步出错。
"""

import argparse
import hashlib
import mimetypes
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

# COS 上对象的 ETag 对普通（非分块）上传就是文件内容的 MD5，可直接用于比对。
# 但分块上传的大文件 ETag 形如 "md5-N"，不能直接用，故标记为不可信、强制重传。
CHUNKED_ETAG_HINT = "-"


def local_files(root):
    """扫描本地目录，返回 {相对路径: (绝对路径, 字节数, md5)}。"""
    out = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d != ".git"]
        for fn in filenames:
            abs_path = os.path.join(dirpath, fn)
            rel = os.path.relpath(abs_path, root).replace(os.sep, "/")
            try:
                with open(abs_path, "rb") as fh:
                    data = fh.read()
            except OSError as e:
                print(f"  ! 读取失败跳过 {rel}: {e}", file=sys.stderr)
                continue
            out[rel] = (abs_path, len(data), hashlib.md5(data).hexdigest())
    return out


def guess_content_type(rel):
    ctype, _enc = mimetypes.guess_type(rel)
    if ctype:
        # 文本类一律补 charset，避免中文页面在部分浏览器出现乱码
        if ctype.startswith("text/") or ctype in (
            "application/javascript", "application/json", "application/xml",
        ):
            ctype += "; charset=utf-8"
        return ctype
    # 兜底：二进制流。站点里主要是 .woff2 / .webp 等，交给浏览器按内容嗅探
    return "application/octet-stream"


def build_client(secret_id, secret_key, region):
    """创建 COS 客户端；SDK 缺失时抛 ImportError 由调用方处理。"""
    from qcloud_cos import CosConfig, CosS3Client  # noqa: WPS433 (可选依赖，运行时才导入)

    config = CosConfig(Region=region, SecretId=secret_id, SecretKey=secret_key)
    return CosS3Client(config)


def remote_objects(client, bucket):
    """拉取远端全部对象，返回 {key: etag}。"""
    objs = {}
    marker = ""
    while True:
        resp = client.list_objects(Bucket=bucket, Marker=marker, MaxKeys=1000)
        for item in resp.get("Contents", []):
            objs[item["Key"]] = item.get("ETag", "").strip('"')
        if resp.get("IsTruncated") == "true":
            marker = resp.get("NextMarker") or ""
        else:
            break
    return objs


def cache_control(rel):
    """按文件类型给出缓存策略。

    这一条不设好，站点会出一种很隐蔽的毛病：文章明明改了、也部署上去了，
    可访客看到的还是旧页面——浏览器/CDN 把他上次访问的那份缓存住了。

    分寸是这样拿的：
      · HTML 页面 —— 每次都要回源问一句，内容一变就能立刻看到。
      · JSON 数据 —— 同理。这些是各板块的新闻数据，每天自动更新，
                      缓存住了就等于新闻永远停在那天。
      · JS / CSS  —— 站点给它们的文件名后面挂了内容哈希（?v=h...），
                      内容一变链接就变，等于换了个新文件，所以可以放心
                      缓存一年，反而让老访客打开更快。
      · 图片 —— 文件名是固定的（换了链接也还是那个名字），不敢缓存太久，
                      折中给 7 天。
    """
    low = rel.lower()
    if low.endswith((".html", ".htm")) or low == "/":
        return "no-cache"
    if low.endswith(".json"):
        return "no-cache"
    if low.endswith((".js", ".css", ".woff", ".woff2", ".ttf")):
        return "public, max-age=31536000, immutable"
    return "public, max-age=604800"


def plan_sync(local, remote, force=False):
    """比对出待上传 / 待删除清单。返回 (to_upload, to_delete, unchanged)。

    force=True 时忽略 ETag 全量重传。用途：缓存策略改了以后，文件本身没变
    （ETag 自然也对得上），但需要让新策略重新写一遍元数据——这时候就得强制重传，
    否则新策略永远落不到老文件头上。
    """
    to_upload, to_delete, unchanged = [], [], 0
    for rel, (_abs, _size, md5) in local.items():
        etag = remote.get(rel)
        # ETag 形如 "md5-N" 表示分块上传，无法直接比对内容，保守起见重传
        if (not force and etag and CHUNKED_ETAG_HINT not in etag
                and etag.lower() == md5.lower()):
            unchanged += 1
        else:
            to_upload.append(rel)
    for key in remote:
        if key not in local:
            to_delete.append(key)
    return sorted(to_upload), sorted(to_delete), unchanged


def main(argv=None):
    ap = argparse.ArgumentParser(description="增量同步 public/ 到腾讯云 COS")
    ap.add_argument("src", help="本地构建产物目录，通常是 public")
    ap.add_argument("--secret-id", default=os.environ.get("TENCENTCLOUD_SECRET_ID", ""))
    ap.add_argument("--secret-key", default=os.environ.get("TENCENTCLOUD_SECRET_KEY", ""))
    ap.add_argument("--bucket", default=os.environ.get("COS_BUCKET", ""))
    ap.add_argument("--region", default=os.environ.get("COS_REGION", "ap-hongkong"))
    ap.add_argument("--prefix", default=os.environ.get("COS_PREFIX", ""),
                    help="远端路径前缀，一般留空表示放在存储桶根目录")
    ap.add_argument("--delete", action="store_true",
                    help="删除远端存在但本地已没有的文件（默认不删）")
    ap.add_argument("--force", action="store_true",
                    help="忽略 ETag 全量重传（改了缓存策略后用它给老文件补上新策略）")
    ap.add_argument("--workers", type=int, default=16, help="并发上传线程数")
    ap.add_argument("--dry-run", action="store_true", help="只演练，不动远端")
    args = ap.parse_args(argv)

    if not os.path.isdir(args.src):
        print(f"[deploy_cos] 源目录不存在: {args.src}")
        return 1

    print(f"[deploy_cos] 扫描本地: {args.src}")
    local = local_files(args.src)
    print(f"[deploy_cos] 本地文件 {len(local)} 个")

    # 演练模式不需要任何凭证
    if args.dry_run:
        remote = {}
        to_upload, to_delete, unchanged = plan_sync(local, remote, args.force)
        print(f"[deploy_cos] DRY-RUN 演练结果：")
        print(f"    将上传 {len(to_upload)} 个（演练模式下远端视为空）")
        print(f"    无变化 {unchanged} 个")
        for rel in to_upload[:12]:
            print(f"      + {rel}")
        if len(to_upload) > 12:
            print(f"      ... 另有 {len(to_upload) - 12} 个")
        print("[deploy_cos] 演练未改动任何远端文件")
        return 0

    # 真跑。这里有个必须分清的界限，搞错会让 CI 显示"假绿"：
    #   · 三项全空      → 这个功能压根没启用（默认状态）→ 安静跳过，返回 0。
    #                     这样没接腾讯云的人跑这条流程不会红。
    #   · 配了但配不齐  → 说明有人想启用却配错了 → 必须报错。
    #   · 配齐了跑不动  → 说明环境有问题（缺 SDK / 密钥无效 / 网络不通）→ 必须报错。
    # 后两种如果也返回 0，CI 会一路绿灯，可站点根本没更新——那比报红危险得多，
    # 因为你压根不知道它没干活。
    missing = [n for n, v in (
        ("--secret-id", args.secret_id), ("--secret-key", args.secret_key),
        ("--bucket", args.bucket),
    ) if not v]

    if len(missing) == 3:
        print("[deploy_cos] 跳过 COS 部署：未配置 --secret-id / --secret-key / --bucket"
              "（未配置即视为不启用，原有 GitHub Pages 流程不受影响）")
        return 0
    if missing:
        print(f"[deploy_cos] COS 配置不完整，缺少 {' / '.join(missing)}。"
              f" 要么补全配置，要么把已填的那几项也一并去掉（全空即视为不启用）。")
        return 1

    try:
        client = build_client(args.secret_id, args.secret_key, args.region)
    except ImportError:
        # 已经明确配置了，却因为环境缺依赖而不干活——必须报红，不能悄悄跳过。
        print("[deploy_cos] 已配置 COS 但未安装 SDK，无法上传："
              "请先 pip install cos-python-sdk-v5")
        return 1

    print(f"[deploy_cos] 拉取远端清单: {args.bucket} @ {args.region}")
    try:
        remote = remote_objects(client, args.bucket)
    except Exception as e:
        print(f"[deploy_cos] 拉取远端清单失败: {type(e).__name__}: {e}")
        return 1
    print(f"[deploy_cos] 远端对象 {len(remote)} 个")

    to_upload, to_delete, unchanged = plan_sync(local, remote, args.force)
    print(f"[deploy_cos] 比对完成：新增/变化 {len(to_upload)}，无变化 {unchanged}，"
          f"远端多余 {len(to_delete)}")

    failed = []

    def put_one(rel):
        abs_path, _size, _md5 = local[rel]
        key = f"{args.prefix}{rel}" if args.prefix else rel
        try:
            with open(abs_path, "rb") as fh:
                client.put_object(
                    Bucket=args.bucket,
                    Body=fh,
                    Key=key,
                    ContentType=guess_content_type(rel),
                    CacheControl=cache_control(rel),
                )
            return rel, None
        except Exception as e:
            return rel, f"{type(e).__name__}: {e}"

    t0 = time.time()
    if to_upload:
        print(f"[deploy_cos] 开始上传 {len(to_upload)} 个文件（并发 {args.workers}）")
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            futs = [pool.submit(put_one, rel) for rel in to_upload]
            done = 0
            for fut in as_completed(futs):
                rel, err = fut.result()
                done += 1
                if err:
                    failed.append((rel, err))
                if done % 100 == 0 or done == len(to_upload):
                    print(f"    进度 {done}/{len(to_upload)}")
    else:
        print("[deploy_cos] 无文件需要上传")

    deleted = 0
    if to_delete:
        if args.delete:
            print(f"[deploy_cos] 删除远端多余文件 {len(to_delete)} 个")
            # COS 批量删除单次上限 1000
            for i in range(0, len(to_delete), 1000):
                batch = to_delete[i:i + 1000]
                try:
                    client.delete_objects(
                        Bucket=args.bucket,
                        Delete={"Object": [{"Key": k} for k in batch], "Quiet": "true"},
                    )
                    deleted += len(batch)
                except Exception as e:
                    print(f"    删除批次失败: {type(e).__name__}: {e}")
        else:
            print(f"[deploy_cos] 远端有 {len(to_delete)} 个文件本地已不存在；"
                  f"未删除（需要删除请显式加 --delete）")
            for k in to_delete[:8]:
                print(f"      - {k}")
            if len(to_delete) > 8:
                print(f"      ... 另有 {len(to_delete) - 8} 个")

    dt = time.time() - t0
    if failed:
        print(f"[deploy_cos] FAIL: {len(failed)} 个文件上传失败")
        for rel, err in failed[:10]:
            print(f"    ! {rel}: {err}")
        return 1

    print(f"[deploy_cos] OK: 上传 {len(to_upload)} 个，删除 {deleted} 个，"
          f"跳过未变化 {unchanged} 个，耗时 {dt:.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
